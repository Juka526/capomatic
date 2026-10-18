"""Raster-coordinate controls; no score, external font, models or Audiveris."""

import math

from PIL import Image, ImageDraw, ImageFont
import pytest

from scripts.research.gt05_raster_anchor import glyph
from scripts.research.gt05_anchor_study import observe, design


@pytest.mark.parametrize('phase', [0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875])
def test_actual_pixels_obey_half_pixel_limit_without_size_or_coverage_changes(phase):
    font = ImageFont.load_default(size=28)
    a, info = glyph((200, 200), font, 'A', (100 + phase, 100 + phase), (0, 0, 20, 30), 0.028)
    b, _ = glyph((200, 200), font, 'A', (130 + phase, 120 + phase), (0, 0, 20, 30), 0.028)
    ma = observe(a, (100 + phase, 100 + phase))
    mb = observe(b, (130 + phase, 120 + phase))
    assert all(abs(x) <= 0.5 for x in ma['residual'])
    assert ma['cropped_alpha_sha256'] == mb['cropped_alpha_sha256']
    assert ma['ink_size'] == mb['ink_size']
    assert info['requested_anchor'] == [100 + phase, 100 + phase]


def test_pixel_edge_and_index_conventions_and_wrong_offset_negative_control():
    image = Image.new('L', (40, 40))
    ImageDraw.Draw(image).rectangle((10, 10, 20, 20), fill=255)
    measured = observe(image, (15, 15))
    assert measured['bbox_center_index'] == [15, 15]
    assert measured['bbox_center_edge'] == [15.5, 15.5]
    assert measured['residual'] == [0, 0]
    shifted = Image.new('L', image.size)
    shifted.paste(image, (1, 0))
    assert observe(shifted, (15, 15))['residual'] == [1, 0]


def test_invalid_font_clipping_and_nonfinite_fail_closed(tmp_path):
    file = tmp_path / 'font'
    file.write_bytes(b'wrong-font')
    with pytest.raises(ValueError, match='hash'):
        design(file)
    font = ImageFont.load_default(size=28)
    with pytest.raises(ValueError, match='Clipped'):
        glyph((100, 100), font, 'A', (0, 0), (0, 0, 20, 30), 0.028)
    with pytest.raises(ValueError, match='nonfinite'):
        glyph((100, 100), font, 'A', (math.nan, 20), (0, 0, 20, 30), 0.028)


def test_bbox_centroid_and_optical_center_are_not_equated():
    image = Image.new('L', (40, 40))
    d = ImageDraw.Draw(image)
    d.rectangle((10, 10, 20, 20), fill=32)
    d.rectangle((10, 10, 12, 20), fill=255)
    result = observe(image, (15, 15))
    assert result['bbox_center_index'] == [15, 15]
    assert result['coverage_centroid'][0] < 15
