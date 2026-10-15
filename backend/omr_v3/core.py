"""Score conversion: page -> Audiveris OMR -> MusicXML -> transposition -> MuseScore PDF.

Experimental. Recognition accuracy is measured offline against hand-made
reference MusicXML (``scripts/omr_v3``); a successful HTTP response says
nothing about musical correctness, so every result carries review warnings.
30 s/page and 99 % accuracy are targets, not runtime thresholds.

Isolation: external tools run in their own process group with a scrubbed
environment (no API keys or Auth0/Sentry settings reach Java or MuseScore),
a private HOME inside the job directory and a hard wall-clock timeout.
"""
from __future__ import annotations

import concurrent.futures
import io
import logging
import math
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PIL import Image, ImageOps, UnidentifiedImageError

from . import cleanup
from .chords import align_ocr_chords, merge_chords, replace_chord_symbols, score_chords
from .geometry import GeometryError, load_geometry
from .transpose import transpose_score, validate_request

logger = logging.getLogger(__name__)

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 40_000_000
ALLOWED = {'.png', '.jpg', '.jpeg', '.pdf', '.xml', '.musicxml', '.mxl'}
# Audiveris needs roughly 15+ px between staff lines; phone photos and web
# images are often far smaller (the 745 px test JPEG has ~6 px). Small pages
# are upscaled toward A4 at 300 dpi before OMR.
TARGET_WIDTH = 2400
MAX_UPSCALE = 4
PDF_DPI = 300
OCR_LANGUAGES = os.environ.get('CAPOMATIC_OMR_OCR_LANGUAGES', 'eng+kor')

ChordDetector = Callable[[str], tuple[list[dict], dict]]


class ScoreError(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Result:
    pdf: bytes
    musicxml: bytes
    recognized_musicxml: bytes
    stages_ms: dict[str, float]
    report: dict = field(default_factory=dict)

    @property
    def warning(self) -> str:
        return self.report.get('warning', '')


def validate(data: bytes, suffix: str) -> None:
    if suffix not in ALLOWED:
        raise ScoreError('Unsupported format')
    if not data or len(data) > MAX_BYTES:
        raise ScoreError('File empty or exceeds 10 MiB', 413)
    if suffix == '.pdf' and not data.startswith(b'%PDF-'):
        raise ScoreError('Invalid PDF header')
    if suffix == '.png' and not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ScoreError('Invalid PNG header')
    if suffix in {'.jpg', '.jpeg'} and not data.startswith(b'\xff\xd8\xff'):
        raise ScoreError('Invalid JPEG header')
    if suffix in {'.png', '.jpg', '.jpeg'}:
        try:
            with Image.open(io.BytesIO(data)) as im:
                if im.format not in {'PNG', 'JPEG'} or getattr(im, 'is_animated', False):
                    raise ScoreError('Unsupported image')
                if im.width * im.height > MAX_PIXELS:
                    raise ScoreError('Image too large', 413)
                im.verify()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            raise ScoreError('Corrupt image') from exc
    if suffix == '.mxl':
        _validate_mxl(data)
    if suffix in {'.xml', '.musicxml'}:
        head = data[:4096].upper()
        if b'<!DOCTYPE' in head and b'MUSICXML' not in head or b'<!ENTITY' in data.upper():
            raise ScoreError('XML entities are not accepted')


MAX_MXL_UNCOMPRESSED = 30 * 1024 * 1024


def _validate_mxl(data: bytes) -> None:
    """Reject zip bombs and entity declarations inside compressed MusicXML."""
    import zipfile

    if not data.startswith(b'PK\x03\x04'):
        raise ScoreError('Invalid MXL archive')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            infos = z.infolist()
            if len(infos) > 50 or sum(i.file_size for i in infos) > MAX_MXL_UNCOMPRESSED:
                raise ScoreError('MXL archive too large', 413)
            for info in infos:
                if info.filename.endswith(('.xml', '.musicxml')) and b'<!ENTITY' in z.read(info).upper():
                    raise ScoreError('XML entities are not accepted')
    except zipfile.BadZipFile as exc:
        raise ScoreError('Invalid MXL archive') from exc


def _bin(env: str, *defaults: str) -> str:
    for name in ([os.environ[env]] if os.environ.get(env) else list(defaults)):
        found = shutil.which(name)
        if found:
            return found
    raise ScoreError(f'{env} executable unavailable', 503)


def _tool_env(home: Path) -> dict[str, str]:
    """Minimal environment for external tools: nothing secret is inherited."""
    env = {
        'PATH': os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin'),
        'HOME': str(home),
        'XDG_RUNTIME_DIR': str(home),
        'LANG': 'C.UTF-8',
        'QT_QPA_PLATFORM': 'offscreen',
        'JAVA_OPTS': os.environ.get('CAPOMATIC_OMR_JAVA_OPTS', '-Xmx1536m -Djava.awt.headless=true'),
    }
    for name in ('JAVA_HOME', 'TESSDATA_PREFIX', 'JAVA_TOOL_OPTIONS'):
        if os.environ.get(name):
            env[name] = os.environ[name]
    return env


def _run(argv: list[str], timeout_seconds: float, home: Path, what: str) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, env=_tool_env(home), cwd=home,
                                start_new_session=True)
    except OSError as exc:
        raise ScoreError(f'{what} could not start', 503) from exc
    try:
        out, _ = proc.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise ScoreError(f'{what} exceeded the operational safety timeout', 504) from exc
    if proc.returncode != 0:
        tail = out.decode('utf-8', 'replace')[-2000:] if out else ''
        logger.warning('%s failed (exit %s): %s', what, proc.returncode, tail)
        raise ScoreError(f'{what} failed', 422)
    return subprocess.CompletedProcess(argv, 0, out, b'')


def _pdf_pages(path: Path, timeout_seconds: float, home: Path) -> int:
    proc = _run([_bin('CAPOMATIC_PDFINFO_BIN', 'pdfinfo'), str(path)], timeout_seconds, home, 'PDF inspection')
    m = re.search(rb'(?m)^Pages:\s*(\d+)\s*$', proc.stdout)
    if not m:
        raise ScoreError('Cannot determine PDF page count')
    return int(m.group(1))


def rasterize(source: Path, suffix: str, out: Path, timeout_seconds: float, home: Path) -> dict:
    """Write the single page to *out* as a grayscale PNG the OMR and chord OCR share."""
    if suffix == '.pdf':
        pages = _pdf_pages(source, timeout_seconds, home)
        if pages != 1:
            raise ScoreError('This pilot accepts exactly one PDF page')
        stem = out.with_suffix('')
        _run([_bin('CAPOMATIC_PDFTOPPM_BIN', 'pdftoppm'), '-r', str(PDF_DPI), '-f', '1', '-l', '1',
              '-gray', '-png', '-singlefile', str(source), str(stem)], timeout_seconds, home, 'PDF rasterization')
        with Image.open(out) as im:
            width, height = im.size
        if width * height > MAX_PIXELS:
            raise ScoreError('PDF page too large', 413)
        return {'source': 'pdf', 'width': width, 'height': height, 'scale': 1.0}
    with Image.open(source) as im:
        im = ImageOps.exif_transpose(im).convert('L')
        scale = 1.0
        if im.width < TARGET_WIDTH:
            scale = min(MAX_UPSCALE, math.ceil(TARGET_WIDTH / im.width))
            # Never upscale beyond the pixel budget (e.g. a long, narrow strip).
            while scale > 1 and im.width * im.height * scale * scale > MAX_PIXELS:
                scale -= 1
            if scale > 1:
                im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
        im.save(out, format='PNG')
        return {'source': 'image', 'width': im.width, 'height': im.height, 'scale': float(scale)}


def run_audiveris(page: Path, out_dir: Path, timeout_seconds: float, home: Path) -> tuple[Path, Path]:
    out_dir.mkdir()
    _run([_bin('CAPOMATIC_AUDIVERIS_BIN', 'audiveris', 'Audiveris'), '-batch',
          '-constant', f'org.audiveris.omr.text.Language.defaultSpecification={OCR_LANGUAGES}',
          '-export', '-output', str(out_dir), '--', str(page)], timeout_seconds, home, 'Audiveris')
    scores = sorted(p for p in out_dir.rglob('*') if p.suffix.lower() in {'.mxl', '.musicxml'})
    books = sorted(out_dir.rglob('*.omr'))
    if not scores:
        raise ScoreError('No music staff was recognised on this page')
    if len(scores) != 1:
        raise ScoreError('OMR split the page into several movements; not supported in this pilot')
    return scores[0], (books[0] if books else None)


def render_pdf(musicxml: Path, pdf: Path, timeout_seconds: float, home: Path) -> None:
    _run([_bin('CAPOMATIC_MUSESCORE_BIN', 'mscore3', 'mscore', 'musescore', 'mscore4', 'musescore3'),
          '-o', str(pdf), str(musicxml)], timeout_seconds, home, 'MuseScore')
    if not pdf.is_file() or not pdf.read_bytes().startswith(b'%PDF-'):
        raise ScoreError('PDF rendering did not produce a valid file', 500)


def _add_header(score, title: str | None, summary: dict) -> None:
    from music21 import expressions, metadata, stream

    if score.metadata is None:
        score.metadata = metadata.Metadata()
    # music21 fills empty metadata with "Music21 Fragment"/"Music21", which
    # MuseScore would print on the sheet; a blank title keeps the page clean.
    score.metadata.title = title or (score.metadata.title if score.metadata.title not in (None, 'Music21 Fragment') else ' ')
    score.metadata.movementName = title or score.metadata.movementName or ' '
    if score.metadata.composer in (None, 'Music21'):
        score.metadata.composer = ''
    first = score.parts[0].getElementsByClass(stream.Measure).first()
    if first is None:
        return
    if summary['mode'] == 'capo' and summary['capo']:
        label = f"Capo {summary['capo']}"
    elif summary['mode'] == 'key' and summary['semitones'] and summary['keys']:
        k = summary['keys'][0]
        label = f"Key {k['original']} → {k['target']}"
    else:
        return
    te = expressions.TextExpression(label)
    te.placement = 'above'
    first.insert(0, te)


def process(data: bytes, suffix: str, semitones: int, mode: str = 'key', *,
            chord_detector: ChordDetector | None = None,
            safety_timeout_seconds: float | None = None) -> Result:
    """Run the full conversion and fail closed on tool errors."""
    validate(data, suffix)
    try:
        validate_request(mode, semitones)
    except ValueError as exc:
        raise ScoreError(str(exc)) from exc
    if safety_timeout_seconds is None:
        safety_timeout_seconds = float(os.environ.get('CAPOMATIC_OMR_TOOL_TIMEOUT_SECONDS', '300'))
    if not 10 <= safety_timeout_seconds <= 3600:
        raise ScoreError('Invalid operational tool timeout', 500)

    started = time.monotonic()
    stages: dict[str, float] = {}

    def lap(name: str, since: float) -> float:
        now = time.monotonic()
        stages[name] = round((now - since) * 1000, 1)
        return now

    report: dict = {'accuracy': 'unverified', 'chord_source': None, 'warnings': []}
    with tempfile.TemporaryDirectory(prefix='capomatic-v3-') as tmp:
        root = Path(tmp)
        home = root / 'home'
        home.mkdir()
        source = root / ('source' + suffix)
        source.write_bytes(data)
        title = None
        geometry = None
        ocr_items: list[dict] | None = None

        if suffix in {'.xml', '.musicxml', '.mxl'}:
            recognized = source
            report['input'] = {'source': 'musicxml'}
        else:
            t = time.monotonic()
            page = root / 'page.png'
            report['input'] = rasterize(source, suffix, page, safety_timeout_seconds, home)
            t = lap('rasterize', t)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                ocr_future = pool.submit(chord_detector, str(page)) if chord_detector else None
                recognized, book = run_audiveris(page, root / 'omr', safety_timeout_seconds, home)
                t = lap('omr', t)
                if ocr_future is not None:
                    try:
                        ocr_items, ocr_meta = ocr_future.result(timeout=safety_timeout_seconds)
                        title = (ocr_meta or {}).get('song_title') or None
                    except Exception:  # chord OCR is an enhancement; OMR output still stands
                        logger.exception('Chord OCR failed; keeping OMR chord names')
                        report['warnings'].append({'type': 'chord_ocr_failed'})
                t = lap('chord_ocr_wait', t)
            if book is not None:
                try:
                    geometry = load_geometry(book)
                except GeometryError:
                    logger.warning('Unreadable Audiveris book; chord placement skipped')

        t = time.monotonic()
        from music21 import converter, stream

        try:
            score = converter.parse(str(recognized))
        except Exception as exc:
            raise ScoreError('Recognised score could not be read') from exc
        if not score.parts:
            raise ScoreError('No recognized music parts')
        if len(score.parts) > 1:
            report['warnings'].append({'type': 'multiple_parts', 'count': len(score.parts)})

        report['repairs'] = {
            'rest_only_voices_removed': cleanup.drop_rest_only_voices(score),
            'lyrics_removed': cleanup.clean_lyrics(score),
            'chord_words': cleanup.chord_words_to_symbols(score),
            'marks_removed': cleanup.strip_marks(score),
        }
        measures = list(score.parts[0].getElementsByClass(stream.Measure))
        if geometry is not None and geometry.measure_count == len(measures):
            report['repairs']['ledger_notes_fixed'] = cleanup.fix_missed_ledgers(score, geometry, root / 'page.png')
        if ocr_items is not None and geometry is not None and geometry.measure_count == len(measures):
            placed = align_ocr_chords(ocr_items, geometry, report)
            report['chord_source'] = 'paddleocr'
            if os.environ.get('CAPOMATIC_OMR_CHORD_MERGE', '1') == '1':
                placed, added = merge_chords(placed, score_chords(score))
                report['chord_source'] = 'paddleocr+audiveris'
                report['chords_from_audiveris'] = added
            report['chords_placed'] = replace_chord_symbols(score, placed)
            report['chords_detected'] = len(ocr_items)
        elif ocr_items is not None:
            report['chord_source'] = 'audiveris'
            report['warnings'].append({'type': 'chord_alignment_unavailable',
                                       'omr_measures': len(measures),
                                       'geometry_measures': geometry.measure_count if geometry else None})
        else:
            report['chord_source'] = 'audiveris' if suffix not in {'.xml', '.musicxml', '.mxl'} else 'input'
        report['measures'] = len(measures)
        report['warnings'].extend({'type': 'bar_length', **w} for w in cleanup.measure_warnings(score))

        recognized_xml = root / 'recognized.musicxml'
        score.write('musicxml', fp=str(recognized_xml))
        summary = transpose_score(score, semitones, mode)  # type: ignore[arg-type]
        report['transposition'] = summary
        _add_header(score, title, summary)
        xml = root / 'transposed.musicxml'
        score.write('musicxml', fp=str(xml))
        t = lap('transpose', t)

        pdf = root / 'transposed.pdf'
        render_pdf(xml, pdf, safety_timeout_seconds, home)
        lap('render', t)
        stages['total'] = round((time.monotonic() - started) * 1000, 1)
        report['review_required'] = True
        report['warning'] = ('Experimental OMR: check notes, rhythm, chords and accidentals before use. '
                             f"{len([w for w in report['warnings'] if w['type'] == 'bar_length'])} bar(s) flagged.")
        return Result(pdf.read_bytes(), xml.read_bytes(), recognized_xml.read_bytes(), stages, report)
