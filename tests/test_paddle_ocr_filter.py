"""Unit tests for direction-marker filter (paddle_ocr) and filter.py edge cases."""
from __future__ import annotations

import sys
import types

import pytest
from PIL import Image

from backend.ocr.paddle_ocr import (
    _apply_direction_filter,
    _get_title_ocr,
    _is_bare_root,
    _is_direction_token,
    _near_any_direction,
    _read_song_title,
    _merge_title_line_items,
    _select_song_title,
    _is_section_marker_row,
    _sort_reading_order,
)
from backend.ocr.filter import (
    _split_bbox,
    _split_chord_text,
    _split_concatenated,
    _strip_leading_number,
    filter_candidates,
    is_chord_candidate,
    is_section_marker,
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


class TestSelectSongTitle:
    def test_title_ocr_uses_mobile_korean_models(self, monkeypatch):
        calls = []

        class FakePaddleOCR:
            def __init__(self, **kwargs):
                calls.append(kwargs)

        monkeypatch.setattr("backend.ocr.paddle_ocr._title_ocr", None)
        monkeypatch.setitem(sys.modules, "paddleocr", types.SimpleNamespace(PaddleOCR=FakePaddleOCR))

        _get_title_ocr()

        assert calls[0]["text_detection_model_name"] == "PP-OCRv5_mobile_det"
        assert calls[0]["text_recognition_model_name"] == "korean_PP-OCRv5_mobile_rec"

    def test_selects_prominent_title_over_metadata(self):
        raw_items = [
            {"raw_text": "Capo: 2", "bbox": [40, 20, 140, 40]},
            {"raw_text": "온 맘 다해", "bbox": [330, 80, 670, 132]},
            {"raw_text": "Babbie Mason", "bbox": [700, 155, 900, 177]},
            {"raw_text": "F", "bbox": [450, 190, 470, 220]},
        ]

        assert _select_song_title(raw_items, (1000, 1500)) == "온 맘 다해"
        assert _is_section_marker_row("Intro - V1 - V2 - C - C")

    def test_returns_none_without_explicit_title(self):
        raw_items = [
            {"raw_text": "Key: F", "bbox": [40, 20, 140, 42]},
            {"raw_text": "F", "bbox": [450, 80, 475, 110]},
            {"raw_text": "작곡 홍길동", "bbox": [700, 100, 900, 121]},
            {"raw_text": "F -> Eb (-2)", "bbox": [300, 20, 550, 55]},
            {"raw_text": "Babbie Mason", "bbox": [400, 100, 600, 120]},
        ]

        assert _select_song_title(raw_items, (1000, 951)) is None

    def test_merges_split_title_on_same_line(self):
        raw_items = [
            {"raw_text": "주님을", "bbox": [244, 48, 338, 87]},
            {"raw_text": "예배하는 것", "bbox": [326, 51, 472, 87]},
        ]

        assert _merge_title_line_items(raw_items)[0]["raw_text"] == "주님을 예배하는 것"

    def test_reads_header_crop(self):
        class FakeOCR:
            def predict(self, crop):
                assert crop.shape == (200, 900, 3)
                return [{
                    "rec_texts": ["온 맘 다해"],
                    "rec_scores": [0.99],
                    "rec_polys": [[[300, 50], [600, 50], [600, 100], [300, 100]]],
                }]

        title, elapsed_ms = _read_song_title(
            FakeOCR(),
            Image.new("RGB", (1000, 1500), "white"),
            [{"y0": 200}],
            "staff_bands",
        )

        assert title == "온 맘 다해"
        assert elapsed_ms >= 0

    def test_recognizes_blank_korean_title_box(self, monkeypatch):
        class FakeOCR:
            def predict(self, _crop):
                return [{
                    "rec_texts": [""],
                    "rec_scores": [0.0],
                    "rec_polys": [[[300, 50], [600, 50], [600, 100], [300, 100]]],
                }]

        class FakeRecognizer:
            def predict(self, _crops):
                return [{"rec_text": "온 맘 다해"}]

        monkeypatch.setattr(
            "backend.ocr.paddle_ocr._get_title_recognizer",
            lambda: FakeRecognizer(),
        )
        title, _ = _read_song_title(
            FakeOCR(),
            Image.new("RGB", (1000, 1500), "white"),
            [{"y0": 200}],
            "staff_bands",
        )

        assert title == "온 맘 다해"


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
    def test_drops_ambiguous_section_chord_in_left_margin(self):
        raw_items = [
            {"raw_text": "C", "confidence": 0.99, "bbox": [73, 952, 104, 979]},
            {"raw_text": "C", "confidence": 0.99, "bbox": [300, 952, 331, 979]},
            {"raw_text": "C7", "confidence": 0.99, "bbox": [73, 500, 110, 530]},
            {"raw_text": "Fm7", "confidence": 0.99, "bbox": [80, 600, 125, 630]},
            {"raw_text": "Gm7", "confidence": 0.99, "bbox": [140, 600, 185, 630]},
        ]

        result = _apply_direction_filter(raw_items, image_width=1042)

        assert [item["text"] for item in result] == ["C", "C7", "Fm7", "Gm7"]

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

    def test_recovers_chord_after_section_marker_with_suffix_bbox(self):
        raw_items = [
            {"raw_text": "[CHORUS] F", "confidence": 0.93, "bbox": [100, 40, 200, 60]},
        ]

        result = _apply_direction_filter(raw_items)

        assert result == [
            {"text": "F", "confidence": 0.93, "bbox": [190, 40, 200, 60]},
        ]

    @pytest.mark.parametrize("text", ["[CHORUS]", "[VERSE] refrain", "[INTRO] H"])
    def test_drops_section_marker_without_valid_chord_suffix(self, text):
        raw_items = [{"raw_text": text, "confidence": 0.93, "bbox": [100, 40, 200, 60]}]

        assert _apply_direction_filter(raw_items) == []

    def test_sort_reading_order_groups_rows_before_x_sort(self):
        items = [
            {"text": "C/F", "confidence": 1, "bbox": [500, 100, 540, 124]},
            {"text": "F", "confidence": 1, "bbox": [100, 101, 120, 123]},
            {"text": "G", "confidence": 1, "bbox": [100, 180, 120, 202]},
        ]

        result = _sort_reading_order(items)

        assert [item["text"] for item in result] == ["F", "C/F", "G"]

    def test_stray_token_above_a_row_does_not_split_it(self):
        # Lyric/note fragments just above a chord row used to start the row,
        # pushing the lower-sitting "D" into a row of its own after "Em7".
        items = [
            {"text": "HO", "confidence": 0.5, "bbox": [81, 227, 196, 247]},
            {"text": "G2", "confidence": 1, "bbox": [80, 252, 104, 272]},
            {"text": "Em7/A", "confidence": 1, "bbox": [270, 252, 315, 272]},
            {"text": "Em7", "confidence": 1, "bbox": [448, 250, 481, 273]},
            {"text": "D", "confidence": 1, "bbox": [338, 254, 350, 270]},
        ]

        result = _sort_reading_order(items)

        assert [item["text"] for item in result] == ["HO", "G2", "Em7/A", "D", "Em7"]

    def test_chords_at_slightly_different_heights_share_a_row(self):
        items = [
            {"text": "A7sus4", "confidence": 1, "bbox": [200, 96, 250, 124]},   # taller superscript box
            {"text": "D", "confidence": 1, "bbox": [100, 102, 115, 120]},
            {"text": "Em7", "confidence": 1, "bbox": [300, 100, 330, 122]},
        ]

        result = _sort_reading_order(items)

        assert [item["text"] for item in result] == ["D", "A7sus4", "Em7"]


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


class TestSectionMarkers:
    @pytest.mark.parametrize("text", [
        "V", "V1", "V2", "V3", "C1", "C2", "B1", "B2",
        "Intro", "Outro", "Bridge", "Coda", "Tag", "Pre",
        "Chorus", "Verse", "D.S", "D.C", "Fine", "optional", "tacet",
    ])
    def test_unambiguous_marker_is_dropped(self, text):
        assert is_section_marker(text)

    @pytest.mark.parametrize("text", ["C", "B"])
    def test_bare_chord_requires_left_margin_context(self, text):
        assert not is_section_marker(text)
        assert is_section_marker(text, [20, 50, 40, 70], image_width=1000)
        assert not is_section_marker(text, [200, 50, 220, 70], image_width=1000)

    @pytest.mark.parametrize("text", ["C7", "Fm7", "Gm7"])
    def test_real_chords_are_not_markers(self, text):
        assert not is_section_marker(text, [20, 50, 60, 70], image_width=1000)


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

    @pytest.mark.parametrize("text,expected", [
        ("Bb/D C/E F/A", ["Bb/D", "C/E", "F/A"]),
        ("Gm7Bb/C", ["Gm7", "Bb/C"]),
        ("Am7Dm7Gm7", ["Am7", "Dm7", "Gm7"]),
    ])
    def test_requested_compound_examples(self, text, expected):
        assert (_split_chord_text(text) or _split_concatenated(text)) == expected

    @pytest.mark.parametrize("text", [
        "1. Bb/D C/E F/A D.S.",
        "2. Bb/D C/E F/A D.C.",
        "3. Bb/D C/E F/A Fine",
    ])
    def test_volta_directions_are_removed(self, text):
        assert _split_chord_text(text) == ["Bb/D", "C/E", "F/A"]

    @pytest.mark.parametrize("text,expected", [
        ("Bb/C(C/Bb)", ["Bb/C", "C/Bb"]),
        ("Bb(Gm7)", ["Bb", "Gm7"]),
    ])
    def test_parenthesized_alternative_chords(self, text, expected):
        assert _split_chord_text(text) == expected

    def test_parenthesized_secondary_row_is_ignored(self):
        assert _split_chord_text("(Am7Dm7)") == []

    def test_single_parenthesized_chord_is_an_occurrence(self):
        assert _split_chord_text("(Am7)") == ["Am7"]

    @pytest.mark.parametrize("text", ["A7(sus4)", "C(add9)", "G(b5)"])
    def test_parenthesized_modifiers_are_not_split(self, text):
        assert _split_chord_text(text) == []


class TestSplitBbox:
    def test_splits_bbox_evenly(self):
        item = {"text": "Gsus4C", "confidence": 0.9, "bbox": [100, 50, 200, 70]}
        parts = ["Gsus4", "C"]
        result = _split_bbox(item, parts, item["bbox"])
        assert len(result) == 2
        assert result[0]["text"] == "Gsus4"
        assert result[1]["text"] == "C"
        assert result[0]["bbox"] == [100, 50, 150, 70]
        assert result[1]["bbox"] == [150, 50, 200, 70]

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

    def test_volta_recovery_splits_bbox_and_transposes(self):
        from backend.chords.parser import parse_chord
        from backend.chords.transpose import transpose_chord

        items = [{
            "text": "2. Bb/D C/E F/A D.S.",
            "confidence": 0.99,
            "bbox": [600, 100, 900, 130],
        }]

        recovered, parse_count, split_count = recover_candidates(items)

        assert [item["text"] for item in recovered] == ["Bb/D", "C/E", "F/A"]
        assert [item["bbox"] for item in recovered] == [
            [600, 100, 700, 130],
            [700, 100, 800, 130],
            [800, 100, 900, 130],
        ]
        assert all(is_chord_candidate(item["text"]) for item in recovered)
        assert [transpose_chord(parse_chord(item["text"]), -2, target_key="Eb") for item in recovered] == [
            "Ab/C", "Bb/D", "Eb/G",
        ]
        assert parse_count == 0
        assert split_count == 1

    @pytest.mark.parametrize("raw_text,expected", [
        ("||2. Eb", ["Eb"]),     # repeat barline read as two pipes
        ("|2. Eb", ["Eb"]),
        ("|||3.Bb/D", ["Bb/D"]),
        ("||2.", []),            # volta number alone is not a chord
    ])
    def test_volta_after_repeat_barline_keeps_chord(self, raw_text, expected):
        raw = [{"raw_text": raw_text, "confidence": 0.85, "bbox": [900, 100, 980, 130]}]

        assert [item["text"] for item in _apply_direction_filter(raw)] == expected

    @pytest.mark.parametrize("raw_text", [
        "2. Bb/D C/E F/A D.S.",
        "Bb/D C/E F/A D.S.",
    ])
    def test_paddle_volta_path_uses_same_split(self, raw_text):
        raw = [{
            "raw_text": raw_text,
            "confidence": 0.99,
            "bbox": [600, 100, 900, 130],
        }]

        result = _apply_direction_filter(raw)

        assert [item["text"] for item in result] == ["Bb/D", "C/E", "F/A"]
        assert [item["bbox"] for item in result] == [
            [600, 100, 700, 130],
            [700, 100, 800, 130],
            [800, 100, 900, 130],
        ]

    def test_non_recoverable_items_skipped(self):
        items = [{"text": "HelloWorld", "confidence": 0.9, "bbox": [0, 0, 10, 10]}]
        recovered, parse_count, split_count = recover_candidates(items)
        assert len(recovered) == 0

    def test_recovers_five_read_as_s_in_altered_extension(self):
        items = [{
            "text": "F#m7(bs)",
            "confidence": 0.96,
            "bbox": [100, 50, 170, 75],
        }]

        result = filter_candidates(items)

        assert [item["text"] for item in result] == ["F#m7b5"]

    def test_filter_candidates_preserves_recovered_order(self):
        items = [
            {"text": "Am7b5", "confidence": 1.0, "bbox": [0, 0, 10, 10]},
            {"text": "D7b9Gm7", "confidence": 1.0, "bbox": [10, 0, 80, 10]},
            {"text": "Bb", "confidence": 1.0, "bbox": [80, 0, 100, 10]},
        ]

        result = filter_candidates(items)

        assert [item["text"] for item in result] == ["Am7b5", "D7b9", "Gm7", "Bb"]

    def test_filter_candidates_splits_parenthesized_alternatives(self):
        items = [
            {"text": "Bb/C(C/Bb)", "confidence": 0.97, "bbox": [400, 230, 500, 250]},
            {"text": "Bb(Gm7)", "confidence": 1.0, "bbox": [140, 230, 210, 250]},
            {"text": "(Am7)", "confidence": 0.95, "bbox": [215, 230, 270, 250]},
            {"text": "(Am7Dm7)", "confidence": 1.0, "bbox": [520, 250, 600, 270]},
        ]

        result = filter_candidates(items)

        assert [item["text"] for item in result] == [
            "Bb/C", "C/Bb", "Bb", "Gm7", "Am7",
        ]
        assert [item["bbox"] for item in result[:2]] == [
            [400, 230, 450, 250],
            [450, 230, 500, 250],
        ]
        assert [item.get("style", {}).get("parenthesis") for item in result] == [
            None, "both", None, "both", "both",
        ]


# ---------------------------------------------------------------------------
# Generic OCR confusion repairs (issue #9)
# ---------------------------------------------------------------------------

def _filter_one(text: str, confidence: float = 0.95) -> list[tuple[str, str | None]]:
    result = filter_candidates([{"text": text, "confidence": confidence, "bbox": [0, 0, 100, 20]}])
    return [(item["text"], (item.get("style") or {}).get("parenthesis")) for item in result]


class TestOcrConfusionRepairs:
    @pytest.mark.parametrize("text,expected", [
        ("F#m7(bs)", "F#m7b5"),
        ("F#m7(bS)", "F#m7b5"),
        ("Am7bs", "Am7b5"),
        ("Am7bS", "Am7b5"),
        ("Bdim7bs", "Bdim7b5"),
        ("Asus4bs", "Asus4b5"),
        ("C7bs(b9)", "C7b5b9"),
        ("Em(bs)", "Emb5"),
        ("A(bs)", "A(b5)"),
    ])
    def test_five_read_as_s_is_repaired(self, text, expected):
        assert _filter_one(text) == [(expected, None)]

    @pytest.mark.parametrize("text,expected", [
        ("Bm7bs/F", "Bm7b5/F"),
        ("Bm7(bs)/F", "Bm7b5/F"),
        ("Dm7bS/C", "Dm7b5/C"),
        ("Flm7(bs)/E", "F#m7b5/E"),
    ])
    def test_repair_keeps_slash_bass(self, text, expected):
        assert _filter_one(text) == [(expected, None)]

    @pytest.mark.parametrize("text", ["Am7b5", "F#m7(b5)", "Am7b5/G", "Absus", "Gb", "Ab7"])
    def test_already_valid_chords_are_unchanged(self, text):
        assert _filter_one(text) == [(text, None)]

    @pytest.mark.parametrize("text", [
        "Bbs",      # B-flat root plus noise: no digit, so "bs" is not an alteration
        "Gbs",
        "Am7bs5",   # would become the invalid alteration b55
        "Cbs/Z",
        "bs",
        "Am7bsus",  # "bsus" is not an alteration
    ])
    def test_invalid_repairs_are_rejected(self, text):
        assert _filter_one(text) == []

    @pytest.mark.parametrize("text,expected", [
        ("Clm", "C#m"),
        ("CHm", "C#m"),
        ("Flm", "F#m"),
        ("F|m", "F#m"),
        ("FI7", "F#7"),
        ("Clmaj7", "C#maj7"),
        ("Gl/B", "G#/B"),
        ("Flm7bs", "F#m7b5"),
    ])
    def test_sharp_read_as_stroke_is_repaired(self, text, expected):
        assert _filter_one(text) == [(expected, None)]

    def test_sharp_repair_applies_below_main_threshold(self):
        assert _filter_one("Clm", confidence=0.75) == [("C#m", None)]

    @pytest.mark.parametrize("text", [
        "Elm",  # E#/B# are not conventional roots
        "Blm",
        "Cl",   # no chord syntax after the stroke
        "CH",
        "Al",
        "Dim",  # "i" is excluded: it would collide with dim
        "Cim",
    ])
    def test_sharp_repair_rejects_non_chords(self, text):
        assert _filter_one(text) == []


class TestFullyParenthesizedChords:
    @pytest.mark.parametrize("text,expected", [
        ("(Am7)", "Am7"),
        ("(G/B)", "G/B"),
        ("(F#m7(b5))", "F#m7b5"),
        ("(Am7bs)", "Am7b5"),
        ("(Clm)", "C#m"),
        (" (Dsus4) ", "Dsus4"),
    ])
    def test_single_wrapped_chord_is_one_occurrence(self, text, expected):
        assert _filter_one(text) == [(expected, "both")]

    @pytest.mark.parametrize("text", ["(Am7G)", "(Am7Dm7)", "(Am)(G)", "(Xyz)", "()"])
    def test_wrapped_concatenated_or_invalid_rows_are_rejected(self, text):
        assert _filter_one(text) == []

    def test_chord_with_parenthesized_alternative_row_marks_open_and_close(self):
        assert _filter_one("C(Am7G)") == [("C", None), ("Am7", "open"), ("G", "close")]

    @pytest.mark.parametrize("text", ["A7(sus4)", "C(add9)", "G(b5)"])
    def test_parenthesized_modifier_is_not_a_wrapped_chord(self, text):
        assert _filter_one(text) == [(text, None)]


class TestSmallGlyphConfusions:
    @pytest.mark.parametrize("text,expected", [
        ("FIA", "F/A"),
        ("GlB", "G/B"),
        ("Bm7IA", "Bm7/A"),
        ("Bradd2", "Bbadd2"),
        ("Brm7", "Bbm7"),
        ("Arsus4", "Absus4"),
        ("Cto", "C#dim"),
        ("Cto7", "C#dim7"),
        ("C#o7", "C#dim7"),
        ("G7(9)", "G7(9)"),
    ])
    def test_repaired(self, text, expected):
        assert _filter_one(text) == [(expected, None)]

    @pytest.mark.parametrize("text", [
        "Bread", "Br",     # flat repair needs chord syntax after "r"
        "Frm", "Crm",      # Fb/Cb are not conventional roots
        "Ct", "Cto3",      # "t" is a sharp only before chord syntax
        "Go", "Co",        # a bare "o" is a word, not diminished
        "Al", "Gl",        # no bass note after the stroke
        "C03", "Am7b05",   # extensions never start with zero
    ])
    def test_rejected(self, text):
        assert _filter_one(text) == []


class TestShortRescuedRoots:
    @staticmethod
    def _page(extra):
        chords = [
            {"text": t, "confidence": 1.0, "bbox": [i * 60, 100, i * 60 + 40, 124]}
            for i, t in enumerate(["G", "D/F#", "Em7", "C", "Am7"])
        ]
        return chords + [extra]

    def test_short_low_confidence_root_is_dropped(self):
        noise = {"text": "F", "confidence": 0.6, "bbox": [400, 130, 410, 138]}

        result = filter_candidates(self._page(noise))

        assert "F" not in [i["text"] for i in result]

    @pytest.mark.parametrize("extra", [
        {"text": "F", "confidence": 0.99, "bbox": [400, 130, 410, 138]},  # confident: kept
        {"text": "F", "confidence": 0.6, "bbox": [400, 100, 415, 122]},   # full height: kept
        {"text": "F7", "confidence": 0.6, "bbox": [400, 130, 410, 138]},  # not a bare root: kept
    ])
    def test_other_detections_are_kept(self, extra):
        result = filter_candidates(self._page(extra))

        assert extra["text"] in [i["text"] for i in result]

    def test_too_few_items_for_a_median_keeps_everything(self):
        items = [
            {"text": "G", "confidence": 1.0, "bbox": [0, 100, 40, 124]},
            {"text": "F", "confidence": 0.6, "bbox": [60, 130, 70, 138]},
        ]

        assert [i["text"] for i in filter_candidates(items)] == ["G", "F"]


@pytest.mark.parametrize("text", ["G7", "G9", "G11", "G13", "C69", "C6", "C2", "Am7b5", "C7#11", "G7b13", "Cm7b6"])
def test_chord_candidate_accepts_musical_extension_degrees(text):
    assert is_chord_candidate(text)


@pytest.mark.parametrize("text", ["G1", "C3", "C8", "C10", "Cm12", "D7b8"])
def test_chord_candidate_rejects_non_musical_extension_numbers(text):
    assert not is_chord_candidate(text)
