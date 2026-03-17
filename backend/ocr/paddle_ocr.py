"""PaddleOCR runner for chord sheet images.

Loads a singleton OCR engine on first call so subsequent requests reuse
the already-initialised models without re-loading weights.
"""
from __future__ import annotations

import math
import os
import re
import time
from typing import TYPE_CHECKING

import cv2
from PIL import Image

from backend.ocr.preprocess import select_ocr_regions, stitch_regions
from backend.chords.normalize import normalize_chord_text

if TYPE_CHECKING:
    from paddleocr import PaddleOCR as _PaddleOCRType

_ocr_instances: "dict[str, _PaddleOCRType]" = {}

# Maximum total pixel count of the stitched canvas fed to predict().
# Canvases larger than this are downscaled proportionally with INTER_AREA before
# inference and their OCR coordinates are scaled back afterward.
# Lower values reduce predict() time; too low degrades small-text accuracy.
MAX_STITCHED_PIXELS = 600_000

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
    "2. Bb/D C/E F/A D.S." or "|3.Bb/D".  This function strips the volta
    numbering, splits by whitespace, normalises each token, and returns
    valid chord items.  Non-chord tokens (D.S., al, Coda) are discarded.

    Returns an empty list if the text does not look like a volta block.
    """
    stripped = _VOLTA_PREFIX_RE.sub("", raw_text).strip()
    if not stripped:
        return []

    tokens = stripped.split()
    results: list[dict] = []
    for token in tokens:
        # Skip direction markers (D.S., al, Coda, Fine, etc.)
        if "." in token or _is_direction_token(token):
            continue
        normalized = normalize_chord_text(token)
        if not normalized:
            continue
        results.append({
            "text":       normalized,
            "confidence": item["confidence"],
            "bbox":       item["bbox"],
        })
    return results


def _apply_direction_filter(raw_items: list[dict]) -> list[dict]:
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

        # Volta bracket extraction: try to recover chords from text like
        # "2. Bb/D C/E F/A D.S." before the period filter discards it.
        if "." in raw_text and _VOLTA_PREFIX_RE.match(raw_text):
            chords.extend(_extract_volta_chords(raw_text, item))
            continue

        # Period in the raw text → definitely a direction marker, not a chord.
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


def get_ocr(det_variant: "str | None" = None) -> "_PaddleOCRType":
    """Return a cached PaddleOCR engine for *det_variant*, initialising on first call.

    PaddleOCR is imported lazily so the module can be imported without
    PaddlePaddle installed (useful when running with --engine stub).

    Parameters
    ----------
    det_variant : "server" | "mobile" | None
        Which detector to use. When None the value is read from the env var
        TRANSCHORD_OCR_DET_MODEL (default "server"). Separate cached instances
        are kept per variant so switching does not reuse the wrong model.

    Tuning notes
    ------------
    * lang="en"  — English character set covers all chord symbols.
    * use_doc_orientation_classify=False / use_doc_unwarping=False — skips the
      document-level orientation and unwarping models; chord sheets are always
      flat and upright so these add time with no benefit.
    * use_textline_orientation=False — skips per-line rotation model for speed.
    * Set PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True to skip connectivity check.
    * TRANSCHORD_OCR_DET_MODEL=server|mobile selects the detection model variant.
    """
    global _ocr_instances
    if det_variant is None:
        det_variant = os.environ.get("TRANSCHORD_OCR_DET_MODEL", "server").lower()
    if det_variant not in ("server", "mobile"):
        raise ValueError(
            f"TRANSCHORD_OCR_DET_MODEL must be 'server' or 'mobile', got {det_variant!r}"
        )
    if det_variant not in _ocr_instances:
        from paddleocr import PaddleOCR  # noqa: PLC0415
        kwargs: dict = dict(
            lang="en",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        if det_variant == "mobile":
            kwargs["text_detection_model_name"] = "PP-OCRv5_mobile_det"
        _ocr_instances[det_variant] = PaddleOCR(**kwargs)
    return _ocr_instances[det_variant]


def run_ocr_paddle(image_path: str) -> tuple[list[dict], dict]:
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
        det_model_variant: "server" | "mobile"
    """
    t_start = time.perf_counter()

    det_variant = os.environ.get("TRANSCHORD_OCR_DET_MODEL", "server").lower()
    if det_variant not in ("server", "mobile"):
        raise ValueError(
            f"TRANSCHORD_OCR_DET_MODEL must be 'server' or 'mobile', got {det_variant!r}"
        )

    # ------------------------------------------------------------------
    # Stage 1 — preprocess: load image + select OCR regions
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    img = Image.open(image_path).convert("RGB")
    regions, mode = select_ocr_regions(img)
    preprocess_ms = (time.perf_counter() - t0) * 1000

    ocr = get_ocr(det_variant)
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

    if mode == "staff_bands" and len(regions) > 1:
        # --------------------------------------------------------------
        # Stage 2 — stitch all bands into one canvas
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
                        int(min(ys)) + y_offset,
                        int(max(xs)) + x_offset,
                        int(max(ys)) + y_offset,
                    ],
                })

        items.extend(_apply_direction_filter(raw_items))
        post_ms = (time.perf_counter() - t0) * 1000

        meta = {
            "crop_mode":     mode,
            "num_regions":   len(regions),
            "stitched":      True,
            "predict_calls": 1,
            "regions":       region_meta,
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
            items.extend(_apply_direction_filter(raw_region_items))
            post_ms += (time.perf_counter() - t0) * 1000

        meta = {
            "crop_mode":     mode,
            "num_regions":   len(regions),
            "stitched":      False,
            "predict_calls": len(regions),
            "regions":       region_meta,
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
    })

    return items, meta
