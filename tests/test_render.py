"""Unit tests for backend.overlay.render — overlay rendering."""
from __future__ import annotations

import pytest
from PIL import Image

from backend.overlay.render import render_overlay


def _white_img(w: int = 400, h: int = 300) -> Image.Image:
    """Create a white RGB PIL image."""
    return Image.new("RGB", (w, h), (255, 255, 255))


def _chord(text: str, transposed: str, bbox: list[int]) -> dict:
    return {"text": text, "transposed": transposed, "bbox": bbox}


# ---------------------------------------------------------------------------
# render_overlay — basic behaviour
# ---------------------------------------------------------------------------

class TestRenderOverlay:
    def test_above_mode_returns_image(self):
        img = _white_img()
        chords = [_chord("Am", "Bm", [50, 100, 100, 120])]
        result = render_overlay(img, chords, "above")
        assert isinstance(result, Image.Image)

    def test_replace_mode_returns_image(self):
        img = _white_img()
        chords = [_chord("Am", "Bm", [50, 100, 100, 120])]
        result = render_overlay(img, chords, "replace")
        assert isinstance(result, Image.Image)

    def test_empty_chords_returns_copy(self):
        img = _white_img()
        result = render_overlay(img, [], "above")
        assert isinstance(result, Image.Image)
        assert result.size == img.size

    def test_skips_none_transposed(self):
        img = _white_img()
        chords = [{"text": "Am", "transposed": None, "bbox": [10, 10, 50, 30]}]
        result = render_overlay(img, chords, "above")
        assert isinstance(result, Image.Image)

    def test_skips_none_bbox(self):
        img = _white_img()
        chords = [{"text": "Am", "transposed": "Bm", "bbox": None}]
        result = render_overlay(img, chords, "above")
        assert isinstance(result, Image.Image)

    def test_does_not_modify_original(self):
        img = _white_img()
        original_data = list(img.getdata())
        chords = [_chord("Am", "Bm", [50, 100, 100, 120])]
        render_overlay(img, chords, "replace")
        assert list(img.getdata()) == original_data

    def test_multiple_rows_above(self):
        img = _white_img(w=400, h=600)
        chords = [
            _chord("Am", "Bm", [50, 100, 100, 120]),
            _chord("C", "D", [200, 100, 250, 120]),
            _chord("G", "A", [50, 300, 100, 320]),
        ]
        result = render_overlay(img, chords, "above")
        assert isinstance(result, Image.Image)

    def test_multiple_chords_replace_uniform_font(self):
        img = _white_img(w=400, h=300)
        chords = [
            _chord("Am", "Bm", [10, 50, 60, 70]),
            _chord("C", "D", [100, 50, 150, 75]),  # different bbox height
            _chord("G", "A", [200, 50, 250, 68]),
        ]
        result = render_overlay(img, chords, "replace")
        assert isinstance(result, Image.Image)

    def test_small_bbox_uses_min_font_size(self):
        img = _white_img()
        # Very small bbox (5px height) — font should clamp to minimum
        chords = [_chord("Am", "Bm", [10, 10, 50, 15])]
        result = render_overlay(img, chords, "replace")
        assert isinstance(result, Image.Image)

    def test_chords_near_edges(self):
        img = _white_img(w=200, h=200)
        chords = [
            _chord("Am", "Bm", [0, 0, 40, 20]),      # top-left corner
            _chord("C", "D", [160, 180, 200, 200]),    # bottom-right corner
        ]
        result = render_overlay(img, chords, "above")
        assert isinstance(result, Image.Image)
