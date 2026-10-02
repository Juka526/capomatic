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

# Letter names in order, and the pitch class of each natural letter.
_LETTERS = "CDEFGAB"
_NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_FORBIDDEN_OUT = {"E#", "B#", "Cb", "Fb"}

# Standard key names for each chromatic index.
# Uses flats for enharmonic pairs (Db not C#, Eb not D#, etc.) except F# which
# is more standard than Gb.  Used by compute_target_key() and key_detect.
_KEY_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


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


def _letter_shift(original_key: str, target_key: str) -> int:
    """How many letter names the key moves (e.g. D -> C is 6, i.e. one letter down)."""
    return (_LETTERS.index(target_key[0].upper()) - _LETTERS.index(original_key[0].upper())) % 7


def _spell_by_letter(note: str, semitones: int, letter_shift: int) -> Optional[str]:
    """Transpose keeping the note's letter relation to the key.

    The letter moves by *letter_shift*; the accidental is whatever reaches the
    transposed pitch. Returns None when that needs a double accidental or a
    forbidden spelling (E#, B#, Cb, Fb), so the caller can fall back.
    """
    letter = _LETTERS[(_LETTERS.index(note[0]) + letter_shift) % 7]
    pitch = (_note_to_index(note) + semitones) % 12
    accidental = {0: "", 1: "#", 11: "b"}.get((pitch - _NATURAL[letter]) % 12)
    if accidental is None or letter + accidental in _FORBIDDEN_OUT:
        return None
    return letter + accidental


def compute_target_key(original_key: str, semitones: int) -> str:
    """Compute the target key by transposing *original_key* by *semitones*.

    Returns the most standard key name for the resulting chromatic position
    (e.g. "Db" not "C#", but "F#" not "Gb").

    Raises ValueError if *original_key* is not a recognised note name.
    """
    idx = _note_to_index(original_key)
    return _KEY_NAMES[(idx + semitones) % 12]


def transpose_chord(
    chord: Chord,
    semitones: int,
    target_key: Optional[str] = None,
    original_key: Optional[str] = None,
) -> str:
    """Transpose *chord* by *semitones* and return a compact chord string.

    With both keys known, notes keep their letter relation to the key (as
    notation software does): a borrowed Bb in D becomes Ab in C, not G#, and
    A/C# in D becomes G/B in C. Spellings that would need a double accidental
    or E#/B#/Cb/Fb fall back to the target key's sharp/flat preference. With
    either key unknown, only that preference is used.

    Both the root and slash bass are transposed independently.
    Extensions are written compactly (e.g. "7sus4" not "7(sus4)"), except an
    extension starting with an accidental directly after the root, which
    stays wrapped so "A(b5)" is not read as an A-flat chord.
    """
    prefer = _key_preference(target_key)
    shift = _letter_shift(original_key, target_key) if original_key and target_key else None

    def spell(note: str) -> str:
        spelled = _spell_by_letter(note, semitones, shift) if shift is not None else None
        return spelled or transpose_note(note, semitones, prefer)

    new_root = spell(chord.root)
    suffix = chord.quality + chord.extensions
    if not chord.quality and chord.extensions[:1] in ("b", "#"):
        suffix = f"({chord.extensions})"
    result = new_root + suffix
    if chord.bass is not None:
        result += "/" + spell(chord.bass)
    return result