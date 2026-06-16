from __future__ import annotations

import numpy as np
from PIL import Image

import backend.ocr.paddle_ocr as paddle_ocr


class _FakeOCR:
    def __init__(self) -> None:
        self.calls = 0

    def predict(self, _img):
        self.calls += 1
        return []


def test_oversized_stitched_canvas_uses_per_region_path(tmp_path, monkeypatch):
    image_path = tmp_path / "sheet.png"
    Image.new("RGB", (100, 100), "white").save(image_path)

    regions = [
        {
            "crop": np.full((300, 2000, 3), 255, dtype=np.uint8),
            "x0": 0,
            "y0": 0,
            "w": 2000,
            "h": 300,
            "staff_top": 250,
            "staff_bottom": 300,
        },
        {
            "crop": np.full((300, 2000, 3), 255, dtype=np.uint8),
            "x0": 0,
            "y0": 500,
            "w": 2000,
            "h": 300,
            "staff_top": 750,
            "staff_bottom": 800,
        },
    ]
    fake_ocr = _FakeOCR()

    monkeypatch.setattr(paddle_ocr, "select_ocr_regions", lambda _img: (regions, "staff_bands"))
    monkeypatch.setattr(paddle_ocr, "get_ocr", lambda *args, **kwargs: fake_ocr)
    monkeypatch.setattr(paddle_ocr, "STITCH_MAX_SAFE_PIXELS", 900_000)
    monkeypatch.setattr(paddle_ocr, "MAX_STITCHED_PIXELS", 600_000)
    monkeypatch.setattr(paddle_ocr, "MIN_STITCH_RESIZE_SCALE", 0.85)

    items, meta = paddle_ocr.run_ocr_paddle(str(image_path))

    assert items == []
    assert fake_ocr.calls == 2
    assert meta["stitched"] is False
    assert meta["predict_calls"] == 2
    assert meta["stitch_decision"] == "per_region"
    assert meta["stitch_skip_reason"] == "too_many_pixels"
    assert meta["stitched_candidate_pixels"] == 1_220_000


def test_small_stitched_canvas_stays_single_predict_call(tmp_path, monkeypatch):
    image_path = tmp_path / "sheet.png"
    Image.new("RGB", (100, 100), "white").save(image_path)

    regions = [
        {
            "crop": np.full((80, 600, 3), 255, dtype=np.uint8),
            "x0": 0,
            "y0": 0,
            "w": 600,
            "h": 80,
            "staff_top": 70,
            "staff_bottom": 100,
        },
        {
            "crop": np.full((80, 600, 3), 255, dtype=np.uint8),
            "x0": 0,
            "y0": 200,
            "w": 600,
            "h": 80,
            "staff_top": 270,
            "staff_bottom": 300,
        },
    ]
    fake_ocr = _FakeOCR()

    monkeypatch.setattr(paddle_ocr, "select_ocr_regions", lambda _img: (regions, "staff_bands"))
    monkeypatch.setattr(paddle_ocr, "get_ocr", lambda *args, **kwargs: fake_ocr)
    monkeypatch.setattr(paddle_ocr, "STITCH_MAX_SAFE_PIXELS", 900_000)
    monkeypatch.setattr(paddle_ocr, "MAX_STITCHED_PIXELS", 600_000)
    monkeypatch.setattr(paddle_ocr, "MIN_STITCH_RESIZE_SCALE", 0.85)

    items, meta = paddle_ocr.run_ocr_paddle(str(image_path))

    assert items == []
    assert fake_ocr.calls == 1
    assert meta["stitched"] is True
    assert meta["predict_calls"] == 1
    assert meta["stitch_decision"] == "stitched"
    assert meta["stitched_candidate_pixels"] == 102_000
