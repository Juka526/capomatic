#!/usr/bin/env python3
"""Draw detected chord bounding boxes on fixture images.

Usage
-----
    # All fixture images
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True python scripts/bbox_debug.py

    # Single image
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True python scripts/bbox_debug.py --image "fixtures/images/친구야.jpeg"

Writes
------
    tmp/debug_bboxes_<stem>.png  — original image with chord bbox overlays

Color coding
------------
    Green  (conf >= 0.90) — high-confidence detection
    Orange (conf >= 0.78) — medium confidence
    Red    (conf <  0.78) — rescued (below normal threshold)
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Union

from PIL import Image, ImageDraw, ImageFont

from backend.ocr.paddle_ocr import run_ocr_paddle
from backend.ocr.filter import filter_candidates

_FIXTURES_DIR = Path("fixtures/images")
_OUT_DIR = Path("tmp")
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

_COLOR_HIGH   = (0,   200,  80)   # green  — conf >= 0.90
_COLOR_MID    = (255, 160,   0)   # orange — conf >= 0.78
_COLOR_LOW    = (220,  50,  50)   # red    — rescued

try:
    _FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size=14)
except Exception:
    _FONT = ImageFont.load_default()


def _conf_color(conf: float) -> tuple:
    if conf >= 0.90:
        return _COLOR_HIGH
    elif conf >= 0.78:
        return _COLOR_MID
    return _COLOR_LOW


def bbox_debug_single(image_path: Union[str, Path]) -> str:
    """Run OCR on *image_path*, draw chord bboxes, save to tmp/debug_bboxes_<stem>.png."""
    image_path = Path(image_path)
    raw_items, _ = run_ocr_paddle(str(image_path))
    chord_items = filter_candidates(raw_items)

    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    for item in chord_items:
        bbox = item.get("bbox")
        if bbox is None:
            continue
        x1, y1, x2, y2 = bbox
        color = _conf_color(item["confidence"])

        # Bounding box rectangle
        draw.rectangle([x1, y1, x2, y2], outline=color, width=2)

        # Chord label — draw above the box, fall back to inside if at image top
        label = item["text"]
        label_y = y1 - 15 if y1 >= 15 else y2 + 2
        draw.text((x1, label_y), label, fill=color, font=_FONT)

    _OUT_DIR.mkdir(exist_ok=True)
    out_path = _OUT_DIR / f"debug_bboxes_{image_path.stem}.png"
    img.save(str(out_path))
    return str(out_path)


def main() -> None:
    if "--image" in sys.argv:
        idx = sys.argv.index("--image")
        if idx + 1 >= len(sys.argv):
            print("Error: --image requires a path argument")
            sys.exit(1)
        images = [Path(sys.argv[idx + 1])]
    else:
        images = sorted(
            p for p in _FIXTURES_DIR.iterdir()
            if p.suffix.lower() in _IMAGE_EXTS
        )

    if not images:
        print(f"No images found in {_FIXTURES_DIR}")
        sys.exit(1)

    print(f"Processing {len(images)} image(s)...\n")

    passed = 0
    failed = 0
    for img_path in images:
        print(f"  {img_path.name}", end=" ... ", flush=True)
        try:
            out = bbox_debug_single(img_path)
            print(f"saved → {out}")
            passed += 1
        except Exception as exc:
            print(f"ERROR: {exc}")
            failed += 1

    print(f"\nDone. {passed} saved, {failed} failed.")
    print(f"Output directory: {_OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
