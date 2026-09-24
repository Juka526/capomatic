"""Unit tests for backend.api.main — endpoint validation and helpers."""
from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.auth.auth0 import get_token_payload
from backend.api.main import (
    MAX_UPLOAD_BYTES,
    MAX_OCR_IN_FLIGHT,
    MAX_RENDER_IN_FLIGHT,
    _VALID_KEYS,
    _build_chord_item,
    _validate_params,
    _cache_put,
    _cache_get,
    _detection_cache,
    _ocr_admission,
    _render_admission,
    _parse_chords_override,
    app,
)

client = TestClient(app, raise_server_exceptions=False)


def _png_bytes(size: int = 100) -> bytes:
    """Create a minimal valid PNG in memory."""
    from PIL import Image
    img = Image.new("RGB", (size, size), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _oriented_jpeg_bytes() -> bytes:
    """Create a 10x20 JPEG whose EXIF orientation rotates it to 20x10."""
    from PIL import Image
    img = Image.new("RGB", (10, 20), (255, 255, 255))
    exif = Image.Exif()
    exif[274] = 6
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# _validate_params
# ---------------------------------------------------------------------------

class TestValidateParams:
    def test_valid_semitones_and_key(self):
        _validate_params(3, "Bb")  # should not raise

    def test_valid_semitones_no_key(self):
        _validate_params(-5, None)  # should not raise

    def test_semitones_out_of_range_low(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_params(-12, None)
        assert exc_info.value.status_code == 422

    def test_semitones_out_of_range_high(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_params(12, None)
        assert exc_info.value.status_code == 422

    def test_invalid_target_key(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_params(0, "H")
        assert exc_info.value.status_code == 422
        assert "H" in exc_info.value.detail



# ---------------------------------------------------------------------------
# _build_chord_item
# ---------------------------------------------------------------------------

class TestBuildChordItem:
    def test_successful_transpose(self):
        item = {"text": "Am", "confidence": 0.95, "bbox": [10, 20, 50, 40]}
        result = _build_chord_item(item, semitones=2, target_key=None)
        assert result["text"] == "Am"
        assert result["transposed"] == "Bm"
        assert result["confidence"] == 0.95
        assert result["bbox"] == [10, 20, 50, 40]

    def test_unparseable_chord_returns_none_transposed(self):
        item = {"text": "XYZ", "confidence": 0.8, "bbox": [0, 0, 10, 10]}
        result = _build_chord_item(item, semitones=0, target_key=None)
        assert result["transposed"] is None

    def test_none_bbox_preserved(self):
        item = {"text": "C", "confidence": 1.0, "bbox": None}
        result = _build_chord_item(item, semitones=0, target_key=None)
        assert result["bbox"] is None

    @pytest.mark.parametrize("marker,expected", [
        ("open", "(Bb/Ab"),
        ("close", "Bb/Ab)"),
        ("both", "(Bb/Ab)"),
    ])
    def test_preserves_parentheses_after_transpose(self, marker, expected):
        item = {
            "text": "C/Bb",
            "confidence": 1.0,
            "bbox": [0, 0, 10, 10],
            "style": {"parenthesis": marker},
        }

        result = _build_chord_item(item, semitones=-2, target_key="Eb")

        assert result["transposed"] == expected


# ---------------------------------------------------------------------------
# Detection cache
# ---------------------------------------------------------------------------

class TestDetectionCache:
    def setup_method(self):
        _detection_cache.clear()

    def test_put_and_get(self):
        _cache_put("abc", {"items": []})
        assert _cache_get("abc") == {"items": []}

    def test_get_missing_returns_none(self):
        assert _cache_get("nonexistent") is None

    def test_lru_eviction(self):
        from backend.api.main import _MAX_CACHE
        for i in range(_MAX_CACHE + 5):
            _cache_put(f"id_{i}", {"i": i})
        # First 5 should be evicted
        for i in range(5):
            assert _cache_get(f"id_{i}") is None
        # Last _MAX_CACHE should remain
        for i in range(5, _MAX_CACHE + 5):
            assert _cache_get(f"id_{i}") is not None

    def test_pixel_budget_evicts_large_images(self):
        large_image = type("LargeImage", (), {"width": 10000, "height": 5000})()
        _cache_put("first", {"items": [], "img": large_image})
        _cache_put("second", {"items": [], "img": large_image})

        assert _cache_get("first") is None
        assert _cache_get("second") is not None

    def teardown_method(self):
        _detection_cache.clear()


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /detect
# ---------------------------------------------------------------------------

class TestDetectEndpoint:
    @patch("backend.api.main.detect_chords_hybrid")
    def test_detect_returns_detection_id_and_chords(self, mock_detect):
        mock_detect.return_value = (
            [{"text": "Am", "confidence": 0.9, "bbox": [0, 0, 10, 10]}],
            {"crop_mode": "staff_bands", "num_regions": 1,
             "predict_ms": 10, "gate": {"pass": True}},
        )
        resp = client.post(
            "/detect",
            files={"image": ("test.png", _png_bytes(), "image/png")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "detection_id" in data
        assert data["count"] == 1
        assert data["chords"][0]["text"] == "Am"
        assert data["song_title"] == "알수없음"
        assert "original_key" in data
        # No transposed field in /detect response
        assert "transposed" not in data["chords"][0]

    @patch("backend.api.main.detect_chords_hybrid")
    def test_detect_returns_ocr_song_title(self, mock_detect):
        mock_detect.return_value = ([], {"song_title": "온 맘 다해"})

        resp = client.post(
            "/detect",
            files={"image": ("wrong-filename.png", _png_bytes(), "image/png")},
        )

        assert resp.json()["song_title"] == "온 맘 다해"

    @patch("backend.api.main.detect_chords_hybrid")
    def test_detect_caches_results(self, mock_detect):
        mock_detect.return_value = (
            [{"text": "C", "confidence": 1.0, "bbox": [0, 0, 10, 10]}],
            {"crop_mode": "staff_bands", "num_regions": 1,
             "predict_ms": 5, "gate": {"pass": True}},
        )
        resp = client.post(
            "/detect",
            files={"image": ("test.png", _png_bytes(), "image/png")},
        )
        detection_id = resp.json()["detection_id"]
        cached = _cache_get(detection_id)
        assert cached is not None
        assert len(cached["items"]) == 1
        _detection_cache.clear()

    @patch("backend.api.main.detect_chords_hybrid")
    def test_detect_rejects_paid_engine_without_running_ocr(self, mock_detect):
        resp = client.post(
            "/detect",
            files={"image": ("test.png", _png_bytes(), "image/png")},
            data={"ocr_engine": "paddle-gpt"},
        )
        assert resp.status_code == 422
        mock_detect.assert_not_called()

    def test_detect_rejects_invalid_ocr_engine(self):
        resp = client.post(
            "/detect",
            files={"image": ("test.png", _png_bytes(), "image/png")},
            data={"ocr_engine": "gpt"},
        )
        assert resp.status_code == 422

    def test_detect_rejects_invalid_original_key(self):
        resp = client.post(
            "/detect",
            files={"image": ("test.png", _png_bytes(), "image/png")},
            data={"original_key": "Z"},
        )
        assert resp.status_code == 422

    def test_detect_rejects_oversized_upload(self):
        big_data = b"\x00" * (MAX_UPLOAD_BYTES + 1)
        resp = client.post(
            "/detect",
            files={"image": ("big.png", big_data, "image/png")},
        )
        assert resp.status_code == 413

    @pytest.mark.parametrize("name,content_type,data", [
        ("bad.txt", "text/plain", b"not an image"),
        ("broken.png", "image/png", b"\x89PNG\r\n\x1a\ntruncated"),
    ])
    def test_detect_rejects_invalid_image_before_ocr(self, name, content_type, data):
        with patch("backend.api.main.detect_chords_hybrid") as mock_detect:
            resp = client.post("/detect", files={"image": (name, data, content_type)})
        assert resp.status_code == 422
        assert "valid PNG or JPEG" in resp.json()["detail"]
        mock_detect.assert_not_called()

    def test_detect_rejects_other_decodable_image_format(self):
        resp = client.post(
            "/detect",
            files={"image": ("test.gif", b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x00\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b", "image/gif")},
        )
        assert resp.status_code == 422

    def test_detect_rejects_animated_png(self):
        from PIL import Image
        frames = [
            Image.new("RGB", (10, 10), (255, 255, 255)),
            Image.new("RGB", (10, 10), (0, 0, 0)),
        ]
        buf = io.BytesIO()
        frames[0].save(buf, format="PNG", save_all=True, append_images=frames[1:])

        resp = client.post(
            "/detect",
            files={"image": ("animated.png", buf.getvalue(), "image/png")},
        )

        assert resp.status_code == 422
        assert resp.json()["detail"] == "Animated images are not supported."

    def test_detect_applies_exif_orientation_before_ocr(self):
        observed_size = None

        def fake_detect(path, **kwargs):
            nonlocal observed_size
            from PIL import Image
            with Image.open(path) as image:
                observed_size = image.size
            return [], {}

        with patch("backend.api.main.detect_chords_hybrid", side_effect=fake_detect):
            resp = client.post(
                "/detect",
                files={"image": ("phone.jpg", _oriented_jpeg_bytes(), "image/jpeg")},
            )

        assert resp.status_code == 200
        assert observed_size == (20, 10)

    def test_detect_rejects_excessive_pixel_count_before_ocr(self):
        fake_image = type("LargeImage", (), {
            "__enter__": lambda self: self,
            "__exit__": lambda self, *args: None,
            "format": "PNG",
            "width": 10000,
            "height": 10000,
            "load": lambda self: None,
        })()
        with (
            patch("backend.api.main.Image.open", return_value=fake_image),
            patch("backend.api.main.detect_chords_hybrid") as mock_detect,
        ):
            resp = client.post(
                "/detect",
                files={"image": ("large.png", _png_bytes(), "image/png")},
            )
        assert resp.status_code == 413
        mock_detect.assert_not_called()

    def test_detect_rejects_when_ocr_capacity_is_full(self):
        acquired = 0
        try:
            for _ in range(MAX_OCR_IN_FLIGHT):
                assert _ocr_admission.acquire(blocking=False)
                acquired += 1

            with patch("backend.api.main.detect_chords_hybrid") as mock_detect:
                resp = client.post(
                    "/detect",
                    files={"image": ("test.png", _png_bytes(), "image/png")},
                )

            assert resp.status_code == 429
            assert resp.headers["retry-after"] == "5"
            mock_detect.assert_not_called()
        finally:
            for _ in range(acquired):
                _ocr_admission.release()


# ---------------------------------------------------------------------------
# /detect/refine
# ---------------------------------------------------------------------------

class TestRefineDetectionEndpoint:
    def setup_method(self):
        _detection_cache.clear()

    def test_refine_disabled_even_when_paid_key_configured(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        resp = client.post("/detect/refine", data={"detection_id": "any"})
        assert resp.status_code == 410

    def test_refine_rejects_missing_detection_id(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        resp = client.post("/detect/refine", data={"detection_id": "missing"})

        assert resp.status_code == 410

    @patch("backend.api.main.detect_chords_hybrid")
    def test_refine_rejects_missing_openai_api_key(self, mock_detect, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        mock_detect.return_value = (
            [{"text": "C", "confidence": 1.0, "bbox": [0, 0, 10, 10]}],
            {"predict_ms": 5},
        )
        detect_resp = client.post(
            "/detect",
            files={"image": ("test.png", _png_bytes(), "image/png")},
        )
        detection_id = detect_resp.json()["detection_id"]

        resp = client.post("/detect/refine", data={"detection_id": detection_id})

        assert resp.status_code == 410


# ---------------------------------------------------------------------------
# /render
# ---------------------------------------------------------------------------

class TestRenderEndpoint:
    def setup_method(self):
        _detection_cache.clear()

    @patch("backend.api.main.detect_chords_hybrid")
    def test_render_returns_both_images(self, mock_detect):
        mock_detect.return_value = (
            [{"text": "Am", "confidence": 0.9, "bbox": [10, 20, 50, 40]}],
            {"crop_mode": "staff_bands", "num_regions": 1,
             "predict_ms": 10, "gate": {"pass": True}},
        )
        # First detect
        resp = client.post(
            "/detect",
            files={"image": ("test.png", _png_bytes(), "image/png")},
        )
        detection_id = resp.json()["detection_id"]

        # Then render
        resp = client.post(
            "/render",
            data={"detection_id": detection_id, "semitones": "-3"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["replace_image"].startswith("data:image/png;base64,")
        assert data["above_image"].startswith("data:image/png;base64,")
        assert data["semitones"] == -3
        assert "render_ms" in data

    @patch("backend.api.main.detect_chords_hybrid")
    def test_render_replace_mode_returns_only_replace_image(self, mock_detect):
        mock_detect.return_value = (
            [{"text": "Am", "confidence": 0.9, "bbox": [10, 20, 50, 40]}],
            {"crop_mode": "staff_bands", "num_regions": 1,
             "predict_ms": 10, "gate": {"pass": True}},
        )
        detect_resp = client.post(
            "/detect",
            files={"image": ("test.png", _png_bytes(), "image/png")},
        )
        detection_id = detect_resp.json()["detection_id"]

        resp = client.post(
            "/render",
            data={"detection_id": detection_id, "semitones": "-3", "mode": "replace"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["replace_image"].startswith("data:image/png;base64,")
        assert data["above_image"] is None

    def test_render_rejects_bad_mode(self):
        resp = client.post(
            "/render",
            data={"detection_id": "x", "semitones": "-1", "mode": "fast"},
        )
        assert resp.status_code == 422

    def test_render_rejects_missing_detection_id(self):
        resp = client.post(
            "/render",
            data={"detection_id": "nonexistent", "semitones": "-1"},
        )
        assert resp.status_code == 404

    def test_render_rejects_bad_semitones(self):
        resp = client.post(
            "/render",
            data={"detection_id": "x", "semitones": "-12"},
        )
        assert resp.status_code == 422

    def test_render_rejects_when_capacity_is_full(self):
        from PIL import Image
        _cache_put("busy", {
            "items": [],
            "img": Image.new("RGB", (10, 10), "white"),
            "original_key": "C",
            "meta": {},
        })
        acquired = 0
        try:
            for _ in range(MAX_RENDER_IN_FLIGHT):
                assert _render_admission.acquire(blocking=False)
                acquired += 1

            resp = client.post(
                "/render",
                data={"detection_id": "busy", "semitones": "0"},
            )

            assert resp.status_code == 429
            assert resp.headers["retry-after"] == "2"
        finally:
            for _ in range(acquired):
                _render_admission.release()

    def teardown_method(self):
        _detection_cache.clear()


class TestChordCorrections:
    def test_accepts_trimmed_chord_and_bounded_numeric_bbox(self):
        result = _parse_chords_override(
            '[{"text":" Am7 ","bbox":[1.2,2.6,30.4,40.5]}]',
            (100, 100),
        )

        assert result == [{
            "text": "Am7",
            "confidence": 1.0,
            "bbox": [1, 3, 30, 40],
        }]

    @pytest.mark.parametrize("value", [
        '{}',
        '["Am"]',
        '[{"text":"","bbox":null}]',
        '[{"text":"not-a-chord","bbox":null}]',
        '[{"text":"Am","bbox":[0,0,101,10]}]',
        '[{"text":"Am","bbox":[0,0,10]}]',
        '[{"text":"Am","bbox":[0,0,10,NaN]}]',
    ])
    def test_rejects_malformed_or_out_of_bounds_values(self, value):
        with pytest.raises(HTTPException) as exc_info:
            _parse_chords_override(value, (100, 100))

        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# /overlay — legacy validation
# ---------------------------------------------------------------------------

class TestOverlayEndpoint:
    @patch("backend.api.main.detect_chords_hybrid")
    def test_overlay_uses_paddle_only(self, mock_detect):
        mock_detect.return_value = ([], {})

        resp = client.post(
            "/overlay",
            files={"image": ("test.png", _png_bytes(), "image/png")},
            data={"semitones": "0"},
        )

        assert resp.status_code == 200
        assert mock_detect.call_args.kwargs["use_ai_fallback"] is False

    def test_overlay_rejects_bad_mode(self):
        resp = client.post(
            "/overlay",
            files={"image": ("test.png", _png_bytes(), "image/png")},
            data={"semitones": "0", "mode": "badmode"},
        )
        assert resp.status_code == 422

    def test_overlay_rejects_bad_semitones(self):
        resp = client.post(
            "/overlay",
            files={"image": ("test.png", _png_bytes(), "image/png")},
            data={"semitones": "-12"},
        )
        assert resp.status_code == 422

    def test_overlay_rejects_invalid_image(self):
        resp = client.post(
            "/overlay",
            files={"image": ("broken.png", b"not an image", "image/png")},
            data={"semitones": "0"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# V1 login identity and retired administration
# ---------------------------------------------------------------------------

def test_auth_me_returns_verified_identity_without_database():
    async def identity_override():
        return {"sub": "auth0|123", "email": "user@example.com", "name": "User"}

    app.dependency_overrides[get_token_payload] = identity_override
    try:
        resp = client.get("/api/auth/me")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json() == {
        "sub": "auth0|123",
        "email": "user@example.com",
        "name": "User",
    }


@pytest.mark.parametrize("path", ["/api/auth/admin-test", "/api/admin/users"])
def test_admin_endpoints_are_retired_in_v1(path):
    resp = client.get(path)
    assert resp.status_code == 410
