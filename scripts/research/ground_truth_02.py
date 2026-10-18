"""Post-reference measure registration/coverage diagnostics; no score edits or truth labels."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
from xml.etree import ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw

from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes, verify_files
from scripts.research.evaluate_paired_ground_truth_01 import (
    verify_baseline,
    reference_matches,
    chords,
)
from backend.omr_v4.visual_graph import load_visual_graph, safe_xml
from backend.omr_v4.matcher import read_semantics

RASTER_POLICY = {
    'version': 'gt02-raster-proposals/1',
    'dark_below': 127,
    'horizontal_page_fraction': 0.65,
    'staff_cluster_gap_px': 60,
    'vertical_coverage': 0.9,
    'staff_row_exclusion_px': 3,
    'compound_bar_gap_interline': 0.75,
    'header_exclusion_interlines': 10,
    'omr_boundary_tolerance_interlines': 0.25,
    'purpose': 'coordinator proposals only, never ink ownership/admission or human truth',
}
GT01_BASELINE_MANIFEST_SHA = '68f327663cf91011f62b16db770cba4e06aea1323d0b06bade1cbfe2c904ad49'
GT01_PUBLIC_KEY_SHA = 'b55a88e832c781eaf96e1faf8b09accb8909224e04e675330d95e4596544f0b7'


def clusters(values, gap=1):
    result = []
    for v in values:
        v = float(v)
        if not result or v - result[-1][-1] > gap:
            result.append([v])
        else:
            result[-1].append(v)
    return result


def raster_systems(image):
    array = np.asarray(image)
    if (
        image.mode == 'RGB'
        and np.array_equal(array[:, :, 0], array[:, :, 1])
        and np.array_equal(array[:, :, 1], array[:, :, 2])
    ):
        array = array[:, :, 0]  # Lossless view; original RGB pixels/mode remain untouched.
    elif image.mode != 'L':
        raise ValueError('Require L or exactly identical RGB channels; no implicit conversion')
    ink = array < RASTER_POLICY['dark_below']
    bands = clusters(np.flatnonzero(ink.sum(1) > image.width * 0.65))
    centers = [statistics.mean(b) for b in bands]
    result = []
    for number, lines in enumerate(clusters(centers, 60), 1):
        if len(lines) != 5:
            raise ValueError('Cannot uniquely identify five original staff lines')
        interline = (lines[-1] - lines[0]) / 4
        if interline <= 0:
            raise ValueError('Invalid staff spacing')
        common = ink[[round(y) for y in lines]].sum(0) >= 4
        xs = np.flatnonzero(common)
        if not len(xs):
            raise ValueError('Unknown staff extent')
        left, right = int(xs[0]), int(xs[-1])
        sample = [
            y
            for y in range(int(lines[0]) + 3, int(lines[-1]) - 2)
            if min(abs(y - l) for l in lines) > 3
        ]
        if not sample:
            raise ValueError('Staff too small for barline analysis')
        coverage = ink[sample].mean(0)
        bars = []
        for columns in clusters(np.flatnonzero(coverage >= 0.9), max(3, int(0.75 * interline))):
            center = statistics.mean(columns)
            if left + 10 * interline < center < right - interline / 2:
                bars.append(
                    {
                        'x': center,
                        'stroke_span': [min(columns), max(columns)],
                        'minimum_sampled_vertical_coverage': float(
                            min(coverage[int(x)] for x in columns)
                        ),
                        'status': 'NEEDS_COORDINATOR_CLASSIFICATION',
                    }
                )
        end = [int(x) for x in np.flatnonzero(coverage >= 0.9) if abs(x - right) <= interline / 2]
        if not end:
            raise ValueError('No end barline witness at staff right edge')
        result.append(
            {
                'system': number,
                'staff_lines_y': lines,
                'staff_left': left,
                'staff_right': right,
                'interline': interline,
                'bar_proposals': bars,
                'end_bar_pixels': end,
            }
        )
    return result


def registered_page(image, page, observations):
    systems = raster_systems(image)
    records = []
    audit = []
    number = 1
    for system in systems:
        rejections = observations['rejected_vertical_candidates'].get(str(system['system']), [])
        accepted = []
        for bar in system['bar_proposals']:
            rejects = [r for r in rejections if abs(r['x'] - bar['x']) <= 1]
            if len(rejects) > 1:
                raise ValueError('Duplicate coordinator rejection')
            if rejects:
                audit.append(
                    {
                        **bar,
                        'system': system['system'],
                        'classification': rejects[0]['classification'],
                        'reason': rejects[0]['reason'],
                    }
                )
            else:
                confirmed = observations['accepted_internal_boundaries'].get(
                    str(system['system']), []
                )
                if sum(abs(x - bar['x']) <= 1 for x in confirmed) != 1:
                    raise ValueError('Unreviewed barline proposal; do not force registration')
                accepted.append(bar)
                audit.append(
                    {
                        **bar,
                        'system': system['system'],
                        'classification': 'PRINTED_BARLINE_CANDIDATE',
                        'reason': 'Raster proposal plus coordinator source-image review; independent human review pending',
                    }
                )
        if any(
            not any(abs(r['x'] - b['x']) <= 1 for b in system['bar_proposals']) for r in rejections
        ):
            raise ValueError('Rejection does not name an observed raster candidate')
        confirmed = observations['accepted_internal_boundaries'].get(str(system['system']), [])
        if len(confirmed) != len(accepted) or any(
            not any(abs(x - b['x']) <= 1 for b in accepted) for x in confirmed
        ):
            raise ValueError('Confirmation does not name a unique retained raster candidate')
        bounds = [
            {
                'x': system['staff_left'],
                'stroke_span': [system['staff_left']] * 2,
                'type': 'SYSTEM_START_CONTEXT_EDGE',
            },
            *[{**b, 'type': 'PRINTED_INTERNAL_BARLINE'} for b in accepted],
            {
                'x': system['staff_right'],
                'stroke_span': [min(system['end_bar_pixels']), max(system['end_bar_pixels'])],
                'type': 'SYSTEM_END_BARLINE',
            },
        ]
        for position, (left, right) in enumerate(zip(bounds, bounds[1:]), 1):
            if left['x'] >= right['x']:
                raise ValueError('Nonordered printed boundaries')
            record = {
                'page_label': page,
                'pdf_page': observations['pdf_page'],
                'system': system['system'],
                'printed_measure': number,
                'identity': f'printed-{number:02d}',
                'within_system': position,
                'left': left,
                'right': right,
                'staff_lines_y': system['staff_lines_y'],
                'staff_interline': system['interline'],
                'staff_range_x': [system['staff_left'], system['staff_right']],
                'repeat_ending_context': observations['ending_context'].get(
                    str(number),
                    {
                        'literal': 'No coordinator-noted ending mark',
                        'performance_expansion': 'NOT_INFERRED',
                    },
                ),
                'confidence': 'HIGH_COORDINATOR_RASTER_CANDIDATE_NOT_ACCEPTED_GROUND_TRUTH',
                'independent_human_verified': False,
                'unresolved': 'Independent A/B boundary/identity/ending verification pending',
            }
            records.append(record)
            number += 1
    starts = [r['printed_measure'] for r in records if r['within_system'] == 1]
    if starts != observations['visually_read_system_start_labels']:
        raise ValueError('Raster/visible printed bar labels disagree; do not force count')
    return {
        'source_sha256': observations['source_sha256'],
        'pdf_page': observations['pdf_page'],
        'systems': systems,
        'measures': records,
        'proposal_audit': audit,
        'source': 'Raster pixels and coordinator observations, no OMR indices',
    }


def staff_system(graph, page, staff_id):
    matches = []
    staff = next((s for s in graph.staves if s.id == staff_id), None)
    if staff and len(staff.lines) == 5:
        ys = [statistics.mean(p[1] for p in line) for line in staff.lines]
        matches = [
            s['system']
            for s in page['systems']
            if max(abs(a - b) for a, b in zip(ys, s['staff_lines_y'])) <= s['interline'] / 4
        ]
    return matches[0] if len(matches) == 1 else None


def region_for_box(page, system, box):
    if box is None or not all(np.isfinite(v) for v in box) or box[2] < box[0] or box[3] < box[1]:
        return 'UNMATCHED', [], 'Missing/invalid physical geometry'
    x1, _, x2, _ = box
    regions = [
        m
        for m in page['measures']
        if m['system'] == system and x2 > m['left']['x'] and x1 < m['right']['x']
    ]
    safe = [
        m for m in regions if x1 > m['left']['stroke_span'][1] and x2 < m['right']['stroke_span'][0]
    ]
    if len(safe) == 1:
        return (
            'MATCHED',
            [safe[0]['printed_measure']],
            'Unique physical staff and head/rest bbox inside independently registered barlines',
        )
    return (
        ('AMBIGUOUS' if regions else 'UNMATCHED'),
        [m['printed_measure'] for m in regions],
        'Geometry crosses barline uncertainty band or cannot identify printed region',
    )


def segmentation(graph, page):
    result = []
    for m in graph.measures:
        staff = next(s for s in graph.staves if s.system == m.system and s.part == m.part)
        system = staff_system(graph, page, staff.id)
        physical = [
            r
            for r in page['measures']
            if r['system'] == system
            and m.bounds
            and min(m.bounds[2], r['right']['x']) - max(m.bounds[0], r['left']['x'])
            > page['systems'][system - 1]['interline']
        ]
        tol = page['systems'][system - 1]['interline'] / 4 if system else 0
        aligned = (
            bool(physical)
            and abs(m.bounds[0] - physical[0]['left']['x']) <= tol
            and abs(m.bounds[2] - physical[-1]['right']['x']) <= tol
        )
        status = (
            'MATCHED'
            if len(physical) == 1 and aligned
            else (
                'PARTIAL'
                if len(physical) > 1 and aligned
                else 'AMBIGUOUS' if physical else 'UNMATCHED'
            )
        )
        missing = []
        for r in physical[:-1]:
            boundary = r['right']
            x = boundary['x']
            nearby = []
            for symbol in graph.symbols.values():
                region = symbol.geometry.region
                if (
                    symbol.system == m.system
                    and symbol.kind in {'barline', 'staff-barline'}
                    and region
                    and region[0] - tol <= x <= region[2] + tol
                ):
                    nearby.append(
                        {
                            'symbol_id': symbol.id,
                            'kind': symbol.kind,
                            'bbox': region,
                            'attributes': dict(symbol.attributes),
                        }
                    )
            missing.append(
                {
                    'after_printed_measure': r['printed_measure'],
                    'physical_x': x,
                    'raster_barline_span': boundary['stroke_span'],
                    'nearby_persisted_sig_barlines': nearby,
                    'cause': (
                        'SIG_BARLINE_NOT_USED_AS_STACK_BOUNDARY'
                        if nearby
                        else 'PRINTED_BARLINE_NOT_PERSISTED_AS_SIG_BOUNDARY'
                    ),
                    'omr_stack_duration': str(m.duration),
                    'note': 'No repeat unfolding or invented measure; this OMR stack spans distinct printed regions',
                }
            )
        result.append(
            {
                'omr_measure_id': m.id,
                'omr_number': m.number,
                'system': system,
                'bounds': m.bounds,
                'printed_measures': [r['printed_measure'] for r in physical],
                'status': status,
                'reason': (
                    'Physical staff/edge agreement'
                    if status == 'MATCHED'
                    else (
                        'Merged printed regions'
                        if status == 'PARTIAL'
                        else 'Physical boundary correspondence unresolved'
                    )
                ),
                'missing_boundaries': missing,
                'stack_source_xml': m.stack_source_xml,
                'measure_source_xml': m.source_xml,
            }
        )
    return result


def xml_events(path):
    """Retain exact XML timing. No correction/re-export or OMR index cross-alignment."""
    root = safe_xml(path.read_bytes(), musicxml=True)
    result = []
    for pi, part in enumerate(root.findall('part'), 1):
        divisions = Fraction(1)
        for mi, m in enumerate(part.findall('measure')):
            cursor = Fraction(0)
            prev = Fraction(0)
            pitched = 0
            rests = 0
            for el in m:
                if el.tag == 'attributes' and el.find('divisions') is not None:
                    divisions = Fraction(el.findtext('divisions'))
                if el.tag in {'backup', 'forward'}:
                    amount = Fraction(el.findtext('duration')) / divisions
                    cursor += amount if el.tag == 'forward' else -amount
                if el.tag != 'note':
                    continue
                duration = Fraction(el.findtext('duration', '0')) / divisions
                onset = prev if el.find('chord') is not None else cursor
                if el.find('chord') is None:
                    prev = cursor
                    cursor += duration
                is_rest = el.find('rest') is not None
                ident = f'p{pi}:m{mi}:r{rests}' if is_rest else f'p{pi}:m{mi}:n{pitched}'
                if is_rest:
                    rests += 1
                else:
                    pitched += 1
                result.append(
                    {
                        'id': ident,
                        'part_index': pi,
                        'omr_number': m.get('number'),
                        'omr_measure_index': mi,
                        'kind': 'REST' if is_rest else 'NOTE',
                        'offset': onset,
                        'duration': duration,
                        'staff': int(el.findtext('staff', '1')),
                        'voice': el.findtext('voice'),
                        'measure_rest': is_rest and el.find('rest').get('measure') == 'yes',
                        'chord_continuation': el.find('chord') is not None,
                    }
                )
    return result


def rest_geometry(event, graph, measures):
    candidates = []
    for m in measures:
        slots = {s.id: s for s in m.slots}
        for chord, slot, voice in m.onsets:
            if slot not in slots or slots[slot].suspicious or slots[slot].offset != event['offset']:
                continue
            if event['voice'] is not None and event['voice'] != voice:
                continue
            children = [
                r.target for r in graph.relations if r.kind == 'contains' and r.source == chord
            ]
            candidates.extend(
                graph.symbols[c]
                for c in children
                if c in graph.symbols and graph.symbols[c].kind == 'rest'
            )
        if event['measure_rest'] and event['offset'] == 0:
            element = safe_xml(m.source_xml.encode())
            for voice in element.findall('voice'):
                chord = voice.get('measure-rest-chord')
                if chord:
                    ident = m.page + ':' + chord
                    children = [
                        r.target
                        for r in graph.relations
                        if r.kind == 'contains' and r.source == ident
                    ]
                    candidates.extend(
                        graph.symbols[c]
                        for c in children
                        if c in graph.symbols and graph.symbols[c].kind == 'rest'
                    )
    staff_numbers = {s.id: s.number for s in graph.staves}
    unique = {s.id: s for s in candidates if staff_numbers.get(s.staff) == event['staff']}
    return next(iter(unique.values())) if len(unique) == 1 else None


def tiled_origin(events, expected=Fraction(4)):
    if not events:
        return None, 'NO_UNIQUE_EVENTS'
    if any(e['status'] != 'MATCHED' for e in events):
        return None, 'UNRESOLVED_GEOMETRY'
    if len({e['voice'] for e in events}) != 1:
        return None, 'VOICE_AMBIGUITY'
    ordered = sorted(events, key=lambda e: (e['offset'], e['id']))
    origin = ordered[0]['offset']
    cursor = origin
    for event in ordered:
        if event['chord_continuation'] or event['offset'] != cursor or event['duration'] <= 0:
            return None, 'RHYTHM_OVERLAP_GAP_OR_UNSUPPORTED_CHORD'
        cursor += event['duration']
    if cursor - origin != expected:
        return None, 'RECOGNIZED_DURATION_NOT_FOUR_QUARTERS'
    return origin, 'RECOGNIZED_SINGLE_VOICE_FOUR_BEAT_TILE_NOT_GROUND_TRUTH'


def mapped_events(folder, graph, page):
    matches = reference_matches(folder, graph)
    by_id = {r.note.id: r for r in matches.notes}
    measures = defaultdict(list)
    for m in graph.measures:
        measures[m.number].append(m)
    result = []
    for e in xml_events(folder / 'recognized.musicxml'):
        if e['kind'] == 'NOTE':
            match = by_id.get(e['id'])
            symbol = (
                graph.symbols.get(match.head_id) if match and match.status == 'MATCHED' else None
            )
            e.update(
                pitch=match.note.pitch if match else None,
                chord_size=match.note.chord_size if match else None,
                member=match.note.member if match else None,
                ownership_basis=match.ownership_basis if match else None,
            )
        else:
            symbol = rest_geometry(e, graph, measures[e['omr_number']])
        if symbol:
            system = staff_system(graph, page, symbol.staff)
            status, regions, reason = region_for_box(page, system, symbol.geometry.bbox)
            e.update(
                symbol_id=symbol.id,
                bbox=symbol.geometry.bbox,
                system=system,
                status=status,
                printed_measures=regions,
                reason=reason,
            )
        else:
            e.update(
                symbol_id=None,
                status='UNMATCHED',
                printed_measures=[],
                reason='No unique existing semantic/head ownership or explicit rest-chord BEGIN/measure-rest lineage',
            )
        result.append(e)
    for measure in page['measures']:
        group = [e for e in result if e['printed_measures'] == [measure['printed_measure']]]
        origin, proof = tiled_origin(group)
        if any(
            e['status'] == 'AMBIGUOUS' and measure['printed_measure'] in e['printed_measures']
            for e in result
        ):
            origin, proof = None, 'AMBIGUOUS_BOUNDARY_EVENT_BLOCKS_NEIGHBORING_TILE'
        measure['event_tile'] = {
            'status': proof,
            'raw_origin': str(origin) if origin is not None else None,
            'unique_events': len(group),
        }
        for e in group:
            e['local_offset'] = e['offset'] - origin if origin is not None else None
            e['onset_evidence'] = proof
    return result, matches.summary()


def pairing(left, right, predictions, shift):
    def key(e):
        if (
            e['status'] != 'MATCHED'
            or len(e['printed_measures']) != 1
            or e.get('local_offset') is None
        ):
            return None
        return (
            e['printed_measures'][0],
            e['staff'],
            e['voice'],
            e['local_offset'],
            e['duration'],
            e['kind'],
            e.get('chord_size'),
            e.get('member'),
        )

    aa = defaultdict(list)
    bb = defaultdict(list)
    for e in left:
        if (k := key(e)) is not None:
            aa[k].append(e)
    for e in right:
        if (k := key(e)) is not None:
            bb[k].append(e)
    from music21 import pitch

    rows = []
    for k in sorted(aa.keys() & bb.keys(), key=str):
        if len(aa[k]) != 1 or len(bb[k]) != 1:
            continue
        a, b = aa[k][0], bb[k][0]
        row = {
            'printed_measure': k[0],
            'left_id': a['id'],
            'right_id': b['id'],
            'kind': a['kind'],
            'local_onset': a['local_offset'],
            'duration': a['duration'],
            'rhythm_agrees': True,
            'status': 'UNIQUE_ALGORITHMIC_CANDIDATE_NOT_INDEPENDENT_TRUTH',
        }
        if a['kind'] == 'NOTE':
            row.update(
                left_pitch=a['pitch'],
                right_pitch=b['pitch'],
                interval_agrees=pitch.Pitch(b['pitch']).midi - pitch.Pitch(a['pitch']).midi
                == shift,
            )
            if a['id'] in predictions:
                row['frozen_target_spelling_agrees'] = predictions[a['id']] == b['pitch']
        rows.append(row)
    note_rows = [r for r in rows if r['kind'] == 'NOTE']
    rhythm = []
    for number in sorted(set(n for e in left + right for n in e['printed_measures'])):
        a = [e for e in left if e['printed_measures'] == [number]]
        b = [e for e in right if e['printed_measures'] == [number]]
        touching_unknown = any(
            e['status'] == 'AMBIGUOUS' and number in e['printed_measures'] for e in left + right
        )
        if touching_unknown:
            state, reason = (
                'AMBIGUOUS',
                'Boundary event uncertainty propagates to neighboring measures',
            )
        elif not a or not b:
            state, reason = 'UNMATCHED', 'No uniquely located recognized events on one side'
        elif any(e.get('local_offset') is None for e in a + b):
            state, reason = 'PARTIAL', 'Incomplete or unsupported recognized rhythm tile'
        else:
            signature = lambda events: sorted(
                (e['local_offset'], e['duration'], e['kind'], str(e['voice']), e['staff'])
                for e in events
            )
            state = 'MATCHED' if signature(a) == signature(b) else 'PARTIAL'
            reason = 'Pitch-independent onset/duration/rest/voice signature compared across the full printed measure'
        rhythm.append({'printed_measure': number, 'status': state, 'reason': reason})
    return {
        'pairs': rows,
        'paired_pitched_notes': len(note_rows),
        'interval_agreements': sum(r['interval_agrees'] for r in note_rows),
        'frozen_prediction_spelling_agreements': (
            sum(r.get('frozen_target_spelling_agrees', False) for r in note_rows)
            if predictions
            else None
        ),
        'paired_rests': sum(r['kind'] == 'REST' for r in rows),
        'measure_rhythm_comparison': rhythm,
        'measure_rhythm_statuses': dict(Counter(r['status'] for r in rhythm)),
        'left_unpaired_pitched_notes': sum(e['kind'] == 'NOTE' for e in left) - len(note_rows),
        'right_unpaired_pitched_notes': sum(e['kind'] == 'NOTE' for e in right) - len(note_rows),
        'independently_verified_denominator': 0,
        'musical_accuracy_percentage': None,
        'policy': 'Unique printed region + explicit existing ownership + self-contained recognized four-quarter rhythm tile + exact onset/duration/voice. Pitch is tested AFTER pairing, never a tie-break.',
    }


def source_chords(folder, graph, page, observations, segments):
    from backend.chords.parser import parse_chord
    from dataclasses import asdict

    recognized = chords(folder / 'recognized.musicxml')
    lookup = {s['omr_number']: s for s in segments}
    rows = []
    for candidate in observations['printed_chord_candidates']:
        measure = next(
            m for m in page['measures'] if m['printed_measure'] == candidate['printed_measure']
        )
        text = candidate['coordinator_read_text']
        parsed = asdict(parse_chord(text))
        box = candidate['bbox']
        typed = [
            s
            for s in graph.symbols.values()
            if s.kind == 'chord-name'
            and s.geometry.bbox
            and min(box[2], s.geometry.bbox[2]) > max(box[0], s.geometry.bbox[0])
            and min(box[3], s.geometry.bbox[3]) > max(box[1], s.geometry.bbox[1])
        ]
        words = [
            s
            for s in graph.symbols.values()
            if s.kind in {'word', 'lyric-item'}
            and s.geometry.bbox
            and min(box[2], s.geometry.bbox[2]) > max(box[0], s.geometry.bbox[0])
            and min(box[3], s.geometry.bbox[3]) > max(box[1], s.geometry.bbox[1])
        ]
        exported = [
            {'identity': k, **v}
            for k, v in recognized.items()
            if lookup[k[2]]['printed_measures'] == [candidate['printed_measure']]
        ]
        same = [
            h
            for h in exported
            if h['parsed']
            and all(h['parsed'][k] == parsed[k] for k in ('root', 'quality', 'extensions', 'bass'))
        ]
        status = (
            'MATCHED'
            if len(same) == len(exported) == 1
            else 'AMBIGUOUS' if exported else 'UNMATCHED'
        )
        rows.append(
            {
                **candidate,
                'coordinator_reading_is_independent_human_truth': False,
                'parsed_candidate': parsed,
                'status': status,
                'recognized_harmonies': exported,
                'sig_chord_names': [{'id': s.id, 'xml': s.source_xml} for s in typed],
                'overlapping_word_lyric_evidence': [
                    {'id': s.id, 'kind': s.kind, 'xml': s.source_xml} for s in words
                ],
                'text_context': [
                    {
                        'symbol_id': child.id,
                        'parents': [
                            {
                                'id': edge.source,
                                'kind': graph.symbols[edge.source].kind,
                                'attributes': dict(graph.symbols[edge.source].attributes),
                                'relations': [
                                    (r.kind, r.source, r.target)
                                    for r in graph.relations
                                    if r.source == edge.source or r.target == edge.source
                                ],
                            }
                            for edge in graph.relations
                            if edge.kind == 'contains'
                            and edge.target == child.id
                            and edge.source in graph.symbols
                        ],
                    }
                    for child in typed + words
                ],
                'omission_class': (
                    'PRESENT_IN_XML'
                    if status == 'MATCHED'
                    else (
                        'SIG_CHORD_NAME_NOT_EXPORTED'
                        if typed and not exported
                        else (
                            'NO_PERSISTED_CHORD_NAME_OR_EXPORTED_HARMONY'
                            if not typed and not exported
                            else 'SEMANTIC_OR_POSITION_AMBIGUITY'
                        )
                    )
                ),
                'lyric_confusion': (
                    'POSSIBLE_REVIEW'
                    if any(s.kind == 'lyric-item' for s in words)
                    else 'NO_LOCAL_LYRIC_ATTRIBUTION_OBSERVED'
                ),
            }
        )
    return {
        'mode': 'AUDIVERIS_ONLY',
        'candidate_method': 'Full Bb source-only strip review by coordinator; no A/G chord texts used and no source repair',
        'printed_candidates': len(rows),
        'recognized_xml_harmonies': len(recognized),
        'matched_candidates': sum(r['status'] == 'MATCHED' for r in rows),
        'missing_candidates': sum(r['status'] == 'UNMATCHED' for r in rows),
        'ambiguous_candidates': sum(r['status'] == 'AMBIGUOUS' for r in rows),
        'sig_chord_name_count': sum(s.kind == 'chord-name' for s in graph.symbols.values()),
        'independent_human_labels': 0,
        'candidates': rows,
    }


def verify_inputs(root):
    if (
        sha(root / 'baseline-manifest.json') != GT01_BASELINE_MANIFEST_SHA
        or sha(root / 'baseline-public.pem') != GT01_PUBLIC_KEY_SHA
    ):
        raise ValueError('Unexpected GT-01 baseline or public-key identity')
    frozen = verify_baseline(root)
    if sha(root / 'source-only/source.png') != frozen['source_raster_sha256']:
        raise ValueError('Original source raster hash changed')
    subprocess.run(
        [
            'openssl',
            'dgst',
            '-sha256',
            '-verify',
            str(root / 'baseline-public.pem'),
            '-signature',
            str(root / 'research-final-manifest.sig'),
            str(root / 'research-final-manifest.json'),
        ],
        check=True,
        capture_output=True,
    )
    final = json.loads((root / 'research-final-manifest.json').read_text())
    if final['final_commit'] != 'bf5903bba4a00326288c40237a7c84ff9e32183c':
        raise ValueError('Wrong GT-01 final revision')
    for field, folder in [
        ('reference_rasters', 'reference-input'),
        ('reference_recognition_artifacts', 'references'),
    ]:
        verify_files(root / folder, final[field])
    pdf = Path(json.loads((root / 'coordinator/pdf-provenance.json').read_text())['path'])
    if sha(pdf) != frozen['source_pdf_sha256']:
        raise ValueError('Original PDF hash changed')
    return {
        'baseline_manifest_sha256': sha(root / 'baseline-manifest.json'),
        'source_pdf_sha256': sha(pdf),
        'prediction_revision': frozen['code_revision'],
    }


def run(root, observations_path, out):
    if (
        out.resolve() == root.resolve()
        or root.resolve() in out.resolve().parents
        or out.resolve() in root.resolve().parents
    ):
        raise ValueError('Output overlaps GT-01 evidence')
    binding = verify_inputs(root)
    obs = json.loads(observations_path.read_text())
    out.mkdir(parents=True, exist_ok=True)
    names = [
        'measure-registration.json',
        'omr-segmentation-differences.json',
        'source-chord-coverage.json',
        'note-correspondence-diagnostic.json',
        'validation-summary.json',
    ]
    if any((out / n).exists() for n in names):
        raise ValueError('Do not overwrite study outputs')
    paths = {
        'Bb': (root / 'source-only/source.png', root / 'predictions/baseline-exec/source'),
        'A': (root / 'reference-input/A.png', root / 'references/A'),
        'G': (root / 'reference-input/G.png', root / 'references/G'),
    }
    pages = {}
    segments = {}
    events = {}
    matching = {}
    for name, (raster, folder) in paths.items():
        if sha(raster) != obs[name]['source_sha256']:
            raise ValueError('Coordinator observation/raster binding mismatch')
        with Image.open(raster) as image:
            pages[name] = registered_page(image, name, obs[name])
        graph = load_visual_graph(folder / 'recognized.omr')
        segments[name] = segmentation(graph, pages[name])
        events[name], matching[name] = mapped_events(folder, graph, pages[name])
    lengths = {len(p['measures']) for p in pages.values()}
    if len(lengths) != 1:
        raise ValueError('Printed counts disagree; human review required before cross-page mapping')
    for page in pages.values():
        for m in page['measures']:
            m['corresponding_regions'] = {
                n: {
                    'pdf_page': p['pdf_page'],
                    'system': p['measures'][m['printed_measure'] - 1]['system'],
                    'left': p['measures'][m['printed_measure'] - 1]['left']['x'],
                    'right': p['measures'][m['printed_measure'] - 1]['right']['x'],
                }
                for n, p in pages.items()
            }
    pairs = {}
    for name, shift in [('A', -1), ('G', -3)]:
        pred = read_semantics(root / f'predictions/baseline-exec/{name}/transposed.musicxml')
        pairs[name] = pairing(
            events['Bb'], events[name], {n.id: n.pitch for n in pred.notes}, shift
        )
    pairs['A_to_G'] = pairing(events['A'], events['G'], {}, -2)
    chord = source_chords(
        paths['Bb'][1],
        load_visual_graph(paths['Bb'][1] / 'recognized.omr'),
        pages['Bb'],
        obs['Bb'],
        segments['Bb'],
    )
    registration = {
        'binding': binding,
        'raster_policy': RASTER_POLICY,
        'coordinator_observations_sha256': sha(observations_path),
        'pages': pages,
        'accepted_ground_truth': False,
        'human_review_required': True,
    }
    dump(out / names[0], registration)
    dump(out / names[1], segments)
    dump(out / names[2], chord)
    dump(
        out / names[3],
        {
            'events': events,
            'matching': matching,
            'comparisons': pairs,
            'no_frozen_prediction_changed': True,
            'independent_ground_truth_denominator': 0,
        },
    )
    summary = {
        'binding': binding,
        'printed_measures_per_page': {n: len(p['measures']) for n, p in pages.items()},
        'omr_stacks': {n: dict(Counter(s['status'] for s in rows)) for n, rows in segments.items()},
        'printed_measure_mapping': {
            n: dict(
                Counter(
                    (
                        'PARTIAL'
                        if any(
                            m['printed_measure'] in s['printed_measures']
                            and s['status'] == 'PARTIAL'
                            for s in segments[n]
                        )
                        else (
                            'MATCHED'
                            if any(
                                m['printed_measure'] in s['printed_measures']
                                and s['status'] == 'MATCHED'
                                for s in segments[n]
                            )
                            else 'UNMATCHED'
                        )
                    )
                    for m in p['measures']
                )
            )
            for n, p in pages.items()
        },
        'event_statuses': {n: dict(Counter(e['status'] for e in ee)) for n, ee in events.items()},
        'comparisons': {n: {k: v for k, v in r.items() if k != 'pairs'} for n, r in pairs.items()},
        'chords': {k: v for k, v in chord.items() if k != 'candidates'},
        'independent_human_labels': 0,
        'code_sha256': sha(Path(__file__)),
        'gt01_unchanged': verify_inputs(root) == binding,
    }
    dump(out / names[4], summary)
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--gt01', type=Path, required=True)
    p.add_argument('--observations', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(run(a.gt01, a.observations, a.out), indent=2, default=str))


if __name__ == '__main__':
    main()
