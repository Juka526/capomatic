"""Key detection from chord progressions.

Infers the most likely major key of a song from its detected chord symbols
using a Krumhansl-inspired diatonic scoring algorithm.  Each of the 12
candidate keys is scored by how well the detected chord roots fit its
diatonic scale, weighted by functional importance (tonic > dominant/
subdominant > other diatonic degrees).

Minor keys share diatonic notes with their relative major, so a song in
Am will be detected as C major.  This is acceptable because the enharmonic
spelling preference is identical for relative major/minor pairs.
"""
from __future__ import annotations

from collections import Counter

from backend.chords.parser import parse_chord
from backend.chords.transpose import _KEY_NAMES, _note_to_index

# Diatonic scale degree intervals (semitones from root) for a major key.
_DIATONIC_INTERVALS = [0, 2, 4, 5, 7, 9, 11]

# Functional weight for each scale degree: I, ii, iii, IV, V, vi, vii°.
# Tonic (I) is weighted highest; dominant (V) and subdominant (IV) next.
_DEGREE_WEIGHTS = [4, 2, 1, 3, 3, 2, 1]


def infer_key(chords: list[dict]) -> str | None:
    """Infer the original key of a song from its detected chord symbols.

    Parameters
    ----------
    chords : list of dicts with at least a ``"text"`` key containing a chord
        symbol string (e.g. ``"Am7"``, ``"D/F#"``).  Items that cannot be
        parsed are silently skipped.

    Returns
    -------
    str or None
        The most likely major key name (e.g. ``"F"``, ``"A"``, ``"Bb"``),
        or ``None`` if no chord roots could be extracted.
    """
    # Collect root note indices with their occurrence counts.
    root_counts: Counter[int] = Counter()
    for chord_dict in chords:
        try:
            chord = parse_chord(chord_dict["text"])
            root_counts[_note_to_index(chord.root)] += 1
        except (ValueError, KeyError):
            continue  # unparseable or missing "text" key

    if not root_counts:
        return None

    # Score each candidate key.
    best_key_idx = 0
    best_score = -1
    best_tonic_count = -1

    for key_idx in range(12):
        score = 0
        for degree, weight in zip(_DIATONIC_INTERVALS, _DEGREE_WEIGHTS):
            note_idx = (key_idx + degree) % 12
            score += weight * root_counts.get(note_idx, 0)

        tonic_count = root_counts.get(key_idx, 0)

        # Tie-break: prefer higher tonic frequency, then lower _KEY_NAMES index.
        if (score > best_score
                or (score == best_score and tonic_count > best_tonic_count)):
            best_score = score
            best_tonic_count = tonic_count
            best_key_idx = key_idx

    return _KEY_NAMES[best_key_idx]
