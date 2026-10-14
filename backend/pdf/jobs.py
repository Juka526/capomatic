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

Every native call (inspect or page) is counted in ``job.running`` until the
concurrent future itself finishes -- independent of the orchestrating task or
the event loop -- and resources are freed only at zero. Those completion
callbacks run on worker threads, so manager state is guarded by ``_lock``.
Only one PDF page is admitted globally at a time, and a waiting job holds no
OCR permit, so image requests keep their admission.
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
import threading
from collections import OrderedDict
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
MAX_TOMBSTONES = 8  # failed-job status shells, content-free
TOMBSTONE_TTL_S = 120


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
    running: int = 0  # native calls still executing (inspect or page)
    failed_at: float = 0.0
    gone: asyncio.Event = field(default_factory=asyncio.Event)
    task: asyncio.Task | None = None


def _analyze_page(data: bytes, index: int, detect: Callable, cancelled: Callable[[], bool]):
    """Thread body. Returns None if cancelled before OCR started."""
    _, img = core.rasterize_page(data, index)
    path = None
    try:
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
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
        img.close()
        if path:
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
        self._lock = threading.RLock()  # completion callbacks run on worker threads
        self._jobs: dict[str, Job] = {}  # addressable jobs (live or failed tombstones)
        self._live: set[Job] = set()  # jobs still holding resources
        self._sessions: dict[bytes, Job] = {}
        self._tombs: OrderedDict[str, Job] = OrderedDict()
        self._page_busy = False  # one PDF page in the OCR executor at a time
        self._inspect_pool = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_LIVE_JOBS)
        self._reaper: asyncio.Task | None = None

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        self._reaper = asyncio.get_running_loop().create_task(self._reap_loop())

    async def shutdown(self) -> None:
        if self._reaper:
            self._reaper.cancel()
        with self._lock:
            for job in list(self._jobs.values()):
                self.remove(job)
            tasks = [j.task for j in self._live if j.task and not j.task.done()]
        if tasks:  # native calls cannot be killed: wait for them to return
            await asyncio.wait(tasks, timeout=30)
        # If a call outlives this wait, its own completion callback frees the job.

    async def _reap_loop(self) -> None:
        while True:
            await asyncio.sleep(SWEEP_INTERVAL_S)
            self.sweep()

    def sweep(self) -> None:
        now = self._clock()
        with self._lock:
            for job in list(self._jobs.values()):
                if (now - job.touched > IDLE_TTL_S or now - job.created > HARD_TTL_S
                        or (job.state == "failed" and now - job.failed_at > TOMBSTONE_TTL_S)):
                    self.remove(job)

    # -- ownership / admission --------------------------------------------

    def reserve(self, session_token: str | None) -> tuple[Job, str, str | None]:
        """Reserve a slot BEFORE the upload is read. Returns (job, job_cap, new_session)."""
        self.sweep()
        new_session = None
        if session_token is None:
            session_token = new_session = secrets.token_urlsafe(32)
        session_hash = _digest(session_token)
        with self._lock:
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

    async def receive(self, job: Job, stream, limit: int) -> bytes:
        """Read the body, giving up at once if the job expires or is removed."""
        chunks: list[bytes] = []
        total = 0
        it = stream.__aiter__()
        gone = asyncio.ensure_future(job.gone.wait())
        nxt = None
        try:
            while True:
                nxt = asyncio.ensure_future(it.__anext__())
                await asyncio.wait({nxt, gone}, return_when=asyncio.FIRST_COMPLETED)
                if job.removed:
                    raise JobError("not_found", 404)
                try:
                    chunk = nxt.result()
                except StopAsyncIteration:
                    return b"".join(chunks)
                total += len(chunk)
                if total > limit:
                    raise PdfError("pdf_too_large")
                chunks.append(chunk)
        finally:
            chunks.clear()
            for t in (gone, nxt):
                if t is not None and not t.done():
                    t.cancel()

    async def submit(self, job: Job, data: bytes) -> None:
        """Validate structure (off-loop) and start analysis; the caller removes the job on error."""
        if len(data) > MAX_JOB_BYTES:
            raise PdfError("pdf_too_large")
        # The slot stays held until the native call itself returns, even if the
        # request is cancelled or the job expires meanwhile.
        cf = self._native(job, self._inspect_pool.submit, lambda: core.inspect_pdf(data))
        infos = await asyncio.wrap_future(cf)
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
        with self._lock:
            job.removed = job.cancel = True
            self._jobs.pop(job.id, None)
            self._tombs.pop(job.id, None)
            job.gone.set()
            self._maybe_free(job)

    def _maybe_free(self, job: Job) -> None:
        with self._lock:
            if job.running == 0 and (job.removed or job.state == "failed"):
                job.data, job.previews = None, {}
                for p in job.pages:
                    p.items = []
                self._live.discard(job)
                if self._sessions.get(job.session_hash) is job:
                    del self._sessions[job.session_hash]

    def _fail(self, job: Job, code: str) -> None:
        with self._lock:
            job.state, job.error, job.cancel = "failed", code, True
            job.failed_at = self._clock()
            for p in job.pages:  # a failed job serves no detected results
                p.title = p.key = None
                p.chord_count, p.items, p.state = 0, [], "pending"
            job.previews = {}
            if job.id in self._jobs:
                self._tombs[job.id] = job
                while len(self._tombs) > MAX_TOMBSTONES:
                    old, _ = self._tombs.popitem(last=False)
                    self._jobs.pop(old, None)
            self._maybe_free(job)

    def _native(self, job: Job, submit: Callable, fn: Callable,
                on_done: Callable[[], None] | None = None) -> concurrent.futures.Future:
        """Run ``fn`` on a pool; ``job.running``/``on_done`` end only when it returns."""
        with self._lock:
            job.running += 1

        def done(_=None):
            with self._lock:
                job.running -= 1
                if on_done:
                    on_done()
                self._maybe_free(job)

        try:
            cf = submit(fn)
        except BaseException:
            done()
            raise
        cf.add_done_callback(done)
        return cf

    # -- analysis ----------------------------------------------------------

    async def _run(self, job: Job) -> None:
        try:
            await self._pages(job)
        except asyncio.CancelledError:
            self._fail(job, "canceled")
            raise
        except Exception as exc:  # fixed code only; never log the message
            code = (exc.code if isinstance(exc, PdfError)
                    else "analysis_timeout" if isinstance(exc, TimeoutError) else "analysis_failed")
            logger.warning("pdf job failed: %s", code)
            self._fail(job, code)

    def _admit_page(self) -> bool:
        with self._lock:
            if self._page_busy or not self._try_admit():
                return False
            self._page_busy = True
            return True

    def _page_done(self) -> None:
        self._page_busy = False
        self._release_admit()

    async def _pages(self, job: Job) -> None:
        start = self._clock()
        loop = asyncio.get_running_loop()
        for page in job.pages:
            if self._clock() - start > DOC_BUDGET_S:  # before every new page
                raise TimeoutError
            while not self._admit_page():  # waiting holds no OCR permit
                if job.cancel:
                    return
                if self._clock() - start > DOC_BUDGET_S:
                    raise TimeoutError
                await asyncio.sleep(ADMISSION_POLL_S)
            if job.cancel:
                with self._lock:
                    self._page_done()
                return
            job.state, job.stage, page.state = "analyzing", "detecting", "analyzing"
            # Permit and page turn return only when the thread call itself has returned.
            cf = self._native(job, self._submit, lambda p=page: _analyze_page(
                job.data, p.info.index, self._detect, lambda: job.cancel), self._page_done)
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
