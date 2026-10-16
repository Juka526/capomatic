"""Stage 1 of the reliability gate: is this page good enough to attempt full-score OMR?

Adapted from the V3 completion package (``omr_v3_final/quality.py``) with one
substantive change: staff spacing is measured with the run-length method OMR
engines use (most common white run + black run between staff lines) on the
image *as uploaded*, instead of a projection peak on a downscaled preview.
Thresholds are calibrated on the development sheets only (see
``docs/pr-assets/omr-v3/REPORT.md``); they are a guardrail, not an accuracy
estimate.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum

import numpy as np
from PIL import Image, ImageOps


class ProcessingMode(str, Enum):
    FULL_SCORE = 'full_score'
    CHORD_ONLY = 'chord_only'


@dataclass(frozen=True)
class QualityMetrics:
    width: int
    height: int
    interline_px: float | None     # staff line spacing (line + space) in the analysed raster
    effective_interline_px: float | None  # the same at the source's native resolution
    line_thickness_px: float | None
    contrast: float                # grey-level standard deviation
    sharpness: float               # Laplacian variance at a normalised scale
    dark_ratio: float              # share of ink pixels


@dataclass(frozen=True)
class QualityDecision:
    mode: ProcessingMode
    score: float
    reasons: tuple[str, ...]
    metrics: QualityMetrics

    def to_dict(self) -> dict:
        return {'mode': self.mode.value, 'score': self.score, 'reasons': list(self.reasons),
                'metrics': asdict(self.metrics)}


# Calibrated thresholds (development set only); env overrides exist for tuning.
MIN_INTERLINE_PX = 11.0        # below this Audiveris misreads ledger/rhythm badly (745 px JPEG: ~6 px)
MIN_SHARPNESS = 40.0
MIN_CONTRAST = 25.0


def _gray(image: Image.Image) -> np.ndarray:
    return np.asarray(ImageOps.grayscale(image), dtype=np.float32)


def _runs(column: np.ndarray) -> tuple[list[int], list[int]]:
    """Lengths of black and white runs in a binary column (True = ink)."""
    if column.size == 0:
        return [], []
    change = np.flatnonzero(np.diff(column.astype(np.int8))) + 1
    bounds = np.concatenate(([0], change, [column.size]))
    black, white = [], []
    for a, b in zip(bounds[:-1], bounds[1:]):
        (black if column[a] else white).append(int(b - a))
    return black, white


def estimate_interline(gray: np.ndarray) -> tuple[float | None, float | None]:
    """Most common (black run, white run) pair between staff lines, in pixels."""
    h, w = gray.shape
    if h < 50 or w < 50:
        return None, None
    threshold = min(200.0, float(np.percentile(gray, 50)) - 40.0)
    ink = gray < threshold
    black_hist: dict[int, int] = {}
    white_hist: dict[int, int] = {}
    for x in range(w // 10, w - w // 10, max(1, w // 300)):
        black, white = _runs(ink[:, x])
        for r in black:
            if r <= h // 50:
                black_hist[r] = black_hist.get(r, 0) + 1
        for r in white:
            if 2 <= r <= h // 15:
                white_hist[r] = white_hist.get(r, 0) + 1
    if not black_hist or not white_hist:
        return None, None
    line = max(black_hist, key=black_hist.get)
    space = max(white_hist, key=white_hist.get)
    if white_hist[space] < 20:
        return None, None
    return float(line + space), float(line)


def _sharpness(gray: np.ndarray, interline: float | None) -> float:
    """Laplacian variance after scaling the page to ~20 px staff spacing.

    Normalising by staff spacing keeps a sharp 150 dpi scan and a sharp 300 dpi
    export comparable; blur is what this signal is meant to catch.
    """
    im = Image.fromarray(gray.astype('uint8'))
    if interline:
        f = 20.0 / interline
        im = im.resize((max(3, int(im.width * f)), max(3, int(im.height * f))), Image.BILINEAR)
    a = np.asarray(im, dtype=np.float32)
    if min(a.shape) < 3:
        return 0.0
    c = a[1:-1, 1:-1]
    lap = -4 * c + a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:]
    return float(np.var(lap))


def assess(image: Image.Image, native_scale: float = 1.0) -> QualityDecision:
    """Measure the page and decide whether a full-score attempt is reasonable.

    *native_scale* < 1 when *image* is an upsampled raster of a lower-resolution
    source (a 150 dpi scan inside a PDF rasterised at 300 dpi gives 0.5): the
    detail OMR can recover is that of the source, not of the raster.
    """
    import os

    min_interline = float(os.environ.get('CAPOMATIC_OMR_MIN_INTERLINE_PX', MIN_INTERLINE_PX))
    gray = _gray(image)
    interline, line = estimate_interline(gray)
    effective = None if interline is None else interline * min(1.0, native_scale)
    contrast = float(np.std(gray))
    sharp = _sharpness(gray, interline)
    dark = float(np.mean(gray < 128))
    metrics = QualityMetrics(image.width, image.height,
                             None if interline is None else round(interline, 1),
                             None if effective is None else round(effective, 1),
                             None if line is None else round(line, 1),
                             round(contrast, 1), round(sharp, 1), round(dark, 4))

    reasons: list[str] = []
    if effective is None:
        reasons.append('no_staff_lines_found')
    elif effective < min_interline:
        reasons.append('staff_spacing_too_small')
    if sharp < MIN_SHARPNESS:
        reasons.append('image_too_blurry')
    if contrast < MIN_CONTRAST:
        reasons.append('contrast_too_low')

    # A soft score for the report (0..1); the decision itself uses the hard rules above.
    def clamp(x: float) -> float:
        return max(0.0, min(1.0, x))
    staff_s = 0.0 if effective is None else clamp((effective - 6) / (20 - 6))
    sharp_s = clamp((sharp - 20) / 300)
    contrast_s = clamp((contrast - 15) / 60)
    score = round(0.5 * staff_s + 0.3 * sharp_s + 0.2 * contrast_s, 3)

    mode = ProcessingMode.CHORD_ONLY if reasons else ProcessingMode.FULL_SCORE
    return QualityDecision(mode, score, tuple(reasons), metrics)
