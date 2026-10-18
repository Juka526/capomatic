"""Offline B1 coordinate audit. Annotations only; never replacement notation.

Run from repository root with --inputs MANIFEST --registration JSON --out DIR.
Registration must already exist. This helper never selects/reselects excerpts.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import resource
import time
from pathlib import Path

from backend.omr_v4.matcher import read_semantics
from backend.omr_v4.plan import to_data
from backend.omr_v4.visual_graph import load_visual_graph


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + '\n')


def verify_inputs(manifest):
    data = json.loads(manifest.read_text())
    root = Path(data['input_root'])
    for name, expected in data['files'].items():
        if digest(root / name) != expected:
            raise ValueError(f'Input hash mismatch: {name}')
    return root, {'verified_files': len(data['files']), 'manifest_sha256': digest(manifest)}


def line_y(points, x):
    """Interpolate original staff polyline; never fit or straighten the staff."""
    if (
        not math.isfinite(x)
        or len(points) < 2
        or any(not math.isfinite(v) for point in points for v in point)
        or any(b[0] <= a[0] for a, b in zip(points, points[1:]))
    ):
        raise ValueError('Invalid/nonfinite staff polyline')
    if x < points[0][0] or x > points[-1][0]:
        raise ValueError('Head outside original staff polyline')
    for a, b in zip(points, points[1:]):
        if a[0] <= x <= b[0] and b[0] > a[0]:
            return a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])
    raise ValueError('Invalid staff polyline')


def absolute_target_y(staff, x, target_staff_pitch):
    if target_staff_pitch is None or not math.isfinite(target_staff_pitch):
        raise ValueError('Unknown target staff pitch')
    if (
        not staff.valid
        or len(staff.lines) != 5
        or not math.isfinite(staff.interline)
        or staff.interline <= 0
    ):
        raise ValueError('Invalid/nonfinite staff geometry')
    result = line_y(staff.lines[2], x) + target_staff_pitch * staff.interline / 2
    if not math.isfinite(result):
        raise ValueError('Nonfinite target geometry')
    return result


def overlap(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def changed_pixel_count(original, annotated):
    from PIL import ImageChops

    if original.mode != annotated.mode or original.size != annotated.size:
        raise ValueError('Pixel comparison requires matching mode and dimensions')
    bands = ImageChops.difference(original, annotated).split()
    maximum = bands[0]
    for band in bands[1:]:
        maximum = ImageChops.lighter(maximum, band)
    return sum(count for value, count in enumerate(maximum.histogram()) if value != 0)


def validate_output_directory(out, root):
    output, evidence = out.resolve(), root.resolve()
    if output == evidence or evidence in output.parents or output in evidence.parents:
        raise ValueError('Output must not modify the evidence tree')
    if out.exists() and any(
        p.is_symlink() or (p.is_file() and p.stat().st_nlink > 1) for p in out.iterdir()
    ):
        raise ValueError('Output contains a symlink or hardlink alias')


def run(manifest, registration, out):
    from PIL import Image, ImageDraw
    from music21 import converter, harmony
    from backend.omr_v3.music_guard import validate, _measure_content
    from backend.omr_v3.transpose import transpose_score

    started = time.perf_counter()
    root, verified = verify_inputs(manifest)
    reg = json.loads(registration.read_text())
    registration_hash = digest(registration)
    if reg['input_manifest_sha256'] != digest(manifest):
        raise ValueError('Registration input binding mismatch')
    validate_output_directory(out, root)
    frozen_hash = registration.with_suffix('.sha256').read_text().strip()
    if registration_hash != frozen_hash:
        raise ValueError('Frozen registration hash mismatch')
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / 'input-verification-before.json', verified)
    graph = load_visual_graph(root / 'recognized.omr')
    plan = json.loads((root / 'plan.json').read_text())
    source = read_semantics(root / 'recognized.musicxml')
    target = read_semantics(root / 'transposed.musicxml')
    targets = {a.id: b for a, b in zip(source.notes, target.notes)}
    if len(source.notes) != len(target.notes) or any(
        a.identity != b.identity for a, b in zip(source.notes, target.notes)
    ):
        raise ValueError('Semantic identity changed')
    staff_by_id = {s.id: s for s in graph.staves}
    matches = {n['note']['id']: n for n in plan['matches']['notes']}
    moves = {n['semantic_id']: n for n in plan['note_moves']}
    image = Image.open(root / 'source.png').convert('RGB')
    assert len(graph.pages) == 1
    assert image.size == (graph.pages[0].width, graph.pages[0].height)
    before = converter.parse(str(root / 'recognized.musicxml'))
    after = converter.parse(str(root / 'transposed.musicxml'))
    if len(before.parts) != 1 or len(after.parts) != 1:
        raise ValueError('This narrowly scoped jayu helper requires one part')
    full = validate(before, after, -2, 'key')
    # Re-run the unchanged V3 transposer in memory to locate export/semantic issues.
    import copy

    fresh = copy.deepcopy(before)
    summary = transpose_score(fresh, -2)
    fresh_guard = validate(before, fresh, -2, 'key', summary)
    chord_details = []
    for a, b in zip(_measure_content(before), _measure_content(after)):
        if a[2] and any(ca[4] != cb[4] or ca[3] != cb[3] for ca, cb in zip(a[2], b[2])):
            ma = before.parts[0].measure(int(a[0]))
            mb = after.parts[0].measure(int(b[0]))
            chord_details.append(
                {
                    'measure': a[0],
                    'before': [to_data(c) for c in a[2]],
                    'after': [to_data(c) for c in b[2]],
                    'source_figures': [
                        c.figure for c in ma.recurse().getElementsByClass(harmony.ChordSymbol)
                    ],
                    'target_figures': [
                        c.figure for c in mb.recurse().getElementsByClass(harmony.ChordSymbol)
                    ],
                }
            )
    write_json(
        out / 'fresh-full-integrity.json',
        {
            'existing_xml_full_guard': full.to_dict(),
            'fresh_unchanged_v3_transpose_full_guard': fresh_guard.to_dict(),
            'fresh_transposition_summary': summary,
            'chord_investigation': chord_details,
        },
    )
    all_rows, excerpts = [], []
    for excerpt in reg['excerpts']:
        num = excerpt['measure_number']
        ids = excerpt['semantic_ids']
        rows = []
        for ident in ids:
            match, move, note = matches[ident], moves[ident], targets[ident]
            if match['status'] != 'MATCHED' or move['source_head_id'] != match['head_id']:
                raise ValueError('Frozen correspondence mismatch')
            head = graph.symbols[match['head_id']]
            staff = staff_by_id[head.staff]
            x, raw_y = head.geometry.center
            if note.staff_pitch is None:
                raise ValueError('Unknown clef/pitch position')
            # Absolute staff position independently anchors corrected target semantics.
            mid_y = line_y(staff.lines[2], x)
            expected_y = absolute_target_y(staff, x, note.staff_pitch)
            if not 0 <= expected_y < image.height:
                raise ValueError('Target geometry outside original page')
            raw_pitch_y = mid_y + head.pitch_position * staff.interline / 2
            box = head.geometry.region
            assert box is not None
            delta = expected_y - raw_y
            rows.append(
                {
                    'semantic_id': ident,
                    'head_id': head.id,
                    'measure_number': num,
                    'staff': staff.id,
                    'ownership': match['ownership_basis'],
                    'source_pitch': move['source_pitch'],
                    'target_pitch': note.pitch,
                    'target_staff_pitch': note.staff_pitch,
                    'raw_visual_staff_pitch': head.pitch_position,
                    'source_xy': [x, raw_y],
                    'target_xy': [x, expected_y],
                    'expected_displacement_px': delta,
                    'raw_pitch_center_residual_px': raw_y - raw_pitch_y,
                    'existing_plan_target_y': move['target_y'],
                    'existing_plan_absolute_y_error_px': move['target_y'] - expected_y,
                    'target_head_envelope': [box[0], box[1] + delta, box[2], box[3] + delta],
                    'existing_plan_blockers': move['blockers'],
                }
            )
        measure = next(m for m in graph.measures if m.number == num)
        heads = set(excerpt['head_ids'])
        selected_beams = [b for b in plan['beam_groups'] if heads.intersection(b['heads'])]
        selected_curves = [s for s in plan['slurs'] if any(e[1] in heads for e in s['endpoints'])]
        protected = [
            p
            for p in graph.text_protected_regions
            if p.bbox
            and p.page == measure.page
            and p.bbox[0] < measure.bounds[2]
            and p.bbox[2] > measure.bounds[0]
            and p.bbox[1] < measure.bounds[3] + 170
            and p.bbox[3] > measure.bounds[1] - 150
        ]
        # These are conservative rectangular envelopes, never claims about glyph ink.
        pairs = [
            {'a': a['head_id'], 'b': b['head_id']}
            for a, b in itertools.combinations(rows, 2)
            if overlap(a['target_head_envelope'], b['target_head_envelope'])
        ]
        protected_hits = [
            {'head': r['head_id'], 'protected': p.id, 'kind': p.kind}
            for r in rows
            for p in protected
            if overlap(r['target_head_envelope'], p.bbox)
        ]
        candidate_envelopes = (
            [
                {
                    'id': moves[i]['semantic_id'],
                    'bbox': moves[i]['potential_edit_region'],
                    'kind': 'note_component_swept',
                }
                for i in ids
            ]
            + [
                {'id': b['id'], 'bbox': b['potential_edit_region'], 'kind': 'beam_group_swept'}
                for b in selected_beams
            ]
            + [
                {'id': s['id'], 'bbox': s['potential_edit_region'], 'kind': 'curve_swept'}
                for s in selected_curves
            ]
        )
        envelope_pairs = [
            {'a': a['id'], 'b': b['id'], 'kinds': [a['kind'], b['kind']]}
            for a, b in itertools.combinations(candidate_envelopes, 2)
            if a['bbox'] and b['bbox'] and overlap(a['bbox'], b['bbox'])
        ]
        envelope_protected = [
            {'candidate': a['id'], 'protected': p.id, 'kind': p.kind}
            for a in candidate_envelopes
            for p in protected
            if a['bbox'] and overlap(a['bbox'], p.bbox)
        ]
        plan_hits = [
            i
            for i in plan['intersections']
            if i['edit_id']
            in heads
            | {b['id'] for b in selected_beams}
            | {s['id'] for s in selected_curves}
            | set(ids)
        ]
        overlay = image.copy()
        draw = ImageDraw.Draw(overlay)
        for r in rows:
            x, y = r['source_xy']
            tx, ty = r['target_xy']
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), outline='blue', width=2)
            draw.line((x, y, tx, ty), fill='red', width=2)
            draw.rectangle((tx - 7, ty - 3, tx + 7, ty + 3), outline='red', width=2)
        for p in protected:
            draw.rectangle(p.bbox, outline='orange', width=2)
        draw.text(
            (measure.bounds[0], measure.bounds[1] - 110),
            'DEVELOPER ANNOTATION ONLY - NO REPLACEMENT NOTATION',
            fill='red',
        )
        draw.text(
            (measure.bounds[0], measure.bounds[1] - 90),
            'blue=raw head; red=absolute semantic target; orange=protected bbox',
            fill='red',
        )
        crop = (
            max(0, int(measure.bounds[0]) - 10),
            max(0, int(measure.bounds[1]) - 125),
            min(image.width, math.ceil(measure.bounds[2]) + 10),
            min(image.height, math.ceil(measure.bounds[3]) + 180),
        )
        overlay.crop(crop).save(out / f'measure-{num}-ANNOTATED.png')
        lyrics = []
        for p in protected:
            if p.kind != 'lyrics':
                continue
            bbox = tuple(map(int, p.bbox))
            changed = changed_pixel_count(image.crop(bbox), overlay.crop(bbox))
            lyrics.append(
                {
                    'id': p.id,
                    'bbox': p.bbox,
                    'scope': 'recognized protected lyric bbox; whole original page annotation before crop',
                    'annotation_changed_pixel_count': changed,
                    'replacement_pixel_equality': 'NOT_APPLICABLE_B2_NOT_RUN',
                }
            )
        before_chords = list(
            before.parts[0].measure(int(num)).recurse().getElementsByClass(harmony.ChordSymbol)
        )
        after_chords = list(
            after.parts[0].measure(int(num)).recurse().getElementsByClass(harmony.ChordSymbol)
        )
        chord_lengths = [
            {
                'source': a.figure,
                'target': b.figure,
                'source_characters': len(a.figure),
                'target_characters': len(b.figure),
                'rendered_width_conflict': 'UNKNOWN_NO_CHORD_GLYPH_LAYOUT',
            }
            for a, b in zip(before_chords, after_chords)
        ]
        excerpts.append(
            {
                'measure_number': num,
                'existing_plan_swept_envelope_pair_overlap_count': len(envelope_pairs),
                'existing_plan_swept_envelope_pair_overlaps': envelope_pairs,
                'existing_plan_swept_envelope_protected_overlaps': envelope_protected,
                'envelope_scope': 'Existing V4 plan swept bounding boxes; overlaps include expected attachment/group containment and are NOT actual notation ink collisions or validated absolute-target layout',
                'coordinate_count': len(rows),
                'head_envelope_pair_overlap_count': len(pairs),
                'head_envelope_pair_overlaps': pairs,
                'target_head_protected_envelope_overlap_count': len(protected_hits),
                'target_head_protected_envelope_overlaps': protected_hits,
                'existing_plan_swept_protected_intersections': plan_hits,
                'actual_ink_collision_count': None,
                'actual_ink_collision_status': 'UNKNOWN_NOT_RENDERED',
                'beam_groups': selected_beams,
                'slurs_ties': selected_curves,
                'protected_lyrics': lyrics,
                'chord_text_lengths': chord_lengths,
                'measure_width_px': measure.bounds[2] - measure.bounds[0],
                'measure_width_deviation_px': 0,
                'source_crop': crop,
            }
        )
        all_rows += rows
    geometry = {
        'pages': to_data(graph.pages),
        'systems': to_data(graph.systems),
        'staves': to_data(graph.staves),
        'measures': [
            to_data(m)
            for m in graph.measures
            if m.number in {e['measure_number'] for e in reg['excerpts']}
        ],
        'contract': 'Original page dimensions, system membership, measure bounds and staff polylines copied verbatim from graph; target x copied from original head; absolute target y=interpolated original middle staff line + target SemanticNote.staff_pitch*original Staff.interline/2. No reflow, raster edits, lyric OCR or notation rendering.',
    }
    write_json(out / 'target-geometry.json', geometry)
    write_json(out / 'coordinate-map.json', all_rows)
    write_json(out / 'collision-report.json', excerpts)
    _, verified_after = verify_inputs(manifest)
    write_json(out / 'input-verification-after.json', verified_after)
    assert digest(registration) == registration_hash
    result = {
        'decision': 'GEOMETRY_LOCKED_POC_NEEDS_WORK',
        'b1_validated': False,
        'b2': 'SKIPPED: full V3 integrity fails; unresolved beam/slur/ink/protected-region/chord layout validation',
        'registration_sha256': registration_hash,
        'excerpts': [e['measure_number'] for e in excerpts],
        'note_count': len(all_rows),
        'page_size': image.size,
        'staff_polyline_deviation_px': 0,
        'head_x_deviation_px': max(abs(r['source_xy'][0] - r['target_xy'][0]) for r in all_rows),
        'measure_width_deviation_px': 0,
        'system_breaks_deviation': 0,
        'expected_displacement_range_px': [
            min(r['expected_displacement_px'] for r in all_rows),
            max(r['expected_displacement_px'] for r in all_rows),
        ],
        'existing_plan_absolute_y_max_error_px': max(
            abs(r['existing_plan_absolute_y_error_px']) for r in all_rows
        ),
        'head_envelope_pair_overlap_count': sum(
            e['head_envelope_pair_overlap_count'] for e in excerpts
        ),
        'target_head_protected_envelope_overlap_count': sum(
            e['target_head_protected_envelope_overlap_count'] for e in excerpts
        ),
        'actual_ink_collision_count': None,
        'musical_integrity_full': full.to_dict(),
        'fresh_v3_transposition_full': fresh_guard.to_dict(),
        'original_content_loss': '0 source pixels/files edited; replacement loss UNKNOWN because B2 skipped',
        'geometry_deviations_scope': 'coordinate-map and immutable geometry contract ONLY; no reconstructed canvas exists',
        'protected_lyric_equality_scope': 'annotation differences reported separately; replacement equality NOT_APPLICABLE',
        'runtime_seconds': time.perf_counter() - started,
        'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'peak_rss_platform': 'macOS ru_maxrss bytes (whole helper process including music21)',
        'input_hashes_before_after': verified_after['verified_files'],
    }
    write_json(
        out / 'run-resources.json',
        {k: result.pop(k) for k in ('runtime_seconds', 'peak_rss_bytes', 'peak_rss_platform')},
    )
    write_json(out / 'summary.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.inputs, args.registration, args.out), indent=2))


if __name__ == '__main__':
    main()
