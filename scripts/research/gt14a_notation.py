"""Research-only whole rest and first-ending/backward-repeat components."""

import math
import xml.etree.ElementTree as ET

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

from scripts.research.gt04_visual import HEAD
from scripts.research.gt11_complete_measure import FONT, require
from scripts.research.gt13a4_header import semantic_glyph, font_units
from scripts.research.gt12_render_context import text_mask
from scripts.research.paired_ground_truth_01 import line_y

WHOLE_REST = chr(0x1D13B)


def whole_rest(size, staff, x):
    inter = staff['interline']
    require(math.isfinite(inter) and inter > 0 and math.isfinite(x), 'Invalid rest geometry')
    tt = TTFont(FONT)
    upm = tt['head'].unitsPerEm
    black = font_units(tt, HEAD)
    font = ImageFont.truetype(str(FONT), round(1.25 * inter * upm / (black[2] - black[0])))
    y = line_y(staff['lines'][1], x)
    mask, info = semantic_glyph(
        size, font, WHOLE_REST, (x, y), font_units(tt, WHOLE_REST), font.size / upm, (191, 560)
    )
    info.update(symbol='WHOLE_REST', duration='4', staff_line_index=1, font_size=font.size)
    return mask, info


def ending_repeat(size, ending, bars, dots, numeral_xy):
    raw = ET.fromstring(ending['source_xml'])

    def point(path):
        p = raw.find(path)
        require(p is not None, 'Missing source bracket geometry')
        return [float(p.get('x')), float(p.get('y'))]

    left_top = point('left-leg/p1')
    left_bottom = point('left-leg/p2')
    right_top = point('right-leg/p1')
    right_bottom = point('right-leg/p2')
    top = point('line/p1')[1]
    require(
        all(math.isfinite(v) for p in [left_top, left_bottom, right_top, right_bottom] for v in p)
        and left_top[0] < right_top[0]
        and left_bottom[1] > top
        and right_bottom[1] > top,
        'Invalid bracket',
    )
    thin = next(b for b in bars if b['shape'] == 'THIN_BARLINE')
    thick = next(b for b in bars if b['shape'] == 'THICK_BARLINE')
    require(
        thin['geometry']['bbox'][2] < thick['geometry']['bbox'][0] and len(dots) == 2,
        'Not a backward repeat',
    )
    require(
        all(d['geometry']['bbox'][2] < thin['geometry']['bbox'][0] for d in dots),
        'Dots must be left of backward repeat',
    )
    parts = {}
    mask = Image.new('L', size)
    path = [left_bottom, [left_top[0], top], [right_top[0], top], right_bottom]
    ImageDraw.Draw(mask).line([tuple(p) for p in path], fill=255, width=2)
    parts['ending1-bracket'] = mask
    font = ImageFont.truetype(str(FONT), 40)
    parts['ending1-number'], number = text_mask(size, font, '1.', left_top=numeral_xy)
    for name, symbol in [('backward-thin', thin), ('backward-heavy', thick)]:
        mask = Image.new('L', size)
        b = symbol['geometry']['bbox']
        ImageDraw.Draw(mask).rectangle((b[0], b[1], b[2] - 1, b[3] - 1), fill=255)
        parts[name] = mask
    for i, dot in enumerate(sorted(dots, key=lambda d: d['geometry']['bbox'][1])):
        mask = Image.new('L', size)
        b = dot['geometry']['bbox']
        ImageDraw.Draw(mask).ellipse((b[0], b[1], b[2] - 1, b[3] - 1), fill=255)
        parts[f'backward-dot-{i}'] = mask
    for mask in parts.values():
        b = mask.getbbox()
        require(b and 0 < b[0] < b[2] < size[0] and 0 < b[1] < b[3] < size[1], 'Clipped notation')
    return parts, {
        'ending_number': '1',
        'repeat_direction': 'end',
        'bracket_source_id': ending['id'],
        'path': path,
        'number': number,
        'bar_ids': [thin['id'], thick['id']],
        'dot_ids': [d['id'] for d in dots],
        'number_and_bracket_are_distinct_components': True,
    }
