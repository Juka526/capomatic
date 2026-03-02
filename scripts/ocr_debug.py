#!/usr/bin/env python3
"""Offline OCR debug script.

Usage
-----
    python scripts/ocr_debug.py "fixtures/images/<filename>"

Prints
------
  - crop mode (staff_bands or top40_fallback) and region breakdown
  - load / OCR / filter timing breakdown
  - total raw detections and chord candidates
  - up to 30 candidates with confidence and bbox

Writes
------
  tmp/debug_regions.png  — original image with OCR bands highlighted
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image, ImageDraw
from backend.ocr.paddle_ocr import run_ocr_paddle
from backend.ocr.filter import filter_candidates, recover_candidates, is_chord_candidate, CONFIDENCE_THRESHOLD


# Colours for region rectangles (cycles if > 6 regions)
_BAND_COLOURS = [
    (0, 120, 215),    # blue
    (0, 153, 76),     # green
    (204, 85, 0),     # orange
    (153, 0, 153),    # purple
    (0, 153, 153),    # teal
    (180, 0, 0),      # red
]


def _draw_overlay(image_path: str, meta: dict) -> str:
    """Draw band rectangles on the original image and save to tmp/."""
    img = Image.open(image_path).convert("RGB")
    W, H = img.size
    draw = ImageDraw.Draw(img)

    for i, region in enumerate(meta["regions"]):
        colour = _BAND_COLOURS[i % len(_BAND_COLOURS)]
        y0 = region["y0"]
        y1 = y0 + region["h"]
        # Band rectangle
        draw.rectangle([0, y0, W - 1, y1], outline=colour, width=3)
        # Label
        label = f"R{i + 1} y={y0}–{y1}"
        if region.get("line_spacing") is not None:
            label += (
                f" ls={region['line_spacing']:.1f}"
                f" gap={region['gap_above']}"
                f" below={region['pad_below']}"
            )
        draw.text((4, max(0, y0 + 2)), label, fill=colour)

    os.makedirs("tmp", exist_ok=True)
    out_path = "tmp/debug_regions.png"
    img.save(out_path)
    return out_path


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/ocr_debug.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(f"[ERROR] File not found: {image_path}")
        sys.exit(1)

    print(f"Image : {image_path}")
    print("-" * 60)

    # --- OCR (includes image open, staff detection, band crops) ---
    t0 = time.perf_counter()
    raw_items, meta = run_ocr_paddle(image_path)
    ocr_ms = (time.perf_counter() - t0) * 1000

    # --- Filter (strict + recovery) ---
    t1 = time.perf_counter()
    confident_items = [i for i in raw_items if i["confidence"] > CONFIDENCE_THRESHOLD]
    strict_items = [i for i in confident_items if is_chord_candidate(i["text"])]
    failed_items = [i for i in confident_items if not is_chord_candidate(i["text"])]
    recovered, parse_count, split_count = recover_candidates(failed_items)
    chord_items = strict_items + recovered
    filter_ms = (time.perf_counter() - t1) * 1000

    # --- Crop mode + region breakdown ---
    print(f"Crop mode         : {meta['crop_mode']}")
    print(f"Regions           : {meta['num_regions']}")
    for i, r in enumerate(meta["regions"]):
        y1 = r["y0"] + r["h"]
        staff_str = ""
        if r.get("staff_top") is not None:
            staff_str = f"  →  staff y={r['staff_top']}–{r['staff_bottom']}"
        print(f"  Region {i + 1:<2}      : y={r['y0']}–{y1}  (h={r['h']}){staff_str}")
    print()

    # --- Timing + counts ---
    print(f"Raw detections    : {len(raw_items)}")
    print(f"Strict pass       : {len(strict_items)}")
    print(f"Recovered (parse) : {parse_count}")
    print(f"Recovered (split) : {split_count}")
    print(f"Total kept        : {len(chord_items)}")
    print(f"OCR time          : {ocr_ms:.1f} ms")
    print(f"Filter time       : {filter_ms:.1f} ms")
    print(f"Total             : {ocr_ms + filter_ms:.1f} ms")
    if meta.get("predict_ms") is not None:
        print(f"  preprocess      : {meta['preprocess_ms']:.1f} ms")
        print(f"  stitch          : {meta['stitch_ms']:.1f} ms")
        print(f"  predict         : {meta['predict_ms']:.1f} ms")
        print(f"  post            : {meta['post_ms']:.1f} ms")
        print(f"  paddle total    : {meta['total_ms']:.1f} ms")
    if meta.get("stitched_shape"):
        H, W = meta["stitched_shape"]
        print(f"Stitched shape    : {H}×{W}  ({meta['stitched_pixels']:,} px)")
    if meta.get("resize_applied"):
        H, W = meta["resized_shape"]
        print(f"Resize applied    : scale={meta['resize_scale']:.3f}  → {H}×{W}")
    if split_count > 0:
        print()
        print("Split recoveries:")
        for item in failed_items:
            from backend.ocr.filter import _split_concatenated  # noqa: PLC0415
            parts = _split_concatenated(item["text"])
            if parts:
                print(f'  "{item["text"]}"  →  "{parts[0]}" + "{parts[1]}"')
    print()

    # --- Quality gate (shown when hybrid_detect was used, skipped for raw paddle) ---
    if meta.get("gate"):
        g = meta["gate"]
        gate_str = "PASS" if g["pass"] else f"FAIL – {'; '.join(g['reasons'])}"
        print(f"Gate              : {gate_str}  (score={g['score']:.3f})")
        s = g["stats"]
        print(f"  strict={s['strict_count']}  recovered={s['recovered_count']}"
              f"  failed={s['failed_count']}  suspicious={s['suspicious_count']}"
              f"  parseable_unique={s['parseable_unique']}")
        print(f"AI used           : {meta.get('ai_used', False)}"
              + (f"  (provider={meta['ai_provider']})" if meta.get("ai_used") else ""))
        print()

    # --- Debug overlay image ---
    overlay_path = _draw_overlay(image_path, meta)
    print(f"Debug overlay     : {overlay_path}")
    print()

    if not chord_items:
        print("No chord candidates detected.")
        return

    # --- Candidate table (first 30) ---
    print(f"Candidates (showing up to 30 of {len(chord_items)}):")
    print(f"  {'#':<5}{'Text':<16}{'Conf':>6}   BBox")
    print("  " + "-" * 52)
    for i, item in enumerate(chord_items[:30]):
        print(
            f"  {i + 1:<5}{item['text']:<16}{item['confidence']:>6.3f}"
            f"   {item['bbox']}"
        )


if __name__ == "__main__":
    main()