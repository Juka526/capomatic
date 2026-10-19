"""Synthetic mixed-beam contracts; no score/OMR execution dependency."""

import copy
import numpy as np
import pytest
from PIL import ImageFont
from fontTools.ttLib import TTFont
from scripts.research.gt13a2_provisional import (
    mixed_layout,
    translated_curve,
    curve_mask,
    EIGHTH_REST,
)
from scripts.research.gt05_raster_anchor import glyph
from scripts.research.gt11_complete_measure import FONT


def fixture(hooks=False):
    nodes = {
        str(i): {'x': 20 + i * 40, 'y': 120 + i * 3, 'event': {'beams': [{'number': 1, 'type': t}]}}
        for i, t in enumerate(['start', 'continue', 'stop'])
    }

    def beam(ident, kind, line, members):
        return {'id': ident, 'kind': kind, 'geometry': {'line': line, 'thickness': 8}}, [
            {'kind': 'beam-stem', 'source': ident, 'target': str(i)} for i in members
        ]

    p, rs = beam('primary', 'beam', [[20, 50], [100, 56]], [0, 1, 2])
    symbols = {'primary': p}
    if hooks:
        for i, d in [(0, 'right'), (2, 'left')]:
            nodes[str(i)]['event']['beams'].append({'number': 2, 'type': 'partial', 'direction': d})
            x = nodes[str(i)]['x']
            lo, hi = (x, x + 20) if i == 0 else (x - 20, x)
            b, r = beam(
                'hook' + str(i),
                'beam-hook',
                [[lo, 64 + (lo - 20) * 0.075], [hi, 64 + (hi - 20) * 0.075]],
                [i],
            )
            symbols[b['id']] = b
            rs += r
    else:
        for i, t in [(1, 'start'), (2, 'stop')]:
            nodes[str(i)]['event']['beams'].append({'number': 2, 'type': t})
        b, r = beam('secondary', 'beam', [[60, 67], [100, 70]], [1, 2])
        symbols[b['id']] = b
        rs += r
    return nodes, symbols, rs


@pytest.mark.parametrize('hooks', [False, True])
def test_mixed_layout_duration_membership_stems_and_source_slope(hooks):
    args = fixture(hooks)
    before = copy.deepcopy(args)
    rows, tips = mixed_layout(*args, 18)
    assert len(rows) == (3 if hooks else 2)
    assert set(tips) == set(args[0])
    assert all(args[0][s]['y'] - y >= 63 for s, y in tips.items())
    assert rows[0]['thickness'] == 8
    assert args == before
    assert (rows, tips) == mixed_layout(*args, 18)


def test_missing_beam_relation_rejects_not_simplifies():
    n, s, r = fixture()
    r.pop()
    with pytest.raises(ValueError):
        mixed_layout(n, s, r, 18)


def test_wrong_hook_direction_rejected():
    n, s, r = fixture(True)
    n['0']['event']['beams'][1]['direction'] = None
    with pytest.raises(ValueError, match='direction'):
        mixed_layout(n, s, r, 18)


def test_remote_group_member_blocks():
    n, s, r = fixture()
    r.append({'kind': 'beam-stem', 'source': 'primary', 'target': 'remote'})
    with pytest.raises(ValueError, match='Incomplete'):
        mixed_layout(n, s, r, 18)


def test_curve_uses_semantic_endpoint_displacements_without_changing_x():
    c = [[10, 20], [20, 30], [30, 30], [40, 20]]
    shifted = translated_curve(c, 9, 18)
    assert shifted[0] == [10, 29] and shifted[-1] == [40, 38]
    assert [p[0] for p in shifted] == [10, 20, 30, 40]
    assert curve_mask((100, 100), shifted).tobytes() == curve_mask((100, 100), shifted).tobytes()
    with pytest.raises(ValueError):
        translated_curve(c, float('nan'), 9)


def test_eighth_rest_is_real_glyph_and_deterministic():
    if not FONT.exists():
        pytest.skip('Pinned research font not available')
    tt = TTFont(FONT)
    g = tt['glyf'][tt.getBestCmap()[ord(EIGHTH_REST)]]
    units = (g.xMin, g.yMin, g.xMax, g.yMax)
    font = ImageFont.truetype(str(FONT), 94)
    a, info = glyph(
        (200, 200), font, EIGHTH_REST, (100.25, 100.75), units, 94 / tt['head'].unitsPerEm
    )
    b, _ = glyph((200, 200), font, EIGHTH_REST, (100.25, 100.75), units, 94 / tt['head'].unitsPerEm)
    assert np.count_nonzero(np.asarray(a)) > 0 and a.tobytes() == b.tobytes()
    assert max(map(abs, info['anchor_residual'])) <= 0.5


def test_annotation_clearance_measures_distance_even_without_overlap():
    from PIL import Image
    from scripts.research.gt13a2_provisional import annotation_metrics, ink_distance

    music = Image.new('L', (50, 50))
    music.putpixel((20, 20), 1)
    annotation = Image.new('L', (50, 50))
    annotation.putpixel((17, 16), 1)
    distances = ink_distance(music)
    row = annotation_metrics(annotation, music, distances, (0, 18, 50, 30))
    assert row['ink_contacts'] == 0 and row['notation_region_pixels'] == 0
    assert row['min_pixel_center_distance_px'] == 5
    assert row['pixel_square_clearance_lower_bound_px'] == pytest.approx(5 - np.sqrt(2))
    annotation.putpixel((20, 20), 1)
    row = annotation_metrics(annotation, music, distances, (0, 18, 50, 30))
    assert row['ink_contacts'] == 1 and row['notation_region_pixels'] == 1
    assert row['min_pixel_center_distance_px'] == 0


def test_final_panel_diagnostics_are_outside_native_unchanged_viewport():
    from PIL import Image, ImageDraw
    from scripts.research.gt13a2_provisional import panel

    image = Image.new('RGB', (2300, 410), 'white')
    music = Image.new('L', image.size)
    ImageDraw.Draw(music).rectangle((1200, 200, 1220, 220), fill=255)
    image.paste((25, 65, 150), (0, 0, *image.size), music)
    before = image.tobytes()
    result, report, mask = panel(image, 'synthetic A', target='A', music=music, score_ink=music)
    viewport = report['source_viewport']
    assert result.crop(viewport).tobytes() == before
    assert mask.crop(viewport).getbbox() is None
    assert all(r['ink_contacts'] == r['notation_region_pixels'] == 0 for r in report['annotations'])
    assert report['minimum_musical_ink_clearance_px'] > 0
    again, other, _ = panel(image, 'synthetic A', target='A', music=music, score_ink=music)
    assert again.tobytes() == result.tobytes() and other == report


def test_annotation_coordinate_mismatch_is_rejected():
    from PIL import Image
    from scripts.research.gt13a2_provisional import annotation_metrics, ink_distance

    with pytest.raises(ValueError, match='alignment'):
        annotation_metrics(
            Image.new('L', (5, 5)), Image.new('L', (6, 5)), np.zeros((5, 6)), (0, 0, 5, 5)
        )
