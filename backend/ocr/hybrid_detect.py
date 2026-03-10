"""Hybrid chord detection pipeline.

Orchestrates the full pipeline:

  1. PaddleOCR  → raw items + spatial metadata        ┐ run in parallel
  2. Claude Vision → authoritative chord text (rows)   ┘
  3. Filter     → strict regex + recovery pass (with confidence gate)
  4. Quality gate → diagnostic score (no longer gates Claude invocation)
  5. Merge      → align Claude rows to PaddleOCR rows by position;
                  Claude text is authoritative, PaddleOCR bboxes are reused

Claude Vision always runs when ``use_ai_fallback=True`` (not just on gate
failure), fixing two categories of error:
  • PaddleOCR completely misses a chord  → Claude adds it with bbox=None
  • PaddleOCR misreads a chord symbol    → Claude's text replaces it,
                                           PaddleOCR's bbox is preserved

Items from the AI path carry ``bbox=None`` and ``confidence=1.0`` instead
of real OCR values.  All existing callers are drop-in compatible.
"""
from __future__ import annotations

import concurrent.futures
import logging

from backend.ocr.paddle_ocr import run_ocr_paddle

logger = logging.getLogger(__name__)
from backend.ocr.filter import (
    CONFIDENCE_THRESHOLD,
    is_chord_candidate,
    recover_candidates,
)
from backend.ocr.quality_gate import evaluate_ocr_quality, GateDecision
from backend.ocr.ai_fallback import (
    ai_detect_chords_rows,
    AIFallbackResult,
)
from backend.ocr.merge import cluster_paddle_items_by_row, merge_rows

_CLAUDE_TIMEOUT_S = 20.0  # max seconds to wait for Claude before falling back


def detect_chords_hybrid(
    image_path: str,
    *,
    use_ai_fallback: bool = True,
    ai_provider: str = "mock",
) -> tuple[list[dict], dict]:
    """Run the full hybrid pipeline on *image_path*.

    Parameters
    ----------
    image_path      : Path to the chord sheet image.
    use_ai_fallback : If False, skip Claude entirely and return Paddle-only
                      result (useful for benchmarking / offline mode).
    ai_provider     : ``"mock"`` (default, no API key needed) or ``"claude"``
                      (requires ANTHROPIC_API_KEY).

    Returns
    -------
    items : list[dict]
        Each dict has ``text``, ``confidence``, ``bbox``.
        ``bbox`` is None for chords that had no matching PaddleOCR detection.
    meta  : dict
        Superset of the paddle_ocr meta dict, with extra keys:
        ``gate``        — GateDecision fields (pass, score, reasons, stats)
        ``ai_used``     — bool: whether Claude items are in the final output
        ``ai_provider`` — provider name or None
        ``recovery``    — {"parse": int, "split": int}
        ``merge_stats`` — {"paddle_rows", "claude_rows", "final_count"} or None
    """
    # ------------------------------------------------------------------
    # 1. PaddleOCR + Claude Vision — run concurrently
    # ------------------------------------------------------------------
    ai_result: AIFallbackResult | None = None

    if use_ai_fallback:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            paddle_future = executor.submit(run_ocr_paddle, image_path)
            claude_future = executor.submit(
                ai_detect_chords_rows, image_path, provider=ai_provider
            )
            try:
                raw_items, paddle_meta = paddle_future.result()
            except Exception:
                logger.exception("PaddleOCR failed; returning empty results")
                raw_items, paddle_meta = [], {}
            try:
                ai_result = claude_future.result(timeout=_CLAUDE_TIMEOUT_S)
            except concurrent.futures.TimeoutError:
                logger.warning("Claude timed out after %.1fs", _CLAUDE_TIMEOUT_S)
                ai_result = None  # fall through to legacy path
            except Exception:
                logger.exception("Claude fallback failed")
                ai_result = None
    else:
        raw_items, paddle_meta = run_ocr_paddle(image_path)

    # ------------------------------------------------------------------
    # 2. Filter (mirrors the logic in eval_ocr.py / ocr_debug.py)
    # ------------------------------------------------------------------
    confident = [i for i in raw_items if i["confidence"] > CONFIDENCE_THRESHOLD]
    strict    = [i for i in confident if is_chord_candidate(i["text"])]
    failed    = [i for i in confident if not is_chord_candidate(i["text"])]
    recovered, parse_count, split_count = recover_candidates(failed)

    # ------------------------------------------------------------------
    # 3. Quality gate (kept for diagnostics; no longer gates Claude)
    # ------------------------------------------------------------------
    gate: GateDecision = evaluate_ocr_quality(raw_items, strict, recovered)

    # ------------------------------------------------------------------
    # 4. Merge or legacy fallback
    # ------------------------------------------------------------------
    if ai_result is not None and ai_result.rows:
        # Always-on merge: Claude text is authoritative, Paddle bboxes reused
        paddle_rows = cluster_paddle_items_by_row(strict + recovered)
        final_items = merge_rows(paddle_rows, ai_result.rows)
        ai_used = True
        merge_stats: dict | None = {
            "paddle_rows": len(paddle_rows),
            "claude_rows": len(ai_result.rows),
            "final_count": len(final_items),
        }
    else:
        # Legacy path: Claude unavailable (mock, timeout, API error)
        # Exact pre-refineOCR behaviour preserved for backward compatibility
        final_items = strict + recovered
        ai_used = False
        merge_stats = None

    # ------------------------------------------------------------------
    # 5. Build enriched meta
    # ------------------------------------------------------------------
    meta = {
        **paddle_meta,
        "gate": {
            "pass":    gate.pass_gate,
            "score":   gate.score,
            "reasons": gate.reasons,
            "stats":   gate.stats,
        },
        "ai_used":     ai_used,
        "ai_provider": ai_result.provider if ai_result is not None else None,
        "recovery":    {"parse": parse_count, "split": split_count},
        "merge_stats": merge_stats,
    }

    return final_items, meta
