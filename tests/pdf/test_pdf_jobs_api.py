"""P2 behaviour: /pdf/jobs through the real app, real OCR executor and admission.

Only the Paddle call is replaced (a gated stub recording each call), and the job
manager's clock is a fake. Every bound is probed by behaviour, not by reading
constants. Inputs are hand-built PDFs from _pdf_bytes.py.
"""
import asyncio
import gc
import io
import os
import tempfile
import threading
import weakref

import httpx
import pytest
from PIL import Image

from backend.api import main
from backend.pdf import core, jobs
from _pdf_bytes import build_pdf, fill

TITLE = "SENTINEL_DETECTED_TITLE_주님"
CAP, SES = "X-PDF-Job-Capability", "X-PDF-Session"


def _pdf(n=2, size=100):
    return build_pdf([{"media": [0, 0, size, size], "content": fill((1, 0, 0), 0, 0, size, size)}
                      for _ in range(n)])


class Clock:
    def __init__(self):
        self.t = 10_000.0

    def __call__(self):
        return self.t


class Detector:
    """Stands in for Paddle; gated so tests control when a native call returns."""

    def __init__(self):
        self.calls, self.lock = [], threading.Lock()
        self.gate = threading.Event()
        self.gate.set()
        self.started = threading.Event()
        self.on_call = None
        self.raise_exc = None

    def __call__(self, path, *args, **kwargs):
        with self.lock:
            self.calls.append({"path": path, "existed": os.path.exists(path), "kwargs": kwargs})
            n = len(self.calls)
        self.started.set()
        if self.on_call:
            self.on_call(n)
        assert self.gate.wait(10), "test gate never opened"
        if self.raise_exc:
            raise self.raise_exc()  # fresh instance: no traceback kept by the test
        items = [{"text": t, "confidence": 0.9, "bbox": [1 + 4 * i, 1, 4 + 4 * i, 5]}
                 for i, t in enumerate(["C", "F", "G", "C", "Am"])]
        return items, {"song_title": TITLE}


@pytest.fixture
def env(monkeypatch):
    mgr = main._pdf_jobs
    mgr._jobs.clear(), mgr._live.clear(), mgr._sessions.clear()
    clock, det = Clock(), Detector()
    monkeypatch.setattr(mgr, "_clock", clock)
    monkeypatch.setattr(main, "detect_chords_hybrid", det)  # wiring via _detect_pdf_page kept
    monkeypatch.setattr(jobs, "ADMISSION_POLL_S", 0.01)
    temps = []
    real_mkstemp = tempfile.mkstemp

    def tracking_mkstemp(*a, **k):
        fd, path = real_mkstemp(*a, **k)
        temps.append(path)
        return fd, path
    monkeypatch.setattr(jobs.tempfile, "mkstemp", tracking_mkstemp)
    cache_before = list(main._detection_cache)
    yield types_ns(mgr=mgr, clock=clock, det=det, temps=temps)
    det.gate.set()
    main._ocr_executor.submit(lambda: None).result(15)  # let any running page finish
    # Afterwards: no temp PNG left, both OCR permits free, legacy cache untouched.
    assert [p for p in temps if os.path.exists(p)] == []
    got = [main._ocr_admission.acquire(blocking=False) for _ in range(main.MAX_OCR_IN_FLIGHT)]
    for ok in got:
        if ok:
            main._ocr_admission.release()
    assert all(got), "an OCR admission permit leaked"
    assert list(main._detection_cache) == cache_before


class types_ns:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def free_permits():
    got = [main._ocr_admission.acquire(blocking=False) for _ in range(main.MAX_OCR_IN_FLIGHT)]
    for ok in got:
        if ok:
            main._ocr_admission.release()
    return sum(got)


def run(coro):
    return asyncio.run(coro)


def client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://t")


async def until(pred, timeout=5.0):
    for _ in range(int(timeout / 0.01)):
        if pred():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition not reached")


async def wait_thread_event(ev):
    assert await asyncio.to_thread(ev.wait, 5)


async def create(c, data=None, session=None):
    headers = {SES: session} if session else {}
    return await c.post("/pdf/jobs", content=_pdf() if data is None else data, headers=headers)


async def finish(env):
    env.det.gate.set()
    await env.mgr.shutdown()


# --- happy path, capabilities, generic errors --------------------------------

def test_create_status_source_delete_roundtrip(env):
    async def go():
        async with client() as c:
            r = await create(c)
            assert r.status_code == 202 and r.headers["cache-control"] == "no-store"
            body = r.json()
            jid, cap, ses = body["job_id"], body["job_capability"], body["session_token"]
            assert len({jid, cap, ses}) == 3 and min(map(len, (cap, ses))) >= 32
            await until(lambda: env.mgr._jobs[jid].state == "needs_review")
            s = await c.get(f"/pdf/jobs/{jid}", headers={CAP: cap})
            assert s.status_code == 200 and s.headers["cache-control"] == "no-store"
            st = s.json()
            assert (st["pages_total"], st["pages_done"]) == (2, 2) and st["state"] == "needs_review"
            assert [p["key"] for p in st["pages"]] == ["C", "C"]
            src = await c.get(f"/pdf/jobs/{jid}/pages/1/source", headers={CAP: cap})
            assert src.status_code == 200 and src.headers["content-type"] == "image/jpeg"
            img = Image.open(io.BytesIO(src.content))
            assert img.format == "JPEG" and max(img.size) <= 1200 and img.size == (200, 200)
            assert img.getpixel((100, 100))[0] > 200  # the red page, not some other image
            # Wrong capability, no capability and unknown id answer identically.
            bad = [await c.get(f"/pdf/jobs/{jid}", headers={CAP: "x" * 43}),
                   await c.get(f"/pdf/jobs/{jid}"),
                   await c.get("/pdf/jobs/nope", headers={CAP: cap}),
                   await c.get(f"/pdf/jobs/{jid}", headers={CAP: ses})]  # session token is not a capability
            assert {(b.status_code, b.text, b.headers["cache-control"]) for b in bad} == {
                (404, '{"detail":{"code":"not_found"}}', "no-store")}
            d = await c.delete(f"/pdf/jobs/{jid}", headers={CAP: cap})
            assert d.status_code == 204 and d.headers["cache-control"] == "no-store"
            assert (await c.get(f"/pdf/jobs/{jid}", headers={CAP: cap})).status_code == 404
        # One Paddle call per page, image path settings (no AI fallback), temp PNG present then gone.
        assert len(env.det.calls) == 2
        assert all(c["kwargs"] == {"use_ai_fallback": False} and c["existed"] for c in env.det.calls)
        await finish(env)
    run(go())


def test_source_not_ready_and_out_of_range(env):
    async def go():
        env.det.gate.clear()
        async with client() as c:
            b = (await create(c)).json()
            h = {CAP: b["job_capability"]}
            await wait_thread_event(env.det.started)
            assert (await c.get(f"/pdf/jobs/{b['job_id']}/pages/0/source", headers=h)).status_code == 409
            for page in ("2", "-1"):
                r = await c.get(f"/pdf/jobs/{b['job_id']}/pages/{page}/source", headers=h)
                assert (r.status_code, r.json()) == (404, {"detail": {"code": "not_found"}})
            r = await c.get(f"/pdf/jobs/{b['job_id']}/pages/SENTINEL_X/source", headers=h)
            assert (r.status_code, r.text) == (422, '{"detail":{"code":"invalid_request"}}')
            assert r.headers["cache-control"] == "no-store"
        await finish(env)
    run(go())


@pytest.mark.parametrize("data, status, code", [
    (b"", 422, "pdf_empty"),
    (b"%PDF-1.4 SENTINEL_GARBAGE", 422, "pdf_corrupt"),
    (None, 413, "pdf_too_many_pages"),
])
def test_rejected_upload_frees_slot_with_fixed_code(env, data, status, code):
    async def go():
        async with client() as c:
            r = await create(c, _pdf(11) if data is None else data)
            assert (r.status_code, r.json()) == (status, {"detail": {"code": code}})
            assert "SENTINEL" not in r.text and r.headers["cache-control"] == "no-store"
            assert not env.mgr._live and not env.mgr._jobs and not env.mgr._sessions
        await finish(env)
    run(go())


def test_cors_preflight_and_no_store(env):
    async def go():
        async with client() as c:
            ok = await c.options("/pdf/jobs/x", headers={
                "Origin": "http://localhost:3000", "Access-Control-Request-Method": "DELETE",
                "Access-Control-Request-Headers": "x-pdf-job-capability,x-pdf-session"})
            assert ok.status_code == 200 and ok.headers["access-control-allow-origin"] == "http://localhost:3000"
            assert ok.headers["cache-control"] == "no-store"
            evil = await c.options("/pdf/jobs/x", headers={
                "Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
            assert "access-control-allow-origin" not in evil.headers
    run(go())


# --- reserve before read, ownership, global/session limits -------------------

class SlowBody:
    """Streaming request body that pauses after the first chunk until released."""

    def __init__(self, data, chunk=64):
        self.data, self.chunk = data, chunk
        self.release = asyncio.Event()
        self.sent = 0
        self.sent_after_release = 0

    async def __aiter__(self):
        for i in range(0, len(self.data), self.chunk):
            if i:
                await self.release.wait()
            piece = self.data[i:i + self.chunk]
            self.sent += len(piece)
            if self.release.is_set():
                self.sent_after_release += len(piece)
            yield piece


def test_global_and_session_limits_reject_before_reading(env):
    async def go():
        env.det.gate.clear()
        async with client() as c:
            a = await create(c, session="s" * 20)
            b = await create(c, session="t" * 20)
            assert a.status_code == b.status_code == 202
            for session, status, code in (("s" * 20, 409, "pdf_session_busy"),
                                          ("u" * 20, 429, "pdf_busy"), (None, 429, "pdf_busy")):
                body = SlowBody(_pdf())
                try:
                    r = await asyncio.wait_for(c.post("/pdf/jobs", content=body.__aiter__(),
                                                      headers={SES: session} if session else {}), 2)
                except TimeoutError:
                    raise AssertionError(f"accepted and reading body for session {session!r}") from None
                assert (r.status_code, r.json()["detail"]["code"]) == (status, code)
                assert body.sent <= 64, "body was read past the first chunk before rejection"
                if status == 429:
                    assert r.headers["retry-after"] == "15"
            assert len(env.mgr._live) == 2
        await finish(env)
    run(go())


def test_declared_oversize_is_rejected_without_reading(env):
    async def go():
        async with client() as c:
            body = SlowBody(b"%PDF" + b"0" * 200)
            try:
                r = await asyncio.wait_for(c.post(
                    "/pdf/jobs", content=body.__aiter__(),
                    headers={"Content-Length": str(core.MAX_PDF_BYTES + 1)}), 2)
            except TimeoutError:
                raise AssertionError("declared oversize accepted; body is being read") from None
            assert (r.status_code, r.json()["detail"]["code"]) == (413, "pdf_too_large")
            assert body.sent == 0 and not env.mgr._live
    run(go())


def test_streamed_oversize_stops_reading(env, monkeypatch):
    monkeypatch.setattr(main, "MAX_PDF_BYTES", 1000)

    async def go():
        async with client() as c:
            body = SlowBody(b"%PDF" + b"0" * 5000, chunk=300)
            body.release.set()
            r = await c.post("/pdf/jobs", content=body.__aiter__())
            assert (r.status_code, r.json()["detail"]["code"]) == (413, "pdf_too_large")
            assert body.sent <= 1200 and not env.mgr._live
    run(go())


def test_invalid_session_header(env):
    async def go():
        async with client() as c:
            for s in ("short", "x" * 129):
                r = await create(c, session=s)
                assert (r.status_code, r.text) == (422, '{"detail":{"code":"invalid_request"}}')
            assert not env.mgr._live
    run(go())


def test_cancel_keeps_slot_and_permit_until_native_call_returns(env):
    """Controlled schedule: A's page blocks; B waits (one PDF page globally); C is refused."""
    async def go():
        env.det.gate.clear()
        async with client() as c:
            a = (await create(c, session="a" * 20)).json()
            await wait_thread_event(env.det.started)
            job_a = env.mgr._jobs[a["job_id"]]
            # Known positive: A's running page holds exactly one OCR permit.
            assert free_permits() == main.MAX_OCR_IN_FLIGHT - 1
            assert (await c.delete(f"/pdf/jobs/{a['job_id']}", headers={CAP: a["job_capability"]})).status_code == 204
            assert (await c.get(f"/pdf/jobs/{a['job_id']}", headers={CAP: a["job_capability"]})).status_code == 404
            assert job_a in env.mgr._live and job_a.data is not None  # native call still running
            assert free_permits() == main.MAX_OCR_IN_FLIGHT - 1
            b = (await create(c, session="b" * 20)).json()
            job_b = env.mgr._jobs[b["job_id"]]
            body = SlowBody(_pdf())
            r = await asyncio.wait_for(c.post("/pdf/jobs", content=body.__aiter__(),
                                              headers={SES: "c" * 20}), 2)
            assert (r.status_code, r.json()["detail"]["code"]) == (429, "pdf_busy") and body.sent <= 64
            await asyncio.sleep(0.1)
            # B holds no permit while A's page runs, and has started no page.
            assert len(env.det.calls) == 1 and free_permits() == main.MAX_OCR_IN_FLIGHT - 1
            assert all(p.state == "pending" for p in job_b.pages)
            env.det.gate.set()
            await until(lambda: job_a not in env.mgr._live)
            assert job_a.data is None and job_a.previews == {} and job_a.pages[0].items == []
            assert job_a.pages[1].state == "pending"  # canceled A: one page, no result
            await until(lambda: job_b.state == "needs_review")
            st = (await c.get(f"/pdf/jobs/{b['job_id']}", headers={CAP: b["job_capability"]})).json()
            assert (st["pages_done"], st["pages_total"]) == (2, 2)
            assert len(env.det.calls) == 3  # A page 0, then B pages 0 and 1
            assert (await create(c, session="c" * 20)).status_code == 202  # A's slot is free now
        await finish(env)
    run(go())


def test_ttl_expiry_during_native_call_discards_and_stops(env):
    async def go():
        env.det.gate.clear()
        async with client() as c:
            a = (await create(c, _pdf(3))).json()
            await wait_thread_event(env.det.started)
            job = env.mgr._jobs[a["job_id"]]
            env.clock.t += jobs.IDLE_TTL_S + 1
            assert (await c.get(f"/pdf/jobs/{a['job_id']}", headers={CAP: a["job_capability"]})).status_code == 404
            assert job in env.mgr._live  # still held while the native call runs
            env.det.gate.set()
            await until(lambda: job not in env.mgr._live)
            assert len(env.det.calls) == 1 and job.previews == {}
        await finish(env)
    run(go())


# --- fairness / admission ----------------------------------------------------

def _png():
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_one_pdf_leaves_a_permit_for_images(env):
    async def go():
        env.det.gate.clear()
        async with client() as c:
            await create(c)
            await wait_thread_event(env.det.started)
            img = asyncio.create_task(c.post("/detect", files={"image": ("a.png", _png(), "image/png")}))
            await asyncio.sleep(0.2)
            env.det.gate.set()
            r = await img
            assert r.status_code == 200
            main._detection_cache.pop(r.json()["detection_id"], None)
        await finish(env)
    run(go())


def test_two_pdfs_do_not_take_every_ocr_permit(env):
    """Plan: one PDF OCR page admitted at a time; image requests retain admission."""
    async def go():
        env.det.gate.clear()
        async with client() as c:
            await create(c, session="a" * 20)
            await create(c, session="b" * 20)
            await wait_thread_event(env.det.started)
            await asyncio.sleep(0.2)  # second job polls admission meanwhile
            img = asyncio.create_task(c.post("/detect", files={"image": ("a.png", _png(), "image/png")}))
            await asyncio.sleep(0.2)
            env.det.gate.set()
            r = await img
            if r.status_code == 200:
                main._detection_cache.pop(r.json()["detection_id"], None)
            assert r.status_code != 429, "both OCR permits held by PDF jobs; image request refused"
        await finish(env)
    run(go())


def test_pages_rasterize_sequentially_within_pixel_bound(env, monkeypatch):
    live, state = [], {"active": 0, "max": 0, "max_live": 0, "max_px": 0}
    lock = threading.Lock()
    real = core.rasterize_page

    def spy(data, index, scale=None):
        with lock:
            state["active"] += 1
            state["max"] = max(state["max"], state["active"])
            state["max_live"] = max(state["max_live"], sum(r() is not None for r in live))
        try:
            info, img = real(data, index, scale)
            live.append(weakref.ref(img))
            state["max_px"] = max(state["max_px"], img.width * img.height)
            return info, img
        finally:
            with lock:
                state["active"] -= 1
    monkeypatch.setattr(jobs.core, "rasterize_page", spy)

    async def go():
        async with client() as c:
            a = (await create(c, build_pdf([{"media": [0, 0, 2000, 4000]}] * 2), session="a" * 20)).json()
            b = (await create(c, _pdf(3), session="b" * 20)).json()
            await until(lambda: all(env.mgr._jobs[j].state == "needs_review"
                                    for j in (a["job_id"], b["job_id"])))
        await finish(env)
    run(go())
    gc.collect()
    assert state["max"] == 1 and state["max_live"] <= 1
    assert 0 < state["max_px"] <= core.MAX_RASTER_PIXELS


# --- budgets ------------------------------------------------------------------

def test_document_budget_stops_next_page(env):
    env.det.on_call = lambda n: setattr(env.clock, "t", env.clock.t + jobs.DOC_BUDGET_S + 1)

    async def go():
        async with client() as c:
            b = (await create(c, _pdf(3))).json()
            await until(lambda: env.mgr._jobs[b["job_id"]].state == "failed")
            st = (await c.get(f"/pdf/jobs/{b['job_id']}", headers={CAP: b["job_capability"]})).json()
            assert st["error"] == "analysis_timeout" and len(env.det.calls) == 1
        await finish(env)
    run(go())


def test_budget_expires_while_waiting_for_admission(env):
    async def go():
        held = [main._ocr_admission.acquire(blocking=False) for _ in range(main.MAX_OCR_IN_FLIGHT)]
        try:
            async with client() as c:
                b = (await create(c)).json()
                await asyncio.sleep(0.05)
                env.clock.t += jobs.DOC_BUDGET_S + 1
                await until(lambda: env.mgr._jobs[b["job_id"]].state == "failed")
                assert env.mgr._jobs[b["job_id"]].error == "analysis_timeout" and env.det.calls == []
        finally:
            for ok in held:
                if ok:
                    main._ocr_admission.release()
        await finish(env)
    run(go())


def test_job_byte_budget_counts_previews(env, monkeypatch):
    async def go():
        data = _pdf(3)
        monkeypatch.setattr(jobs, "MAX_JOB_BYTES", len(data) + 1500)  # room for ~1 preview
        async with client() as c:
            b = (await create(c, data)).json()
            await until(lambda: env.mgr._jobs[b["job_id"]].state == "failed")
            job = env.mgr._jobs[b["job_id"]]
            assert job.error == "pdf_result_too_large" and job.previews == {}
            monkeypatch.setattr(jobs, "MAX_JOB_BYTES", len(data) - 1)
            r = await create(c, data)
            assert (r.status_code, r.json()["detail"]["code"]) == (413, "pdf_too_large")
        await finish(env)
    run(go())


# --- failure cleanup ------------------------------------------------------------

def test_failed_job_clears_source_results_and_detected_metadata(env):
    """Plan: delete stored source/results on failure (detected titles are results)."""
    async def go():
        # page 0 analyses; page 1 passes inspection but cannot be rasterized.
        data = build_pdf([{"media": [0, 0, 100, 100]}, {"media": [0, 0, 14400, 14400]}])
        async with client() as c:
            b = (await create(c, data)).json()
            await until(lambda: env.mgr._jobs[b["job_id"]].state == "failed")
            job = env.mgr._jobs[b["job_id"]]
            assert job.error == "pdf_page_too_large"
            assert job.data is None and job.previews == {} and all(p.items == [] for p in job.pages)
            st = (await c.get(f"/pdf/jobs/{b['job_id']}", headers={CAP: b["job_capability"]})).text
            assert TITLE not in st, "detected title retained and served after failure"
        await finish(env)
    run(go())


@pytest.mark.parametrize("where", ["png", "jpeg", "mkstemp", "detect"])
def test_page_errors_release_image_and_temp_file(env, monkeypatch, where):
    rasters = []
    real_raster = core.rasterize_page

    def spy(*a, **k):
        info, img = real_raster(*a, **k)
        rasters.append(weakref.ref(img))
        return info, img
    monkeypatch.setattr(jobs.core, "rasterize_page", spy)
    if where in ("png", "jpeg"):
        real_save = Image.Image.save

        def save(self, fp, format=None, **kw):
            if (format or "").upper() == where.upper():
                raise OSError("SENTINEL_DISK")
            return real_save(self, fp, format=format, **kw)
        monkeypatch.setattr(Image.Image, "save", save)
    elif where == "mkstemp":
        def boom(*a, **k):
            raise OSError("SENTINEL_TMP")
        monkeypatch.setattr(jobs.tempfile, "mkstemp", boom)
    else:
        env.det.raise_exc = lambda: RuntimeError("SENTINEL_PADDLE")

    async def go():
        async with client() as c:
            b = (await create(c)).json()
            await until(lambda: env.mgr._jobs[b["job_id"]].state == "failed")
            st = (await c.get(f"/pdf/jobs/{b['job_id']}", headers={CAP: b["job_capability"]})).json()
            assert st["error"] == "analysis_failed" and "SENTINEL" not in str(st)
        await finish(env)
    run(go())
    gc.collect()
    assert rasters and all(r() is None for r in rasters)


# --- upload/validation vs TTL sweep -------------------------------------------

def test_ttl_sweep_does_not_free_a_slot_still_uploading(env):
    async def go():
        env.det.gate.clear()
        async with client() as c:
            body = SlowBody(_pdf(), chunk=64)
            up = asyncio.create_task(c.post("/pdf/jobs", content=body.__aiter__(), headers={SES: "a" * 20}))
            await until(lambda: len(env.mgr._live) == 1)
            env.clock.t += jobs.IDLE_TTL_S + 1
            await c.get("/pdf/jobs/none")  # any call sweeps
            new = [await create(c, session=s * 20) for s in "bc"]
            holders = len(env.mgr._live) + (0 if up.done() else 1)
            body.release.set()
            r = await up
            issues = []
            if holders > jobs.MAX_LIVE_JOBS:
                issues.append(f"{holders} uploads/jobs holding resources")
            if body.sent_after_release:
                issues.append(f"expired upload kept being read: {body.sent_after_release} more bytes")
            assert not issues, issues
            assert r.status_code == 404 and all(n.status_code == 202 for n in new)
        await finish(env)
    run(go())


def test_ttl_sweep_does_not_free_a_slot_still_validating(env, monkeypatch):
    """A's native inspect is latched; expiry must keep A's slot until that call returns."""
    gate, started = threading.Event(), threading.Event()
    real = core.inspect_pdf
    latched = []

    def inspect(data):
        if not latched:
            latched.append(1)
            started.set()
            assert gate.wait(10)
        return real(data)
    monkeypatch.setattr(jobs.core, "inspect_pdf", inspect)

    def holders():
        return {j.id for j in env.mgr._live} | {j.id for j in env.mgr._jobs.values() if j.running}

    async def go():
        env.det.gate.clear()
        async with client() as c:
            up = asyncio.create_task(create(c, session="a" * 20))
            await wait_thread_event(started)
            job_a = next(iter(env.mgr._live))
            env.clock.t += jobs.IDLE_TTL_S + 1
            await c.get("/pdf/jobs/none")  # sweep: A expires while its inspect still runs
            assert job_a.removed and job_a.running == 1 and job_a in env.mgr._live
            b = await create(c, session="b" * 20)
            assert b.status_code == 202
            body = SlowBody(_pdf())
            r = await asyncio.wait_for(c.post("/pdf/jobs", content=body.__aiter__(),
                                              headers={SES: "c" * 20}), 2)
            assert (r.status_code, body.sent <= 64) == (429, True)  # saturated: refused before reading
            seen = holders()
            assert len(seen) <= jobs.MAX_LIVE_JOBS and job_a.id in seen
            gate.set()
            assert (await up).status_code == 404
            await until(lambda: job_a not in env.mgr._live)
            assert job_a.data is None and (await create(c, session="d" * 20)).status_code == 202
        await finish(env)
    run(go())


# --- task cancellation and shutdown ---------------------------------------------

def test_task_cancel_keeps_resources_until_worker_returns(env):
    async def go():
        env.det.gate.clear()
        async with client() as c:
            b = (await create(c)).json()
            await wait_thread_event(env.det.started)
            job = env.mgr._jobs[b["job_id"]]
            job.task.cancel()
            await asyncio.sleep(0.05)
            assert job.task.cancelled()
            # Future cancelled, native worker still blocked: resources must stay held.
            assert job in env.mgr._live and job.data is not None
            env.det.gate.set()
            await asyncio.to_thread(main._ocr_executor.submit(lambda: None).result, 5)
            st = (await c.get(f"/pdf/jobs/{b['job_id']}", headers={CAP: b["job_capability"]})).json()
            assert st["state"] != "analyzing" and job not in env.mgr._live, \
                "after task cancel + worker return, job stays analyzing and holds its slot until idle TTL"
        await finish(env)
    run(go())


def test_shutdown_waits_for_running_native_call(env):
    async def go():
        env.det.gate.clear()
        async with client() as c:
            b = (await create(c)).json()
            await wait_thread_event(env.det.started)
            job = env.mgr._jobs[b["job_id"]]
            asyncio.get_running_loop().call_later(0.3, env.det.gate.set)
            await env.mgr.shutdown()
            assert env.det.gate.is_set() and job not in env.mgr._live and job.data is None
    run(go())


def test_lifespan_and_legacy_image_route(env):
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:  # runs the new lifespan (reaper start + shutdown)
        assert c.get("/health").json() == {"status": "ok"}
        r = c.post("/detect", files={"image": ("a.png", _png(), "image/png")})
        assert r.status_code == 200 and "detection_id" in r.json()
        assert "cache-control" not in r.headers  # no-store is scoped to /pdf
        main._detection_cache.pop(r.json()["detection_id"], None)
        assert main._pdf_jobs._reaper is not None and not main._pdf_jobs._reaper.done()


def test_shutdown_timeout_then_loop_close_keeps_slot_until_worker_returns(env, monkeypatch):
    """After shutdown's wait times out, the loop closes and cancels the job task."""
    real_wait = asyncio.wait
    holder = {}

    async def go():
        env.det.gate.clear()
        async with client() as c:
            b = (await create(c)).json()
            await wait_thread_event(env.det.started)
            holder["job"] = env.mgr._jobs[b["job_id"]]
            monkeypatch.setattr(asyncio, "wait", lambda fs, timeout=None, **kw: real_wait(fs, timeout=0.1, **kw))
            await env.mgr.shutdown()
            monkeypatch.setattr(asyncio, "wait", real_wait)
            assert holder["job"] in env.mgr._live  # wait timed out; worker still blocked
    run(go())  # loop closes here and cancels the still-running job task
    job = holder["job"]
    still_running = not env.det.gate.is_set()
    in_live = job in env.mgr._live
    held = free_permits() == main.MAX_OCR_IN_FLIGHT - 1  # known positive: permit still held
    env.det.gate.set()
    main._ocr_executor.submit(lambda: None).result(15)
    assert still_running and in_live and held, "slot freed by loop shutdown while the native call still ran"
    # The worker returned after the loop closed: its own callback must free everything.
    assert job not in env.mgr._live and job.data is None and not env.mgr._sessions
    assert free_permits() == main.MAX_OCR_IN_FLIGHT and len(env.det.calls) == 1


def test_same_turn_reservations_after_upload_expiry(env):
    """Expired A keeps its slot while its receive buffer exists: max 2 holders throughout."""
    async def go():
        async with client() as c:
            body = SlowBody(_pdf(), chunk=64)
            up = asyncio.create_task(c.post("/pdf/jobs", content=body.__aiter__(), headers={SES: "a" * 20}))
            await until(lambda: len(env.mgr._live) == 1 and body.sent > 0)
            job_a = next(iter(env.mgr._live))
            session_a = job_a.session_hash

            def holders():
                return ({j.id for j in env.mgr._live}
                        | ({job_a.id} if job_a.running or job_a.receiving else set()))

            env.clock.t += jobs.IDLE_TTL_S + 1
            # Same loop turn, no await: B's reserve sweeps A; A's buffer still exists.
            b_job, _, _ = env.mgr.reserve("b" * 20)
            with pytest.raises(jobs.JobError) as busy:
                env.mgr.reserve("c" * 20)
            assert (busy.value.status, busy.value.code) == (429, "pdf_busy")  # before any body read
            assert job_a.removed and job_a.receiving == 1  # T5 positive: detector sees A
            assert holders() == {job_a.id, b_job.id}
            # A stops on its own (body never released) and only then frees its slot.
            await until(lambda: up.done())
            assert up.result().status_code == 404
            assert job_a.receiving == 0 and job_a not in env.mgr._live  # negative after completion
            assert session_a not in env.mgr._sessions and holders() == {b_job.id}
            body.release.set()
            await asyncio.sleep(0.05)
            assert body.sent_after_release == 0, "expired upload kept being read"
            assert (await create(c, session="c" * 20)).status_code == 202
            env.mgr.remove(b_job)
        await finish(env)
    run(go())


def test_failed_tombstones_are_bounded_content_free_and_expire(env):
    data = build_pdf([{"media": [0, 0, 100, 100]}, {"media": [0, 0, 14400, 14400]}])

    async def go():
        async with client() as c:
            made = []
            for _ in range(30):
                b = (await create(c, data)).json()
                await until(lambda: b["job_id"] not in env.mgr._jobs or env.mgr._jobs[b["job_id"]].state == "failed")
                made.append(b)
            assert not env.mgr._live and len(env.mgr._jobs) <= jobs.MAX_TOMBSTONES
            last = made[-1]
            h = {CAP: last["job_capability"]}
            st = await c.get(f"/pdf/jobs/{last['job_id']}", headers=h)
            assert st.status_code == 200 and st.json()["state"] == "failed"  # terminal: polling stops
            assert TITLE not in st.text and all(p["chord_count"] == 0 for p in st.json()["pages"])
            assert (await c.get(f"/pdf/jobs/{made[0]['job_id']}",
                                headers={CAP: made[0]["job_capability"]})).status_code == 404
            env.clock.t += jobs.TOMBSTONE_TTL_S - 1
            assert (await c.get(f"/pdf/jobs/{last['job_id']}", headers=h)).status_code == 200  # positive
            env.clock.t += 2
            assert (await c.get(f"/pdf/jobs/{last['job_id']}", headers=h)).status_code == 404
        await finish(env)
    run(go())
