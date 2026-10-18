"""Offline paired-score research. Predictions never receive the multi-page PDF.

No rendering, production acceptance or annotation truth is supplied here.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, is_dataclass
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import resource
import shutil
import time
import traceback
from xml.etree import ElementTree as ET

from PIL import Image

BASE = '04687ce6ac65eb4d9505365b92aa96c886c88530'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_default(value):
    if isinstance(value, Fraction):
        return str(value)
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f'Unsupported diagnostic value: {type(value).__name__}')


def dump(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
            default=json_default,
        )
        + '\n'
    )


def file_hashes(root):
    if any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('Symlink evidence forbidden')
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def verify_files(root, expected):
    if file_hashes(root) != expected:
        raise ValueError('Frozen prediction files changed/missing/added')


def line_y(points, x):
    if (
        len(points) < 2
        or not math.isfinite(x)
        or any(not math.isfinite(v) for p in points for v in p)
    ):
        raise ValueError('Invalid staff polyline')
    if (
        any(b[0] <= a[0] for a, b in zip(points, points[1:]))
        or not points[0][0] <= x <= points[-1][0]
    ):
        raise ValueError('Outside valid polyline domain')
    for a, b in zip(points, points[1:]):
        if a[0] <= x <= b[0]:
            return a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])
    raise ValueError('No staff segment')


def absolute_y(staff, x, staff_pitch):
    if (
        not staff.valid
        or len(staff.lines) != 5
        or not math.isfinite(staff.interline)
        or staff.interline <= 0
        or staff_pitch is None
    ):
        raise ValueError('Unknown absolute staff coordinate')
    return line_y(staff.lines[2], x) + staff_pitch * staff.interline / 2


def overlap(a, b):
    return (
        a is not None
        and b is not None
        and max(a[0], b[0]) < min(a[2], b[2])
        and max(a[1], b[1]) < min(a[3], b[3])
    )


def inventory(path):
    from backend.omr_v4.visual_graph import safe_xml
    from backend.omr_v4.matcher import read_semantics
    from backend.omr_v4.plan import to_data

    xml = safe_xml(path.read_bytes(), musicxml=True)
    semantic = read_semantics(path)
    return {
        'keys': to_data(semantic.keys),
        'pitched_notes': to_data(semantic.notes),
        'parts': len(xml.findall('part')),
        'measures_per_part': [len(p.findall('measure')) for p in xml.findall('part')],
        'rest_events': len(xml.findall('.//note/rest')),
        'ties': [e.attrib for e in xml.findall('.//note/tie')],
        'slurs': [e.attrib for e in xml.findall('.//slur')],
        'lyrics': [ET.tostring(e, encoding='unicode') for e in xml.findall('.//lyric')],
        'harmonies': [ET.tostring(e, encoding='unicode') for e in xml.findall('.//harmony')],
        'limitations': 'Recognition inventory, not independently verified musical truth. Full XML retains voices, rests, durations, repeats, accidental/tie/slur/lyric details.',
    }


def recognize(source, out):
    """Unchanged V3 Audiveris and diagnostic cleanup order, no PaddleOCR pass."""
    from music21 import converter, stream
    from backend.omr_v3.core import run_audiveris, validate
    from backend.omr_v3 import cleanup
    from backend.omr_v3.geometry import load_geometry
    from backend.omr_v4.matcher import read_semantics, match_notes
    from backend.omr_v4.visual_graph import load_visual_graph
    from backend.omr_v4.provenance import capture_ledger_repairs, match_with_provenance
    from backend.omr_v4.plan import to_data
    from scripts.omr_v4.inspect_layout import _stable_export_ids

    out.mkdir(parents=True, exist_ok=False)
    initial = sha(source)
    validate(source.read_bytes(), '.png')
    shutil.copyfile(source, out / 'source.png')
    home = out / 'tool-home'
    home.mkdir()
    raw, book = run_audiveris(
        (out / 'source.png').resolve(), (out / 'omr').resolve(), 300, home.resolve()
    )
    shutil.copyfile(book, out / 'recognized.omr')
    shutil.copyfile(raw, out / ('audiveris' + raw.suffix))
    graph = load_visual_graph(book)
    with Image.open(source) as image:
        if len(graph.pages) != 1 or image.size != (graph.pages[0].width, graph.pages[0].height):
            raise ValueError('Source/OMR page geometry mismatch')
    score = converter.parse(str(raw))
    if not score.parts:
        raise ValueError('Unreadable recognized parts')
    repairs = {
        'rest_only_voices_removed': cleanup.drop_rest_only_voices(score),
        'lyrics_removed': cleanup.clean_lyrics(score),
        'chord_words': cleanup.chord_words_to_symbols(score),
        'marks_removed': cleanup.strip_marks(score),
        'layout': cleanup.normalize_layout(score),
    }
    before = out / 'pre-ledger.musicxml'
    score.write('musicxml', fp=str(before))
    _stable_export_ids(before)
    raw_semantics = read_semantics(before)
    raw_matches = match_notes(raw_semantics, graph)
    fixed = 0
    if graph.invalid_geometry_count == 0:
        geometry = load_geometry(book)
        measures = list(score.parts[0].getElementsByClass(stream.Measure))
        if geometry.remap_to_measures(
            [m.measureNumberWithSuffix() for m in measures]
        ) or geometry.measure_count == len(measures):
            fixed = cleanup.fix_missed_ledgers(score, geometry, source)
    repairs['ledger_notes_fixed'] = fixed
    recognized = out / 'recognized.musicxml'
    score.write('musicxml', fp=str(recognized))
    _stable_export_ids(recognized)
    semantic = read_semantics(recognized)
    provenance = capture_ledger_repairs(raw_semantics, semantic, raw_matches, fixed)
    matches = match_with_provenance(raw_semantics, semantic, graph, raw_matches, provenance)
    dump(
        out / 'recognition-report.json',
        {
            'source_sha256_before': initial,
            'source_sha256_after': sha(source),
            'input_is_exact_raster_passed_to_audiveris': initial == sha(out / 'source.png'),
            'coordinate_binding': 'witnessed isolated run, source digest + exact OMR page dimensions; not an OMR-embedded original hash',
            'repairs': repairs,
            'repair_provenance': to_data(provenance),
            'matches': matches.summary(),
            'recognition_scope': 'V3 Audiveris + existing cleanup; no independent PaddleOCR chord detection/merge; not full production conversion',
        },
    )
    dump(out / 'inventory.json', inventory(recognized))
    dump(out / 'visual-graph.json', to_data(graph))
    if initial != sha(source):
        raise ValueError('Input changed')
    return graph, semantic, matches


def geometry_audit(graph, source_semantics, target_semantics, plan):
    """B1 analysis only. Existing delta planner is neither changed nor corrected."""
    target = {a.id: b for a, b in zip(source_semantics.notes, target_semantics.notes)}
    staves = {s.id: s for s in graph.staves}
    rows = []
    for move in plan.note_moves:
        staff = staves[move.staff]
        a = next(n for n in source_semantics.notes if n.id == move.semantic_id)
        b = target[a.id]
        try:
            source_y = absolute_y(staff, move.source_x, a.staff_pitch)
            target_y = absolute_y(staff, move.source_x, b.staff_pitch)
            delta = target_y - source_y
            box = graph.symbols[move.source_head_id].geometry.bbox
            envelope = (
                (
                    box[0],
                    box[1] + target_y - move.source_y,
                    box[2],
                    box[3] + target_y - move.source_y,
                )
                if box
                else None
            )
            protected = [r.id for r in graph.text_protected_regions if overlap(envelope, r.bbox)]
            structural = [
                s.id
                for s in graph.symbols.values()
                if s.kind in ('barline', 'staff-barline') and overlap(envelope, s.geometry.bbox)
            ]
            neighbors = [
                m.source_head_id
                for m in plan.note_moves
                if m.source_head_id != move.source_head_id
                and overlap(envelope, graph.symbols[m.source_head_id].geometry.bbox)
            ]
            page = next(p for p in graph.pages if p.id == move.page)
            bounds_fail = envelope is None or not (
                0 <= envelope[0] < envelope[2] <= page.width
                and 0 <= envelope[1] < envelope[3] <= page.height
            )
            system = next(s for s in graph.systems if s.id == staff.system)
            system_fail = (
                system.bounds is None
                or envelope is None
                or not (
                    system.bounds[0] <= envelope[0]
                    and envelope[2] <= system.bounds[2]
                    and system.bounds[1] <= envelope[1]
                    and envelope[3] <= system.bounds[3]
                )
            )
            rows.append(
                {
                    'semantic_id': a.id,
                    'head_id': move.source_head_id,
                    'source_pitch': a.pitch,
                    'target_pitch': b.pitch,
                    'detected_head_x': move.source_x,
                    'detected_head_y': move.source_y,
                    'corrected_semantic_source_staff_y': source_y,
                    'absolute_target_staff_y': target_y,
                    'expected_diatonic_delta_y': delta,
                    'existing_delta_planner_target_y': move.target_y,
                    'delta_vs_absolute_anchor_discrepancy_px': move.target_y - target_y,
                    'target_x': move.source_x,
                    'replacement_glyph_anchor': 'UNDEFINED_NOT_RENDERED',
                    'target_head_bbox_envelope_only': envelope,
                    'protected_collisions': protected,
                    'structural_collisions': structural,
                    'unrelated_head_envelope_candidates': neighbors,
                    'page_boundary_blocked': bounds_fail,
                    'system_boundary_blocked': system_fail,
                    'complete_notation_collision_validation': 'BLOCKED: no verified target stem/beam/curve/attachment/font geometry',
                }
            )
        except ValueError as exc:
            rows.append({'semantic_id': a.id, 'head_id': move.source_head_id, 'blocked': str(exc)})
    good = [r for r in rows if 'blocked' not in r]
    return {
        'diagnostic_only': True,
        'notes': rows,
        'metrics': {
            'matched_note_count': len(plan.note_moves),
            'absolute_coordinates_computed': len(good),
            'staff_coordinate_deviation_px': 0,
            'notehead_x_deviation_px': 0,
            'measure_width_deviation_px': 0,
            'zero_deviation_basis': 'construction invariants relative to original graph, not physical reference accuracy',
            'max_delta_vs_absolute_anchor_discrepancy_px': max(
                (abs(r['delta_vs_absolute_anchor_discrepancy_px']) for r in good), default=None
            ),
            'target_head_protected_collision_pairs': sum(
                len(r['protected_collisions']) for r in good
            ),
            'target_head_structural_collision_pairs': sum(
                len(r['structural_collisions']) for r in good
            ),
            'unrelated_head_envelope_pairs_unresolved': sum(
                len(r['unrelated_head_envelope_candidates']) for r in good
            ),
            'page_boundary_blocks': sum(r['page_boundary_blocked'] for r in good),
            'system_boundary_blocks': sum(r['system_boundary_blocked'] for r in good),
        },
        'glyph_placement': 'BLOCKED_PENDING_INDEPENDENT_PHYSICAL_ANCHORS',
        'beam_slur_chord_width_accidental_collision_completeness': 'UNVERIFIED_NO_RENDERER',
        'protected_lyric_pixel_equality': 'NOT_APPLICABLE_NO_COMPOSITE_OUTPUT; original raster unchanged',
        'staff_polylines': [asdict(s) for s in graph.staves],
        'measures': [asdict(m) for m in graph.measures],
    }


def predict(source, out):
    from music21 import converter
    from backend.omr_v3.music_guard import validate
    from backend.omr_v3.transpose import transpose_score
    from backend.omr_v4.matcher import read_semantics
    from backend.omr_v4.plan import build_plan, to_data
    from backend.omr_v4.source_ink import read_processed_bundle, isolate_source_ink, coverage
    from backend.omr_v4.masks import plan_masks, validate_pixel_integrity
    from scripts.omr_v4.inspect_layout import _stable_export_ids

    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    status = {'recognition': 'NOT_RUN', 'targets': {}, 'track_a': 'NOT_RUN', 'track_b': 'NOT_RUN'}
    try:
        graph, semantic, matches = recognize(source, out / 'source')
        status['recognition'] = 'COMPLETED_UNVERIFIED_RECOGNITION'
    except Exception as exc:
        status.update(
            recognition='RECOGNITION FAILURE',
            error=type(exc).__name__ + ': ' + str(exc),
            traceback=traceback.format_exc(),
        )
        dump(out / 'status.json', status)
        return status
    score = converter.parse(str(out / 'source/recognized.musicxml'))
    image = Image.open(source).copy()
    ink = None
    try:
        ink = isolate_source_ink(
            image, graph, *read_processed_bundle(out / 'source/recognized.omr', graph)
        )
        (out / 'track-a-ink-evidence.json').write_text(ink.to_json())
        status['track_a'] = coverage(ink)
    except Exception as exc:
        status['track_a'] = {'status': 'UNSUPPORTED CASE', 'error': str(exc)}
    for name, shift in [('A', -1), ('G', -3)]:
        dest = out / name
        dest.mkdir()
        stage = 'TRANSPOSITION FAILURE'
        try:
            transposed = copy.deepcopy(score)
            summary = transpose_score(transposed, shift)
            memory_guard = validate(score, transposed, shift, 'key').to_dict()
            stage = 'SERIALIZATION FAILURE'
            path = dest / 'transposed.musicxml'
            transposed.write('musicxml', fp=str(path))
            _stable_export_ids(path)
            serialized = converter.parse(str(path))
            serial_guard = validate(score, serialized, shift, 'key').to_dict()
            usable = memory_guard['ok'] and serial_guard['ok']
            result = {
                'status': 'GUARD_PASS_RECOGNITION_UNVERIFIED' if usable else 'INTEGRITY FAILURE',
                'usable_transposed_score_declared': False,
                'semitones': shift,
                'guard_in_memory': memory_guard,
                'guard_serialized': serial_guard,
                'transposition': summary,
            }
            dump(dest / 'integrity-report.json', result)
            dump(dest / 'inventory.json', inventory(path))
            target = read_semantics(path)
            plan = build_plan(graph, semantic, target, matches)
            # Plan output is a failed-attempt diagnostic if either full guard fails.
            plan_data = to_data(plan)
            plan_data['metrics'] = dict(plan.metrics)
            plan_data['full_guard_passed'] = usable
            plan_data['edit_authorization'] = False
            dump(dest / 'plan.json', plan_data)
            geometry = geometry_audit(graph, semantic, target, plan)
            # to_data handles Fraction-valued geometry witness structures.
            dump(dest / 'track-b-geometry.json', to_data(geometry))
            if ink is not None:
                mask_plan, masks = plan_masks(image, graph, plan_data, ink.owned(image))
                dump(
                    dest / 'track-a-mask-summary.json',
                    {
                        'metrics': dict(mask_plan.metrics),
                        'complete_only': True,
                        'source_pixel_integrity': validate_pixel_integrity(
                            image, image.copy(), masks.approved
                        ),
                        'not_edit_permission_if_integrity_failed': not usable,
                    },
                )
                masks.approved.save(dest / 'approved-mask.png')
            status['targets'][name] = result
        except Exception as exc:
            status['targets'][name] = {
                'status': stage,
                'error': str(exc),
                'traceback': traceback.format_exc(),
            }
    status.update(
        seconds=time.monotonic() - started,
        peak_rss_kib_linux=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        source_sha256=sha(source),
        code_sha256=sha(Path(__file__)),
        base=BASE,
        references_accessible_to_worker=False,
        no_rendering=True,
    )
    dump(out / 'status.json', status)
    return status


def candidate_compare(left, right, semitones):
    """Strict event-identity candidate correspondence, explicitly not ground truth."""
    from music21 import pitch
    from backend.omr_v4.matcher import read_semantics

    a, b = read_semantics(left), read_semantics(right)
    aa = {n.identity: n for n in a.notes}
    bb = {n.identity: n for n in b.notes}
    if len(aa) != len(a.notes) or len(bb) != len(b.notes):
        raise ValueError('Duplicate candidate event identities')
    common = sorted(aa.keys() & bb.keys(), key=str)
    rows = []
    for identity in common:
        x, y = aa[identity], bb[identity]
        rows.append(
            {
                'source_id': x.id,
                'reference_id': y.id,
                'source_pitch': x.pitch,
                'reference_pitch': y.pitch,
                'observed_semitones': pitch.Pitch(y.pitch).midi - pitch.Pitch(x.pitch).midi,
                'interval_agrees': pitch.Pitch(y.pitch).midi - pitch.Pitch(x.pitch).midi
                == semitones,
            }
        )
    return {
        'status': 'UNVERIFIED_RECOGNIZER_AGREEMENT_NOT_ACCURACY',
        'expected_semitones': semitones,
        'left_notes': len(a.notes),
        'right_notes': len(b.notes),
        'unique_exact_identity_candidates': len(rows),
        'candidate_interval_agreements': sum(r['interval_agrees'] for r in rows),
        'unmatched_left_identities': len(aa.keys() - bb.keys()),
        'unmatched_right_identities': len(bb.keys() - aa.keys()),
        'verified_ground_truth_denominator': 0,
        'events': rows,
        'correspondence': 'candidate by part, measure index/number, staff, voice, onset, duration, chord membership; not independently adjudicated',
    }


def evaluate(source, out, freeze, frozen_predictions):
    # Signature verified by coordinator using openssl before invocation; binding rechecked here.
    manifest = json.loads(freeze.read_text())
    if (
        out.resolve() == frozen_predictions.resolve()
        or frozen_predictions.resolve() in out.resolve().parents
    ):
        raise ValueError('Reference output must be separate from frozen predictions')
    verify_files(frozen_predictions, manifest['prediction_files'])
    if manifest['phase'] != 'SOURCE_ONLY_PREDICTIONS_FROZEN':
        raise ValueError('Predictions must freeze before references')
    graph, semantic, matches = recognize(source, out)
    verify_files(frozen_predictions, manifest['prediction_files'])
    return {'reference_recognition': 'COMPLETED_UNVERIFIED', 'matches': matches.summary()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['predict', 'reference'])
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--freeze', type=Path)
    parser.add_argument('--predictions', type=Path)
    args = parser.parse_args()
    if args.phase == 'predict':
        result = predict(args.source, args.out)
    else:
        if not args.freeze or not args.predictions:
            parser.error('Reference evaluation requires frozen baseline and prediction root')
        result = evaluate(args.source, args.out, args.freeze, args.predictions)
    print(json.dumps(result, sort_keys=True, default=str, indent=2))


if __name__ == '__main__':
    main()
