"""Sentry payload inspection for issue #5: errors are reported without PII."""
from __future__ import annotations

import io
import json
from unittest.mock import patch

import pytest
import sentry_sdk
from fastapi.testclient import TestClient
from PIL import Image
from sentry_sdk.transport import Transport

from backend.api.main import _sentry_options, app

_TOKEN = "eyJhbGciOiJSUzI1NiJ9.secret-bearer-payload.signature"
_EMAIL = "worship.leader@example.com"
_IMAGE_MARKER = b"CAPOMATIC-IMAGE-BYTES"


class _CaptureTransport(Transport):
    def __init__(self, options=None):
        super().__init__(options)
        self.payloads: list[str] = []

    def capture_envelope(self, envelope):
        for item in envelope.items:
            self.payloads.append(item.get_bytes().decode("utf-8", "replace"))


def _init_capture(**overrides):
    transport = _CaptureTransport()
    options = {**_sentry_options(), "traces_sample_rate": 0.0, "release": "test-sha", **overrides}
    sentry_sdk.init(dsn="https://public@o0.ingest.sentry.io/1", transport=transport, **options)
    return transport


@pytest.fixture
def sentry_events():
    try:
        yield _init_capture()
    finally:
        sentry_sdk.get_client().close()
        sentry_sdk.init()


@pytest.fixture
def unscrubbed_sentry_events():
    """Same transport with the app's event scrubbers off: the known positive."""
    try:
        yield _init_capture(before_send=None, before_send_transaction=None, before_breadcrumb=None)
    finally:
        sentry_sdk.get_client().close()
        sentry_sdk.init()


def _png_with_marker() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), (255, 255, 255)).save(buf, format="PNG")
    # Trailing bytes after IEND are ignored by decoders but let us search
    # the Sentry payload for any trace of the uploaded image body.
    return buf.getvalue() + _IMAGE_MARKER


def test_privacy_options_are_set():
    options = _sentry_options()

    assert options["send_default_pii"] is False
    assert options["max_request_body_size"] == "never"
    assert options["include_local_variables"] is False


def _post_failing_detect():
    def explode(*_args, **_kwargs):
        secret_local = f"{_EMAIL} {_TOKEN}"  # must not appear via local-variable capture
        raise RuntimeError("controlled backend error " + str(len(secret_local)))

    client = TestClient(app, raise_server_exceptions=False)
    with patch("backend.api.main.detect_chords_hybrid", side_effect=explode):
        resp = client.post(
            "/detect",
            files={"image": ("sheet.png", _png_with_marker(), "image/png")},
            headers={"Authorization": f"Bearer {_TOKEN}", "Cookie": f"email={_EMAIL}"},
        )
    sentry_sdk.flush()
    return resp


def test_capture_sees_exception_message_without_scrubbers(unscrubbed_sentry_events):
    assert _post_failing_detect().status_code == 500
    assert "controlled backend error" in "\n".join(unscrubbed_sentry_events.payloads)


def test_backend_error_event_contains_no_token_email_image_or_locals(sentry_events):
    resp = _post_failing_detect()

    assert resp.status_code == 500
    events = [json.loads(p) for p in sentry_events.payloads if '"exception"' in p]
    assert events, "the controlled error was not reported"
    payload = "\n".join(sentry_events.payloads)
    # Exception text can carry detected content, so only the type is sent.
    assert "controlled backend error" not in payload
    assert events[0]["exception"]["values"][-1]["type"] == "RuntimeError"
    assert events[0]["exception"]["values"][-1]["value"] == "redacted"
    assert events[0]["release"] == "test-sha"
    for secret in (_TOKEN, _EMAIL, _IMAGE_MARKER.decode()):
        assert secret not in payload
    for event in events:
        for exc in event["exception"]["values"]:
            for frame in (exc.get("stacktrace") or {}).get("frames", []):
                assert "vars" not in frame
