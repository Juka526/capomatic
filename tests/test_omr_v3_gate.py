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
    detector = lambda path: ([{'text': 'G', 'confidence': 0.9, 'bbox': [10, 10, 30, 30]}], {})
    with patch.object(core, 'run_audiveris', side_effect=AssertionError('OMR must not run')):
        result = core.process(_png(_staff_page(6, 700, 1000)), '.png', -2, 'capo',
                              chord_detector=detector, chord_only_renderer=_renderer(calls))
    assert result.mode == 'chord_only' and result.musicxml is None
    assert result.pdf.startswith(b'%PDF') and result.png.startswith(b'\x89PNG')
    assert result.report['decision']['reason'] == 'preflight:staff_spacing_too_small'
    assert calls == [('page.png', 1, -2)]


def test_chord_only_needs_chord_recognition():
    with patch.object(core, 'run_audiveris', side_effect=AssertionError('OMR must not run')):
        with pytest.raises(core.ScoreError) as exc:
            core.process(_png(_staff_page(6, 700, 1000)), '.png', 2, 'key')
    assert exc.value.status == 422


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
