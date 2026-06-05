"""GPT vision OCR for chord detection.

Returns the same item shape used by the PaddleOCR pipeline:
``{"text": str, "bbox": [x1, y1, x2, y2], "confidence": float}``.
"""
from __future__ import annotations

import base64
import io
import json
import mimetypes
import os
import time
import urllib.error
import urllib.request
from typing import Any

from PIL import Image

from backend.chords.normalize import normalize_chord_text
from backend.ocr.filter import is_chord_candidate, recover_candidates
from backend.ocr.preprocess import select_ocr_regions

_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_MODEL = os.environ.get("OPENAI_OCR_MODEL", "gpt-5.4-mini")
_MAX_SIDE = os.environ.get("OPENAI_OCR_MAX_SIDE")
MAX_SIDE = int(_MAX_SIDE) if _MAX_SIDE else None
_PROMPT = (
    "List every chord symbol in this sheet music image. For each, return text "
    "and position as percentages relative to the full image width and height. "
    "The bounding box must match how PaddleOCR detects text regions. "
    "x_pct and y_pct must be the top-left corner of the tight visible chord glyph bounding box. "
    "w_pct must be the width of the exact chord text pixel span. "
    "h_pct must be the height of the exact chord text pixel span. "
    "Use no padding, no whitespace, and no row region. "
    "Measure only the dark ink pixels of the chord symbol. "
    "Do not return the center point, baseline position, row region, or surrounding whitespace. "
    "Measure each chord like a tight rectangle drawn around only the visible ink strokes "
    "of the chord text. x_pct and y_pct are the top-left corner. "
    "w_pct and h_pct are the exact width and height of that ink rectangle. "
    "Percentages are relative to full image dimensions. "
    "For chord 'Am7' whose text starts at 30% from left and 10% from top, "
    "and the text spans 5% wide and 2% tall: "
    "x_pct=0.30, y_pct=0.10, w_pct=0.05, h_pct=0.02. "
    "plus approximate font style metadata: font_size_pct as percentage of image height, "
    "font_weight ('regular' or 'bold'), italic (true or false), and color ('black', "
    "'dark_gray', 'gray', 'blue', or 'other'). "
    "Exclude lyrics, numbers, and non-chord text. Respond in JSON only: "
    "{chords: [{text, x_pct, y_pct, w_pct, h_pct, font_size_pct, font_weight, italic, color}]}"
)


def _media_type(image_path: str) -> str:
    guessed, _ = mimetypes.guess_type(image_path)
    return guessed or "image/jpeg"


def _extract_json(raw_text: str) -> dict[str, Any]:
    """Parse a JSON object, tolerating fenced responses if the model emits one."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object from OpenAI, got {type(data)}")
    return data


def _pct_to_unit(value: Any) -> float:
    number = float(value)
    if number > 1.0:
        number /= 100.0
    return max(0.0, min(1.0, number))


def _bbox_from_pct(chord: dict[str, Any], width: int, height: int) -> list[int]:
    x = _pct_to_unit(chord["x_pct"])
    y = _pct_to_unit(chord["y_pct"])
    w = _pct_to_unit(chord["w_pct"])
    h = _pct_to_unit(chord["h_pct"])

    x1 = min(width - 1, int(round(x * width)))
    y1 = min(height - 1, int(round(y * height)))
    x2 = int(round(min(1.0, x + w) * width))
    y2 = int(round(min(1.0, y + h) * height))
    return [x1, y1, min(width, max(x1 + 1, x2)), min(height, max(y1 + 1, y2))]


def _expanded_bbox(
    bbox: list[int],
    width: int,
    height: int,
    *,
    x_ratio: float = 0.35,
    y_ratio: float = 0.60,
) -> list[int]:
    x1, y1, x2, y2 = bbox
    box_w = max(1, x2 - x1)
    box_h = max(1, y2 - y1)
    pad_x = max(4, int(round(box_w * x_ratio)))
    pad_y = max(3, int(round(box_h * y_ratio)))
    return [
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(width, x2 + pad_x),
        min(height, y2 + pad_y),
    ]


def _dark_pixel_bounds(
    gray: Image.Image,
    search_bbox: list[int],
    *,
    dark_threshold: int = 180,
) -> list[int] | None:
    """Return a tight bbox around dark non-staff pixels in *search_bbox*."""
    x1, y1, x2, y2 = search_bbox
    crop_w = x2 - x1
    crop_h = y2 - y1
    if crop_w < 2 or crop_h < 2:
        return None

    dark_rows: dict[int, list[int]] = {}
    for y in range(y1, y2):
        xs: list[int] = []
        for x in range(x1, x2):
            if gray.getpixel((x, y)) <= dark_threshold:
                xs.append(x)
        if xs:
            dark_rows[y] = xs

    if not dark_rows:
        return None

    # Staff lines run horizontally through most of the local crop. Chord glyph
    # rows are much shorter and more irregular, so skip long dense rows.
    staff_like_rows = {
        y for y, xs in dark_rows.items()
        if len(xs) / crop_w >= 0.65
    }

    dark_xs: list[int] = []
    dark_ys: list[int] = []
    for y, xs in dark_rows.items():
        if y in staff_like_rows:
            continue
        dark_xs.extend(xs)
        dark_ys.extend([y] * len(xs))

    if len(dark_xs) < max(3, int(crop_w * crop_h * 0.003)):
        return None

    return [min(dark_xs), min(dark_ys), max(dark_xs) + 1, max(dark_ys) + 1]


def _staff_band_for_bbox(
    bbox: list[int],
    regions: list[dict],
) -> dict | None:
    """Return the staff-aware chord band most likely associated with *bbox*."""
    staff_regions = [
        r for r in regions
        if "staff_top" in r and "staff_bottom" in r and "y0" in r and "h" in r
    ]
    if not staff_regions:
        return None

    y1 = bbox[1]
    for region in sorted(staff_regions, key=lambda r: r["staff_top"]):
        staff_bottom = int(region["staff_bottom"])
        # If GPT placed the box on the staff, just below it, or in the lyric
        # area under it, snap refinement back to this staff's chord band.
        if y1 <= staff_bottom + 80:
            return region
    return staff_regions[-1]


def _constrain_search_to_staff_band(
    search_bbox: list[int],
    bbox: list[int],
    regions: list[dict],
) -> tuple[list[int], bool]:
    region = _staff_band_for_bbox(bbox, regions)
    if region is None:
        return search_bbox, False

    band_top = int(region["y0"])
    band_bottom = min(
        int(region["y0"] + region["h"]),
        int(region.get("staff_top", region["y0"] + region["h"])),
    )
    if band_bottom <= band_top:
        return search_bbox, False

    x1, _, x2, _ = search_bbox
    constrained = [x1, band_top, x2, band_bottom]
    return constrained, True


def _refine_bbox_to_glyph(
    gray: Image.Image,
    bbox: list[int],
    regions: list[dict] | None = None,
) -> list[int]:
    """Tighten an OCR bbox to the visible dark chord glyph when possible."""
    width, height = gray.size
    search = _expanded_bbox(bbox, width, height)
    constrained = False
    if regions:
        search, constrained = _constrain_search_to_staff_band(search, bbox, regions)
    refined = _dark_pixel_bounds(gray, search)
    if refined is None:
        return bbox

    rx1, ry1, rx2, ry2 = refined
    bx1, by1, bx2, by2 = bbox
    refined_w = rx2 - rx1
    refined_h = ry2 - ry1
    bbox_w = max(1, bx2 - bx1)
    bbox_h = max(1, by2 - by1)

    # Reject implausible refinements caused by nearby notation or lyrics.
    if refined_w < 2 or refined_h < 2:
        return bbox
    if refined_w > bbox_w * 2.2 or refined_h > bbox_h * 1.8:
        return bbox
    if rx2 <= bx1 or rx1 >= bx2:
        return bbox
    if not constrained and (ry2 <= by1 or ry1 >= by2):
        return bbox

    return refined


def _style_from_gpt(chord: dict[str, Any], height: int) -> dict:
    style: dict = {}
    try:
        font_size_pct = _pct_to_unit(chord["font_size_pct"])
        font_size = int(round(font_size_pct * height))
        if font_size > 0:
            style["font_size"] = font_size
    except (KeyError, TypeError, ValueError):
        pass

    weight = chord.get("font_weight")
    if isinstance(weight, str) and weight.lower() in {"regular", "bold"}:
        style["font_weight"] = weight.lower()

    italic = chord.get("italic")
    if isinstance(italic, bool):
        style["italic"] = italic

    color = chord.get("color")
    if isinstance(color, str):
        color = color.lower()
        palette = {
            "black": (25, 25, 25),
            "dark_gray": (55, 55, 55),
            "gray": (95, 95, 95),
            "blue": (30, 45, 120),
        }
        if color in palette:
            style["ink"] = palette[color]
            style["color_name"] = color
    return style


def _image_payload(image_path: str) -> tuple[str, str, tuple[int, int]]:
    """Return media type, base64 data, and the size sent to OpenAI."""
    media_type = _media_type(image_path)
    if MAX_SIDE is None:
        with open(image_path, "rb") as f:
            return media_type, base64.b64encode(f.read()).decode("ascii"), (0, 0)

    with Image.open(image_path) as img:
        img = img.convert("RGB")
        width, height = img.size
        scale = min(1.0, MAX_SIDE / max(width, height))
        if scale < 1.0:
            new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92, optimize=True)
        return "image/jpeg", base64.b64encode(buf.getvalue()).decode("ascii"), img.size


def _request_openai(image_path: str) -> tuple[str, dict]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")

    media_type, b64_data, sent_size = _image_payload(image_path)
    payload = {
        "model": _MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": _PROMPT,
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{b64_data}",
                    },
                },
            ],
        }],
    }

    req = urllib.request.Request(
        _OPENAI_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            response_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI OCR request failed: {exc.code} {detail}") from exc

    try:
        raw_text = response_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"Unexpected OpenAI response shape: {response_data}") from exc
    return raw_text, {
        "usage": response_data.get("usage", {}),
        "sent_size": sent_size,
    }


def run_ocr_gpt_vision(image_path: str) -> tuple[list[dict], dict]:
    """Detect chord symbols with GPT vision and convert percent boxes to pixels."""
    t0 = time.perf_counter()
    with Image.open(image_path) as img:
        rgb = img.convert("RGB")
        width, height = img.size
        gray = rgb.convert("L")
        regions, region_mode = select_ocr_regions(rgb)

    raw_text, response_meta = _request_openai(image_path)
    data = _extract_json(raw_text)
    chords = data.get("chords")
    if not isinstance(chords, list):
        raise ValueError(f"Expected 'chords' list from OpenAI, got {type(chords)}")

    raw_items: list[dict] = []
    for chord in chords:
        if not isinstance(chord, dict) or not isinstance(chord.get("text"), str):
            continue
        text = normalize_chord_text(chord["text"])
        try:
            bbox = _bbox_from_pct(chord, width, height)
        except (KeyError, TypeError, ValueError):
            continue
        raw_items.append({
            "text": text,
            "bbox": bbox,
            "confidence": 1.0,
            "style": _style_from_gpt(chord, height),
        })

    strict_items = [item for item in raw_items if is_chord_candidate(item["text"])]
    failed_items = [item for item in raw_items if not is_chord_candidate(item["text"])]
    recovered_items, parse_count, split_count = recover_candidates(failed_items)

    items: list[dict] = []
    refined_count = 0
    for item in strict_items + recovered_items:
        bbox = item.get("bbox")
        if bbox is None:
            items.append(item)
            continue
        refined_bbox = _refine_bbox_to_glyph(gray, [int(v) for v in bbox], regions)
        if refined_bbox != bbox:
            refined_count += 1
        items.append({**item, "bbox": refined_bbox})

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    usage = response_meta["usage"]
    sent_width, sent_height = response_meta["sent_size"]
    if sent_width == 0 or sent_height == 0:
        sent_width, sent_height = width, height
    return items, {
        "ocr_engine": "gpt-vision",
        "model": _MODEL,
        "max_side": MAX_SIDE,
        "image_width": width,
        "image_height": height,
        "sent_image_width": sent_width,
        "sent_image_height": sent_height,
        "predict_ms": elapsed_ms,
        "total_ms": elapsed_ms,
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "ai_used": True,
        "raw_response_text": raw_text,
        "recovery": {"parse": parse_count, "split": split_count},
        "bbox_refined_count": refined_count,
        "bbox_refine_region_mode": region_mode,
    }
