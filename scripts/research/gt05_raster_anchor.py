"""Research-only fixed-phase glyph registration; no pitch or source-image editing."""

import hashlib
import math

from PIL import Image, ImageDraw


def glyph(mask_size, font, char, xy, units, scale):
    """Place an unscaled canonical raster using its explicit pixel-index center."""
    if not all(math.isfinite(v) for v in (*xy, *units, scale)) or scale <= 0:
        raise ValueError('Invalid/nonfinite glyph geometry')
    size = font.size
    reference = (2 * size, 2 * size)
    tile = Image.new('L', (6 * size, 6 * size))
    ImageDraw.Draw(tile).text(reference, char, font=font, fill=255, anchor='ls', stroke_width=0)
    box = tile.getbbox()
    if box is None or box[0] <= 0 or box[1] <= 0 or box[2] >= tile.width or box[3] >= tile.height:
        raise ValueError('Missing or clipped canonical glyph')
    bitmap = tile.crop(box)
    anchor = ((bitmap.width - 1) / 2, (bitmap.height - 1) / 2)
    destination = tuple(math.floor(t - a + 0.5) for t, a in zip(xy, anchor))
    if (
        destination[0] < 0
        or destination[1] < 0
        or destination[0] + bitmap.width > mask_size[0]
        or destination[1] + bitmap.height > mask_size[1]
    ):
        raise ValueError('Clipped glyph placement')
    mask = Image.new('L', mask_size)
    mask.paste(bitmap, destination)
    center = [d + a for d, a in zip(destination, anchor)]
    baseline = [destination[0] + reference[0] - box[0], destination[1] + reference[1] - box[1]]
    outline_center = [
        baseline[0] + (units[0] + units[2]) * scale / 2,
        baseline[1] - (units[1] + units[3]) * scale / 2,
    ]
    return mask, {
        'requested_anchor': list(xy),
        'raster_placement_anchor': center,
        'font_outline_anchor': outline_center,
        'baseline': baseline,
        'canonical_baseline_phase': [0, 0],
        'canonical_alpha_sha256': hashlib.sha256(bitmap.tobytes()).hexdigest(),
        'rendered_bounds': [
            destination[0],
            destination[1],
            destination[0] + bitmap.width,
            destination[1] + bitmap.height,
        ],
        'raster_ink_bbox_center': center,
        'anchor_residual': [c - t for c, t in zip(center, xy)],
        'placement_method': 'fixed-phase raster bbox center; nearest integer translation; no resizing/alpha threshold',
    }
