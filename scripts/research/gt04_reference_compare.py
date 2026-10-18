"""Post-freeze reference comparison only; never regenerates/tunes predictions."""

import argparse
import json
from pathlib import Path

from PIL import Image

from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes
from scripts.research.gt04_visual import panel_label


def compare(prototype, gt01, gt02, out):
    if out.exists() or prototype.resolve() in out.resolve().parents:
        raise ValueError('Separate new comparison directory required')
    for immutable in [gt01, gt02]:
        if out.resolve() == immutable.resolve() or immutable.resolve() in out.resolve().parents:
            raise ValueError('Comparison output inside immutable evidence')
    freeze = json.loads((prototype / 'prototype-freeze.json').read_text())
    current = file_hashes(prototype)
    current.pop('prototype-freeze.json')
    if current != freeze['files']:
        raise ValueError('Frozen prototype changed or unexpected file added')
    for name, digest in freeze['files'].items():
        if sha(prototype / name) != digest:
            raise ValueError('Frozen prototype changed')
    metrics = json.loads((prototype / 'rendering-metrics.json').read_text())
    # Only here, AFTER prediction hash verification, open reference evidence.
    diagnostic = json.loads((gt02 / 'note-correspondence-diagnostic.json').read_text())
    registration = json.loads((gt02 / 'measure-registration.json').read_text())
    out.mkdir(parents=True)
    report = {
        'study': 'POST_REFERENCE_ACCESS_DEVELOPMENT_NOT_ACCURACY',
        'prototype_freeze_sha256': sha(prototype / 'prototype-freeze.json'),
        'independent_human_denominator': 0,
        'reference_recognizer_is_not_ground_truth': True,
        'reference_edited': False,
        'prediction_regenerated': False,
        'targets': {},
    }
    for key in ['A', 'G']:
        events = {e['id']: e for e in diagnostic['events'][key]}
        pairs = {p['left_id']: p for p in diagnostic['comparisons'][key]['pairs']}
        page = Image.open(gt01 / 'reference-input' / f'{key}.png')
        rows = []
        panels = []
        for record in metrics['metrics']:
            if record['target'] != key:
                continue
            number = record['measure']
            for predicted in record['events']:
                pair = pairs.get(predicted['semantic_id'])
                if pair is None:
                    rows.append({'id': predicted['semantic_id'], 'status': 'UNKNOWN'})
                    continue
                observed = events[pair['right_id']]
                bbox = observed['bbox']
                center = [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2]
                rows.append(
                    {
                        'id': predicted['semantic_id'],
                        'measure': number,
                        'kind': predicted['kind'],
                        'status': 'ALGORITHMIC_CANDIDATE_NOT_HUMAN_TRUTH',
                        'duration_equal': predicted['duration'] == observed['duration'],
                        'spelling_equal': (
                            predicted.get('target_pitch') == observed.get('pitch')
                            if predicted['kind'] == 'NOTE'
                            else None
                        ),
                        'raster_center_minus_reference_detected_center': [
                            predicted['raster_ink_bbox_center'][i] - center[i] for i in [0, 1]
                        ],
                        'reference_observation': observed,
                    }
                )
            reg = next(
                r for r in registration['pages'][key]['measures'] if r['printed_measure'] == number
            )
            source_reg = next(
                r for r in registration['pages']['Bb']['measures'] if r['printed_measure'] == number
            )
            y0 = record['viewport_page_coordinates'][1]
            y1 = record['viewport_page_coordinates'][3]
            crop = page.crop((int(reg['left']['x']) - 8, y0, int(reg['right']['x']) + 9, y1))
            panels.append(
                panel_label(crop, f'REFERENCE {key} source evidence ONLY; printed {number}')
            )
            reg['gt04_width_difference_source_minus_reference'] = (
                source_reg['right']['x'] - source_reg['left']['x']
            ) - (reg['right']['x'] - reg['left']['x'])
        image = Image.new(
            'RGB', (max(p.width for p in panels), sum(p.height for p in panels) + 12), 'white'
        )
        y = 0
        for p in panels:
            image.paste(p, (0, y))
            y += p.height + 12
        image.save(out / f'reference-{key.lower()}-context.png')
        report['targets'][key] = {
            'events': rows,
            'pitched_candidates': sum(r.get('kind') == 'NOTE' for r in rows),
            'pitch_spelling_agreements': sum(r.get('spelling_equal') is True for r in rows),
            'duration_agreements': sum(r.get('duration_equal') is True for r in rows),
            'harmonic_comparison': 'UNVERIFIED: no predicted chord layer; source missing harmonies remain incomplete',
            'lyric_comparison': 'No target composite; original Bb visible crop pixels equal. Reference lyric layout may differ; independent ownership/complete text denominator absent.',
        }
    dump(out / 'reference-comparison.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['prototype', 'gt01', 'gt02', 'out']:
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    compare(a.prototype, a.gt01, a.gt02, a.out)
