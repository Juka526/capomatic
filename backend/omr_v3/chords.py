"""Chord symbols for the score pipeline.

Audiveris reads chord names with a generic text OCR and misses many of them
(on the first test sheet it found 3 of 6 distinct chords in the first 16 bars),
so the pipeline places Capomatic's own PaddleOCR chord detections onto the
recognised measures instead. Chord text is always handled through
``backend.chords`` so V3 spells and transposes chords exactly like V1.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from backend.chords.parser import parse_chord

from .geometry import SheetGeometry

# MusicXML <kind> value for a (quality, extensions) pair. Anything else is
# written as the nearest triad with the printed suffix in kind@text, which is
# what MuseScore displays.
_KIND_BY_SUFFIX = {
    ('', ''): 'major', ('m', ''): 'minor', ('', '7'): 'dominant',
    ('maj', '7'): 'major-seventh', ('m', '7'): 'minor-seventh',
    ('', '6'): 'major-sixth', ('m', '6'): 'minor-sixth',
    ('', '9'): 'dominant-ninth', ('maj', '9'): 'major-ninth', ('m', '9'): 'minor-ninth',
    ('dim', ''): 'diminished', ('dim', '7'): 'diminished-seventh',
    ('aug', ''): 'augmented', ('sus', '4'): 'suspended-fourth', ('sus', ''): 'suspended-fourth',
    ('sus', '2'): 'suspended-second', ('m', '7b5'): 'half-diminished',
}
# Reverse map for harmonies that arrive without kind@text (Audiveris output).
_SUFFIX_BY_KIND = {
    'major': '', 'minor': 'm', 'dominant': '7', 'dominant-seventh': '7',
    'major-seventh': 'maj7', 'minor-seventh': 'm7', 'major-sixth': '6', 'minor-sixth': 'm6',
    'dominant-ninth': '9', 'major-ninth': 'maj9', 'minor-ninth': 'm9',
    'dominant-11th': '11', 'minor-11th': 'm11', 'diminished': 'dim',
    'diminished-seventh': 'dim7', 'augmented': 'aug', 'suspended-fourth': 'sus4',
    'suspended-second': 'sus2', 'half-diminished': 'm7b5', 'power': '5',
}


def _m21_name(note: str) -> str:
    return note[0] + note[1:].replace('b', '-')


def _plain_name(m21_name: str) -> str:
    return m21_name[0] + m21_name[1:].replace('-', 'b')


def display_suffix(quality: str, extensions: str) -> str:
    """Chord suffix as printed on worship lead sheets (``maj`` -> ``M``)."""
    return ('M' if quality == 'maj' else quality) + extensions


def canonical(text: str) -> str:
    """Spelling-preserving canonical form used for comparison (``BbM7`` -> ``Bbmaj7``)."""
    c = parse_chord(text)
    out = c.root + c.quality + c.extensions.replace('(', '').replace(')', '')
    return out + (f'/{c.bass}' if c.bass and c.bass != c.root else '')


def chord_symbol_from_text(text: str):
    """Build a music21 ChordSymbol that writes *text* faithfully to MusicXML."""
    from music21 import harmony

    c = parse_chord(text)
    kind = _KIND_BY_SUFFIX.get((c.quality, c.extensions))
    if kind is None:
        kind = {'m': 'minor', 'dim': 'diminished', 'aug': 'augmented',
                'sus': 'suspended-fourth'}.get(c.quality, 'major')
    kwargs = {'root': _m21_name(c.root), 'kind': kind}
    if c.bass:
        kwargs['bass'] = _m21_name(c.bass)
    cs = harmony.ChordSymbol(**kwargs)
    cs.chordKindStr = display_suffix(c.quality, c.extensions)
    cs.editorial.capomaticText = c.original
    return cs


def chord_text(cs) -> str:
    """Recover chord text from a music21 ChordSymbol read from MusicXML."""
    stored = getattr(cs.editorial, 'capomaticText', None)
    if stored:
        return stored
    root = cs.root()
    if root is None:
        raise ValueError('chord symbol without root')
    suffix = cs.chordKindStr if cs.chordKindStr not in (None, '') else _SUFFIX_BY_KIND.get(cs.chordKind, '')
    if suffix == 'M' or (suffix.startswith('M') and suffix[1:2].isdigit()):
        suffix = 'maj' + suffix[1:]
    text = _plain_name(root.name) + suffix
    bass = cs.bass()
    if bass is not None and bass.name != root.name:
        text += '/' + _plain_name(bass.name)
    return text


@dataclass(frozen=True)
class PlacedChord:
    measure_index: int  # index into the part's measure list (0-based, pickup included)
    offset: Fraction    # quarter lengths from the start of the measure
    text: str


def align_ocr_chords(items: list[dict], geometry: SheetGeometry) -> list[PlacedChord]:
    """Place OCR chord boxes (pixel coordinates of the OMR raster) on measure offsets.

    A chord belongs to the nearest staff system *below* it and to the time slot
    whose x position is closest to the chord's left edge plus half a note head
    (lead sheets left-align chord names with the note they sound on).
    """
    placed: list[PlacedChord] = []
    head = geometry.head_width
    for item in items:
        bbox = item.get('bbox')
        text = item.get('text', '')
        if not bbox or not text:
            continue
        try:
            parse_chord(text)
        except ValueError:
            continue
        x1, _, x2, y2 = (float(v) for v in bbox)
        system = geometry.system_below(y2)
        if system is None:
            continue
        x = x1 + head / 2
        stack = system.stack_at(x)
        if stack is None:
            continue
        offset = stack.offset_at(x, tolerance=head * 1.5)
        placed.append(PlacedChord(stack.index, offset, text))
    placed.sort(key=lambda p: (p.measure_index, p.offset))
    # Two detections on the same beat are one chord read twice; keep the first.
    unique: list[PlacedChord] = []
    for p in placed:
        if unique and (unique[-1].measure_index, unique[-1].offset) == (p.measure_index, p.offset):
            continue
        unique.append(p)
    return unique


def replace_chord_symbols(score, placed: list[PlacedChord]) -> int:
    """Swap the score's chord symbols for *placed* ones; return how many were inserted."""
    from music21 import harmony, stream

    part = score.parts[0]
    measures = list(part.getElementsByClass(stream.Measure))
    for m in measures:
        for cs in list(m.recurse().getElementsByClass(harmony.ChordSymbol)):
            cs.activeSite.remove(cs)
    inserted = 0
    for p in placed:
        if p.measure_index >= len(measures):
            continue
        measures[p.measure_index].insert(float(p.offset), chord_symbol_from_text(p.text))
        inserted += 1
    return inserted
