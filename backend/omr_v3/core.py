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

from . import chord_coverage, cleanup, music_guard, quality, reliability
from .chords import align_ocr_chords, merge_chords, replace_chord_symbols, score_chords
from .geometry import GeometryError, load_geometry
from .transpose import transpose_score, validate_request

logger = logging.getLogger(__name__)

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 10
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
# (page image path, OCR chord items, semitones) -> (rendered page, info). Supplied by the
# host app so chord-only output is exactly V1's /render "replace" result.
ChordOnlyRenderer = Callable[[str, list[dict], int], tuple[Image.Image, dict]]


class ScoreError(Exception):
    def __init__(self, message: str, status: int = 422, report: dict | None = None):
        super().__init__(message)
        self.status = status
        self.report = report or {}


@dataclass(frozen=True)
class Result:
    pdf: bytes
    musicxml: bytes | None            # None in chord-only mode
    recognized_musicxml: bytes | None
    stages_ms: dict[str, float]
    report: dict = field(default_factory=dict)
    mode: str = 'full_score'          # 'full_score' or 'chord_only'
    png: bytes | None = None          # chord-only page image
    pages: tuple[Result | None, ...] = ()

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
        # sun.java2d.uiScale / GDK_SCALE make Audiveris skip its GTK HiDPI probe:
        # it loads libgtk-3 through JNA and only catches Exception, so on a
        # server image without GTK the UnsatisfiedLinkError killed every run.
        'GDK_SCALE': '1',
        'JAVA_OPTS': os.environ.get('CAPOMATIC_OMR_JAVA_OPTS',
                                    '-Xmx1536m -Djava.awt.headless=true -Dsun.java2d.uiScale=1'),
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


def _native_scale(source: Path, suffix: str, home: Path, timeout_seconds: float) -> float:
    """Native resolution of a raster PDF relative to the 300 dpi raster (1.0 for vector PDFs)."""
    if suffix != '.pdf':
        return 1.0
    try:
        out = _run([_bin('CAPOMATIC_PDFIMAGES_BIN', 'pdfimages'), '-list', str(source)],
                   timeout_seconds, home, 'PDF inspection').stdout.decode('utf-8', 'replace')
    except ScoreError:
        return 1.0
    best = None
    for line in out.splitlines()[2:]:
        f = line.split()
        if len(f) > 13 and f[2] == 'image':
            try:
                area, ppi = int(f[3]) * int(f[4]), float(f[12])
            except ValueError:
                continue
            if best is None or area > best[0]:
                best = (area, ppi)
    return min(1.0, best[1] / PDF_DPI) if best and best[1] > 0 else 1.0


def _preflight(source: Path, suffix: str, page: Path, home: Path, timeout_seconds: float):
    """Stage 1: judge the page as uploaded (images before our upscaling)."""
    if suffix in {'.png', '.jpg', '.jpeg'}:
        with Image.open(source) as im:
            return quality.assess(ImageOps.exif_transpose(im))
    with Image.open(page) as im:
        return quality.assess(im, native_scale=_native_scale(source, suffix, home, timeout_seconds))


def _chord_only(page: Path, items: list[dict] | None, semitones: int, renderer: ChordOnlyRenderer | None,
                report: dict, stages: dict, started: float) -> Result:
    """Fallback: V1 chord transposition on the page image; no notes are rewritten."""
    if renderer is None or items is None:
        raise ScoreError('This page is not reliable enough for full-score conversion, '
                         'and chord-only conversion is unavailable', 422)
    with Image.open(page) as image:
        coverage = chord_coverage.assess(image, items)
    report['chord_only_confidence'] = coverage
    if not coverage['accepted']:
        raise ScoreError(chord_coverage.REASON + ': Please upload a clearer PDF/image; '
                         'too few confident chord symbols cover the staff systems.', 422, report)
    t = time.monotonic()
    image, info = renderer(str(page), items, semitones)
    png, pdf = io.BytesIO(), io.BytesIO()
    image.convert('RGB').save(png, format='PNG')
    image.convert('RGB').save(pdf, format='PDF', resolution=PDF_DPI)
    stages['chord_only_render'] = round((time.monotonic() - t) * 1000, 1)
    stages['total'] = round((time.monotonic() - started) * 1000, 1)
    report['chord_only'] = info
    report['review_required'] = True
    report['warning'] = ('Chord-only result: the page or its recognition was not reliable enough to rewrite '
                         f"the notes ({report['decision']['reason']}). Only the {len(items)} recognised chord symbols were "
                         'transposed; any chord that was not recognised is still in the original key.')
    return Result(pdf.getvalue(), None, None, stages, report, mode='chord_only', png=png.getvalue())


def _process_page(data: bytes, suffix: str, semitones: int, mode: str = 'key', *,
            chord_detector: ChordDetector | None = None,
            chord_only_renderer: ChordOnlyRenderer | None = None,
            gate: bool = True,
            safety_timeout_seconds: float | None = None) -> Result:
    """Run the conversion and fail closed on tool errors.

    With *gate* on (the API always uses it) an unreliable page or recognition
    returns a chord-only result instead of a full score. The evaluation turns
    it off to measure what the full-score path would have produced; the
    decision is still computed and reported.
    """
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

    report: dict = {'accuracy': 'unverified', 'chord_source': None, 'warnings': [], 'gate_enforced': gate}
    with tempfile.TemporaryDirectory(prefix='capomatic-v3-') as tmp:
        root = Path(tmp)
        home = root / 'home'
        home.mkdir()
        source = root / ('source' + suffix)
        source.write_bytes(data)
        page = root / 'page.png'
        title = None
        geometry = None
        ocr_items: list[dict] | None = None
        preflight = None

        if suffix in {'.xml', '.musicxml', '.mxl'}:
            recognized = source
            report['input'] = {'source': 'musicxml'}
        else:
            t = time.monotonic()
            report['input'] = rasterize(source, suffix, page, safety_timeout_seconds, home)
            if report['input'].get('scale', 1.0) > 2:
                report['warnings'].append({'type': 'low_resolution_input',
                                           'upscale': report['input']['scale'],
                                           'advice': 'Use a 300 dpi PDF or a photo at least 2000 px wide.'})
            t = lap('rasterize', t)
            preflight = _preflight(source, suffix, page, home, safety_timeout_seconds)
            report['preflight'] = preflight.to_dict()
            t = lap('preflight', t)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                ocr_future = pool.submit(chord_detector, str(page)) if chord_detector else None

                def chord_items() -> list[dict] | None:
                    nonlocal title
                    if ocr_future is None:
                        return None
                    try:
                        items, meta = ocr_future.result(timeout=safety_timeout_seconds)
                    except Exception:  # chord OCR is an enhancement for the full score
                        logger.exception('Chord OCR failed')
                        report['warnings'].append({'type': 'chord_ocr_failed'})
                        return None
                    title = (meta or {}).get('song_title') or None
                    return items

                if gate and preflight.mode is quality.ProcessingMode.CHORD_ONLY:
                    decision = reliability.decide(preflight, None)
                    report['decision'] = decision.to_dict()
                    items = chord_items()
                    lap('chord_ocr_wait', t)
                    return _chord_only(page, items, semitones, chord_only_renderer, report, stages, started)
                recognized, book = run_audiveris(page, root / 'omr', safety_timeout_seconds, home)
                t = lap('omr', t)
                ocr_items = chord_items()
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
            'layout': cleanup.normalize_layout(score),
        }
        measures = list(score.parts[0].getElementsByClass(stream.Measure))
        aligned = geometry is not None and (
            geometry.remap_to_measures([m.measureNumberWithSuffix() for m in measures])
            or geometry.measure_count == len(measures))
        if aligned:
            report['repairs']['ledger_notes_fixed'] = cleanup.fix_missed_ledgers(score, geometry, page)
        if ocr_items is not None and aligned:
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
        bar_warnings = cleanup.measure_warnings(score)
        report['warnings'].extend({'type': 'bar_length', **w} for w in bar_warnings)

        if suffix not in {'.xml', '.musicxml', '.mxl'}:
            signals = reliability.post_omr_signals(score, geometry, aligned, len(bar_warnings))
            report['post_omr'] = signals.to_dict()
            decision = reliability.decide(preflight, signals)
            report['decision'] = decision.to_dict()
            if gate and decision.mode is quality.ProcessingMode.CHORD_ONLY:
                lap('analyse', t)
                return _chord_only(page, ocr_items, semitones, chord_only_renderer, report, stages, started)
        else:
            report['decision'] = {'mode': 'full_score', 'reason': 'musicxml_input'}

        recognized_xml = root / 'recognized.musicxml'
        score.write('musicxml', fp=str(recognized_xml))
        summary = transpose_score(score, semitones, mode)  # type: ignore[arg-type]
        report['transposition'] = summary
        _add_header(score, title, summary)
        xml = root / 'transposed.musicxml'
        score.write('musicxml', fp=str(xml))
        t = lap('transpose', t)

        # Stage 3: the files we are about to hand out must differ only by the transposition.
        guard = music_guard.validate(converter.parse(str(recognized_xml)), converter.parse(str(xml)),
                                     semitones, mode, summary)
        report['integrity'] = guard.to_dict()
        t = lap('integrity_check', t)
        if not guard.ok:
            logger.error('Transposition integrity check failed: %s', guard.issues[:5])
            raise ScoreError('Transposition integrity check failed; no result was produced', 500)

        pdf = root / 'transposed.pdf'
        render_pdf(xml, pdf, safety_timeout_seconds, home)
        lap('render', t)
        stages['total'] = round((time.monotonic() - started) * 1000, 1)
        report['review_required'] = True
        report['warning'] = ('Experimental OMR: check notes, rhythm, chords and accidentals before use. '
                             f"{len(bar_warnings)} bar(s) flagged.")
        return Result(pdf.read_bytes(), xml.read_bytes(), recognized_xml.read_bytes(), stages, report)


def process(data: bytes, suffix: str, semitones: int, mode: str = 'key', **kwargs) -> Result:
    """Process up to ten PDF pages sequentially; retain explicit failures in order."""
    validate(data, suffix)
    try:
        validate_request(mode, semitones)
    except ValueError as exc:
        raise ScoreError(str(exc)) from exc
    if suffix != '.pdf':
        return _process_page(data, suffix, semitones, mode, **kwargs)
    timeout = kwargs.get('safety_timeout_seconds')
    if timeout is None:
        timeout = float(os.environ.get('CAPOMATIC_OMR_TOOL_TIMEOUT_SECONDS', '300'))
    if not 10 <= timeout <= 3600:
        raise ScoreError('Invalid operational tool timeout', 500)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='capomatic-document-') as tmp:
        root = Path(tmp)
        source = root / 'source.pdf'
        source.write_bytes(data)
        count = _pdf_pages(source, timeout, root)
        if not 1 <= count <= MAX_PAGES:
            raise ScoreError(f'PDF must contain 1 to {MAX_PAGES} pages', 413)
        if count == 1:
            return _process_page(data, suffix, semitones, mode, **kwargs)
        _run([_bin('CAPOMATIC_PDFSEPARATE_BIN', 'pdfseparate'), str(source),
              str(root / 'input-%d.pdf')], timeout, root, 'PDF splitting')
        results, details, pdfs = [], [], []
        for number in range(1, count + 1):
            output = root / f'result-{number}.pdf'
            try:
                result = _process_page((root / f'input-{number}.pdf').read_bytes(),
                                       '.pdf', semitones, mode, **kwargs)
            except ScoreError as exc:
                # Integrity and service errors must never become a successful document.
                if exc.status != 422:
                    raise
                results.append(None)
                details.append({'page': number, 'mode': 'failure', 'status': exc.status,
                                'error': str(exc)})
                from PIL import ImageDraw
                placeholder = Image.new('RGB', (1240, 1754), 'white')
                draw = ImageDraw.Draw(placeholder)
                draw.text((80, 100), f'Page {number}: conversion failed', fill='black')
                draw.text((80, 140), 'No transposed score is available. Upload a clearer PDF/image.', fill='black')
                placeholder.save(output, format='PDF', resolution=150)
            else:
                results.append(result)
                details.append({'page': number, 'mode': result.mode,
                                'stages_ms': result.stages_ms, **result.report})
                output.write_bytes(result.pdf)
            pdfs.append(str(output))
        combined = root / 'combined.pdf'
        _run([_bin('CAPOMATIC_PDFUNITE_BIN', 'pdfunite'), *pdfs, str(combined)],
             timeout, root, 'PDF combination')
        failures = sum(r is None for r in results)
        report = {'document': {'page_count': count, 'successful_pages': count - failures,
                               'failed_pages': failures, 'complete': failures == 0},
                  'pages': details, 'review_required': True,
                  'warning': 'Review each page. Failure placeholders are not transposed scores.'}
        modes = {r.mode for r in results if r is not None}
        result_mode = 'partial_failure' if failures else (next(iter(modes)) if len(modes) == 1 else 'mixed')
        return Result(combined.read_bytes(), None, None,
                      {'total': round((time.monotonic() - started) * 1000, 1)},
                      report, mode=result_mode, pages=tuple(results))
