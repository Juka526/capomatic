"""V3 reliability gate, chord-only fallback and post-transposition integrity check."""
import io
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from music21 import converter, harmony, key, meter, note, stream
from PIL import Image, ImageDraw, ImageFilter

from backend.omr_v3 import core, music_guard, quality, reliability
from backend.omr_v3.chords import chord_symbol_from_text
from backend.omr_v3.quality import ProcessingMode
from backend.omr_v3.transpose import transpose_score


def _staff_page(spacing: int, width: int = 1600, height: int = 2000) -> Image.Image:
    im = Image.new('L', (width, height), 255)
    d = ImageDraw.Draw(im)
    y = 150
    while y + 5 * spacing < height - 50:
        for i in range(5):
            d.line((80, y + i * spacing, width - 80, y + i * spacing), fill=0, width=max(1, spacing // 8))
        for x in range(200, width - 150, spacing * 4):
            d.ellipse((x, y + spacing, x + spacing * 1.3, y + spacing * 2), fill=0)
        y += spacing * 10
    return im


def test_preflight_measures_staff_spacing_and_allows_a_clear_page():
    q = quality.assess(_staff_page(20))
    assert q.mode is ProcessingMode.FULL_SCORE
    assert 19 <= q.metrics.interline_px <= 22


def test_preflight_rejects_tiny_staff_spacing():
    q = quality.assess(_staff_page(6, 700, 1000))
    assert q.mode is ProcessingMode.CHORD_ONLY and 'staff_spacing_too_small' in q.reasons


def test_preflight_uses_native_resolution_of_raster_pdfs():
    q = quality.assess(_staff_page(20), native_scale=0.4)
    assert q.metrics.effective_interline_px == pytest.approx(q.metrics.interline_px * 0.4)
    assert 'staff_spacing_too_small' in q.reasons


def test_preflight_rejects_blur_and_blank_pages():
    assert 'image_too_blurry' in quality.assess(_staff_page(20).filter(ImageFilter.GaussianBlur(6))).reasons
    assert 'no_staff_lines_found' in quality.assess(Image.new('L', (800, 1000), 255)).reasons


def _signals(**kw):
    base = dict(bars=30, bad_bars=0, geometry_aligned=True, heads=200, mean_head_grade=0.8,
                low_grade_heads=3, has_time_signature=True, notes=200)
    base.update(kw)
    return reliability.PostOmrSignals(**base)


@pytest.mark.parametrize('kw,reason', [
    ({'bad_bars': 6}, 'omr:too_many_inconsistent_bars'),
    ({'has_time_signature': False}, 'omr:no_time_signature'),
    ({'notes': 0}, 'omr:no_music_recognised'),
    ({'mean_head_grade': 0.4}, 'omr:low_note_confidence'),
])
def test_post_omr_signals_force_chord_only(kw, reason):
    good = quality.assess(_staff_page(20))
    d = reliability.decide(good, _signals(**kw))
    assert d.mode is ProcessingMode.CHORD_ONLY and d.reason == reason


def test_preflight_failure_wins_and_good_signals_allow_full_score():
    bad = quality.assess(_staff_page(6, 700, 1000))
    assert reliability.decide(bad, _signals()).reason.startswith('preflight:')
    assert reliability.decide(quality.assess(_staff_page(20)), _signals()).mode is ProcessingMode.FULL_SCORE


def _score() -> stream.Score:
    part = stream.Part()
    for i in range(2):
        m = stream.Measure(number=i + 1)
        if i == 0:
            m.insert(0, key.KeySignature(-1))
            m.insert(0, meter.TimeSignature('4/4'))
        for j, p in enumerate(['F4', 'A4', 'C5', 'B-4']):
            m.insert(j, note.Note(p, quarterLength=1))
        m.insert(0, chord_symbol_from_text('F'))
        m.insert(2, chord_symbol_from_text('BbM7'))
        part.append(m)
    s = stream.Score()
    s.insert(0, part)
    return s


def _roundtrip(s, tmp_path, name):
    p = tmp_path / name
    s.write('musicxml', fp=str(p))
    return converter.parse(str(p))


@pytest.mark.parametrize('semitones,mode', [(2, 'key'), (-1, 'key'), (-3, 'capo')])
def test_guard_passes_a_correct_transposition(semitones, mode, tmp_path):
    original = _roundtrip(_score(), tmp_path, 'a.musicxml')
    s = _score()
    summary = transpose_score(s, semitones, mode)
    report = music_guard.validate(original, _roundtrip(s, tmp_path, 'b.musicxml'), semitones, mode, summary)
    assert report.ok, report.issues
    assert report.events == (8, 8) and report.chords == (4, 4)


@pytest.mark.parametrize('damage', ['pitch', 'rhythm', 'chord', 'measure', 'key'])
def test_guard_catches_damage(damage, tmp_path):
    original = _roundtrip(_score(), tmp_path, 'a.musicxml')
    s = _score()
    summary = transpose_score(s, 2, 'key')
    m = s.parts[0].getElementsByClass(stream.Measure)[0]
    notes = [n for n in m.notes if not isinstance(n, harmony.ChordSymbol)]
    if damage == 'pitch':
        notes[0].pitch.midi += 1
    elif damage == 'rhythm':
        notes[-1].quarterLength = 0.5
    elif damage == 'chord':
        m.remove(next(iter(m.getElementsByClass(harmony.ChordSymbol))))
    elif damage == 'measure':
        s.parts[0].remove(s.parts[0].getElementsByClass(stream.Measure)[1])
    else:
        m.getElementsByClass(key.KeySignature).first().sharps = 5
    report = music_guard.validate(original, _roundtrip(s, tmp_path, 'b.musicxml'), 2, 'key', summary)
    assert not report.ok and report.issues


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _renderer(calls):
    def render(path, items, semitones):
        calls.append((Path(path).name, len(items), semitones))
        with Image.open(path) as im:
            return im.convert('RGB'), {'chords': [{'text': i['text'], 'transposed': 'X'} for i in items]}
    return render


def test_unreliable_page_returns_chord_only_without_running_omr():
    calls = []
    detector = _coverage_items
    with patch.object(core, 'run_audiveris', side_effect=AssertionError('OMR must not run')):
        result = core.process(_png(_staff_page(6, 700, 1000)), '.png', -2, 'capo',
                              chord_detector=detector, chord_only_renderer=_renderer(calls))
    assert result.mode == 'chord_only' and result.musicxml is None
    assert result.pdf.startswith(b'%PDF') and result.png.startswith(b'\x89PNG')
    assert result.report['decision']['reason'] == 'preflight:staff_spacing_too_small'
    assert len(calls) == 1 and calls[0][1] > 2 and calls[0][2] == -2


def test_chord_only_needs_chord_recognition():
    with patch.object(core, 'run_audiveris', side_effect=AssertionError('OMR must not run')):
        with pytest.raises(core.ScoreError) as exc:
            core.process(_png(_staff_page(6, 700, 1000)), '.png', 2, 'key')
    assert exc.value.status == 422


def test_chord_only_without_any_recognised_chord_is_an_error():
    calls = []
    with patch.object(core, 'run_audiveris', side_effect=AssertionError('OMR must not run')):
        with pytest.raises(core.ScoreError) as exc:
            core.process(_png(_staff_page(6, 700, 1000)), '.png', 2, 'key',
                         chord_detector=lambda path: ([], {}), chord_only_renderer=_renderer(calls))
    assert exc.value.status == 422 and 'chord_only:insufficient_chord_coverage' in str(exc.value)
    assert calls == []


def _musicxml_bytes(tmp_path) -> bytes:
    p = tmp_path / 'in.musicxml'
    _score().write('musicxml', fp=str(p))
    return p.read_bytes()


def test_integrity_failure_is_an_error_not_a_result(tmp_path):
    bad = music_guard.GuardReport()
    bad.fail('bar 1: pitch moved by an unexpected interval at 0')
    with patch.object(music_guard, 'validate', return_value=bad), \
            patch.object(core, 'render_pdf', side_effect=AssertionError('must not render')):
        with pytest.raises(core.ScoreError) as exc:
            core.process(_musicxml_bytes(tmp_path), '.musicxml', 2, 'key')
    assert exc.value.status == 500


@pytest.mark.skipif(not (shutil.which('mscore3') or shutil.which('mscore')), reason='MuseScore not installed')
def test_musicxml_fast_path_skips_gate_and_passes_integrity(tmp_path):
    with patch.object(core, 'run_audiveris', side_effect=AssertionError('OMR must not run')):
        result = core.process(_musicxml_bytes(tmp_path), '.musicxml', 2, 'key')
    assert result.mode == 'full_score' and result.report['decision']['reason'] == 'musicxml_input'
    assert result.report['integrity']['ok'] and result.pdf.startswith(b'%PDF')

@pytest.mark.parametrize('kw', [dict(low_grade_heads=40), dict(heads=0),
                                dict(geometry_aligned=False), dict(mean_head_grade=None)])
def test_consistent_bars_do_not_override_weak_head_evidence(kw):
    assert reliability.decide(None, _signals(**kw)).mode is ProcessingMode.CHORD_ONLY


@pytest.mark.parametrize('text', ['Cmaj7', 'Cm7', 'Csus4', 'Cadd2', 'Cadd11', 'C7sus4', 'Cm7b5', 'C/E'])
def test_guard_preserves_complex_chord_semantics(text, tmp_path):
    s = _score()
    m = s.parts[0].measure(1)
    for cs in list(m.getElementsByClass(harmony.ChordSymbol)):
        m.remove(cs)
    m.insert(0, chord_symbol_from_text(text))
    original = _roundtrip(s, tmp_path, 'a.musicxml')
    summary = transpose_score(s, 2)
    assert music_guard.validate(original, _roundtrip(s, tmp_path, 'b.musicxml'), 2, 'key', summary).ok


@pytest.mark.parametrize('before,after', [('Cmaj7', 'D'), ('Cm7', 'Dm9'), ('Csus4', 'D'),
                                          ('Cadd11', 'Dadd2'), ('C/E', 'D'),
                                          ('C', 'D/F#'), ('C/E', 'D/F')])
def test_guard_rejects_chord_semantic_damage(before, after, tmp_path):
    s = _score()
    m = s.parts[0].measure(1)
    for cs in list(m.getElementsByClass(harmony.ChordSymbol)):
        m.remove(cs)
    m.insert(0, chord_symbol_from_text(before))
    original = _roundtrip(s, tmp_path, 'a.musicxml')
    summary = transpose_score(s, 2)
    m.remove(m.getElementsByClass(harmony.ChordSymbol).first())
    m.insert(0, chord_symbol_from_text(after))
    assert not music_guard.validate(original, _roundtrip(s, tmp_path, 'b.musicxml'), 2, 'key', summary).ok


@pytest.mark.parametrize('damage', ['offset', 'missing_key', 'region_key'])
def test_guard_rejects_chord_offset_and_key_region_damage(damage, tmp_path):
    s = _score()
    original = _roundtrip(s, tmp_path, 'a.musicxml')
    summary = transpose_score(s, 2)
    m = s.parts[0].measure(1)
    if damage == 'offset':
        m.getElementsByClass(harmony.ChordSymbol).first().offset = 1
    elif damage == 'missing_key':
        m.remove(m.getElementsByClass(key.KeySignature).first())
    else:
        s.parts[0].measure(2).insert(0, key.KeySignature(5))
    assert not music_guard.validate(original, _roundtrip(s, tmp_path, 'b.musicxml'), 2, 'key', summary).ok


def _coverage_items(path):
    from backend.ocr.preprocess import detect_staff_systems
    with Image.open(path) as im:
        systems = detect_staff_systems(im)
        width = im.width
    return ([{'text': 'G', 'confidence': .95, 'bbox': [x, top - 35, x + 30, top - 10]}
             for top, _ in systems for x in (width * .2, width * .7)], {})


@pytest.mark.parametrize('damage', ['sparse', 'low', 'zero', 'duplicate', 'no_staff', 'nan'])
def test_chord_coverage_rejects_uncertain_output(damage, tmp_path):
    from backend.omr_v3 import chord_coverage
    image = _staff_page(20)
    path = tmp_path / 'page.png'
    image.save(path)
    items, _ = _coverage_items(path)
    if damage == 'sparse':
        items = items[:2]
    elif damage == 'low':
        for item in items:
            item['confidence'] = .5
    elif damage == 'zero':
        items = []
    elif damage == 'duplicate':
        items.append(items[0])
    elif damage == 'nan':
        items[0]['confidence'] = float('nan')
    else:
        image = Image.new('L', image.size, 255)
    assert not chord_coverage.assess(image, items)['accepted']


def test_head_export_disagreement_catches_confident_missing_notes():
    decision = reliability.decide(None, _signals(heads=100, notes=90, mean_head_grade=.96,
                                                low_grade_heads=0))
    assert decision.reason == 'omr:head_export_disagreement'
    assert reliability.decide(None, _signals(heads=100, notes=99)).mode is ProcessingMode.FULL_SCORE
