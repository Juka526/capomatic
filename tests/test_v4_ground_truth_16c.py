"""Synthetic optical spacing, pixel-square geometry and supersampled beam controls."""

import math

import numpy as np
import pytest
from PIL import Image, ImageDraw

from scripts.research.gt13a2_provisional import ink_distance
from scripts.research.gt16c_optical_engraving import (
    Distances,
    beam_candidate,
    beam_metrics,
    compose,
    contact,
    layout,
    minimum_dy,
    piece,
)


def dot(x, y, size=(80, 80)):
    p = Image.new('L', size)
    p.putpixel((x, y), 255)
    return p


@pytest.mark.parametrize('dx,dy', [(0, 6), (6, 0), (3, 4), (1, 1), (0, 0)])
def test_exact_pixel_square_edge_distance_matches_independent_pair_formula(dx, dy):
    obstacle = dot(30, 30)
    text = piece('t', dot(30 + dx, 30 + dy), 1, 1, 'SYLLABLE')
    r = Distances(obstacle).measure([text])
    assert r['center_distance_px'] == math.hypot(dx, dy)
    assert r['pixel_square_edge_distance_px'] == math.hypot(max(dx - 1, 0), max(dy - 1, 0))


def test_edge_nearest_can_differ_from_center_nearest():
    p = dot(30, 23)
    p.putpixel((35, 25), 255)
    r = Distances(p).measure([piece('t', dot(30, 30), 1, 1, 'SYLLABLE')])
    assert r['center_distance_px'] == 7
    assert r['pixel_square_edge_distance_px'] == math.sqrt(32)


def test_minimal_displacement_is_exhaustive_and_preserves_both_rows_and_alpha():
    fixed = dot(30, 30)
    a = piece('a', dot(30, 32), 1, 1, 'SYLLABLE')
    b = piece('b', dot(30, 40), 1, 1, 'MARK')
    d = minimum_dy([a, b], ink_distance(fixed), 60, 6)
    assert d['selected_dy'] == 4 and d['feasible_dy'] == list(range(4, 20))
    (moved, unchanged), r = layout([a, b], fixed, [(0, 80)], 6)
    assert [p.box[1] for p in moved] == [36, 44]
    assert [p.box[0] for p in moved] == [30, 30]
    assert all(a.tile.tobytes() == b.tile.tobytes() for a, b in zip([a, b], moved))
    assert unchanged.tobytes() == fixed.tobytes() and r['lost_alpha_pixels'] == 0


def test_infeasible_original_allocation_is_not_forced_and_taller_candidate_is_explicit():
    fixed = dot(30, 30)
    p = piece('a', dot(30, 32), 1, 1, 'SYLLABLE')
    assert minimum_dy([p], ink_distance(fixed), 34, 6)['selected_dy'] is None
    p2 = piece('b', dot(30, 60), 2, 2, 'SYLLABLE')
    result, r = layout([p, p2], fixed, [(0, 34), (34, 80)], 6)
    assert result is None and not r['feasible']
    (moved, larger), r = layout([p, p2], fixed, [(0, 34), (34, 80)], 6, extra=12)
    assert larger.height == 104 and moved[0].box[1] == 36 and r['extra'] == 12


@pytest.mark.parametrize('slope', [-0.2, 0, 0.2])
@pytest.mark.parametrize('phase', [0, 0.25, 0.5, 0.75])
def test_supersampled_beams_preserve_endpoints_stem_contact_connectivity_and_finite_support(
    slope, phase
):
    spec = {
        'id': 'beam',
        'line': [[15, 25 + phase], [55, 25 + phase + 40 * slope]],
        'thickness': 6,
        'members': ['a', 'b'],
    }
    for scale in (2, 3, 4):
        p = beam_candidate(spec, scale)
        r = beam_metrics(p, spec)
        assert spec['line'] == [[15, 25 + phase], [55, 25 + phase + 40 * slope]]
        assert p.box[0] == 15 and p.box[2] == 56 and r['connected_components'] == 1
        for x, y in spec['line']:
            stem = Image.new('L', (80, 80))
            ImageDraw.Draw(stem).line([(x, round(y)), (x, 65)], 255, 2)
            assert contact(p, piece('stem', stem, 1, 1, 'STEM')) > 0
        assert beam_candidate(spec, scale).tile.tobytes() == p.tile.tobytes()
        assert r['nonzero_pixels'] <= (41 * int(8 + abs(40 * slope)))


def test_beam_attachment_and_collision_negative_controls():
    p = beam_candidate({'id': 'b', 'line': [[10, 20], [40, 25]], 'thickness': 5}, 4)
    assert contact(p, piece('remote', dot(50, 60), 1, 1, 'STEM')) == 0
    assert contact(p, piece('unrelated', dot(20, 22), 1, 1, 'NOTE')) == 1
    with pytest.raises(ValueError, match='clipping'):
        compose([p.moved(100)], (80, 80))
    with pytest.raises(ValueError):
        beam_candidate({'id': 'b', 'line': [[40, 20], [10, 25]], 'thickness': 5}, 4)


def test_fixed_notation_split_must_not_cut_existing_lyric_allocation():
    fixed = dot(30, 30)
    a = piece('a', dot(30, 36), 1, 1, 'SYLLABLE')
    b = piece('b', dot(30, 65), 2, 2, 'SYLLABLE')
    # A known-safe lyric may extend below a purely administrative notation split.
    failed, r = layout([a, b], fixed, [(0, 34), (34, 80)], 6)
    assert failed is None
    result, r = layout([a, b], fixed, [(0, 34), (34, 80)], 6, lyric_bottoms=[40, 80])
    assert r['feasible'] and r['system_offsets'] == [0, 0]
    assert [p.box for p in result[0]] == [a.box, b.box]
