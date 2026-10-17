"""V4 may diagnose chord failures; no production integrity policy is relaxed."""

import copy
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from music21 import converter, harmony, key, note, stream
from PIL import Image

from backend.omr_v3 import music_guard
from backend.omr_v3.chords import chord_symbol_from_text, chord_text
from backend.omr_v3.transpose import transpose_score
from backend.omr_v4.integrity import classify_integrity
from backend.omr_v4.matcher import read_semantics
from backend.omr_v4.visual_graph import safe_xml
from omr_v4_fixtures import book, musicxml
from scripts.omr_v4.inspect_layout import inspect_recognized

# Exact offending harmony structure: the printed suffix disagrees with add-7/alter-0.
AUDIVERIS_HARMONY = '''<harmony><root><root-step>C</root-step></root>
<kind text="7sus4">suspended-fourth</kind><degree><degree-value>7</degree-value>
<degree-alter>0</degree-alter><degree-type>add</degree-type></degree></harmony>'''


def _source(tmp_path):
    path = musicxml(tmp_path)
    root = safe_xml(path.read_bytes(), musicxml=True)
    measure = root.find('part/measure')
    cs = ET.fromstring(AUDIVERIS_HARMONY)
    divisions = int(measure.findtext('attributes/divisions'))
    ET.SubElement(cs, 'offset').text = str(divisions * 3 // 4)
    measure.insert(1, cs)
    path.write_bytes(ET.tostring(root))
    return path


def _pair(tmp_path):
    original = converter.parse(str(_source(tmp_path)))
    after = copy.deepcopy(original)
    transpose_score(after, -2)
    path = tmp_path / 'target.musicxml'
    after.write('musicxml', fp=str(path))
    return original, converter.parse(str(path))


def _relative_pcs(chord):
    return sorted((p.pitchClass - chord.root().pitchClass) % 12 for p in chord.pitches)


def test_actual_audiveris_encoding_is_not_equivalent_to_transposed_text(tmp_path):
    before, after = _pair(tmp_path)
    a = before.recurse().getElementsByClass(harmony.ChordSymbol).first()
    b = after.recurse().getElementsByClass(harmony.ChordSymbol).first()
    assert chord_text(a) == 'C7sus4' and chord_text(b) == 'Bb7sus4'
    assert _relative_pcs(a) == [0, 5, 7, 11]
    assert _relative_pcs(b) == [0, 5, 7, 10]
    assert not music_guard.validate(before, after, -2, 'key').ok
    report = classify_integrity(before, after, -2)
    assert report['overall'] == 'warning'
    assert report['note_rhythm_key'] == 'pass' and report['chord'] == 'fail'
    assert report['chord_issues'] == ['part 1: bar 1: chord semantics changed at 3/4']
    assert report['note_rhythm_key_guard'][0]['events'] == (2, 2)
    # The classifier did not remove chords or repair either caller-owned score.
    assert len(before.recurse().getElementsByClass(harmony.ChordSymbol)) == 1
    assert not music_guard.validate(before, after, -2, 'key').ok


@pytest.mark.parametrize(
    'damage', ['pitch', 'rhythm', 'key', 'event-count', 'measure-count', 'part-count']
)
def test_nonchord_failures_remain_fatal_even_with_a_chord_failure(tmp_path, damage):
    before, after = _pair(tmp_path)
    n = after.recurse().getElementsByClass(note.Note).first()
    if damage == 'pitch':
        n.pitch.midi += 1
    elif damage == 'rhythm':
        n.quarterLength += 1
    elif damage == 'key':
        after.recurse().getElementsByClass(key.KeySignature).first().sharps += 1
    elif damage == 'event-count':
        n.activeSite.remove(n)
    elif damage == 'measure-count':
        after.parts[0].append(stream.Measure(number=2))
    else:
        after.append(stream.Part())
    report = classify_integrity(before, after, -2)
    assert report['overall'] == 'fail' and report['fatal_issues']
    assert report['note_rhythm_key'] == 'fail'


@pytest.mark.parametrize(
    'issue', ['unreadable chord or score semantics', 'new unknown chord issue']
)
def test_unknown_or_unreadable_full_guard_failure_remains_fatal(tmp_path, monkeypatch, issue):
    before, after = _pair(tmp_path)
    real_validate = music_guard.validate

    def validate(a, b, *args):
        if a.recurse().getElementsByClass(harmony.ChordSymbol):
            return music_guard.GuardReport(ok=False, issues=[issue])
        return real_validate(a, b, *args)

    monkeypatch.setattr(music_guard, 'validate', validate)
    result = classify_integrity(before, after, -2)
    assert result['overall'] == 'fail'
    assert result['note_rhythm_key'] == 'pass'
    assert result['fatal_issues'] == ['part 1: ' + issue]


def test_independent_guard_catches_pitch_failure_hidden_by_issue_cap(tmp_path):
    before, after = _pair(tmp_path)
    a, b = before.parts[0].measure(1), after.parts[0].measure(1)
    template = a.recurse().getElementsByClass(harmony.ChordSymbol).first()
    # More than 20 known chord failures occur before a damaged note in a later bar.
    for i in range(21):
        a.insert(Fraction(i, 32), copy.deepcopy(template))
        b.insert(Fraction(i, 32), chord_symbol_from_text('Bb7sus4'))
    for score, pitch in ((before, 'C4'), (after, 'B3')):
        m = stream.Measure(number=2)
        m.append(note.Note(pitch))
        score.parts[0].append(m)
    full = music_guard.validate(before, after, -2, 'key')
    assert len(full.issues) == 20 and all('chord' in issue for issue in full.issues)
    result = classify_integrity(before, after, -2)
    assert result['overall'] == 'fail' and result['note_rhythm_key'] == 'fail'
    assert any('bar 2: pitch moved' in issue for issue in result['fatal_issues'])


def test_warning_cli_writes_all_evidence_and_deterministic_json(tmp_path):
    source = _source(tmp_path)
    raster = tmp_path / 'raster.png'
    Image.new('L', (400, 300), 255).save(raster)
    omr = book(tmp_path)
    for name in ('first', 'second'):
        out = tmp_path / name
        summary = inspect_recognized(raster, omr, source, -2, out)
        assert summary['semantic_integrity']['overall'] == 'warning'
        assert summary['semantic_integrity']['note_rhythm_key'] == 'pass'
        assert summary['matched_count'] == 2
        report = json.loads((out / 'semantic-report.json').read_text())
        assert not report['integrity'][0]['ok']
        assert report['semantic_integrity']['chord'] == 'fail'
        plan = json.loads((out / 'plan.json').read_text())
        assert any('Chord integrity warning' in b for b in plan['blockers'])
        with Image.open(out / 'diagnostic-overlay.png') as image:
            assert image.getpixel((402, 40)) == (255, 240, 194)
    for filename in ('plan.json', 'graph-summary.json', 'semantic-report.json'):
        assert (tmp_path / 'first' / filename).read_bytes() == (
            tmp_path / 'second' / filename
        ).read_bytes()
    # Harmony labels/degrees have no influence on pitched-event extraction.
    root = safe_xml(source.read_bytes(), musicxml=True)
    root.find('part/measure').remove(root.find('part/measure/harmony'))
    plain = tmp_path / 'without-harmony.musicxml'
    plain.write_bytes(ET.tostring(root))
    assert read_semantics(source) == read_semantics(plain)


@pytest.mark.parametrize('damage', ['pitch', 'rhythm', 'key'])
def test_fatal_cli_never_transfers_ownership_and_writes_failure_report(
    tmp_path, monkeypatch, damage
):
    from backend.omr_v3 import transpose
    from scripts.omr_v4 import inspect_layout

    real_transpose = transpose.transpose_score

    def broken(score, *args):
        result = real_transpose(score, *args)
        n = score.recurse().getElementsByClass(note.Note).first()
        if damage == 'pitch':
            n.pitch.midi += 1
        elif damage == 'rhythm':
            n.quarterLength += 1
        else:
            score.recurse().getElementsByClass(key.KeySignature).first().sharps += 1
        return result

    def forbidden(*args):
        pytest.fail('Fatal integrity failure reached repaired ownership transfer')

    monkeypatch.setattr(transpose, 'transpose_score', broken)
    monkeypatch.setattr(inspect_layout, 'match_with_provenance', forbidden)
    raster = tmp_path / 'raster.png'
    Image.new('L', (400, 300), 255).save(raster)
    out = tmp_path / 'out'
    with pytest.raises(ValueError, match='semantic integrity failed'):
        inspect_recognized(raster, book(tmp_path), _source(tmp_path), -2, out)
    assert (
        json.loads((out / 'semantic-report.json').read_text())['semantic_integrity']['overall']
        == 'fail'
    )
    assert not (out / 'plan.json').exists()
    assert not (out / 'diagnostic-overlay.png').exists()


def test_v3_guard_bytes_match_frozen_baseline():
    guard = Path(music_guard.__file__)
    assert hashlib.sha256(guard.read_bytes()).hexdigest() == (
        '9f27db149414fe38991b86230f4c15fae90c2ecd1bb5205ecfd56892fa992b43'
    )
