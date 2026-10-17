"""Opt-in score routes (``/api/v3/score/*``). Existing Capomatic routes are unchanged.

Operational guards, all configurable by environment:

* ``CAPOMATIC_ENABLE_OMR_V3=1`` turns the routes on (404 otherwise).
* ``CAPOMATIC_OMR_REQUIRE_AUTH`` (default ``1``): an Auth0 bearer token is
  required; OMR costs ~40-60 s of CPU per page, so it is not offered anonymously.
* ``CAPOMATIC_OMR_RATE_LIMIT`` (default ``6/3600``): conversions per caller per
  window (seconds). Callers are keyed by the token subject, or by client IP
  when auth is disabled.
* One conversion runs at a time per process; a second request gets 429.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import os
import threading
import time
import zipfile
from collections import deque
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .core import MAX_BYTES, ChordDetector, ChordOnlyRenderer, Result, ScoreError, process, validate

router = APIRouter(prefix='/api/v3/score', tags=['experimental-score'])
logger = logging.getLogger(__name__)
_slot = threading.BoundedSemaphore(1)
_bearer = HTTPBearer(auto_error=False)
_chord_detector: ChordDetector | None = None
_chord_only_renderer: ChordOnlyRenderer | None = None


def configure(*, chord_detector: ChordDetector | None,
              chord_only_renderer: ChordOnlyRenderer | None = None) -> None:
    """Let the host app supply its PaddleOCR chord detector and V1 chord-only renderer."""
    global _chord_detector, _chord_only_renderer
    _chord_detector = chord_detector
    _chord_only_renderer = chord_only_renderer


class _RateLimiter:
    """Sliding-window counter per caller, in process memory (single replica)."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _limits() -> tuple[int, float]:
        raw = os.environ.get('CAPOMATIC_OMR_RATE_LIMIT', '6/3600')
        try:
            count, window = raw.split('/')
            return max(1, int(count)), max(1.0, float(window))
        except ValueError:
            logger.error('Invalid CAPOMATIC_OMR_RATE_LIMIT=%r; using 6/3600', raw)
            return 6, 3600.0

    def check(self, key: str) -> float | None:
        """Record a hit; return seconds to wait if the caller is over the limit."""
        count, window = self._limits()
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - window:
                hits.popleft()
            if len(hits) >= count:
                return hits[0] + window - now
            hits.append(now)
            if len(self._hits) > 10_000:  # bound memory under key churn
                for k in [k for k, v in self._hits.items() if not v][:5_000]:
                    del self._hits[k]
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


rate_limiter = _RateLimiter()


async def _caller(request: Request) -> str:
    if os.environ.get('CAPOMATIC_OMR_REQUIRE_AUTH', '1') != '0':
        from backend.auth.auth0 import verify_token

        creds: HTTPAuthorizationCredentials | None = await _bearer(request)
        if creds is None:
            raise HTTPException(401, 'Login is required for score conversion')
        payload = await verify_token(creds.credentials)
        return 'sub:' + hashlib.sha256(payload['sub'].encode()).hexdigest()[:32]
    host = request.client.host if request.client else 'unknown'
    return 'ip:' + host


def _execute(data: bytes, suffix: str, semitones: int, mode: str) -> Result:
    # Hold the slot in the worker thread, not the request coroutine: cancelling
    # the HTTP request must not release it while OMR is still running.
    if not _slot.acquire(blocking=False):
        raise ScoreError('Score conversion is busy; retry shortly', 429)
    try:
        return process(data, suffix, semitones, mode, chord_detector=_chord_detector,
                       chord_only_renderer=_chord_only_renderer)
    finally:
        _slot.release()


async def _convert(request: Request, file: UploadFile, semitones: int, mode: str) -> Result:
    if os.environ.get('CAPOMATIC_ENABLE_OMR_V3') != '1':
        raise HTTPException(404, 'Score conversion is disabled')
    caller = await _caller(request)
    if mode not in ('key', 'capo'):
        raise HTTPException(422, "mode must be 'key' or 'capo'")
    if mode == 'key' and not -11 <= semitones <= 11:
        raise HTTPException(422, 'semitones must be -11..11')
    if mode == 'capo' and not -7 <= semitones <= 0:
        raise HTTPException(422, 'capo mode needs semitones -7..0 (capo N = -N)')
    suffix = Path(file.filename or '').suffix.lower()
    data = await file.read(MAX_BYTES + 1)
    try:
        validate(data, suffix)
    except ScoreError as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    wait = rate_limiter.check(caller)
    if wait is not None:
        raise HTTPException(429, 'Too many score conversions; try again later',
                            headers={'Retry-After': str(int(wait) + 1)})
    try:
        return await asyncio.to_thread(_execute, data, suffix, semitones, mode)
    except ScoreError as exc:
        # Messages are fixed strings from core; no score content or paths.
        logger.warning('OMR conversion failed: %s', exc)
        headers = {'Retry-After': '30'} if exc.status == 429 else None
        raise HTTPException(exc.status, str(exc), headers=headers) from exc
    except Exception:
        logger.exception('Unexpected OMR conversion failure')
        raise HTTPException(500, 'Score conversion failed') from None


def _headers(result: Result, filename: str) -> dict[str, str]:
    decision = result.report.get('decision') or {}
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"',
        'Cache-Control': 'no-store',
        'X-OMR-Total-Ms': str(result.stages_ms.get('total', '')),
        'X-OMR-Accuracy': 'unverified',
        'X-OMR-Review-Warnings': str(len(result.report.get('warnings', []))),
        'X-Capomatic-Mode': result.mode,
    }
    if result.mode == 'chord_only':
        # Fixed reason codes only (no user content), e.g. "preflight:staff_spacing_too_small".
        headers['X-Capomatic-Fallback-Reason'] = str(decision.get('reason', 'unknown'))[:120]
    return headers


@router.post('/transpose.pdf')
async def transpose_pdf(request: Request, file: UploadFile = File(...),
                        semitones: int = Form(0), mode: str = Form('key')):
    result = await _convert(request, file, semitones, mode)
    if result.report.get('document', {}).get('failed_pages'):
        raise HTTPException(422, 'Some pages failed conversion; request the ZIP for per-page results.')
    name = 'chord-only.pdf' if result.mode == 'chord_only' else 'transposed.pdf'
    return Response(result.pdf, media_type='application/pdf', headers=_headers(result, name))


@router.post('/transpose.zip')
async def transpose_zip(request: Request, file: UploadFile = File(...),
                        semitones: int = Form(0), mode: str = Form('key')):
    """PDF, editable MusicXML (recognised and transposed) and a conversion report."""
    result = await _convert(request, file, semitones, mode)
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        if result.pages:
            z.writestr('transposed.pdf', result.pdf)
            for number, page in enumerate(result.pages, 1):
                if page is None:
                    continue
                prefix = f'page-{number:03d}'
                z.writestr(prefix + '-' + page.mode + '.pdf', page.pdf)
                if page.musicxml is not None:
                    z.writestr(prefix + '-transposed.musicxml', page.musicxml)
                    z.writestr(prefix + '-recognized.musicxml', page.recognized_musicxml)
                if page.png is not None:
                    z.writestr(prefix + '-chord-only.png', page.png)
        elif result.mode == 'chord_only':
            z.writestr('chord-only.pdf', result.pdf)
            if result.png:
                z.writestr('chord-only.png', result.png)
        else:
            z.writestr('transposed.pdf', result.pdf)
            z.writestr('transposed.musicxml', result.musicxml)
            z.writestr('recognized.musicxml', result.recognized_musicxml)
        z.writestr('conversion-report.json', json.dumps({
            'semitones': semitones, 'mode': mode, 'result_mode': result.mode,
            'stages_ms': result.stages_ms, **result.report,
        }, ensure_ascii=False, indent=2))
    return Response(output.getvalue(), media_type='application/zip',
                    headers=_headers(result, 'capomatic-score-results.zip'))
