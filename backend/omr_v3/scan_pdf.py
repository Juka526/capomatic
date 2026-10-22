"""Decode the source grid of a single-image PDF without rasterizing its page.

This input adapter grants no pixel-edit permission. Page clipping and rotation
remain PDF operations, separate from the decoded image's pixel coordinates.
"""
from __future__ import annotations

import io
import zlib

from PIL import Image
from pypdf import PdfReader
from pypdf.generic import ContentStream, DecodedStreamObject, StreamObject
from pypdf.errors import PdfReadError

from .core import MAX_PIXELS, ScoreError
from .source_layout import Affine, digest, pdf_metadata


def _extract_scan(data: bytes) -> tuple[bytes, dict] | None:
    """Return RGB PNG and exact placement evidence, or defer non-image PDFs.

    Accept only q/cm/Do/Q with one JPEG, DeviceRGB, no masks or annotations.
    The whitelist rules out hidden text, transparency, and custom clipping.
    The original page boxes describe the remaining, explicit page clipping.
    """
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted or len(reader.pages) != 1:
        return None
    page = reader.pages[0]
    if page.get('/Annots') or page.get('/Group') or reader.trailer['/Root'].get('/OCProperties'):
        return None
    content = page.get('/Contents')
    if content is None:
        return None
    content = content.get_object()
    if not isinstance(content, StreamObject) or content.get('/DecodeParms'):
        return None
    raw_content = content._data
    if content.get('/Filter') == '/FlateDecode':
        decoder = zlib.decompressobj()
        raw_content = decoder.decompress(raw_content, 64 * 1024 + 1)
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            return None
    elif content.get('/Filter') is not None:
        return None
    if len(raw_content) > 64 * 1024:
        return None
    decoded_content = DecodedStreamObject()
    decoded_content.set_data(raw_content)
    operations = ContentStream(decoded_content, reader).operations
    if [op for _, op in operations] != [b'q', b'cm', b'Do', b'Q']:
        return None
    if operations[0][0] or operations[3][0] or len(operations[1][0]) != 6 or len(operations[2][0]) != 1:
        return None
    resources = page['/Resources'].get_object()
    if resources.get('/ColorSpace') or resources.get('/ExtGState'):
        return None
    if '/XObject' not in resources:
        return None
    name = operations[2][0][0]
    objects = resources['/XObject'].get_object()
    if name not in objects or len(objects) != 1:
        return None
    image = objects[name].get_object()
    if (image.get('/Subtype') != '/Image' or image.get('/Filter') != '/DCTDecode'
            or image.get('/ColorSpace') != '/DeviceRGB' or image.get('/BitsPerComponent') != 8
            or any(key in image for key in ('/SMask', '/Mask', '/Decode', '/ImageMask', '/Alternates', '/OC', '/Intent', '/OPI'))):
        return None
    params = image.get('/DecodeParms')
    if params:
        params = params.get_object()
        if params.get('/ColorTransform', 1) != 1 or set(params) - {
                '/Blend', '/ColorTransform', '/Colors', '/Columns', '/HSamples',
                '/QFactor', '/Rows', '/VSamples'}:
            return None
    width, height = int(image['/Width']), int(image['/Height'])
    if width <= 0 or height <= 0 or width * height > MAX_PIXELS:
        raise ScoreError('Source raster too large or invalid', 413)
    placement = Affine(*(float(v) for v in operations[1][0]))
    raw = image.get_data()
    with Image.open(io.BytesIO(raw)) as decoded:
        if decoded.format != 'JPEG' or decoded.mode != 'RGB' or decoded.size != (width, height):
            raise ScoreError('Embedded JPEG does not match PDF image contract')
        rgb = decoded.tobytes()
        output = io.BytesIO()
        # DeviceRGB means samples here; JPEG ICC metadata must not alter PNG display.
        Image.frombytes('RGB', decoded.size, rgb).save(output, format='PNG')
    # PDF image unit square uses a bottom-left origin; raster edges use top-left.
    a, b, c, d, e, f = placement.values
    raster_to_pdf = Affine(a/width, b/width, -c/height, -d/height, c+e, d+f)
    meta = pdf_metadata(data)[0]
    return output.getvalue(), {
        **meta, 'source': 'pdf', 'raster_basis': 'embedded_jpeg_rgb',
        'width': width, 'height': height, 'raster_size': [width, height], 'scale': 1.0,
        'image_name': str(name), 'image_placement': placement.values,
        'raster_to_pdf': raster_to_pdf.values,
        'pdf_to_raster': raster_to_pdf.inverse().values,
        'pdf_page_clip': meta['boxes']['cropbox'],
        'jpeg_stream_sha256': digest(raw), 'decoded_rgb_sha256': digest(rgb),
        'coordinate_contract': 'IMAGE_GRID_WITH_EXPLICIT_PDF_PAGE_CLIP',
    }


def extract_scan(data: bytes) -> tuple[bytes, dict] | None:
    """Validate an untrusted single-image PDF; malformed evidence fails at 422."""
    try:
        return _extract_scan(data)
    except (PdfReadError, KeyError, TypeError, ValueError, OSError, OverflowError, AttributeError, zlib.error,
            Image.DecompressionBombError) as exc:
        raise ScoreError('Cannot verify embedded PDF image contract') from exc
