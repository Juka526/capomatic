"""Unit tests for backend.ocr.merge.

All tests are pure Python — no PaddleOCR, no Claude, no image files.
"""
from __future__ import annotations

import pytest

from backend.ocr.merge import (
    cluster_paddle_items_by_row,
    merge_rows,
    merge_single_row,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _item(text: str, x1: int, y1: int, x2: int, y2: int, conf: float = 0.9) -> dict:
    return {"text": text, "confidence": conf, "bbox": [x1, y1, x2, y2]}


def _item_no_bbox(text: str) -> dict:
    return {"text": text, "confidence": 0.9, "bbox": None}


# ---------------------------------------------------------------------------
# TestClusterPaddleItemsByRow
# ---------------------------------------------------------------------------

class TestClusterPaddleItemsByRow:
    def test_empty_returns_empty(self):
        assert cluster_paddle_items_by_row([]) == []

    def test_single_item_one_row(self):
        rows = cluster_paddle_items_by_row([_item("D", 10, 20, 30, 35)])
        assert len(rows) == 1
        assert len(rows[0]) == 1

    def test_two_items_same_y_same_row(self):
        items = [_item("D", 10, 20, 30, 35), _item("A", 50, 22, 70, 37)]
        rows = cluster_paddle_items_by_row(items)
        assert len(rows) == 1
        assert len(rows[0]) == 2

    def test_two_items_far_apart_two_rows(self):
        items = [_item("D", 10, 20, 30, 35), _item("A", 10, 200, 30, 215)]
        rows = cluster_paddle_items_by_row(items)
        assert len(rows) == 2

    def test_row_sorted_left_to_right(self):
        items = [_item("A", 80, 20, 100, 35), _item("D", 10, 20, 30, 35)]
        rows = cluster_paddle_items_by_row(items)
        assert rows[0][0]["text"] == "D"   # lower x1 comes first
        assert rows[0][1]["text"] == "A"

    def test_bbox_none_items_excluded(self):
        items = [_item("D", 10, 20, 30, 35), _item_no_bbox("G")]
        rows = cluster_paddle_items_by_row(items)
        assert len(rows) == 1
        assert rows[0][0]["text"] == "D"

    def test_all_bbox_none_returns_empty(self):
        assert cluster_paddle_items_by_row([_item_no_bbox("D"), _item_no_bbox("A")]) == []

    def test_three_rows_detected(self):
        items = [
            _item("D",  10,  20,  30,  35),
            _item("A",  10, 120,  30, 135),
            _item("G",  10, 220,  30, 235),
        ]
        rows = cluster_paddle_items_by_row(items)
        assert len(rows) == 3


# ---------------------------------------------------------------------------
# TestMergeSingleRow
# ---------------------------------------------------------------------------

class TestMergeSingleRow:
    # --- core regression tests for the two known bugs ---

    def test_df_sharp_corrected(self):
        """D/F# misread by PaddleOCR as D/F; Claude's text restores the #."""
        paddle = [{"text": "D/F", "confidence": 0.81, "bbox": [50, 120, 80, 135]}]
        merged = merge_single_row(paddle, ["D/F#"])
        assert len(merged) == 1
        assert merged[0]["text"] == "D/F#"
        assert merged[0]["bbox"] == [50, 120, 80, 135]   # Paddle bbox preserved
        assert merged[0]["confidence"] == 1.0

    def test_dadd2_missed_by_paddle(self):
        """D(add2) not detected by PaddleOCR; Claude adds it with bbox=None."""
        paddle = [{"text": "Asus4", "confidence": 0.95, "bbox": [100, 20, 140, 35]}]
        merged = merge_single_row(paddle, ["D(add2)", "Asus4"])
        texts = [i["text"] for i in merged]
        assert "Dadd2" in texts            # D(add2) normalised to Dadd2
        dadd2 = next(i for i in merged if i["text"] == "Dadd2")
        assert dadd2["bbox"] is None       # PaddleOCR missed it — no bbox
        # Asus4 should retain its Paddle bbox
        asus4 = next(i for i in merged if i["text"] == "Asus4")
        assert asus4["bbox"] == [100, 20, 140, 35]

    # --- general behaviour ---

    def test_equal_count_uses_claude_text(self):
        paddle = [_item("Em", 10, 20, 30, 35), _item("G", 50, 20, 70, 35)]
        merged = merge_single_row(paddle, ["Em7", "G"])
        assert merged[0]["text"] == "Em7"
        assert merged[0]["bbox"] == [10, 20, 30, 35]
        assert merged[1]["text"] == "G"

    def test_claude_more_than_paddle_gets_none_bbox(self):
        paddle = [_item("D", 10, 20, 30, 35)]
        merged = merge_single_row(paddle, ["D", "Asus4"])
        assert merged[0]["text"] == "D"
        assert merged[0]["bbox"] == [10, 20, 30, 35]
        assert merged[1]["text"] == "Asus4"
        assert merged[1]["bbox"] is None

    def test_paddle_more_than_claude_drops_extra(self):
        paddle = [_item("D", 10, 20, 30, 35), _item("A", 50, 20, 70, 35)]
        merged = merge_single_row(paddle, ["D"])
        assert len(merged) == 1
        assert merged[0]["text"] == "D"

    def test_empty_claude_returns_empty(self):
        paddle = [_item("D", 10, 20, 30, 35)]
        assert merge_single_row(paddle, []) == []

    def test_empty_paddle_all_get_none_bbox(self):
        merged = merge_single_row([], ["D", "Asus4"])
        assert len(merged) == 2
        assert all(i["bbox"] is None for i in merged)

    def test_invalid_claude_string_skipped(self):
        paddle = [_item("D", 10, 20, 30, 35)]
        merged = merge_single_row(paddle, ["notachord", "D"])
        # "notachord" is invalid; "D" matches position 1 (index 1) → bbox=None
        texts = [i["text"] for i in merged]
        assert "D" in texts
        assert "notachord" not in texts

    def test_normalization_applied(self):
        """Claude may return D(add2); it should be normalised to Dadd2."""
        merged = merge_single_row([], ["D(add2)"])
        assert len(merged) == 1
        assert merged[0]["text"] == "Dadd2"

    def test_confidence_is_1_0(self):
        paddle = [_item("D", 10, 20, 30, 35)]
        merged = merge_single_row(paddle, ["D"])
        assert merged[0]["confidence"] == 1.0


# ---------------------------------------------------------------------------
# TestMergeRows
# ---------------------------------------------------------------------------

class TestMergeRows:
    def test_equal_row_count(self):
        paddle_rows = [
            [_item("D", 10, 20, 30, 35), _item("A", 50, 20, 70, 35)],
        ]
        claude_rows = [["D", "A"]]
        merged = merge_rows(paddle_rows, claude_rows)
        assert len(merged) == 2
        assert merged[0]["text"] == "D"
        assert merged[1]["text"] == "A"

    def test_claude_more_rows_extra_items_bbox_none(self):
        paddle_rows = [
            [_item("D", 10, 20, 30, 35)],
        ]
        claude_rows = [["D"], ["G", "Em"]]   # Claude found a 2nd row
        merged = merge_rows(paddle_rows, claude_rows)
        texts = [i["text"] for i in merged]
        assert "D" in texts
        assert "G" in texts
        assert "Em" in texts
        # Extra Claude row items have no bbox
        for item in merged:
            if item["text"] in ("G", "Em"):
                assert item["bbox"] is None

    def test_claude_fewer_rows_extra_paddle_dropped(self):
        paddle_rows = [
            [_item("D", 10, 20, 30, 35)],
            [_item("G", 10, 120, 30, 135)],  # Paddle found a 2nd row Claude didn't
        ]
        claude_rows = [["D"]]
        merged = merge_rows(paddle_rows, claude_rows)
        texts = [i["text"] for i in merged]
        assert "D" in texts
        assert "G" not in texts   # extra Paddle row dropped

    def test_empty_paddle_rows_all_bbox_none(self):
        merged = merge_rows([], [["D", "A"], ["G"]])
        assert len(merged) == 3
        assert all(i["bbox"] is None for i in merged)

    def test_empty_claude_rows_returns_empty(self):
        paddle_rows = [[_item("D", 10, 20, 30, 35)]]
        assert merge_rows(paddle_rows, []) == []

    def test_both_empty(self):
        assert merge_rows([], []) == []

    def test_dadd2_full_scenario(self):
        """Integration: D(add2) missing from PaddleOCR row, present in Claude row."""
        paddle_rows = [
            # Paddle detected only Asus4 and A in row 0 (missed D(add2))
            [_item("Asus4", 100, 20, 140, 35), _item("A", 160, 20, 180, 35)],
        ]
        claude_rows = [["D(add2)", "Asus4", "A"]]
        merged = merge_rows(paddle_rows, claude_rows)
        texts = [i["text"] for i in merged]
        assert "Dadd2" in texts
        assert "Asus4" in texts
        assert "A" in texts
        dadd2 = next(i for i in merged if i["text"] == "Dadd2")
        assert dadd2["bbox"] is None    # missed by Paddle → no spatial data
        asus4 = next(i for i in merged if i["text"] == "Asus4")
        assert asus4["bbox"] is not None  # Paddle found this one
