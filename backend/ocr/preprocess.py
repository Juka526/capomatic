from __future__ import annotations

import logging
import os

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Band image enhancement
# ---------------------------------------------------------------------------

def _enhance_band_crop(crop: np.ndarray) -> np.ndarray:
    """Apply CLAHE + unsharp mask to a band crop for improved OCR contrast.

    Converts to grayscale, applies Contrast Limited Adaptive Histogram
    Equalization (CLAHE) for local contrast normalisation, then sharpens
    chord text strokes with an unsharp mask.  The result is converted back
    to RGB so PaddleOCR receives the expected 3-channel input.

    Only called when PADDLE_ENHANCE_BANDS=1 is set. This is most useful for
    photographed or low-contrast sheets. Clean digital PNGs should NOT use
    this — CLAHE introduces artificial contrast gradients that hurt detection
    on already-clean images.
    """
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    # Unsharp mask: result = original + 1.5 * (original − blurred)
    blurred = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=1.0)
    sharpened = cv2.addWeighted(enhanced, 2.5, blurred, -1.5, 0)
    return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2RGB)


_ENHANCE_BANDS = os.environ.get("PADDLE_ENHANCE_BANDS", "0") == "1"


# ---------------------------------------------------------------------------
# Left-margin crop constants
# ---------------------------------------------------------------------------
# Fraction of image width scanned for bar numbers / segno on the left margin.
_CHORD_X_MARGIN_RATIO = 0.08
# Minimum consecutive blank columns required to confirm a margin/chord gap.
_GAP_MIN_COLS = 4
# Bar numbers end within this fraction; tempo/clef markings extend past it.
# Used to avoid over-cropping on the first staff row where the tempo marking
# (♩=62, time sig) sits in the chord band but must NOT be treated as a
# bar-number margin.
_NARROW_MARGIN_RATIO = 0.03


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

def _staff_fragment_score(binary: np.ndarray, y_top: int, y_bottom: int) -> int:
    """Return count of staff-like dark rows in a candidate vertical window."""
    H, W = binary.shape
    y1 = max(0, y_top)
    y2 = min(H, y_bottom)
    if y2 <= y1:
        return 0
    row_sums = (binary[y1:y2] > 0).sum(axis=1)
    # Fragmented systems under watermarks may not span the full page, but staff
    # line rows still carry clearly more horizontal ink than lyrics/noise.
    min_dark = max(80, int(W * 0.06))
    return int((row_sums >= min_dark).sum())


def _recover_missing_staff_systems(
    binary: np.ndarray,
    systems: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Insert likely staff systems skipped inside unusually large vertical gaps."""
    if len(systems) < 3:
        return systems

    systems = sorted(systems)
    top_gaps = [systems[i + 1][0] - systems[i][0] for i in range(len(systems) - 1)]
    staff_heights = [bottom - top for top, bottom in systems if bottom > top]
    if not top_gaps or not staff_heights:
        return systems

    normal_gap = int(np.median(top_gaps))
    staff_h = max(12, int(np.median(staff_heights)))
    if normal_gap <= 0:
        return systems

    recovered: list[tuple[int, int]] = []
    for idx, system in enumerate(systems[:-1]):
        recovered.append(system)
        cur_top = system[0]
        next_top = systems[idx + 1][0]
        gap = next_top - cur_top
        if gap <= int(normal_gap * 1.55):
            continue

        candidate_top = cur_top + normal_gap
        while next_top - candidate_top > int(normal_gap * 0.65):
            window_top = candidate_top - max(10, staff_h // 2)
            window_bottom = candidate_top + staff_h + max(10, staff_h // 2)
            score = _staff_fragment_score(binary, window_top, window_bottom)
            if score >= 5:
                recovered.append((candidate_top, candidate_top + staff_h))
            candidate_top += normal_gap
    recovered.append(systems[-1])

    recovered = sorted(set(recovered))
    deduped: list[tuple[int, int]] = []
    for system in recovered:
        if deduped and abs(system[0] - deduped[-1][0]) < max(10, staff_h // 2):
            prev = deduped[-1]
            deduped[-1] = (
                min(prev[0], system[0]),
                max(prev[1], system[1]),
            )
        else:
            deduped.append(system)
    return deduped

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
        if H < 10 or W < 10:
            return []

        # --- Binarise (Otsu) ---
        _, binary = cv2.threshold(gray, 0, 255,
                                  cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # --- Pass 1: row-projection — rows where ≥70% of pixels are dark ---
        # Staff lines span the full page width; even when notes break continuity
        # the total dark-pixel count per row stays high.  This is immune to the
        # morphological-open failure mode where dense notation fragments lines
        # into sub-threshold runs.
        # Consecutive hot rows (thick lines or 2-px aliasing) are collapsed to
        # a single peak (the row with the highest dark-pixel count) so that
        # each staff line contributes exactly one Y value to the candidate list.
        dark_threshold = int(W * 0.70)
        row_sums = (binary > 0).sum(axis=1)   # shape (H,)
        hot_rows: list[int] = [int(y) for y in range(H) if row_sums[y] >= dark_threshold]

        # Collapse runs of consecutive hot rows → single peak per run.
        proj_ys: list[int] = []
        if hot_rows:
            run: list[int] = [hot_rows[0]]
            for y in hot_rows[1:]:
                if y == run[-1] + 1:
                    run.append(y)
                else:
                    proj_ys.append(max(run, key=lambda r: row_sums[r]))
                    run = [y]
            proj_ys.append(max(run, key=lambda r: row_sums[r]))

        # --- Pass 2: morphological open — catches sparse/faint staves that
        # row-projection misses because overall pixel count is lower than 50%.
        kw = max(30, int(W * 0.20))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, 1))
        h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        num_labels, _, stats, _ = cv2.connectedComponentsWithStats(
            h_lines, connectivity=8
        )
        min_w = int(W * 0.20)
        max_h = 8
        morph_ys: list[int] = []
        for i in range(1, num_labels):
            comp_w = stats[i, cv2.CC_STAT_WIDTH]
            comp_h = stats[i, cv2.CC_STAT_HEIGHT]
            comp_top = stats[i, cv2.CC_STAT_TOP]
            if comp_w >= min_w and comp_h <= max_h:
                morph_ys.append(comp_top + comp_h // 2)

        # Merge both candidate sets; dedup below handles overlap.
        line_ys: list[int] = proj_ys + morph_ys

        if not line_ys:
            return []

        # Deduplicate y-values that land on the same pixel (e.g. two thin
        # connected components sharing the same centroid row).
        line_ys = sorted(set(line_ys))

        # --- Cluster consecutive y-values into staff groups ---
        # Gap threshold: 28px or ~1.5% of image height, whichever is larger.
        # Raised from 20 → 28 to bridge wider staff-line spacing (~22px) that
        # occurs in denser staves where the row-projection peaks land further
        # apart than in sparse staves.  Smallest inter-system gap is ~126px,
        # so 28px is safe.
        gap_threshold = max(28, int(H * 0.015))
        clusters: list[list[int]] = []
        current: list[int] = [line_ys[0]]

        for y in line_ys[1:]:
            if y - current[-1] <= gap_threshold:
                current.append(y)
            else:
                clusters.append(current)
                current = [y]
        clusters.append(current)

        # --- Keep clusters that look like a staff (2–12 lines) ---
        # Upper limit raised from 6 → 12: combining row-projection and
        # morphological-open candidates can yield up to ~10 entries per staff
        # (5 lines × up to 2 detection sources each, with slight Y offsets).
        # Minimum stays at 2 for JPEG-compressed scans with few detectable lines.
        systems: list[tuple[int, int]] = []
        for cluster in clusters:
            if 2 <= len(cluster) <= 12:
                systems.append((cluster[0], cluster[-1]))

        systems = _recover_missing_staff_systems(binary, systems)
        return systems

    except Exception:
        logger.warning("Staff detection failed; returning empty systems", exc_info=True)
        return []


def find_chord_x_start(band_crop: np.ndarray) -> int:
    """Return x-pixel offset where chord content begins (after bar numbers/segno).

    Scans the leftmost ``_CHORD_X_MARGIN_RATIO`` fraction of the band for
    content (bar numbers, segno).  If found, skips over it and the following
    gap, returning the x-column where chord symbols resume.

    Returns 0 if no leading margin content is detected (safe default: keep
    full-width scan).
    """
    H, W = band_crop.shape[:2]
    margin = int(W * _CHORD_X_MARGIN_RATIO)
    if margin < 10:
        return 0

    gray = cv2.cvtColor(band_crop, cv2.COLOR_RGB2GRAY) if band_crop.ndim == 3 else band_crop
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    col_proj = (binary > 0).sum(axis=0)
    noise_floor = max(2, int(H * 0.03))

    # Rightmost content column within left margin
    margin_cols = [x for x in range(margin) if col_proj[x] > noise_floor]
    if not margin_cols:
        return 0  # no bar number / segno in margin

    right_edge = max(margin_cols) + 1

    # Guard: if margin content extends past the narrow zone it is likely a
    # tempo/clef marking on the first staff row, not a bar number.  Do not
    # crop — returning 0 keeps the full-width scan for that row.
    narrow_margin = int(W * _NARROW_MARGIN_RATIO)
    if right_edge > narrow_margin:
        return 0

    # Skip gap after margin content; find where chords resume
    x = right_edge
    while x < W and col_proj[x] <= noise_floor:
        x += 1

    # Only crop if there is a meaningful gap (avoids splitting continuous content)
    return x if x >= right_edge + _GAP_MIN_COLS else 0


def build_chord_bands(img, systems: list[tuple[int, int]]) -> list[dict]:
    """Build chord-band crop dicts for each staff system.

    For each system the chord band is the inter-system gap between the previous
    system's bottom line and the current system's top line.  This follows the
    standard OMR approach (arXiv:1908.03608): the band is bounded above by the
    previous system's bottom (preventing overlap with its notes/lyrics) and
    below by a small pad below the current staff's top line.

    Parameters
    ----------
    img : PIL.Image.Image or numpy.ndarray (RGB)
    systems : list of (staff_top_y, staff_bottom_y)

    Returns
    -------
    list of dicts (sorted by y0, overlapping bands merged):
        crop         : np.ndarray  RGB uint8 (h, W, 3)
        x0           : int  left-margin crop offset (bar number / segno skip)
        y0           : int  band top in original coords
        w            : int  crop width (image width minus x0)
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

    for i, (top, bottom) in enumerate(systems):
        if bottom <= top:
            continue

        staff_h = bottom - top
        line_spacing = max(6, staff_h / 4)  # 5 lines → 4 gaps

        # Allow up to 3 × line_spacing above the staff; floor at 55 px for
        # small staves.  Raised from 40 to capture volta bracket chords
        # (1st/2nd/3rd endings) whose bracket line sits ~15 px above the
        # chord text.  Still bounded by prev_bottom so no system overlap.
        max_above = max(55, min(80, int(line_spacing * 3.0)))
        pad_below = max(4,  min(8,  int(line_spacing * 0.30)))

        # Inter-system boundary: the band must not extend above the previous
        # system's bottom line (which would capture its notes or lyrics).
        # For the first system the boundary is the top of the image (0).
        prev_bottom = systems[i - 1][1] if i > 0 else 0

        band_bottom = min(H, top + pad_below)
        band_top    = max(prev_bottom, top - max_above)

        if band_bottom <= band_top:
            continue

        full_crop = arr[band_top:band_bottom, :, :]
        x0 = find_chord_x_start(full_crop)
        raw_crop = arr[band_top:band_bottom, x0:, :]
        crop = _enhance_band_crop(raw_crop) if _ENHANCE_BANDS else raw_crop
        bands.append({
            "crop":         crop,
            "x0":           x0,
            "y0":           band_top,
            "w":            W - x0,
            "h":            band_bottom - band_top,
            "staff_top":    top,
            "staff_bottom": bottom,
            "line_spacing": line_spacing,
            "pad_below":    pad_below,
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
            full_merged = arr[new_y0:new_end, :, :]
            x0 = find_chord_x_start(full_merged)
            merged_raw = arr[new_y0:new_end, x0:, :]
            merged[-1] = {
                "crop":         _enhance_band_crop(merged_raw) if _ENHANCE_BANDS else merged_raw,
                "x0":           x0,
                "y0":           new_y0,
                "w":            W - x0,
                "h":            new_end - new_y0,
                "staff_top":    prev["staff_top"],
                "staff_bottom": band["staff_bottom"],
                "line_spacing": prev["line_spacing"],
                "pad_below":    prev["pad_below"],
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
            "x0":     region.get("x0", 0),
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
