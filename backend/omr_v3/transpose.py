"""Key change and capo transposition of a recognised score.

* ``key`` mode moves notes, key signatures and chord symbols together; the song
  really sounds higher or lower.
* ``capo`` mode keeps every note and key signature and rewrites only the chord
  symbols to the shapes a guitarist plays with a capo on fret N, i.e. the same
  ``semitones = -N`` convention the V1 overlay and frontend use.

Spelling: each key-signature region gets its own diatonic interval, from its
major key to the standard name ``compute_target_key`` picks (Db not C#, F# not
Gb). A D->Db shift is therefore spelled as a descending augmented unison and
F# becomes F, not E#. Chord symbols go through V1's ``transpose_chord`` with the
same region keys, so chords and notes always agree.
"""
from __future__ import annotations

from typing import Literal

from backend.chords.parser import parse_chord
from backend.chords.transpose import compute_target_key, transpose_chord

from .chords import chord_symbol_from_text, chord_text

Mode = Literal['key', 'capo']
CAPO_MAX = 7
_MAJOR_BY_FIFTHS = {-7: 'Cb', -6: 'Gb', -5: 'Db', -4: 'Ab', -3: 'Eb', -2: 'Bb', -1: 'F', 0: 'C',
                    1: 'G', 2: 'D', 3: 'A', 4: 'E', 5: 'B', 6: 'F#', 7: 'C#'}
_ENHARMONIC_KEY = {'Cb': 'B', 'C#': 'Db'}  # keys V1's key table does not use


def _region_key(fifths: int) -> str:
    name = _MAJOR_BY_FIFTHS[max(-7, min(7, fifths))]
    return _ENHARMONIC_KEY.get(name, name)


def key_interval(original_key: str, semitones: int):
    """Diatonic interval from *original_key* to its standard transposed key."""
    from music21 import interval, pitch

    target = compute_target_key(original_key, semitones)
    start = pitch.Pitch(original_key.replace('b', '-') + '4')
    end = pitch.Pitch(target.replace('b', '-') + '4')
    while end.midi - start.midi > semitones:
        end.octave -= 1
    while end.midi - start.midi < semitones:
        end.octave += 1
    return interval.Interval(pitchStart=start, pitchEnd=end), target


def validate_request(mode: str, semitones: int) -> None:
    if mode not in ('key', 'capo'):
        raise ValueError("mode must be 'key' or 'capo'")
    if mode == 'key' and not -11 <= semitones <= 11:
        raise ValueError('semitones must be -11..11')
    if mode == 'capo' and not -CAPO_MAX <= semitones <= 0:
        raise ValueError(f'capo mode needs semitones -{CAPO_MAX}..0 (capo N = -N)')


def transpose_score(score, semitones: int, mode: Mode = 'key') -> dict:
    """Transpose *score* in place. Returns a summary for the conversion report."""
    from music21 import harmony, key, note, stream

    validate_request(mode, semitones)
    part_keys: list[dict] = []
    unparsed: list[str] = []
    for part in score.parts:
        fifths = 0
        regions: list[dict] = []
        for m in part.getElementsByClass(stream.Measure):
            for ks in m.getElementsByClass(key.KeySignature):
                fifths = ks.sharps
            original = _region_key(fifths)
            ivl, target = key_interval(original, semitones)
            if not regions or regions[-1]['original'] != original:
                regions.append({'measure': m.number, 'original': original,
                                'target': target if mode == 'key' else original})
            if mode == 'key':
                for ks in m.getElementsByClass(key.KeySignature):
                    ks.transpose(ivl, inPlace=True)
                for n in m.recurse().notes:
                    if isinstance(n, harmony.ChordSymbol):
                        continue
                    if isinstance(n, note.Note) or n.isChord:
                        n.transpose(ivl, inPlace=True)
            for cs in list(m.recurse().getElementsByClass(harmony.ChordSymbol)):
                try:
                    text = chord_text(cs)
                    new = transpose_chord(parse_chord(text), semitones,
                                          target_key=target, original_key=original)
                except ValueError:
                    unparsed.append(str(cs.figure))
                    continue
                site, offset = cs.activeSite, cs.offset
                site.remove(cs)
                site.insert(offset, chord_symbol_from_text(new))
        part_keys.append({'regions': regions})
    return {'mode': mode, 'semitones': semitones,
            'capo': -semitones if mode == 'capo' else None,
            'keys': part_keys[0]['regions'] if part_keys else [],
            'untransposed_chords': unparsed}
