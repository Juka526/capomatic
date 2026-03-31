# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

capomatic takes a church worship chord sheet image, detects chord symbols via OCR, transposes them by a given number of semitones, and renders the transposed chords back onto the image.

## Commands

```bash
# Run all tests
python -m pytest

# Run a single test file
python -m pytest tests/test_render.py -v

# Run a specific test
python -m pytest tests/test_render.py::TestRenderOverlay::test_above_mode_returns_image

# Debug OCR on a single image (writes tmp/debug_regions.png)
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True python scripts/ocr_debug.py "fixtures/images/<filename>"

# Evaluate OCR accuracy against all fixtures
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True python scripts/eval_ocr.py --engine paddle

# Start API server
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True uvicorn backend.api.main:app --port 8000

# Test overlay via API
curl -X POST http://localhost:8000/overlay \
  -F "image=@fixtures/images/친구야.jpeg" \
  -F "semitones=-1" \
  -F "mode=replace" \
  -o tmp/overlay_output.png
```

Note: `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True` is required for any command that loads PaddleOCR models.

## Architecture

The pipeline flows: **Image -> Preprocess -> OCR -> Filter -> Key Detect -> Transpose -> Overlay Render**.

### backend/ocr/ — Detection pipeline

- `preprocess.py`: Staff-aware band cropping. Detects staff systems via morphological analysis, crops chord bands above each staff, stitches into a single strip for OCR.
- `paddle_ocr.py`: PaddleOCR runner. Key functions: `run_ocr_paddle()` (main entry), `_apply_direction_filter()` (removes D.S./D.C. tokens), `_split_multi_token()` (handles space-separated multi-chord OCR text).
- `filter.py`: Two-pass chord validation. Pass 1: strict regex (`_CHORD_RE`). Pass 2: recovery — normalize, split concatenated chords, strip leading numbers, trailing "b"->"6" OCR confusion fix. Also `_RESCUE_FLOOR` for low-confidence chord-syntax rescue.
- `hybrid_detect.py`: Orchestrator. Runs PaddleOCR (and optionally Claude Vision in parallel), filters, quality-gates, merges. Default: PaddleOCR-only (`ai_provider="mock"`).
- `ai_fallback.py`: Claude Vision provider (dormant by default, requires `ANTHROPIC_API_KEY`).
- `merge.py`: Aligns Claude rows to PaddleOCR rows by position when AI is active.
- `quality_gate.py`: Diagnostic scoring of OCR quality (informational, does not gate processing).

### backend/chords/ — Parsing and transposition

- `parser.py`: `parse_chord("Am7/G")` -> `Chord(root="A", quality="m", extensions="7", bass="G")`.
- `transpose.py`: `transpose_chord()` with enharmonic spelling via `target_key`. `compute_target_key()` for key name transposition. Standard key names in `_KEY_NAMES`.
- `key_detect.py`: `infer_key()` — Krumhansl-inspired diatonic scoring. Weights: I=4, ii=2, iii=1, IV=3, V=3, vi=2, vii=1. Returns relative major (Am -> "C").
- `normalize.py`: Case normalization for OCR text (e.g., "am7" -> "Am7").

### backend/overlay/ — Rendering

- `render.py`: Two modes — `"above"` (orange text above original) and `"replace"` (white box over original, dark blue text on top). Key behaviors:
  - Font size auto-reduces via `_find_fit_font_size()` when chords would overlap, down to `_MIN_FONT_SIZE`.
  - White boxes contract inward from OCR bbox (15% vertical, 10% horizontal shrink) to avoid erasing surrounding notation.
  - Chords shortened for display: "maj"->"M", sus/dim/aug split to smaller suffix font.
  - Info header shows key, semitone shift, and capo position.

### backend/api/ — FastAPI endpoints

- `main.py`: `/detect` (JSON), `/overlay` (PNG), `/health`. Auto-resolves `original_key` and `target_key` from detected chords when not provided. 20MB upload limit.

## Key Data Structure

The chord item dict flows through the entire pipeline:
```python
{"text": "Am7", "confidence": 0.95, "bbox": [x1, y1, x2, y2]}
```
After transposition, `"transposed"` is added. `bbox` is `None` for AI-only detections.

## Coding Conventions

- Python 3.12, PEP 8, snake_case functions, UPPER_SNAKE_CASE constants.
- pytest with Arrange-Act-Assert. Use `@pytest.mark.parametrize` to consolidate similar tests.
- Private helpers prefixed with `_`. Public API functions have docstrings.
- Prefer editing existing files over creating new ones.
- Keep `try` blocks small; raise specific exceptions (`ValueError`, `KeyError`).
- Comments explain "why", not "what".
