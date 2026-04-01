"""Key detection from chord progressions.

Infers the most likely key of a song from its detected chord symbols using the
Krumhansl-Kessler profile matching algorithm (standard MIR approach).

Each chord is expanded to all implied pitch classes (root + quality intervals),
building a pitch-class histogram across the whole song.  That histogram is then
correlated (Pearson) against the KK major and minor profiles rotated to each of
the 12 tonic positions.  The tonic + mode with the highest correlation wins.

Minor keys are returned as their relative major so that enharmonic spelling
downstream (compute_target_key / transpose) stays consistent — e.g. a song in
Am is returned as "C".  This is the same behaviour as before.
"""
from __future__ import annotations

from collections import Counter

from backend.chords.parser import parse_chord
from backend.chords.transpose import _KEY_NAMES, _note_to_index

# ---------------------------------------------------------------------------
# Krumhansl-Kessler tonal hierarchy profiles
# Index 0 = tonic (C), rotated per candidate key.
# ---------------------------------------------------------------------------
_KK_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
             2.52, 5.19, 2.39, 3.66, 2.29, 2.88]

_KK_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
             2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

# ---------------------------------------------------------------------------
# Pitch-class intervals for each chord quality above the root.
# ---------------------------------------------------------------------------
_QUALITY_INTERVALS: dict[str, list[int]] = {
    "":    [0, 4, 7],        # major triad
    "m":   [0, 3, 7],        # minor triad
    "maj": [0, 4, 7, 11],    # major 7
    "dim": [0, 3, 6],        # diminished triad
    "aug": [0, 4, 8],        # augmented triad
    "sus": [0, 5, 7],        # sus4
}

# Extension tokens that add extra pitch classes.
_EXTENSION_MAP: dict[str, int] = {
    "7":   10,   # dominant 7 (minor 7th)
    "maj7": 11,  # major 7th (already in "maj" but harmless to add)
    "9":   2,    # major 9th
    "11":  5,    # perfect 11th
    "6":   9,    # major 6th
}


def _chord_to_pitch_classes(root_idx: int, quality: str, extensions: str) -> list[int]:
    """Return chromatic indices (0-11) for all notes implied by this chord."""
    intervals = list(_QUALITY_INTERVALS.get(quality, [0, 4, 7]))

    # Add extension intervals.
    for token, interval in _EXTENSION_MAP.items():
        if token in extensions:
            if interval not in intervals:
                intervals.append(interval)

    return [(root_idx + iv) % 12 for iv in intervals]


def _pearson(hist: list[float], profile: list[float]) -> float:
    """Pearson correlation coefficient between two length-12 vectors."""
    n = 12
    mean_h = sum(hist) / n
    mean_p = sum(profile) / n
    num = sum((hist[i] - mean_h) * (profile[i] - mean_p) for i in range(n))
    den_h = sum((hist[i] - mean_h) ** 2 for i in range(n)) ** 0.5
    den_p = sum((profile[i] - mean_p) ** 2 for i in range(n)) ** 0.5
    if den_h == 0 or den_p == 0:
        return 0.0
    return num / (den_h * den_p)


def infer_key(chords: list[dict]) -> str | None:
    """Infer the key of a song from its detected chord symbols.

    Parameters
    ----------
    chords : list of dicts with at least a ``"text"`` key containing a chord
        symbol string (e.g. ``"Am7"``, ``"D/F#"``).  Items that cannot be
        parsed are silently skipped.

    Returns
    -------
    str or None
        The most likely key name (expressed as relative major, e.g. ``"C"``
        for a song in Am), or ``None`` if no chords could be parsed.
    """
    # Build pitch-class histogram from all notes implied by all chords.
    pc_counts: Counter[int] = Counter()
    for chord_dict in chords:
        try:
            chord = parse_chord(chord_dict["text"])
            root_idx = _note_to_index(chord.root)
            pcs = _chord_to_pitch_classes(root_idx, chord.quality, chord.extensions)
            pc_counts.update(pcs)
        except (ValueError, KeyError):
            continue

    if not pc_counts:
        return None

    # Normalise to a float histogram vector of length 12.
    hist = [float(pc_counts.get(i, 0)) for i in range(12)]

    # Score all 24 keys (12 major + 12 minor) via Pearson correlation.
    best_corr = -2.0
    best_tonic = 0
    best_is_minor = False

    for tonic in range(12):
        # Rotate profiles so index 0 aligns with this tonic.
        maj_profile = [_KK_MAJOR[(i - tonic) % 12] for i in range(12)]
        min_profile = [_KK_MINOR[(i - tonic) % 12] for i in range(12)]

        corr_maj = _pearson(hist, maj_profile)
        corr_min = _pearson(hist, min_profile)

        if corr_maj > best_corr:
            best_corr = corr_maj
            best_tonic = tonic
            best_is_minor = False

        if corr_min > best_corr:
            best_corr = corr_min
            best_tonic = tonic
            best_is_minor = True

    # Return relative major so downstream spelling is consistent.
    if best_is_minor:
        # Relative major is 3 semitones above the minor tonic.
        best_tonic = (best_tonic + 3) % 12

    return _KEY_NAMES[best_tonic]
