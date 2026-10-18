"""Post-freeze candidate comparisons. Detector outputs are never reference truth."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from fractions import Fraction
import json
from pathlib import Path
import statistics
import subprocess
import time

from scripts.research.paired_ground_truth_01 import (
    candidate_compare,
    dump,
    file_hashes,
    sha,
    verify_files,
)


def verify_baseline(root):
    manifest = root / 'baseline-manifest.json'
    subprocess.run(
        [
            'openssl',
            'dgst',
            '-sha256',
            '-verify',
            str(root / 'baseline-public.pem'),
            '-signature',
            str(root / 'baseline-manifest.sig'),
            str(manifest),
        ],
        check=True,
        capture_output=True,
    )
    frozen = json.loads(manifest.read_text())
    if frozen['phase'] != 'SOURCE_ONLY_PREDICTIONS_FROZEN':
        raise ValueError('Unfrozen predictions')
    verify_files(root / 'predictions', frozen['prediction_files'])
    return frozen


def distribution(values):
    return {
        'count': len(values),
        'mean': statistics.mean(values) if values else None,
        'median': statistics.median(values) if values else None,
        'max_absolute': max(map(abs, values)) if values else None,
    }


def reference_matches(folder, graph):
    from backend.omr_v4.matcher import read_semantics, match_notes
    from backend.omr_v4.provenance import capture_ledger_repairs, match_with_provenance

    raw = read_semantics(folder / 'pre-ledger.musicxml')
    corrected = read_semantics(folder / 'recognized.musicxml')
    report = json.loads((folder / 'recognition-report.json').read_text())
    direct = match_notes(raw, graph)
    repairs = capture_ledger_repairs(
        raw, corrected, direct, report['repairs']['ledger_notes_fixed']
    )
    return match_with_provenance(raw, corrected, graph, direct, repairs)


def chords(path):
    from music21 import converter, harmony, stream
    from backend.omr_v3.chords import chord_text
    from backend.chords.parser import parse_chord

    result = {}
    score = converter.parse(str(path))
    for pi, part in enumerate(score.parts):
        for mi, m in enumerate(part.getElementsByClass(stream.Measure)):
            for h in m.recurse().getElementsByClass(harmony.ChordSymbol):
                identity = (
                    pi,
                    mi,
                    m.measureNumberWithSuffix(),
                    str(Fraction(h.getOffsetInHierarchy(m))),
                )
                if identity in result:
                    raise ValueError('Duplicate harmony correspondence candidate')
                try:
                    parsed = asdict(parse_chord(chord_text(h)))
                except ValueError:
                    parsed = None
                result[identity] = {
                    'text': chord_text(h),
                    'parsed': parsed,
                    'kind': h.chordKind,
                    'root_pc': h.root().pitchClass if h.root() else None,
                    'bass_pc': h.bass().pitchClass if h.bass() else None,
                    'modifications': [
                        (d.modType, d.degree, d.interval.chromatic.semitones)
                        for d in h.getChordStepModifications()
                    ],
                }
    return result


def chord_candidates(left, right, shift):
    a, b = chords(left), chords(right)
    rows = []
    for identity in sorted(a.keys() & b.keys()):
        x, y = a[identity], b[identity]
        px, py = x['parsed'], y['parsed']
        rows.append(
            {
                'identity': identity,
                'left': x,
                'right': y,
                'root_interval_agrees': x['root_pc'] is not None
                and y['root_pc'] is not None
                and (y['root_pc'] - x['root_pc']) % 12 == shift % 12,
                'parsed_quality_extensions_agree': (
                    None
                    if px is None or py is None
                    else (px['quality'], px['extensions']) == (py['quality'], py['extensions'])
                ),
                'slash_presence_agrees': (
                    None
                    if px is None or py is None
                    else (px['bass'] is None) == (py['bass'] is None)
                ),
                'bass_interval_agrees': (
                    None
                    if x['bass_pc'] is None or y['bass_pc'] is None
                    else (y['bass_pc'] - x['bass_pc']) % 12 == shift % 12
                ),
            }
        )
    return {
        'status': 'UNVERIFIED_RECOGNIZER_AGREEMENT_NOT_TRUTH',
        'left_harmonies': len(a),
        'right_harmonies': len(b),
        'unique_identity_pairs': len(rows),
        'unmatched_left': len(a.keys() - b.keys()),
        'unmatched_right': len(b.keys() - a.keys()),
        'events': rows,
    }


def graph_metrics(graph):
    return {
        'pages': [(p.width, p.height) for p in graph.pages],
        'systems': len(graph.systems),
        'staves': len(graph.staves),
        'part_measure_regions': len(graph.measures),
        'symbols': dict(sorted(Counter(s.kind for s in graph.symbols.values()).items())),
        'protected_regions': len(graph.text_protected_regions),
        'invalid_geometry': graph.invalid_geometry_count,
    }


def geometry_candidates(source_folder, prediction, reference, comparison):
    from backend.omr_v4.visual_graph import load_visual_graph

    src = load_visual_graph(source_folder / 'recognized.omr')
    ref = load_visual_graph(reference / 'recognized.omr')
    matches = reference_matches(reference, ref)
    heads = {
        m.note.id: ref.symbols[m.head_id].geometry.center
        for m in matches.notes
        if m.status == 'MATCHED'
    }
    notes = {
        n['semantic_id']: n
        for n in json.loads((prediction / 'track-b-geometry.json').read_text())['notes']
        if 'blocked' not in n
    }
    rows = []
    for pair in comparison['events']:
        a, b = notes.get(pair['source_id']), heads.get(pair['reference_id'])
        if a and b:
            rows.append(
                {
                    'source_id': pair['source_id'],
                    'reference_id': pair['reference_id'],
                    'dx_predicted_minus_reference_detected': a['target_x'] - b[0],
                    'dy_absolute_staff_prediction_minus_reference_detected': a[
                        'absolute_target_staff_y'
                    ]
                    - b[1],
                    'candidate_pitch_interval_agrees': pair['interval_agrees'],
                }
            )
    widths = []
    staff_deltas = []
    system_deltas = []
    if len(src.measures) == len(ref.measures) and all(
        (a.number, a.part) == (b.number, b.part) for a, b in zip(src.measures, ref.measures)
    ):
        widths = [
            (a.bounds[2] - a.bounds[0]) - (b.bounds[2] - b.bounds[0])
            for a, b in zip(src.measures, ref.measures)
            if a.bounds and b.bounds
        ]
    if len(src.staves) == len(ref.staves):
        for a, b in zip(src.staves, ref.staves):
            if len(a.lines) == len(b.lines) == 5:
                staff_deltas.extend(
                    statistics.mean(p[1] for p in la) - statistics.mean(p[1] for p in lb)
                    for la, lb in zip(a.lines, b.lines)
                )
    if len(src.systems) == len(ref.systems):
        system_deltas = [
            a.bounds[1] - b.bounds[1]
            for a, b in zip(src.systems, ref.systems)
            if a.bounds and b.bounds
        ]
    lyric_a = [r for r in src.text_protected_regions if 'lyric' in r.kind]
    lyric_b = [r for r in ref.text_protected_regions if 'lyric' in r.kind]
    return {
        'status': 'DETECTOR_COORDINATE_CANDIDATES_NOT_PHYSICAL_GROUND_TRUTH',
        'source_graph': graph_metrics(src),
        'reference_graph': graph_metrics(ref),
        'notehead_x_residual_px': distribution(
            [r['dx_predicted_minus_reference_detected'] for r in rows]
        ),
        'target_y_residual_px': distribution(
            [r['dy_absolute_staff_prediction_minus_reference_detected'] for r in rows]
        ),
        'measure_width_residual_px': distribution(widths),
        'staff_mean_y_residual_px': distribution(staff_deltas),
        'system_top_y_residual_px': distribution(system_deltas),
        'events': rows,
        'geometry_correspondence': 'Exact semantic identity for note candidates; graph order for same-count staves/systems; not adjudicated physical correspondence. Legitimate re-engraving differences are not musical errors.',
        'lyric_protection_regions': [len(lyric_a), len(lyric_b)],
        'lyric_baseline_coordinate_metric': 'UNKNOWN: OCR line/item segmentation is not independent baseline annotation; no forced pairing',
        'protected_pixel_preservation': 'Original source digest unchanged. No composite score exists; source-vs-reference pixel equality is not a preservation metric.',
        'chord_placement_width_accidental_beam_curve_completeness': 'UNKNOWN: missing recognized symbols and no complete renderer; not scored from head centers',
    }


def run(root):
    from backend.omr_v3.music_guard import validate
    from music21 import converter

    start = time.monotonic()
    frozen = verify_baseline(root)
    baseline = root / 'predictions/baseline-exec'
    refs = root / 'references'
    dest = root / 'reference-evaluation'
    comparisons = {}
    for name, shift in [('A', -1), ('G', -3)]:
        original = baseline / 'source/recognized.musicxml'
        reference = refs / name / 'recognized.musicxml'
        recognized = candidate_compare(original, reference, shift)
        predicted = candidate_compare(baseline / name / 'transposed.musicxml', reference, 0)
        for row in predicted['events']:
            row['written_spelling_equal'] = row['source_pitch'] == row['reference_pitch']
        comparisons[name] = {
            'source_to_reference': recognized,
            'frozen_prediction_to_reference': predicted,
            'harmony_candidates': chord_candidates(
                baseline / name / 'transposed.musicxml', reference, 0
            ),
            'reference_full_guard_candidate': validate(
                converter.parse(str(original)), converter.parse(str(reference)), shift, 'key'
            ).to_dict(),
        }
        comparisons[name]['geometry_candidates'] = geometry_candidates(
            baseline / 'source', baseline / name, refs / name, recognized
        )
        comparisons[name]['verified_alignment'] = {
            'status': 'UNKNOWN_UNADJUDICATED_MEASURE_CORRESPONDENCE',
            'ground_truth_geometry_denominator': 0,
            'cause': 'Reference measure segmentation differs from source; identical exported indices may name different printed measures. Raw candidate residuals are forensic alarms, not musical/geometric error estimates.',
        }
    comparisons['A_to_G'] = {
        'notes': candidate_compare(
            refs / 'A/recognized.musicxml', refs / 'G/recognized.musicxml', -2
        ),
        'harmony_candidates': chord_candidates(
            refs / 'A/recognized.musicxml', refs / 'G/recognized.musicxml', -2
        ),
        'full_guard_candidate': validate(
            converter.parse(str(refs / 'A/recognized.musicxml')),
            converter.parse(str(refs / 'G/recognized.musicxml')),
            -2,
            'key',
        ).to_dict(),
    }
    verify_baseline(root)
    result = {
        'baseline_manifest_sha256': sha(root / 'baseline-manifest.json'),
        'reference_file_hashes': file_hashes(refs),
        'reference_raster_hashes': file_hashes(root / 'reference-input'),
        'comparisons': comparisons,
        'automated_reference_ground_truth_denominator': 0,
        'evaluator_sha256': sha(Path(__file__)),
        'raw_candidate_residuals_are_not_accuracy_or_verified_correspondence': True,
        'accuracy_percentage': None,
        'unverified_cases': 'Every automated note/chord/geometry pair until independent adjudication; full-reference consistency not established by common recognizer agreement',
        'prediction_regeneration': False,
        'runtime_seconds': time.monotonic() - start,
    }
    dump(dest / 'candidate-comparison.json', result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    a = p.parse_args()
    r = run(a.root)
    for name, row in r['comparisons'].items():
        c = row.get('source_to_reference', row.get('notes'))
        print(name, {k: v for k, v in c.items() if k != 'events'})


if __name__ == '__main__':
    main()
