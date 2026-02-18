from typing import Optional
from .types import Chord

# Chromatic scale — two spellings for the same 12 positions.
_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_FLAT  = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

# Forbidden spellings that must never appear in output -> their enharmonic equivalents.
# Used only for normalising *input* notes before index lookup.
_ENHARMONIC_IN = {"E#": "F", "B#": "C", "Cb": "B", "Fb": "E"}

# Keys that prefer flat spelling in output.
_FLAT_KEYS = {"F", "Bb", "Eb", "Ab", "Db"}


def _note_to_index(note: str) -> int:
    """Return chromatic index 0-11 for a note name."""
    note = _ENHARMONIC_IN.get(note, note)
    if note in _SHARP:
        return _SHARP.index(note)
    if note in _FLAT:
        return _FLAT.index(note)
    raise ValueError(f"Unknown note: {note!r}")


def transpose_note(note: str, semitones: int, prefer: str = "sharp") -> str:
    """Transpose a single note name by *semitones* (positive = up, negative = down).

    *prefer* must be "sharp" or "flat" and controls enharmonic spelling.
    Forbidden outputs (E#, B#, Cb, Fb) cannot arise because the chromatic
    scale arrays do not contain them.
    """
    idx = (_note_to_index(note) + semitones) % 12
    return _FLAT[idx] if prefer == "flat" else _SHARP[idx]


def _key_preference(target_key: Optional[str]) -> str:
    """Return "flat" or "sharp" preference for a given target key."""
    if target_key is None:
        return "sharp"
    # Gb is treated as F# (sharp-preferred); all other flat keys use flat.
    return "flat" if target_key in _FLAT_KEYS else "sharp"


def transpose_chord(
    chord: Chord,
    semitones: int,
    target_key: Optional[str] = None,
) -> str:
    """Transpose *chord* by *semitones* and return a compact chord string.

    Both the root and slash bass are transposed independently.
    Parentheses are never included in the output; extensions are written
    compactly (e.g. "7sus4" not "7(sus4)").
    """
    prefer = _key_preference(target_key)
    new_root = transpose_note(chord.root, semitones, prefer)
    result = new_root + chord.quality + chord.extensions
    if chord.bass is not None:
        result += "/" + transpose_note(chord.bass, semitones, prefer)
    return result