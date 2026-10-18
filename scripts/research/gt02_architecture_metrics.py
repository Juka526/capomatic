"""Read-only architecture implications from registered regions and frozen GT-01 plans."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from backend.omr_v4.visual_graph import load_visual_graph, safe_xml
from scripts.research.ground_truth_02 import verify_inputs
from scripts.research.paired_ground_truth_01 import dump, sha
from scripts.research.evaluate_paired_ground_truth_01 import distribution


def audit(root, study):
    if (
        root.resolve() == study.resolve()
        or root.resolve() in study.resolve().parents
        or study.resolve() in root.resolve().parents
    ):
        raise ValueError('Study output must be separate from immutable GT-01 evidence')
    binding = verify_inputs(root)
    reg = json.loads((study / 'measure-registration.json').read_text())
    notes = json.loads((study / 'note-correspondence-diagnostic.json').read_text())
    baseline = root / 'predictions/baseline-exec'
    status = json.loads((baseline / 'status.json').read_text())
    result = {
        'study_type': 'POST_REFERENCE_DIAGNOSTIC_NOT_BLINDED_OR_ACCURACY',
        'binding': binding,
        'track_a': {
            'ink_coverage': status['track_a'],
            'complete_only_unchanged': True,
            'per_shift_masks': {
                n: json.loads((baseline / n / 'track-a-mask-summary.json').read_text())['metrics']
                for n in ['A', 'G']
            },
        },
        'track_b': {},
        'harmonies_by_source_stage': {},
    }
    for name in ['A', 'G']:
        source = reg['pages']['Bb']
        target = reg['pages'][name]
        width_rows = []
        for a, b in zip(source['measures'], target['measures']):
            if (a['identity'], a['system']) != (b['identity'], b['system']):
                raise ValueError('Unresolved physical measure order')
            width_rows.append(
                {
                    'printed_measure': a['printed_measure'],
                    'source_width': a['right']['x'] - a['left']['x'],
                    'reference_width': b['right']['x'] - b['left']['x'],
                    'source_minus_reference_width': (a['right']['x'] - a['left']['x'])
                    - (b['right']['x'] - b['left']['x']),
                }
            )
        frozen = {
            n['semantic_id']: n
            for n in json.loads((baseline / name / 'track-b-geometry.json').read_text())['notes']
            if 'blocked' not in n
        }
        right = {e['id']: e for e in notes['events'][name]}
        graph = load_visual_graph(root / 'references' / name / 'recognized.omr')
        residuals = []
        for pair in notes['comparisons'][name]['pairs']:
            if pair['kind'] != 'NOTE':
                continue
            pred = frozen[pair['left_id']]
            observed = right[pair['right_id']]
            center = graph.symbols[observed['symbol_id']].geometry.center
            residuals.append(
                {
                    'printed_measure': pair['printed_measure'],
                    'source_id': pair['left_id'],
                    'reference_id': pair['right_id'],
                    'dx_source_locked_prediction_minus_reference_detector': pred['target_x']
                    - center[0],
                    'dy_absolute_target_staff_minus_reference_detector': pred[
                        'absolute_target_staff_y'
                    ]
                    - center[1],
                }
            )
        result['track_b'][name] = {
            'measure_widths': width_rows,
            'width_residual_px': distribution(
                [r['source_minus_reference_width'] for r in width_rows]
            ),
            'staff_y_residual_px': distribution(
                [
                    a - b
                    for ss, tt in zip(source['systems'], target['systems'])
                    for a, b in zip(ss['staff_lines_y'], tt['staff_lines_y'])
                ]
            ),
            'candidate_note_x_residual_px': distribution(
                [r['dx_source_locked_prediction_minus_reference_detector'] for r in residuals]
            ),
            'candidate_note_y_residual_px': distribution(
                [r['dy_absolute_target_staff_minus_reference_detector'] for r in residuals]
            ),
            'candidate_notes': residuals,
            'replacement_glyph_anchor': 'UNDEFINED_NOT_INFERRED_FROM_HEAD_CENTER',
            'registered_geometry_certification': 'Raster-corrobated coordinator proposals; independent human approval pending',
            'use_of_reference_for_prediction': 'NONE; frozen source-derived targets only',
            'ledger_repair_anchor_case': 'NOT_TESTED_SOURCE_REPAIRS_ZERO',
            'engraving_differences': 'Measured separately; not musical errors',
            'renderer_b2': False,
        }
    with zipfile.ZipFile(baseline / 'source/audiveris.mxl') as archive:
        paths = [
            p for p in archive.namelist() if p.endswith('.xml') and not p.startswith('META-INF/')
        ]
        if len(paths) != 1:
            raise ValueError('Ambiguous raw MusicXML resource')
        raw = safe_xml(archive.read(paths[0]), musicxml=True)
    result['harmonies_by_source_stage']['RAW_AUDIVERIS_MXL'] = len(raw.findall('.//harmony'))
    for name in ['pre-ledger', 'recognized']:
        xml = safe_xml((baseline / 'source' / (name + '.musicxml')).read_bytes(), musicxml=True)
        result['harmonies_by_source_stage'][name] = len(xml.findall('.//harmony'))
    result['gt01_unchanged'] = verify_inputs(root) == binding
    result['helper_sha256'] = sha(Path(__file__))
    dump(study / 'architecture-feasibility.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gt01', type=Path, required=True)
    parser.add_argument('--study', type=Path, required=True)
    a = parser.parse_args()
    audit(a.gt01, a.study)


if __name__ == '__main__':
    main()
