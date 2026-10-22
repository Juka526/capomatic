from xml.etree import ElementTree as ET

import numpy as np
import pytest

from scripts.ordinary_scan_inventory import glyph_support


@pytest.mark.parametrize('orientation', ['VERTICAL', 'HORIZONTAL'])
def test_runs_check_actual_pixels_including_leading_background(orientation):
    glyph = ET.fromstring(f'''<glyph left="1" top="1"><run-table orientation="{orientation}"
        width="2" height="2"><runs>0 1 1</runs><runs>2</runs></run-table></glyph>''')
    binary = np.full((4, 4), 255, dtype=np.uint8)
    binary[1:3, 2] = 0
    binary[2, 1] = 0
    result = glyph_support(glyph, binary)
    assert result == {'status': 'SUPPORTED', 'foreground_samples': 3,
                      'binary_supported_samples': 3, 'unsupported_samples': 0}
    binary[2, 2] = 255
    assert glyph_support(glyph, binary)['unsupported_samples'] == 1


def test_out_of_bounds_runs_cannot_grant_pixel_support():
    glyph = ET.fromstring('''<glyph left="0" top="0"><run-table orientation="VERTICAL"
        width="1" height="2"><runs>3</runs></run-table></glyph>''')
    assert glyph_support(glyph, np.zeros((3, 3)))['status'] == 'INVALID'
