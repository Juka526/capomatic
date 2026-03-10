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
    app,
)

client = TestClient(app, raise_server_exceptions=False)


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

    @pytest.mark.parametrize("key", sorted(_VALID_KEYS))
    def test_all_valid_keys_accepted(self, key):
        _validate_params(0, key)  # should not raise


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
# /health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /detect — validation only (OCR mocked)
# ---------------------------------------------------------------------------

class TestDetectEndpoint:
    def _png_bytes(self, size: int = 100) -> bytes:
        """Create a minimal valid PNG in memory."""
        from PIL import Image
        img = Image.new("RGB", (size, size), (255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @patch("backend.api.main.detect_chords_hybrid")
    def test_detect_returns_chords(self, mock_detect):
        mock_detect.return_value = (
            [{"text": "Am", "confidence": 0.9, "bbox": [0, 0, 10, 10]}],
            {"crop_mode": "staff_bands", "num_regions": 1,
             "predict_ms": 10, "gate": {"pass": True}},
        )
        resp = client.post(
            "/detect",
            files={"image": ("test.png", self._png_bytes(), "image/png")},
            data={"semitones": "2"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["chords"][0]["text"] == "Am"

    def test_detect_rejects_bad_semitones(self):
        resp = client.post(
            "/detect",
            files={"image": ("test.png", self._png_bytes(), "image/png")},
            data={"semitones": "99"},
        )
        assert resp.status_code == 422

    def test_detect_rejects_invalid_target_key(self):
        resp = client.post(
            "/detect",
            files={"image": ("test.png", self._png_bytes(), "image/png")},
            data={"semitones": "0", "target_key": "Z"},
        )
        assert resp.status_code == 422

    def test_detect_rejects_oversized_upload(self):
        # Create data slightly over the limit
        big_data = b"\x00" * (MAX_UPLOAD_BYTES + 1)
        resp = client.post(
            "/detect",
            files={"image": ("big.png", big_data, "image/png")},
            data={"semitones": "0"},
        )
        assert resp.status_code == 413


# ---------------------------------------------------------------------------
# /overlay — validation only
# ---------------------------------------------------------------------------

class TestOverlayEndpoint:
    def _png_bytes(self) -> bytes:
        from PIL import Image
        img = Image.new("RGB", (100, 100), (255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_overlay_rejects_bad_mode(self):
        resp = client.post(
            "/overlay",
            files={"image": ("test.png", self._png_bytes(), "image/png")},
            data={"semitones": "0", "mode": "badmode"},
        )
        assert resp.status_code == 422

    def test_overlay_rejects_bad_semitones(self):
        resp = client.post(
            "/overlay",
            files={"image": ("test.png", self._png_bytes(), "image/png")},
            data={"semitones": "-12"},
        )
        assert resp.status_code == 422
