"""Isolated source-backed score header. No source pixel editing or production routes."""

import math

import numpy as np
from fontTools.ttLib import TTFont
from music21 import pitch
from PIL import Image, ImageDraw, ImageFont

from scripts.research.gt05_raster_anchor import glyph
from scripts.research.gt11_complete_measure import require
from scripts.research.paired_ground_truth_01 import line_y

TREBLE = chr(0x1D11E)
SHARP = chr(0x266F)
CLEF_DESIGN_ANCHOR = (331, 160)


def font_units(tt, char):
    require(ord(char) in tt.getBestCmap(), 'Font lacks required header glyph')
    g = tt['glyf'][tt.getBestCmap()[ord(char)]]
    return (g.xMin, g.yMin, g.xMax, g.yMax)


def semantic_glyph(size, font, char, xy, units, scale, design_anchor):
    """Translate a fixed canonical bitmap by its declared font-specific semantic anchor."""
    tile, info = glyph(
        (6 * font.size, 6 * font.size), font, char, (3 * font.size, 3 * font.size), units, scale
    )
    canonical_anchor = [
        info['baseline'][0] + design_anchor[0] * scale,
        info['baseline'][1] - design_anchor[1] * scale,
    ]
    center = [info['raster_placement_anchor'][i] + xy[i] - canonical_anchor[i] for i in (0, 1)]
    mask, placed = glyph(size, font, char, center, units, scale)
    actual = [
        placed['baseline'][0] + design_anchor[0] * scale,
        placed['baseline'][1] - design_anchor[1] * scale,
    ]
    residual = [actual[i] - xy[i] for i in (0, 1)]
    require(max(map(abs, residual)) <= 0.5, 'Header semantic anchor exceeds half-pixel limit')
    placed.update(
        design_anchor=list(design_anchor),
        requested_semantic_anchor=list(xy),
        actual_semantic_anchor=actual,
        semantic_anchor_residual=residual,
    )
    return mask, placed


def header(size, staff, target, font_path, *, x_shift=0):
    """Render treble / target key / opening repeat / 4/4 before the first event."""
    require(target in ('A', 'G'), 'Unsupported target key')
    inter = staff['interline']
    require(
        math.isfinite(inter) and inter > 0 and math.isfinite(x_shift), 'Invalid header geometry'
    )
    require(len(staff['lines']) == 5, 'Missing five staff polylines')
    tt = TTFont(font_path)
    upm = tt['head'].unitsPerEm
    parts = {}
    metrics = {}

    def sized(char, height):
        u = font_units(tt, char)
        f = ImageFont.truetype(str(font_path), round(height * upm / (u[3] - u[1])))
        return f, u, f.size / upm

    f, u, scale = sized(TREBLE, 7 * inter)
    xy = (200 + x_shift, line_y(staff['lines'][3], 200 + x_shift))
    parts['clef'], metrics['clef'] = semantic_glyph(
        size, f, TREBLE, xy, u, scale, CLEF_DESIGN_ANCHOR
    )
    sharp_font, sharp_units, sharp_scale = sized(SHARP, 2.6 * inter)
    tile, _ = glyph((600, 600), sharp_font, SHARP, (300, 300), sharp_units, sharp_scale)
    width = tile.getbbox()[2] - tile.getbbox()[0]
    sharp_rows = []
    names = ['F5', 'C5', 'G5'] if target == 'A' else ['F5']
    for i, name in enumerate(names):
        x = 236 + x_shift + (width - 1) / 2 + i * 1.1 * inter
        p = pitch.Pitch(name)
        pos = 35 - p.diatonicNoteNum
        y = line_y(staff['lines'][2], x) + pos * inter / 2
        mask, info = glyph(size, sharp_font, SHARP, (x, y), sharp_units, sharp_scale)
        require(max(map(abs, info['anchor_residual'])) <= 0.5, 'Sharp raster anchor gate failed')
        parts[f'sharp-{i}'] = mask
        sharp_rows.append({'pitch': name, 'staff_position': pos, **info})
    key_right = max(p.getbbox()[2] for n, p in parts.items() if n.startswith('sharp'))
    left = max(285 + x_shift, key_right + 0.5 * inter)
    # Group dimensions are original repeat Inter geometry, not a global score transform.
    thick = Image.new('L', size)
    thin = Image.new('L', size)
    top = line_y(staff['lines'][0], left)
    bottom = line_y(staff['lines'][-1], left)
    ImageDraw.Draw(thick).rectangle(
        (round(left), round(top), round(left) + 9, round(bottom)), fill=255
    )
    ImageDraw.Draw(thin).rectangle(
        (round(left) + 16, round(top), round(left) + 18, round(bottom)), fill=255
    )
    parts.update(repeat_thick=thick, repeat_thin=thin)
    dots = []
    for i, sign in enumerate((-1, 1)):
        x = left + 29.5
        y = line_y(staff['lines'][2], x) + sign * inter / 2
        mask = Image.new('L', size)
        radius = 0.18 * inter
        ImageDraw.Draw(mask).ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)
        parts[f'repeat-dot-{i}'] = mask
        dots.append({'center': [x, y], 'radius': radius, 'bbox': mask.getbbox()})
    digit_font, digit_units, digit_scale = sized('4', 1.8 * inter)
    tile, _ = glyph((600, 600), digit_font, '4', (300, 300), digit_units, digit_scale)
    digit_width = tile.getbbox()[2] - tile.getbbox()[0]
    repeat_right = max(parts[f'repeat-dot-{i}'].getbbox()[2] for i in (0, 1))
    time_x = max(338 + x_shift, repeat_right + 0.5 * inter + (digit_width - 1) / 2)
    times = []
    for i, line_index in enumerate((1, 3)):
        y = line_y(staff['lines'][line_index], time_x)
        mask, info = glyph(size, digit_font, '4', (time_x, y), digit_units, digit_scale)
        parts[f'time-{i}'] = mask
        times.append(info)
    intersections = []
    for i, (a, aa) in enumerate(parts.items()):
        for b, bb in list(parts.items())[i + 1 :]:
            overlap = int(np.count_nonzero((np.asarray(aa) > 0) & (np.asarray(bb) > 0)))
            if overlap:
                intersections.append({'a': a, 'b': b, 'pixels': overlap})
    require(not intersections, 'Header glyph collision')
    require(
        all(
            p.getbbox() is not None
            and p.getbbox()[0] > 0
            and p.getbbox()[1] > 0
            and p.getbbox()[2] < size[0]
            and p.getbbox()[3] < size[1]
            for p in parts.values()
        ),
        'Clipped header',
    )
    metrics.update(
        key={'name': target, 'fifths': len(names), 'sharps': sharp_rows},
        time={'ratio': '4/4', 'digits': times},
        forward_repeat={
            'direction': 'start',
            'thick_left': left,
            'thin_left': left + 16,
            'dots': dots,
            'source_left': 285 + x_shift,
            'reflow_dx': left - (285 + x_shift),
        },
        actual_header_component_intersections=intersections,
        glyph_anchor_contract='Font-specific lower-bowl design anchor; not SMuFL/independent optical validation',
    )
    return parts, metrics
