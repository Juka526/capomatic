"""Source coordinate and cache regression contracts; no musical accuracy claims."""
import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, NumberObject, RectangleObject

from backend.api.score import cache_bytes, summary
from backend.omr_v3 import core
from backend.omr_v3.source_layout import (
    Affine, SourceLayoutBundle, SourcePage, pdf_metadata, pdf_transform, readiness,
)


def png(size=(100, 80)):
    out = io.BytesIO()
    Image.new('RGB', size, 'white').save(out, format='PNG')
    return out.getvalue()


def omr(size=(100, 80), slope=0):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as archive:
        archive.writestr('sheet#1/GRAY.png', png(size))
        archive.writestr('sheet#1/sheet#1.xml', f'''
        <sheet><picture width="{size[0]}" height="{size[1]}"/><skew slope="{slope}"/>
        <page><system id="2"><sig><inters><head id="13" glyph="9"/></inters>
        <relations><head-stem source="13" target="14"/></relations></sig></system></page>
        </sheet>''')
    return out.getvalue()


def page():
    return SourcePage.capture(png(), omr(), {'raster_size': [100, 80]})


@pytest.mark.parametrize('rotation', [0, 90, 180, 270])
def test_pdf_box_origin_rotation_and_inverse(rotation):
    writer = PdfWriter(); p = writer.add_blank_page(120, 160)
    p.mediabox = RectangleObject((-10, -20, 110, 140))
    p.cropbox = RectangleObject((10, 20, 82, 92))
    p.rotate(rotation)
    data = io.BytesIO(); writer.write(data)
    meta = pdf_metadata(data.getvalue())[0]
    t, size = pdf_transform(meta, 72)
    assert size == (72, 72)
    expected = {0: (0, 72), 90: (0, 0), 180: (72, 0), 270: (72, 72)}
    assert t.point(10, 20) == expected[rotation]
    for x, y in [(10, 20), (82, 92), (31.25, 53.75)]:
        assert t.inverse().point(*t.point(x, y)) == pytest.approx((x, y), abs=1e-12)
    assert meta['boxes']['mediabox'] == (-10, -20, 110, 140)


@pytest.mark.parametrize('unit,rotation', [(2, 0), (1, 45)])
def test_unverified_pdf_units_and_rotation_rejected(unit, rotation):
    writer = PdfWriter(); p = writer.add_blank_page(120, 160)
    p[NameObject('/UserUnit')] = NumberObject(unit)
    p[NameObject('/Rotate')] = NumberObject(rotation)
    data = io.BytesIO(); writer.write(data)
    with pytest.raises(core.ScoreError, match='unit or rotation'):
        pdf_metadata(data.getvalue())


def test_singular_or_nonfinite_transform_rejected():
    for args in [(0, 0, 0, 0), (float('nan'),)]:
        with pytest.raises(core.ScoreError):
            Affine(*args)


@pytest.mark.parametrize('size,slope,reason', [
    ((101, 80), 0, 'OMR_RASTER_DIMENSION_MISMATCH'),
    ((100, 80), 0.01, 'OMR_DESKEW_TRANSFORM_UNVERIFIED'),
])
def test_same_size_does_not_prove_deskew_transform(size, slope, reason):
    captured = SourcePage.capture(png(), omr(size, slope), {'raster_size': [100, 80]})
    assert not captured.evidence['geometry_ready']
    assert reason in captured.evidence['issues']
    assert captured.metadata['raster_to_omr'] is None


def test_raster_mismatch_is_rejected_without_resize():
    with pytest.raises(core.ScoreError, match='size'):
        SourcePage.capture(png(), omr(), {'raster_size': [99, 80]})


def test_omr_relations_and_bboxes_do_not_authorize_ink_replacement():
    for shift in [0, 1, -1]:
        state = readiness(page(), True, 7, shift)
        assert state['geometry_ready']
        assert not state['lyric_layer_ready'] and not state['render_ready']
        safety = state['source_ink_safety']
        assert not safety['edit_authorized']
        assert safety['protected_region'] == 'ENTIRE_SOURCE_PAGE'
        assert safety['objects'][0]['page'] == 7
        assert safety['objects'][0]['object'] == '13'
        assert safety['objects'][0]['relations'] == [['13', '14', 'head-stem']]
        assert all(value is None for value in state['measurements'].values())


def test_cache_accounts_for_actual_source_and_proof_bytes():
    captured = page()
    bundle = SourceLayoutBundle(b'original', '.png', (captured,))
    result = core.Result(b'', None, b'xml', {}, source_layout=bundle)
    assert cache_bytes(result) == 3 + len(b'{}') + bundle.byte_size
    assert bundle.byte_size == 8 + sum(map(len, (captured.png, captured.omr,
                                                captured.metadata_json, captured.evidence_json)))
    result = replace(result, recognized_musicxml=None)
    result.report['input'] = {'source': 'image'}
    for shift in [1, -1, 0]:
        report = summary(result, shift)
        assert not report['render_ready']
    assert result.source_layout.source == b'original' and result.source_layout.pages[0].png == captured.png


def test_image_capture_preserves_native_colour_and_size(tmp_path):
    source = tmp_path/'native.png'; target = tmp_path/'omr.png'
    image = Image.new('RGB', (15, 20), (100, 121, 149)); image.putpixel((5, 5), (0, 0, 1))
    image.save(source)
    info = core.rasterize(source, '.png', target, 30, tmp_path, retain_source_layout=True)
    with Image.open(target) as actual:
        assert actual.size == image.size and actual.tobytes() == image.tobytes()
    assert info['scale'] == 1


def test_new_omr_path_disables_only_audiveris_text_ocr(tmp_path, monkeypatch):
    commands = []
    monkeypatch.setattr(core, '_bin', lambda *a: 'Audiveris')
    def run(argv, *a):
        commands.append(argv)
        (tmp_path/'omr'/'score.musicxml').write_text('<score-partwise/>')
    monkeypatch.setattr(core, '_run', run)
    core.run_audiveris(tmp_path/'page.png', tmp_path/'omr', 30, tmp_path, disable_text_ocr=True)
    assert 'org.audiveris.omr.text.tesseract.TesseractOCR.useOCR=false' in commands[0]


@pytest.mark.parametrize('rotation', [0, 90, 180, 270])
def test_actual_poppler_dimensions_match_pdf_contract(tmp_path, rotation):
    writer = PdfWriter(); p = writer.add_blank_page(120, 160)
    p.mediabox = RectangleObject((-10, -20, 110, 140))
    p.cropbox = RectangleObject((10, 20, 82, 110))
    p.rotate(rotation)
    source = tmp_path/'source.pdf'; writer.write(source)
    output = tmp_path/'source.png'
    info = core.rasterize(source, '.pdf', output, 30, tmp_path, retain_source_layout=True)
    assert info['raster_size'] == ([375, 300] if rotation in (90, 270) else [300, 375])


def test_decimal_page_dimensions_do_not_add_a_phantom_pixel():
    meta = {'boxes': {'cropbox': [0, 0, 567.12, 802.08]}, 'rotation': 0}
    assert pdf_transform(meta, 300)[1] == (2363, 3342)


def test_equal_dimensions_and_zero_skew_do_not_prove_raster_identity():
    original = page()
    altered = io.BytesIO()
    Image.new('RGB', (100, 80), (250, 250, 250)).save(altered, format='PNG')
    captured = SourcePage.capture(altered.getvalue(), original.omr, {'raster_size': [100, 80]})
    assert not captured.evidence['geometry_ready']
    assert 'OMR_SOURCE_RASTER_IDENTITY_MISMATCH' in captured.evidence['issues']
