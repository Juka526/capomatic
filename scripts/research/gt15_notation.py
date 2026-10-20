"""Narrow research contracts for half heads/rests and explicit simple eighth beams."""

import math

import cv2
import numpy as np
from fontTools.ttLib import TTFont
from PIL import ImageFont

from scripts.research.gt04_visual import HEAD
from scripts.research.gt05_raster_anchor import glyph
from scripts.research.gt11_complete_measure import FONT, require
from scripts.research.gt13a4_header import font_units

VOID = chr(0x1D157)
HALF_REST = chr(0x1D13C)


def font_contract(interline):
    require(math.isfinite(interline) and interline > 0, 'Invalid interline')
    tt = TTFont(FONT)
    upm = tt['head'].unitsPerEm
    units = font_units(tt, HEAD)
    font = ImageFont.truetype(str(FONT), round(1.25 * interline * upm / (units[2] - units[0])))
    return tt, font, font.size / upm


def hole_pixels(mask):
    bbox = mask.getbbox()
    require(bbox is not None, 'Empty glyph')
    tile = np.asarray(mask.crop(bbox)) > 0
    _, _, stats, _ = cv2.connectedComponentsWithStats((~tile).astype('uint8'), 8)
    return int(
        sum(
            s[cv2.CC_STAT_AREA]
            for s in stats[1:]
            if s[0] > 0 and s[1] > 0 and s[0] + s[2] < tile.shape[1] and s[1] + s[3] < tile.shape[0]
        )
    )


def half_symbol(size, interline, xy, *, rest=False):
    tt, font, scale = font_contract(interline)
    char = HALF_REST if rest else VOID
    mask, info = glyph(size, font, char, xy, font_units(tt, char), scale)
    require(max(map(abs, info['anchor_residual'])) <= 0.5, 'Half-symbol raster anchor failed')
    info['glyph_codepoint'] = f'U+{ord(char):05X}'
    info['duration'] = '2'
    info['font_size'] = font.size
    if not rest:
        info['transparent_hole_pixels'] = hole_pixels(mask)
        require(info['transparent_hole_pixels'] > 0, 'Void head hole lost')
    return mask, info


def single_beam(nodes, beam, interline):
    """N=2/4 single-level source-connected groups; source membership checked by caller."""
    require(len(nodes) in (2, 4), 'Unsupported beam member count')
    require(math.isfinite(interline) and interline > 0, 'Invalid interline')
    ordered = sorted(nodes.items(), key=lambda p: p[1]['x'])
    types = [n['event']['beams'] for _, n in ordered]
    expect = ['start'] + ['continue'] * (len(nodes) - 2) + ['stop']
    require(
        all(
            n['event']['duration'] == '1/2' and n['event']['stem_direction'] == 'up'
            for _, n in ordered
        ),
        'Unsupported beam rhythm/direction',
    )
    require(
        all(
            len(v) == 1 and v[0]['number'] == 1 and v[0]['type'] == e for v, e in zip(types, expect)
        ),
        'Beam semantic linkage mismatch',
    )
    line = beam['geometry']['line']
    require(
        len(line) == 2
        and all(math.isfinite(v) for p in line for v in p)
        and line[1][0] > line[0][0],
        'Invalid source beam',
    )
    thickness = round(beam['geometry']['thickness'])
    require(0 < thickness < interline, 'Unsupported beam thickness')
    slope = (line[1][1] - line[0][1]) / (line[1][0] - line[0][0])
    x0, x1 = ordered[0][1]['x'], ordered[-1][1]['x']
    require(
        x1 > x0 and all(math.isfinite(n[k]) for _, n in ordered for k in ('x', 'y')),
        'Invalid stem geometry',
    )
    y0 = min(n['y'] - 3.5 * interline - slope * (n['x'] - x0) for _, n in ordered)
    tips = {s: y0 + slope * (n['x'] - x0) for s, n in ordered}
    return {
        'id': beam['id'],
        'members': [s for s, _ in ordered],
        'line': [[x0, y0], [x1, y0 + slope * (x1 - x0)]],
        'thickness': thickness,
        'source_slope': slope,
    }, tips
