"""Unit tests for backend.ocr.preprocess.find_chord_x_start."""
from __future__ import annotations

import numpy as np
import pytest

from backend.ocr.preprocess import find_chord_x_start


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
        # Bar number cols 5–19, gap 20–34, chord content 35–200
        band = _white(80, 400)
        band = _black_cols(band, 5, 20)    # bar number
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
        # Bar number at col 5–19, gap only 2 cols (< _GAP_MIN_COLS=4), then chords
        band = _white(80, 400)
        band = _black_cols(band, 5, 20)    # bar number
        band = _black_cols(band, 22, 200)  # chords (gap = 2 cols)
        assert find_chord_x_start(band) == 0

    def test_margin_content_at_very_left_edge(self):
        # Bar number at cols 0–10, gap 11–34, chords start at 35 (past 8% margin)
        band = _white(80, 400)
        band = _black_cols(band, 0, 10)
        band = _black_cols(band, 35, 300)
        assert find_chord_x_start(band) == 35
