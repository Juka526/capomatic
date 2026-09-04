"""PaddleOCR runner for chord sheet images.

Loads a singleton OCR engine on first call so subsequent requests reuse
the already-initialised models without re-loading weights.
"""
from __future__ import annotations

import math
import logging
import os
import re
import time
from typing import TYPE_CHECKING

import cv2
import numpy as np
from PIL import Image

from backend.ocr.preprocess import select_ocr_regions, stitch_regions
from backend.chords.normalize import normalize_chord_text
from backend.ocr.filter import SECTION_MARKERS, is_chord_candidate, is_section_marker, recover_candidates

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from paddleocr import PaddleOCR as _PaddleOCRType

_ocr_instances: "dict[tuple[str, float | None, float | None, float | None], _PaddleOCRType]" = {}
_title_ocr = None
_title_recognizer = None
_SECTION_MARKERS_CASEFOLD = {marker.casefold() for marker in SECTION_MARKERS}

_DET_MODEL_NAMES = {
    "server": None,
    "mobile": "PP-OCRv5_mobile_det",
    "v6-tiny": "PP-OCRv6_tiny_det",
    "v6-small": "PP-OCRv6_small_det",
    "v6-medium": "PP-OCRv6_medium_det",
}

# Maximum total pixel count of the stitched canvas fed to predict().
# Canvases larger than this are downscaled proportionally with INTER_AREA before
# inference and their OCR coordinates are scaled back afterward.
# Lower values reduce predict() time; too low degrades small-text accuracy.
# Override via PADDLE_MAX_STITCHED_PIXELS env var (default 600k).
# Lowering to 400k saves ~1.4s per image but causes misses on small glyphs like
# A/C# and G#dim at the resulting resize scale (≈0.87×). Set lower only when
# using the mobile detection model (PP-OCRv5_mobile_det) or speed > accuracy.
MAX_STITCHED_PIXELS = int(os.environ.get("PADDLE_MAX_STITCHED_PIXELS", "600000"))
# Oversized stitched canvases are routed to one OCR call per staff band.  This
# avoids resolution loss on high-DPI full-page sheets where a single stitched
# canvas would otherwise be resized so aggressively that chord symbols vanish.
STITCH_MAX_SAFE_PIXELS = int(os.environ.get("PADDLE_STITCH_MAX_SAFE_PIXELS", "900000"))
MIN_STITCH_RESIZE_SCALE = float(os.environ.get("PADDLE_MIN_STITCH_RESIZE_SCALE", "0.85"))

# Detection threshold parameters — configurable for A/B accuracy vs. recall tuning.
# Lower det_db_thresh / det_db_box_thresh → higher recall, more false positives
# (filter.py handles the extra noise via two-pass chord validation).
# Higher det_db_unclip_ratio → larger text boxes, helps catch tight/small chords.
_DET_DB_THRESH      = float(os.environ.get("PADDLE_DET_DB_THRESH",       "0.25"))
_DET_DB_BOX_THRESH  = float(os.environ.get("PADDLE_DET_DB_BOX_THRESH",   "0.45"))
_DET_DB_UNCLIP_RATIO = float(os.environ.get("PADDLE_DET_DB_UNCLIP_RATIO", "1.8"))

# ---------------------------------------------------------------------------
# Spatial context filter — direction-marker proximity rejection
# ---------------------------------------------------------------------------

# Matches tokens that are musical direction markers, not chord symbols.
# Used to build a list of "direction toxins" from all raw OCR detections.
_DIRECTION_RE = re.compile(
    r'^[\.\-\s]|^al$|^[Cc]oda$|^[Ff]ine$|^segno',
    re.IGNORECASE,
)

# A bare chord root is a single letter A–G with no extension.
# When such a root appears near direction tokens it is likely a false positive
# from a segmented direction phrase (e.g. "D" from "D.S. al Coda").
_BARE_ROOT_RE = re.compile(r'^[A-G]$')

# Proximity thresholds for the direction-toxin check.
_DIRECTION_PROXIMITY_X = 150  # px: horizontal distance to direction token center
_DIRECTION_PROXIMITY_Y = 30   # px: vertical distance to direction token center

# Volta bracket prefix: matches "1.", "2.", "|3.", etc. at the start of OCR text.
# These appear when PaddleOCR reads volta bracket endings (1st/2nd/3rd endings)
# as a single text block, e.g. "2. Bb/D C/E F/A D.S." or "|3.Bb/D".
_VOLTA_PREFIX_RE = re.compile(r'^\|?\d+\.?\s*')
_SECTION_PREFIX_RE = re.compile(
    r'^\s*\[(?:INTRO|VERSE|CHORUS|BRIDGE|OUTRO)\]\s*(.*)$',
    re.IGNORECASE,
)
_TITLE_METADATA_RE = re.compile(
    r"^(?:key|capo|tempo|bpm|words?|music|lyrics?|arr(?:anged)?|"
    r"작사|작곡|편곡|원곡|노래)\b",
    re.IGNORECASE,
)
_TRANSPOSE_HEADER_RE = re.compile(r"^[A-G][#b]?\s*(?:->|→)\s*[A-G][#b]?", re.IGNORECASE)


def _is_direction_token(raw_text: str) -> bool:
    """Return True if *raw_text* matches a known musical direction marker token."""
    return bool(_DIRECTION_RE.search(raw_text.strip()))


def _is_bare_root(text: str) -> bool:
    """Return True if *text* is a bare chord root with no extension (A–G only)."""
    return bool(_BARE_ROOT_RE.match(text))


def _near_any_direction(
    bbox: list[int],
    direction_bboxes: list[list[int]],
) -> bool:
    """Return True if *bbox* center is within proximity of any direction-token bbox.

    Proximity is ±_DIRECTION_PROXIMITY_X px horizontally and
    ±_DIRECTION_PROXIMITY_Y px vertically (center-to-center).
    """
    x1, y1, x2, y2 = bbox
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    for db in direction_bboxes:
        dcx = (db[0] + db[2]) / 2
        dcy = (db[1] + db[3]) / 2
        if (abs(cx - dcx) <= _DIRECTION_PROXIMITY_X
                and abs(cy - dcy) <= _DIRECTION_PROXIMITY_Y):
            return True
    return False


def _extract_volta_chords(raw_text: str, item: dict) -> list[dict]:
    """Extract chord symbols from volta bracket OCR text.

    PaddleOCR may read volta endings as a single text block, e.g.
    "2. Bb/D C/E F/A D.S." or "|3.Bb/D".  The shared recovery filter
    extracts valid chords and discards direction markers.

    Returns an empty list if the text does not look like a volta block.
    """
    recovered, _, _ = recover_candidates([{
        "text": raw_text,
        "confidence": item["confidence"],
        "bbox": item["bbox"],
    }])
    return recovered


def _extract_section_suffix_chord(raw_text: str, item: dict) -> dict | None:
    """Recover a chord fused after a section marker, e.g. "[CHORUS] F"."""
    match = _SECTION_PREFIX_RE.match(raw_text)
    if not match:
        return None
    suffix = match.group(1).strip()
    if not suffix:
        return {"drop": True}
    normalized = normalize_chord_text(suffix)
    if not normalized or not is_chord_candidate(normalized):
        return {"drop": True}

    bbox = item.get("bbox")
    if bbox is None:
        suffix_bbox = None
    else:
        x1, y1, x2, y2 = bbox
        suffix_start = len(raw_text) - len(match.group(1))
        ratio = min(1.0, max(0.0, suffix_start / max(1, len(raw_text))))
        suffix_bbox = [x1 + int((x2 - x1) * ratio), y1, x2, y2]

    return {
        "text": normalized,
        "confidence": item["confidence"],
        "bbox": suffix_bbox,
    }


def _split_multi_token(raw_text: str, item: dict) -> list[dict]:
    """Split space-separated multi-chord OCR text into individual chord items.

    PaddleOCR sometimes reads adjacent chords as a single text block,
    e.g. "A D/E E7" or "D/E E/D".  This function splits on whitespace,
    normalises each token, and returns valid chord items with evenly divided
    bounding boxes.

    Returns an empty list if fewer than 2 tokens normalise to valid chords.
    """
    recovered, _, _ = recover_candidates([{
        "text": raw_text,
        "confidence": item["confidence"],
        "bbox": item["bbox"],
    }])
    return recovered


def _apply_direction_filter(
    raw_items: list[dict],
    image_width: int | None = None,
) -> list[dict]:
    """Convert raw OCR items to chord dicts, rejecting direction-contaminated detections.

    Collects all detections, identifies direction-marker tokens (al, Coda, Fine,
    segno, period-prefixed), then rejects any bare single-root chord (A–G) that
    lies within spatial proximity of a direction token.  This prevents false
    positives such as 'D' being accepted when PaddleOCR segments 'D.S. al Coda'
    into separate boxes.

    Parameters
    ----------
    raw_items : list of {raw_text, confidence, bbox} in original image coords

    Returns
    -------
    list of {text, confidence, bbox} — verified chord candidates only
    """
    direction_bboxes: list[list[int]] = [
        item["bbox"] for item in raw_items
        if _is_direction_token(item["raw_text"])
    ]

    chords: list[dict] = []
    for item in raw_items:
        raw_text = item["raw_text"]

        if is_section_marker(raw_text, item.get("bbox"), image_width):
            continue

        section_chord = _extract_section_suffix_chord(raw_text, item)
        if section_chord is not None:
            if not section_chord.get("drop"):
                chords.append(section_chord)
            continue

        # Volta bracket extraction: try to recover chords from text like
        # "2. Bb/D C/E F/A D.S." before the period filter discards it.
        if "." in raw_text and _VOLTA_PREFIX_RE.match(raw_text):
            chords.extend(_extract_volta_chords(raw_text, item))
            continue

        # Multi-token splitting: "A D/E E7" or chords followed by "D.S."
        # read as one block.  This must run before the period-only rejection.
        if " " in raw_text:
            split_items = _split_multi_token(raw_text, item)
            if split_items:
                # Apply direction-proximity check to each split item.
                for si in split_items:
                    if _is_bare_root(si["text"]) and _near_any_direction(
                        si["bbox"], direction_bboxes
                    ):
                        continue
                    chords.append(si)
                continue

        # Period in the raw text → direction marker, not a chord.
        if "." in raw_text:
            continue

        normalized = normalize_chord_text(raw_text)

        # Spatial context: bare single root near a direction token → false positive.
        if _is_bare_root(normalized) and _near_any_direction(
            item["bbox"], direction_bboxes
        ):
            continue

        chords.append({
            "text":       normalized,
            "confidence": item["confidence"],
            "bbox":       item["bbox"],
        })

    return chords


def _sort_reading_order(items: list[dict]) -> list[dict]:
    """Sort OCR chord items by staff row, then left-to-right within each row."""
    boxed = [item for item in items if item.get("bbox") is not None]
    unboxed = [item for item in items if item.get("bbox") is None]
    if not boxed:
        return items

    avg_h = sum(item["bbox"][3] - item["bbox"][1] for item in boxed) / len(boxed)
    threshold = max(20, int(avg_h * 1.5))
    rows: list[list[dict]] = []
    for item in sorted(boxed, key=lambda i: (i["bbox"][1], i["bbox"][0])):
        if not rows:
            rows.append([item])
            continue
        row_min_y = min(i["bbox"][1] for i in rows[-1])
        if item["bbox"][1] - row_min_y <= threshold:
            rows[-1].append(item)
        else:
            rows.append([item])
    return [
        item
        for row in rows
        for item in sorted(row, key=lambda i: i["bbox"][0])
    ] + unboxed


def _select_song_title(raw_items: list[dict], image_size: tuple[int, int]) -> str | None:
    """Pick the prominent centered text from the title area."""
    width, height = image_size
    min_height = max(14, round(height * 0.022))
    candidates: list[tuple[int, float, str]] = []
    for item in raw_items:
        text = str(item.get("raw_text", "")).strip()
        bbox = item.get("bbox")
        if not text or not bbox or len(re.sub(r"[^0-9A-Za-z가-힣]", "", text)) < 2:
            continue
        x1, y1, x2, y2 = bbox
        box_height = y2 - y1
        center_x = (x1 + x2) / 2
        if (
            box_height < min_height
            or not width * 0.15 <= center_x <= width * 0.85
            or _TITLE_METADATA_RE.match(text)
            or _TRANSPOSE_HEADER_RE.match(text)
            or _is_section_marker_row(text)
            or is_section_marker(text, bbox, width)
            or is_chord_candidate(normalize_chord_text(text))
        ):
            continue
        candidates.append((box_height, -abs(center_x - width / 2), text))
    return max(candidates)[2] if candidates else None


def _merge_title_line_items(raw_items: list[dict]) -> list[dict]:
    """Join nearby OCR boxes that form one title line."""
    merged: list[dict] = []
    for item in sorted(raw_items, key=lambda value: (value["bbox"][1], value["bbox"][0])):
        if not item.get("raw_text", "").strip():
            continue
        if merged:
            previous = merged[-1]
            x1, y1, x2, y2 = item["bbox"]
            px1, py1, px2, py2 = previous["bbox"]
            height = max(y2 - y1, py2 - py1)
            if (
                abs((y1 + y2) / 2 - (py1 + py2) / 2) <= height * 0.5
                and x1 - px2 <= height * 1.5
            ):
                previous["raw_text"] = f'{previous["raw_text"].rstrip()} {item["raw_text"].lstrip()}'
                previous["bbox"] = [min(px1, x1), min(py1, y1), max(px2, x2), max(py2, y2)]
                continue
        merged.append({**item, "bbox": list(item["bbox"])})
    return merged


def _is_section_marker_row(text: str) -> bool:
    parts = [
        part.strip().strip("[]:.")
        for part in re.split(r"[-–—−|]+", text)
        if part.strip().strip("[]:.")
    ]
    return len(parts) >= 2 and all(part.casefold() in _SECTION_MARKERS_CASEFOLD for part in parts)


def _get_title_recognizer():
    global _title_recognizer
    if _title_recognizer is None:
        from paddleocr import TextRecognition  # noqa: PLC0415
        _title_recognizer = TextRecognition(
            model_name="korean_PP-OCRv5_mobile_rec",
            enable_mkldnn=os.environ.get("PADDLE_ENABLE_MKLDNN", "0") == "1",
        )
    return _title_recognizer


def _get_title_ocr():
    global _title_ocr
    if _title_ocr is None:
        from paddleocr import PaddleOCR  # noqa: PLC0415
        _title_ocr = PaddleOCR(
            text_detection_model_name="PP-OCRv5_mobile_det",
            text_recognition_model_name="korean_PP-OCRv5_mobile_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=os.environ.get("PADDLE_ENABLE_MKLDNN", "0") == "1",
        )
    return _title_ocr


def _read_song_title(ocr, img: Image.Image, regions: list[dict], mode: str) -> tuple[str | None, float]:
    """OCR only the page header above the first chord band."""
    if not regions:
        return None, 0.0
    title_bottom = (
        min(region["y0"] for region in regions)
        if mode == "staff_bands"
        else round(img.height * 0.25)
    )
    if title_bottom < max(40, round(img.height * 0.04)):
        return None, 0.0

    margin = round(img.width * 0.05)
    crop = np.array(img)[0:title_bottom, margin:img.width - margin]
    t0 = time.perf_counter()
    result = ocr.predict(crop)
    if not result:
        return None, (time.perf_counter() - t0) * 1000

    res = result[0]
    raw_items = []
    blank_candidates = []
    for text, confidence, poly in zip(
        res.get("rec_texts", []) or [],
        res.get("rec_scores", []) or [],
        res.get("rec_polys", []) or [],
    ):
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        bbox = [
            int(min(xs)) + margin,
            int(min(ys)),
            int(max(xs)) + margin,
            int(max(ys)),
        ]
        raw_items.append({
            "raw_text": str(text),
            "confidence": float(confidence),
            "bbox": bbox,
        })
        if not str(text).strip():
            pad = max(2, round((max(ys) - min(ys)) * 0.1))
            blank_candidates.append(np.array(img)[
                max(0, int(min(ys)) - pad):min(title_bottom, int(max(ys)) + pad),
                max(0, int(min(xs)) + margin - pad):min(img.width, int(max(xs)) + margin + pad),
            ])

    if blank_candidates:
        try:
            recognized = list(_get_title_recognizer().predict(blank_candidates))
            blank_index = 0
            for item in raw_items:
                if not item["raw_text"].strip():
                    item["raw_text"] = str(recognized[blank_index].get("rec_text", ""))
                    blank_index += 1
        except Exception:
            logger.warning("Korean title recognition failed", exc_info=True)
    title = _select_song_title(_merge_title_line_items(raw_items), img.size)
    return title, (time.perf_counter() - t0) * 1000


def get_ocr(
    det_variant: "str | None" = None,
    *,
    det_db_thresh: float | None = None,
    det_db_box_thresh: float | None = None,
    det_db_unclip_ratio: float | None = None,
) -> "_PaddleOCRType":
    """Return a cached PaddleOCR engine for *det_variant*, initialising on first call.

    PaddleOCR is imported lazily so the module can be imported without
    PaddlePaddle installed (useful when running with --engine stub).

    Parameters
    ----------
    det_variant : "server" | "mobile" | "v6-tiny" | "v6-small" | "v6-medium" | None
        Which detector to use. When None the value is read from the env var
        CHORDTAYLOR_OCR_DET_MODEL (default "server"). Separate cached instances
        are kept per variant so switching does not reuse the wrong model.

    Tuning notes
    ------------
    * use_doc_orientation_classify=False / use_doc_unwarping=False — skips the
      document-level orientation and unwarping models; chord sheets are always
      flat and upright so these add time with no benefit.
    * use_textline_orientation=False — skips per-line rotation model for speed.
    * Set PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True to skip connectivity check.
    * CHORDTAYLOR_OCR_DET_MODEL=server|mobile|v6-tiny|v6-small|v6-medium selects the detection model variant.
    * PADDLE_DET_DB_THRESH (default 0.25): lower → higher recall, more noise.
    * PADDLE_DET_DB_BOX_THRESH (default 0.45): box confidence cutoff.
    * PADDLE_DET_DB_UNCLIP_RATIO (default 1.8): box expansion ratio for small glyphs.
    * PADDLE_MAX_STITCHED_PIXELS (default 600000): canvas pixel cap before downscale.
    * PADDLE_STITCH_MAX_SAFE_PIXELS (default 900000): above this, run per-band OCR.
    * PADDLE_MIN_STITCH_RESIZE_SCALE (default 0.85): below this, run per-band OCR.
    """
    global _ocr_instances
    if det_variant is None:
        det_variant = os.environ.get("CHORDTAYLOR_OCR_DET_MODEL", "server").lower()
    if det_variant not in _DET_MODEL_NAMES:
        raise ValueError(
            "CHORDTAYLOR_OCR_DET_MODEL must be one of "
            f"{sorted(_DET_MODEL_NAMES)}, got {det_variant!r}"
        )
    cache_key = (det_variant, det_db_thresh, det_db_box_thresh, det_db_unclip_ratio)
    if cache_key not in _ocr_instances:
        from paddleocr import PaddleOCR  # noqa: PLC0415
        kwargs: dict = dict(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            # Paddle 3.3.x has a Linux oneDNN regression. Production stays on
            # 3.2.2, but acceleration remains opt-in until the HF gate passes.
            enable_mkldnn=os.environ.get("PADDLE_ENABLE_MKLDNN", "0") == "1",
        )
        explicit_params = {
            "det_db_thresh": det_db_thresh,
            "det_db_box_thresh": det_db_box_thresh,
            "det_db_unclip_ratio": det_db_unclip_ratio,
        }
        for kwarg_name, value in explicit_params.items():
            if value is not None:
                kwargs[kwarg_name] = float(value)

        # Only apply env det params when explicitly overridden — PP-OCRv5 server
        # model is sensitive to these values and regressions occur with
        # non-default settings. Explicit function params win over env vars.
        for env_var, kwarg_name in [
            ("PADDLE_DET_DB_THRESH",       "det_db_thresh"),
            ("PADDLE_DET_DB_BOX_THRESH",   "det_db_box_thresh"),
            ("PADDLE_DET_DB_UNCLIP_RATIO", "det_db_unclip_ratio"),
        ]:
            if explicit_params[kwarg_name] is None and env_var in os.environ:
                kwargs[kwarg_name] = float(os.environ[env_var])
        model_name = _DET_MODEL_NAMES[det_variant]
        if model_name:
            kwargs["text_detection_model_name"] = model_name
        _ocr_instances[cache_key] = PaddleOCR(**kwargs)
    return _ocr_instances[cache_key]


def run_ocr_paddle(
    image_path: str,
    *,
    det_db_thresh: float | None = None,
    det_db_box_thresh: float | None = None,
    det_db_unclip_ratio: float | None = None,
    read_title: bool = True,
) -> tuple[list[dict], dict]:
    """Run PaddleOCR on chord-band regions of *image_path*.

    Uses staff-aware band cropping (Section 3.1) when staff lines can be
    detected; falls back to the global top-40% crop otherwise.

    Returns
    -------
    items : list of dict with keys:
        text        : str   — normalised chord text
        confidence  : float — OCR confidence score 0..1
        bbox        : [x1, y1, x2, y2] — axis-aligned box in original coords
    meta : dict with keys:
        crop_mode        : "staff_bands" | "top40_fallback"
        num_regions      : int
        regions          : list of {y0, h, staff_top, staff_bottom}
        stitched         : bool
        predict_calls    : int
        preprocess_ms    : float  — image load + region selection time
        stitch_ms        : float  — stitch_regions() time (0 if not stitched)
        predict_ms       : float  — ocr.predict() time (summed for per-region)
        post_ms          : float  — coordinate mapping + item building time
        total_ms         : float  — total wall time inside run_ocr_paddle
        stitched_shape   : [H, W] or None
        stitched_pixels  : int (H*W) or 0
        resize_applied   : bool
        resize_scale     : float or None
        resized_shape    : [H, W] or None
        det_model_variant: "server" | "mobile" | "v6-tiny" | "v6-small" | "v6-medium"
    """
    t_start = time.perf_counter()

    det_variant = os.environ.get("CHORDTAYLOR_OCR_DET_MODEL", "server").lower()
    if det_variant not in _DET_MODEL_NAMES:
        raise ValueError(
            "CHORDTAYLOR_OCR_DET_MODEL must be one of "
            f"{sorted(_DET_MODEL_NAMES)}, got {det_variant!r}"
        )
    det_model_name = _DET_MODEL_NAMES[det_variant] or "PP-OCRv5_server_det"

    # ------------------------------------------------------------------
    # Stage 1 — preprocess: load image + select OCR regions
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    img = Image.open(image_path).convert("RGB")
    regions, mode = select_ocr_regions(img)
    preprocess_ms = (time.perf_counter() - t0) * 1000

    ocr = get_ocr(
        det_variant,
        det_db_thresh=det_db_thresh,
        det_db_box_thresh=det_db_box_thresh,
        det_db_unclip_ratio=det_db_unclip_ratio,
    )
    song_title = None
    title_predict_ms = 0.0
    if read_title:
        try:
            song_title, title_predict_ms = _read_song_title(_get_title_ocr(), img, regions, mode)
        except Exception:
            logger.warning("Song title OCR failed", exc_info=True)
    items: list[dict] = []

    region_meta = [
        {
            "y0":           r["y0"],
            "h":            r["h"],
            "staff_top":    r.get("staff_top"),
            "staff_bottom": r.get("staff_bottom"),
        }
        for r in regions
    ]

    # Shared timing accumulators (filled by whichever path runs)
    stitch_ms       = 0.0
    predict_ms      = 0.0
    post_ms         = 0.0
    stitched_shape  = None
    stitched_pixels = 0
    resize_applied  = False
    resize_scale    = 1.0
    resized_shape   = None

    stitched_candidate_shape = None
    stitched_candidate_pixels = 0
    stitched_resize_scale = 1.0
    use_stitched = mode == "staff_bands" and len(regions) > 1
    stitch_skip_reason: str | None = None

    if use_stitched:
        max_w = max(r["crop"].shape[1] for r in regions)
        total_h = sum(r["crop"].shape[0] for r in regions) + 10 * (len(regions) - 1)
        stitched_candidate_shape = [total_h, max_w]
        stitched_candidate_pixels = total_h * max_w
        if stitched_candidate_pixels > MAX_STITCHED_PIXELS:
            stitched_resize_scale = math.sqrt(MAX_STITCHED_PIXELS / stitched_candidate_pixels)
        if stitched_candidate_pixels > STITCH_MAX_SAFE_PIXELS:
            use_stitched = False
            stitch_skip_reason = "too_many_pixels"
        elif stitched_resize_scale < MIN_STITCH_RESIZE_SCALE:
            use_stitched = False
            stitch_skip_reason = "resize_scale_too_small"

    if use_stitched:
        # --------------------------------------------------------------
        # Stage 2 — stitch band crops into one canvas
        # --------------------------------------------------------------
        t0 = time.perf_counter()
        stitched, stitch_map = stitch_regions(regions)
        stitch_ms = (time.perf_counter() - t0) * 1000

        H_s, W_s = stitched.shape[:2]
        stitched_shape  = [H_s, W_s]
        stitched_pixels = H_s * W_s

        # --------------------------------------------------------------
        # Stage 2b — resize cap: shrink large canvases to MAX_STITCHED_PIXELS
        # --------------------------------------------------------------
        predict_input = stitched
        orig_pixels   = H_s * W_s
        if orig_pixels > MAX_STITCHED_PIXELS:
            resize_scale  = math.sqrt(MAX_STITCHED_PIXELS / orig_pixels)
            new_W         = max(1, round(W_s * resize_scale))
            new_H         = max(1, round(H_s * resize_scale))
            predict_input = cv2.resize(stitched, (new_W, new_H),
                                       interpolation=cv2.INTER_AREA)
            resize_applied = True
            resized_shape  = [new_H, new_W]

        # --------------------------------------------------------------
        # Stage 3 — predict (single call on stitched/resized canvas)
        # --------------------------------------------------------------
        t0 = time.perf_counter()
        raw_result = ocr.predict(predict_input)
        predict_ms = (time.perf_counter() - t0) * 1000

        # --------------------------------------------------------------
        # Stage 4 — post-process: map coords back to original image
        # --------------------------------------------------------------
        t0 = time.perf_counter()
        raw_items: list[dict] = []
        if raw_result:
            res = raw_result[0]
            rec_texts  = res.get("rec_texts",  []) or []
            rec_scores = res.get("rec_scores", []) or []
            rec_polys  = res.get("rec_polys",  []) or []

            for text, confidence, poly in zip(rec_texts, rec_scores, rec_polys):
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]

                # Scale back from resized → stitched coordinates
                if resize_applied:
                    xs = [x / resize_scale for x in xs]
                    ys = [y / resize_scale for y in ys]

                center_y = (min(ys) + max(ys)) / 2

                # Map stitched-canvas coords back to original image coords.
                # x_offset accounts for left-margin crop (bar numbers / segno).
                y_offset = 0
                x_offset = 0
                for entry in stitch_map:
                    if entry["dst_y0"] <= center_y < entry["dst_y0"] + entry["dst_h"]:
                        y_offset = entry["src_y0"] - entry["dst_y0"]
                        x_offset = entry.get("x0", 0)
                        break

                raw_items.append({
                    "raw_text":   str(text),
                    "confidence": float(confidence),
                    "bbox": [
                        int(min(xs)) + x_offset,
                        int(min(ys) + y_offset),
                        int(max(xs)) + x_offset,
                        int(max(ys) + y_offset),
                    ],
                })

        items.extend(_apply_direction_filter(raw_items, img.width))
        post_ms = (time.perf_counter() - t0) * 1000

        meta = {
            "crop_mode":     mode,
            "num_regions":   len(regions),
            "stitched":      True,
            "predict_calls": 1,
            "regions":       region_meta,
            "stitch_decision": "stitched",
        }

    else:
        # --------------------------------------------------------------
        # PER-REGION PATH — one predict() call per region (fallback)
        # --------------------------------------------------------------
        for region in regions:
            t0 = time.perf_counter()
            raw_result = ocr.predict(region["crop"])
            predict_ms += (time.perf_counter() - t0) * 1000

            if not raw_result:
                continue

            t0 = time.perf_counter()
            res = raw_result[0]
            x0 = region["x0"]
            y0 = region["y0"]

            rec_texts  = res.get("rec_texts",  []) or []
            rec_scores = res.get("rec_scores", []) or []
            rec_polys  = res.get("rec_polys",  []) or []

            raw_region_items: list[dict] = []
            for text, confidence, poly in zip(rec_texts, rec_scores, rec_polys):
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]
                raw_region_items.append({
                    "raw_text":   str(text),
                    "confidence": float(confidence),
                    "bbox": [
                        int(min(xs)) + x0,
                        int(min(ys)) + y0,
                        int(max(xs)) + x0,
                        int(max(ys)) + y0,
                    ],
                })
            items.extend(_apply_direction_filter(raw_region_items, img.width))
            post_ms += (time.perf_counter() - t0) * 1000

        meta = {
            "crop_mode":     mode,
            "num_regions":   len(regions),
            "stitched":      False,
            "predict_calls": len(regions),
            "regions":       region_meta,
            "stitch_decision": "per_region",
            "stitch_skip_reason": stitch_skip_reason,
        }

    # ------------------------------------------------------------------
    # Attach timing + geometry to meta (both paths)
    # ------------------------------------------------------------------
    meta.update({
        "preprocess_ms":  round(preprocess_ms, 1),
        "stitch_ms":      round(stitch_ms, 1),
        "predict_ms":     round(predict_ms, 1),
        "post_ms":        round(post_ms, 1),
        "total_ms":       round((time.perf_counter() - t_start) * 1000, 1),
        "stitched_shape":  stitched_shape,
        "stitched_pixels": stitched_pixels,
        "resize_applied":  resize_applied,
        "resize_scale":    round(resize_scale, 4) if resize_applied else None,
        "resized_shape":   resized_shape,
        "det_model_variant": det_variant,
        "det_model_name": det_model_name,
        "mkldnn_enabled": os.environ.get("PADDLE_ENABLE_MKLDNN", "0") == "1",
        "det_db_thresh": det_db_thresh,
        "det_db_box_thresh": det_db_box_thresh,
        "det_db_unclip_ratio": det_db_unclip_ratio,
        "stitched_candidate_shape": stitched_candidate_shape,
        "stitched_candidate_pixels": stitched_candidate_pixels,
        "stitched_resize_scale": round(stitched_resize_scale, 4),
        "stitch_max_safe_pixels": STITCH_MAX_SAFE_PIXELS,
        "min_stitch_resize_scale": MIN_STITCH_RESIZE_SCALE,
        "song_title": song_title,
        "title_predict_ms": round(title_predict_ms, 1),
    })

    return _sort_reading_order(items), meta
