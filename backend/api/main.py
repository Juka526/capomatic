"""Capomatic FastAPI application.

Endpoints
---------
GET  /health          — liveness probe
POST /detect          — detect chords in an uploaded sheet image, return JSON + detection_id
POST /render          — transpose + render both overlay modes from cached detection
POST /overlay         — legacy: detect, transpose, render overlay image, return PNG

Usage
-----
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \\
      uvicorn backend.api.main:app --reload --port 8000
"""
from __future__ import annotations

import base64
import concurrent.futures
import io
import logging
import os
import tempfile
import time
import uuid
from collections import OrderedDict
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from PIL import Image

from backend.ocr.paddle_gpt_hybrid import (
    refine_paddle_items_with_gpt,
    run_ocr_paddle_gpt_hybrid,
)
from backend.ocr.hybrid_detect import detect_chords_hybrid
from backend.chords.parser import parse_chord
from backend.chords.transpose import transpose_chord, compute_target_key
from backend.chords.key_detect import infer_key
from backend.overlay.render import render_overlay
from backend.auth.auth0 import get_current_user, require_admin
from backend.db.database import get_db
from backend.db.models import User
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Maximum upload size in bytes (20 MB).
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

# Valid target key names for enharmonic spelling.
_VALID_KEYS = frozenset({
    "C", "C#", "Db", "D", "D#", "Eb", "E", "F",
    "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B",
})

# ---------------------------------------------------------------------------
# Detection cache — stores OCR results + original image for /render reuse.
# ---------------------------------------------------------------------------
_MAX_CACHE = 20
_detection_cache: OrderedDict[str, dict] = OrderedDict()


def _cache_put(detection_id: str, data: dict) -> None:
    _detection_cache[detection_id] = data
    _detection_cache.move_to_end(detection_id)
    while len(_detection_cache) > _MAX_CACHE:
        _detection_cache.popitem(last=False)


def _cache_get(detection_id: str) -> dict | None:
    if detection_id in _detection_cache:
        _detection_cache.move_to_end(detection_id)
        return _detection_cache[detection_id]
    return None


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables (idempotent) — skip if DB is unavailable.
    try:
        from backend.db.database import init_db
        await init_db()
        logger.info("Database initialized.")
    except Exception as exc:
        logger.warning("Database not available, auth features disabled: %s", exc)

    yield


app = FastAPI(title="Capomatic", version="0.1.0", lifespan=lifespan)

_cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    """Resolve original and target keys from detected chords."""
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
        "style":      item.get("style"),
    }


def _build_detect_chord(item: dict) -> dict:
    raw_bbox = item.get("bbox")
    return {
        "text":       item["text"],
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


def _render_to_base64(img: Image.Image, chords: list[dict], mode: str,
                      original_key: str | None, target_key: str | None,
                      semitones: int) -> str:
    """Render overlay and return as a base64-encoded PNG data URI."""
    result = render_overlay(
        img, chords, mode,
        original_key=original_key,
        target_key=target_key,
        semitones=semitones,
    )
    buf = io.BytesIO()
    result.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/detect")
async def detect(
    image: UploadFile = File(...),
    original_key: Optional[str] = Form(None),
    ocr_engine: str = Form("paddle"),
) -> dict:
    """Detect chord symbols in *image* and return raw results with a detection_id.

    The detection results and original image are cached server-side so that
    subsequent ``/render`` calls can transpose and render without re-running OCR.

    Parameters
    ----------
    image        : JPEG or PNG sheet music image.
    original_key : Optional override for the original key of the song.
                   When omitted, auto-detected from the chord progression.
    """
    if original_key is not None and original_key not in _VALID_KEYS:
        raise HTTPException(
            status_code=422,
            detail=f"original_key must be one of {sorted(_VALID_KEYS)}, got {original_key!r}",
        )
    if ocr_engine not in {"paddle", "paddle-gpt"}:
        raise HTTPException(
            status_code=422,
            detail="ocr_engine must be one of: paddle, paddle-gpt",
        )

    data = await _read_upload(image)
    suffix = os.path.splitext(image.filename or "upload.png")[1] or ".png"

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        if ocr_engine == "paddle-gpt":
            try:
                items, raw_meta = run_ocr_paddle_gpt_hybrid(tmp_path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Hybrid Paddle+GPT OCR failed; falling back to PaddleOCR: %s", exc)
                items, raw_meta = detect_chords_hybrid(tmp_path, use_ai_fallback=False)
        else:
            items, raw_meta = detect_chords_hybrid(tmp_path, use_ai_fallback=False)
        img = Image.open(tmp_path).convert("RGB")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if original_key is None:
        original_key = infer_key(items)

    detection_id = uuid.uuid4().hex
    _cache_put(detection_id, {
        "items": items,
        "img": img,
        "original_key": original_key,
        "meta": raw_meta,
    })

    chords = [_build_detect_chord(item) for item in items]

    gate = raw_meta.get("gate") or {}
    meta = {
        "ocr_engine":  raw_meta.get("ocr_engine", ocr_engine),
        "crop_mode":   raw_meta.get("crop_mode"),
        "num_regions": raw_meta.get("num_regions"),
        "predict_ms":  raw_meta.get("predict_ms"),
        "gate_pass":   gate.get("pass"),
        "ai_used":     raw_meta.get("ai_used", False),
    }

    return {
        "detection_id": detection_id,
        "chords":       chords,
        "count":        len(chords),
        "original_key": original_key,
        "meta":         meta,
    }


@app.post("/detect/refine")
async def refine_detection(
    detection_id: str = Form(...),
) -> dict:
    """Refine cached Paddle detections with GPT without re-running PaddleOCR."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="GPT hybrid refinement is not configured: OPENAI_API_KEY is not set.",
        )

    cached = _cache_get(detection_id)
    if cached is None:
        raise HTTPException(
            status_code=404,
            detail="detection_id not found — it may have expired. Please re-upload.",
        )

    items = cached["items"]
    img = cached["img"]
    try:
        refined_items, raw_meta = refine_paddle_items_with_gpt(
            img,
            items,
            base_meta=cached.get("meta"),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cached GPT refinement failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"GPT refinement failed: {exc}") from exc

    cached["items"] = refined_items
    cached["meta"] = raw_meta
    if cached.get("original_key") is None:
        cached["original_key"] = infer_key(refined_items)

    chords = [_build_detect_chord(item) for item in refined_items]
    return {
        "detection_id": detection_id,
        "chords":       chords,
        "count":        len(chords),
        "original_key": cached.get("original_key"),
        "meta": {
            "ocr_engine": raw_meta.get("ocr_engine", "paddle-gpt-hybrid"),
            "gpt_used": raw_meta.get("gpt_used", False),
            "gpt_error": raw_meta.get("gpt_error"),
            "gpt_text_replaced": raw_meta.get("gpt_text_replaced", 0),
            "gpt_gap_count": raw_meta.get("gpt_gap_count", 0),
            "dedupe_dropped": raw_meta.get("dedupe_dropped", 0),
            "gap_candidate_count": raw_meta.get("gap_candidate_count", 0),
            "gpt_gap_candidates_accepted": raw_meta.get("gpt_gap_candidates_accepted", 0),
            "input_tokens": raw_meta.get("input_tokens"),
            "output_tokens": raw_meta.get("output_tokens"),
            "total_ms": raw_meta.get("total_ms"),
            "reused_paddle_detection": raw_meta.get("reused_paddle_detection", True),
        },
    }


@app.post("/render")
async def render(
    detection_id: str = Form(...),
    semitones: int = Form(0),
    chords_override: Optional[str] = Form(None),
) -> dict:
    """Transpose and render both overlay modes from a cached detection.

    Parameters
    ----------
    detection_id    : ID returned by ``/detect``.
    semitones       : Semitone shift applied to every detected chord (-11 to 0).
    chords_override : Optional JSON array of manually edited chords
                      ``[{"text": "Am", "bbox": [x1,y1,x2,y2]}, ...]``.
                      When provided, replaces the cached OCR items.
                      Chords with ``bbox: null`` are transposed but not rendered.
    """
    import json as _json

    if not (-11 <= semitones <= 11):
        raise HTTPException(
            status_code=422,
            detail=f"semitones must be between -11 and 11, got {semitones}",
        )

    cached = _cache_get(detection_id)
    if cached is None:
        raise HTTPException(
            status_code=404,
            detail="detection_id not found — it may have expired. Please re-upload.",
        )

    if chords_override is not None:
        try:
            raw = _json.loads(chords_override)
            items = [
                {"text": r["text"], "confidence": 1.0, "bbox": r.get("bbox")}
                for r in raw
                if isinstance(r.get("text"), str) and r["text"].strip()
            ]
        except (ValueError, KeyError, TypeError):
            raise HTTPException(status_code=422, detail="chords_override must be a valid JSON array")
    else:
        items = cached["items"]

    img = cached["img"]
    original_key = cached["original_key"]

    target_key = (
        compute_target_key(original_key, semitones) if original_key else None
    )

    chords = [_build_chord_item(item, semitones, target_key) for item in items]

    t_start = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        fut_replace = pool.submit(
            _render_to_base64, img, chords, "replace",
            original_key, target_key, semitones,
        )
        fut_above = pool.submit(
            _render_to_base64, img, chords, "above",
            original_key, target_key, semitones,
        )
        replace_b64 = fut_replace.result()
        above_b64 = fut_above.result()

    elapsed_ms = int((time.perf_counter() - t_start) * 1000)

    return {
        "replace_image": replace_b64,
        "above_image":   above_b64,
        "original_key":  original_key,
        "target_key":    target_key,
        "semitones":     semitones,
        "render_ms":     elapsed_ms,
    }


@app.post("/overlay")
async def overlay(
    image: UploadFile = File(...),
    semitones: int = Form(0),
    target_key: Optional[str] = Form(None),
    original_key: Optional[str] = Form(None),
    mode: str = Form("above"),
) -> StreamingResponse:
    """Legacy endpoint: detect, transpose, render overlay, return PNG image.

    Parameters
    ----------
    image        : JPEG or PNG sheet music image.
    semitones    : Semitone shift applied to every detected chord (-11 to +11).
    target_key   : Optional override for enharmonic spelling preference.
    original_key : Optional override for the original key of the song.
    mode         : "above" or "replace".
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


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@app.get("/api/auth/me")
async def auth_me(user: User = Depends(get_current_user)) -> dict:
    """Return the authenticated user's profile."""
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
    }


@app.get("/api/auth/admin-test")
async def auth_admin_test(user: User = Depends(require_admin)) -> dict:
    """Test endpoint — requires admin role."""
    return {"message": "Admin access granted", "user": user.email}


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@app.get("/api/admin/users")
async def admin_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """All users (admin only)."""
    result = await db.execute(sa_select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return {
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "name": u.name,
                "role": u.role,
                "created_at": u.created_at.isoformat(),
                "last_login": u.last_login.isoformat() if u.last_login else None,
            }
            for u in users
        ],
    }
