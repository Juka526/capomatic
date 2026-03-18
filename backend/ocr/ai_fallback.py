"""AI vision fallback for chord detection.

When the quality gate decides that PaddleOCR output is not trustworthy,
this module sends the raw image to an AI model and asks it to list chords
row-by-row.  The AI does detection only — transposition remains a separate
deterministic step.

Supported providers
-------------------
"mock"   Always returns empty rows.  Used in tests and CI (no API key needed).
"claude" Uses Anthropic claude-haiku-4-5 via the ``anthropic`` SDK.
         Requires the ANTHROPIC_API_KEY environment variable.

Adding new providers
--------------------
Implement a function ``_run_<provider>(image_path) -> tuple[list[list[str]], str]``
that returns (rows, raw_response_text) and register it in _PROVIDERS.
"""
from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass

from backend.chords.normalize import normalize_chord_text
from backend.ocr.filter import is_chord_candidate

# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------

@dataclass
class AIFallbackResult:
    """Result of an AI-based chord detection call."""

    rows: list[list[str]]        # [["D", "Asus4", "A"], ["G", "Em7"]]
    provider: str
    raw_response_text: str | None
    used_mock: bool
    meta: dict                   # latency_ms, input_tokens, output_tokens, error


# ---------------------------------------------------------------------------
# Row → item conversion
# ---------------------------------------------------------------------------

def flatten_rows_to_items(rows: list[list[str]]) -> list[dict]:
    """Convert AI rows into the same dict format as run_ocr_paddle items.

    Each entry gets ``confidence=1.0`` (AI explicitly named it as a chord)
    and ``bbox=None`` (no spatial information available from text-only AI).

    Invalid strings (fail is_chord_candidate after normalisation) are dropped.
    """
    items: list[dict] = []
    for row in rows:
        for text in row:
            norm = normalize_chord_text(str(text))
            if is_chord_candidate(norm):
                items.append({
                    "text":       norm,
                    "confidence": 1.0,
                    "bbox":       None,
                })
    return items


# ---------------------------------------------------------------------------
# Provider: mock
# ---------------------------------------------------------------------------

def _run_mock(image_path: str) -> tuple[list[list[str]], str | None]:  # noqa: ARG001
    """Return empty rows.  No network call, no dependencies."""
    return [], None


# ---------------------------------------------------------------------------
# Provider: claude
# ---------------------------------------------------------------------------

_CLAUDE_MODEL   = "claude-haiku-4-5-20251001"
_CLAUDE_PROMPT  = (
    "This is a chord sheet for a song. "
    "List EVERY chord symbol exactly as written, row by row "
    "(each row = one staff system / line of music). "
    "Include chords with parenthetical extensions such as D(add2), A(sus4), G(b5). "
    "Do NOT transpose or modify any chord. "
    "Return ONLY valid JSON with no extra text:\n"
    '{"rows": [["D", "Asus4", "A", "Bm7"], ["G", "D", "A"]]}'
)
_MEDIA_TYPES = {
    "jpg":  "image/jpeg",
    "jpeg": "image/jpeg",
    "png":  "image/png",
    "webp": "image/webp",
}


def _run_claude(image_path: str) -> tuple[list[list[str]], str | None]:
    """Call Claude vision API and parse the JSON response."""
    try:
        import anthropic  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            "The 'anthropic' package is required for provider='claude'. "
            "Install it with: pip install anthropic"
        ) from exc

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Set it to use provider='claude'."
        )

    ext = image_path.rsplit(".", 1)[-1].lower() if "." in image_path else "png"
    media_type = _MEDIA_TYPES.get(ext, "image/jpeg")

    with open(image_path, "rb") as f:
        b64_data = base64.standard_b64encode(f.read()).decode()

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=_CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type":       "base64",
                        "media_type": media_type,
                        "data":       b64_data,
                    },
                },
                {"type": "text", "text": _CLAUDE_PROMPT},
            ],
        }],
    )

    raw_text = response.content[0].text
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude returned invalid JSON: {exc}") from exc
    rows = data.get("rows")
    if not isinstance(rows, list):
        raise ValueError(f"Expected 'rows' to be a list, got {type(rows)}")
    return rows, raw_text


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

_PROVIDERS: dict[str, callable] = {
    "mock":   _run_mock,
    "claude": _run_claude,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ai_detect_chords_rows(
    image_path: str,
    *,
    provider: str = "mock",
) -> AIFallbackResult:
    """Detect chords in *image_path* using an AI vision provider.

    Parameters
    ----------
    image_path : str
        Path to the image file.
    provider   : str
        Which backend to use.  ``"mock"`` for tests; ``"claude"`` for real
        inference (requires ANTHROPIC_API_KEY).

    Returns
    -------
    AIFallbackResult
        Always returns a result — errors are captured in ``meta["error"]``
        and ``rows`` is left empty so the caller can fall back gracefully.
    """
    if provider not in _PROVIDERS:
        raise ValueError(
            f"Unknown AI provider: {provider!r}. "
            f"Choose from: {sorted(_PROVIDERS)}"
        )

    used_mock  = provider == "mock"
    meta: dict = {}
    t0 = time.perf_counter()

    try:
        rows, raw_text = _PROVIDERS[provider](image_path)
        meta["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    except Exception as exc:  # noqa: BLE001
        meta["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        meta["error"]      = str(exc)
        return AIFallbackResult(
            rows=[],
            provider=provider,
            raw_response_text=None,
            used_mock=used_mock,
            meta=meta,
        )

    return AIFallbackResult(
        rows=rows,
        provider=provider,
        raw_response_text=raw_text,
        used_mock=used_mock,
        meta=meta,
    )
