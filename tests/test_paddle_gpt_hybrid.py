"""Unit tests for Paddle + GPT hybrid OCR post-processing."""
from __future__ import annotations

from PIL import Image

from backend.ocr import paddle_gpt_hybrid as hybrid


def test_merge_gpt_text_replaces_text_but_keeps_paddle_bbox(monkeypatch):
    monkeypatch.setattr(hybrid, "GPT_TEXT_CONF", 0.70)
    paddle_items = [{
        "text": "D/F",
        "confidence": 0.82,
        "bbox": [10, 20, 50, 40],
    }]
    gpt_by_id = {1: {"text": "D/F#", "confidence": 0.91}}

    merged, replaced, low_conf = hybrid._merge_gpt_text(paddle_items, gpt_by_id)

    assert replaced == 1
    assert low_conf == 0
    assert merged[0]["text"] == "D/F#"
    assert merged[0]["bbox"] == [10, 20, 50, 40]
    assert merged[0]["source"] == "paddle_bbox_gpt_text"


def test_merge_gpt_text_rejects_low_confidence_gpt(monkeypatch):
    monkeypatch.setattr(hybrid, "GPT_TEXT_CONF", 0.70)
    paddle_items = [{
        "text": "D/F",
        "confidence": 0.82,
        "bbox": [10, 20, 50, 40],
    }]
    gpt_by_id = {1: {"text": "D/F#", "confidence": 0.60}}

    merged, replaced, _ = hybrid._merge_gpt_text(paddle_items, gpt_by_id)

    assert replaced == 0
    assert merged[0]["text"] == "D/F"
    assert merged[0]["source"] == "paddle"


def test_dedupe_prefers_paddle_bbox_over_gpt_gap_duplicate():
    items = [
        {
            "text": "Am",
            "confidence": 0.9,
            "bbox": [10, 20, 50, 40],
            "source": "paddle_bbox_gpt_confirmed",
        },
        {
            "text": "Am",
            "confidence": 0.95,
            "bbox": [12, 21, 52, 42],
            "source": "gpt_gap",
        },
    ]

    kept, dropped = hybrid._dedupe_items(items)

    assert dropped == 1
    assert len(kept) == 1
    assert kept[0]["bbox"] == [10, 20, 50, 40]
    assert kept[0]["source"] == "paddle_bbox_gpt_confirmed"


def test_dedupe_prefers_paddle_over_high_recall_gpt_gap_even_with_lower_confidence():
    items = [
        {
            "text": "Am",
            "confidence": 0.70,
            "bbox": [10, 20, 50, 40],
            "source": "paddle",
        },
        {
            "text": "Am",
            "confidence": 0.99,
            "bbox": [12, 21, 52, 42],
            "source": "paddle_high_recall_gpt_gap",
        },
    ]

    kept, dropped = hybrid._dedupe_items(items)

    assert dropped == 1
    assert kept[0]["bbox"] == [10, 20, 50, 40]
    assert kept[0]["source"] == "paddle"


def test_gpt_recognize_crops_batched_preserves_global_ids(monkeypatch):
    img = Image.new("RGB", (300, 200), "white")
    calls = []

    def fake_recognize(image, items, **kwargs):
        calls.append(len(items))
        return (
            {idx: {"text": item["text"], "confidence": 0.95} for idx, item in enumerate(items, start=1)},
            {"usage": {"prompt_tokens": 10, "completion_tokens": 2}},
        )

    monkeypatch.setattr(hybrid, "_gpt_recognize_crops", fake_recognize)

    result, meta = hybrid._gpt_recognize_crops_batched(
        img,
        [
            {"text": "A", "bbox": [0, 0, 10, 10]},
            {"text": "B", "bbox": [10, 0, 20, 10]},
            {"text": "C", "bbox": [20, 0, 30, 10]},
        ],
        batch_size=2,
    )

    assert calls == [2, 1]
    assert sorted(result) == [1, 2, 3]
    assert result[3]["text"] == "C"
    assert meta["batches"] == 2
    assert meta["usage"]["prompt_tokens"] == 20


def test_run_hybrid_without_api_key_returns_paddle_only(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(hybrid, "run_ocr_paddle", lambda path: (
        [{"text": "Am", "confidence": 0.95, "bbox": [10, 20, 50, 40]}],
        {"predict_ms": 1.0},
    ))

    items, meta = hybrid.run_ocr_paddle_gpt_hybrid("fake.jpg")

    assert items == [{"text": "Am", "confidence": 0.95, "bbox": [10, 20, 50, 40]}]
    assert meta["ocr_engine"] == "paddle-only"
    assert meta["gpt_used"] is False


def test_gap_candidate_rejects_tiny_bottom_right_bbox():
    ok, reason = hybrid._valid_gap_candidate_bbox(
        [1279, 1278, 1280, 1279],
        [{"text": "Am", "confidence": 0.9, "bbox": [10, 20, 50, 44]}],
        1280,
        1279,
        [{"y0": 100, "h": 60}],
    )

    assert ok is False
    assert reason == "too_small"


def test_high_recall_candidates_reject_overlap_and_keep_new_box(monkeypatch):
    img = Image.new("RGB", (300, 200), "white")
    existing = [{"text": "Am", "confidence": 0.9, "bbox": [10, 20, 50, 44]}]

    monkeypatch.setattr(hybrid, "run_ocr_paddle", lambda *args, **kwargs: (
        [
            {"text": "Am", "confidence": 0.95, "bbox": [11, 21, 51, 45]},
            {"text": "Fmaj7", "confidence": 0.50, "bbox": [150, 20, 210, 44]},
        ],
        {"predict_ms": 12.0, "total_ms": 20.0},
    ))

    candidates, meta = hybrid._run_high_recall_paddle_candidates(
        img,
        existing,
        [{"y0": 0, "h": 80}],
    )

    assert len(candidates) == 1
    assert candidates[0]["bbox"] == [150, 20, 210, 44]
    assert candidates[0]["source"] == "paddle_high_recall_candidate"
    assert meta["gap_candidate_reject_reasons"]["duplicate"] == 1


def test_gpt_validate_gap_candidates_adds_confirmed_candidate(monkeypatch):
    img = Image.new("RGB", (300, 200), "white")
    candidates = [{
        "text": "Fmaj7",
        "confidence": 0.50,
        "bbox": [150, 20, 210, 44],
        "source": "paddle_high_recall_candidate",
    }]
    monkeypatch.setattr(hybrid, "_gpt_recognize_crops", lambda image, items, **kwargs: (
        {1: {"text": "Fmaj7", "confidence": 0.92}},
        {"usage": {"prompt_tokens": 100, "completion_tokens": 20}},
    ))

    accepted, meta = hybrid._gpt_validate_gap_candidates(img, candidates)

    assert len(accepted) == 1
    assert accepted[0]["text"] == "Fmaj7"
    assert accepted[0]["bbox"] == [150, 20, 210, 44]
    assert accepted[0]["source"] == "paddle_high_recall_gpt_gap"
    assert meta["gpt_gap_candidates_accepted"] == 1


def test_gpt_validate_gap_candidates_splits_concatenated_gpt_text(monkeypatch):
    img = Image.new("RGB", (300, 200), "white")
    candidates = [{
        "text": "",
        "confidence": 0.45,
        "bbox": [100, 20, 180, 44],
        "source": "component_gap_candidate",
    }]
    monkeypatch.setattr(hybrid, "_gpt_recognize_crops", lambda image, items, **kwargs: (
        {
            1: {
                "text": "Abm7",
                "confidence": 0.93,
                "recovered_items": [
                    {"text": "Abm7", "confidence": 0.93, "bbox": [100, 20, 148, 44]},
                    {"text": "Db", "confidence": 0.93, "bbox": [148, 20, 180, 44]},
                ],
            },
        },
        {"usage": {"prompt_tokens": 100, "completion_tokens": 20}},
    ))

    accepted, meta = hybrid._gpt_validate_gap_candidates(img, candidates)

    assert [item["text"] for item in accepted] == ["Abm7", "Db"]
    assert accepted[0]["bbox"] == [100, 20, 148, 44]
    assert accepted[1]["bbox"] == [148, 20, 180, 44]
    assert meta["gpt_gap_candidates_accepted"] == 2


def test_gpt_recognize_crops_recovers_minor_major_ocr_confusion(monkeypatch):
    img = Image.new("RGB", (300, 200), "white")

    monkeypatch.setattr(hybrid, "_request_openai_image", lambda *args, **kwargs: (
        {"items": [{"id": 1, "text": "AbmM7", "confidence": 0.95}]},
        {"usage": {"prompt_tokens": 100, "completion_tokens": 20}},
    ))

    result, _ = hybrid._gpt_recognize_crops(
        img,
        [{"bbox": [100, 20, 150, 44]}],
        recover_invalid=True,
    )

    assert result[1]["text"] == "Abm7"
    assert result[1]["recovered_items"] == [{
        "text": "Abm7",
        "confidence": 0.95,
        "bbox": [100, 20, 150, 44],
    }]


def test_gpt_recognize_crops_repairs_and_splits_joined_gap_chords(monkeypatch):
    img = Image.new("RGB", (300, 200), "white")

    monkeypatch.setattr(hybrid, "_request_openai_image", lambda *args, **kwargs: (
        {"items": [{"id": 1, "text": "AbmM7Abm7Db", "confidence": 0.95}]},
        {"usage": {"prompt_tokens": 100, "completion_tokens": 20}},
    ))

    result, _ = hybrid._gpt_recognize_crops(
        img,
        [{"bbox": [100, 20, 220, 44]}],
        recover_invalid=True,
    )

    assert [item["text"] for item in result[1]["recovered_items"]] == ["Abm7", "Abm7", "Db"]
    assert result[1]["recovered_items"][0]["bbox"] == [100, 20, 148, 44]
    assert result[1]["recovered_items"][2]["bbox"] == [196, 20, 220, 44]


def test_component_gap_candidates_find_dark_glyph_group():
    img = Image.new("RGB", (260, 120), "white")
    px = img.load()
    for x1, y1, x2, y2 in (
        (100, 35, 111, 51),
        (113, 34, 120, 52),
        (123, 34, 136, 51),
        (139, 34, 146, 51),
    ):
        for y in range(y1, y2):
            for x in range(x1, x2):
                px[x, y] = (0, 0, 0)

    candidates, meta = hybrid._component_gap_candidates(
        img,
        [{"text": "Eb", "confidence": 1.0, "bbox": [30, 34, 60, 54]}],
        [{"y0": 20, "h": 60}],
    )

    assert len(candidates) == 1
    assert candidates[0]["bbox"] == [100, 34, 146, 52]
    assert candidates[0]["source"] == "component_gap_candidate"
    assert meta["component_gap_candidate_count"] == 1


def test_refine_adds_high_recall_gpt_gap_without_full_image_gap(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(hybrid, "ENABLE_FULL_IMAGE_GAP_FILL", False)
    monkeypatch.setattr(hybrid, "ENABLE_HIGH_RECALL_GAP_FILL", True)
    monkeypatch.setattr(hybrid, "_gpt_recognize_crops", lambda image, items, **kwargs: (
        {idx: {"text": item["text"], "confidence": 0.95} for idx, item in enumerate(items, start=1)},
        {"usage": {"prompt_tokens": 100, "completion_tokens": 20}},
    ))
    monkeypatch.setattr(hybrid, "run_ocr_paddle", lambda *args, **kwargs: (
        [{"text": "Fmaj7", "confidence": 0.50, "bbox": [150, 20, 210, 44]}],
        {"predict_ms": 12.0, "total_ms": 20.0},
    ))

    items, meta = hybrid.refine_paddle_items_with_gpt(
        Image.new("RGB", (300, 200), "white"),
        [{"text": "Am", "confidence": 0.9, "bbox": [10, 20, 50, 44]}],
        base_meta={"regions": [{"y0": 0, "h": 80}]},
    )

    assert [item["text"] for item in items] == ["Am", "Fmaj7"]
    assert items[1]["source"] == "paddle_high_recall_gpt_gap"
    assert meta["gap_candidate_count"] == 1
    assert meta["gpt_gap_candidates_accepted"] == 1


def test_refine_runs_gap_fill_when_initial_gpt_text_confirmation_fails(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(hybrid, "ENABLE_FULL_IMAGE_GAP_FILL", False)
    monkeypatch.setattr(hybrid, "ENABLE_HIGH_RECALL_GAP_FILL", True)
    monkeypatch.setattr(
        hybrid,
        "_gpt_recognize_crops_batched",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("text timeout")),
    )
    monkeypatch.setattr(hybrid, "_component_gap_candidates", lambda *args, **kwargs: (
        [{"text": "", "confidence": 0.45, "bbox": [100, 20, 150, 44], "source": "component_gap_candidate"}],
        {"component_gap_candidate_count": 1},
    ))
    monkeypatch.setattr(hybrid, "_run_high_recall_paddle_candidates", lambda *args, **kwargs: (
        [],
        {"gap_candidate_count": 1},
    ))
    monkeypatch.setattr(hybrid, "_gpt_validate_gap_candidates", lambda *args, **kwargs: (
        [{"text": "Fmaj7", "confidence": 0.92, "bbox": [100, 20, 150, 44], "source": "paddle_high_recall_gpt_gap"}],
        {
            "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            "gpt_gap_candidates_sent": 1,
            "gpt_gap_candidates_accepted": 1,
            "gpt_gap_candidates_rejected": 0,
        },
    ))

    items, meta = hybrid.refine_paddle_items_with_gpt(
        Image.new("RGB", (300, 200), "white"),
        [{"text": "Am", "confidence": 0.9, "bbox": [10, 20, 50, 44]}],
        base_meta={"regions": [{"y0": 0, "h": 80}]},
    )

    assert [item["text"] for item in items] == ["Am", "Fmaj7"]
    assert meta["gpt_error"] == "text timeout"
    assert meta["gpt_used"] is True
    assert meta["gpt_gap_candidates_accepted"] == 1
