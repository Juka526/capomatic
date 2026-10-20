"""Lossless integration, independent collision controls and export-gap audit."""

import numpy as np
import pytest
from PIL import Image

from scripts.research import gt14e_two_system_validation as gt


def test_integration_retains_page_coordinates_and_all_source_alphas():
    first = Image.new('L', (40, 50))
    first.putpixel((7, 8), 130)
    second = first.copy()
    second.putpixel((22, 38), 255)
    out, a, b = gt.integrate(first, second, 25)
    assert out.tobytes() == second.tobytes()
    assert a.getpixel((7, 8)) == 130 and b.getpixel((22, 38)) == 255
    assert not np.any((np.asarray(a) > 0) & (np.asarray(b) > 0))


@pytest.mark.parametrize('fault', ['first-changed', 'cross-split', 'dimension', 'mode'])
def test_integration_fails_closed_instead_of_moving_or_rescaling(fault):
    first = Image.new('L', (40, 50))
    first.putpixel((7, 8), 130)
    second = first.copy()
    second.putpixel((22, 38), 255)
    if fault == 'first-changed':
        second.putpixel((7, 8), 129)
    if fault == 'cross-split':
        first.putpixel((6, 26), 255)
    if fault == 'dimension':
        second = Image.new('L', (41, 50))
    if fault == 'mode':
        second = second.convert('RGB')
    with pytest.raises(ValueError):
        gt.integrate(first, second, 25)


def test_only_empty_padding_may_be_cropped_and_coordinate_width_cannot_change():
    page = Image.new('L', (40, 90))
    page.putpixel((20, 30), 200)
    out = gt.expanded(page, (40, 50))
    assert out.size == (40, 50) and out.getpixel((20, 30)) == 200
    page.putpixel((20, 80), 1)
    with pytest.raises(ValueError, match='clipped'):
        gt.expanded(page, (40, 50))
    with pytest.raises(ValueError, match='coordinate'):
        gt.expanded(Image.new('L', (41, 50)), (40, 50))


def test_collision_uses_independent_notation_without_subtracting_text():
    text = Image.new('L', (50, 60))
    text.putpixel((20, 30), 1)
    music = Image.new('L', (50, 60))
    music.putpixel((20, 30), 1)
    r = gt.text_check({'lyric': text}, music, (0, 0, 50, 60))
    assert r['text_notation_unique_contact_pixels'] == 1
    assert r['minimum_text_notation_ink_center_distance_px'] == 0
    music = Image.new('L', (50, 60))
    music.putpixel((20, 28), 255)
    r = gt.text_check({'lyric': text}, music, (0, 0, 50, 60))
    assert r['text_notation_unique_contact_pixels'] == 0
    assert r['minimum_text_notation_ink_center_distance_px'] == 2


def test_text_pair_contacts_and_clipping_not_hidden_by_canvas_union():
    p = Image.new('L', (50, 60))
    p.putpixel((20, 30), 255)
    fixed = Image.new('L', (50, 60))
    fixed.putpixel((5, 5), 255)
    r = gt.text_check({'a': p, 'b': p.copy()}, fixed, (21, 0, 50, 60))
    assert r['text_text_contacts'] == [{'a': 'a', 'b': 'b', 'pixels': 1}]
    assert r['clipped_text_components'] == ['a', 'b']


def test_missing_lyric_extender_serialization_is_reported_not_fixed(tmp_path):
    p = tmp_path / 'source.musicxml'
    p.write_text(
        '<score-partwise><part><measure number="1"><note><tie type="start"/><lyric number="1"><text>곳</text></lyric></note></measure></part></score-partwise>'
    )
    before = p.read_bytes()
    r = gt.serialization_audit(p)
    assert r['lyric_elements'] == 1 and r['extend_elements'] == 0 and r['tie_elements'] == 1
    assert not r['production_export_modified'] and p.read_bytes() == before
    p.write_text(
        '<score-partwise><part><measure number="1"><note><lyric><text>곳</text><extend type="start"/></lyric></note></measure></part></score-partwise>'
    )
    assert gt.serialization_audit(p)['extend_elements'] == 1


def test_deterministic_pixel_identity_repeated_assembly():
    a = Image.new('L', (30, 40))
    a.putpixel((5, 10), 255)
    b = a.copy()
    b.putpixel((20, 30), 128)
    first = gt.integrate(a, b, 20)[0]
    second = gt.integrate(a, b, 20)[0]
    assert first.tobytes() == second.tobytes()
