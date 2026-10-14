"""Real Sentry SDK envelopes (local transport only) for legacy and PDF paths.

T5: every negative ("sentinel absent") is preceded by the same transport and
search catching the sentinel when the app's scrubbers are switched off.
"""
import io
import json

import httpx
import pytest
import sentry_sdk
from fastapi.testclient import TestClient
from PIL import Image
from sentry_sdk.transport import Transport

from backend.api import main
from _pdf_bytes import build_pdf

SENT = "SENTINEL_DETECTED_Amazing_Grace_Cmaj7"
SESSION = "SENTINELSESSION" + "s" * 20
FILENAME = "SENTINEL_FILENAME_sheet.png"


class _Capture(Transport):
    def __init__(self, options=None):
        super().__init__(options)
        self.items: list[str] = []

    def capture_envelope(self, envelope):
        for item in envelope.items:
            self.items.append(item.get_bytes().decode("utf-8", "replace"))


def _init(scrub: bool):
    t = _Capture()
    opts = {**main._sentry_options(), "traces_sample_rate": 1.0, "release": "test"}
    if not scrub:
        for k in ("before_send", "before_send_transaction", "before_breadcrumb"):
            opts.pop(k)
    sentry_sdk.init(dsn="https://public@o0.ingest.sentry.io/1", transport=t, **opts)
    return t


@pytest.fixture
def sentry():
    yield _init
    sentry_sdk.get_client().close()
    sentry_sdk.init()


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(buf, format="PNG")
    return buf.getvalue() + SENT.encode()


def _drive_legacy_error(monkeypatch):
    def explode(*a, **k):
        local_secret = SENT  # local variable must not be captured
        main.logger.error("detected %s", local_secret)  # logger event + breadcrumb
        sentry_sdk.set_tag("detected", SENT)
        sentry_sdk.set_context("detected", {"text": SENT})
        raise RuntimeError(f"failed on {SENT}")
    monkeypatch.setattr(main, "detect_chords_hybrid", explode)
    c = TestClient(main.app, raise_server_exceptions=False)
    r = c.post(f"/detect?q={SENT}", files={"image": (FILENAME, _png(), "image/png")},
               headers={"Authorization": f"Bearer {SENT}", SESSION[:10]: SESSION})
    sentry_sdk.flush()
    assert r.status_code == 500


def _events(t):
    out = []
    for raw in t.items:
        try:
            out.append(json.loads(raw))
        except ValueError:
            pass
    return out


@pytest.mark.parametrize("scrub", [False, True])
def test_legacy_error_and_transaction_envelopes(sentry, monkeypatch, scrub):
    t = sentry(scrub)
    _drive_legacy_error(monkeypatch)
    payload = "\n".join(t.items)
    events = _events(t)
    errors = [e for e in events if e.get("exception")]
    assert errors and any(e.get("type") == "transaction" for e in events)
    if not scrub:  # known positive: the same search sees every channel
        assert SENT in payload
        assert f"failed on {SENT}" in payload
        return
    for needle in (SENT, "SENTINEL", "Bearer", "Amazing"):
        assert needle not in payload, needle
    exc = errors[0]["exception"]["values"][-1]
    assert exc["type"] == "RuntimeError" and exc["value"] == "redacted"
    assert errors[0]["release"] == "test"
    for e in errors:
        for v in e["exception"]["values"]:
            assert all("vars" not in f for f in v["stacktrace"]["frames"])


def _pdf_job_with_failing_page(monkeypatch):
    def explode(*a, **k):
        raise RuntimeError(f"paddle failed on {SENT}")
    monkeypatch.setattr(main, "detect_chords_hybrid", explode)
    mgr = main._pdf_jobs
    mgr._jobs.clear(), mgr._live.clear(), mgr._sessions.clear()
    data = build_pdf([{"media": [0, 0, 100, 100]}]) + f"%{SENT}\n".encode()
    import asyncio

    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://t") as c:
            r = await c.post("/pdf/jobs", content=data, headers={"X-PDF-Session": SESSION})
            b = r.json()
            for _ in range(500):
                job = mgr._jobs.get(b["job_id"])
                if job and job.state == "failed":
                    break
                await asyncio.sleep(0.01)
            s = await c.get(f"/pdf/jobs/{b['job_id']}", headers={"X-PDF-Job-Capability": b["job_capability"]})
            await c.get(f"/pdf/jobs/{SENT}", headers={"X-PDF-Job-Capability": b["job_capability"]})
            await mgr.shutdown()
            return b, s.json()
    b, status = asyncio.run(go())
    sentry_sdk.flush()
    return b, status


@pytest.mark.parametrize("scrub", [False, True])
def test_pdf_job_envelopes(sentry, monkeypatch, scrub):
    t = sentry(scrub)
    b, status = _pdf_job_with_failing_page(monkeypatch)
    assert status["state"] == "failed" and status["error"] == "analysis_failed"
    payload = "\n".join(t.items)
    secrets = (SENT, SESSION, b["job_capability"], b["job_id"])
    if not scrub:  # known positive: request URL/headers carry ids and session
        assert any(s in payload for s in secrets)
        return
    for s in secrets:
        assert s not in payload
    for e in _events(t):
        if e.get("type") == "transaction":
            assert e["transaction"] == "/pdf/*" and "spans" not in e and "request" not in e


@pytest.mark.parametrize("scrub", [False, True])
def test_custom_span_data_and_description(sentry, monkeypatch, scrub):
    """contexts.trace channel: span data/description must not carry detected text."""
    t = sentry(scrub)

    def explode(*a, **k):
        span = sentry_sdk.get_current_span()
        span.set_data("detected", SENT)
        span.description = SENT
        raise RuntimeError("x")
    monkeypatch.setattr(main, "detect_chords_hybrid", explode)
    TestClient(main.app, raise_server_exceptions=False).post(
        "/detect", files={"image": ("a.png", _png(), "image/png")})
    sentry_sdk.flush()
    traces = [e.get("contexts", {}).get("trace", {}) for e in _events(t)]
    hit = any(SENT in json.dumps(tr) for tr in traces)
    assert hit is (not scrub)  # unscrubbed: same channel carries it (known positive)
    if scrub:
        for tr in traces:
            assert set(tr) <= {"trace_id", "span_id", "parent_span_id", "op", "status"}


@pytest.mark.parametrize("scrub", [False, True])
def test_unmatched_route_transaction_name(sentry, scrub):
    t = sentry(scrub)
    TestClient(main.app, raise_server_exceptions=False).get(f"/detect/{SENT}")
    sentry_sdk.flush()
    names = [e.get("transaction") for e in _events(t) if e.get("type") == "transaction"]
    assert names
    if not scrub:
        assert any(SENT in n for n in names)  # known positive: URL becomes the name
    else:
        assert names == ["unknown"]


def test_malformed_metadata_fails_safe(sentry):
    t = sentry(True)
    sentry_sdk.capture_event({
        "message": SENT, "transaction": {"x": SENT}, "tags": {"t": SENT}, "extra": {"e": SENT},
        "contexts": {"trace": {"op": 7, "status": SENT, "data": {"d": SENT}}, "runtime": SENT,
                     "detected": {"t": SENT}},
        "request": {"url": SENT}, "user": {"id": SENT},
    })
    sentry_sdk.capture_event({"message": "m", "contexts": {"trace": {"op": "http.server", "span_id": SENT}}})
    sentry_sdk.flush()
    assert SENT not in "\n".join(t.items)  # scrubbed or dropped, never forwarded


def test_scrub_without_routes_fails_safe(sentry, monkeypatch):
    """If app is not built yet (import time), the SDK drops instead of leaking."""
    t = sentry(True)
    monkeypatch.setattr(main, "app", None)
    with sentry_sdk.start_transaction(name=f"/x/{SENT}", op="http.server"):
        pass
    sentry_sdk.capture_exception(RuntimeError(SENT))
    sentry_sdk.flush()
    assert SENT not in "\n".join(t.items)
