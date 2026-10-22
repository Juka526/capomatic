"""Read retained Audiveris runs against BINARY; never authorize source edits.

A matching run proves binary pixel support, not unique ownership, semantic
correctness, or the execution's coordinate transform. All remain separate gates.
"""
import argparse
import io
import json
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET

import numpy as np
from PIL import Image


def glyph_support(glyph, binary):
    """Measure serialized foreground runs at their stored source coordinates."""
    table = glyph.find('run-table')
    if table is None:
        return {'status': 'UNKNOWN', 'reason': 'RUN_TABLE_MISSING'}
    orientation = table.get('orientation')
    if orientation not in {'VERTICAL', 'HORIZONTAL'}:
        return {'status': 'UNKNOWN', 'reason': 'RUN_ORIENTATION_UNSUPPORTED'}
    width, height = int(table.get('width')), int(table.get('height'))
    x0, y0 = int(glyph.get('left')), int(glyph.get('top'))
    bh, bw = binary.shape
    if width <= 0 or height <= 0 or x0 < 0 or y0 < 0 or x0+width > bw or y0+height > bh:
        return {'status': 'INVALID', 'reason': 'GLYPH_OUTSIDE_BINARY'}
    sequences = table.findall('runs')
    if len(sequences) != (width if orientation == 'VERTICAL' else height):
        return {'status': 'INVALID', 'reason': 'RUN_SEQUENCE_COUNT'}
    supported = total = 0
    for index, sequence in enumerate(sequences):
        cursor = 0
        for run_index, length in enumerate(map(int, (sequence.text or '').split())):
            end = cursor + length
            if length < 0 or end > (height if orientation == 'VERTICAL' else width):
                return {'status': 'INVALID', 'reason': 'RUN_LENGTH_OUTSIDE_GLYPH'}
            if run_index % 2 == 0:
                pixels = (binary[y0+cursor:y0+end, x0+index] if orientation == 'VERTICAL'
                          else binary[y0+index, x0+cursor:x0+end])
                total += length
                supported += int(np.count_nonzero(pixels == 0))
            cursor = end
    return {'status': 'SUPPORTED' if supported == total and total else 'MISMATCH',
            'foreground_samples': total, 'binary_supported_samples': supported,
            'unsupported_samples': total-supported}


def inventory(folder):
    """Read bounded evaluation artifacts saved by ordinary_scan_evidence_server."""
    with zipfile.ZipFile(folder/'recognition.omr') as archive:
        root = ET.fromstring(archive.read('sheet#1/sheet#1.xml'))
        with Image.open(io.BytesIO(archive.read('sheet#1/BINARY.png'))) as image:
            binary = np.asarray(image.convert('L'))
    glyphs = {g.get('id'): {'glyph': g.get('id'), **glyph_support(g, binary)}
              for g in root.findall('glyph-index/glyph')}
    objects = []
    for system in root.findall('page/system'):
        for obj in system.findall('sig/inters/*'):
            bounds = obj.find('bounds')
            objects.append({'page': 1, 'system': system.get('id'), 'measure': None,
                            'object': obj.get('id'), 'kind': obj.tag, 'glyph': obj.get('glyph'),
                            'evidence_region': dict(bounds.attrib) if bounds is not None else 'UNKNOWN',
                            'binary_support': glyphs.get(obj.get('glyph'), {'status': 'UNKNOWN'}),
                            'ownership': 'UNVERIFIED', 'edit_authorized': False})
    return {'geometry_ready': False, 'semantic_ready': False, 'lyric_layer_ready': False,
            'render_ready': False, 'protected_region': 'ENTIRE_SOURCE_PAGE',
            'pixel_support_is_not_ownership': True,
            'glyphs': list(glyphs.values()), 'objects': objects,
            'binary_size': [binary.shape[1], binary.shape[0]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence_root', type=Path)
    args = parser.parse_args()
    for folder in sorted(args.evidence_root.iterdir()):
        if (folder/'recognition.omr').exists():
            report = inventory(folder)
            (folder/'pixel-support.json').write_text(json.dumps(report, indent=2))
            print(folder.name, len(report['objects']), 'unverified objects')


if __name__ == '__main__':
    main()
