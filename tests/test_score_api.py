"""Score sessions must reuse recognition, preserve gates, and isolate callers."""
import copy
import io
import json
import time
import zipfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from music21 import converter, harmony, key, meter, note, stream

from backend.api import score as score_api
from backend.api.main import app, _cache_put, _cache_get, _detection_cache
from backend.omr_v3 import core, music_guard, router as v3
from backend.omr_v3.transpose import transpose_score


def xml_score():
    measure = stream.Measure(number=1)
    measure.append(key.KeySignature(-1))
    measure.append(meter.TimeSignature('4/4'))
    n = note.Note('F4', quarterLength=4)
    n.addLyric('주님')
    measure.insert(0, n)
    measure.insert(0, harmony.ChordSymbol('C7'))
    return stream.Score([stream.Part([measure])]).write('musicxml').read_bytes()


@pytest.fixture
def session(monkeypatch):
    monkeypatch.setenv('CAPOMATIC_OMR_REQUIRE_AUTH', '0')
    monkeypatch.setenv('CAPOMATIC_ENABLE_SCORE_API', '1')
    monkeypatch.setenv('CAPOMATIC_OMR_RATE_LIMIT', '100/3600')
    _detection_cache.clear(); v3.rate_limiter.reset()
    yield TestClient(app, raise_server_exceptions=False)
    _detection_cache.clear(); v3.rate_limiter.reset()


def test_detect_then_render_reuses_xml_without_musescore(session, monkeypatch):
    xml = xml_score()
    detect = Mock(return_value=core.Result(b'', None, xml, {}, {
        'decision': {'mode': 'full_score'}, 'input': {'source': 'musicxml'}}))
    monkeypatch.setattr(score_api, 'recognize', detect)
    render = Mock(return_value=core.Result(b'', xml, xml, {}, {}))
    monkeypatch.setattr(core, 'process', render)
    response = session.post('/detect', files={'image': ('test.musicxml', xml)})
    assert response.status_code == 200
    data = response.json()
    assert data['semantic_ready'] and not data['render_ready']
    assert data['pages'][0]['lyric_entries'] == 1
    for shift in [1, -1]:
        r = session.post('/render', data={'detection_id': data['detection_id'],
                         'semitones': shift, 'output_format': 'musicxml'})
        assert r.status_code == 200 and r.content == xml
        assert r.headers['x-capomatic-mode'] == 'editable_semantics'
        assert 'No source layout' in r.headers['x-capomatic-preservation']
    assert detect.call_count == 1
    assert all(call.kwargs['musicxml_only'] for call in render.call_args_list)
    assert [c.args for c in render.call_args_list] == [
        (xml, '.musicxml', 1, 'key'), (xml, '.musicxml', -1, 'key')]


def test_unreliable_recognition_never_becomes_successful_full_score(session, monkeypatch):
    recognized = core.Result(b'', None, xml_score(), {}, {'decision': {
        'mode': 'chord_only', 'reason': 'omr:too_many_inconsistent_bars'}}, mode='chord_only')
    monkeypatch.setattr(score_api, 'recognize', lambda *a: recognized)
    render = Mock(); monkeypatch.setattr(core, 'process', render)
    d = session.post('/detect', files={'image': ('test.pdf', b'%PDF-test')}).json()
    assert not d['can_render_full_score']
    r = session.post('/render', data={'detection_id': d['detection_id'], 'semitones': 1})
    assert r.status_code == 422
    assert 'not ready' in r.json()['detail']['message']
    render.assert_not_called()


def test_score_sessions_require_authentication_by_default(session, monkeypatch):
    monkeypatch.delenv('CAPOMATIC_OMR_REQUIRE_AUTH')
    recognize = Mock(); monkeypatch.setattr(score_api, 'recognize', recognize)
    assert session.post('/detect', files={'image': ('test.pdf', b'%PDF-test')}).status_code == 401
    recognize.assert_not_called()


def test_other_caller_cannot_render_cached_score(session):
    _cache_put('private', {'score': core.Result(b'', None, xml_score(), {}, {}), 'owner': 'another-owner'})
    assert session.post('/render', data={'detection_id': 'private'}).status_code == 404


def test_expired_or_oversized_score_does_not_stay_in_cache():
    _detection_cache.clear()
    _cache_put('expired', {'expires_at': time.monotonic() - 1})
    assert _cache_get('expired') is None
    _cache_put('huge', {'score_bytes': 33 * 1024 * 1024})
    assert _cache_get('huge') is None


def test_partial_document_rejects_full_pdf(session, monkeypatch):
    good = core.Result(b'', None, xml_score(), {}, {})
    result = core.Result(b'', None, None, {}, {'document': {'failed_pages': 1}},
                         mode='partial_failure', pages=(good, None))
    monkeypatch.setattr(score_api, 'recognize', lambda *a: result)
    d = session.post('/detect', files={'image': ('test.pdf', b'%PDF-test')}).json()
    assert d['page_count'] == 2 and not d['can_render_full_score']
    assert session.post('/render', data={'detection_id': d['detection_id']}).status_code == 422


@pytest.mark.parametrize('kind,mods', [('dominant-seventh', []), ('suspended-fourth', [('add', 7, -1)])])
@pytest.mark.parametrize('shift', [-1, 1, 2])
def test_imported_chord_semantics_survive_transposition_and_serialization(kind, mods, shift, tmp_path):
    s = converter.parseData(xml_score().decode(), format='musicxml')
    m = s.parts[0].getElementsByClass(stream.Measure).first()
    for c in list(m.getElementsByClass(harmony.ChordSymbol)):m.remove(c)
    c = harmony.ChordSymbol(root='C', bass='G', kind=kind)
    c.chordKindStr = '7' if kind == 'dominant-seventh' else '7sus4'
    for typ, degree, alter in mods:
        c.addChordStepModification(harmony.ChordStepModification(typ, degree, alter))
    m.insert(0, c)
    t = copy.deepcopy(s); summary = transpose_score(t, shift, 'key')
    tc = t.recurse().getElementsByClass(harmony.ChordSymbol).first()
    assert tc.chordKind == kind
    assert [(d.modType, d.degree, d.interval.chromatic.semitones) for d in tc.getChordStepModifications()] == mods
    assert (tc.root().pitchClass - c.root().pitchClass) % 12 == shift % 12
    assert (tc.bass().pitchClass - c.bass().pitchClass) % 12 == shift % 12
    assert music_guard.validate(s, t, shift, 'key', summary).ok
    a, b = tmp_path/'source.musicxml', tmp_path/'target.musicxml'
    s.write('musicxml', fp=str(a));t.write('musicxml', fp=str(b))
    assert music_guard.validate(converter.parse(str(a)), converter.parse(str(b)), shift, 'key', summary).ok


def test_recognition_only_xml_does_not_transpose_or_render(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Detection must not transpose or render')
    monkeypatch.setattr(core, 'transpose_score', forbidden)
    monkeypatch.setattr(core, 'render_pdf', forbidden)
    result = core.process(xml_score(), '.musicxml', 0, recognition_only=True)
    assert result.recognized_musicxml and not result.pdf and result.musicxml is None


@pytest.mark.parametrize('output_format', ['pdf', 'png', 'zip'])
@pytest.mark.parametrize('shift', [0, 1, -1])
def test_raster_export_never_falls_back_to_reflow(session, monkeypatch, output_format, shift):
    recognized = core.Result(b'', None, xml_score(), {}, {})
    monkeypatch.setattr(score_api, 'recognize', lambda *a: recognized)
    reflow = Mock(); monkeypatch.setattr(core, 'process', reflow)
    d = session.post('/detect', files={'image': ('test.pdf', b'%PDF-test')}).json()
    r = session.post('/render', data={'detection_id': d['detection_id'],
                       'output_format': output_format, 'semitones': shift})
    assert r.status_code == 422
    report = r.json()['detail']['report']
    assert report['render_request'] == {'semitones': shift}
    assert not report['render_ready'] and not report['lyric_layer_ready']
    assert all(not p['source_ink_safety']['edit_authorized'] for p in report['pages'])
    reflow.assert_not_called()


def test_worker_failure_is_isolated_and_receives_no_api_credentials(monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'must-not-leak')
    def failed(argv, timeout, home, what):
        assert 'must-not-leak' not in str(argv)
        assert 'backend.ocr.score_worker' in argv
        raise core.ScoreError('Chord OCR failed', 422)
    monkeypatch.setattr(core, '_run', failed)
    with pytest.raises(core.ScoreError, match='Chord OCR failed'):
        score_api.isolated_chords('/tmp/input.png')


def test_sharp_key_slash_bass_has_no_double_accidental_after_roundtrip(tmp_path):
    s = converter.parseData(xml_score().decode(), format='musicxml')
    m = s.parts[0].getElementsByClass(stream.Measure).first()
    for cs in list(m.getElementsByClass(harmony.ChordSymbol)):m.remove(cs)
    m.insert(0, harmony.ChordSymbol('A7/C#'))
    t = copy.deepcopy(s); summary = transpose_score(t, 1, 'key')
    path = tmp_path/'target.musicxml'; t.write('musicxml', fp=str(path))
    parsed = converter.parse(str(path))
    cs = parsed.recurse().getElementsByClass(harmony.ChordSymbol).first()
    assert cs.root().name == 'A#' and cs.bass().name == 'D'
    assert music_guard.validate(s, parsed, 1, 'key', summary).ok


def test_reviewed_xml_retains_lyrics_dynamics_and_articulations(monkeypatch):
    from music21 import articulations, dynamics
    s = converter.parseData(xml_score().decode(), format='musicxml')
    m = s.parts[0].getElementsByClass(stream.Measure).first()
    m.insert(0, dynamics.Dynamic('p'))
    n = next(n for n in m.notes if isinstance(n, note.Note))
    n.lyric = 'WELOVE'; n.articulations = [articulations.Accent()]
    path = s.write('musicxml')
    def fake_pdf(xml, pdf, *args):pdf.write_bytes(b'%PDF-1.4\n')
    monkeypatch.setattr(core, 'render_pdf', fake_pdf)
    r = core.process(path.read_bytes(), '.musicxml', 1, preserve_notation=True)
    parsed = converter.parseData(r.musicxml.decode(), format='musicxml')
    assert parsed.recurse().getElementsByClass(dynamics.Dynamic).first().value == 'p'
    actual = next(n for n in parsed.recurse().notes if isinstance(n, note.Note))
    assert actual.lyric == 'WELOVE' and isinstance(actual.articulations[0], articulations.Accent)


def test_multi_page_recognition_does_not_call_pdf_combiner(monkeypatch):
    page = core.Result(b'', None, xml_score(), {}, {'decision': {'mode': 'full_score'}})
    monkeypatch.setattr(core, '_pdf_pages', lambda *a: 2)
    def tool(argv, timeout, home, what):
        assert Path(argv[0]).name == 'pdfseparate'
        for number in [1, 2]:(home/f'input-{number}.pdf').write_bytes(b'%PDF-test')
    monkeypatch.setattr(core, '_run', tool)
    monkeypatch.setattr(core, '_process_page', lambda *a, **kw: page)
    result = core.process(b'%PDF-test', '.pdf', 0, recognition_only=True)
    assert len(result.pages) == 2 and not result.pdf


def test_pdf_recognizer_override_does_not_reuse_default_engine(monkeypatch):
    import sys
    from types import SimpleNamespace
    from backend.ocr import paddle_ocr
    calls = []
    def factory(**kwargs):
        calls.append(kwargs)
        return object()
    monkeypatch.setitem(sys.modules, 'paddleocr', SimpleNamespace(PaddleOCR=factory))
    monkeypatch.setattr(paddle_ocr, '_ocr_instances', {})
    monkeypatch.delenv('CHORDTAYLOR_OCR_REC_MODEL', raising=False)
    default = paddle_ocr.get_ocr('mobile')
    monkeypatch.setenv('CHORDTAYLOR_OCR_REC_MODEL', 'en_PP-OCRv5_mobile_rec')
    explicit = paddle_ocr.get_ocr('mobile')
    assert default is not explicit
    assert 'text_recognition_model_name' not in calls[0]
    assert calls[1]['text_recognition_model_name'] == 'en_PP-OCRv5_mobile_rec'


def test_worker_json_preserves_numpy_coordinate_numbers():
    import numpy as np
    from backend.ocr.score_worker import json_scalar
    encoded = json.dumps({'bbox': [np.int64(12)], 'confidence': np.float32(0.9)}, default=json_scalar)
    decoded = json.loads(encoded)
    assert decoded['bbox'] == [12] and isinstance(decoded['bbox'][0], int)
    assert abs(decoded['confidence'] - 0.9) < 1e-6


def test_pdf_filename_title_is_metadata_not_source_verification(monkeypatch):
    monkeypatch.setattr(core, 'process', lambda *a, **kw: core.Result(b'', None, xml_score(), {}, {}))
    result = score_api.recognize(b'%PDF-test', '1 주님 난 알고 싶어요_1758826856.pdf', None)
    assert result.report['display_title'] == '주님 난 알고 싶어요'
    assert result.report['display_title_basis'].startswith('user_supplied_filename')
    assert not score_api.summary(result)['source_completeness'] == 'verified'


def test_failed_detection_id_keeps_owner_bound_diagnostics(session, monkeypatch):
    from PIL import Image
    image = io.BytesIO(); Image.new('RGB', (20, 20), 'white').save(image, format='PNG')
    def reject(*args, **kwargs):
        raise core.ScoreError('Unverified source coordinate transform')
    monkeypatch.setattr(core, 'process', reject)
    response = session.post('/detect', files={'image': ('score.png', image.getvalue())},
                            data={'processing': 'score'})
    assert response.status_code == 422
    detail = response.json()['detail']
    assert not detail['report']['render_ready']
    ident = detail['detection_id']
    cached = _cache_get(ident)
    assert cached['score'].source_layout.source == image.getvalue()
    for shift in [0, 1, -1]:
        render = session.post('/render', data={'detection_id': ident, 'semitones': shift})
        assert render.status_code == 422
        assert 'Unverified source coordinate' in str(render.json())
    cached['owner'] = 'different-owner'
    assert session.post('/render', data={'detection_id': ident}).status_code == 404


def test_source_bundle_bytes_cannot_bypass_cache_budget(session, monkeypatch):
    from backend.omr_v3.source_layout import SourceLayoutBundle
    source = SourceLayoutBundle(b'x' * (33 * 1024 * 1024), '.pdf', (None,))
    recognized = core.Result(b'', None, None, {}, source_layout=source)
    monkeypatch.setattr(score_api, 'recognize', lambda *a: recognized)
    response = session.post('/detect', files={'image': ('test.pdf', b'%PDF-test')})
    assert response.status_code == 413
    assert not _detection_cache
