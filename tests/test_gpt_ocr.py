"""Unit tests for GPT vision OCR post-processing."""
from __future__ import annotations

from PIL import Image, ImageDraw

from backend.ocr import gpt_ocr
from backend.ocr.filter import recover_candidates


def test_bbox_from_pct_accepts_fraction_values():
    chord = {
        "x_pct": 0.25,
        "y_pct": 0.10,
        "w_pct": 0.05,
        "h_pct": 0.02,
    }

    assert gpt_ocr._bbox_from_pct(chord, 1000, 500) == [250, 50, 300, 60]


def test_bbox_from_pct_accepts_percent_values():
    chord = {
        "x_pct": 25,
        "y_pct": 10,
        "w_pct": 5,
        "h_pct": 2,
    }

    assert gpt_ocr._bbox_from_pct(chord, 1000, 500) == [250, 50, 300, 60]


def test_refine_bbox_to_glyph_tightens_loose_box_and_ignores_staff_line():
    img = Image.new("L", (160, 90), 255)
    draw = ImageDraw.Draw(img)
    draw.text((52, 20), "Am7", fill=0)
    draw.line((0, 55, 159, 55), fill=0)

    refined = gpt_ocr._refine_bbox_to_glyph(img, [40, 10, 110, 65])

    assert refined[0] >= 48
    assert refined[1] >= 18
    assert refined[2] <= 80
    assert refined[3] < 55


def test_refine_bbox_to_glyph_can_snap_from_staff_to_chord_band():
    img = Image.new("L", (180, 120), 255)
    draw = ImageDraw.Draw(img)
    draw.text((52, 24), "G", fill=0)
    for y in (60, 66, 72, 78, 84):
        draw.line((0, y, 179, y), fill=0)

    regions = [{
        "y0": 12,
        "h": 48,
        "staff_top": 60,
        "staff_bottom": 84,
    }]

    refined = gpt_ocr._refine_bbox_to_glyph(img, [50, 80, 70, 105], regions)

    assert refined[0] >= 50
    assert refined[1] < 60
    assert refined[3] < 60


def test_existing_recovery_rules_handle_concatenated_gpt_chords():
    items = [{
        "text": "Em7G/A",
        "confidence": 1.0,
        "bbox": [10, 20, 90, 40],
    }]

    recovered, _, split_count = recover_candidates(items)

    assert split_count == 1
    assert [item["text"] for item in recovered] == ["Em7", "G/A"]
    assert recovered[0]["bbox"] == [10, 20, 50, 40]
    assert recovered[1]["bbox"] == [50, 20, 90, 40]
