"""Pixel ownership requires complete source support, never a rectangle alone."""
import io
import zipfile
from dataclasses import replace
from xml.etree import ElementTree as ET

import numpy as np
import pytest
from PIL import Image

from backend.omr_v3.scan_ink import analyze_source, relations, run_mask
from backend.omr_v3.source_layout import SourcePage


def png(array):
    out = io.BytesIO(); Image.fromarray(array).save(out, format='PNG')
    return out.getvalue()


def evidence(*, edge=False, shared_staff=False, protected_contact=False, duplicate=False):
    rgb = np.full((12, 16, 3), 255, dtype=np.uint8)
    rgb[3:6, 4:6] = 0
    binary = np.full((12, 16), 255, dtype=np.uint8)
    binary[3:6, 4:6] = 0
    if edge:
        rgb[3:6, 6] = 240
    if shared_staff:
        rgb[4, 1:14] = 0; binary[4, 1:14] = 0
    if protected_contact:
        rgb[6:8, 5] = 0; binary[6:8, 5] = 0
    glyph = '<glyph id="9" left="4" top="3"><run-table orientation="VERTICAL" width="2" height="3"><runs>3</runs><runs>3</runs></run-table></glyph>'
    staff = '<staff><lines><line glyph="10"><point x="1" y="4"/><point x="13" y="4"/></line></lines></staff>' if shared_staff else ''
    other = '<rest id="2" glyph="11"/>' if protected_contact else ''
    staff_glyph = '<glyph id="10" left="1" top="4"><run-table orientation="HORIZONTAL" width="13" height="1"><runs>13</runs></run-table></glyph>' if shared_staff else ''
    other_glyph = '<glyph id="11" left="5" top="6"><run-table orientation="VERTICAL" width="1" height="2"><runs>2</runs></run-table></glyph>' if protected_contact else ''
    xml = f'<sheet><picture width="16" height="12"/><skew slope="0"/><page><system id="1"><part>{staff}</part><sig><inters><head id="1" glyph="9"/>{other}</inters></sig></system></page><glyph-index>{glyph}{glyph if duplicate else ""}{staff_glyph}{other_glyph}</glyph-index></sheet>'
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('sheet#1/sheet#1.xml', xml)
        z.writestr('sheet#1/GRAY.png', png(rgb.max(axis=2)))
        z.writestr('sheet#1/BINARY.png', png(binary))
    return png(rgb), out.getvalue()


def mask(data, name):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        with Image.open(io.BytesIO(z.read(name+'.png'))) as image:
            return np.asarray(image).copy() > 0


def test_complete_component_coverage_does_not_grant_semantic_edit_permission():
    source, omr = evidence()
    report, masks = analyze_source(source, omr)
    assert report['source_component_coverage_pixels'] == 6
    assert not report['edit_authorized'] and not report['ownership_ready']
    assert np.count_nonzero(mask(masks, 'component_coverage')) == 6
    assert np.all(mask(masks, 'protected') != mask(masks, 'component_coverage'))
    assert source == evidence()[0]


@pytest.mark.parametrize('kwargs,code', [
    ({'edge': True}, 'UNASSIGNED_SOURCE_RGB_OR_JPEG_EDGE'),
    ({'shared_staff': True}, 'MUSIC_STAFF_COMPONENT_REQUIRES_RECONSTRUCTION_PROOF'),
    ({'protected_contact': True}, 'MUSIC_PROTECTED_GLYPH_CONTACT'),
])
def test_full_connected_component_stays_protected(kwargs, code):
    source, omr = evidence(**kwargs)
    report, masks = analyze_source(source, omr)
    assert report['source_component_coverage_pixels'] == 0
    assert any(code in b['codes'] for b in report['blockers'])
    assert any('1' in b['objects'] and b['page'] == 1 for b in report['blockers'])
    assert any(o['object'] == '1' and o['components'] for o in report['object_regions'])
    assert mask(masks, 'protected').all()
    assert not mask(masks, 'component_coverage').any()


def test_duplicate_glyphs_cannot_silently_overwrite_ownership():
    report, masks = analyze_source(*evidence(duplicate=True))
    assert any(i['code'] == 'DUPLICATE_GLYPH_ID' for i in report['structure_issues'])
    assert mask(masks, 'protected').all()


def test_real_audiveris_relation_wrapper_retains_the_child_type():
    system = ET.fromstring('<system><sig><relations><relation source="1" target="2"><head-stem head-side="RIGHT"/></relation></relations></sig></system>')
    assert relations(system) == [{'source': '1', 'target': '2', 'kind': 'head-stem',
                                   'attributes': {'head-side': 'RIGHT'}}]


def test_immutable_masks_are_charged_to_source_cache():
    source, omr = evidence()
    page = SourcePage.capture(source, omr, {'raster_size': [16, 12]})
    assert page.ink_masks
    assert page.byte_size - replace(page, ink_masks=b'').byte_size == len(page.ink_masks)
    assert page.evidence['component_analysis']['masks_sha256']


@pytest.mark.parametrize('runs', ['-1 2', '4'])
def test_malformed_runs_reject_without_clipping(runs):
    glyph = ET.fromstring(f'<glyph left="0" top="0"><run-table orientation="VERTICAL" width="1" height="3"><runs>{runs}</runs></run-table></glyph>')
    with pytest.raises(ValueError):
        run_mask(glyph, (10, 10))


def test_source_pixel_limit_precedes_conversion(monkeypatch):
    from backend.omr_v3 import scan_ink
    source, omr = evidence()
    monkeypatch.setattr(scan_ink, 'MAX_PIXELS', 10)
    def forbidden(*args, **kwargs):
        pytest.fail('Pixel conversion preceded the size check')
    monkeypatch.setattr(Image.Image, 'convert', forbidden)
    with pytest.raises(ValueError, match='SOURCE_PIXEL_LIMIT'):
        analyze_source(source, omr)


def test_dangling_relation_cannot_authorize_component_coverage():
    source, omr = evidence()
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(omr)) as original, zipfile.ZipFile(output, 'w') as changed:
        for name in original.namelist():
            data = original.read(name)
            if name.endswith('.xml'):
                data = data.replace(b'</sig>', b'<relations><relation source="1" target="999"><head-stem/></relation></relations></sig>')
            changed.writestr(name, data)
    report, masks = analyze_source(source, output.getvalue())
    assert any(i['code'] == 'DANGLING_OBJECT_RELATION' for i in report['structure_issues'])
    assert not report['source_component_coverage_pixels']
    assert mask(masks, 'protected').all()
