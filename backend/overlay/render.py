"""Chord overlay rendering for Capomatic.

Renders transposed chord symbols onto a PIL image using one of two modes:

  above   — orange transposed chord printed above each original chord.
             One uniform font size across all rows (median bbox height x scale).
             Labels within a row are shifted right as needed to avoid horizontal
             overlap.  If the row has insufficient space above it, white rows
             are inserted to create room.
  replace — local paper colour covers the original chord; new chord is
             rendered in sampled dark ink at the same position.
"""
from __future__ import annotations

import os
import pathlib
import statistics

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Bundled font. If it is missing or invalid, system fonts are tried.
_FONT_PATH = pathlib.Path(__file__).parent / "fonts" / "BravuraText.otf"
_FONT_CANDIDATES = [
    os.environ.get("CHORD_RENDER_FONT", ""),
    str(_FONT_PATH),
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/local/share/fonts/dejavu/DejaVuSans.ttf",
    "/opt/anaconda3/lib/python3.12/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf",
]
_BOLD_FONT_CANDIDATES = [
    os.environ.get("CHORD_RENDER_BOLD_FONT", ""),
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/opt/anaconda3/lib/python3.12/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans-Bold.ttf",
]

# Font size = median bbox_height * this scale.
_FONT_SCALE    = 0.85
_MIN_FONT_SIZE = 10

# Ratio for the smaller suffix font (sus, dim, aug).
_SMALL_FONT_RATIO = 0.70

# Vertical gap (px) between the bottom of a label and the top of its chord box.
_GAP = 2

# Padding around replacement boxes.
_BOX_PAD = 4

# Colours
_ORANGE     = (255, 140, 0)
_DARK_BLUE  = (0, 0, 160)
_DEFAULT_INK = (30, 30, 30)
_HEADER_BG  = (255, 255, 255, 220)   # info header background
_REPLACE_LABEL_BG = (255, 255, 255)
_CLARITY_THRESHOLD = 0.58

# Quality/modifier suffixes rendered in smaller font.
_SMALL_SUFFIXES = ("sus", "dim", "aug")


# ---------------------------------------------------------------------------
# Font loader
# ---------------------------------------------------------------------------

def _load_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    """Return a readable chord font at *size* pt, falling back to PIL default."""
    size = max(_MIN_FONT_SIZE, size)
    candidates = (_BOLD_FONT_CANDIDATES if bold else []) + _FONT_CANDIDATES
    for candidate in candidates:
        if not candidate:
            continue
        path = pathlib.Path(candidate)
        if not path.exists():
            continue
        try:
            return ImageFont.truetype(str(path), size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)  # type: ignore[call-arg]
    except TypeError:
        return ImageFont.load_default()


def _median_rgb(samples: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    if not samples:
        return (255, 255, 255)
    channels = zip(*samples)
    return tuple(int(statistics.median(channel)) for channel in channels)  # type: ignore[return-value]


def _sample_background(
    img: Image.Image,
    bbox: list[int],
    *,
    pad: int = 6,
) -> tuple[int, int, int]:
    """Estimate local paper colour from the border around *bbox*."""
    rgb = img.convert("RGB")
    W, H = rgb.size
    x1, y1, x2, y2 = _expanded_bbox(
        bbox,
        W,
        H,
        x_ratio=0.18,
        y_ratio=0.12,
    )
    rx1 = max(0, x1 - pad)
    ry1 = max(0, y1 - pad)
    rx2 = min(W, x2 + pad)
    ry2 = min(H, y2 + pad)
    all_samples: list[tuple[int, int, int]] = []
    samples: list[tuple[int, int, int]] = []
    for y in range(ry1, ry2):
        for x in range(rx1, rx2):
            if x1 <= x <= x2 and y1 <= y <= y2:
                continue
            r, g, b = rgb.getpixel((x, y))
            all_samples.append((r, g, b))
            if (r + g + b) / 3 >= 170:
                samples.append((r, g, b))
    return _median_rgb(samples or all_samples)


def _sample_ink(
    img: Image.Image,
    bbox: list[int],
) -> tuple[int, int, int]:
    """Estimate original chord ink colour from dark pixels inside *bbox*."""
    rgb = img.convert("RGB")
    W, H = rgb.size
    x1, y1, x2, y2 = bbox
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(W, x2), min(H, y2)
    samples: list[tuple[int, int, int]] = []
    for y in range(y1, y2):
        for x in range(x1, x2):
            r, g, b = rgb.getpixel((x, y))
            if (r + g + b) / 3 <= 150:
                samples.append((r, g, b))
    if not samples:
        return _DEFAULT_INK
    return _median_rgb(samples)


def _estimate_font_size_from_bbox(
    img: Image.Image,
    bbox: list[int],
    fallback_size: int,
) -> int:
    """Estimate original glyph height from dark pixels inside the OCR bbox."""
    rgb = img.convert("RGB")
    W, H = rgb.size
    x1, y1, x2, y2 = bbox
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(W, x2), min(H, y2)
    dark_ys: list[int] = []
    for y in range(y1, y2):
        dark_count = 0
        for x in range(x1, x2):
            r, g, b = rgb.getpixel((x, y))
            if (r + g + b) / 3 <= 170:
                dark_count += 1
        if dark_count >= 1:
            dark_ys.append(y)
    if not dark_ys:
        return fallback_size
    glyph_h = max(dark_ys) - min(dark_ys) + 1
    return max(_MIN_FONT_SIZE, int(round(glyph_h * 1.15)))


def _style_font_size(chord: dict, img: Image.Image, fallback_size: int) -> int:
    style = chord.get("style") if isinstance(chord.get("style"), dict) else {}
    raw_size = style.get("font_size")
    if isinstance(raw_size, (int, float)) and raw_size > 0:
        return max(_MIN_FONT_SIZE, int(round(raw_size)))
    return _estimate_font_size_from_bbox(img, chord["bbox"], fallback_size)


def _style_bold(chord: dict, protocol: dict | None = None) -> bool:
    if protocol and protocol.get("use_default_font"):
        return False
    style = chord.get("style") if isinstance(chord.get("style"), dict) else {}
    return style.get("font_weight") == "bold"


def _style_ink(chord: dict, img: Image.Image, protocol: dict | None = None) -> tuple[int, int, int]:
    if protocol and not protocol.get("use_sampled_ink", True):
        return _DEFAULT_INK
    style = chord.get("style") if isinstance(chord.get("style"), dict) else {}
    ink = style.get("ink")
    if (
        isinstance(ink, (list, tuple))
        and len(ink) == 3
        and all(isinstance(v, (int, float)) for v in ink)
    ):
        return tuple(max(0, min(255, int(v))) for v in ink)  # type: ignore[return-value]
    return _sample_ink(img, chord["bbox"])


def _estimate_glyph_clarity(
    img: Image.Image,
    bbox: list[int],
) -> float:
    """Estimate whether original chord glyphs are crisp enough to mimic."""
    gray = img.convert("L")
    W, H = gray.size
    x1, y1, x2, y2 = bbox
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(W, x2), min(H, y2)
    if x2 - x1 < 2 or y2 - y1 < 2:
        return 0.0

    dark = 0
    mid = 0
    edge = 0
    for y in range(y1, y2):
        for x in range(x1, x2):
            v = gray.getpixel((x, y))
            if v < 120:
                dark += 1
            elif v < 210:
                mid += 1
            if x > x1 and y > y1:
                dx = abs(v - gray.getpixel((x - 1, y)))
                dy = abs(v - gray.getpixel((x, y - 1)))
                if max(dx, dy) > 55:
                    edge += 1

    area = max(1, (x2 - x1) * (y2 - y1))
    dark_ratio = dark / area
    if dark_ratio < 0.02:
        return 0.0
    transition_ratio = mid / max(1, dark + mid)
    edge_ratio = edge / area
    return max(0.0, min(1.0, edge_ratio * 8.0 + dark_ratio * 2.0 - transition_ratio * 0.45))


def _choose_render_protocol(
    rows: list[list[dict]],
    img: Image.Image,
) -> dict:
    """Choose sheet-level rendering rules for readability and source matching.

    Low-clarity scans use a clean default font and stable ink colour. High
    clarity pages may use detected style hints and sampled ink.
    """
    clarity_scores = [
        _estimate_glyph_clarity(img, chord["bbox"])
        for row in rows
        for chord in row
    ]
    clarity = statistics.median(clarity_scores) if clarity_scores else 0.0
    return {
        "clarity": clarity,
        "use_default_font": clarity < _CLARITY_THRESHOLD,
        "use_sampled_ink": clarity >= _CLARITY_THRESHOLD,
    }


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
        try:
            return font.getsize(text)[0]  # type: ignore[attr-defined]
        except AttributeError:
            return len(text) * getattr(font, "size", _MIN_FONT_SIZE) * 0.6


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


def _render_font_size(chords: list[dict]) -> int:
    """Return one stable font size for every chord in this render."""
    heights = [
        c["bbox"][3] - c["bbox"][1]
        for c in chords
        if c.get("bbox") is not None
    ]
    if not heights:
        return _MIN_FONT_SIZE
    median_height = statistics.median(heights)
    return max(_MIN_FONT_SIZE, int(round(median_height * _FONT_SCALE)))


def _draw_text_left_top(
    draw: ImageDraw.Draw,
    xy: tuple[int, int],
    text: str,
    *,
    fill: tuple,
    font: ImageFont.ImageFont,
) -> None:
    x, y = xy
    try:
        ink_bbox = font.getbbox(text, anchor="lt")
        x -= int(ink_bbox[0])
        y -= int(ink_bbox[1])
    except Exception:
        pass
    try:
        draw.text((x, y), text, fill=fill, font=font, anchor="lt")
    except TypeError:
        draw.text((x, y), text, fill=fill, font=font)



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

    The main part is drawn at *font* size, anchored to the exact left-top
    position provided by the caller.
    """
    main, suffix = _shorten_chord_display(transposed)
    _draw_text_left_top(draw, (x, y), main, fill=fill, font=font)
    main_w = _text_width(font, main)

    if suffix:
        _draw_text_left_top(
            draw,
            (x + int(main_w), y),
            suffix,
            fill=fill,
            font=small_font,
        )
        return main_w + _text_width(small_font, suffix)

    return main_w


def _draw_replace_label_background(
    draw: ImageDraw.Draw,
    chord: dict,
    x: int,
    y: int,
    transposed: str,
    font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
    img_width: int,
) -> None:
    """Draw a clean rectangular backing for replace-mode chord text."""
    text_w = int(round(_chord_display_width(transposed, font, small_font)))
    font_size = max(
        _MIN_FONT_SIZE,
        int(getattr(font, "size", _MIN_FONT_SIZE)),
    )
    bbox = chord["bbox"]
    pad_x = 4
    pad_y = 3
    x1 = min(x, bbox[0])
    y1 = min(y, bbox[1])
    x2 = max(x + text_w, bbox[2])
    y2 = max(y + font_size, bbox[3])
    draw.rectangle(
        [
            max(0, x1 - pad_x),
            max(0, y1 - pad_y),
            min(img_width, x2 + pad_x),
            y2 + pad_y,
        ],
        fill=_REPLACE_LABEL_BG,
    )


def _expanded_bbox(
    bbox: list[int],
    width: int,
    height: int,
    *,
    x_ratio: float = 0.25,
    y_ratio: float = 0.35,
) -> list[int]:
    x1, y1, x2, y2 = bbox
    box_w = max(1, x2 - x1)
    box_h = max(1, y2 - y1)
    pad_x = max(2, int(round(box_w * x_ratio)))
    pad_y = max(2, int(round(box_h * y_ratio)))
    return [
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(width, x2 + pad_x),
        min(height, y2 + pad_y),
    ]


def _glyph_mask_pixels(
    img: Image.Image,
    bbox: list[int],
    *,
    dark_threshold: int = 185,
) -> set[tuple[int, int]]:
    """Return dark non-staff pixels around *bbox* for chord replacement."""
    gray = img.convert("L")
    W, H = gray.size
    x1, y1, x2, y2 = _expanded_bbox(bbox, W, H)
    crop_w = x2 - x1
    crop_h = y2 - y1
    if crop_w < 2 or crop_h < 2:
        return set()

    rows: dict[int, list[int]] = {}
    for y in range(y1, y2):
        xs = [x for x in range(x1, x2) if gray.getpixel((x, y)) <= dark_threshold]
        if xs:
            rows[y] = xs

    if not rows:
        return set()

    staff_like_rows = set()
    for y, xs in rows.items():
        page_dark_count = sum(
            1 for x in range(W)
            if gray.getpixel((x, y)) <= dark_threshold
        )
        if len(xs) / crop_w >= 0.65 and page_dark_count / max(1, W) >= 0.25:
            staff_like_rows.add(y)

    pixels: set[tuple[int, int]] = set()
    for y, xs in rows.items():
        if y in staff_like_rows:
            continue
        for x in xs:
            pixels.add((x, y))

    if len(pixels) < max(3, int(crop_w * crop_h * 0.003)):
        return set()
    return pixels


def _erase_glyph_pixels(
    img: Image.Image,
    source_img: Image.Image,
    bbox: list[int],
    fill: tuple[int, int, int],
) -> None:
    """Erase original chord glyph pixels while preserving surrounding content."""
    W, H = img.size
    px = img.load()
    pixels = _glyph_mask_pixels(source_img, bbox)
    if not pixels:
        return

    # Inpainting removes the old chord while preserving uneven paper, scans, and
    # watermark gradients better than filling the mask with one sampled colour.
    mask = np.zeros((H, W), dtype=np.uint8)
    x1, y1, x2, y2 = bbox
    x1 = max(0, min(W, x1))
    y1 = max(0, min(H, y1))
    x2 = max(x1, min(W, x2))
    y2 = max(y1, min(H, y2))
    if x2 > x1 and y2 > y1:
        gray = source_img.convert("L")
        box_w = max(1, x2 - x1)
        for yy in range(y1, y2):
            dark_count = sum(
                1 for xx in range(x1, x2)
                if gray.getpixel((xx, yy)) <= 185
            )
            page_dark_count = sum(
                1 for xx in range(W)
                if gray.getpixel((xx, yy)) <= 185
            )
            if dark_count / box_w >= 0.65 and page_dark_count / max(1, W) >= 0.25:
                continue
            mask[yy, x1:x2] = 255

    for x, y in pixels:
        for yy in range(max(0, y - 1), min(H, y + 2)):
            for xx in range(max(0, x - 1), min(W, x + 2)):
                mask[yy, xx] = 255

    if int(mask.sum()) > 0:
        arr = np.array(img.convert("RGB"))
        restored = cv2.inpaint(arr, mask, 3, cv2.INPAINT_TELEA)
        img.paste(Image.fromarray(restored))
        return

    for x, y in pixels:
        px[x, y] = fill


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


def _row_aligned_top(row: list[dict]) -> int:
    """Return one stable text top for every chord in a row.

    OCR boxes in the same printed row can have slightly different heights or y
    positions.  Aligning from the median bottom minus median height keeps the
    rendered chord bottoms visually level without mutating stored OCR bboxes.
    """
    if not row:
        return 0
    bottoms = [c["bbox"][3] for c in row]
    heights = [c["bbox"][3] - c["bbox"][1] for c in row]
    row_bottom = statistics.median(bottoms)
    row_height = statistics.median(heights)
    return int(round(row_bottom - row_height))


def _find_row_font_sizes(
    rows: list[list[dict]],
    initial_size: int,
    img_width: int,
    img: Image.Image | None = None,
    h_gap: int = 6,
) -> list[int]:
    """Find optimal font size for each row independently.

    Each row shrinks only as much as needed to fit all chords at their
    original x-positions without overlap.
    """
    sizes: list[int] = []
    for row in rows:
        row_initial_size = initial_size
        if img is not None:
            estimated_sizes = [
                _style_font_size(chord, img, initial_size)
                for chord in row
            ]
            if estimated_sizes:
                row_initial_size = max(_MIN_FONT_SIZE, int(statistics.median(estimated_sizes)))
        sorted_row = sorted(row, key=lambda c: c["bbox"][0])
        found = _MIN_FONT_SIZE
        for size in range(row_initial_size, _MIN_FONT_SIZE - 1, -1):
            font = _load_font(size)
            small_font = _load_font(int(size * _SMALL_FONT_RATIO))
            fits = True
            prev_right = -h_gap
            for chord in sorted_row:
                tw = int(_chord_display_width(chord["transposed"], font, small_font))
                effective_w = tw + 2 * _BOX_PAD
                anchor_x = max(chord["bbox"][0], chord["bbox"][2] - effective_w)
                if anchor_x < prev_right + h_gap:
                    fits = False
                    break
                prev_right = anchor_x + effective_w
            if fits:
                found = size
                break
        sizes.append(found)
    return sizes


def _place_row_labels_anchored(
    row: list[dict],
    font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
    img_width: int,
    h_gap: int = 6,
) -> list[tuple[dict, int]]:
    """Place chord labels anchored to their original x-positions.

    Only adjusts when even ``_MIN_FONT_SIZE`` can't prevent overlap —
    in that case, overlap is split equally between colliding chords.
    """
    sorted_row = sorted(row, key=lambda c: c["bbox"][0])
    placements: list[list] = []
    for chord in sorted_row:
        tw = int(_chord_display_width(chord["transposed"], font, small_font))
        x = max(chord["bbox"][0], chord["bbox"][2] - tw)
        x = min(x, max(0, img_width - tw))
        placements.append([chord, x, tw + 2 * _BOX_PAD])
    for i in range(len(placements) - 1):
        x_i = placements[i][1]
        ew_i = placements[i][2]
        x_next = placements[i + 1][1]
        overlap = (x_i + ew_i + h_gap) - x_next
        if overlap > 0:
            shift_left = overlap // 2
            shift_right = overlap - shift_left
            placements[i][1] = max(0, x_i - shift_left)
            ew_next = placements[i + 1][2]
            placements[i + 1][1] = min(img_width - ew_next, x_next + shift_right)
    return [(p[0], p[1]) for p in placements]


def _font_fits_row(
    row: list[dict],
    sizes: dict[int, int],
    img_width: int,
    protocol: dict | None = None,
    h_gap: int = 6,
) -> bool:
    prev_right = -h_gap
    for chord in sorted(row, key=lambda c: c["bbox"][0]):
        size = sizes[id(chord)]
        bold = _style_bold(chord, protocol)
        font = _load_font(size, bold=bold)
        small_font = _load_font(int(size * _SMALL_FONT_RATIO), bold=bold)
        tw = int(_chord_display_width(chord["transposed"], font, small_font))
        effective_w = tw + 2 * _BOX_PAD
        anchor_x = max(chord["bbox"][0], chord["bbox"][2] - effective_w)
        if anchor_x < prev_right + h_gap:
            return False
        prev_right = anchor_x + effective_w
        if prev_right > img_width:
            return False
    return True


def _resolve_fixed_font_sizes(
    row: list[dict],
    img: Image.Image,
    fixed_size: int,
    img_width: int,
    protocol: dict | None = None,
) -> dict[int, int]:
    """Use one fixed size for readability; shrink only if row space is limited."""
    sizes = {id(chord): fixed_size for chord in row}
    while (
        not _font_fits_row(row, sizes, img_width, protocol)
        and max(sizes.values()) > _MIN_FONT_SIZE
    ):
        for key in list(sizes):
            sizes[key] = max(_MIN_FONT_SIZE, sizes[key] - 1)
    return sizes


def _estimate_document_font_size(
    rows: list[list[dict]],
    img: Image.Image,
    fallback_size: int,
) -> int:
    """Estimate one stable chord font size for the whole rendered sheet."""
    sizes = [
        _style_font_size(chord, img, fallback_size)
        for row in rows
        for chord in row
    ]
    if not sizes:
        return fallback_size
    return max(_MIN_FONT_SIZE, int(round(statistics.median(sizes))))


def _place_row_labels_fixed(
    row: list[dict],
    sizes: dict[int, int],
    img_width: int,
    protocol: dict | None = None,
    h_gap: int = 6,
) -> list[tuple[dict, int, int]]:
    """Place labels using fixed per-chord font sizes."""
    placements: list[list] = []
    for chord in sorted(row, key=lambda c: c["bbox"][0]):
        size = sizes[id(chord)]
        bold = _style_bold(chord, protocol)
        font = _load_font(size, bold=bold)
        small_font = _load_font(int(size * _SMALL_FONT_RATIO), bold=bold)
        tw = int(_chord_display_width(chord["transposed"], font, small_font))
        x = max(chord["bbox"][0], chord["bbox"][2] - tw)
        x = min(x, max(0, img_width - tw))
        placements.append([chord, x, tw + 2 * _BOX_PAD, size])
    for i in range(len(placements) - 1):
        x_i = placements[i][1]
        ew_i = placements[i][2]
        x_next = placements[i + 1][1]
        overlap = (x_i + ew_i + h_gap) - x_next
        if overlap > 0:
            shift_left = overlap // 2
            shift_right = overlap - shift_left
            placements[i][1] = max(0, x_i - shift_left)
            ew_next = placements[i + 1][2]
            placements[i + 1][1] = min(img_width - ew_next, x_next + shift_right)
    return [(p[0], p[1], p[3]) for p in placements]


def _replace_row_fits(
    row: list[dict],
    size: int,
    img_width: int,
    h_gap: int = 4,
) -> bool:
    font = _load_font(size)
    small_font = _load_font(int(size * _SMALL_FONT_RATIO))
    total_w = 0
    for chord in row:
        total_w += int(_chord_display_width(chord["transposed"], font, small_font))
    total_w += h_gap * max(0, len(row) - 1)
    left = min(c["bbox"][0] for c in row)
    right_limit = img_width - left
    return total_w <= right_limit


def _resolve_replace_row_font_size(
    row: list[dict],
    fixed_size: int,
    img_width: int,
) -> int:
    """Keep the document font size unless a dense row cannot fit."""
    size = fixed_size
    while size > _MIN_FONT_SIZE and not _replace_row_fits(row, size, img_width):
        size -= 1
    return max(_MIN_FONT_SIZE, size)


def _place_replace_row_labels(
    row: list[dict],
    font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
    img_width: int,
    h_gap: int = 4,
) -> list[tuple[dict, int]]:
    """Place replace-mode labels left-to-right without horizontal overlap."""
    placements: list[list] = []
    for chord in sorted(row, key=lambda c: c["bbox"][0]):
        tw = int(_chord_display_width(chord["transposed"], font, small_font))
        x = max(0, min(chord["bbox"][0], img_width - tw))
        placements.append([chord, x, tw])

    prev_right = -h_gap
    for p in placements:
        p[1] = max(p[1], prev_right + h_gap)
        prev_right = p[1] + p[2]

    overflow = prev_right - img_width
    if overflow > 0 and placements:
        for p in placements:
            p[1] = max(0, p[1] - overflow)

        # One final forward pass handles cases where the left shift created a
        # new collision at the row start.
        prev_right = -h_gap
        for p in placements:
            p[1] = max(p[1], prev_right + h_gap)
            p[1] = min(p[1], max(0, img_width - p[2]))
            prev_right = p[1] + p[2]

    return [(p[0], int(p[1])) for p in placements]


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
    """Draw key info, and capo info only for down-transpose/capo renders."""
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

    if semitones < 0:
        lines.append("")  # blank line gap between key info and capo
        capo = (-semitones) % 12
        if capo:
            lines.append(f"Capo: {capo}")

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
        return _render_above(
            img.copy(), eligible,
            original_key=original_key,
            target_key=target_key,
            semitones=semitones,
        )
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


def _safe_above_insert_y(
    img_arr: np.ndarray,
    row_top: int,
    font_size: int,
    *,
    dark_threshold: int = 200,
    content_ratio_threshold: float = 0.02,
) -> int | None:
    """Find a mostly blank horizontal band above a chord row.

    Above mode may need to add vertical space for labels.  Inserting exactly at
    the chord row can split lyric or staff content when the area above the row
    is occupied.  This helper only returns an insertion y when there is a blank
    band wide enough to cut through safely.
    """
    H = img_arr.shape[0]
    if H == 0 or row_top <= 1:
        return None

    needed = max(4, int((font_size + _GAP) * 0.7))
    search_top = max(0, row_top - max(font_size * 3, needed * 2))
    search_bottom = max(search_top, min(H, row_top))
    if search_bottom - search_top < needed:
        return None

    region = img_arr[search_top:search_bottom, :]
    if region.size == 0:
        return None

    row_dark_ratio = np.mean(region < dark_threshold, axis=1)
    blank_rows = row_dark_ratio <= content_ratio_threshold

    best_start: int | None = None
    best_len = 0
    start: int | None = None
    for idx, is_blank in enumerate(blank_rows):
        if is_blank and start is None:
            start = idx
        elif not is_blank and start is not None:
            run_len = idx - start
            if run_len >= needed:
                best_start = start
                best_len = run_len
            start = None
    if start is not None:
        run_len = len(blank_rows) - start
        if run_len >= needed:
            best_start = start
            best_len = run_len

    if best_start is None:
        return None

    # Insert near the lower edge of the blank band so the new space appears
    # close to the chord row without cutting through visible content.
    return search_top + best_start + best_len


def _render_above(
    img: Image.Image,
    chords: list[dict],
    *,
    original_key: str | None = None,
    target_key: str | None = None,
    semitones: int = 0,
) -> Image.Image:
    """Render transposed chords above the original chord positions."""
    W, H = img.size
    rows = _cluster_by_row(chords)
    if not rows:
        return img

    # One font size is used across all rows in this render.
    font_size = _render_font_size(chords)

    # Pass 1 — adaptively insert whitespace above each chord row.
    import numpy as np
    img_arr = np.array(img.convert("L"))
    expansions: list[tuple[int, int]] = []
    row_insert_y: dict[int, int] = {}
    for row_idx, row in enumerate(rows):
        needed = font_size + _GAP + 2
        min_y1 = min(c["bbox"][1] for c in row)
        label_top = max(0, min_y1 - font_size - _GAP)
        region = img_arr[label_top:min_y1, :]
        if region.size > 0:
            dark_ratio = np.mean(region < 200)
            if dark_ratio > 0.02:
                insert_y = _safe_above_insert_y(img_arr, min_y1, font_size)
                if insert_y is not None:
                    expansions.append((insert_y, needed))
                    row_insert_y[row_idx] = insert_y

    # Pass 2 — expand the image where needed.
    if expansions:
        img = _insert_whitespace(img, expansions)

    # Pass 3 — cumulative y-offset per row after expansion.
    sorted_expansions = sorted(expansions)

    def _y_offset_for(orig_y1: int) -> int:
        return sum(extra for y, extra in sorted_expansions if y <= orig_y1)

    def _y_offset_before(insert_y: int) -> int:
        return sum(extra for y, extra in sorted_expansions if y < insert_y)

    # Pass 4 — draw labels with one vertical anchor per row.
    draw = ImageDraw.Draw(img)
    font = _load_font(font_size)
    small_font = _load_font(int(font_size * _SMALL_FONT_RATIO))
    for row_idx, row in enumerate(rows):

        row_y1 = _row_aligned_top(row)
        if row_idx in row_insert_y:
            insert_y = row_insert_y[row_idx]
            label_y = insert_y + _y_offset_before(insert_y) + 2
        else:
            offset = _y_offset_for(row_y1)
            label_y = row_y1 + offset - font_size - _GAP

        for chord, label_x in _place_row_labels_anchored(row, font, small_font, W):
            _draw_chord_text(draw, label_x, label_y, chord["transposed"],
                             font, small_font, _ORANGE)

    _draw_info_header(
        draw, img, font_size,
        original_key=original_key,
        target_key=target_key,
        semitones=semitones,
    )

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
    if not chords:
        return img
    rows = _cluster_by_row(chords)
    protocol = _choose_render_protocol(rows, img)
    font_size = _render_font_size(chords)

    # ------------------------------------------------------------------
    # Pass 2 — cover original chord glyphs with sampled local paper colour.
    # ------------------------------------------------------------------
    composited = img.copy().convert("RGB")
    ink_by_id: dict[int, tuple[int, int, int]] = {}
    for chord in chords:
        x1, y1, x2, y2 = chord["bbox"]
        box_x1 = max(0, x1)
        box_y1 = max(0, y1)
        box_x2 = min(W, x2)
        box_y2 = min(H, y2)
        fill = _sample_background(img, [box_x1, box_y1, box_x2, box_y2])
        ink_by_id[id(chord)] = _DARK_BLUE
        _erase_glyph_pixels(
            composited,
            img,
            [box_x1, box_y1, box_x2, box_y2],
            fill,
        )

    # ------------------------------------------------------------------
    # Pass 3 — draw text at one row-level y unless dense rows need x adjustment.
    # ------------------------------------------------------------------
    draw = ImageDraw.Draw(composited)
    for row in rows:
        row_size = _resolve_replace_row_font_size(row, font_size, W)
        font = _load_font(row_size)
        small_font = _load_font(int(row_size * _SMALL_FONT_RATIO))
        row_y = _row_aligned_top(row)
        for chord, x in _place_replace_row_labels(row, font, small_font, W):
            _draw_replace_label_background(
                draw,
                chord,
                x,
                row_y,
                chord["transposed"],
                font,
                small_font,
                W,
            )
            _draw_chord_text(draw, x, row_y, chord["transposed"],
                             font, small_font, ink_by_id.get(id(chord), _DEFAULT_INK))

    _draw_info_header(
        draw, composited, font_size,
        original_key=original_key,
        target_key=target_key,
        semitones=semitones,
    )

    return composited
