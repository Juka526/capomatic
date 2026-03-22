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

# Minimum OCR confidence score required to consider any detection at all.
# Items below this threshold are dropped before chord matching so that
# low-confidence noise never accidentally passes the chord filter.
CONFIDENCE_THRESHOLD = 0.78

# Lower floor for chord-syntax rescue: detections between this and
# CONFIDENCE_THRESHOLD are accepted only if they pass the strict chord
# regex.  The regex is selective enough that random OCR noise virtually
# never matches, so this rescues real chords (e.g. "Gm6" at 0.70) that
# fall just below the main threshold.
_RESCUE_FLOOR = 0.40

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

# Matches a leading digit sequence followed by a chord root, e.g. "7Am", "4G/B".
# The captured group is the chord portion (everything after the digits).
_LEADING_NUM_RE = re.compile(r"^\d+([A-G].*)$")

# OCR confusion: trailing "b" after a quality/extension → try "6".
# In music-engraving fonts, "6" and "b" (flat) are visually similar and OCR
# frequently misreads one as the other.  "Gmb" is not a valid chord but "Gm6" is.
_TRAILING_B_RE = re.compile(r'^([A-G][#b]?(?:maj|m(?!aj)|dim|aug|sus)?)b$')


def _strip_leading_number(text: str) -> str | None:
    """Strip a leading digit sequence when the remainder starts with a chord root.

    Examples: "7Am" -> "Am",  "4G/B" -> "G/B",  "12Cmaj7" -> "Cmaj7"
    Returns None if the text does not match the pattern.
    """
    m = _LEADING_NUM_RE.match(text)
    return m.group(1) if m else None


def _try_slash_chord(text: str) -> str | None:
    """Try interpreting *text* as a slash chord with a missing "/".

    OCR sometimes misses the "/" in slash chords like "G/B" → "GB".
    If the text is exactly two adjacent root notes (with optional sharp/flat),
    try inserting "/" and check if the result is a valid chord.

    Returns the slash chord string if valid, else None.
    """
    m = re.match(r'^([A-G][#b]?)([A-G][#b]?)$', text)
    if m:
        slash = f"{m.group(1)}/{m.group(2)}"
        if is_chord_candidate(slash):
            return slash
    return None


def _split_concatenated(text: str) -> list[str]:
    """Recursively split *text* into valid chord strings (handles 2+ chords).

    If the left part is a valid chord but the right part isn't, recursively
    attempts to split the remainder so that 3+ concatenated chords are handled.

    Returns a list of chord strings if a valid split is found, else [].

    Examples
    --------
    "Em7G/A"           → ["Em7", "G/A"]
    "F#7sus4F#7/A#Bm7" → ["F#7sus4", "F#7/A#", "Bm7"]
    "D/F#"             → []  (F preceded by / → not a split point)
    """
    for m in _SPLIT_ROOT_RE.finditer(text):
        pos = m.start()
        if pos == 0:
            continue
        c1 = normalize_chord_text(text[:pos])
        if not is_chord_candidate(c1):
            continue
        rest = text[pos:]
        rest_norm = normalize_chord_text(rest)
        if is_chord_candidate(rest_norm):
            return [c1, rest_norm]
        # Right part not valid — try recursive split.
        sub = _split_concatenated(rest)
        if sub:
            return [c1] + sub
    return []


def _split_bbox(
    item: dict,
    parts: list[str],
    bbox: list[int] | None,
) -> list[dict]:
    """Create split items with proportionally divided bboxes.

    Divides the original bbox horizontally by character-length ratio so each
    chord gets its own approximate bounding box.  Supports any number of parts.
    If bbox is None, all items share bbox=None.
    """
    if bbox is None:
        return [{**item, "text": part} for part in parts]

    x1, y1, x2, y2 = bbox
    total_len = sum(len(p) for p in parts)
    results: list[dict] = []
    cur_x = x1
    for i, part in enumerate(parts):
        ratio = len(part) / total_len if total_len > 0 else 1 / len(parts)
        seg_w = int((x2 - x1) * ratio)
        seg_x2 = cur_x + seg_w if i < len(parts) - 1 else x2
        results.append({**item, "text": part, "bbox": [cur_x, y1, seg_x2, y2]})
        cur_x = seg_x2
    return results


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

        # --- leading-number strip recovery ---
        # Handles OCR artefacts like "7Am" or "4G/B" where a measure/beat
        # number is fused to the chord root.
        stripped = _strip_leading_number(text)
        if stripped is not None:
            norm = normalize_chord_text(stripped)
            if is_chord_candidate(norm):
                recovered.append({**item, "text": norm})
                parse_count += 1
                continue
            # OCR confusion: trailing "b" → "6" (e.g. "Gmb" → "Gm6")
            m_b = _TRAILING_B_RE.match(norm)
            if m_b:
                alt = m_b.group(1) + "6"
                if is_chord_candidate(alt):
                    recovered.append({**item, "text": alt})
                    parse_count += 1
                    continue

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

        # OCR confusion: trailing "b" → "6" (e.g. "Gmb" → "Gm6").
        # Applied here for items that arrive without leading numbers
        # (e.g. after multi-token space-splitting of "17 Gmb").
        m_b = _TRAILING_B_RE.match(norm)
        if m_b:
            alt = m_b.group(1) + "6"
            if is_chord_candidate(alt):
                recovered.append({**item, "text": alt})
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

        # --- slash chord recovery ---
        # Try interpreting adjacent root notes as a slash chord with missing "/".
        # Must be checked BEFORE split recovery so "GB" → "G/B" (one chord)
        # rather than "G" + "B" (two separate chords).
        slash = _try_slash_chord(text)
        if slash:
            recovered.append({**item, "text": slash})
            parse_count += 1
            continue

        # --- split recovery ---
        parts = _split_concatenated(text)
        if parts:
            bbox = item.get("bbox")
            split_items = _split_bbox(item, parts, bbox)
            recovered.extend(split_items)
            split_count += 1

    return recovered, parse_count, split_count


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def filter_candidates(ocr_items: list[dict]) -> list[dict]:
    """Keep only items whose ``text`` field is a valid chord symbol.

    Runs the strict regex first, then attempts recovery on failing items.
    Items below CONFIDENCE_THRESHOLD but above _RESCUE_FLOOR are accepted
    if they pass the strict chord regex (chord-syntax rescue).
    Bbox and confidence are preserved (split items share the source bbox).
    """
    candidates = [item for item in ocr_items if item["confidence"] > CONFIDENCE_THRESHOLD]
    strict = [item for item in candidates if is_chord_candidate(item["text"])]
    failed = [item for item in candidates if not is_chord_candidate(item["text"])]
    extra, _, _ = recover_candidates(failed)

    # Chord-syntax rescue: accept lower-confidence items that match the
    # strict chord regex.  The regex rejects noise so this is safe.
    rescued = [
        item for item in ocr_items
        if _RESCUE_FLOOR < item["confidence"] <= CONFIDENCE_THRESHOLD
        and is_chord_candidate(item["text"])
    ]

    return strict + extra + rescued
