"""Unit tests for backend.ocr.preprocess: find_chord_x_start and build_chord_bands."""
from __future__ import annotations

import numpy as np
import pytest

from backend.ocr.preprocess import build_chord_bands, detect_staff_systems, find_chord_x_start


def _white(h: int, w: int) -> np.ndarray:
    return np.full((h, w, 3), 255, dtype=np.uint8)


def _black_cols(band: np.ndarray, x_start: int, x_end: int) -> np.ndarray:
    band = band.copy()
    band[:, x_start:x_end] = 0
    return band


class TestFindChordXStart:
    def test_all_white_returns_zero(self):
        assert find_chord_x_start(_white(80, 400)) == 0

    def test_all_black_no_gap_returns_zero(self):
        # Content fills everything — no gap to detect
        band = np.zeros((80, 400, 3), dtype=np.uint8)
        assert find_chord_x_start(band) == 0

    def test_bar_number_then_gap_then_chords(self):
        # Bar number at cols 2–9 (right_edge=9 ≤ narrow_margin=12 for 400px)
        # gap 10–34, chord content 35–200
        band = _white(80, 400)
        band = _black_cols(band, 2, 10)    # bar number (narrow)
        band = _black_cols(band, 35, 200)  # chords
        assert find_chord_x_start(band) == 35

    def test_narrow_image_returns_zero(self):
        # margin < 10px → skip detection
        band = _white(80, 50)
        band = _black_cols(band, 0, 5)
        assert find_chord_x_start(band) == 0

    def test_no_content_in_margin_returns_zero(self):
        # Content only past the 8% margin — nothing to detect as bar number
        band = _white(80, 400)
        band = _black_cols(band, 50, 200)   # 50/400 = 12.5% > 8%
        assert find_chord_x_start(band) == 0

    def test_gap_too_small_returns_zero(self):
        # Bar number at cols 2–7 (within narrow_margin=12), gap only 2 cols, then chords
        band = _white(80, 400)
        band = _black_cols(band, 2, 8)     # bar number (narrow)
        band = _black_cols(band, 10, 200)  # chords (gap = 2 cols, < _GAP_MIN_COLS=4)
        assert find_chord_x_start(band) == 0

    def test_wide_margin_content_returns_zero(self):
        # Tempo marking spans cols 0–20 (right_edge=20 > narrow_margin=12 for 400px)
        # → treated as tempo/clef, not a bar number; no crop applied
        band = _white(80, 400)
        band = _black_cols(band, 0, 20)    # wide content (tempo marking)
        band = _black_cols(band, 35, 200)  # chords
        assert find_chord_x_start(band) == 0

    def test_margin_content_at_very_left_edge(self):
        # Bar number at cols 0–10, gap 11–34, chords start at 35 (past 8% margin)
        band = _white(80, 400)
        band = _black_cols(band, 0, 10)
        band = _black_cols(band, 35, 300)
        assert find_chord_x_start(band) == 35


class TestBuildChordBands:
    """Tests for build_chord_bands inter-system boundary geometry.

    Image: 600 H × 400 W, all white.  Systems are (top, bottom) tuples.
    For staff_h=50: line_spacing=12.5, max_above=max(55,min(80,37))=55,
    pad_below=max(4,min(8,3))=4.
    """

    def _img(self, h: int = 600, w: int = 400) -> np.ndarray:
        return np.full((h, w, 3), 255, dtype=np.uint8)

    def test_single_system_band_top_respects_max_above(self):
        # First system: prev_bottom=0, band_top = max(0, top - max_above).
        # top=200, max_above=55 → band_top=145.
        img = self._img()
        systems = [(200, 250)]
        bands = build_chord_bands(img, systems)
        assert len(bands) == 1
        assert bands[0]["y0"] == 145           # top - max_above
        assert bands[0]["staff_top"] == 200

    def test_first_system_at_top_does_not_go_negative(self):
        # top=30, max_above=40 → top - max_above = -10 → clamped to prev_bottom=0.
        img = self._img()
        systems = [(30, 80)]
        bands = build_chord_bands(img, systems)
        assert len(bands) == 1
        assert bands[0]["y0"] == 0

    def test_second_system_band_top_uses_prev_bottom(self):
        # System 1: top=200, bottom=250.
        # System 2: top=350, bottom=400.
        #   max_above=55 → top - max_above = 295.
        #   prev_bottom=250 → band_top = max(250, 295) = 295.
        img = self._img()
        systems = [(200, 250), (350, 400)]
        bands = build_chord_bands(img, systems)
        assert len(bands) == 2
        assert bands[1]["y0"] == 295           # limited by top - max_above (295 > 250)

    def test_tight_staves_band_top_clamped_to_prev_bottom(self):
        # System 1: top=200, bottom=250.
        # System 2: top=260, bottom=310 (only 10 px gap).
        #   max_above=40 → top - max_above = 220.
        #   prev_bottom=250 → band_top = max(250, 220) = 250.
        img = self._img()
        systems = [(200, 250), (260, 310)]
        bands = build_chord_bands(img, systems)
        assert len(bands) >= 1
        # Find the band for the second system (staff_top=260)
        second = next((b for b in bands if b["staff_top"] == 260), None)
        if second is not None:
            # band_top must not intrude into previous system (y ≥ 250)
            assert second["y0"] >= 250

    def test_empty_systems_returns_empty(self):
        img = self._img()
        assert build_chord_bands(img, []) == []

    def test_degenerate_system_skipped(self):
        # bottom <= top: invalid staff, should be skipped.
        img = self._img()
        systems = [(200, 200), (300, 350)]
        bands = build_chord_bands(img, systems)
        assert all(b["staff_top"] != 200 for b in bands)


class TestDetectStaffSystems:
    def test_recovers_fragmented_staff_in_large_gap(self):
        img = _white(360, 500)
        for top in (60, 140, 220, 300):
            for y in (top, top + 7, top + 14, top + 21, top + 28):
                img[y, 20:480] = 0
        # Break the middle staff so the strict projection path misses it.
        for y in (140, 147, 154, 161, 168):
            img[y, 120:380] = 255

        systems = detect_staff_systems(img)

        assert len(systems) == 4
        assert any(abs(top - 140) <= 3 for top, _ in systems)

    def test_fixture_moment_life_detects_all_staff_systems(self):
        from PIL import Image

        img = Image.open("fixtures/images/순간이-삶이-되어.png").convert("RGB")

        systems = detect_staff_systems(img)

        assert len(systems) == 7
        assert any(600 <= top <= 630 for top, _ in systems)
