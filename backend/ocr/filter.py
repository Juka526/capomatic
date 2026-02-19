"""Chord-candidate filter for raw OCR output.

Filtering runs in two passes:
  1. Strict regex  — conservative pattern; high precision.
  2. Recovery pass — attempts to salvage items that fail strict by:
       a) re-normalising text (catches leftover case variants), then
       b) splitting concatenated detections such as "Em7G/A" → "Em7" + "G/A".
"""
from __future__ import annotations

import re

from backend.chords.normalize import normalize_chord_text
from backend.chords.parser import parse_chord

# ---------------------------------------------------------------------------
# Strict regex (pass 1)
# ---------------------------------------------------------------------------
# Root       [A-G][#b]?
# Quality    maj | m (not followed by "aj") | dim | aug | sus
# Numeric    1-2 digit extension (6, 7, 9, 11, 13, ...)
# Sus suffix sus followed by optional 2 or 4
# Add suffix add followed by digits
# Paren      any parenthesised block, e.g. (sus4), (add9), (b5)
# Slash bass /[A-G][#b]?
#
# Ordering matters: "maj" must be tried before bare "m".
# ---------------------------------------------------------------------------

_CHORD_RE = re.compile(
    r"^"
    r"[A-G][#b]?"                        # root
    r"(?:maj|m(?!aj)|dim|aug|sus)?"      # optional quality
    r"(?:[0-9]{1,2})?"                   # optional numeric extension
    r"(?:sus[24]?)?"                     # optional sus modifier
    r"(?:add[0-9]+)?"                    # optional add modifier
    r"(?:\([^)]*\))?"                    # optional parenthesised part
    r"(?:/[A-G][#b]?)?"                  # optional slash bass
    r"$"
)


def is_chord_candidate(text: str) -> bool:
    """Return True if *text* looks like a chord symbol (strict check).

    Normalise the text with ``normalize_chord_text`` before calling this.
    """
    return bool(_CHORD_RE.match(text))


# ---------------------------------------------------------------------------
# Recovery pass (pass 2)
# ---------------------------------------------------------------------------

# Pre-screen: root + up to 14 mixed chars.  Rejects long lyric words cheaply.
_LOOSE_RE = re.compile(r"^[A-G][#b]?[A-Za-z0-9()/#b+\-]{0,14}$")

# Find a chord root that is NOT immediately preceded by a slash-bass slash.
# Used to locate candidate split points in concatenated strings like "Em7G/A".
_SPLIT_ROOT_RE = re.compile(r"(?<=[^/])([A-G][#b]?)")


def _split_concatenated(text: str) -> list[str]:
    """Try to split *text* into two valid chord strings.

    Returns [chord1, chord2] if a valid split is found, else [].

    Examples
    --------
    "Em7G/A"  → ["Em7", "G/A"]   (split at pos 3; /A is bass, not a root)
    "D/F#"    → []                (F preceded by / → not a split point)
    """
    for m in _SPLIT_ROOT_RE.finditer(text):
        pos = m.start()
        if pos == 0:
            continue  # the first root is not a split point
        c1 = normalize_chord_text(text[:pos])
        c2 = normalize_chord_text(text[pos:])
        if is_chord_candidate(c1) and is_chord_candidate(c2):
            return [c1, c2]
    return []


def recover_candidates(
    items: list[dict],
) -> tuple[list[dict], int, int]:
    """Attempt to recover chord items that failed the strict regex.

    Parameters
    ----------
    items : list of OCR item dicts (text, confidence, bbox) — all items that
        failed ``is_chord_candidate`` on their current ``text`` value.

    Returns
    -------
    recovered : list[dict]
        Items accepted via recovery, with ``text`` updated to the normalised
        (or split) form.
    parse_count : int
        Items recovered by normalisation + parse validation.
    split_count : int
        Items recovered by splitting concatenated chord strings (each split
        detection counts as one event even though it yields two output items).
    """
    recovered: list[dict] = []
    parse_count = 0
    split_count = 0

    for item in items:
        text = item["text"]

        # Pre-screen: skip items that clearly cannot be chords.
        if not _LOOSE_RE.match(text):
            continue

        norm = normalize_chord_text(text)

        # --- parse recovery ---
        # Re-normalise here in case upstream normalisation missed a case variant
        # (should not happen after normalize.py fix, but kept for robustness).
        if is_chord_candidate(norm):
            recovered.append({**item, "text": norm})
            parse_count += 1
            continue

        # Secondary check: parse_chord as a less strict gate, still guarded by
        # is_chord_candidate to prevent false positives.
        try:
            parse_chord(norm)
        except ValueError:
            pass  # not parseable at all → fall through to split
        else:
            if is_chord_candidate(norm):
                recovered.append({**item, "text": norm})
                parse_count += 1
                continue

        # --- split recovery ---
        parts = _split_concatenated(text)
        if parts:
            for part in parts:
                recovered.append({**item, "text": part})
            split_count += 1

    return recovered, parse_count, split_count


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def filter_candidates(ocr_items: list[dict]) -> list[dict]:
    """Keep only items whose ``text`` field is a valid chord symbol.

    Runs the strict regex first, then attempts recovery on failing items.
    Bbox and confidence are preserved (split items share the source bbox).
    """
    strict = [item for item in ocr_items if is_chord_candidate(item["text"])]
    failed = [item for item in ocr_items if not is_chord_candidate(item["text"])]
    extra, _, _ = recover_candidates(failed)
    return strict + extra
