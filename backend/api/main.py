"""transchord FastAPI application.

Endpoints
---------
GET  /health          — liveness probe
POST /detect          — detect chords in an uploaded sheet image and transpose them
POST /overlay         — detect, transpose, render overlay image, return PNG

Usage
-----
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \\
      uvicorn backend.api.main:app --reload --port 8000
"""
from __future__ import annotations

import io
import logging
import os
import tempfile
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image

from backend.ocr.hybrid_detect import detect_chords_hybrid
from backend.ocr.paddle_ocr import get_ocr
from backend.chords.parser import parse_chord
from backend.chords.transpose import transpose_chord, compute_target_key
from backend.chords.key_detect import infer_key
from backend.overlay.render import render_overlay

logger = logging.getLogger(__name__)

# Maximum upload size in bytes (20 MB).
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

# Valid target key names for enharmonic spelling.
_VALID_KEYS = frozenset({
    "C", "C#", "Db", "D", "D#", "Eb", "E", "F",
    "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B",
})


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-load the OCR model so the first /detect request doesn't pay the
    # ~20s cold-start penalty from lazy model initialisation.
    get_ocr()
    yield


app = FastAPI(title="transchord", version="0.1.0", lifespan=lifespan)


def _validate_params(
    semitones: int,
    target_key: str | None = None,
    original_key: str | None = None,
) -> None:
    """Validate common request parameters; raise HTTPException on failure."""
    if not (-11 <= semitones <= 11):
        raise HTTPException(
            status_code=422,
            detail=f"semitones must be between -11 and 11, got {semitones}",
        )
    if target_key is not None and target_key not in _VALID_KEYS:
        raise HTTPException(
            status_code=422,
            detail=f"target_key must be one of {sorted(_VALID_KEYS)}, got {target_key!r}",
        )
    if original_key is not None and original_key not in _VALID_KEYS:
        raise HTTPException(
            status_code=422,
            detail=f"original_key must be one of {sorted(_VALID_KEYS)}, got {original_key!r}",
        )


def _resolve_keys(
    items: list[dict],
    semitones: int,
    original_key: str | None = None,
    target_key: str | None = None,
) -> tuple[str | None, str | None]:
    """Resolve original and target keys from detected chords.

    Auto-detects original_key from chord roots if not provided.
    Auto-computes target_key from original_key + semitones if not provided.
    Explicit overrides take precedence over auto-detection.
    """
    if original_key is None:
        original_key = infer_key(items)
    if target_key is None and original_key is not None:
        target_key = compute_target_key(original_key, semitones)
    return original_key, target_key


def _build_chord_item(item: dict, semitones: int, target_key: str | None) -> dict:
    """Build a chord response dict from a raw detection item."""
    transposed: str | None = None
    try:
        chord = parse_chord(item["text"])
        transposed = transpose_chord(chord, semitones, target_key=target_key)
    except (ValueError, KeyError):
        logger.debug("Could not transpose %r: skipping", item["text"])

    raw_bbox = item.get("bbox")
    return {
        "text":       item["text"],
        "transposed": transposed,
        "confidence": float(item["confidence"]),
        "bbox":       [int(v) for v in raw_bbox] if raw_bbox is not None else None,
    }


async def _read_upload(image: UploadFile) -> bytes:
    """Read and validate uploaded image bytes; raise HTTPException if too large."""
    data = await image.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large ({len(data)} bytes). "
                   f"Maximum is {MAX_UPLOAD_BYTES} bytes.",
        )
    return data


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/detect")
async def detect(
    image: UploadFile = File(...),
    semitones: int = Form(0),
    target_key: Optional[str] = Form(None),
    original_key: Optional[str] = Form(None),
) -> dict:
    """Detect chord symbols in *image*, transpose by *semitones*, return JSON.

    Parameters
    ----------
    image        : JPEG or PNG sheet music image.
    semitones    : Semitone shift applied to every detected chord (-11 to +11).
    target_key   : Optional override for enharmonic spelling preference.
                   When omitted, auto-computed from the detected original key.
    original_key : Optional override for the original key of the song.
                   When omitted, auto-detected from the chord progression.
    """
    _validate_params(semitones, target_key, original_key)

    data = await _read_upload(image)
    suffix = os.path.splitext(image.filename or "upload.png")[1] or ".png"

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        items, raw_meta = detect_chords_hybrid(tmp_path)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    original_key, target_key = _resolve_keys(
        items, semitones, original_key, target_key,
    )
    chords = [_build_chord_item(item, semitones, target_key) for item in items]

    # Return a small, JSON-safe subset of the pipeline metadata.
    gate = raw_meta.get("gate") or {}
    meta = {
        "crop_mode":   raw_meta.get("crop_mode"),
        "num_regions": raw_meta.get("num_regions"),
        "predict_ms":  raw_meta.get("predict_ms"),
        "gate_pass":   gate.get("pass"),
        "ai_used":     raw_meta.get("ai_used", False),
    }

    return {
        "chords":      chords,
        "count":       len(chords),
        "semitones":   semitones,
        "original_key": original_key,
        "target_key":  target_key,
        "meta":        meta,
    }


@app.post("/overlay")
async def overlay(
    image: UploadFile = File(...),
    semitones: int = Form(0),
    target_key: Optional[str] = Form(None),
    original_key: Optional[str] = Form(None),
    mode: str = Form("above"),
) -> StreamingResponse:
    """Detect chords, transpose, render overlay, return PNG image.

    Parameters
    ----------
    image        : JPEG or PNG sheet music image.
    semitones    : Semitone shift applied to every detected chord (-11 to +11).
    target_key   : Optional override for enharmonic spelling preference.
                   When omitted, auto-computed from the detected original key.
    original_key : Optional override for the original key of the song.
                   When omitted, auto-detected from the chord progression.
    mode         : "above"   — orange transposed chord printed above each original (default).
                   "replace" — white box over original chord, new chord on top.
    """
    _validate_params(semitones, target_key, original_key)
    if mode not in ("above", "replace"):
        raise HTTPException(
            status_code=422,
            detail=f"mode must be 'above' or 'replace', got {mode!r}",
        )

    t_start = time.perf_counter()

    data = await _read_upload(image)
    suffix = os.path.splitext(image.filename or "upload.png")[1] or ".png"
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        items, _ = detect_chords_hybrid(tmp_path)
        img = Image.open(tmp_path).convert("RGB")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    original_key, target_key = _resolve_keys(
        items, semitones, original_key, target_key,
    )
    chords = [_build_chord_item(item, semitones, target_key) for item in items]

    result = render_overlay(
        img, chords, mode,
        original_key=original_key,
        target_key=target_key,
        semitones=semitones,
    )

    elapsed_ms = int((time.perf_counter() - t_start) * 1000)

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={"X-Processing-Time-Ms": str(elapsed_ms)},
    )
