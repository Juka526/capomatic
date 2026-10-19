"""Research-only, separately bounded continuation segments. No note glyph rendering."""

import math

import numpy as np
from PIL import Image

from scripts.research.gt11_complete_measure import require
from scripts.research.gt13a2_provisional import curve_mask, translated_curve


def require_owner_confirmation(status):
    """OMR support, silence and uncertainty never authorize a real continuation."""
    require(status == 'OWNER_CONFIRMED', 'Destination requires explicit owner confirmation')


def render_segments(size, outgoing, incoming, unrelated_ink=None):
    """Low-level geometry for synthetic tests; real-source callers must apply owner gate."""
    specs = [outgoing, incoming]
    require([s['role'] for s in specs] == ['OUTGOING', 'INCOMING'], 'Wrong segment roles')
    require(specs[0]['system_bbox'][3] < specs[1]['system_bbox'][1], 'Systems must be separated')
    masks = {}
    reports = []
    for spec in specs:
        box = spec['system_bbox']
        require(
            len(box) == 4
            and all(math.isfinite(v) for v in box)
            and 0 <= box[0] < box[2] <= size[0]
            and 0 <= box[1] < box[3] <= size[1],
            'Invalid system viewport',
        )
        curve = translated_curve(spec['source_curve'], spec['dy'], spec['dy'])
        require(
            all(box[0] + 1 <= x < box[2] - 1 and box[1] + 1 <= y < box[3] - 1 for x, y in curve),
            'Curve/stroke clipping',
        )
        anchor = spec['head_anchor']
        offset = spec['attachment_offset']
        require(
            len(anchor) == 2
            and len(offset) == 2
            and all(math.isfinite(v) for v in [*anchor, *offset]),
            'Invalid attachment geometry',
        )
        require(offset[1] > 0, 'Only source-supported below ties are implemented')
        index = 0 if spec['role'] == 'OUTGOING' else -1
        desired = [anchor[i] + offset[i] for i in (0, 1)]
        residual = [curve[index][i] - desired[i] for i in (0, 1)]
        require(max(map(abs, residual)) <= 0.5, 'Curve attachment mismatch')
        require(
            (curve[1][1] >= curve[0][1] and curve[2][1] >= curve[-1][1]),
            'Unsupported tie direction',
        )
        mask = curve_mask(size, curve)
        actual = mask.getbbox()
        require(
            actual
            and actual[0] >= box[0]
            and actual[1] >= box[1]
            and actual[2] <= box[2]
            and actual[3] <= box[3],
            'Raster clipping',
        )
        if unrelated_ink is not None:
            require(
                unrelated_ink.size == size and unrelated_ink.mode == 'L',
                'Obstacle alignment mismatch',
            )
            require(
                not np.any((np.asarray(mask) > 0) & (np.asarray(unrelated_ink) > 0)),
                'Unexpected ink collision',
            )
        masks[spec['role']] = mask
        reports.append(
            {
                'role': spec['role'],
                'curve': curve,
                'attachment_residual': residual,
                'bbox': actual,
                'unrelated_ink_contacts': 0,
            }
        )
    gap = Image.fromarray(np.maximum.reduce([np.asarray(m) for m in masks.values()]))
    require(
        not gap.crop(
            (0, int(outgoing['system_bbox'][3]), size[0], int(incoming['system_bbox'][1]))
        ).getbbox(),
        'Inter-system bridge forbidden',
    )
    return masks, {
        'segments': reports,
        'gap_ink_pixels': 0,
        'scope': 'Declared-anchor geometry only; no independent optical or whole-note glyph-anchor validation',
    }
