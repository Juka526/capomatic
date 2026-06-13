"""Unit tests for backend.api.main — endpoint validation and helpers."""
from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.api.main import (
    MAX_UPLOAD_BYTES,
    _VALID_KEYS,
    _build_chord_item,
    _validate_params,
    _cache_put,
    _cache_get,
    _detection_cache,
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
        assert "original_key" in data
        # No transposed field in /detect response
        assert "transposed" not in data["chords"][0]

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

    @patch("backend.api.main.run_ocr_paddle_gpt_hybrid")
    def test_detect_uses_paddle_gpt_when_requested(self, mock_detect):
        mock_detect.return_value = (
            [{"text": "G", "confidence": 1.0, "bbox": [0, 0, 10, 10]}],
            {"ocr_engine": "paddle-gpt-hybrid", "predict_ms": 5},
        )
        resp = client.post(
            "/detect",
            files={"image": ("test.png", _png_bytes(), "image/png")},
            data={"ocr_engine": "paddle-gpt"},
        )
        assert resp.status_code == 200
        assert resp.json()["meta"]["ocr_engine"] == "paddle-gpt-hybrid"
        mock_detect.assert_called_once()

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


# ---------------------------------------------------------------------------
# /detect/refine
# ---------------------------------------------------------------------------

class TestRefineDetectionEndpoint:
    def setup_method(self):
        _detection_cache.clear()

    @patch("backend.api.main.refine_paddle_items_with_gpt")
    @patch("backend.api.main.detect_chords_hybrid")
    def test_refine_reuses_cached_detection_and_updates_cache(self, mock_detect, mock_refine, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        mock_detect.return_value = (
            [{"text": "D/F", "confidence": 0.82, "bbox": [10, 20, 50, 40]}],
            {"predict_ms": 5},
        )
        mock_refine.return_value = (
            [{"text": "D/F#", "confidence": 0.95, "bbox": [10, 20, 50, 40]}],
            {
                "ocr_engine": "paddle-gpt-hybrid",
                "gpt_used": True,
                "gpt_text_replaced": 1,
                "reused_paddle_detection": True,
            },
        )

        detect_resp = client.post(
            "/detect",
            files={"image": ("test.png", _png_bytes(), "image/png")},
        )
        detection_id = detect_resp.json()["detection_id"]
        refine_resp = client.post("/detect/refine", data={"detection_id": detection_id})

        assert refine_resp.status_code == 200
        data = refine_resp.json()
        assert data["detection_id"] == detection_id
        assert data["chords"][0]["text"] == "D/F#"
        assert data["meta"]["reused_paddle_detection"] is True
        assert _cache_get(detection_id)["items"][0]["text"] == "D/F#"
        mock_detect.assert_called_once()
        mock_refine.assert_called_once()

    def test_refine_rejects_missing_detection_id(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        resp = client.post("/detect/refine", data={"detection_id": "missing"})

        assert resp.status_code == 404

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

        assert resp.status_code == 503
        assert "OPENAI_API_KEY" in resp.json()["detail"]


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

    def teardown_method(self):
        _detection_cache.clear()


# ---------------------------------------------------------------------------
# /overlay — legacy validation
# ---------------------------------------------------------------------------

class TestOverlayEndpoint:
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
