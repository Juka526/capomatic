"""Hybrid PaddleOCR + GPT vision chord OCR.

PaddleOCR is the spatial source of truth. GPT is used to correct text inside
Paddle boxes and to optionally fill missed chord gaps.
"""
from __future__ import annotations

import base64
import concurrent.futures
import io
import json
import os
import re
import tempfile
import threading
import time
import urllib.error
import urllib.request
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from backend.chords.normalize import normalize_chord_text
from backend.ocr.filter import filter_candidates, is_chord_candidate, recover_candidates
from backend.ocr.gpt_ocr import _MODEL, _extract_json, _media_type, _pct_to_unit
from backend.ocr.paddle_ocr import run_ocr_paddle

_OPENAI_URL = "https://api.openai.com/v1/chat/completions"

PADDLE_HIGH_CONF = float(os.environ.get("HYBRID_PADDLE_HIGH_CONF", "0.88"))
PADDLE_LOW_CONF = float(os.environ.get("HYBRID_PADDLE_LOW_CONF", "0.78"))
GPT_TEXT_CONF = float(os.environ.get("HYBRID_GPT_TEXT_CONF", "0.70"))
GPT_GAP_CONF = float(os.environ.get("HYBRID_GPT_GAP_CONF", "0.80"))
ENABLE_GAP_FILL = os.environ.get("HYBRID_GPT_GAP_FILL", "1") != "0"
ENABLE_FULL_IMAGE_GAP_FILL = os.environ.get("HYBRID_GPT_FULL_IMAGE_GAP_FILL", "0") == "1"
ENABLE_HIGH_RECALL_GAP_FILL = os.environ.get("HYBRID_PADDLE_HIGH_RECALL_GAP_FILL", "1") != "0"
CONTACT_SHEET_MAX_SIDE = int(os.environ.get("HYBRID_GPT_CONTACT_MAX_SIDE", "1800"))
FULL_IMAGE_MAX_SIDE = int(os.environ.get("HYBRID_GPT_FULL_MAX_SIDE", "1800"))
HIGH_RECALL_DET_DB_THRESH = float(os.environ.get("HYBRID_PADDLE_DET_DB_THRESH", "0.20"))
HIGH_RECALL_DET_DB_BOX_THRESH = float(os.environ.get("HYBRID_PADDLE_DET_DB_BOX_THRESH", "0.35"))
HIGH_RECALL_DET_DB_UNCLIP_RATIO = float(os.environ.get("HYBRID_PADDLE_DET_DB_UNCLIP_RATIO", "2.0"))
HIGH_RECALL_MIN_NEW_CONF = float(os.environ.get("HYBRID_PADDLE_MIN_NEW_CONF", "0.35"))
CROP_RECOGNITION_BATCH_SIZE = int(os.environ.get("HYBRID_GPT_CROP_BATCH_SIZE", "20"))
GAP_VALIDATION_BATCH_SIZE = int(os.environ.get("HYBRID_GPT_GAP_BATCH_SIZE", "12"))
GPT_MAX_CONCURRENCY = max(1, int(os.environ.get("HYBRID_GPT_MAX_CONCURRENCY", "2")))
_GPT_REQUEST_SLOTS = threading.BoundedSemaphore(GPT_MAX_CONCURRENCY)

_CROP_PROMPT = (
    "Each numbered crop contains one or more possible chord symbols from a sheet music image. "
    "For each crop id, return the chord symbol exactly as written. If the crop contains "
    "multiple adjacent chord symbols, return all chord symbols separated by spaces in one text "
    "value, for example: \"Abm7 Abm7 Db\". Return null if the crop is not a chord. "
    "Exclude lyrics, measure numbers, directions, and non-chord text. "
    "Return JSON only: {items: [{id, text, confidence}]}. confidence is 0.0 to 1.0."
)

_GAP_PROMPT = (
    "This sheet music image has existing OCR boxes drawn in colored rectangles and "
    "numbered labels. Find chord symbols that are NOT covered by any existing box. "
    "Return missed chords only. Coordinates must be percentages relative to the full "
    "image width and height: x_pct,y_pct are top-left of the tight visible chord text; "
    "w_pct,h_pct are exact text width and height. Return JSON only: "
    "{missing: [{text, x_pct, y_pct, w_pct, h_pct, confidence}]}."
)


def _request_openai_image(
    prompt: str,
    image: Image.Image,
    *,
    max_side: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")

    img = image.convert("RGB")
    width, height = img.size
    scale = min(1.0, max_side / max(width, height))
    if scale < 1.0:
        img = img.resize(
            (max(1, round(width * scale)), max(1, round(height * scale))),
            Image.Resampling.LANCZOS,
        )

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92, optimize=True)
    b64_data = base64.b64encode(buf.getvalue()).decode("ascii")

    payload = {
        "model": _MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_data}"},
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
        with _GPT_REQUEST_SLOTS:
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
                response_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI OCR request failed: {exc.code} {detail}") from exc

    raw_text = response_data["choices"][0]["message"]["content"]
    return _extract_json(raw_text), {
        "usage": response_data.get("usage", {}),
        "raw_response_text": raw_text,
        "sent_image_width": img.size[0],
        "sent_image_height": img.size[1],
    }


def _load_label_font(size: int = 18) -> ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _crop_with_padding(
    img: Image.Image,
    bbox: list[int],
    *,
    pad_ratio: float = 0.25,
) -> Image.Image:
    width, height = img.size
    x1, y1, x2, y2 = bbox
    box_w = max(1, x2 - x1)
    box_h = max(1, y2 - y1)
    pad_x = max(3, int(round(box_w * pad_ratio)))
    pad_y = max(3, int(round(box_h * pad_ratio)))
    return img.crop((
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(width, x2 + pad_x),
        min(height, y2 + pad_y),
    ))


def _build_contact_sheet(
    img: Image.Image,
    items: list[dict],
) -> Image.Image:
    font = _load_label_font(18)
    crops: list[tuple[int, Image.Image]] = []
    target_h = 70
    for idx, item in enumerate(items, start=1):
        crop = _crop_with_padding(img, item["bbox"])
        scale = target_h / max(1, crop.height)
        crop = crop.resize(
            (max(1, round(crop.width * scale)), target_h),
            Image.Resampling.LANCZOS,
        )
        crops.append((idx, crop))

    cell_w = max(120, max((crop.width for _, crop in crops), default=80) + 18)
    cell_h = 100
    cols = min(5, max(1, len(crops)))
    rows = (len(crops) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, max(1, rows) * cell_h), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)

    for i, (idx, crop) in enumerate(crops):
        col = i % cols
        row = i // cols
        x = col * cell_w
        y = row * cell_h
        draw.rectangle([x, y, x + cell_w - 1, y + cell_h - 1], outline=(180, 180, 180))
        draw.text((x + 5, y + 4), str(idx), fill=(220, 0, 0), font=font)
        sheet.paste(crop, (x + 8, y + 26))

    return sheet


def _gpt_recognize_crops(
    img: Image.Image,
    items: list[dict],
    *,
    recover_invalid: bool = False,
) -> tuple[dict[int, dict], dict]:
    if not items:
        return {}, {}
    sheet = _build_contact_sheet(img, items)
    data, meta = _request_openai_image(
        _CROP_PROMPT,
        sheet,
        max_side=CONTACT_SHEET_MAX_SIDE,
    )
    result: dict[int, dict] = {}
    raw_items = data.get("items")
    if not isinstance(raw_items, list):
        return result, meta

    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        try:
            idx = int(raw["id"])
        except (KeyError, TypeError, ValueError):
            continue
        text = raw.get("text")
        if text is None:
            continue
        try:
            confidence = float(raw.get("confidence", 1.0))
        except (TypeError, ValueError):
            confidence = 1.0
        confidence = max(0.0, min(1.0, confidence))
        norm = normalize_chord_text(str(text))
        if is_chord_candidate(norm):
            result[idx] = {"text": norm, "confidence": confidence}
            continue
        if not recover_invalid:
            continue

        bbox = items[idx - 1].get("bbox") if 1 <= idx <= len(items) else None
        repaired = re.sub(r"mM(?=\d)", "m", norm)
        if repaired != norm and is_chord_candidate(repaired):
            result[idx] = {
                "text": repaired,
                "confidence": confidence,
                "recovered_items": [{"text": repaired, "confidence": confidence, "bbox": bbox}],
            }
            continue

        recovered, _, _ = recover_candidates([{
            "text": repaired,
            "confidence": confidence,
            "bbox": bbox,
        }])
        if recovered:
            result[idx] = {
                "text": recovered[0]["text"],
                "confidence": confidence,
                "recovered_items": recovered,
            }
    return result, meta


def _empty_usage() -> dict[str, int]:
    return {"prompt_tokens": 0, "completion_tokens": 0}


def _add_usage(target: dict[str, int], usage: dict[str, Any]) -> None:
    target["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
    target["completion_tokens"] += int(usage.get("completion_tokens") or 0)


def _gpt_recognize_crops_batched(
    img: Image.Image,
    items: list[dict],
    *,
    batch_size: int,
    recover_invalid: bool = False,
) -> tuple[dict[int, dict], dict]:
    """Recognize crops in smaller contact sheets and preserve global item ids."""
    if not items:
        return {}, {}

    t_start = time.perf_counter()
    result: dict[int, dict] = {}
    meta: dict[str, Any] = {
        "usage": _empty_usage(),
        "batches": 0,
    }
    batch_size = max(1, batch_size)
    batches = [
        (start, items[start:start + batch_size])
        for start in range(0, len(items), batch_size)
    ]

    def recognize_batch(batch_info: tuple[int, list[dict]]) -> tuple[int, dict, dict]:
        start, batch = batch_info
        batch_by_id, batch_meta = _gpt_recognize_crops(
            img,
            batch,
            recover_invalid=recover_invalid,
        )
        return start, batch_by_id, batch_meta

    workers = min(GPT_MAX_CONCURRENCY, len(batches))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        batch_results = pool.map(recognize_batch, batches)
        for start, batch_by_id, batch_meta in batch_results:
            meta["batches"] += 1
            _add_usage(meta["usage"], batch_meta.get("usage", {}))
            for local_idx, value in batch_by_id.items():
                result[start + local_idx] = value

    meta["usage"]["total_tokens"] = (
        meta["usage"]["prompt_tokens"] + meta["usage"]["completion_tokens"]
    )
    meta["max_concurrency"] = workers
    meta["elapsed_ms"] = round((time.perf_counter() - t_start) * 1000, 1)
    return result, meta


def _draw_marked_boxes(img: Image.Image, items: list[dict]) -> Image.Image:
    marked = img.convert("RGB").copy()
    draw = ImageDraw.Draw(marked)
    font = _load_label_font(16)
    for idx, item in enumerate(items, start=1):
        x1, y1, x2, y2 = item["bbox"]
        draw.rectangle([x1, y1, x2, y2], outline=(255, 0, 0), width=3)
        draw.text((x1, max(0, y1 - 18)), str(idx), fill=(255, 0, 0), font=font)
    return marked


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


def _gpt_gap_fill(
    img: Image.Image,
    items: list[dict],
) -> tuple[list[dict], dict]:
    marked = _draw_marked_boxes(img, items)
    data, meta = _request_openai_image(
        _GAP_PROMPT,
        marked,
        max_side=FULL_IMAGE_MAX_SIDE,
    )
    missing = data.get("missing")
    if not isinstance(missing, list):
        return [], meta

    width, height = img.size
    results: list[dict] = []
    for raw in missing:
        if not isinstance(raw, dict) or not isinstance(raw.get("text"), str):
            continue
        text = normalize_chord_text(raw["text"])
        if not is_chord_candidate(text):
            continue
        try:
            bbox = _bbox_from_pct(raw, width, height)
            confidence = float(raw.get("confidence", 0.8))
        except (KeyError, TypeError, ValueError):
            continue
        results.append({
            "text": text,
            "bbox": bbox,
            "confidence": max(0.0, min(1.0, confidence)),
            "source": "gpt_gap",
        })
    return results, meta


def _iou(a: list[int], b: list[int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1, (bx2 - bx1) * (by2 - by1))
    return inter / (area_a + area_b - inter)


def _center_distance(a: list[int], b: list[int]) -> float:
    acx, acy = (a[0] + a[2]) / 2, (a[1] + a[3]) / 2
    bcx, bcy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    return ((acx - bcx) ** 2 + (acy - bcy) ** 2) ** 0.5


def _dedupe_items(items: list[dict]) -> tuple[list[dict], int]:
    if not items:
        return [], 0
    heights = [i["bbox"][3] - i["bbox"][1] for i in items if i.get("bbox")]
    median_h = sorted(heights)[len(heights) // 2] if heights else 20
    kept: list[dict] = []
    dropped = 0
    for item in items:
        bbox = item.get("bbox")
        if bbox is None:
            kept.append(item)
            continue
        duplicate_idx = None
        for idx, existing in enumerate(kept):
            eb = existing.get("bbox")
            if eb is None:
                continue
            same_row = abs(((bbox[1] + bbox[3]) / 2) - ((eb[1] + eb[3]) / 2)) <= median_h
            if _iou(bbox, eb) >= 0.35 or (same_row and _center_distance(bbox, eb) < 0.6 * median_h):
                duplicate_idx = idx
                break
        if duplicate_idx is None:
            kept.append(item)
            continue

        dropped += 1
        existing = kept[duplicate_idx]
        existing_priority = _source_priority(existing)
        item_priority = _source_priority(item)
        if item_priority < existing_priority:
            kept[duplicate_idx] = item
        elif (
            item_priority == existing_priority
            and float(item.get("confidence", 0)) > float(existing.get("confidence", 0))
        ):
            kept[duplicate_idx] = item
    return kept, dropped


def _source_priority(item: dict) -> int:
    """Return lower priority value for spatially more trustworthy detections."""
    source = str(item.get("source") or "paddle")
    if source in {"paddle", "paddle_bbox_gpt_text", "paddle_bbox_gpt_confirmed"}:
        return 0
    if source in {"paddle_high_recall", "paddle_high_recall_candidate", "component_gap_candidate"}:
        return 1
    if source == "gpt_gap":
        return 2
    if source in {"gpt_high_recall_gap", "paddle_high_recall_gpt_gap"}:
        return 3
    return 4


def _median_bbox_height(items: list[dict]) -> float:
    heights = [
        item["bbox"][3] - item["bbox"][1]
        for item in items
        if item.get("bbox")
    ]
    if not heights:
        return 20.0
    heights.sort()
    mid = len(heights) // 2
    if len(heights) % 2:
        return float(heights[mid])
    return (heights[mid - 1] + heights[mid]) / 2


def _bbox_center(bbox: list[int]) -> tuple[float, float]:
    return (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2


def _bbox_in_chord_regions(bbox: list[int], regions: list[dict] | None) -> bool:
    if not regions:
        return True
    _, cy = _bbox_center(bbox)
    for region in regions:
        y0 = int(region.get("y0", 0))
        h = int(region.get("h", 0))
        if y0 <= cy <= y0 + h:
            return True
    return False


def _overlaps_existing_candidate(
    bbox: list[int],
    existing_items: list[dict],
    median_h: float,
) -> bool:
    for existing in existing_items:
        eb = existing.get("bbox")
        if eb is None:
            continue
        if _iou(bbox, eb) >= 0.25:
            return True
        same_row = abs(_bbox_center(bbox)[1] - _bbox_center(eb)[1]) <= median_h
        if same_row and _center_distance(bbox, eb) < 0.75 * median_h:
            return True
    return False


def _valid_gap_candidate_bbox(
    bbox: list[int],
    existing_items: list[dict],
    width: int,
    height: int,
    regions: list[dict] | None,
) -> tuple[bool, str | None]:
    x1, y1, x2, y2 = bbox
    box_w = x2 - x1
    box_h = y2 - y1
    median_h = _median_bbox_height(existing_items)

    if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
        return False, "out_of_bounds"
    if box_w < 6 or box_h < 6:
        return False, "too_small"
    if box_w > 8 * median_h:
        return False, "too_wide"
    if box_h > 2.5 * median_h:
        return False, "too_tall"
    if x1 >= width - 2 or y1 >= height - 2:
        return False, "near_page_edge"
    if not _bbox_in_chord_regions(bbox, regions):
        return False, "outside_chord_region"
    if _overlaps_existing_candidate(bbox, existing_items, median_h):
        return False, "duplicate"
    return True, None


def _run_high_recall_paddle_candidates(
    img: Image.Image,
    existing_items: list[dict],
    regions: list[dict] | None,
) -> tuple[list[dict], dict]:
    width, height = img.size
    meta: dict = {
        "gap_candidate_count": 0,
        "gap_candidate_rejected": 0,
        "gap_candidate_reject_reasons": {},
    }

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
        img.save(tmp, format="PNG")

    try:
        raw_items, paddle_meta = run_ocr_paddle(
            tmp_path,
            det_db_thresh=HIGH_RECALL_DET_DB_THRESH,
            det_db_box_thresh=HIGH_RECALL_DET_DB_BOX_THRESH,
            det_db_unclip_ratio=HIGH_RECALL_DET_DB_UNCLIP_RATIO,
            read_title=False,
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    meta.update({
        "high_recall_raw_count": len(raw_items),
        "high_recall_predict_ms": paddle_meta.get("predict_ms"),
        "high_recall_total_ms": paddle_meta.get("total_ms"),
        "high_recall_det_db_thresh": HIGH_RECALL_DET_DB_THRESH,
        "high_recall_det_db_box_thresh": HIGH_RECALL_DET_DB_BOX_THRESH,
        "high_recall_det_db_unclip_ratio": HIGH_RECALL_DET_DB_UNCLIP_RATIO,
    })

    candidates: list[dict] = []
    reject_reasons: dict[str, int] = {}
    for item in raw_items:
        bbox = item.get("bbox")
        if bbox is None:
            continue
        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < HIGH_RECALL_MIN_NEW_CONF:
            reject_reasons["low_paddle_confidence"] = reject_reasons.get("low_paddle_confidence", 0) + 1
            continue

        bbox = [int(v) for v in bbox]
        ok, reason = _valid_gap_candidate_bbox(bbox, existing_items + candidates, width, height, regions)
        if not ok:
            key = reason or "invalid"
            reject_reasons[key] = reject_reasons.get(key, 0) + 1
            continue

        candidates.append({
            "text": item.get("text", ""),
            "bbox": bbox,
            "confidence": confidence,
            "source": "paddle_high_recall_candidate",
        })

    meta["gap_candidate_count"] = len(candidates)
    meta["gap_candidate_rejected"] = sum(reject_reasons.values())
    meta["gap_candidate_reject_reasons"] = reject_reasons
    return candidates, meta


def _component_gap_candidates(
    img: Image.Image,
    existing_items: list[dict],
    regions: list[dict] | None,
) -> tuple[list[dict], dict]:
    """Find dark chord-like glyph groups inside OCR bands missed by Paddle."""
    if not regions:
        return [], {
            "component_gap_candidate_count": 0,
            "component_gap_rejected": 0,
            "component_gap_reject_reasons": {},
        }

    width, height = img.size
    gray = np.array(img.convert("L"))
    median_h = _median_bbox_height(existing_items)
    candidates: list[dict] = []
    reject_reasons: dict[str, int] = {}

    for region in regions:
        y0 = int(region.get("y0", 0))
        h = int(region.get("h", 0))
        if h <= 0:
            continue
        y1 = max(0, y0)
        y2 = min(height, y0 + h)
        if y2 <= y1:
            continue

        band = gray[y1:y2, :]
        # Use a strict threshold so gray watermark strokes are ignored while
        # black chord glyphs remain connected components.
        binary = (band < 155).astype("uint8") * 255
        num_labels, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

        components: list[list[int]] = []
        for idx in range(1, num_labels):
            x, y, w, comp_h, area = [int(v) for v in stats[idx]]
            if area < 8:
                continue
            if w < 2 or comp_h < 6:
                continue
            if w > max(90, int(median_h * 3.0)) or comp_h > max(45, int(median_h * 1.8)):
                continue
            # Skip staff-line fragments near the bottom of the chord band.
            if y + comp_h > (y2 - y1) - 4:
                continue
            components.append([x, y, x + w, y + comp_h])

        components.sort(key=lambda b: (b[0], b[1]))
        groups: list[list[list[int]]] = []
        for comp in components:
            placed = False
            cx1, cy1, cx2, cy2 = comp
            cy_mid = (cy1 + cy2) / 2
            for group in groups:
                gx1 = min(c[0] for c in group)
                gy1 = min(c[1] for c in group)
                gx2 = max(c[2] for c in group)
                gy2 = max(c[3] for c in group)
                gy_mid = (gy1 + gy2) / 2
                x_gap = cx1 - gx2
                same_line = abs(cy_mid - gy_mid) <= max(6, median_h * 0.35)
                if same_line and 0 <= x_gap <= max(12, median_h * 0.55):
                    group.append(comp)
                    placed = True
                    break
            if not placed:
                groups.append([comp])

        for group in groups:
            if len(group) < 2:
                continue
            bbox = [
                min(c[0] for c in group),
                y1 + min(c[1] for c in group),
                max(c[2] for c in group),
                y1 + max(c[3] for c in group),
            ]
            ok, reason = _valid_gap_candidate_bbox(
                bbox,
                existing_items + candidates,
                width,
                height,
                regions,
            )
            if not ok:
                key = reason or "invalid"
                reject_reasons[key] = reject_reasons.get(key, 0) + 1
                continue
            candidates.append({
                "text": "",
                "bbox": bbox,
                "confidence": 0.45,
                "source": "component_gap_candidate",
            })

    return candidates, {
        "component_gap_candidate_count": len(candidates),
        "component_gap_rejected": sum(reject_reasons.values()),
        "component_gap_reject_reasons": reject_reasons,
    }


def _gpt_validate_gap_candidates(
    img: Image.Image,
    candidates: list[dict],
) -> tuple[list[dict], dict]:
    if not candidates:
        return [], {}

    gpt_by_id, batch_meta = _gpt_recognize_crops_batched(
        img,
        candidates,
        batch_size=GAP_VALIDATION_BATCH_SIZE,
        recover_invalid=True,
    )
    accepted: list[dict] = []
    rejected = 0
    for idx, candidate in enumerate(candidates, start=1):
        gpt = gpt_by_id.get(idx)
        if not gpt or gpt["confidence"] < GPT_GAP_CONF:
            rejected += 1
            continue
        before_count = len(accepted)
        recovered_items = gpt.get("recovered_items")
        if isinstance(recovered_items, list) and recovered_items:
            for item in recovered_items:
                text = item.get("text")
                bbox = item.get("bbox") or candidate["bbox"]
                if not isinstance(text, str) or not is_chord_candidate(text):
                    continue
                accepted.append({
                    "text": text,
                    "bbox": [int(v) for v in bbox],
                    "confidence": min(1.0, max(float(candidate.get("confidence", 0.0)), gpt["confidence"])),
                    "source": "paddle_high_recall_gpt_gap",
                })
            if len(accepted) == before_count:
                rejected += 1
            continue
        accepted.append({
            "text": gpt["text"],
            "bbox": candidate["bbox"],
            "confidence": min(1.0, max(float(candidate.get("confidence", 0.0)), gpt["confidence"])),
            "source": "paddle_high_recall_gpt_gap",
        })

    meta: dict[str, Any] = {
        "usage": batch_meta.get("usage", _empty_usage()),
        "gpt_gap_batches": batch_meta.get("batches", 0),
        "gpt_gap_max_concurrency": batch_meta.get("max_concurrency", 1),
    }
    meta["gpt_gap_candidates_sent"] = len(candidates)
    meta["gpt_gap_candidates_accepted"] = len(accepted)
    meta["gpt_gap_candidates_rejected"] = rejected
    return accepted, meta


def _refine_gap_items(
    img: Image.Image,
    paddle_items: list[dict],
    regions: list[dict] | None,
) -> tuple[list[dict], dict]:
    """Discover and validate missed chords without changing Paddle detections."""
    t_start = time.perf_counter()
    component_candidates, component_meta = _component_gap_candidates(
        img,
        paddle_items,
        regions,
    )
    candidates = list(component_candidates)
    high_recall_candidates, candidate_meta = _run_high_recall_paddle_candidates(
        img,
        paddle_items + candidates,
        regions,
    )
    candidates.extend(high_recall_candidates)
    validated, gap_meta = _gpt_validate_gap_candidates(img, candidates)
    return validated, {
        **candidate_meta,
        **component_meta,
        "gpt_gap_mode": "paddle_high_recall_candidates",
        "gpt_gap_used": bool(candidates),
        "gpt_gap_ms": round((time.perf_counter() - t_start) * 1000, 1),
        "gpt_gap_count": len(validated),
        "gpt_gap_batches": gap_meta.get("gpt_gap_batches"),
        "gpt_gap_max_concurrency": gap_meta.get("gpt_gap_max_concurrency"),
        "gpt_gap_input_tokens": gap_meta.get("usage", {}).get("prompt_tokens"),
        "gpt_gap_output_tokens": gap_meta.get("usage", {}).get("completion_tokens"),
        "gpt_gap_candidates_sent": gap_meta.get("gpt_gap_candidates_sent", len(candidates)),
        "gpt_gap_candidates_accepted": gap_meta.get("gpt_gap_candidates_accepted", len(validated)),
        "gpt_gap_candidates_rejected": gap_meta.get("gpt_gap_candidates_rejected", 0),
    }


def _merge_gpt_text(
    paddle_items: list[dict],
    gpt_by_id: dict[int, dict],
) -> tuple[list[dict], int, int]:
    merged: list[dict] = []
    replaced = 0
    low_conf_flags = 0
    for idx, item in enumerate(paddle_items, start=1):
        out = {**item, "source": "paddle"}
        if item["confidence"] < PADDLE_LOW_CONF:
            low_conf_flags += 1
        gpt = gpt_by_id.get(idx)
        if gpt and gpt["confidence"] >= GPT_TEXT_CONF and gpt["text"] != item["text"]:
            out["text"] = gpt["text"]
            out["confidence"] = min(1.0, max(float(item["confidence"]), gpt["confidence"]))
            out["source"] = "paddle_bbox_gpt_text"
            replaced += 1
        elif gpt and gpt["confidence"] >= GPT_TEXT_CONF:
            out["confidence"] = min(1.0, max(float(item["confidence"]), gpt["confidence"]))
            out["source"] = "paddle_bbox_gpt_confirmed"
        merged.append(out)
    return merged, replaced, low_conf_flags


def refine_paddle_items_with_gpt(
    img: Image.Image,
    paddle_items: list[dict],
    *,
    base_meta: dict | None = None,
) -> tuple[list[dict], dict]:
    """Apply GPT text correction and gap fill to existing Paddle detections."""
    t_start = time.perf_counter()
    meta: dict = {
        **(base_meta or {}),
        "ocr_engine": "paddle-gpt-hybrid",
        "model": _MODEL,
        "paddle_chord_count": len(paddle_items),
        "gpt_used": False,
        "gpt_gap_used": False,
        "gpt_text_replaced": 0,
        "gpt_gap_count": 0,
        "dedupe_dropped": 0,
        "reused_paddle_detection": True,
    }

    if not os.environ.get("OPENAI_API_KEY"):
        meta["ocr_engine"] = "paddle-only"
        meta["gpt_error"] = "OPENAI_API_KEY environment variable is not set"
        meta["total_ms"] = round((time.perf_counter() - t_start) * 1000, 1)
        return paddle_items, meta

    gap_items: list[dict] = []
    regions = (base_meta or {}).get("regions")
    gap_enabled = ENABLE_GAP_FILL and ENABLE_HIGH_RECALL_GAP_FILL

    # GPT text correction preserves every Paddle bbox. Gap discovery depends on
    # those bboxes only, so both quality-equivalent branches can run together.
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        crop_future = pool.submit(
            _gpt_recognize_crops_batched,
            img.copy(),
            paddle_items,
            batch_size=CROP_RECOGNITION_BATCH_SIZE,
        )
        gap_future = (
            pool.submit(_refine_gap_items, img.copy(), paddle_items, regions)
            if gap_enabled else None
        )

        try:
            gpt_by_id, crop_meta = crop_future.result()
            merged, replaced, low_conf_flags = _merge_gpt_text(paddle_items, gpt_by_id)
            meta.update({
                "gpt_used": True,
                "gpt_crop_batches": crop_meta.get("batches"),
                "gpt_crop_max_concurrency": crop_meta.get("max_concurrency"),
                "gpt_crop_ms": crop_meta.get("elapsed_ms"),
                "gpt_crop_items": len(gpt_by_id),
                "gpt_text_replaced": replaced,
                "low_conf_flags": low_conf_flags,
                "gpt_crop_input_tokens": crop_meta.get("usage", {}).get("prompt_tokens"),
                "gpt_crop_output_tokens": crop_meta.get("usage", {}).get("completion_tokens"),
            })
        except Exception as exc:  # noqa: BLE001
            merged = [{**item, "source": "paddle"} for item in paddle_items]
            meta["gpt_error"] = str(exc)

        if gap_future is not None:
            try:
                gap_items, gap_stage_meta = gap_future.result()
                meta.update(gap_stage_meta)
                meta["gpt_used"] = bool(gap_stage_meta.get("gpt_gap_used")) or bool(meta.get("gpt_used"))
            except Exception as exc:  # noqa: BLE001
                meta["gpt_gap_error"] = str(exc)

    meta["parallel_refinement"] = gap_enabled
    meta["gpt_max_concurrency"] = GPT_MAX_CONCURRENCY

    if ENABLE_GAP_FILL and ENABLE_FULL_IMAGE_GAP_FILL and meta.get("gpt_used"):
        try:
            t0 = time.perf_counter()
            full_gap_items, gap_meta = _gpt_gap_fill(img, merged + gap_items)
            gap_items.extend(full_gap_items)
            meta.update({
                "gpt_gap_used": True,
                "gpt_full_image_gap_ms": round((time.perf_counter() - t0) * 1000, 1),
                "gpt_full_image_gap_count": len(full_gap_items),
                "gpt_full_image_gap_input_tokens": gap_meta.get("usage", {}).get("prompt_tokens"),
                "gpt_full_image_gap_output_tokens": gap_meta.get("usage", {}).get("completion_tokens"),
                "gpt_full_image_gap_sent_image_width": gap_meta.get("sent_image_width"),
                "gpt_full_image_gap_sent_image_height": gap_meta.get("sent_image_height"),
            })
        except Exception as exc:  # noqa: BLE001
            meta["gpt_full_image_gap_error"] = str(exc)

    final_items, dedupe_dropped = _dedupe_items(merged + gap_items)
    meta["dedupe_dropped"] = dedupe_dropped
    meta["final_count"] = len(final_items)
    meta["input_tokens"] = sum(
        int(meta.get(key) or 0)
        for key in ("gpt_crop_input_tokens", "gpt_gap_input_tokens", "gpt_full_image_gap_input_tokens")
    ) or None
    meta["output_tokens"] = sum(
        int(meta.get(key) or 0)
        for key in ("gpt_crop_output_tokens", "gpt_gap_output_tokens", "gpt_full_image_gap_output_tokens")
    ) or None
    meta["total_ms"] = round((time.perf_counter() - t_start) * 1000, 1)
    return final_items, meta


def run_ocr_paddle_gpt_hybrid(image_path: str) -> tuple[list[dict], dict]:
    """Detect chords with Paddle bboxes, GPT text correction, and GPT gap fill."""
    t_start = time.perf_counter()
    raw_paddle_items, paddle_meta = run_ocr_paddle(image_path)
    paddle_items = filter_candidates(raw_paddle_items)

    meta: dict = {
        **paddle_meta,
        "ocr_engine": "paddle-gpt-hybrid",
        "model": _MODEL,
        "paddle_raw_count": len(raw_paddle_items),
        "paddle_chord_count": len(paddle_items),
        "gpt_used": False,
        "gpt_gap_used": False,
        "gpt_text_replaced": 0,
        "gpt_gap_count": 0,
        "dedupe_dropped": 0,
    }

    if not os.environ.get("OPENAI_API_KEY"):
        meta["ocr_engine"] = "paddle-only"
        meta["gpt_error"] = "OPENAI_API_KEY environment variable is not set"
        meta["total_ms"] = round((time.perf_counter() - t_start) * 1000, 1)
        return paddle_items, meta

    img = Image.open(image_path).convert("RGB")
    final_items, meta = refine_paddle_items_with_gpt(img, paddle_items, base_meta=meta)
    meta["paddle_raw_count"] = len(raw_paddle_items)
    meta["total_ms"] = round((time.perf_counter() - t_start) * 1000, 1)
    return final_items, meta
