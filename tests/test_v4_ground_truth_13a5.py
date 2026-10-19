"""Synthetic integer-layout controls fixed before any new score prediction."""

import numpy as np
import pytest
from PIL import Image

from scripts.research.gt13a5_lyric_layout import (
    contacts,
    displacement_domain,
    layout,
    spacing_obstacle,
    translate,
    union,
)


def mask(points, size=(60, 80)):
    im = Image.new('L', size)
    for x, y in points:
        im.putpixel((x, y), 127)
    return im


def test_full_domain_proves_minimal_shift_and_one_pixel_gap():
    lyric = mask([(10, 20), (10, 21)])
    music = mask([(10, 20), (10, 22), (10, 24)])
    d = displacement_domain(lyric, music, mask([]), (0, 0, 60, 80))
    assert d['selected_dy'] == 6
    assert d['forbidden_dy'] == list(range(6))
    assert d['feasible_dy'] == list(range(6, 59))
    # Contact-free dy=5 still fails spacing. A negative control for overlap-only checks.
    moved = translate(lyric, 5, (0, 0, 60, 80))
    assert not np.any((np.asarray(moved) > 0) & (np.asarray(music) > 0))
    assert np.any((np.asarray(moved) > 0) & spacing_obstacle(music))


def test_clear_baseline_stays_exactly_fixed():
    p = {'a': mask([(10, 20)]), 'b': mask([(30, 35)])}
    moved, r = layout(p, {'a': 1, 'b': 3}, mask([(10, 10)]), 'local', (0, 0, 60, 80))
    assert r['dy_by_measure'] == {1: 0, 3: 0}
    assert all(p[n].tobytes() == moved[n].tobytes() for n in p)


def test_both_rows_marks_and_horizontal_anchors_translate_together():
    p = {
        'upper': mask([(10, 20)]),
        'lower': mask([(10, 30)]),
        'mark': mask([(15, 20)]),
        'm3': mask([(40, 30)]),
    }
    groups = {'upper': 2, 'lower': 2, 'mark': 2, 'm3': 3}
    moved, r = layout(p, groups, mask([(10, 20)]), 'local', (0, 0, 60, 80))
    assert r['dy_by_measure'] == {2: 2, 3: 0}
    assert moved['lower'].getbbox()[1] - moved['upper'].getbbox()[1] == 10
    for n in p:
        assert moved[n].getbbox()[0] == p[n].getbbox()[0]
        assert moved[n].crop(moved[n].getbbox()).tobytes() == p[n].crop(p[n].getbbox()).tobytes()


def test_global_discloses_m3_change_and_determinism():
    p = {'a': mask([(10, 20)]), 'b': mask([(40, 30)])}
    args = (p, {'a': 2, 'b': 3}, mask([(10, 20)]), 'global', (0, 0, 60, 80))
    moved, r = layout(*args)
    again, other = layout(*args)
    assert r == other and r['m3_changed_on_new_canvas']
    assert r['dy_by_measure'] == {2: 2, 3: 2}
    assert all(moved[n].tobytes() == again[n].tobytes() for n in p)


@pytest.mark.parametrize('dy', [-1, 0.5, True, 80])
def test_invalid_transform_or_clipping_rejected(dy):
    with pytest.raises(ValueError):
        translate(mask([(10, 20)]), dy, (0, 0, 60, 80))


def test_unsatisfiable_and_m3_collision_fail_closed():
    p = {'a': mask([(10, 78)]), 'b': mask([(40, 30)])}
    with pytest.raises(ValueError, match='No feasible'):
        layout(p, {'a': 2, 'b': 3}, mask([(10, 78), (10, 79)]), 'local', (0, 0, 60, 80))
    with pytest.raises(ValueError, match='measure 3'):
        layout({'b': p['b']}, {'b': 3}, mask([(40, 30)]), 'local', (0, 0, 60, 80))


def test_neighbor_lyric_is_obstacle_not_silently_overlapped():
    p = mask([(10, 20)])
    d = displacement_domain(p, mask([(10, 20)]), mask([(10, 22)]), (0, 0, 60, 80))
    assert d['selected_dy'] == 3
    assert contacts({'a': p, 'b': p})[0]['pixels'] == 1
    assert np.count_nonzero(np.asarray(union([p, p]))) == 1


def test_all_antialias_values_preserved_not_thresholded():
    p = mask([(10, 20), (11, 20)])
    p.putpixel((10, 20), 1)
    p.putpixel((11, 20), 254)
    moved = translate(p, 2, (0, 0, 60, 80))
    assert moved.getpixel((10, 22)) == 1 and moved.getpixel((11, 22)) == 254
    assert int(np.asarray(moved).sum()) == int(np.asarray(p).sum())
