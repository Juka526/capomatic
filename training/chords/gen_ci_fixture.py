"""Deterministic generator for fixtures/images/ci-selfmade.png.

Original chord/staff page drawn with Pillow and the pinned DejaVu Sans font
only (no system-font fallback). CI-diagnostic material, NEVER holdout truth.
Usage: python training/chords/gen_ci_fixture.py [--check]
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONT = ROOT / "training/chords/fonts/DejaVuSans.ttf"
OUT = ROOT / "fixtures/images/ci-selfmade.png"
MANIFEST = ROOT / "training/chords/manifest.json"

# Original progression composed for this fixture (4 bars per system).
SYSTEMS = [
    (["G", "D/F#", "Em7", "C"], "la la la la la la la la"),
    (["Am7", "D7", "Bm7", "Em"], "la la la la la la la la"),
    (["C", "G/B", "Am7", "D"], "la la la la la la la la"),
]
CHORDS = [c for chords, _ in SYSTEMS for c in chords]

W, LEFT, BAR_W, GAP = 1100, 60, 240, 14
TOP0, SYS_STEP = 130, 190


def render() -> Image.Image:
    img = Image.new("RGB", (W, 700), "white")
    d = ImageDraw.Draw(img)
    chord_f = ImageFont.truetype(str(FONT), 34)
    lyric_f = ImageFont.truetype(str(FONT), 22)
    for s, (chords, lyric) in enumerate(SYSTEMS):
        top = TOP0 + s * SYS_STEP
        right = LEFT + BAR_W * len(chords)
        for i in range(5):
            d.line([(LEFT, top + i * GAP), (right, top + i * GAP)], fill="black", width=2)
        for b in range(len(chords) + 1):
            x = LEFT + b * BAR_W
            d.line([(x, top), (x, top + 4 * GAP)], fill="black", width=3 if b in (0, len(chords)) else 2)
        for b, chord in enumerate(chords):
            x = LEFT + b * BAR_W
            d.text((x + 12, top - 62), chord, font=chord_f, fill="black")
            for n in range(3):  # three quarter notes per bar, fixed pitches
                cx, cy = x + 55 + n * 65, top + (2 + (b + n) % 3) * GAP
                d.ellipse([cx - 9, cy - 7, cx + 9, cy + 7], fill="black")
                d.line([(cx + 8, cy), (cx + 8, cy - 44)], fill="black", width=2)
        d.text((LEFT + 12, top + 4 * GAP + 24), lyric, font=lyric_f, fill="black")
    return img


def main() -> int:
    img = render()
    if "--check" in sys.argv:
        got = hashlib.sha256(OUT.read_bytes()).hexdigest()
        want = next(i["sha256"] for i in json.loads(MANIFEST.read_text())["items"] if i["path"] == "fixtures/images/ci-selfmade.png")
        print("committed png matches manifest:", got == want)
        return 0 if got == want else 1
    img.save(OUT, optimize=False)
    print(OUT, hashlib.sha256(OUT.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
