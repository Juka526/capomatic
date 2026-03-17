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
_RESCUE_FLOOR = 0.50

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


def _split_bbox(
    item: dict,
    parts: list[str],
    bbox: list[int] | None,
) -> list[dict]:
    """Create split items with proportionally divided bboxes.

    When a concatenated detection like "Gsus4C" is split into ["Gsus4", "C"],
    the original bbox is divided horizontally by character-length ratio so each
    chord gets its own approximate bounding box.  If bbox is None, both items
    share bbox=None.
    """
    if bbox is None or len(parts) != 2:
        return [{**item, "text": part} for part in parts]

    x1, y1, x2, y2 = bbox
    total_len = sum(len(p) for p in parts)
    ratio = len(parts[0]) / total_len if total_len > 0 else 0.5
    x_split = x1 + int((x2 - x1) * ratio)
    return [
        {**item, "text": parts[0], "bbox": [x1, y1, x_split, y2]},
        {**item, "text": parts[1], "bbox": [x_split, y1, x2, y2]},
    ]


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
