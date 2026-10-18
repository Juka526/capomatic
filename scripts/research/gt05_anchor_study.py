"""Frozen synthetic glyph placements; no score/reference inputs to calibration."""

import argparse
import hashlib
import inspect
import itertools
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, features
from fontTools.ttLib import TTFont

from scripts.research.gt04_visual import glyph as legacy_glyph
from scripts.research.paired_ground_truth_01 import dump, sha

DESIGN = Path(__file__).parents[2] / 'docs/V4_GT05_ANCHOR_PREREGISTRATION.json'


def design(font):
    spec = json.loads(DESIGN.read_text())
    if sha(font) != spec['font_sha256']:
        raise ValueError('Font hash mismatch')
    return spec


def cases(spec, family):
    subset = spec[family]
    for code, size, origin, dx, dy in itertools.product(
        spec['glyphs'], subset['font_sizes'], subset['origins'], subset['phases'], subset['phases']
    ):
        yield {'codepoint': code, 'font_size': size, 'target': [origin[0] + dx, origin[1] + dy]}


def observe(mask, target):
    a = np.asarray(mask)
    ys, xs = np.nonzero(a)
    if not len(xs):
        raise ValueError('No actual ink')
    bbox = [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]
    center = [(bbox[0] + bbox[2] - 1) / 2, (bbox[1] + bbox[3] - 1) / 2]
    alpha = a.astype(float)
    mass = alpha.sum()
    centroid = [
        float((alpha.sum(axis=0) * np.arange(a.shape[1])).sum() / mass),
        float((alpha.sum(axis=1) * np.arange(a.shape[0])).sum() / mass),
    ]
    cropped = mask.crop(bbox)
    return {
        'bbox': bbox,
        'bbox_center_index': center,
        'bbox_center_edge': [c + 0.5 for c in center],
        'coverage_centroid': centroid,
        'residual': [c - t for c, t in zip(center, target)],
        'centroid_residual': [c - t for c, t in zip(centroid, target)],
        'ink_size': list(cropped.size),
        'cropped_alpha_sha256': hashlib.sha256(cropped.tobytes()).hexdigest(),
        'nonzero_pixels': len(xs),
        'nonbinary_pixels': int(np.count_nonzero((a > 0) & (a < 255))),
    }


def evaluate(font_path, out, family, implementation):
    if out.exists():
        raise ValueError('New output required')
    spec = design(font_path)
    tt = TTFont(font_path)
    cmap = tt.getBestCmap()
    upm = tt['head'].unitsPerEm
    if implementation == 'calibrated':
        from scripts.research.gt05_raster_anchor import glyph as method
    else:
        method = legacy_glyph
    rows = []
    for item in cases(spec, family):
        char = chr(item['codepoint'])
        g = tt['glyf'][cmap[item['codepoint']]]
        units = (g.xMin, g.yMin, g.xMax, g.yMax)
        size = item['font_size']
        font = ImageFont.truetype(str(font_path), size)
        mask, info = method(tuple(spec['canvas']), font, char, item['target'], units, size / upm)
        measured = observe(mask, item['target'])
        again, _ = method(tuple(spec['canvas']), font, char, item['target'], units, size / upm)
        deterministic = again.tobytes() == mask.tobytes()
        # This scorer reads actual pixels, not the implementation's residual field.
        rows.append(
            {
                **item,
                'outline_bounds_font_units': units,
                'outline_center_font_units': [(units[0] + units[2]) / 2, (units[1] + units[3]) / 2],
                'baseline': info.get('baseline'),
                'measurement': measured,
                'pass': all(abs(x) <= 0.5 for x in measured['residual']) and deterministic,
                'deterministic': deterministic,
            }
        )
    out.mkdir(parents=True)
    result = {
        'family': family,
        'implementation': implementation,
        'font_sha256': sha(font_path),
        'design_sha256': sha(DESIGN),
        'code_sha256': sha(Path(__file__)),
        'implementation_sha256': sha(Path(inspect.getfile(method))),
        'case_count': len(rows),
        'pass_count': sum(r['pass'] for r in rows),
        'max_per_axis': [max(abs(r['measurement']['residual'][i]) for r in rows) for i in [0, 1]],
        'max_centroid_residual': [
            max(abs(r['measurement']['centroid_residual'][i]) for r in rows) for i in [0, 1]
        ],
        'rows': rows,
        'independent_human_labels': 0,
        'optical_center': 'UNDEFINED',
    }
    dump(out / 'results.json', result)
    dump(
        out / 'backend.json',
        {
            'pillow_version': Image.__version__,
            'freetype_version': features.version_module('freetype2'),
            'ImageDraw.py_sha256': sha(Path(inspect.getfile(ImageDraw))),
            'ImageFont.py_sha256': sha(Path(inspect.getfile(ImageFont))),
            'getmask2_doc_fractional_start': 'Pillow documents fractional start may change rendering.',
        },
    )
    return {
        k: result[k] for k in ['case_count', 'pass_count', 'max_per_axis', 'max_centroid_residual']
    }


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--font', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--family', choices=['calibration', 'independent_regression'], required=True)
    p.add_argument('--implementation', choices=['legacy', 'calibrated'], required=True)
    a = p.parse_args()
    print(evaluate(a.font, a.out, a.family, a.implementation))
