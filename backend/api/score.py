"""Full-score branch of /detect -> /render; legacy chord overlays stay separate."""
from __future__ import annotations

import asyncio
import io
import zipfile
import json
import hashlib
import os
import re
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import Response

from backend.omr_v3 import core, router as v3
from backend.omr_v3.source_layout import SourceLayoutBundle, readiness


def is_score(data: bytes, filename: str, processing: str) -> bool:
    if processing not in {'auto', 'chords', 'score'}:
        raise HTTPException(422, "processing must be auto, chords or score")
    suffix = Path(filename).suffix.lower()
    return processing == 'score' or (processing == 'auto' and (
        data.startswith(b'%PDF-') or suffix in {'.pdf', '.xml', '.musicxml', '.mxl'}))


async def caller(request: Request) -> str:
    if os.environ.get('CAPOMATIC_ENABLE_SCORE_API', '1') != '1':
        raise HTTPException(404, 'Full-score API is disabled')
    return await v3._caller(request)


async def execute(owner: str, operation):
    wait = v3.rate_limiter.check(owner)
    if wait is not None:
        raise HTTPException(429, 'Too many score operations; retry later',
                            headers={'Retry-After': str(int(wait) + 1)})

    def run():
        if not v3._slot.acquire(blocking=False):
            raise core.ScoreError('Score conversion is busy; retry shortly', 429)
        try:
            return operation()
        finally:
            v3._slot.release()

    try:
        return await asyncio.to_thread(run)
    except core.ScoreError as exc:
        detail = {'message': str(exc), 'report': exc.report}
        raise HTTPException(exc.status, detail,
                            headers={'Retry-After': '30'} if exc.status == 429 else None) from exc


def recognize(data: bytes, filename: str, chord_detector) -> core.Result:
    suffix = '.pdf' if data.startswith(b'%PDF-') else Path(filename).suffix.lower()
    core.validate(data, suffix)
    try:
        result = None
        if suffix == '.pdf' and b'/CapomaticSource' in data:
            from backend.omr_v3 import native_pdf
            result = native_pdf.recognize(data)
        if result is None:
            result = core.process(data, suffix, 0, 'key', recognition_only=True,
                                  preserve_notation=True,
                                  retain_source_layout=suffix not in {'.xml', '.musicxml', '.mxl'},
                                  chord_detector=chord_detector)
    except core.ScoreError as exc:
        if exc.status != 422:
            raise
        # A failed detection stays a 422, but an owner-bound diagnostic ID
        # allows later render requests to return the same evidence safely.
        result = core.Result(b'', None, None, {}, {
            'recognition_failure': {'message': str(exc), 'report': exc.report},
            'failure_status': 422,
        }, mode='recognition_failure', source_layout=SourceLayoutBundle(data, suffix, (None,)))
    result.report['source_sha256'] = hashlib.sha256(data).hexdigest()
    if suffix == '.pdf':
        name = unicodedata.normalize('NFC', Path(filename).stem)
        name = re.sub(r'_\d{8,}(?: \(\d+\))?$', '', name)
        name = re.sub(r'^\d+\s+', '', name)
        result.report['display_title'] = re.sub(r'-\d+$', '', name)[:200]
        result.report['display_title_basis'] = 'user_supplied_filename_not_verified_source_text'
    return result


def isolated_chords(image_path: str):
    """A native OCR crash must not terminate the API or lose its OMR job."""
    with tempfile.TemporaryDirectory(prefix='capomatic-chord-ocr-') as tmp:
        home = Path(tmp)
        output = home / 'chords.json'
        settings = {
            'PYTHONPATH': str(Path(__file__).resolve().parents[2]),
            'PYTHONDONTWRITEBYTECODE': '1',
            'PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK': 'True',
            'PADDLE_PDX_CACHE_HOME': os.environ.get('PADDLE_PDX_CACHE_HOME',
                                                   str(Path.home() / '.paddlex')),
            'CHORDTAYLOR_OCR_DET_MODEL': os.environ.get('CAPOMATIC_SCORE_DET_MODEL', 'mobile'),
            'CHORDTAYLOR_OCR_REC_MODEL': os.environ.get('CAPOMATIC_SCORE_REC_MODEL', 'en_PP-OCRv5_mobile_rec'),
            'PADDLE_OCR_CPU_THREADS': '1',
        }
        for name in ('PADDLE_ENABLE_MKLDNN',
                     'PADDLE_MAX_STITCHED_PIXELS', 'PADDLE_STITCH_MAX_SAFE_PIXELS',
                     'PADDLE_MIN_STITCH_RESIZE_SCALE'):
            if name in os.environ:
                settings[name] = os.environ[name]
        core._run(['env', *(f'{k}={v}' for k, v in settings.items()), sys.executable,
                   '-m', 'backend.ocr.score_worker', image_path, str(output)],
                  180, home, 'Chord OCR')
        if not output.exists():
            raise core.ScoreError('Chord OCR did not produce a result', 503)
        result = json.loads(output.read_text())
        return result['items'], result['meta']


def pages(result: core.Result) -> tuple[core.Result | None, ...]:
    return result.pages or (result,)


def summary(result: core.Result, semitones: int | None = None) -> dict:
    from music21 import converter, harmony, key, stream

    details = []
    for number, page in enumerate(pages(result), 1):
        row = {'page': number, 'can_render_full_score': False}
        if page is not None:
            row.update(report=page.report, stages_ms=page.stages_ms,
                       can_render_full_score=(page.mode == 'full_score'
                                              and page.recognized_musicxml is not None))
            if page.recognized_musicxml:
                score = converter.parseData(page.recognized_musicxml.decode(), format='musicxml')
                row['parts'] = len(score.parts)
                if len(score.parts) != 1:
                    row['can_render_full_score'] = False
                    row['limitation'] = 'Multi-part integrity is not verified by the current score guard'
                keys = list(score.recurse().getElementsByClass(key.KeySignature))
                row.update(
                    measures=len(list(score.parts[0].getElementsByClass(stream.Measure))),
                    notes_and_rests=sum(1 for n in score.recurse().notesAndRests
                                        if not isinstance(n, harmony.ChordSymbol)),
                    chords=len(list(score.recurse().getElementsByClass(harmony.ChordSymbol))),
                    lyric_entries=sum(1 for n in score.recurse().notesAndRests
                                      for lyric in n.lyrics if lyric.text),
                    key_fifths=keys[0].sharps if keys else 0,
                )
        bundle = result.source_layout
        source_page = bundle.pages[number-1] if bundle else None
        # V3 consistency is not a proof of unique OMR event/relation matching.
        semantic_ready = bool(row['can_render_full_score'] and not bundle
                              and page.report.get('input', {}).get('source') == 'musicxml'
                              and not page.report.get('warnings')) if page else False
        if source_page and source_page.evidence.get('native_profile_verified'):
            semantic_ready = True
        row.update(readiness(source_page, semantic_ready, number, semitones))
        if page and page.report.get('recognition_failure'):
            row['reasons'].append({'page': number, 'measure': None, 'object': None,
                                   'code': 'RECOGNITION_FAILED',
                                   **page.report['recognition_failure']})
        row['can_export_musicxml'] = bool(page and page.recognized_musicxml
                                           and page.mode == 'full_score')
        row['can_render_full_score'] = row['render_ready']
        if source_page:
            row['source_coordinates'] = source_page.metadata
        details.append(row)
    return {
        'processing': 'score', 'page_count': len(details), 'pages': details,
        'can_render_full_score': all(p['can_render_full_score'] for p in details),
        **{name: all(p[name] for p in details) for name in (
            'semantic_ready', 'geometry_ready', 'lyric_layer_ready', 'render_ready')},
        'render_request': {'semitones': semitones} if semitones is not None else None,
        'can_export_musicxml': all(p['can_export_musicxml'] for p in details),
        'accuracy': 'unverified', 'review_required': True,
        'source_completeness': 'unverified', 'stages_ms': result.stages_ms,
        'source_sha256': result.report.get('source_sha256'),
        'status': 'source_review_required',
    }


def cache_bytes(result: core.Result) -> int:
    """Count retained bytes, including source pixels, OMR and evidence metadata."""
    total = len(result.pdf) + len(result.musicxml or b'') + len(result.png or b'')
    total += len(result.recognized_musicxml or b'')
    total += len(json.dumps(result.report).encode())
    if result.source_layout:
        total += result.source_layout.byte_size
    return total + sum(cache_bytes(p) for p in result.pages if p)


def render(result: core.Result, semitones: int, output_format: str) -> Response:
    """Export editable semantics or fail closed on unproved raster replacement."""
    if output_format not in {'pdf', 'png', 'musicxml', 'zip'}:
        raise core.ScoreError('output_format must be pdf, png, musicxml or zip')
    try:
        core.validate_request('key', semitones)
    except ValueError as exc:
        raise core.ScoreError(str(exc)) from exc
    detection = summary(result, semitones)
    if output_format != 'musicxml':
        bundle = result.source_layout
        if bundle and bundle.pages and all(
                page and page.evidence.get('native_profile_verified') for page in bundle.pages):
            return _render_native(result, semitones, output_format, detection)
        if (semitones == 0 and bundle and bundle.suffix == '.pdf'
                and b'/CapomaticSource' not in bundle.source and output_format in {'pdf', 'zip'}):
            from backend.omr_v3.source_layout import pdf_metadata
            metadata = pdf_metadata(bundle.source)
            report = {'render_path': 'lossless_original_pdf_identity', 'semitones': 0,
                      'identity_only': True, 'nonzero_transposition_demonstrated': False,
                      'source_sha256': bundle.sha256, 'output_sha256': bundle.sha256,
                      'page_count': len(metadata), 'page_metadata': metadata,
                      'all_original_bytes_preserved': True,
                      'accuracy': 'unverified', 'source_detection': detection}
            return _output(bundle.source, [], report, [], output_format, identity=True)
        reasons = [reason for p in detection['pages'] for reason in p['reasons']]
        detection['first_blocker'] = reasons[0] if reasons else {'code': 'COMPLETE_OWNERSHIP_IMPLEMENTATION_REQUIRED'}
        detection['secondary_blockers'] = reasons[1:]
        detection['collision_assessment'] = 'NOT_EVALUABLE_WITHOUT_COMPLETE_OWNERSHIP'
        raise core.ScoreError(
            'Geometry-locked rendering is not ready: source pixel ownership, '
            'lyric separation or semantic relationships need verification', 422, detection)
    source_pages = pages(result)
    if len(source_pages) != 1:
        raise core.ScoreError('MusicXML export requires exactly one complete page', 422, detection)
    if not detection['can_export_musicxml']:
        raise core.ScoreError('Recognition needs correction before MusicXML export', 422, detection)
    page = source_pages[0]
    rendered = core.process(page.recognized_musicxml, '.musicxml', semitones, 'key',
                            preserve_notation=True, musicxml_only=True)
    return Response(rendered.musicxml, media_type='application/vnd.recordare.musicxml+xml', headers={
        'Content-Disposition': 'attachment; filename="transposed.musicxml"',
        'Cache-Control': 'no-store', 'X-Capomatic-Mode': 'editable_semantics',
        'X-Capomatic-Preservation': 'No source layout or lyric pixel preservation guarantee',
        'X-OMR-Accuracy': 'unverified',
    })


def _render_native(result, semitones, output_format, detection):
    from backend.omr_v3 import native_pdf
    bundle = result.source_layout
    if output_format == 'png' and len(bundle.pages) != 1:
        raise core.ScoreError('PNG requires one page; use PDF or ZIP', 422, detection)
    try:
        images, reports, xml_pages = native_pdf.compose(bundle.source, semitones)
        pdf = native_pdf.lossless_pdf(images, [p.metadata for p in bundle.pages])
    except core.ScoreError as exc:
        if exc.status != 422:
            raise
        blocker = {'code': exc.report.get('first_blocker', str(exc)),
                   **{k: v for k, v in exc.report.items() if k != 'first_blocker'}}
        report = {**detection, 'first_blocker': blocker,
                  'secondary_blockers': [], 'render_ready': False}
        raise core.ScoreError(str(exc), 422, report) from exc
    report = {'render_path': 'native_geometry_transposition' if semitones else 'native_identity',
              'semitones': semitones, 'pages': reports, 'render_ready': True,
              'semantic_ready': True, 'geometry_ready': True, 'lyric_layer_ready': True,
              'source_sha256': bundle.sha256,
              'accuracy': 'UNVERIFIED; source-provided native semantics, not OMR accuracy'}
    return _output(pdf, images, report, xml_pages, output_format, identity=semitones==0)


def _output(pdf, images, report, xml_pages, output_format, *, identity=False):
    if output_format == 'png':
        out = io.BytesIO(); images[0].save(out, format='PNG', dpi=(core.PDF_DPI, core.PDF_DPI))
        data, media, name = out.getvalue(), 'image/png', 'transposed.png'
    elif output_format == 'zip':
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('transposed.pdf', pdf)
            archive.writestr('conversion-report.json', json.dumps(report, ensure_ascii=False, indent=2))
            for i, image in enumerate(images, 1):
                png = io.BytesIO(); image.save(png, format='PNG', dpi=(core.PDF_DPI, core.PDF_DPI))
                archive.writestr(f'page-{i:03d}.png', png.getvalue())
            for i, xml in enumerate(xml_pages, 1):
                archive.writestr(f'page-{i:03d}.musicxml', xml)
        data, media, name = out.getvalue(), 'application/zip', 'geometry-score.zip'
    else:
        data, media, name = pdf, 'application/pdf', 'transposed.pdf'
    return Response(data, media_type=media, headers={
        'Content-Disposition': f'attachment; filename="{name}"', 'Cache-Control': 'no-store',
        'X-Capomatic-Mode': report['render_path'], 'X-OMR-Accuracy': 'unverified',
        'X-Capomatic-Identity': 'true' if identity else 'false',
        'X-Capomatic-Source-SHA256': report['source_sha256'],
    })
