"""Unit tests for direction-marker filter (paddle_ocr) and filter.py edge cases."""
from __future__ import annotations

import pytest

from backend.ocr.paddle_ocr import (
    _apply_direction_filter,
    _is_bare_root,
    _is_direction_token,
    _near_any_direction,
)
from backend.ocr.filter import (
    _split_bbox,
    _split_concatenated,
    _strip_leading_number,
    is_chord_candidate,
    recover_candidates,
)


# ---------------------------------------------------------------------------
# Direction-marker spatial filter (paddle_ocr)
# ---------------------------------------------------------------------------

class TestIsDirectionToken:
    @pytest.mark.parametrize("text", [".", ".S.", "al", "Coda", "coda", "Fine", "fine", "segno"])
    def test_direction_tokens_detected(self, text):
        assert _is_direction_token(text)

    @pytest.mark.parametrize("text", ["Am", "G7", "D", "C#m", "sus4"])
    def test_chord_text_not_direction(self, text):
        assert not _is_direction_token(text)


class TestIsBareRoot:
    @pytest.mark.parametrize("text", ["A", "B", "C", "D", "E", "F", "G"])
    def test_bare_roots(self, text):
        assert _is_bare_root(text)

    @pytest.mark.parametrize("text", ["Am", "D7", "C#", "Bb", ""])
    def test_non_bare_roots(self, text):
        assert not _is_bare_root(text)


class TestNearAnyDirection:
    def test_within_proximity(self):
        bbox = [100, 50, 120, 70]  # center (110, 60)
        direction_bboxes = [[200, 50, 220, 70]]  # center (210, 60)
        # dx=100, dy=0 → within 150px/30px
        assert _near_any_direction(bbox, direction_bboxes)

    def test_outside_x_proximity(self):
        bbox = [100, 50, 120, 70]  # center (110, 60)
        direction_bboxes = [[400, 50, 420, 70]]  # center (410, 60), dx=300
        assert not _near_any_direction(bbox, direction_bboxes)

    def test_outside_y_proximity(self):
        bbox = [100, 50, 120, 70]  # center (110, 60)
        direction_bboxes = [[100, 150, 120, 170]]  # center (110, 160), dy=100
        assert not _near_any_direction(bbox, direction_bboxes)

    def test_empty_direction_list(self):
        assert not _near_any_direction([0, 0, 10, 10], [])


class TestApplyDirectionFilter:
    def test_filters_bare_root_near_direction(self):
        raw_items = [
            {"raw_text": "D", "confidence": 0.9, "bbox": [100, 50, 120, 70]},
            {"raw_text": ".S.", "confidence": 0.5, "bbox": [130, 50, 160, 70]},
            {"raw_text": "al", "confidence": 0.5, "bbox": [170, 50, 190, 70]},
            {"raw_text": "Coda", "confidence": 0.5, "bbox": [200, 50, 250, 70]},
        ]
        result = _apply_direction_filter(raw_items)
        texts = [item["text"] for item in result]
        assert "D" not in texts

    def test_keeps_chord_with_extension_near_direction(self):
        raw_items = [
            {"raw_text": "D7", "confidence": 0.9, "bbox": [100, 50, 120, 70]},
            {"raw_text": "Coda", "confidence": 0.5, "bbox": [200, 50, 250, 70]},
        ]
        result = _apply_direction_filter(raw_items)
        texts = [item["text"] for item in result]
        assert "D7" in texts

    def test_keeps_bare_root_far_from_direction(self):
        raw_items = [
            {"raw_text": "D", "confidence": 0.9, "bbox": [100, 50, 120, 70]},
            {"raw_text": "Coda", "confidence": 0.5, "bbox": [500, 50, 550, 70]},
        ]
        result = _apply_direction_filter(raw_items)
        texts = [item["text"] for item in result]
        assert "D" in texts

    def test_filters_period_in_raw_text(self):
        raw_items = [
            {"raw_text": "D.S.", "confidence": 0.9, "bbox": [100, 50, 150, 70]},
        ]
        result = _apply_direction_filter(raw_items)
        assert len(result) == 0

    def test_no_direction_tokens_passes_all(self):
        raw_items = [
            {"raw_text": "Am", "confidence": 0.9, "bbox": [10, 10, 50, 30]},
            {"raw_text": "G", "confidence": 0.85, "bbox": [100, 10, 130, 30]},
        ]
        result = _apply_direction_filter(raw_items)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# filter.py edge cases
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["Am7b5", "D7b9", "C7#9", "G13b9"])
def test_chord_candidate_accepts_altered_degrees(text):
    assert is_chord_candidate(text)


class TestStripLeadingNumber:
    @pytest.mark.parametrize("text,expected", [
        ("7Am", "Am"),
        ("4G/B", "G/B"),
        ("12Cmaj7", "Cmaj7"),
        ("01Am", "Am"),
    ])
    def test_strips_leading_digits(self, text, expected):
        assert _strip_leading_number(text) == expected

    @pytest.mark.parametrize("text", ["Am", "G7", "D", "123", ""])
    def test_no_match_returns_none(self, text):
        assert _strip_leading_number(text) is None


class TestSplitConcatenated:
    def test_em7_g_over_a(self):
        parts = _split_concatenated("Em7G/A")
        assert parts == ["Em7", "G/A"]

    def test_slash_bass_not_split(self):
        assert _split_concatenated("D/F#") == []

    def test_single_chord_no_split(self):
        assert _split_concatenated("Am7") == []

    def test_two_simple_chords(self):
        parts = _split_concatenated("AmG")
        assert parts == ["Am", "G"]


class TestSplitBbox:
    def test_splits_bbox_proportionally(self):
        item = {"text": "Gsus4C", "confidence": 0.9, "bbox": [100, 50, 200, 70]}
        parts = ["Gsus4", "C"]
        result = _split_bbox(item, parts, item["bbox"])
        assert len(result) == 2
        assert result[0]["text"] == "Gsus4"
        assert result[1]["text"] == "C"
        # Gsus4 is 5 chars, C is 1 char → ratio = 5/6 ≈ 0.833
        # x_split = 100 + int(100 * 5/6) = 100 + 83 = 183
        assert result[0]["bbox"] == [100, 50, 183, 70]
        assert result[1]["bbox"] == [183, 50, 200, 70]

    def test_none_bbox_preserved(self):
        item = {"text": "AmG", "confidence": 0.9, "bbox": None}
        result = _split_bbox(item, ["Am", "G"], None)
        assert len(result) == 2
        assert result[0]["bbox"] is None
        assert result[1]["bbox"] is None


class TestRecoverCandidates:
    def test_leading_number_recovery(self):
        items = [{"text": "7Am", "confidence": 0.9, "bbox": [0, 0, 10, 10]}]
        recovered, parse_count, split_count = recover_candidates(items)
        assert len(recovered) == 1
        assert recovered[0]["text"] == "Am"
        assert parse_count == 1
        assert split_count == 0

    def test_split_recovery(self):
        items = [{"text": "Em7G", "confidence": 0.9, "bbox": [0, 0, 100, 20]}]
        recovered, parse_count, split_count = recover_candidates(items)
        assert len(recovered) == 2
        assert split_count == 1
        # Split items should have different bboxes
        assert recovered[0]["bbox"] != recovered[1]["bbox"]
        assert recovered[0]["bbox"][0] == 0        # first starts at x1
        assert recovered[1]["bbox"][2] == 100      # second ends at x2

    def test_non_recoverable_items_skipped(self):
        items = [{"text": "HelloWorld", "confidence": 0.9, "bbox": [0, 0, 10, 10]}]
        recovered, parse_count, split_count = recover_candidates(items)
        assert len(recovered) == 0
