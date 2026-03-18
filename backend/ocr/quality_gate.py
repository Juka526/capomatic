"""Page-level OCR quality gate for chord sheet detection.

Heuristically decides whether the PaddleOCR result is trustworthy enough to
use directly, or whether an AI fallback should be invoked.

Thresholds are module-level constants so they can be tuned without touching
the logic:

MIN_PARSEABLE_UNIQUE  — minimum distinct chord strings that parse successfully.
                        Low count → bands may be misaligned or image too noisy.
MAX_SUSPICIOUS_RAW    — maximum "garbage" tokens among items that failed both
                        the strict regex and the recovery pass.
MAX_RECOVERED_RATIO   — recovered / strict ratio cap.  High ratio implies OCR
                        is producing many malformed strings that need repair.
MAX_PARSE_FAIL_RATIO  — fraction of unique candidate strings that do not parse.
                        High ratio means the chord filter is accepting noise.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from backend.chords.parser import parse_chord

# ---------------------------------------------------------------------------
# Thresholds — frozen after tuning run on 8-fixture dataset (2026-02-25)
#
# Tuning observations (hybrid eval, 8 Korean chord-sheet images):
#   MAX_SUSPICIOUS_RAW raised 12 → 30: Korean sheets OCR more non-chord tokens
#   (lyrics, bar numbers) than the initial estimate assumed.
#   Max observed suspicious_count on a clean image: 27 (빛으로 비추시네.jpg)
#   Safety margin: 30 − 27 = 3 tokens
#
#   All other thresholds unchanged — no false negatives observed for them.
#   Post-tune: 8/8 gate PASS, 0/8 AI fallback triggered, avg overhead < 1 ms
#
# To re-tune: run  python scripts/eval_ocr.py --engine hybrid  and compare
# observed stats against these limits.
# ---------------------------------------------------------------------------

MIN_PARSEABLE_UNIQUE = 8    # min distinct parseable chords; margin: all fixtures ≥ 10
MAX_SUSPICIOUS_RAW   = 30   # max garbage tokens; observed max = 27 on clean images
MAX_RECOVERED_RATIO  = 0.6  # recovered/strict cap; no fixture exceeded 0.4
MAX_PARSE_FAIL_RATIO = 0.35 # parse-fail fraction cap; all fixtures near 0.0

# Score denominator caps (same values — used in _compute_score normalization)
_CAP_SUSPICIOUS  = MAX_SUSPICIOUS_RAW
_CAP_REC_RATIO   = MAX_RECOVERED_RATIO
_CAP_PF_RATIO    = MAX_PARSE_FAIL_RATIO

# Tokens whose ALL-CAPS form indicate musical directions, not chords.
_SCORE_MARKERS = {"D.S.", "D.C.", "FINE", "CODA", "AL", "DS", "DC"}


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------

@dataclass
class GateDecision:
    """Result of a quality gate evaluation."""

    pass_gate: bool
    score: float              # 0..1; higher = more trustworthy
    reasons: list[str]        # failure reasons (empty if pass_gate is True)
    stats: dict               # raw counters for downstream debugging


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_suspicious(text: str) -> bool:
    """Return True if *text* (already normalised) looks like OCR noise/non-chord.

    Called only on items that failed both the strict regex and recovery.
    """
    if not text:
        return False
    # Pure digits → measure / bar number
    if re.match(r"^\d+$", text):
        return True
    # Musical direction markers
    if text.upper() in _SCORE_MARKERS:
        return True
    # Very long strings → almost certainly a lyric or merged text block
    if len(text) > 10:
        return True
    # All-lowercase and at least 3 chars → likely a lyric word
    if len(text) >= 3 and text.islower():
        return True
    return False


def _compute_score(
    parseable: int,
    n_suspicious: int,
    rec_ratio: float,
    pf_ratio: float,
) -> float:
    """Return a 0..1 composite trustworthiness score.

    Computed as a product of four independent penalty factors so that any
    single bad dimension can drag the score toward zero.
    """
    s = min(1.0, parseable / max(1, MIN_PARSEABLE_UNIQUE))
    s *= max(0.0, 1.0 - n_suspicious / max(1, _CAP_SUSPICIOUS))
    s *= max(0.0, 1.0 - rec_ratio   / _CAP_REC_RATIO)
    s *= max(0.0, 1.0 - pf_ratio    / _CAP_PF_RATIO)
    return round(s, 3)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_ocr_quality(
    raw_items: list[dict],
    strict_items: list[dict],
    recovered_items: list[dict],
) -> GateDecision:
    """Evaluate whether the OCR result is trustworthy.

    Parameters
    ----------
    raw_items      : All items returned by run_ocr_paddle (after normalisation).
    strict_items   : Subset that passed is_chord_candidate directly.
    recovered_items: Subset recovered by recover_candidates.

    Returns
    -------
    GateDecision with pass_gate, score, reasons, and stats.
    """
    chord_items = strict_items + recovered_items

    # Unique candidate texts
    all_unique: set[str] = {item["text"] for item in chord_items}

    # Build identity sets for fast membership test (by id — items are dicts)
    _chord_ids = {id(i) for i in chord_items}
    failed_items = [i for i in raw_items if id(i) not in _chord_ids]

    # 1. Parseability of unique candidate texts
    parseable_unique = 0
    for text in all_unique:
        try:
            parse_chord(text)
            parseable_unique += 1
        except ValueError:
            pass
    unparseable_unique = len(all_unique) - parseable_unique
    parse_fail_ratio = unparseable_unique / max(1, len(all_unique))

    # 2. Suspicious tokens among failures
    suspicious = [i for i in failed_items if _is_suspicious(i["text"])]

    # 3. Recovery pressure
    recovered_ratio = len(recovered_items) / max(1, len(strict_items))

    # 4. Gate rules
    reasons: list[str] = []
    if parseable_unique < MIN_PARSEABLE_UNIQUE:
        reasons.append(
            f"too few parseable unique chords: {parseable_unique} "
            f"(min {MIN_PARSEABLE_UNIQUE})"
        )
    if len(suspicious) > MAX_SUSPICIOUS_RAW:
        reasons.append(
            f"too many suspicious tokens: {len(suspicious)} "
            f"(max {MAX_SUSPICIOUS_RAW})"
        )
    if recovered_ratio > MAX_RECOVERED_RATIO:
        reasons.append(
            f"high recovery pressure: {recovered_ratio:.2f} "
            f"(max {MAX_RECOVERED_RATIO})"
        )
    if parse_fail_ratio > MAX_PARSE_FAIL_RATIO:
        reasons.append(
            f"high parse fail ratio: {parse_fail_ratio:.2f} "
            f"(max {MAX_PARSE_FAIL_RATIO})"
        )

    score = _compute_score(parseable_unique, len(suspicious), recovered_ratio, parse_fail_ratio)

    stats = {
        "total_raw":          len(raw_items),
        "strict_count":       len(strict_items),
        "recovered_count":    len(recovered_items),
        "failed_count":       len(failed_items),
        "suspicious_count":   len(suspicious),
        "unique_candidates":  len(all_unique),
        "parseable_unique":   parseable_unique,
        "unparseable_unique": unparseable_unique,
        "parse_fail_ratio":   round(parse_fail_ratio, 3),
        "recovered_ratio":    round(recovered_ratio, 3),
    }

    return GateDecision(
        pass_gate=len(reasons) == 0,
        score=score,
        reasons=reasons,
        stats=stats,
    )
