"""transchord FastAPI application.

Endpoints
---------
GET  /health          — liveness probe
POST /detect          — detect chords in an uploaded sheet image and transpose them

Usage
-----
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \\
      uvicorn backend.api.main:app --reload --port 8000
"""
from __future__ import annotations

import os
import tempfile
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from backend.ocr.hybrid_detect import detect_chords_hybrid
from backend.chords.parser import parse_chord
from backend.chords.transpose import transpose_chord

app = FastAPI(title="transchord", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/detect")
async def detect(
    image: UploadFile = File(...),
    semitones: int = Form(0),
    target_key: Optional[str] = Form(None),
) -> dict:
    """Detect chord symbols in *image*, transpose by *semitones*, return JSON.

    Parameters
    ----------
    image       : JPEG or PNG sheet music image.
    semitones   : Semitone shift applied to every detected chord (-11 to +11).
    target_key  : Optional target key name (e.g. "F", "Bb") used to select
                  flat vs sharp enharmonic spelling in the transposed output.
                  When omitted the spelling is inferred from semitones alone.
    """
    if not (-11 <= semitones <= 11):
        raise HTTPException(
            status_code=422,
            detail=f"semitones must be between -11 and 11, got {semitones}",
        )

    # Determine file suffix for temp file so PaddleOCR receives the right format.
    suffix = os.path.splitext(image.filename or "upload.png")[1] or ".png"

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await image.read())
            tmp_path = tmp.name

        items, raw_meta = detect_chords_hybrid(tmp_path)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    chords = []
    for item in items:
        transposed: str | None = None
        try:
            chord = parse_chord(item["text"])
            transposed = transpose_chord(chord, semitones, target_key=target_key)
        except (ValueError, KeyError):
            pass

        raw_bbox = item.get("bbox")
        bbox = [int(v) for v in raw_bbox] if raw_bbox is not None else None
        chords.append({
            "text":       item["text"],
            "transposed": transposed,
            "confidence": float(item["confidence"]),
            "bbox":       bbox,
        })

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
        "chords":     chords,
        "count":      len(chords),
        "semitones":  semitones,
        "target_key": target_key,
        "meta":       meta,
    }
