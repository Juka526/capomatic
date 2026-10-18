"""Held-out synthetic gate and separately identified score rerun, in that order."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

from scripts.research.gt05_anchor_study import DESIGN, design, evaluate, observe
from scripts.research.gt05_raster_anchor import glyph
from scripts.research.gt04_visual import HEAD, ink_intersections, render
from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes


def topology_controls(font_path):
    design(font_path)
    tt = TTFont(font_path)
    g = tt['glyf'][tt.getBestCmap()[ord(HEAD)]]
    units = (g.xMin, g.yMin, g.xMax, g.yMax)
    font = ImageFont.truetype(str(font_path), 94)
    parts = {}
    checks = {}
    staff = Image.new('L', (512, 512))
    d = ImageDraw.Draw(staff)
    for y in [210, 228, 246, 264, 282]:
        d.line([(60, y), (420, y)], fill=255, width=2)
    parts['staff'] = staff
    for ident, xy in [('n0', (180.375, 246.125)), ('n1', (330.625, 300.375))]:
        head, info = glyph((512, 512), font, HEAD, xy, units, 94 / 1000)
        parts[ident + ':head'] = head
        a = np.array(head)
        ys, xs = np.nonzero(a)
        edge = int(xs.max() - 1)
        start = float(np.median(ys[xs == edge]))
        stem = Image.new('L', (512, 512))
        ImageDraw.Draw(stem).line([(edge, start), (edge, xy[1] - 63)], fill=255, width=2)
        parts[ident + ':stem'] = stem
        checks[ident + '_stem_attachment'] = bool(np.count_nonzero((a > 0) & (np.array(stem) > 0)))
        if ident == 'n0':
            checks['staff_crossing_observed'] = bool(
                np.count_nonzero((a > 0) & (np.array(staff) > 0))
            )
        else:
            ledger = Image.new('L', (512, 512))
            ImageDraw.Draw(ledger).line(
                [(xy[0] - 15.75, xy[1]), (xy[0] + 15.75, xy[1])], fill=255, width=2
            )
            parts[ident + ':ledger'] = ledger
            checks['ledger_contact'] = bool(np.count_nonzero((a > 0) & (np.array(ledger) > 0)))
        checks[ident + '_deterministic'] = (
            glyph((512, 512), font, HEAD, xy, units, 94 / 1000)[0].tobytes() == head.tobytes()
        )
    contacts = ink_intersections(parts)
    checks['no_unintended_collision'] = not any(not c['intentional_contact'] for c in contacts)
    for name, xy in [('clipping', (0, 0)), ('nonfinite', (float('nan'), 200))]:
        try:
            glyph((512, 512), font, HEAD, xy, units, 94 / 1000)
        except ValueError:
            checks[name + '_rejected'] = True
        else:
            checks[name + '_rejected'] = False
    # Analytic control unrelated to font implementation: inclusive 11-pixel square.
    square = Image.new('L', (50, 50))
    ImageDraw.Draw(square).rectangle((10, 10, 20, 20), fill=255)
    checks['positive_known_pixel_center'] = observe(square, (15, 15))['residual'] == [0, 0]
    shifted = Image.new('L', square.size)
    shifted.paste(square, (1, 0))
    checks['negative_one_pixel_error_detected'] = observe(shifted, (15, 15))['residual'] == [1, 0]
    checks['edge_index_distinction'] = observe(square, (15, 15))['bbox_center_edge'] == [15.5, 15.5]
    return {'checks': checks, 'all_pass': all(checks.values()), 'ink_contacts': contacts}


def synthetic(font, root):
    if root.exists():
        raise ValueError('New independent-test directory required')
    # Both designs were frozen before calibration. No reading score positions.
    corrected = evaluate(font, root / 'corrected', 'independent_regression', 'calibrated')
    legacy = evaluate(font, root / 'legacy', 'independent_regression', 'legacy')
    controls = topology_controls(font)
    raw = json.loads((root / 'corrected/results.json').read_text())
    shapes = {}
    for row in raw['rows']:
        shapes.setdefault((row['codepoint'], row['font_size']), set()).add(
            row['measurement']['cropped_alpha_sha256']
        )
    stable = all(len(v) == 1 for v in shapes.values())
    result = {
        'corrected': corrected,
        'legacy': legacy,
        'controls': controls,
        'coverage_bitmap_translation_invariant': stable,
        'design_sha256': sha(DESIGN),
        'algorithm_sha256': sha(Path(__file__).with_name('gt05_raster_anchor.py')),
        'independent_test_code_sha256': sha(Path(__file__)),
        'passed': corrected['case_count'] == 192
        and corrected['pass_count'] == 192
        and stable
        and controls['all_pass'],
        'synthetic_only_not_independent_musical_truth': True,
    }
    dump(root / 'gate.json', result)
    return result


def score_run(font, root, gt04, out):
    if gt04.resolve() == out.resolve() or gt04.resolve() in out.resolve().parents:
        raise ValueError('Output inside historical GT-04 evidence')
    if (out.parent / 'score-run-binding.json').exists():
        raise ValueError('New score run identity required')
    gate = json.loads((root / 'gate.json').read_text())
    if (
        not gate['passed']
        or gate['design_sha256'] != sha(DESIGN)
        or gate['algorithm_sha256'] != sha(Path(__file__).with_name('gt05_raster_anchor.py'))
    ):
        raise ValueError('Independent synthetic gate is not valid')
    design(font)
    frozen = json.loads((gt04 / 'visual-prototype/prototype-freeze.json').read_text())
    current = file_hashes(gt04 / 'visual-prototype')
    current.pop('prototype-freeze.json')
    if current != frozen['files']:
        raise ValueError('Historical GT-04 image/artifact changed')
    from music21 import converter
    from backend.omr_v3.music_guard import validate

    baseline = Path(
        '/private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output/predictions/baseline-exec'
    )
    from scripts.research.ground_truth_02 import verify_inputs

    verify_inputs(baseline.parents[1])
    source = converter.parse(str(baseline / 'source/recognized.musicxml'))
    for name, shift in [('A', -1), ('G', -3)]:
        if not validate(
            source, converter.parse(str(baseline / name / 'transposed.musicxml')), shift, 'key'
        ).ok:
            raise ValueError('Full musical integrity failed')
    inputs = gt04 / 'render-input'
    if json.loads((inputs / 'selection.json').read_text())['selected'] != [3, 32]:
        raise ValueError('Changed source selection')
    verdict = render(inputs, font, out, glyph_renderer=glyph)
    dump(
        out.parent / 'score-run-binding.json',
        {
            'run_id': 'GT05A-score-rerun-01',
            'independent_gate_sha256': sha(root / 'gate.json'),
            'historical_gt04_freeze_sha256': sha(gt04 / 'visual-prototype/prototype-freeze.json'),
            'glyph_algorithm_sha256': sha(Path(__file__).with_name('gt05_raster_anchor.py')),
            'source_selection_sha256': sha(inputs / 'selection.json'),
            'verdict': verdict,
            'old_images_unchanged': True,
        },
    )
    return verdict


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['synthetic', 'score'])
    p.add_argument('--font', type=Path, required=True)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--gt04', type=Path)
    p.add_argument('--out', type=Path)
    a = p.parse_args()
    print(
        synthetic(a.font, a.root)
        if a.mode == 'synthetic'
        else score_run(a.font, a.root, a.gt04, a.out)
    )
