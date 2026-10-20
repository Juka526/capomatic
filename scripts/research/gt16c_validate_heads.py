"""Post-freeze check of all 60 immutable head masks against the refined composite."""

import argparse
from fractions import Fraction
from pathlib import Path

import numpy as np
from music21 import converter, stream
from PIL import Image

from scripts.research.gt11_complete_measure import events_of, read, require
from scripts.research.gt16c_optical_engraving import BASE, GT13A2, GT14, GT15, GT16, SOURCE_DIR
from scripts.research.paired_ground_truth_01 import dump, line_y, sha

GT11 = Path('/private/tmp/capomatic-v4-gt11/gt11-output')


def run(out):
    freeze = read(out / 'prediction-freeze.json')
    require(all(sha(out / n) == h for n, h in freeze['files'].items()), 'Prediction freeze changed')
    graph = read(SOURCE_DIR / 'visual-graph.json')
    reports = []
    for target in ['A', 'G']:
        score = converter.parse(str(BASE / f'{target}-transposed.musicxml'))
        ms = list(score.parts[0].getElementsByClass(stream.Measure))
        old = Image.open(BASE / f'{target}-combined-alpha.png')
        new = Image.open(out / f'{target}-refined-alpha.png')
        # This frozen candidate chose the native layout; no system translation is permitted here.
        layout = next(
            r for r in read(out / 'optical-spacing-metrics.json') if r['target'] == target
        )
        require(
            layout['selected_layout']['system_offsets'] == [0, 0, 0, 0],
            'Different layout needs offset-aware validation',
        )
        rows = []
        for directory in [GT13A2, GT14, GT15, GT16]:
            for record in read(directory / 'source-event-inventory.json')['measures']:
                number = record['printed_measure']
                staff = graph['staves'][(number - 1) // 4]
                for e in record['events']:
                    if not e.get('pitch'):
                        continue
                    eid = e.get('id', e.get('event_id'))
                    matches = [
                        n
                        for n in events_of(ms[number - 1])
                        if Fraction(n.getOffsetInHierarchy(ms[number - 1])) == Fraction(e['onset'])
                    ]
                    require(
                        len(matches) == 1 and matches[0].isNote,
                        'Head semantic correspondence changed',
                    )
                    basename = eid.replace(':', '_') + '_head'
                    paths = [
                        directory / f'{target}-{basename}{suffix}'
                        for suffix in ['.png', '-alpha.png']
                    ]
                    path = next((p for p in paths if p.exists()), None)
                    if number == 3:
                        path = GT11 / f'components/{target}/{basename}.png'
                        key = str(path.relative_to(GT11))
                        require(
                            sha(path) == read(GT11 / 'prediction-freeze.json')['files'][key],
                            'GT11 cached head changed',
                        )
                    require(path is not None and path.exists(), 'Missing frozen head: ' + eid)
                    mask = Image.open(path)
                    b = mask.getbbox()
                    support = np.asarray(mask.crop(b)) > 0
                    require(
                        np.array_equal(
                            np.asarray(old.crop(b))[support], np.asarray(new.crop(b))[support]
                        ),
                        'Head alpha changed in composite',
                    )
                    sourcebox = e['source_bbox']
                    x = (sourcebox[0] + sourcebox[2]) / 2
                    y = (
                        line_y(staff['lines'][2], x)
                        + (35 - matches[0].pitch.diatonicNoteNum) * staff['interline'] / 2
                    )
                    residual = [(b[0] + b[2] - 1) / 2 - x, (b[1] + b[3] - 1) / 2 - y]
                    require(max(map(abs, residual)) <= 0.5, 'Head anchor failed: ' + eid)
                    rows.append(
                        {
                            'event_id': eid,
                            'printed_measure': number,
                            'target_pitch': matches[0].pitch.nameWithOctave,
                            'requested_staff_coordinate': [x, y],
                            'actual_head_bbox': b,
                            'residual': residual,
                            'mask_path': str(path),
                            'mask_sha256': sha(path),
                            'head_support_pixels_unchanged': True,
                        }
                    )
        require(
            len(rows) == len({r['event_id'] for r in rows}) == 60,
            '60 unique pitched events required',
        )
        from scripts.research.gt14e_two_system_validation import GT13A3, GT12, GT14A
        from scripts.research.gt16c_optical_engraving import GT15B

        chord_paths = [GT13A3 / f'{target}-new-chord-alpha.png', GT12 / f'{target}-chord-alpha.png']
        chord_paths += [GT14A / f'{target}-chord-m{m}-alpha.png' for m in [5, 6, 7]]
        chord_paths += [GT15B / f'{target}-chord-m{m}-alpha.png' for m in [10, 12]]
        chord_paths += [BASE / f'{target}-chord-m{m}-alpha.png' for m in [14, 15, 16]]
        for path in chord_paths:
            mask = Image.open(path)
            box = mask.getbbox()
            support = np.asarray(mask.crop(box)) > 0
            require(
                np.array_equal(
                    np.asarray(old.crop(box))[support], np.asarray(new.crop(box))[support]
                ),
                'Chord ink changed in composite',
            )
        reports.append(
            {
                'target': target,
                'heads_checked': 60,
                'chord_masks_checked': 10,
                'chord_alpha_preserved': True,
                'max_residual_per_axis_px': max(max(map(abs, r['residual'])) for r in rows),
                'events': rows,
            }
        )
    dump(
        out / 'all-head-anchor-preservation.json',
        {
            'prediction_freeze_sha256': sha(out / 'prediction-freeze.json'),
            'validator_sha256': sha(Path(__file__)),
            'targets': reports,
        },
    )


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    run(p.parse_args().out)
