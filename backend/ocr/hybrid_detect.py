"""Hybrid chord detection pipeline.

Orchestrates the full Section 4 pipeline:

  1. PaddleOCR  → raw items + spatial metadata
  2. Filter     → strict regex + recovery pass (with confidence gate)
  3. Quality gate → decide if Paddle result is trustworthy
  4. AI fallback  → (optional) ask Claude when gate fails

The output (items, meta) has the same shape as run_ocr_paddle so all
existing callers are drop-in compatible.  Items from the AI path carry
``bbox=None`` and ``confidence=1.0`` instead of real OCR values.
"""
from __future__ import annotations

from backend.ocr.paddle_ocr import run_ocr_paddle
from backend.ocr.filter import (
    CONFIDENCE_THRESHOLD,
    is_chord_candidate,
    recover_candidates,
)
from backend.ocr.quality_gate import evaluate_ocr_quality, GateDecision
from backend.ocr.ai_fallback import (
    ai_detect_chords_rows,
    flatten_rows_to_items,
    AIFallbackResult,
)


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
    use_ai_fallback : If False, skip AI even when the gate fails (Paddle
                      result is returned as-is).  Useful for benchmarking.
    ai_provider     : ``"mock"`` (default, no API key needed) or ``"claude"``
                      (requires ANTHROPIC_API_KEY).

    Returns
    -------
    items : list[dict]
        Each dict has ``text``, ``confidence``, ``bbox``.
        ``bbox`` is None for items that came from the AI fallback.
    meta  : dict
        Superset of the paddle_ocr meta dict, with extra keys:
        ``gate``        — GateDecision fields (pass, score, reasons, stats)
        ``ai_used``     — bool: whether AI items are in the final output
        ``ai_provider`` — provider name or None
        ``recovery``    — {"parse": int, "split": int}
    """
    # ------------------------------------------------------------------
    # 1. Paddle OCR
    # ------------------------------------------------------------------
    raw_items, paddle_meta = run_ocr_paddle(image_path)

    # ------------------------------------------------------------------
    # 2. Filter (mirrors the logic in eval_ocr.py / ocr_debug.py)
    # ------------------------------------------------------------------
    confident = [i for i in raw_items if i["confidence"] > CONFIDENCE_THRESHOLD]
    strict    = [i for i in confident if is_chord_candidate(i["text"])]
    failed    = [i for i in confident if not is_chord_candidate(i["text"])]
    recovered, parse_count, split_count = recover_candidates(failed)

    # ------------------------------------------------------------------
    # 3. Quality gate
    # ------------------------------------------------------------------
    gate: GateDecision = evaluate_ocr_quality(raw_items, strict, recovered)

    # ------------------------------------------------------------------
    # 4. AI fallback (only when gate fails and caller allows it)
    # ------------------------------------------------------------------
    ai_result: AIFallbackResult | None = None
    final_items = strict + recovered

    if not gate.pass_gate and use_ai_fallback:
        ai_result = ai_detect_chords_rows(image_path, provider=ai_provider)
        if ai_result.rows:
            final_items = flatten_rows_to_items(ai_result.rows)

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
        "ai_used":     ai_result is not None and bool(ai_result.rows),
        "ai_provider": ai_result.provider if ai_result is not None else None,
        "recovery":    {"parse": parse_count, "split": split_count},
    }

    return final_items, meta
