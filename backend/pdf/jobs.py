"""Ephemeral, in-memory PDF analysis jobs (P2).

Ownership: a job is reachable only with its unpredictable id plus a separate
job capability; one anonymous session token may own one live job. Nothing is
persisted, and errors/logs carry fixed codes only -- never filenames, parser
messages, titles or chord text.

Concurrency: all bookkeeping runs on the event loop. Each page is ONE call in
the shared OCR executor (rasterize -> temp PNG -> preview -> detect), holding
one OCR admission permit that is released only when that thread call returns.
A running native call cannot be killed, so cancel/expiry only sets a flag; the
current page finishes, its output is discarded, and no further page starts.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import hashlib
import hmac
import io
import logging
import os
import secrets
import tempfile
import time
from dataclasses import dataclass, field
from typing import Callable

from PIL import Image

from backend.chords.key_detect import infer_key
from backend.pdf import core
from backend.pdf.core import PageInfo, PdfError

logger = logging.getLogger(__name__)

MAX_LIVE_JOBS = 2
IDLE_TTL_S = 15 * 60
HARD_TTL_S = 30 * 60
DOC_BUDGET_S = 600
MAX_JOB_BYTES = 128 * 1024 * 1024  # source + previews
PREVIEW_MAX_SIDE = 1200
ADMISSION_POLL_S = 0.5
SWEEP_INTERVAL_S = 30


class JobError(Exception):
    """Content-free failure; ``code`` and HTTP ``status`` are fixed."""

    def __init__(self, code: str, status: int, retry_after: int | None = None):
        super().__init__(code)
        self.code, self.status, self.retry_after = code, status, retry_after


def _digest(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


@dataclass
class _Page:
    info: PageInfo
    state: str = "pending"  # pending | analyzing | done
    title: str | None = None
    key: str | None = None
    chord_count: int = 0
    items: list = field(default_factory=list)  # kept for P3 grouping/render


@dataclass(eq=False)
class Job:
    id: str
    cap_hash: bytes
    session_hash: bytes
    created: float
    touched: float
    state: str = "queued"  # queued | analyzing | needs_review | failed
    stage: str = "uploading"
    error: str | None = None
    data: bytes | None = None
    pages: list[_Page] = field(default_factory=list)
    previews: dict[int, bytes] = field(default_factory=dict)
    bytes_used: int = 0
    cancel: bool = False
    removed: bool = False
    worker_running: bool = False
    task: asyncio.Task | None = None


def _analyze_page(data: bytes, index: int, detect: Callable, cancelled: Callable[[], bool]):
    """Thread body. Returns None if cancelled before OCR started."""
    _, img = core.rasterize_page(data, index)
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        img.save(path, format="PNG")
        img.thumbnail((PREVIEW_MAX_SIDE, PREVIEW_MAX_SIDE))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        img.close()
        if cancelled():
            return None
        items, meta = detect(path)
        return items, meta, buf.getvalue()
    finally:
        with contextlib.suppress(OSError):
            os.unlink(path)


class PdfJobManager:
    def __init__(self, submit: Callable[[Callable], concurrent.futures.Future],
                 detect: Callable[[str], tuple[list, dict]],
                 try_admit: Callable[[], bool], release: Callable[[], None],
                 clock: Callable[[], float] = time.monotonic):
        self._submit, self._detect = submit, detect
        self._try_admit, self._release_admit = try_admit, release
        self._clock = clock
        self._jobs: dict[str, Job] = {}  # addressable jobs
        self._live: set[Job] = set()  # jobs still holding resources
        self._sessions: dict[bytes, Job] = {}
        self._reaper: asyncio.Task | None = None

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        self._reaper = asyncio.get_running_loop().create_task(self._reap_loop())

    async def shutdown(self) -> None:
        if self._reaper:
            self._reaper.cancel()
        for job in list(self._jobs.values()):
            self.remove(job)
        tasks = [j.task for j in self._live if j.task]
        if tasks:  # native calls cannot be killed: wait for them to return
            await asyncio.wait(tasks, timeout=30)

    async def _reap_loop(self) -> None:
        while True:
            await asyncio.sleep(SWEEP_INTERVAL_S)
            self.sweep()

    def sweep(self) -> None:
        now = self._clock()
        for job in list(self._jobs.values()):
            if now - job.touched > IDLE_TTL_S or now - job.created > HARD_TTL_S:
                self.remove(job)

    # -- ownership / admission --------------------------------------------

    def reserve(self, session_token: str | None) -> tuple[Job, str, str | None]:
        """Reserve a slot BEFORE the upload is read. Returns (job, job_cap, new_session)."""
        self.sweep()
        new_session = None
        if session_token is None:
            session_token = new_session = secrets.token_urlsafe(32)
        session_hash = _digest(session_token)
        if session_hash in self._sessions:
            raise JobError("pdf_session_busy", 409)
        if len(self._live) >= MAX_LIVE_JOBS:
            raise JobError("pdf_busy", 429, retry_after=15)
        cap = secrets.token_urlsafe(32)
        now = self._clock()
        job = Job(secrets.token_urlsafe(16), _digest(cap), session_hash, now, now)
        self._jobs[job.id] = job
        self._live.add(job)
        self._sessions[session_hash] = job
        return job, cap, new_session

    async def submit(self, job: Job, data: bytes) -> None:
        """Validate structure (off-loop) and start analysis; releases the slot on rejection."""
        try:
            infos = await asyncio.to_thread(core.inspect_pdf, data)
            if len(data) > MAX_JOB_BYTES:
                raise PdfError("pdf_too_large")
        except BaseException:
            self.remove(job)
            raise
        if job.removed:  # expired/shut down while validating
            raise JobError("not_found", 404)
        job.data, job.bytes_used = data, len(data)
        job.pages = [_Page(i) for i in infos]
        job.stage = "waiting_for_ocr"
        job.task = asyncio.get_running_loop().create_task(self._run(job))

    def get(self, job_id: str, cap: str | None) -> Job | None:
        self.sweep()
        job = self._jobs.get(job_id)
        # Always hash so a wrong/missing capability costs the same.
        ok = hmac.compare_digest(_digest(cap or ""), job.cap_hash if job else b"\0" * 32)
        if job is None or not ok:
            return None
        job.touched = self._clock()
        return job

    def remove(self, job: Job) -> None:
        """Cancel/expire: unaddressable now; resources freed once no thread uses them."""
        job.removed = job.cancel = True
        self._jobs.pop(job.id, None)
        if not job.worker_running:
            self._free(job)

    def _free(self, job: Job) -> None:
        job.data, job.previews = None, {}
        for p in job.pages:
            p.items = []
        self._live.discard(job)
        if self._sessions.get(job.session_hash) is job:
            del self._sessions[job.session_hash]

    # -- analysis ----------------------------------------------------------

    async def _run(self, job: Job) -> None:
        job.worker_running = True
        try:
            await self._pages(job)
        except Exception as exc:  # fixed code only; never log the message
            job.state = "failed"
            job.error = (exc.code if isinstance(exc, PdfError)
                         else "analysis_timeout" if isinstance(exc, TimeoutError) else "analysis_failed")
            logger.warning("pdf job failed: %s", job.error)
        finally:
            job.worker_running = False
            if job.removed or job.state == "failed":
                self._free(job)

    async def _pages(self, job: Job) -> None:
        start = self._clock()
        loop = asyncio.get_running_loop()
        for page in job.pages:
            while not self._try_admit():  # existing OCR admission; never bypassed
                if job.cancel:
                    return
                if self._clock() - start > DOC_BUDGET_S:
                    raise TimeoutError
                await asyncio.sleep(ADMISSION_POLL_S)
            if job.cancel:
                self._release_admit()
                return
            try:
                cf = self._submit(lambda p=page: _analyze_page(
                    job.data, p.info.index, self._detect, lambda: job.cancel))
            except BaseException:
                self._release_admit()
                raise
            # Permit returns only when the thread call itself has returned.
            cf.add_done_callback(lambda _: self._release_admit())
            job.state, job.stage, page.state = "analyzing", "detecting", "analyzing"
            result = await asyncio.wrap_future(cf, loop=loop)
            if job.cancel or result is None:
                return
            items, meta, preview = result
            if job.bytes_used + len(preview) > MAX_JOB_BYTES:
                raise PdfError("pdf_result_too_large")
            job.bytes_used += len(preview)
            job.previews[page.info.index] = preview
            title = (meta.get("song_title") or "").strip()
            page.title = title[:200] or None
            page.key = infer_key(items)
            page.chord_count, page.items, page.state = len(items), items, "done"
            if self._clock() - start > DOC_BUDGET_S and page is not job.pages[-1]:
                raise TimeoutError  # no further pages after the budget
        job.state, job.stage = "needs_review", "done"

    # -- views -------------------------------------------------------------

    def snapshot(self, job: Job) -> dict:
        done = sum(p.state == "done" for p in job.pages)
        return {
            "state": job.state,
            "stage": job.stage,
            "error": job.error,
            "pages_total": len(job.pages),
            "pages_done": done,
            "pages": [
                {"index": p.info.index, "width_pt": p.info.width_pt,
                 "height_pt": p.info.height_pt, "rotation": p.info.rotation,
                 "state": p.state, "title": p.title, "key": p.key,
                 "chord_count": p.chord_count}
                for p in job.pages
            ],
        }
