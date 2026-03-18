"""Chord overlay rendering for transchord.

Renders transposed chord symbols onto a PIL image using one of two modes:

  above   — orange transposed chord printed above each original chord.
             One uniform font size across all rows (median bbox height x scale).
             Labels within a row are shifted right as needed to avoid horizontal
             overlap.  If the row has insufficient space above it, white rows
             are inserted to create room.
  replace — fully opaque white box covers the original chord; new chord
             rendered on top in dark blue at the same position.  An info header
             in the upper-left shows original/target key, semitone shift, and
             capo position.
"""
from __future__ import annotations

import pathlib
import re

from PIL import Image, ImageDraw, ImageFont

# Bundled font: BravuraText (Steinberg, SIL OFL) — music-engraving style.
_FONT_PATH = pathlib.Path(__file__).parent / "fonts" / "BravuraText.otf"

# Font size = bbox_height * this scale.
_FONT_SCALE    = 0.85
_MIN_FONT_SIZE = 20   # never render below this — keeps labels legible

# Ratio for the smaller suffix font (sus, dim, aug).
_SMALL_FONT_RATIO = 0.70

# Vertical gap (px) between the bottom of a label and the top of its chord box.
_GAP = 4

# Padding around white boxes in replace mode.
_BOX_PAD = 4

# Colours
_ORANGE     = (255, 140, 0)
_DARK_BLUE  = (0, 0, 160)
_WHITE_RGBA = (255, 255, 255, 255)   # fully opaque for replace boxes
_HEADER_BG  = (255, 255, 255, 220)   # info header background

# Quality/modifier suffixes rendered in smaller font.
_SMALL_SUFFIXES = ("sus", "dim", "aug")


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
# Display text helpers
# ---------------------------------------------------------------------------

def _shorten_chord_display(transposed: str) -> tuple[str, str]:
    """Shorten chord display text and split off suffix for smaller rendering.

    Returns (main_part, small_suffix).  "maj" is replaced with "M" globally.
    The first occurrence of sus/dim/aug splits the text into main + suffix.

    Examples
    --------
    "Bbmaj7"   -> ("BbM7", "")
    "A7sus4"   -> ("A7", "sus4")
    "G#dim"    -> ("G#", "dim")
    "Faug7"    -> ("F", "aug7")
    "Am7"      -> ("Am7", "")
    """
    text = transposed.replace("maj", "M")
    for suffix in _SMALL_SUFFIXES:
        idx = text.find(suffix)
        if idx >= 0:
            return text[:idx], text[idx:]
    return text, ""


def _text_width(font: ImageFont.ImageFont, text: str) -> float:
    """Return the horizontal pixel width of *text* rendered with *font*."""
    try:
        return font.getlength(text)
    except AttributeError:
        return font.getsize(text)[0]  # type: ignore[attr-defined]


def _chord_display_width(
    transposed: str,
    font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
) -> float:
    """Return the total rendered width of a chord after shortening."""
    main, suffix = _shorten_chord_display(transposed)
    w = _text_width(font, main)
    if suffix:
        w += _text_width(small_font, suffix)
    return w



def _draw_chord_text(
    draw: ImageDraw.Draw,
    x: int,
    y: int,
    transposed: str,
    font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
    fill: tuple,
) -> float:
    """Draw chord with optional smaller suffix.  Returns total width.

    The main part is drawn at *font* size.  If the chord contains a
    sus/dim/aug suffix, that part is drawn in *small_font* with baseline
    alignment.
    """
    main, suffix = _shorten_chord_display(transposed)
    draw.text((x, y), main, fill=fill, font=font)
    main_w = _text_width(font, main)

    if suffix:
        # Baseline-align the smaller suffix with the main text.
        try:
            main_ascent, _ = font.getmetrics()
            small_ascent, _ = small_font.getmetrics()
        except AttributeError:
            main_ascent = font.size if hasattr(font, "size") else 14
            small_ascent = small_font.size if hasattr(small_font, "size") else 10
        y_offset = main_ascent - small_ascent
        draw.text((x + int(main_w), y + y_offset), suffix,
                  fill=fill, font=small_font)
        return main_w + _text_width(small_font, suffix)

    return main_w


# ---------------------------------------------------------------------------
# Row clustering and greedy placement
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


def _place_row_labels(
    row: list[dict],
    font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
    img_width: int,
    h_gap: int = 6,
) -> list[tuple[dict, int]]:
    """Return [(chord, label_x), ...] shifted right to avoid horizontal overlap.

    Each label starts at chord["bbox"][0] but is nudged right if it would
    overlap the previous label.  The rightmost label is clamped to the image
    width so nothing overflows off-screen.

    The effective width includes ``_BOX_PAD`` on each side so white boxes in
    replace mode never merge into a single blob.
    """
    sorted_row = sorted(row, key=lambda c: c["bbox"][0])
    result: list[tuple[dict, int]] = []
    prev_right = -h_gap
    for chord in sorted_row:
        tw = int(_chord_display_width(chord["transposed"], font, small_font))
        effective_w = tw + 2 * _BOX_PAD   # account for white box padding
        x = max(chord["bbox"][0], prev_right + h_gap)
        x = min(x, max(0, img_width - tw))   # clamp to image edge
        result.append((chord, x))
        prev_right = x + effective_w
    return result


def _all_rows_fit(
    rows: list[list[dict]],
    font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
    img_width: int,
    h_gap: int = 6,
) -> bool:
    """Return True if all chords fit at their original x without shifting."""
    for row in rows:
        sorted_row = sorted(row, key=lambda c: c["bbox"][0])
        prev_right = -h_gap
        for chord in sorted_row:
            tw = int(_chord_display_width(chord["transposed"], font, small_font))
            effective_w = tw + 2 * _BOX_PAD
            natural_x = chord["bbox"][0]
            if natural_x < prev_right + h_gap:
                return False
            prev_right = natural_x + effective_w
    return True


def _find_fit_font_size(
    rows: list[list[dict]],
    initial_size: int,
    img_width: int,
) -> int:
    """Find the largest font size where no chord needs rightward shifting.

    Starts at *initial_size* and decreases by 1 px per iteration until all
    chords fit at their original bbox x-positions without overlap, or
    ``_MIN_FONT_SIZE`` is reached.  At ``_MIN_FONT_SIZE`` the greedy shift
    in ``_place_row_labels`` handles any remaining collisions.
    """
    for size in range(initial_size, _MIN_FONT_SIZE - 1, -1):
        font = _load_font(size)
        small_font = _load_font(int(size * _SMALL_FONT_RATIO))
        if _all_rows_fit(rows, font, small_font, img_width):
            return size
    return _MIN_FONT_SIZE


# ---------------------------------------------------------------------------
# Info header (replace mode only)
# ---------------------------------------------------------------------------

def _draw_info_header(
    draw: ImageDraw.Draw,
    img: Image.Image,
    font_size: int,
    *,
    original_key: str | None,
    target_key: str | None,
    semitones: int,
) -> None:
    """Draw key/capo info in the upper-left corner.

    Shows whenever *semitones* is non-zero or a key is provided.  When only
    semitones is given, a compact "Semitones: +N / Capo: M" header is drawn.
    """
    if not original_key and not target_key and semitones == 0:
        return

    header_font = _load_font(27)

    lines: list[str] = []
    if original_key and target_key:
        if semitones == 0:
            lines.append(f"Key: {original_key}")
        else:
            sign = f"+{semitones}" if semitones > 0 else str(semitones)
            lines.append(f"{original_key} -> {target_key} ({sign})")
    elif target_key:
        lines.append(f"Key: {target_key}")
    elif original_key:
        sign = f"+{semitones}" if semitones > 0 else str(semitones)
        lines.append(f"{original_key} ({sign})")
    else:
        # No key names — show the semitone shift on its own.
        sign = f"+{semitones}" if semitones > 0 else str(semitones)
        lines.append(f"Semitones: {sign}")

    lines.append("")  # blank line gap between key info and capo
    capo = (-semitones) % 12
    lines.append(f"Capo: {capo}" if capo else "No capo")

    # Measure text block size.
    line_h = int(font_size * 0.65) + 4
    max_w = max(_text_width(header_font, line) for line in lines)
    block_w = int(max_w) + 16
    block_h = line_h * len(lines) + 8

    # Draw background rectangle.
    x0, y0 = 8, 6
    # Use RGBA overlay for the header background.
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rectangle(
        [x0, y0, x0 + block_w, y0 + block_h],
        fill=_HEADER_BG,
    )
    composited = Image.alpha_composite(img.convert("RGBA"), overlay)
    img.paste(composited.convert("RGB"))

    # Draw text lines.
    for i, line in enumerate(lines):
        draw.text(
            (x0 + 8, y0 + 4 + i * line_h),
            line,
            fill=_DARK_BLUE,
            font=header_font,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_overlay(
    img: Image.Image,
    chords: list[dict],
    mode: str,
    *,
    original_key: str | None = None,
    target_key: str | None = None,
    semitones: int = 0,
) -> Image.Image:
    """Render transposed chord symbols onto *img* and return a new RGB image.

    Parameters
    ----------
    img          : PIL RGB image (original, not modified in-place).
    chords       : List of dicts with keys: text, transposed, bbox.
                   Entries where transposed or bbox is None are skipped.
    mode         : "above" or "replace".
    original_key : Original key of the song (e.g. "F").
    target_key   : Target key after transposition (e.g. "D#").
    semitones    : Semitone shift applied (-11 to +11).
    """
    eligible = [
        c for c in chords
        if c.get("transposed") is not None and c.get("bbox") is not None
    ]

    if mode == "above":
        return _render_above(img.copy(), eligible)
    else:
        return _render_replace(
            img.copy(), eligible,
            original_key=original_key,
            target_key=target_key,
            semitones=semitones,
        )


# ---------------------------------------------------------------------------
# above mode — labels placed ABOVE the original chord boxes
# ---------------------------------------------------------------------------

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
    """Render transposed chords above the original chord positions."""
    W, H = img.size
    rows = _cluster_by_row(chords)
    if not rows:
        return img

    # Global uniform font sizes — shrink if chords would overlap.
    all_heights = sorted(c["bbox"][3] - c["bbox"][1] for c in chords)
    median_h    = all_heights[len(all_heights) // 2]
    initial_size = max(_MIN_FONT_SIZE, int(median_h * _FONT_SCALE))
    font_size   = _find_fit_font_size(rows, initial_size, W)
    font        = _load_font(font_size)
    small_font  = _load_font(int(font_size * _SMALL_FONT_RATIO))

    # Pass 1 — check vertical space per row; record expansions needed.
    expansions: list[tuple[int, int]] = []
    prev_max_y2 = 0
    for row in rows:
        min_y1 = min(c["bbox"][1] for c in row)
        max_y2 = max(c["bbox"][3] for c in row)
        space_orig = min_y1 - prev_max_y2
        needed     = font_size + _GAP * 2
        if needed > space_orig:
            expansions.append((prev_max_y2, needed - space_orig))
        prev_max_y2 = max_y2

    # Pass 2 — expand the image where needed.
    if expansions:
        img = _insert_whitespace(img, expansions)

    # Pass 3 — cumulative y-offset per row after expansion.
    sorted_expansions = sorted(expansions)

    def _y_offset_for(orig_y1: int) -> int:
        return sum(extra for y, extra in sorted_expansions if y <= orig_y1)

    # Pass 4 — draw labels with greedy placement and row y-alignment.
    draw = ImageDraw.Draw(img)
    for row in rows:
        row_y1 = min(c["bbox"][1] for c in row)
        offset = _y_offset_for(row_y1)
        shifted_y1 = row_y1 + offset
        label_y = shifted_y1 - font_size - _GAP

        for chord, label_x in _place_row_labels(row, font, small_font, W):
            _draw_chord_text(draw, label_x, label_y, chord["transposed"],
                             font, small_font, _ORANGE)

    return img


# ---------------------------------------------------------------------------
# replace mode
# ---------------------------------------------------------------------------

def _render_replace(
    img: Image.Image,
    chords: list[dict],
    *,
    original_key: str | None = None,
    target_key: str | None = None,
    semitones: int = 0,
) -> Image.Image:
    """Render transposed chords over original positions with white boxes."""
    W, H = img.size
    rows = _cluster_by_row(chords)

    # Global uniform font sizes — shrink if chords would overlap.
    all_heights = sorted(c["bbox"][3] - c["bbox"][1] for c in chords)
    median_h    = all_heights[len(all_heights) // 2]
    initial_size = max(_MIN_FONT_SIZE, int(median_h * _FONT_SCALE))
    font_size   = _find_fit_font_size(rows, initial_size, W)
    font        = _load_font(font_size)
    small_font  = _load_font(int(font_size * _SMALL_FONT_RATIO))

    # ------------------------------------------------------------------
    # Pass 1 — compute placements (greedy overlap avoidance per row).
    # Collect (chord, label_x, row_y1) for each chord.
    # ------------------------------------------------------------------
    placements: list[tuple[dict, int, int]] = []
    for row in rows:
        row_y1 = min(c["bbox"][1] for c in row)
        for chord, label_x in _place_row_labels(row, font, small_font, W):
            placements.append((chord, label_x, row_y1))

    # ------------------------------------------------------------------
    # Pass 2 — draw fully opaque white boxes via RGBA compositing.
    # Each box covers the original bbox AND the resolved label area.
    # ------------------------------------------------------------------
    img_rgba = img.convert("RGBA")
    overlay  = Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
    ov_draw  = ImageDraw.Draw(overlay)

    for chord, label_x, row_y1 in placements:
        x1, y1, x2, y2 = chord["bbox"]
        bh = y2 - y1

        # Contract OCR bbox inward to approximate actual glyph area.
        # PaddleOCR adds ~2–4px margin per side; shrink proportionally
        # so the white box erases only the chord text, not surrounding
        # musical notation (stems, dots, articulation marks).
        shrink_y = max(1, int(bh * 0.15))
        shrink_x = max(1, int(bh * 0.10))
        box_x1 = x1 + shrink_x
        box_y1 = y1 + shrink_y
        box_x2 = x2 - shrink_x
        box_y2 = y2 - shrink_y

        ov_draw.rectangle([box_x1, box_y1, box_x2, box_y2], fill=_WHITE_RGBA)

    composited = Image.alpha_composite(img_rgba, overlay).convert("RGB")

    # ------------------------------------------------------------------
    # Pass 3 — draw text at resolved positions, vertically centered.
    # ------------------------------------------------------------------
    draw = ImageDraw.Draw(composited)
    for chord, label_x, row_y1 in placements:
        _, y1, _, y2 = chord["bbox"]
        box_h = y2 - y1
        text_y = y1 + (box_h - font_size) // 2
        _draw_chord_text(draw, label_x, text_y, chord["transposed"],
                         font, small_font, _DARK_BLUE)

    # ------------------------------------------------------------------
    # Pass 4 — info header (key, capo).
    # ------------------------------------------------------------------
    _draw_info_header(
        draw, composited, font_size,
        original_key=original_key,
        target_key=target_key,
        semitones=semitones,
    )

    return composited
