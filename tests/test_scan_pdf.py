"""Embedded image grid contracts, independent of music recognition."""
import io

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject, EncodedStreamObject,
                           NameObject, NumberObject, RectangleObject)

from backend.omr_v3.core import ScoreError, rasterize
from backend.omr_v3.scan_pdf import extract_scan
from backend.omr_v3.source_layout import Affine, SourcePage


def scan_pdf(rotation=0, extra=b'', **image_values):
    jpeg = io.BytesIO()
    image = Image.new('RGB', (27, 35), (141, 90, 173))
    image.putpixel((3, 8), (10, 20, 30))
    image.save(jpeg, format='JPEG')
    writer = PdfWriter()
    page = writer.add_blank_page(100, 130)
    page.mediabox = RectangleObject((-10, -20, 90, 110))
    page.cropbox = RectangleObject((-5, -15, 85, 105))
    page.rotate(rotation)
    obj = EncodedStreamObject()
    obj._data = jpeg.getvalue()
    values = dict(Type=NameObject('/XObject'), Subtype=NameObject('/Image'),
                           Filter=NameObject('/DCTDecode'), Width=NumberObject(27),
                           Height=NumberObject(35), ColorSpace=NameObject('/DeviceRGB'),
                           BitsPerComponent=NumberObject(8))
    values.update(image_values)
    for key, value in values.items():
        obj[NameObject('/'+key)] = value
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/XObject'):
        DictionaryObject({NameObject('/Scan'): writer._add_object(obj)})})
    content = DecodedStreamObject()
    content.set_data(b'q 90 0 0 120 -5 -15 cm /Scan Do Q'+extra)
    page[NameObject('/Contents')] = writer._add_object(content)
    output = io.BytesIO(); writer.write(output)
    return output.getvalue(), jpeg.getvalue()


@pytest.mark.parametrize('rotation', [0, 90, 180, 270])
def test_embedded_grid_and_pdf_inverse_preserve_decoded_pixels(rotation, tmp_path):
    data, jpeg = scan_pdf(rotation)
    source = tmp_path/'scan.pdf'; source.write_bytes(data)
    output = tmp_path/'scan.png'
    meta = rasterize(source, '.pdf', output, 30, tmp_path, retain_source_layout=True)
    with Image.open(io.BytesIO(jpeg)) as original, Image.open(output) as decoded:
        assert decoded.size == (27, 35)
        assert decoded.tobytes() == original.tobytes()
    assert meta['rotation'] == rotation
    forward, inverse = Affine(*meta['raster_to_pdf']), Affine(*meta['pdf_to_raster'])
    assert forward.point(0, 0) == (-5, 105)
    assert forward.point(27, 35) == (85, -15)
    for point in [(0, 0), (27, 35), (3.25, 8.5)]:
        assert inverse.point(*forward.point(*point)) == pytest.approx(point, abs=1e-12)
    page = SourcePage.capture(output.read_bytes(), b'', meta)
    assert page.metadata['raster_size'] == [27, 35]
    assert not page.evidence['geometry_ready']


@pytest.mark.parametrize('extra', [b' 0 0 m 1 1 l S', b' BT ET', b' q 0 0 3 3 re W n Q'])
def test_extra_drawing_or_clipping_defers_to_safe_legacy_path(extra):
    assert extract_scan(scan_pdf(extra=extra)[0]) is None


@pytest.mark.parametrize('values', [
    {'ColorSpace': NameObject('/DeviceCMYK')},
    {'Decode': ArrayObject([NumberObject(1), NumberObject(0)])},
    {'Mask': NumberObject(1)},
])
def test_unproven_color_and_masks_not_accepted(values):
    assert extract_scan(scan_pdf(**values)[0]) is None


def test_single_pixel_pdf_render_grid_difference_does_not_resize_image(tmp_path):
    data, jpeg = scan_pdf()
    writer = PdfWriter(clone_from=io.BytesIO(data))
    writer.pages[0].mediabox = RectangleObject((0, 0, 6.48, 8.40001))
    writer.pages[0].cropbox = writer.pages[0].mediabox
    output = io.BytesIO(); writer.write(output)
    png, meta = extract_scan(output.getvalue())
    assert meta['raster_size'] == [27, 35]
    with Image.open(io.BytesIO(png)) as actual, Image.open(io.BytesIO(jpeg)) as expected:
        assert actual.tobytes() == expected.tobytes()


def test_capture_rejects_changed_pixels_or_matrix():
    png, meta = extract_scan(scan_pdf()[0])
    altered = {**meta, 'raster_to_pdf': [1, 0, 0, 1, 0, 0]}
    with pytest.raises(ScoreError, match='transform mismatch'):
        SourcePage.capture(png, b'', altered)
    altered = {**meta, 'decoded_rgb_sha256': '0'*64}
    with pytest.raises(ScoreError, match='RGB digest mismatch'):
        SourcePage.capture(png, b'', altered)


def test_invalid_pdf_is_reported_as_score_error():
    with pytest.raises(ScoreError):
        extract_scan(b'%PDF-1.4\ninvalid')


def test_output_png_does_not_inherit_jpeg_color_metadata():
    data, _ = scan_pdf()
    writer = PdfWriter(clone_from=io.BytesIO(data))
    obj = writer.pages[0]['/Resources']['/XObject']['/Scan'].get_object()
    jpeg = io.BytesIO()
    Image.new('RGB', (27, 35), (100, 150, 200)).save(jpeg, format='JPEG', icc_profile=b'test-profile')
    obj._data = jpeg.getvalue()
    result = io.BytesIO(); writer.write(result)
    png, _ = extract_scan(result.getvalue())
    with Image.open(io.BytesIO(png)) as actual:
        assert 'icc_profile' not in actual.info


def test_content_expansion_is_bounded_before_pypdf_decode(monkeypatch):
    import zlib
    data, _ = scan_pdf()
    writer = PdfWriter(clone_from=io.BytesIO(data))
    stream = EncodedStreamObject()
    stream[NameObject('/Filter')] = NameObject('/FlateDecode')
    stream._data = zlib.compress(b' ' * 100_000)
    writer.pages[0][NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO(); writer.write(output)
    def unbounded_decode(*args, **kwargs):
        pytest.fail('Unbounded content decoder was called')
    monkeypatch.setattr(EncodedStreamObject, 'get_data', unbounded_decode)
    assert extract_scan(output.getvalue()) is None


def test_singular_pdf_image_matrix_is_rejected():
    data, _ = scan_pdf()
    writer = PdfWriter(clone_from=io.BytesIO(data))
    stream = DecodedStreamObject()
    stream.set_data(b'q 0 0 0 0 0 0 cm /Scan Do Q')
    writer.pages[0][NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO(); writer.write(output)
    with pytest.raises(ScoreError, match='singular'):
        extract_scan(output.getvalue())
