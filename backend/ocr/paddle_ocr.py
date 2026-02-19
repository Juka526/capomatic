"""PaddleOCR runner for chord sheet images.

Loads a singleton OCR engine on first call so subsequent requests reuse
the already-initialised models without re-loading weights.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from backend.ocr.preprocess import select_ocr_regions, stitch_regions
from backend.chords.normalize import normalize_chord_text

if TYPE_CHECKING:
    from paddleocr import PaddleOCR as _PaddleOCRType

_ocr_instance: "_PaddleOCRType | None" = None


def get_ocr():
    """Return the singleton PaddleOCR engine, initialising it on first call.

    PaddleOCR is imported lazily so the module can be imported without
    PaddlePaddle installed (useful when running with --engine stub).

    Tuning notes
    ------------
    * lang="en"  — English character set covers all chord symbols.
    * use_doc_orientation_classify=False / use_doc_unwarping=False — skips the
      document-level orientation and unwarping models; chord sheets are always
      flat and upright so these add time with no benefit.
    * use_textline_orientation=False — skips per-line rotation model for speed.
    * Set PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True to skip connectivity check.
    """
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR  # noqa: PLC0415
        _ocr_instance = PaddleOCR(
            lang="en",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    return _ocr_instance


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
        crop_mode   : "staff_bands" | "top40_fallback"
        num_regions : int
        regions     : list of {y0, h, staff_top, staff_bottom}
    """
    img = Image.open(image_path).convert("RGB")
    regions, mode = select_ocr_regions(img)

    ocr = get_ocr()
    items: list[dict] = []

    region_meta = [
        {
            "y0":          r["y0"],
            "h":           r["h"],
            "staff_top":   r.get("staff_top"),
            "staff_bottom": r.get("staff_bottom"),
        }
        for r in regions
    ]

    if mode == "staff_bands" and len(regions) > 1:
        # --- STITCHED PATH: one predict() call for all bands combined ---
        stitched, stitch_map = stitch_regions(regions)
        raw_result = ocr.predict(stitched)
        if raw_result:
            res = raw_result[0]
            rec_texts  = res.get("rec_texts",  []) or []
            rec_scores = res.get("rec_scores", []) or []
            rec_polys  = res.get("rec_polys",  []) or []

            for text, confidence, poly in zip(rec_texts, rec_scores, rec_polys):
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]
                center_y = (min(ys) + max(ys)) / 2

                # Map stitched-canvas y back to original image y.
                # All staff bands have x0=0 so x needs no adjustment.
                y_offset = 0
                for entry in stitch_map:
                    if entry["dst_y0"] <= center_y < entry["dst_y0"] + entry["dst_h"]:
                        y_offset = entry["src_y0"] - entry["dst_y0"]
                        break

                items.append({
                    "text":       normalize_chord_text(str(text)),
                    "confidence": float(confidence),
                    "bbox":       [
                        int(min(xs)),
                        int(min(ys)) + y_offset,
                        int(max(xs)),
                        int(max(ys)) + y_offset,
                    ],
                })

        meta = {
            "crop_mode":    mode,
            "num_regions":  len(regions),
            "stitched":     True,
            "predict_calls": 1,
            "regions":      region_meta,
        }

    else:
        # --- PER-REGION PATH: one predict() call per region (fallback) ---
        for region in regions:
            raw_result = ocr.predict(region["crop"])
            if not raw_result:
                continue

            res = raw_result[0]
            x0 = region["x0"]
            y0 = region["y0"]

            rec_texts  = res.get("rec_texts",  []) or []
            rec_scores = res.get("rec_scores", []) or []
            rec_polys  = res.get("rec_polys",  []) or []

            for text, confidence, poly in zip(rec_texts, rec_scores, rec_polys):
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]
                items.append({
                    "text":       normalize_chord_text(str(text)),
                    "confidence": float(confidence),
                    "bbox":       [
                        int(min(xs)) + x0,
                        int(min(ys)) + y0,
                        int(max(xs)) + x0,
                        int(max(ys)) + y0,
                    ],
                })

        meta = {
            "crop_mode":    mode,
            "num_regions":  len(regions),
            "stitched":     False,
            "predict_calls": len(regions),
            "regions":      region_meta,
        }

    return items, meta