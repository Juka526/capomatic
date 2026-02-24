from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


# ---------------------------------------------------------------------------
# Fallback: global top-N% crop (original Section 3 implementation)
# ---------------------------------------------------------------------------

def crop_top_region(img, ratio: float = 0.40):
    """Crop the top *ratio* fraction of an image.

    Parameters
    ----------
    img : PIL.Image.Image or numpy.ndarray
        Source image.  PIL images are converted to RGB numpy arrays.
    ratio : float
        Fraction of the image height to keep (default 0.40 = top 40 %).

    Returns
    -------
    cropped : numpy.ndarray
        RGB uint8 array of shape (crop_h, W, 3).
    y_offset : int
        Y-pixel in the original image where the crop starts (always 0 here;
        kept for future non-zero-origin crops so callers can map bbox coords).
    """
    if isinstance(img, np.ndarray):
        h = img.shape[0]
        crop_h = max(1, int(h * ratio))
        cropped = img[:crop_h]
        # Ensure RGB; numpy arrays from cv2 are BGR — convert if 3-channel.
        # Callers using PIL should pass the PIL image directly for safety.
    else:
        img = img.convert("RGB")
        w, h = img.size
        crop_h = max(1, int(h * ratio))
        cropped = np.array(img.crop((0, 0, w, crop_h)))

    y_offset = 0
    return cropped, y_offset


# ---------------------------------------------------------------------------
# Section 3.1: Staff-aware chord band cropping
# ---------------------------------------------------------------------------

def detect_staff_systems(img) -> list[tuple[int, int]]:
    """Detect staff systems in *img* and return their Y extents.

    Parameters
    ----------
    img : PIL.Image.Image or numpy.ndarray (RGB or grayscale)

    Returns
    -------
    list of (staff_top_y, staff_bottom_y) in original image coordinates,
    sorted top-to-bottom.  Returns [] if detection fails or finds nothing.
    """
    try:
        # --- Normalise to grayscale numpy array ---
        if isinstance(img, np.ndarray):
            arr = img
            if arr.ndim == 3:
                gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            else:
                gray = arr
        else:
            gray = np.array(img.convert("L"))

        H, W = gray.shape

        # --- Binarise (Otsu) ---
        _, binary = cv2.threshold(gray, 0, 255,
                                  cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # --- Morphological open: keep only long horizontal strokes ---
        # Kernel width covers at least 20% of page width to ignore noteheads/clefs
        # while still detecting lines in lower-resolution or JPEG-compressed scans
        # where staff lines may have gaps (raised from 0.25 → 0.20 for that reason).
        kw = max(30, int(W * 0.20))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, 1))
        h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # --- Find connected components of the horizontal-line image ---
        num_labels, _, stats, _ = cv2.connectedComponentsWithStats(
            h_lines, connectivity=8
        )

        # stats columns: LEFT, TOP, WIDTH, HEIGHT, AREA
        min_w = int(W * 0.20)
        max_h = 8
        line_ys: list[int] = []

        for i in range(1, num_labels):          # skip background (label 0)
            comp_w = stats[i, cv2.CC_STAT_WIDTH]
            comp_h = stats[i, cv2.CC_STAT_HEIGHT]
            comp_top = stats[i, cv2.CC_STAT_TOP]
            if comp_w >= min_w and comp_h <= max_h:
                y_center = comp_top + comp_h // 2
                line_ys.append(y_center)

        if not line_ys:
            return []

        # Deduplicate y-values that land on the same pixel (e.g. two thin
        # connected components sharing the same centroid row).
        line_ys = sorted(set(line_ys))

        # --- Cluster consecutive y-values into staff groups ---
        # Gap threshold: 15px or ~0.9% of image height, whichever is larger.
        # 15px (raised from 12) avoids splitting a staff whose lines are
        # unevenly spaced by up to ~13px (common in lower-res scans).
        gap_threshold = max(15, int(H * 0.009))
        clusters: list[list[int]] = []
        current: list[int] = [line_ys[0]]

        for y in line_ys[1:]:
            if y - current[-1] <= gap_threshold:
                current.append(y)
            else:
                clusters.append(current)
                current = [y]
        clusters.append(current)

        # --- Keep clusters that look like a staff (2–6 lines) ---
        # Minimum lowered to 2: JPEG-compressed scans can lose most staff lines
        # to the morphological open, leaving only 2 clearly detectable segments.
        systems: list[tuple[int, int]] = []
        for cluster in clusters:
            if 2 <= len(cluster) <= 6:
                systems.append((cluster[0], cluster[-1]))

        return systems

    except Exception:
        return []


def build_chord_bands(img, systems: list[tuple[int, int]]) -> list[dict]:
    """Build chord-band crop dicts for each staff system.

    For each system the chord band is the strip directly above the staff top
    line where chord symbols are printed.

    Parameters
    ----------
    img : PIL.Image.Image or numpy.ndarray (RGB)
    systems : list of (staff_top_y, staff_bottom_y)

    Returns
    -------
    list of dicts (sorted by y0, overlapping bands merged):
        crop         : np.ndarray  RGB uint8 (h, W, 3)
        x0           : int  always 0
        y0           : int  band top in original coords
        w            : int  image width
        h            : int  band height
        staff_top    : int  top staff line Y of the associated system
        staff_bottom : int  bottom staff line Y of the associated system
    """
    # Normalise to RGB numpy array
    if isinstance(img, np.ndarray):
        arr = img if img.ndim == 3 else np.stack([img] * 3, axis=-1)
    else:
        arr = np.array(img.convert("RGB"))

    H, W = arr.shape[:2]
    bands: list[dict] = []

    for (top, bottom) in systems:
        if bottom <= top:
            continue

        staff_h = bottom - top
        line_spacing = max(6, staff_h / 4)  # 5 lines → 4 gaps

        gap_above = max(8,  min(26,  int(line_spacing * 0.70)))
        pad_below = max(4,  min(16,  int(line_spacing * 0.40)))
        band_h    = max(80, min(190, int(line_spacing * 3.40)))

        band_bottom = min(H, top + pad_below)
        band_top    = max(0, top - gap_above - band_h)

        if band_bottom <= band_top:
            continue

        crop = arr[band_top:band_bottom, :, :]
        bands.append({
            "crop":         crop,
            "x0":           0,
            "y0":           band_top,
            "w":            W,
            "h":            band_bottom - band_top,
            "staff_top":    top,
            "staff_bottom": bottom,
            "line_spacing": line_spacing,
            "gap_above":    gap_above,
            "pad_below":    pad_below,
            "band_h":       band_h,
        })

    if not bands:
        return []

    # --- Merge overlapping / adjacent bands (sorted by y0) ---
    bands.sort(key=lambda b: b["y0"])
    merged: list[dict] = [bands[0]]

    for band in bands[1:]:
        prev     = merged[-1]
        prev_end = prev["y0"] + prev["h"]
        merge_gap = max(10, min(28, int(prev["line_spacing"] * 0.9)))
        if band["y0"] <= prev_end + merge_gap:
            new_y0  = min(prev["y0"], band["y0"])
            new_end = max(prev_end, band["y0"] + band["h"])
            merged[-1] = {
                "crop":         arr[new_y0:new_end, :, :],
                "x0":           0,
                "y0":           new_y0,
                "w":            W,
                "h":            new_end - new_y0,
                "staff_top":    prev["staff_top"],
                "staff_bottom": band["staff_bottom"],
                "line_spacing": prev["line_spacing"],
                "gap_above":    prev["gap_above"],
                "pad_below":    prev["pad_below"],
                "band_h":       prev["band_h"],
            }
        else:
            merged.append(band)

    return merged


def stitch_regions(regions: list[dict], pad: int = 10, bg: int = 255) -> tuple[np.ndarray, list[dict]]:
    """Stitch multiple band crops vertically into one image for a single predict() call.

    Parameters
    ----------
    regions : list of dicts from select_ocr_regions (each must have 'crop', 'y0', 'h')
    pad     : pixels of white space inserted between consecutive regions
    bg      : background fill value (default 255 = white)

    Returns
    -------
    stitched_rgb : np.ndarray  (H_total, W_max, 3) uint8
    stitch_map   : list of dicts:
        { src_y0, src_h, dst_y0, dst_h }
        where src_y0/src_h are in original image coordinates and
        dst_y0/dst_h are in the stitched canvas.
    """
    sorted_regions = sorted(regions, key=lambda r: r["y0"])
    W_max   = max(r["crop"].shape[1] for r in sorted_regions)
    H_total = sum(r["crop"].shape[0] for r in sorted_regions) + pad * (len(sorted_regions) - 1)

    canvas = np.full((H_total, W_max, 3), bg, dtype=np.uint8)
    stitch_map: list[dict] = []
    dst_y = 0

    for region in sorted_regions:
        crop = region["crop"]
        h, w = crop.shape[:2]
        canvas[dst_y : dst_y + h, :w] = crop
        stitch_map.append({
            "src_y0": region["y0"],
            "src_h":  h,
            "dst_y0": dst_y,
            "dst_h":  h,
        })
        dst_y += h + pad

    return canvas, stitch_map


def select_ocr_regions(img) -> tuple[list[dict], str]:
    """Choose OCR regions for *img*: staff bands when possible, top-40% fallback.

    Parameters
    ----------
    img : PIL.Image.Image or numpy.ndarray (RGB)

    Returns
    -------
    (regions, mode)
        regions : list[dict]  same schema as build_chord_bands output
        mode    : "staff_bands" | "top40_fallback"
    """
    # Normalise to PIL for crop_top_region fallback + dimension access
    if isinstance(img, np.ndarray):
        pil_img = Image.fromarray(img)
    else:
        pil_img = img.convert("RGB")

    W, H = pil_img.size
    arr = np.array(pil_img)

    systems = detect_staff_systems(arr)
    if systems:
        bands = build_chord_bands(arr, systems)
        if bands:
            return bands, "staff_bands"

    # Fallback: top-40% global crop
    cropped, _ = crop_top_region(pil_img, ratio=0.40)
    return (
        [{"crop": cropped, "x0": 0, "y0": 0, "w": W, "h": cropped.shape[0]}],
        "top40_fallback",
    )
