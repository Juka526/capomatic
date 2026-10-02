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

import asyncio
import base64
import concurrent.futures
import contextlib
import functools
import io
import json
import logging
import math
import os
import tempfile
import threading
import time
import uuid
from collections import OrderedDict
from typing import Callable, Iterator, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from PIL import Image, ImageOps
from PIL import UnidentifiedImageError
import sentry_sdk

from backend.ocr.hybrid_detect import detect_chords_hybrid
from backend.chords.parser import parse_chord
from backend.chords.transpose import transpose_chord, compute_target_key
from backend.chords.key_detect import infer_key
from backend.overlay.render import _get_staff_systems, render_overlay
from backend.auth.auth0 import get_token_payload

logger = logging.getLogger(__name__)

def _sentry_options() -> dict:
    """Privacy-safe Sentry settings: no PII, request bodies, or local variables."""
    return {
        "environment": os.environ.get("SENTRY_ENVIRONMENT", "production"),
        "release": os.environ.get("SENTRY_RELEASE"),
        "traces_sample_rate": 0.05,
        "send_default_pii": False,
        "max_request_body_size": "never",
        "include_local_variables": False,
    }


_sentry_dsn = os.environ.get("SENTRY_DSN", "").strip()
if _sentry_dsn:
    sentry_sdk.init(dsn=_sentry_dsn, **_sentry_options())

# Maximum upload size in bytes (20 MB).
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_UPLOAD_PIXELS = 50_000_000
MAX_OCR_IN_FLIGHT = 2
MAX_RENDER_IN_FLIGHT = 4
MAX_OVERRIDE_CHORDS = 500
MAX_CHORD_TEXT_LENGTH = 32

# Valid target key names for enharmonic spelling.
_VALID_KEYS = frozenset({
    "C", "C#", "Db", "D", "D#", "Eb", "E", "F",
    "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B",
})

# ---------------------------------------------------------------------------
# Detection cache — stores OCR results + original image for /render reuse.
# ---------------------------------------------------------------------------
_MAX_CACHE = 20
_MAX_CACHE_PIXELS = 80_000_000
_detection_cache: OrderedDict[str, dict] = OrderedDict()
# Keep Paddle requests serialized, but run them off the event loop so health
# checks and other lightweight endpoints stay responsive during OCR.
_ocr_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
_render_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
# Admit at most one active OCR job and one queued job. Additional requests fail
# quickly instead of exhausting the single-replica process with an unbounded
# executor queue.
_ocr_admission = threading.BoundedSemaphore(MAX_OCR_IN_FLIGHT)
_render_admission = threading.BoundedSemaphore(MAX_RENDER_IN_FLIGHT)


def _cache_put(detection_id: str, data: dict) -> None:
    _detection_cache[detection_id] = data
    _detection_cache.move_to_end(detection_id)
    while (
        len(_detection_cache) > _MAX_CACHE
        or sum(
            entry["img"].width * entry["img"].height
            for entry in _detection_cache.values()
            if entry.get("img") is not None
        ) > _MAX_CACHE_PIXELS
    ):
        _detection_cache.popitem(last=False)


def _cache_get(detection_id: str) -> dict | None:
    if detection_id in _detection_cache:
        _detection_cache.move_to_end(detection_id)
        return _detection_cache[detection_id]
    return None


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Capomatic", version="1.0.0")

_cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins.split(",")],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
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


def _build_chord_item(
    item: dict, semitones: int, target_key: str | None, original_key: str | None = None,
) -> dict:
    """Build a chord response dict from a raw detection item."""
    transposed: str | None = None
    try:
        chord = parse_chord(item["text"])
        transposed = transpose_chord(chord, semitones, target_key=target_key, original_key=original_key)
    except (ValueError, KeyError):
        logger.debug("Could not transpose %r: skipping", item["text"])

    style = item.get("style")
    parenthesis = style.get("parenthesis") if isinstance(style, dict) else None
    if transposed is not None and parenthesis in {"open", "both"}:
        transposed = f"({transposed}"
    if transposed is not None and parenthesis in {"close", "both"}:
        transposed = f"{transposed})"

    raw_bbox = item.get("bbox")
    return {
        "text":       item["text"],
        "transposed": transposed,
        "confidence": float(item["confidence"]),
        "bbox":       [int(v) for v in raw_bbox] if raw_bbox is not None else None,
        "style":      style,
    }


def _build_detect_chord(item: dict) -> dict:
    raw_bbox = item.get("bbox")
    return {
        "text":       item["text"],
        "confidence": float(item["confidence"]),
        "bbox":       [int(v) for v in raw_bbox] if raw_bbox is not None else None,
        "style":      item.get("style"),
    }


def _parse_chords_override(value: str, image_size: tuple[int, int]) -> list[dict]:
    """Validate user-edited chords before sending them to the renderer."""
    try:
        raw = json.loads(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid chord corrections.") from exc
    if not isinstance(raw, list) or len(raw) > MAX_OVERRIDE_CHORDS:
        raise HTTPException(status_code=422, detail="Invalid chord corrections.")

    width, height = image_size
    items: list[dict] = []
    for row in raw:
        if not isinstance(row, dict):
            raise HTTPException(status_code=422, detail="Invalid chord corrections.")
        text = row.get("text")
        if not isinstance(text, str):
            raise HTTPException(status_code=422, detail="Invalid chord corrections.")
        text = text.strip()
        if not text or len(text) > MAX_CHORD_TEXT_LENGTH:
            raise HTTPException(status_code=422, detail="Invalid chord corrections.")
        try:
            parse_chord(text)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid chord corrections.") from exc

        raw_bbox = row.get("bbox")
        bbox: list[int] | None = None
        if raw_bbox is not None:
            if (
                not isinstance(raw_bbox, list)
                or len(raw_bbox) != 4
                or any(
                    isinstance(coordinate, bool)
                    or not isinstance(coordinate, (int, float))
                    or not math.isfinite(coordinate)
                    for coordinate in raw_bbox
                )
            ):
                raise HTTPException(status_code=422, detail="Invalid chord corrections.")
            x1, y1, x2, y2 = (round(coordinate) for coordinate in raw_bbox)
            if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
                raise HTTPException(status_code=422, detail="Invalid chord corrections.")
            bbox = [x1, y1, x2, y2]

        item = {"text": text, "confidence": 1.0, "bbox": bbox}
        # Only the parenthesis marker round-trips; other style keys are
        # renderer-internal and must not be client-controlled.
        style = row.get("style")
        if style is not None:
            if not isinstance(style, dict):
                raise HTTPException(status_code=422, detail="Invalid chord corrections.")
            parenthesis = style.get("parenthesis")
            if parenthesis not in {None, "open", "close", "both"}:
                raise HTTPException(status_code=422, detail="Invalid chord corrections.")
            if parenthesis:
                item["style"] = {"parenthesis": parenthesis}
        items.append(item)
    return items


async def _read_upload(image: UploadFile) -> bytes:
    """Read and validate uploaded image bytes; raise HTTPException if too large."""
    data = await image.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large ({len(data)} bytes). "
                   f"Maximum is {MAX_UPLOAD_BYTES} bytes.",
        )
    try:
        with Image.open(io.BytesIO(data)) as decoded:
            if decoded.format not in {"PNG", "JPEG"}:
                raise HTTPException(status_code=422, detail="Upload a PNG or JPEG image.")
            if getattr(decoded, "is_animated", False):
                raise HTTPException(status_code=422, detail="Animated images are not supported.")
            if decoded.width * decoded.height > MAX_UPLOAD_PIXELS:
                raise HTTPException(status_code=413, detail="Image dimensions are too large.")
            decoded.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(status_code=422, detail="Upload a valid PNG or JPEG image.") from exc
    return data


@contextlib.contextmanager
def _temporary_upload(data: bytes) -> Iterator[str]:
    """Expose validated upload bytes as a temp file with EXIF orientation applied."""
    suffix = ".png" if data.startswith(b"\x89PNG\r\n\x1a\n") else ".jpg"
    tmp_path: str | None = None
    try:
        with Image.open(io.BytesIO(data)) as decoded:
            orientation = decoded.getexif().get(274, 1)
            if orientation != 1:
                suffix = ".png"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp_path = tmp.name
                ImageOps.exif_transpose(decoded).convert("RGB").save(tmp_path, format="PNG")
            else:
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(data)
                    tmp_path = tmp.name
        yield tmp_path
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


async def _run_ocr(
    runner: Callable[[], tuple[list[dict], dict]],
) -> tuple[list[dict], dict]:
    """Run one admitted OCR job without blocking the event loop."""
    return await asyncio.get_running_loop().run_in_executor(_ocr_executor, runner)


@contextlib.contextmanager
def _admit_ocr() -> Iterator[None]:
    """Bound upload decoding, temp storage, and OCR work for one request."""
    if not _ocr_admission.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail="OCR is busy. Try again shortly.",
            headers={"Retry-After": "5"},
        )
    try:
        yield
    finally:
        _ocr_admission.release()


async def _run_render(runner: Callable[[], object]):
    """Run admitted CPU rendering without blocking lightweight endpoints."""
    if not _render_admission.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail="Rendering is busy. Try again shortly.",
            headers={"Retry-After": "2"},
        )
    try:
        return await asyncio.get_running_loop().run_in_executor(_render_executor, runner)
    finally:
        _render_admission.release()


def _render_requested_modes(
    img: Image.Image,
    chords: list[dict],
    mode: str,
    original_key: str | None,
    target_key: str | None,
    semitones: int,
) -> tuple[str | None, str | None]:
    replace_b64 = (
        _render_to_base64(img, chords, "replace", original_key, target_key, semitones)
        if mode in {"replace", "both"} else None
    )
    above_b64 = (
        _render_to_base64(img, chords, "above", original_key, target_key, semitones)
        if mode in {"above", "both"} else None
    )
    return replace_b64, above_b64


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


@app.get("/")
def root() -> dict:
    return {"status": "ok", "service": "capomatic"}


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
    request_started = time.perf_counter()
    if original_key is not None and original_key not in _VALID_KEYS:
        raise HTTPException(
            status_code=422,
            detail=f"original_key must be one of {sorted(_VALID_KEYS)}, got {original_key!r}",
        )
    if ocr_engine != "paddle":
        raise HTTPException(
            status_code=422,
            detail="Only PaddleOCR is available in v1.",
        )

    with _admit_ocr():
        data = await _read_upload(image)
        with _temporary_upload(data) as tmp_path:
            runner = functools.partial(
                detect_chords_hybrid,
                tmp_path,
                use_ai_fallback=False,
            )
            items, raw_meta = await _run_ocr(runner)
            with Image.open(tmp_path) as uploaded:
                img = uploaded.convert("RGB")
            _get_staff_systems(img)

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
        "stitched":    raw_meta.get("stitched"),
        "predict_calls": raw_meta.get("predict_calls"),
        "predict_ms":  raw_meta.get("predict_ms"),
        "total_ms":    raw_meta.get("total_ms"),
        "title_predict_ms": raw_meta.get("title_predict_ms"),
        "det_model_variant": raw_meta.get("det_model_variant"),
        "det_model_name": raw_meta.get("det_model_name"),
        "mkldnn_enabled": raw_meta.get("mkldnn_enabled"),
        "service_ms":  round((time.perf_counter() - request_started) * 1000, 1),
        "gate_pass":   gate.get("pass"),
        "ai_used":     raw_meta.get("ai_used", False),
        "gpt_used":    raw_meta.get("gpt_used", False),
        "gpt_crop_ms": raw_meta.get("gpt_crop_ms"),
        "gpt_gap_ms":  raw_meta.get("gpt_gap_ms"),
        "high_recall_predict_ms": raw_meta.get("high_recall_predict_ms"),
        "parallel_refinement": raw_meta.get("parallel_refinement", False),
    }

    return {
        "detection_id": detection_id,
        "song_title":   raw_meta.get("song_title") or "알수없음",
        "chords":       chords,
        "count":        len(chords),
        "original_key": original_key,
        "meta":         meta,
    }


@app.post("/detect/refine")
async def refine_detection(
    detection_id: str = Form(...),
) -> dict:
    """Retired V1 endpoint: paid refinement is not available."""
    raise HTTPException(status_code=410, detail="GPT refinement is unavailable in v1.")


@app.post("/render")
async def render(
    detection_id: str = Form(...),
    semitones: int = Form(0),
    mode: str = Form("both"),
    chords_override: Optional[str] = Form(None),
) -> dict:
    """Transpose and render overlay image(s) from a cached detection.

    Parameters
    ----------
    detection_id    : ID returned by ``/detect``.
    semitones       : Semitone shift applied to every detected chord (-11 to 11).
    mode            : "replace", "above", or "both" (default).
    chords_override : Optional JSON array of manually edited chords
                      ``[{"text": "Am", "bbox": [x1,y1,x2,y2]}, ...]``.
                      When provided, replaces the cached OCR items.
                      Chords with ``bbox: null`` are transposed but not rendered.
    """
    if not (-11 <= semitones <= 11):
        raise HTTPException(
            status_code=422,
            detail=f"semitones must be between -11 and 11, got {semitones}",
        )
    if mode not in {"replace", "above", "both"}:
        raise HTTPException(
            status_code=422,
            detail=f"mode must be one of: replace, above, both; got {mode!r}",
        )

    cached = _cache_get(detection_id)
    if cached is None:
        raise HTTPException(
            status_code=404,
            detail="detection_id not found — it may have expired. Please re-upload.",
        )

    if chords_override is not None:
        items = _parse_chords_override(chords_override, cached["img"].size)
    else:
        items = cached["items"]

    img = cached["img"]
    original_key = cached["original_key"]

    target_key = (
        compute_target_key(original_key, semitones) if original_key else None
    )

    chords = [_build_chord_item(item, semitones, target_key, original_key) for item in items]

    t_start = time.perf_counter()

    replace_b64, above_b64 = await _run_render(functools.partial(
        _render_requested_modes,
        img,
        chords,
        mode,
        original_key,
        target_key,
        semitones,
    ))

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

    with _admit_ocr():
        data = await _read_upload(image)
        with _temporary_upload(data) as tmp_path:
            runner = functools.partial(
                detect_chords_hybrid,
                tmp_path,
                use_ai_fallback=False,
            )
            items, _ = await _run_ocr(runner)
            with Image.open(tmp_path) as uploaded:
                img = uploaded.convert("RGB")

    original_key, target_key = _resolve_keys(
        items, semitones, original_key, target_key,
    )
    chords = [_build_chord_item(item, semitones, target_key, original_key) for item in items]

    result = await _run_render(functools.partial(
        render_overlay,
        img,
        chords,
        mode,
        original_key=original_key,
        target_key=target_key,
        semitones=semitones,
    ))

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
async def auth_me(payload: dict = Depends(get_token_payload)) -> dict:
    """Return verified Auth0 identity claims without requiring a database."""
    return {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "name": payload.get("name"),
    }


@app.get("/api/auth/admin-test")
async def auth_admin_test() -> dict:
    """Retired V1 endpoint: administrator roles are not supported."""
    raise HTTPException(status_code=410, detail="Administration is unavailable in v1.")


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@app.get("/api/admin/users")
async def admin_users() -> dict:
    """Retired V1 endpoint: no user list is exposed."""
    raise HTTPException(status_code=410, detail="Administration is unavailable in v1.")
