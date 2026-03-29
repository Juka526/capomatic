"""transchord FastAPI application.

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

from backend.ocr.hybrid_detect import detect_chords_hybrid
from backend.ocr.paddle_ocr import get_ocr
from backend.chords.parser import parse_chord
from backend.chords.transpose import transpose_chord, compute_target_key
from backend.chords.key_detect import infer_key
from backend.overlay.render import render_overlay
from backend.auth.auth0 import get_current_user, require_admin
from backend.db.database import get_db
from backend.db.models import User, Job
from sqlalchemy import func, select as sa_select, text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.jobs import (
    create_job, update_job_completed, update_job_failed,
    get_user_jobs, soft_delete_job,
)
from backend.storage.manager import get_storage_manager

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
    # Pre-load the OCR model so the first /detect request doesn't pay the
    # ~20s cold-start penalty from lazy model initialisation.
    get_ocr()

    # Create database tables (idempotent) — skip if DB is unavailable.
    try:
        from backend.db.database import init_db
        await init_db()
        logger.info("Database initialized.")
    except Exception as exc:
        logger.warning("Database not available, auth/jobs features disabled: %s", exc)

    yield


app = FastAPI(title="transchord", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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

    data = await _read_upload(image)
    suffix = os.path.splitext(image.filename or "upload.png")[1] or ".png"
    storage = get_storage_manager()
    image_hash = storage.compute_hash(data)

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        items, raw_meta = detect_chords_hybrid(tmp_path)
        img = Image.open(tmp_path).convert("RGB")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if original_key is None:
        original_key = infer_key(items)

    # Cache detection results + image for /render.
    detection_id = uuid.uuid4().hex
    _cache_put(detection_id, {
        "items": items,
        "img": img,
        "original_key": original_key,
        "image_hash": image_hash,
    })

    # Build chord list (no transposition — raw detection only).
    chords = []
    for item in items:
        raw_bbox = item.get("bbox")
        chords.append({
            "text":       item["text"],
            "confidence": float(item["confidence"]),
            "bbox":       [int(v) for v in raw_bbox] if raw_bbox is not None else None,
        })

    gate = raw_meta.get("gate") or {}
    meta = {
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


@app.post("/render")
async def render(
    detection_id: str = Form(...),
    semitones: int = Form(0),
) -> dict:
    """Transpose and render both overlay modes from a cached detection.

    Parameters
    ----------
    detection_id : ID returned by ``/detect``.
    semitones    : Semitone shift applied to every detected chord (-11 to 0).
    """
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

    items = cached["items"]
    img = cached["img"]
    original_key = cached["original_key"]
    image_hash = cached.get("image_hash")

    target_key = (
        compute_target_key(original_key, semitones) if original_key else None
    )

    # Filesystem cache: check if both modes already rendered.
    storage = get_storage_manager()
    replace_path = storage.check_cache(image_hash, semitones, "replace") if image_hash else None
    above_path = storage.check_cache(image_hash, semitones, "above") if image_hash else None

    if replace_path and above_path:
        replace_bytes = await storage.get_output(replace_path)
        above_bytes = await storage.get_output(above_path)
        return {
            "replace_image": f"data:image/png;base64,{base64.b64encode(replace_bytes).decode()}",
            "above_image":   f"data:image/png;base64,{base64.b64encode(above_bytes).decode()}",
            "original_key":  original_key,
            "target_key":    target_key,
            "semitones":     semitones,
            "render_ms":     0,
            "cached":        True,
        }

    chords = [_build_chord_item(item, semitones, target_key) for item in items]

    t_start = time.perf_counter()

    # Render both modes in parallel.
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

    # Save rendered outputs to filesystem for future cache hits.
    if image_hash:
        try:
            # Strip "data:image/png;base64," prefix before decoding
            replace_raw = replace_b64.split(",", 1)[1] if "," in replace_b64 else replace_b64
            above_raw = above_b64.split(",", 1)[1] if "," in above_b64 else above_b64
            await storage.save_output(image_hash, semitones, "replace", base64.b64decode(replace_raw))
            await storage.save_output(image_hash, semitones, "above", base64.b64decode(above_raw))
        except Exception as exc:
            logger.warning("Failed to save render cache: %s", exc)

    return {
        "replace_image": replace_b64,
        "above_image":   above_b64,
        "original_key":  original_key,
        "target_key":    target_key,
        "semitones":     semitones,
        "render_ms":     elapsed_ms,
        "cached":        False,
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
# Auth test endpoints
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
# Protected endpoints (authenticated, with job tracking + cache)
# ---------------------------------------------------------------------------

@app.post("/api/overlay")
async def api_overlay(
    image: UploadFile = File(...),
    semitones: int = Form(0),
    target_key: Optional[str] = Form(None),
    original_key: Optional[str] = Form(None),
    mode: str = Form("above"),
    song_name: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Authenticated overlay: detect, transpose, render, track job, cache result."""
    _validate_params(semitones, target_key, original_key)
    if mode not in ("above", "replace"):
        raise HTTPException(
            status_code=422,
            detail=f"mode must be 'above' or 'replace', got {mode!r}",
        )

    data = await _read_upload(image)
    storage = get_storage_manager()

    image_hash = storage.compute_hash(data)

    # Filesystem cache check
    cached_path = storage.check_cache(image_hash, semitones, mode)
    if cached_path:
        output_bytes = await storage.get_output(cached_path)
        job = await create_job(
            db, user.id,
            song_name=song_name,
            original_key=original_key,
            semitones=semitones,
            mode=mode,
            image_hash=image_hash,
        )
        await update_job_completed(
            db, job.id,
            output_path=cached_path,
            original_key=original_key,
            target_key=None,
            chords=None,
            detected_chords_count=0,
            processing_time_ms=0,
            from_cache=True,
        )
        return StreamingResponse(
            io.BytesIO(output_bytes),
            media_type="image/png",
            headers={"X-Cache": "HIT", "X-Job-Id": str(job.id)},
        )

    # Cache miss — full processing
    job = await create_job(
        db, user.id,
        song_name=song_name,
        original_key=original_key,
        semitones=semitones,
        mode=mode,
        image_hash=image_hash,
    )

    suffix = os.path.splitext(image.filename or "upload.png")[1] or ".png"
    tmp_path: str | None = None
    t_start = time.perf_counter()
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        items, _ = detect_chords_hybrid(tmp_path)
        img = Image.open(tmp_path).convert("RGB")

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

        processing_time_ms = int((time.perf_counter() - t_start) * 1000)

        buf = io.BytesIO()
        result.save(buf, format="PNG")
        output_bytes = buf.getvalue()

        # Persist input + output (output file = filesystem cache)
        await storage.save_input(image_hash, data)
        output_path = await storage.save_output(image_hash, semitones, mode, output_bytes)

        chords_json = [
            {"text": c["text"], "transposed": c.get("transposed"), "bbox": c.get("bbox")}
            for c in chords
        ]
        await update_job_completed(
            db, job.id,
            output_path=output_path,
            original_key=original_key,
            target_key=target_key,
            chords=chords_json,
            detected_chords_count=len(chords),
            processing_time_ms=processing_time_ms,
            from_cache=False,
        )

        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="image/png",
            headers={"X-Cache": "MISS", "X-Job-Id": str(job.id)},
        )

    except Exception as exc:
        await update_job_failed(db, job.id, str(exc))
        raise HTTPException(status_code=500, detail="Processing failed") from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.get("/api/jobs/my")
async def api_my_jobs(
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the authenticated user's job history."""
    jobs = await get_user_jobs(db, user.id, limit=limit, offset=offset)
    return {
        "jobs": [
            {
                "id": str(j.id),
                "song_name": j.song_name,
                "original_key": j.original_key,
                "target_key": j.target_key,
                "semitones": j.semitones,
                "mode": j.mode,
                "status": j.status,
                "detected_chords_count": j.detected_chords_count,
                "processing_time_ms": j.processing_time_ms,
                "from_cache": j.from_cache,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            }
            for j in jobs
        ],
        "count": len(jobs),
    }


@app.get("/api/results/{job_id}")
async def api_get_result(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Download the rendered image for a completed job (ownership check)."""
    from sqlalchemy import select as sa_select
    from backend.db.models import Job

    try:
        jid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID")

    result = await db.execute(
        sa_select(Job).where(Job.id == jid, Job.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed" or not job.output_path:
        raise HTTPException(status_code=404, detail="Result not available")

    storage = get_storage_manager()
    output_bytes = await storage.get_output(job.output_path)
    return StreamingResponse(
        io.BytesIO(output_bytes),
        media_type="image/png",
    )


@app.delete("/api/jobs/{job_id}")
async def api_delete_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Soft-delete a job (ownership check)."""
    try:
        jid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID")

    deleted = await soft_delete_job(db, jid, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@app.get("/api/admin/stats")
async def admin_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Overall statistics (admin only)."""
    total_users = await db.scalar(sa_select(func.count(User.id))) or 0
    total_jobs = await db.scalar(sa_select(func.count(Job.id))) or 0

    cached_jobs = await db.scalar(
        sa_select(func.count(Job.id)).where(Job.from_cache == True)  # noqa: E712
    ) or 0
    cache_hit_rate = round((cached_jobs / total_jobs) * 100, 1) if total_jobs else 0.0

    avg_time = await db.scalar(
        sa_select(func.avg(Job.processing_time_ms)).where(
            Job.status == "completed",
            Job.from_cache == False,  # noqa: E712
        )
    )

    return {
        "total_users": total_users,
        "total_jobs": total_jobs,
        "total_cached": cached_jobs,
        "cache_hit_rate": cache_hit_rate,
        "avg_processing_time": round(avg_time) if avg_time else 0,
    }


@app.get("/api/admin/popular")
async def admin_popular(
    limit: int = 20,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Popular songs ranking (admin only)."""
    query = text("""
        SELECT
            song_name,
            original_key,
            target_key,
            semitones,
            COUNT(*) AS request_count,
            COUNT(DISTINCT user_id) AS unique_users,
            MAX(created_at) AS last_requested
        FROM jobs
        WHERE is_deleted = false
          AND status = 'completed'
          AND song_name IS NOT NULL
        GROUP BY song_name, original_key, target_key, semitones
        ORDER BY request_count DESC
        LIMIT :limit
    """)
    result = await db.execute(query, {"limit": limit})
    songs = [
        {
            "song_name": row.song_name,
            "original_key": row.original_key,
            "target_key": row.target_key,
            "semitones": row.semitones,
            "request_count": row.request_count,
            "unique_users": row.unique_users,
            "last_requested": row.last_requested.isoformat() if row.last_requested else None,
        }
        for row in result
    ]
    return {"songs": songs}


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
