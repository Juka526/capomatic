"""Lossless raster PDF bridge using installed system pypdf, separate from font runtime."""

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, NumberObject, DictionaryObject, DecodedStreamObject


def export(image, path):
    if image.mode != 'RGB':
        raise ValueError('PDF requires RGB')
    if path.exists():
        raise ValueError('Do not overwrite a PDF')
    w, h = image.size
    factor = 72 / 300
    writer = PdfWriter()
    page = writer.add_blank_page(width=w * factor, height=h * factor)
    data = DecodedStreamObject()
    data.set_data(image.tobytes())
    data.update(
        {
            NameObject('/Type'): NameObject('/XObject'),
            NameObject('/Subtype'): NameObject('/Image'),
            NameObject('/Width'): NumberObject(w),
            NameObject('/Height'): NumberObject(h),
            NameObject('/ColorSpace'): NameObject('/DeviceRGB'),
            NameObject('/BitsPerComponent'): NumberObject(8),
        }
    )
    ref = writer._add_object(data.flate_encode())
    page[NameObject('/Resources')] = DictionaryObject(
        {NameObject('/XObject'): DictionaryObject({NameObject('/Im0'): ref})}
    )
    stream = DecodedStreamObject()
    stream.set_data(f'q {w*factor} 0 0 {h*factor} 0 0 cm /Im0 Do Q'.encode())
    page[NameObject('/Contents')] = writer._add_object(stream)
    writer.add_metadata(
        {
            '/Title': 'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING'
        }
    )
    with path.open('wb') as f:
        writer.write(f)
    return inspect(path)


def inspect(path):
    reader = PdfReader(path)
    page = reader.pages[0]
    obj = page['/Resources']['/XObject']['/Im0'].get_object()
    return {
        'pages': len(reader.pages),
        'page_size_points': [float(page.mediabox.width), float(page.mediabox.height)],
        'raster_dpi': 300,
        'encoding': str(obj['/Filter']),
        'pixel_size': [int(obj['/Width']), int(obj['/Height'])],
        'rgb_sha256': hashlib.sha256(obj.get_data()).hexdigest(),
        'title': reader.metadata.title,
        'coordinate_transform': 'PNG x/y scaled72/300; header140px outside source registration',
        'runtime': sys.executable,
        'pypdf': __import__('pypdf').__version__,
    }


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path)
    p.add_argument('--inspect', type=Path)
    a = p.parse_args()
    if a.inspect:
        result = inspect(a.inspect)
    else:
        result = export(Image.open(io.BytesIO(sys.stdin.buffer.read())), a.output)
    print(json.dumps(result, sort_keys=True))
