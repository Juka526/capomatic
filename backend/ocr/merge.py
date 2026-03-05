"""Row-alignment merge of PaddleOCR spatial data and Claude Vision chord text.

PaddleOCR provides reliable bounding boxes but misreads some chord symbols
(e.g. drops '#' from D/F# → D/F) and occasionally misses chords entirely.
Claude Vision reads chord text with high accuracy but returns no spatial data.

This module aligns the two outputs row-by-row so that:
- Claude's text is always used (authoritative)
- PaddleOCR's bboxes are preserved where a positional match exists
- Chords found by Claude but missed by PaddleOCR get bbox=None
- PaddleOCR detections not confirmed by Claude are dropped (false positives)

Matching strategy
-----------------
Within each row, LCS (Longest Common Subsequence) on normalised chord text
finds pairs where PaddleOCR and Claude agree on the text.  For PaddleOCR
items not matched by LCS (e.g. OCR misread "D/F#" as "D/F"), a positional
fallback donates those bboxes to the nearest unmatched Claude items so that
text corrections do not lose their spatial data.
"""
from __future__ import annotations

from backend.chords.normalize import normalize_chord_text
from backend.ocr.filter import is_chord_candidate


# ---------------------------------------------------------------------------
# Row clustering
# ---------------------------------------------------------------------------

def cluster_paddle_items_by_row(
    items: list[dict],
) -> list[list[dict]]:
    """Group PaddleOCR items into horizontal staff rows.

    Items with ``bbox=None`` are excluded before clustering.
    Within each row, items are sorted left-to-right by x1.

    Parameters
    ----------
    items : list of OCR item dicts with keys ``text``, ``confidence``, ``bbox``.

    Returns
    -------
    list of rows, each row is a list of item dicts sorted left-to-right.
    Returns ``[]`` for empty input.
    """
    valid = [i for i in items if i.get("bbox") is not None]
    if not valid:
        return []

    avg_h = sum(i["bbox"][3] - i["bbox"][1] for i in valid) / len(valid)
    threshold = max(20, int(avg_h * 1.5))

    sorted_items = sorted(valid, key=lambda i: i["bbox"][1])
    rows: list[list[dict]] = [[sorted_items[0]]]

    for item in sorted_items[1:]:
        row_min_y1 = min(x["bbox"][1] for x in rows[-1])
        if item["bbox"][1] - row_min_y1 <= threshold:
            rows[-1].append(item)
        else:
            rows.append([item])

    for row in rows:
        row.sort(key=lambda i: i["bbox"][0])

    return rows


# ---------------------------------------------------------------------------
# LCS helpers
# ---------------------------------------------------------------------------

def _lcs_matched_pairs(
    seq_a: list[str],
    seq_b: list[str],
) -> list[tuple[int, int]]:
    """Return (a_idx, b_idx) pairs from Longest Common Subsequence of seq_a, seq_b.

    Only pairs where seq_a[i] == seq_b[j] are returned, in order.
    """
    n, m = len(seq_a), len(seq_b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if seq_a[i - 1] == seq_b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    pairs: list[tuple[int, int]] = []
    i, j = n, m
    while i > 0 and j > 0:
        if seq_a[i - 1] == seq_b[j - 1]:
            pairs.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    return pairs


# ---------------------------------------------------------------------------
# Single-row merge
# ---------------------------------------------------------------------------

def merge_single_row(
    paddle_items: list[dict],
    claude_texts: list[str],
) -> list[dict]:
    """Align one row of Claude chord strings to one row of PaddleOCR items.

    Algorithm
    ---------
    1. Normalise and validate each Claude text string; skip invalid ones.
    2. LCS alignment on normalised Claude texts vs PaddleOCR texts:
       matched pairs share a bbox (Claude text replaces PaddleOCR text).
    3. Positional fallback: unmatched PaddleOCR items donate their bboxes to
       the closest unmatched Claude item by position ratio.  This ensures that
       text corrections (e.g. PaddleOCR read "D/F" instead of "D/F#") still
       produce an item with the correct spatial bbox rather than bbox=None.
    4. Remaining unmatched Claude items get bbox=None (PaddleOCR missed them).

    Parameters
    ----------
    paddle_items : Left-to-right sorted items from ``cluster_paddle_items_by_row``.
    claude_texts : Chord strings returned by Claude for this row.

    Returns
    -------
    list of merged item dicts (``text``, ``confidence=1.0``, ``bbox``).
    """
    # Step 1: normalise and validate Claude texts; track original index
    valid_c: list[tuple[int, str]] = []   # (original_idx, normalised_text)
    for idx, raw in enumerate(claude_texts):
        norm = normalize_chord_text(str(raw))
        if is_chord_candidate(norm):
            valid_c.append((idx, norm))

    n_valid = len(valid_c)
    n_p = len(paddle_items)

    # Edge cases
    if n_valid == 0:
        return []
    if n_p == 0:
        return [{"text": norm, "confidence": 1.0, "bbox": None}
                for _, norm in valid_c]

    # Step 2: LCS alignment
    c_texts_local = [norm for _, norm in valid_c]
    p_texts_local = [item["text"] for item in paddle_items]
    lcs_pairs = _lcs_matched_pairs(c_texts_local, p_texts_local)

    # Build maps: local_c_idx → local_p_idx
    c_to_p: dict[int, int] = {}
    matched_p: set[int] = set()
    for ci, pi in lcs_pairs:
        c_to_p[ci] = pi
        matched_p.add(pi)

    # Step 3: positional fallback for unmatched PaddleOCR items
    unmatched_c = [ci for ci in range(n_valid) if ci not in c_to_p]
    unmatched_p = [pi for pi in range(n_p) if pi not in matched_p]

    remaining_c = list(unmatched_c)
    for pi in unmatched_p:
        if not remaining_c:
            break
        p_ratio = pi / n_p
        # Pick the unmatched Claude item whose position ratio is closest
        best_ci = min(remaining_c, key=lambda ci: abs(ci / n_valid - p_ratio))
        c_to_p[best_ci] = pi
        remaining_c.remove(best_ci)

    # Step 4: build result in Claude's reading order
    result: list[dict] = []
    for local_ci, (_, norm) in enumerate(valid_c):
        bbox = paddle_items[c_to_p[local_ci]]["bbox"] if local_ci in c_to_p else None
        result.append({
            "text":       norm,
            "confidence": 1.0,
            "bbox":       bbox,
        })

    return result


# ---------------------------------------------------------------------------
# Multi-row merge
# ---------------------------------------------------------------------------

def merge_rows(
    paddle_rows: list[list[dict]],
    claude_rows: list[list[str]],
) -> list[dict]:
    """Align Claude rows to PaddleOCR rows by index and merge each pair.

    - Matched rows (up to ``min(len(paddle_rows), len(claude_rows))``):
      merged via ``merge_single_row``.
    - Extra Claude rows (Claude found more staff rows than Paddle):
      all chords added with ``bbox=None``.
    - Extra Paddle rows (Paddle found more than Claude): dropped.

    Parameters
    ----------
    paddle_rows : Output of ``cluster_paddle_items_by_row``.
    claude_rows : ``AIFallbackResult.rows`` — list of rows, each a list of
                  chord strings.

    Returns
    -------
    Flat list of merged item dicts.
    """
    n_matched = min(len(paddle_rows), len(claude_rows))
    result: list[dict] = []

    for i in range(n_matched):
        result.extend(merge_single_row(paddle_rows[i], claude_rows[i]))

    # Extra Claude rows: no Paddle row to match — all chords get bbox=None
    for extra_row in claude_rows[n_matched:]:
        result.extend(merge_single_row([], extra_row))

    return result
