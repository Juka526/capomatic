"""Opt-in score routes. Existing Capomatic routes are not changed."""
from __future__ import annotations

import asyncio
import io
import logging
import os
import threading
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from .core import MAX_BYTES, ScoreError, process, validate

router = APIRouter(prefix='/api/v3/score', tags=['experimental-score'])
_slot = threading.BoundedSemaphore(1)
logger = logging.getLogger(__name__)


def _execute(data: bytes, suffix: str, semitones: int):
    # Hold the semaphore in the worker thread, not the request coroutine:
    # cancelling an HTTP request must not release the slot while OMR still runs.
    if not _slot.acquire(blocking=False):
        raise ScoreError('OMR worker busy; retry later', 429)
    try:
        return process(data, suffix, semitones)
    finally:
        _slot.release()


async def _convert(file: UploadFile, semitones: int):
    if os.environ.get('CAPOMATIC_ENABLE_OMR_V3') != '1':
        raise HTTPException(404, 'Score conversion is disabled')
    if not -11 <= semitones <= 11:
        raise HTTPException(422, 'semitones must be -11..11')
    suffix = Path(file.filename or '').suffix.lower()
    data = await file.read(MAX_BYTES + 1)
    try:
        validate(data, suffix)
        return await asyncio.to_thread(_execute, data, suffix, semitones)
    except ScoreError as exc:
        logger.warning('OMR conversion: %s', exc)
        headers = {'Retry-After': '5'} if exc.status == 429 else None
        raise HTTPException(exc.status, str(exc), headers=headers) from exc
    except Exception:
        logger.exception('Unexpected OMR conversion failure')
        raise HTTPException(500, 'Score conversion failed') from None


@router.post('/transpose.pdf')
async def transpose_pdf(file: UploadFile = File(...), semitones: int = Form(0)):
    result = await _convert(file, semitones)
    return Response(result.pdf, media_type='application/pdf', headers={
        'Content-Disposition': 'attachment; filename="transposed.pdf"',
        'Cache-Control': 'no-store',
        'X-OMR-Total-Ms': str(result.stages_ms['total']),
        'X-OMR-Accuracy': 'unverified',
    })


@router.post('/transpose.zip')
async def transpose_zip(file: UploadFile = File(...), semitones: int = Form(0)):
    """Deliver both editable MusicXML and rendered PDF from one conversion."""
    result = await _convert(file, semitones)
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('transposed.pdf', result.pdf)
        z.writestr('transposed.musicxml', result.musicxml)
        import json
        z.writestr('conversion-report.json', json.dumps({
            'semitones': semitones,
            'stages_ms': result.stages_ms,
            'accuracy': 'not_measured',
            'warning': result.warning,
        }, ensure_ascii=False, indent=2))
    return Response(output.getvalue(), media_type='application/zip', headers={
        'Content-Disposition': 'attachment; filename="capomatic-score-results.zip"',
        'Cache-Control': 'no-store',
        'X-OMR-Total-Ms': str(result.stages_ms['total']),
    })
