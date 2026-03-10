"""Chord overlay rendering for transchord.

Renders transposed chord symbols onto a PIL image using one of two modes:

  above   — orange transposed chord printed above each original chord.
             One uniform font size across all rows (median bbox height × scale).
             Labels within a row are shifted right as needed to avoid horizontal
             overlap.  If the row has insufficient space above it, white rows
             are inserted to create room.
  replace — semi-transparent white box covers the original chord; new chord
             rendered on top in dark blue at the same position.
"""
from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw, ImageFont

# Bundled font: BravuraText (Steinberg, SIL OFL) — music-engraving style.
_FONT_PATH = pathlib.Path(__file__).parent / "fonts" / "BravuraText.otf"

# Font size = bbox_height * this scale; reduced further if h-overlap detected.
_FONT_SCALE    = 0.85
_MIN_FONT_SIZE = 14   # never render below this — keeps labels legible

# Vertical gap (px) between the bottom of a label and the top of its chord box.
_GAP = 4

# Colours
_ORANGE     = (255, 140, 0)
_DARK_BLUE  = (0, 0, 160)
_WHITE_RGBA = (255, 255, 255, 210)   # ~82% opaque for replace boxes


# ---------------------------------------------------------------------------
# Font loader
# ---------------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.ImageFont:
    """Return BravuraText at *size* pt, falling back to the PIL default font."""
    size = max(_MIN_FONT_SIZE, size)
    if _FONT_PATH.exists():
        try:
            return ImageFont.truetype(str(_FONT_PATH), size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)  # type: ignore[call-arg]
    except TypeError:
        return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_overlay(
    img: Image.Image,
    chords: list[dict],
    mode: str,
) -> Image.Image:
    """Render transposed chord symbols onto *img* and return a new RGB image.

    Parameters
    ----------
    img    : PIL RGB image (original, not modified in-place).
    chords : List of dicts with keys: text, transposed, bbox.
             Entries where transposed or bbox is None are skipped.
    mode   : "above" or "replace".
    """
    eligible = [
        c for c in chords
        if c.get("transposed") is not None and c.get("bbox") is not None
    ]

    if mode == "above":
        return _render_above(img.copy(), eligible)
    else:
        return _render_replace(img.copy(), eligible)


# ---------------------------------------------------------------------------
# above mode — labels placed ABOVE the original chord boxes
# ---------------------------------------------------------------------------

def _cluster_by_row(chords: list[dict]) -> list[list[dict]]:
    """Group chords into horizontal rows by proximity of their y1 coordinates."""
    if not chords:
        return []
    avg_h = sum(c["bbox"][3] - c["bbox"][1] for c in chords) / len(chords)
    threshold = max(20, int(avg_h * 1.5))
    sorted_c = sorted(chords, key=lambda c: c["bbox"][1])
    rows: list[list[dict]] = [[sorted_c[0]]]
    for c in sorted_c[1:]:
        row_min_y1 = min(x["bbox"][1] for x in rows[-1])
        if c["bbox"][1] - row_min_y1 <= threshold:
            rows[-1].append(c)
        else:
            rows.append([c])
    return rows


def _text_width(font: ImageFont.ImageFont, text: str) -> float:
    try:
        return font.getlength(text)
    except AttributeError:
        return font.getsize(text)[0]  # type: ignore[attr-defined]


def _place_row_labels(
    row: list[dict],
    font: ImageFont.ImageFont,
    img_width: int,
    h_gap: int = 3,
) -> list[tuple[dict, int]]:
    """Return [(chord, label_x), ...] shifted right to avoid horizontal overlap.

    Each label starts at chord["bbox"][0] but is nudged right if it would
    overlap the previous label.  The rightmost label is clamped to the image
    width so nothing overflows off-screen.
    """
    sorted_row = sorted(row, key=lambda c: c["bbox"][0])
    result: list[tuple[dict, int]] = []
    prev_right = -h_gap
    for chord in sorted_row:
        tw = int(_text_width(font, chord["transposed"]))
        x = max(chord["bbox"][0], prev_right + h_gap)
        x = min(x, max(0, img_width - tw))   # clamp to image edge
        result.append((chord, x))
        prev_right = x + tw
    return result


def _insert_whitespace(
    img: Image.Image,
    expansions: list[tuple[int, int]],
) -> Image.Image:
    """Return a new image with white rows inserted at the given y positions.

    Parameters
    ----------
    expansions : list of (y_insert, extra_pixels) in ascending order of y_insert.
                 White space is inserted AT y_insert, pushing everything below
                 further down.
    """
    W, H = img.size
    total_extra = sum(e for _, e in expansions)
    new_img = Image.new("RGB", (W, H + total_extra), (255, 255, 255))
    src_y = 0
    dst_y = 0
    for y_insert, extra in sorted(expansions):
        if y_insert > src_y:
            strip = img.crop((0, src_y, W, y_insert))
            new_img.paste(strip, (0, dst_y))
            dst_y += y_insert - src_y
        dst_y += extra          # white gap already initialised in Image.new
        src_y = y_insert
    if src_y < H:
        strip = img.crop((0, src_y, W, H))
        new_img.paste(strip, (0, dst_y))
    return new_img


def _render_above(img: Image.Image, chords: list[dict]) -> Image.Image:
    W, H = img.size
    rows = _cluster_by_row(chords)
    if not rows:
        return img

    # ------------------------------------------------------------------
    # Global uniform font size — median bbox height across all chords.
    # ------------------------------------------------------------------
    all_heights = sorted(c["bbox"][3] - c["bbox"][1] for c in chords)
    median_h  = all_heights[len(all_heights) // 2]
    font_size = max(_MIN_FONT_SIZE, int(median_h * _FONT_SCALE))
    font      = _load_font(font_size)

    # ------------------------------------------------------------------
    # Pass 1 — check vertical space per row; record expansions needed.
    # ------------------------------------------------------------------
    expansions: list[tuple[int, int]] = []  # (y_insert_orig, extra_px)
    prev_max_y2 = 0

    for row in rows:
        min_y1 = min(c["bbox"][1] for c in row)
        max_y2 = max(c["bbox"][3] for c in row)
        space_orig = min_y1 - prev_max_y2
        needed     = font_size + _GAP * 2
        if needed > space_orig:
            expansions.append((prev_max_y2, needed - space_orig))
        prev_max_y2 = max_y2

    # ------------------------------------------------------------------
    # Pass 2 — expand the image where needed.
    # ------------------------------------------------------------------
    if expansions:
        img = _insert_whitespace(img, expansions)

    # ------------------------------------------------------------------
    # Pass 3 — cumulative y-offset per row after expansion.
    # ------------------------------------------------------------------
    sorted_expansions = sorted(expansions)

    def _y_offset_for(orig_y1: int) -> int:
        return sum(extra for y, extra in sorted_expansions if y <= orig_y1)

    # ------------------------------------------------------------------
    # Pass 4 — draw labels with greedy left-to-right x placement.
    # ------------------------------------------------------------------
    draw = ImageDraw.Draw(img)
    for row in rows:
        for chord, label_x in _place_row_labels(row, font, W):
            offset     = _y_offset_for(chord["bbox"][1])
            shifted_y1 = chord["bbox"][1] + offset
            label_y    = shifted_y1 - font_size - _GAP
            draw.text((label_x, label_y), chord["transposed"], fill=_ORANGE, font=font)

    return img


# ---------------------------------------------------------------------------
# replace mode
# ---------------------------------------------------------------------------

def _render_replace(img: Image.Image, chords: list[dict]) -> Image.Image:
    # Pass 1 — draw semi-transparent white boxes via RGBA compositing
    img_rgba = img.convert("RGBA")
    overlay  = Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
    ov_draw  = ImageDraw.Draw(overlay)

    for chord in chords:
        x1, y1, x2, y2 = chord["bbox"]
        ov_draw.rectangle(
            [x1 - 2, y1 - 2, x2 + 2, y2 + 2],
            fill=_WHITE_RGBA,
        )

    composited = Image.alpha_composite(img_rgba, overlay).convert("RGB")

    # Pass 2 — draw transposed text on top of the white boxes
    draw = ImageDraw.Draw(composited)
    for chord in chords:
        x1, y1, x2, y2 = chord["bbox"]
        font_size = int((y2 - y1) * _FONT_SCALE)
        font = _load_font(font_size)
        draw.text((x1, y1), chord["transposed"], fill=_DARK_BLUE, font=font)

    return composited
