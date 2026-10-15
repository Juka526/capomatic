"""V3 score pipeline: chord symbols, transposition, cleanup and placement (music21 only)."""
from fractions import Fraction
from pathlib import Path

import pytest
from music21 import converter, expressions, harmony, key, meter, note, stream

from backend.omr_v3 import cleanup
from backend.omr_v3.chords import (PlacedChord, align_ocr_chords, canonical, chord_symbol_from_text,
                                   chord_text, replace_chord_symbols)
from backend.omr_v3.geometry import Head, SheetGeometry, Stack, System
from backend.omr_v3.transpose import key_interval, transpose_score


def _score(fifths: int, notes: list[str], chords: list[tuple[float, str]] = (), measures: int = 1) -> stream.Score:
    part = stream.Part()
    for i in range(measures):
        m = stream.Measure(number=i + 1)
        if i == 0:
            m.insert(0, key.KeySignature(fifths))
            m.insert(0, meter.TimeSignature('4/4'))
        for j, n in enumerate(notes):
            m.insert(j, note.Note(n, quarterLength=1))
        for off, text in chords:
            m.insert(off, chord_symbol_from_text(text))
        part.append(m)
    s = stream.Score()
    s.insert(0, part)
    return s


def _roundtrip(s: stream.Score, tmp_path: Path) -> stream.Score:
    path = tmp_path / 'x.musicxml'
    s.write('musicxml', fp=str(path))
    return converter.parse(str(path))


def _chords(s):
    return [chord_text(c) for c in s.recurse().getElementsByClass(harmony.ChordSymbol)]


@pytest.mark.parametrize('text', ['Bbadd2', 'Bbm6', 'Dm7(11)', 'Gsus4', 'C7sus4', 'A7/C#', 'BbM7', 'Em/A', 'F#/A#', 'Ab6', 'BbM9'])
def test_chord_text_survives_musicxml(text, tmp_path):
    back = _roundtrip(_score(0, ['C4'] * 4, [(0, text)]), tmp_path)
    assert [canonical(t) for t in _chords(back)] == [canonical(text)]


@pytest.mark.parametrize('orig,semis,target,interval_name', [
    ('D', 2, 'E', 'M2'), ('D', -1, 'Db', 'd1'), ('F', 2, 'G', 'M2'), ('B', 1, 'C', 'm2'),
    ('C', -5, 'G', 'P4'), ('Eb', 3, 'F#', 'A2'),
])
def test_key_interval_names(orig, semis, target, interval_name):
    ivl, tgt = key_interval(orig, semis)
    assert tgt == target and ivl.semitones == semis and ivl.simpleName == interval_name


def test_key_mode_moves_notes_key_signature_and_chords(tmp_path):
    s = _score(2, ['D4', 'F#4', 'A4', 'C#5'], [(0, 'D'), (2, 'A/C#')])
    summary = transpose_score(s, 2, 'key')
    back = _roundtrip(s, tmp_path)
    assert [n.pitch.nameWithOctave for n in back.recurse().getElementsByClass(note.Note)
            if not isinstance(n, harmony.ChordSymbol)] == ['E4', 'G#4', 'B4', 'D#5']
    assert back.recurse().getElementsByClass(key.KeySignature).first().sharps == 4
    assert _chords(back) == ['E', 'B/D#']
    assert summary['keys'][0] == {'measure': 1, 'original': 'D', 'target': 'E'}


def test_key_mode_flat_target_spelling():
    s = _score(2, ['D4', 'F#4', 'A4', 'C#5'], [(0, 'D')])
    transpose_score(s, -1, 'key')
    assert [n.pitch.name for n in s.recurse().notes if isinstance(n, note.Note)] == ['D-', 'F', 'A-', 'C']
    assert s.recurse().getElementsByClass(key.KeySignature).first().sharps == -5
    assert _chords(s) == ['Db']


def test_capo_mode_changes_only_chords():
    s = _score(-1, ['F4', 'A4', 'C5', 'B-4'], [(0, 'F'), (2, 'BbM7')])
    summary = transpose_score(s, -2, 'capo')
    assert [n.pitch.nameWithOctave for n in s.recurse().notes if isinstance(n, note.Note)] == ['F4', 'A4', 'C5', 'B-4']
    assert s.recurse().getElementsByClass(key.KeySignature).first().sharps == -1
    assert [canonical(c) for c in _chords(s)] == ['Eb', 'Abmaj7']
    assert summary['capo'] == 2


def test_each_key_region_gets_its_own_spelling():
    s = _score(2, ['F#4', 'F#4', 'F#4', 'F#4'], measures=2)
    second = s.parts[0].getElementsByClass(stream.Measure)[1]
    second.insert(0, key.KeySignature(-1))
    for n in second.notes:
        n.pitch.name = 'B-'
    summary = transpose_score(s, -1, 'key')
    assert [r['target'] for r in summary['keys']] == ['Db', 'E']
    names = [n.pitch.name for n in s.recurse().notes if isinstance(n, note.Note)]
    assert names[:4] == ['F'] * 4 and names[4:] == ['A'] * 4  # not Fb-major spellings


def test_drop_rest_only_voices():
    m = stream.Measure()
    v1, v2 = stream.Voice(), stream.Voice()
    for i in range(4):
        v1.insert(i, note.Note('C4'))
    v2.insert(0, note.Rest(quarterLength=4))
    m.insert(0, v1)
    m.insert(0, v2)
    p = stream.Part([m])
    s = stream.Score([p])
    assert cleanup.drop_rest_only_voices(s) == 1
    assert len(list(s.recurse().getElementsByClass(note.Rest))) == 0


def test_clean_lyrics_drops_footer_and_primes():
    s = _score(0, ['C4', 'D4', 'E4', 'F4'])
    ns = list(s.recurse().notes)
    for n, text in zip(ns, ['주님도′', '이리', '아프', 'WELOVE']):
        n.lyric = text
    ns[2].addLyric('© 2025')
    assert cleanup.clean_lyrics(s) == 2
    assert [[ly.text for ly in n.lyrics] for n in ns] == [['주님도'], ['이리'], ['아프'], []]


def test_chord_words_become_symbols_and_marks_are_removed():
    from music21 import articulations, dynamics

    s = _score(-1, ['F4', 'G4', 'A4', 'B-4'])
    m = s.parts[0].getElementsByClass(stream.Measure).first()
    m.insert(0, expressions.TextExpression('B♭add2'))
    m.insert(1, expressions.TextExpression('Fine'))
    m.insert(0, dynamics.Dynamic('p'))
    m.notes[1].articulations = [articulations.Accent()]
    assert cleanup.chord_words_to_symbols(s) == 1
    assert _chords(s) == ['Bbadd2']
    assert cleanup.strip_marks(s) == {'dynamics': 1, 'articulations': 1}


def _geometry() -> SheetGeometry:
    # one system, staff lines at y=500..588, two 4/4 bars with 16th slots
    slots1 = [(100 + 20 * i, Fraction(i, 4)) for i in range(16)]
    slots2 = [(500 + 20 * i, Fraction(i, 4)) for i in range(16)]
    sys_ = System(500, 588, [Stack(0, 80, 480, slots1), Stack(1, 480, 880, slots2)],
                  line_ys=[500, 522, 544, 566, 588])
    return SheetGeometry(1000, 1000, 22, 28, [sys_])


def test_align_ocr_chords_to_measure_and_beat():
    items = [
        {'text': 'F', 'bbox': [86, 420, 110, 450]},          # over slot 0 of bar 1
        {'text': 'C/E', 'bbox': [246, 420, 300, 452]},       # near slot 2.0 (x=260)
        {'text': 'Bbm6', 'bbox': [666, 420, 720, 450]},      # bar 2: 16th slot 2.25 is nearer, beat 2.0 wins
        {'text': '조롱하', 'bbox': [100, 620, 160, 650]},     # lyric, not a chord
        {'text': 'G', 'bbox': [100, 100, 120, 130]},         # far above any staff
    ]
    placed = align_ocr_chords(items, _geometry())
    assert [(p.measure_index, p.offset, p.text) for p in placed[:2]] == [(0, Fraction(0), 'F'), (0, Fraction(2), 'C/E')]
    assert (placed[2].measure_index, placed[2].offset) == (1, Fraction(2))
    assert len(placed) == 3


def test_replace_chord_symbols():
    s = _score(0, ['C4'] * 4, [(0, 'Am')], measures=2)
    n = replace_chord_symbols(s, [PlacedChord(1, Fraction(2), 'G7')])
    assert n == 1 and _chords(s) == ['G7']


def test_ledger_detection_on_synthetic_page(tmp_path):
    from PIL import Image, ImageDraw

    im = Image.new('L', (400, 300), 255)
    d = ImageDraw.Draw(im)
    for y in (100, 122, 144, 166, 188):
        d.line([(0, y), (399, y)], fill=0, width=3)
    d.ellipse([100, 199, 128, 221], fill=0)           # C4 head on a ledger at y=210
    d.line([(92, 210), (136, 210)], fill=0, width=4)
    d.ellipse([200, 190, 228, 212], fill=0)           # D4 head hanging below the staff
    px = im.load()
    on_ledger = Head(100, 199, 28, 22, 5)
    hanging = Head(200, 190, 28, 22, 5)
    lines = [100, 122, 144, 166, 188]
    assert cleanup._has_ledger(px, 400, 300, on_ledger, lines)
    assert not cleanup._has_ledger(px, 400, 300, hanging, lines)
