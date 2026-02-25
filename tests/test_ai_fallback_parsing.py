"""Unit tests for backend/ocr/ai_fallback.py and hybrid_detect.py.

All tests use the mock provider — no API key or network access needed.
Tests that exercise hybrid_detect inject synthetic OCR results via monkeypatching
so no PaddleOCR engine is loaded.
"""
import pytest

from backend.ocr.ai_fallback import (
    AIFallbackResult,
    ai_detect_chords_rows,
    flatten_rows_to_items,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _item(text: str, conf: float = 0.95) -> dict:
    return {"text": text, "confidence": conf, "bbox": [0, 0, 10, 10]}


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------

class TestMockProvider:
    def test_returns_result(self):
        result = ai_detect_chords_rows("any_path.jpg", provider="mock")
        assert isinstance(result, AIFallbackResult)

    def test_used_mock_is_true(self):
        result = ai_detect_chords_rows("any_path.jpg", provider="mock")
        assert result.used_mock is True

    def test_rows_is_empty_list(self):
        result = ai_detect_chords_rows("any_path.jpg", provider="mock")
        assert result.rows == []

    def test_provider_name(self):
        result = ai_detect_chords_rows("any_path.jpg", provider="mock")
        assert result.provider == "mock"

    def test_raw_response_is_none(self):
        result = ai_detect_chords_rows("any_path.jpg", provider="mock")
        assert result.raw_response_text is None

    def test_meta_has_latency(self):
        result = ai_detect_chords_rows("any_path.jpg", provider="mock")
        assert "latency_ms" in result.meta

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown AI provider"):
            ai_detect_chords_rows("any_path.jpg", provider="openai")


# ---------------------------------------------------------------------------
# flatten_rows_to_items
# ---------------------------------------------------------------------------

class TestFlattenRows:
    def test_valid_chords_are_kept(self):
        rows  = [["D", "Asus4", "G/B"]]
        items = flatten_rows_to_items(rows)
        texts = [i["text"] for i in items]
        assert texts == ["D", "Asus4", "G/B"]

    def test_invalid_strings_are_dropped(self):
        rows  = [["notachord", "D", "hello"]]
        items = flatten_rows_to_items(rows)
        assert len(items) == 1
        assert items[0]["text"] == "D"

    def test_multi_row(self):
        rows  = [["D", "Am"], ["G", "Em7"]]
        items = flatten_rows_to_items(rows)
        assert len(items) == 4

    def test_normalisation_applied(self):
        """Case-folded or noise-prefixed chords should be cleaned."""
        rows  = [["GmAj7", "B_m7"]]    # normalize_chord_text handles both
        items = flatten_rows_to_items(rows)
        texts = [i["text"] for i in items]
        assert "Gmaj7" in texts
        assert "Bm7"   in texts

    def test_confidence_is_one(self):
        items = flatten_rows_to_items([["D"]])
        assert items[0]["confidence"] == 1.0

    def test_bbox_is_none(self):
        items = flatten_rows_to_items([["D"]])
        assert items[0]["bbox"] is None

    def test_empty_rows(self):
        assert flatten_rows_to_items([]) == []

    def test_empty_inner_list(self):
        assert flatten_rows_to_items([[]]) == []


# ---------------------------------------------------------------------------
# hybrid_detect — gate pass / fail behaviour (no real OCR engine)
# ---------------------------------------------------------------------------

class TestHybridDetect:
    """These tests monkeypatch run_ocr_paddle so no PaddlePaddle is loaded."""

    def _make_paddle_result(self, texts: list[str]) -> tuple[list[dict], dict]:
        """Synthetic run_ocr_paddle output."""
        items = [_item(t) for t in texts]
        meta  = {
            "crop_mode":    "top40_fallback",
            "num_regions":  1,
            "stitched":     False,
            "predict_calls": 1,
            "regions":      [{"y0": 0, "h": 100, "staff_top": None, "staff_bottom": None}],
        }
        return items, meta

    def test_paddle_result_used_when_gate_passes(self, monkeypatch):
        """When gate passes, final items are the Paddle chord candidates."""
        # 10 healthy parseable chords → gate should pass
        healthy = ["D", "A", "Bm7", "G", "F#m", "Em", "Asus4", "Dmaj7", "Gmaj7", "Am"]
        paddle_items, paddle_meta = self._make_paddle_result(healthy)

        import backend.ocr.hybrid_detect as hd
        monkeypatch.setattr(hd, "run_ocr_paddle", lambda _: (paddle_items, paddle_meta))

        items, meta = hd.detect_chords_hybrid("fake.jpg", ai_provider="mock")

        assert meta["gate"]["pass"] is True
        assert meta["ai_used"] is False
        # All healthy chords should appear in result
        result_texts = {i["text"] for i in items}
        assert result_texts >= set(healthy)

    def test_ai_used_when_gate_fails_and_mock_has_rows(self, monkeypatch):
        """When gate fails, AI result replaces Paddle if rows are non-empty."""
        # Only 3 chords → gate fails on MIN_PARSEABLE_UNIQUE
        bad_paddle_items, paddle_meta = self._make_paddle_result(["D", "A", "G"])

        # Provide a mock that returns real rows
        def mock_ai(*_args, provider="mock", **_kw):
            return AIFallbackResult(
                rows=[["D", "Asus4", "A", "Bm7", "G", "F#m", "Em", "Dmaj7"]],
                provider="mock",
                raw_response_text=None,
                used_mock=True,
                meta={"latency_ms": 0},
            )

        import backend.ocr.hybrid_detect as hd
        monkeypatch.setattr(hd, "run_ocr_paddle", lambda _: (bad_paddle_items, paddle_meta))
        monkeypatch.setattr(hd, "ai_detect_chords_rows", mock_ai)

        items, meta = hd.detect_chords_hybrid("fake.jpg", ai_provider="mock")

        assert meta["gate"]["pass"] is False
        assert meta["ai_used"] is True
        # Items should come from AI rows
        texts = [i["text"] for i in items]
        assert "Asus4" in texts

    def test_paddle_kept_when_ai_disabled(self, monkeypatch):
        """use_ai_fallback=False keeps Paddle even when gate fails."""
        bad_paddle_items, paddle_meta = self._make_paddle_result(["D", "A", "G"])

        import backend.ocr.hybrid_detect as hd
        monkeypatch.setattr(hd, "run_ocr_paddle", lambda _: (bad_paddle_items, paddle_meta))

        items, meta = hd.detect_chords_hybrid(
            "fake.jpg", use_ai_fallback=False, ai_provider="mock"
        )

        assert meta["gate"]["pass"] is False
        assert meta["ai_used"] is False
        # Paddle items (which pass strict) should be in result
        texts = [i["text"] for i in items]
        assert "D" in texts

    def test_paddle_kept_when_ai_returns_empty_rows(self, monkeypatch):
        """If AI returns empty rows (e.g. mock), fall through to Paddle result."""
        bad_paddle_items, paddle_meta = self._make_paddle_result(["D", "A", "G"])

        import backend.ocr.hybrid_detect as hd
        monkeypatch.setattr(hd, "run_ocr_paddle", lambda _: (bad_paddle_items, paddle_meta))
        # mock provider returns [] rows by default — no monkeypatching needed

        items, meta = hd.detect_chords_hybrid("fake.jpg", ai_provider="mock")

        assert meta["ai_used"] is False   # rows was [], so AI not "used"

    def test_meta_shape(self, monkeypatch):
        """hybrid_detect meta contains all expected keys."""
        paddle_items, paddle_meta = self._make_paddle_result(
            ["D", "A", "Bm7", "G", "F#m", "Em", "Asus4", "Dmaj7", "Gmaj7", "Am"]
        )
        import backend.ocr.hybrid_detect as hd
        monkeypatch.setattr(hd, "run_ocr_paddle", lambda _: (paddle_items, paddle_meta))

        _, meta = hd.detect_chords_hybrid("fake.jpg")

        for key in ("gate", "ai_used", "ai_provider", "recovery",
                    "crop_mode", "num_regions"):
            assert key in meta, f"Missing key: {key}"
        assert "pass"    in meta["gate"]
        assert "score"   in meta["gate"]
        assert "reasons" in meta["gate"]
        assert "stats"   in meta["gate"]
