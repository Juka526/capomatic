"""Fixed measure 3, source-first inventory and reused calibrated music-only renderer."""

import argparse
import copy
from fractions import Fraction
import json
import math
from pathlib import Path
import shutil

import numpy as np
from PIL import Image
from music21 import converter, harmony, key, stream

from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.evaluate_paired_ground_truth_01 import verify_baseline
from scripts.research.gt04_visual import render
from scripts.research.gt05_raster_anchor import glyph
from scripts.research.gt05_anchor_study import design, observe
from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes, line_y

BASE = 'f3b808d3fb072d521f516ef9e8f50ef54bd59756'
ROOT = Path('/private/tmp')
GT01 = ROOT / 'capomatic-v4-ground-truth-01/ground-truth-01-output'
GT04 = ROOT / 'capomatic-v4-gt04-visual/ground-truth-04-output'
GT05 = ROOT / 'capomatic-v4-gt05-anchor/gt05-anchor-output'
GT06 = ROOT / 'capomatic-v4-gt06-extended/gt06-output'
GT07 = ROOT / 'capomatic-v4-gt07-flags/gt07-flag-output'
PROTOCOL = Path(__file__).resolve().parents[2] / 'docs/V4_GT11_PROTOCOL.json'
FONT = GT04 / 'font/FreeSerif.ttf'
SOURCE_SHA = 'eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de'
MOVING_KINDS = {'head', 'head-chord', 'stem', 'ledger'}


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_bytes())


def freeze_check(root):
    frozen = read(root / 'prototype-freeze.json')
    actual = file_hashes(root)
    actual.pop('prototype-freeze.json')
    require(actual == frozen['files'], 'Historical prototype changed: ' + str(root))
    return frozen


def events_of(measure):
    return [n for n in measure.recurse().notesAndRests if not isinstance(n, harmony.ChordSymbol)]


def measure_context(measure, kind):
    local = list(measure.getElementsByClass(kind))
    return local[-1] if local else measure.getContextByClass(kind)


def event_signature(measure):
    return [
        {
            'onset': str(Fraction(n.getOffsetInHierarchy(measure))),
            'duration': str(Fraction(n.quarterLength)),
            'pitch': n.pitch.nameWithOctave if n.isNote else None,
            'kind': 'REST' if n.isRest else 'NOTE' if n.isNote else 'CHORD',
            'voice': (
                str(n.getContextByClass(stream.Voice).id)
                if n.getContextByClass(stream.Voice) is not None
                else None
            ),
            'tie': getattr(getattr(n, 'tie', None), 'type', None),
            'articulations': [type(a).__name__ for a in n.articulations],
            'expressions': [type(a).__name__ for a in n.expressions],
        }
        for n in events_of(measure)
    ]


def ledger_positions(pitch):
    position = 35 - pitch.diatonicNoteNum
    return list(
        range(6, position + 1, 2)
        if position >= 6
        else range(-6, position - 1, -2) if position <= -6 else []
    )


def unsupported_event(n, row, related_kinds, attachments):
    reasons = []
    if row['status'] != 'MATCHED':
        reasons.append('AMBIGUOUS_OR_UNMATCHED_SOURCE_EVENT')
    if n.duration.type != 'quarter' or n.duration.dots or n.duration.isGrace or n.duration.tuplets:
        reasons.append('UNSUPPORTED_DURATION_IN_REUSED_QUARTER_COMPOSER')
    if not (n.isNote or n.isRest):
        reasons.append('UNSUPPORTED_CHORD_EVENT')
    if row.get('chord_size', 1) != 1 or row.get('chord_continuation'):
        reasons.append('UNSUPPORTED_CHORD_MEMBERSHIP')
    if set(related_kinds) - MOVING_KINDS:
        reasons.append('UNSUPPORTED_CONNECTED_COMPONENT')
    if attachments or n.tie is not None or n.articulations or n.expressions or n.getSpannerSites():
        reasons.append('UNSUPPORTED_REQUIRED_ATTACHMENT')
    return reasons


def source_inventory(score, excerpt, graph, moves):
    require(excerpt['number'] == 3, 'Fixed target is printed measure 3; no substitution')
    indices = {r['omr_measure_index'] for r in excerpt['events']}
    require(len(indices) == 1 and len(score.parts) == 1, 'Ambiguous part/measure identity')
    index = next(iter(indices))
    m = list(score.parts[0].getElementsByClass(stream.Measure))[index]
    notes = events_of(m)
    rows = sorted(excerpt['events'], key=lambda r: Fraction(r['local_offset']))
    require(len(notes) == len(rows), 'MusicXML/source mapping event-count mismatch')
    require(len({r['id'] for r in rows}) == len(rows), 'Duplicate source event identity')
    result = []
    for n, row in zip(notes, rows):
        require(
            row['printed_measures'] == [3] and row['part_index'] == 1,
            'Incorrect printed measure/part',
        )
        require(
            Fraction(n.getOffsetInHierarchy(m)) == Fraction(row['local_offset'])
            and Fraction(n.quarterLength) == Fraction(row['duration']),
            'Event onset/duration mismatch',
        )
        require(
            (n.isRest and row['kind'] == 'REST')
            or (n.isNote and n.pitch.nameWithOctave == row['pitch']),
            'Source written pitch mismatch',
        )
        symbol = graph['symbols'][row['symbol_id']]
        require(
            symbol['geometry']['valid'] and symbol['staff'] == excerpt['staff']['id'],
            'Unknown source staff geometry',
        )
        bbox = symbol['geometry']['bbox']
        x = (bbox[0] + bbox[2]) / 2
        require(excerpt['left'] <= x < excerpt['right'], 'Event outside physical measure')
        connected = moves[row['id']]['connected_symbols'] if n.isNote else []
        owned = {row['symbol_id']} | {i for _, ids in connected for i in ids}
        relations = [r for r in graph['relations'] if r['source'] in owned or r['target'] in owned]
        attachments = [
            r for r in relations if any(k in r['kind'] for k in ['slur', 'articulation', 'fermata'])
        ]
        stems = [
            r for r in relations if r['kind'] == 'head-stem' and r['source'] == row['symbol_id']
        ]
        if n.isNote:
            require(
                len(stems) == 1 and dict(stems[0]['attributes']).get('head-side') == 'RIGHT',
                'Unsupported or ambiguous source stem lineage',
            )
        blockers = unsupported_event(n, row, [k for k, _ in connected], attachments)
        source_pitch = n.pitch.nameWithOctave if n.isNote else None
        expected_staff_pitch = 35 - n.pitch.diatonicNoteNum if n.isNote else None
        source_y = (
            line_y(excerpt['staff']['lines'][2], x)
            + expected_staff_pitch * excerpt['staff']['interline'] / 2
            if n.isNote
            else (bbox[1] + bbox[3]) / 2
        )
        result.append(
            {
                'source_event_id': row['id'],
                'printed_measure': 3,
                'part': row['part_index'],
                'voice': event_signature(m)[len(result)]['voice'],
                'onset': row['local_offset'],
                'duration': row['duration'],
                'written_pitch': source_pitch,
                'kind': row['kind'],
                'notehead_id': row['symbol_id'] if n.isNote else None,
                'rest_id': row['symbol_id'] if n.isRest else None,
                'stem_direction': 'up' if n.isNote else None,
                'stem_relation': stems[0] if stems else None,
                'beam_flag_relations': [
                    r for r in relations if r['kind'] in ['beam-stem', 'flag-stem']
                ],
                'ledger_positions': ledger_positions(n.pitch) if n.isNote else [],
                'source_accidental': (
                    None
                    if n.isRest or n.pitch.accidental is None
                    else {
                        'alter': n.pitch.accidental.alter,
                        'display_status': n.pitch.accidental.displayStatus,
                    }
                ),
                'attachment_relations': attachments,
                'semantic_tie': getattr(getattr(n, 'tie', None), 'type', None),
                'connected_source_symbols': connected,
                'source_physical_bbox': bbox,
                'physical_detected_center': [x, (bbox[1] + bbox[3]) / 2],
                'semantic_source_staff_y': source_y,
                'staff_pitch': expected_staff_pitch,
                'omr_grade': symbol['grade'],
                'omr_contextual_grade': symbol['contextual_grade'],
                'recognition': 'RECOGNIZED',
                'interpretation': 'UNSUPPORTED' if blockers else 'SUPPORTED',
                'renderer_capability': 'UNSUPPORTED' if blockers else 'SUPPORTED',
                'source_completeness': 'UNVERIFIED_SOURCE_COMPLETENESS',
                'required_renderer_capabilities': (
                    ['quarter_rest']
                    if n.isRest
                    else ['filled_head', 'stem'] + (['ledger'] if ledger_positions(n.pitch) else [])
                ),
                'blockers': blockers,
            }
        )
    spatial = {
        s['id']
        for s in graph['symbols'].values()
        if s['kind'] in ('head', 'rest')
        and s['staff'] == excerpt['staff']['id']
        and s['geometry']['bbox']
        and excerpt['left']
        <= (s['geometry']['bbox'][0] + s['geometry']['bbox'][2]) / 2
        < excerpt['right']
    }
    semantic_ids = {r['symbol_id'] for r in rows}
    require(spatial == semantic_ids, 'Unaccounted persisted head/rest in physical source measure')
    source_attachments = [
        {'event_id': r['source_event_id'], 'blockers': r['blockers']}
        for r in result
        if r['blockers']
    ]
    return {
        'printed_measure': 3,
        'omr_measure_index': index,
        'omr_measure_number': m.number,
        'part_count': 1,
        'staff': excerpt['staff'],
        'system': excerpt['system'],
        'left': excerpt['left'],
        'right': excerpt['right'],
        'written_key_fifths': measure_context(m, key.KeySignature).sharps,
        'clef': type(measure_context(m, 'Clef')).__name__,
        'time_signature': (
            str(m.getContextByClass('TimeSignature'))
            if m.getContextByClass('TimeSignature')
            else 'NOT_SERIALIZED_IN_RECOGNIZED_CONTEXT'
        ),
        'recognized_quarter_length_total': str(sum(Fraction(n.quarterLength) for n in notes)),
        'source_signature': event_signature(m),
        'events': result,
        'persisted_heads_and_rests_accounted_for': True,
        'source_attachments': source_attachments,
        'recognized_harmony_count': len(list(m.recurse().getElementsByClass(harmony.ChordSymbol))),
        'recognized_musicxml_lyric_items': sum(len(n.lyrics) for n in notes),
        'independent_source_labels': 0,
        'SOURCE_RECOGNITION_COMPLETENESS': 'UNVERIFIED',
        'independence_limit': 'Agreement between MusicXML and the same OMR graph is not independent source completeness evidence',
    }


def whole_verdict(source, rendering, visual, integrity):
    if rendering == 'BLOCKED':
        return 'COMPLETE_MEASURE_BLOCKED'
    if (
        source == 'COMPLETE'
        and rendering == 'COMPLETE'
        and visual == 'ACCEPTABLE_FOR_EXPERIMENT'
        and integrity
    ):
        return 'COMPLETE_MEASURE_RENDERED_WITH_LIMITATIONS'
    return 'COMPLETE_MEASURE_INCOMPLETE'


def prepare(inputs):
    inputs = Path(inputs)
    require(
        not (inputs / 'source-inventory-freeze.json').exists(), 'Source inventory is already frozen'
    )
    require(
        sha(GT01 / 'baseline-manifest.json')
        == '68f327663cf91011f62b16db770cba4e06aea1323d0b06bade1cbfe2c904ad49',
        'Wrong baseline identity',
    )
    require(
        sha(GT01 / 'baseline-public.pem')
        == 'b55a88e832c781eaf96e1faf8b09accb8909224e04e675330d95e4596544f0b7',
        'Wrong baseline trust key',
    )
    frozen = verify_baseline(GT01)  # Source-derived predictions only; no reference folders opened.
    for root in [GT04 / 'visual-prototype', GT05 / 'revised-visual-prototype', GT06, GT07]:
        freeze_check(root)
    design(FONT)
    gate = read(GT05 / 'independent-tests/gate.json')
    require(
        gate['passed']
        and gate['algorithm_sha256'] == sha(Path(__file__).with_name('gt05_raster_anchor.py')),
        'Validated anchor gate mismatch',
    )
    selection = GT04 / 'render-input/selection.json'
    require(
        sha(selection) == read(GT04 / 'visual-prototype/prototype-freeze.json')['selection_sha256'],
        'Historical source selection changed',
    )
    spec = read(selection)
    excerpt = next(e for e in spec['excerpts'] if e['number'] == 3)
    baseline = GT01 / 'predictions/baseline-exec'
    graph = read(baseline / 'source/visual-graph.json')
    require(
        excerpt['staff'] == next(s for s in graph['staves'] if s['id'] == excerpt['staff']['id']),
        'Source staff geometry mismatch',
    )
    require(spec['protected'] == graph['text_protected_regions'], 'Protection changed')
    require(
        sha(baseline / 'source/source.png') == spec['source_sha256'] == SOURCE_SHA,
        'Wrong Bb source raster',
    )
    score = converter.parse(str(baseline / 'source/recognized.musicxml'))
    moves = {n['semantic_id']: n for n in read(baseline / 'A/plan.json')['note_moves']}
    inv = source_inventory(score, excerpt, graph, moves)
    inputs.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(baseline / 'source/source.png', inputs / 'source.png')
    single = copy.deepcopy(spec)
    single['selected'] = [3]
    single['excerpts'] = [copy.deepcopy(excerpt)]
    # Existing targets are source-derived predictions, not supplied A/G reference notation.
    dump(inputs / 'selection.json', single)
    dump(inputs / 'source-event-inventory.json', inv)
    local_text = []
    for symbol in graph['symbols'].values():
        if symbol['kind'] not in ['word', 'sentence', 'lyric-line', 'lyric-item', 'chord-name']:
            continue
        box = symbol['geometry']['bbox']
        loc = symbol['geometry']['location']
        if (
            box
            and box[0] < excerpt['right']
            and box[2] > excerpt['left']
            and 350 < box[3]
            and box[1] < 770
        ) or (loc and excerpt['left'] <= loc[0] < excerpt['right'] and 350 < loc[1] < 770):
            local_text.append(
                {
                    'id': symbol['id'],
                    'kind': symbol['kind'],
                    'geometry': symbol['geometry'],
                    'attributes': symbol['attributes'],
                }
            )
    audit = {
        'SOURCE_RECOGNITION_COMPLETENESS': 'UNVERIFIED',
        'independent_human_labels': 0,
        'musical_ground_truth_denominator': 0,
        'recognized_music_layer_events': len(inv['events']),
        'missing_music_events': 'UNKNOWN_WITHOUT_INDEPENDENT_SOURCE_ACCOUNTING',
        'printed_chord_candidates': [
            {
                'text_candidate': 'F',
                'recognition': 'MISSING_FROM_OMR',
                'basis': 'Agent source-only crop inspection, not independent transcription',
                'included_in_music_layer': False,
            }
        ],
        'lyrics': {
            'visible_in_original': True,
            'musicxml_lyric_items': inv['recognized_musicxml_lyric_items'],
            'local_omr_text_objects': local_text,
            'classification': 'UNVERIFIED_SOURCE_COMPLETENESS',
            'rendered': False,
            'source_review_crop_limit': 'Inherited GT05 viewport ends y=657; lower lyric row is partially cropped. No full lyric-preservation claim.',
        },
        'recognized_harmonies_in_measure': inv['recognized_harmony_count'],
        'semantic_vs_graph_agreement_is_not_independence': True,
        'unsupported_known_music_layer_events': inv['source_attachments'],
        'source_only_visual_inspection': 'Quarter rest, three noteheads/stems, F chord candidate and Korean lyrics observed; not independent human ground truth',
        'reference_pages_used': False,
    }
    dump(inputs / 'source-completeness-audit.json', audit)
    paths = {
        str(p): sha(p)
        for root in [
            GT04 / 'render-input',
            GT05 / 'independent-tests',
            GT05 / 'revised-visual-prototype',
            GT06,
            GT07,
        ]
        for p in root.rglob('*')
        if p.is_file()
    }
    for p in [
        PROTOCOL,
        FONT,
        GT01 / 'baseline-manifest.json',
        GT01 / 'baseline-public.pem',
        baseline / 'source/recognized.musicxml',
        baseline / 'source/source.png',
        baseline / 'source/recognized.omr',
        baseline / 'source/visual-graph.json',
        baseline / 'A/transposed.musicxml',
        baseline / 'G/transposed.musicxml',
    ]:
        paths[str(p)] = sha(p)
    dump(
        inputs / 'source-inventory-freeze.json',
        {
            'phase': 'SOURCE_INVENTORY_FROZEN_BEFORE_RENDERING',
            'base': BASE,
            'printed_measure': 3,
            'source_pdf_sha256': frozen['source_pdf_sha256'],
            'source_sha256': SOURCE_SHA,
            'files': file_hashes(inputs),
            'historical_inputs_sha256': paths,
            'source_only_references': 'No supplied A/G reference pages parsed or opened',
        },
    )
    return inv


def verify_inventory(inputs):
    frozen = read(inputs / 'source-inventory-freeze.json')
    current = file_hashes(inputs)
    current.pop('source-inventory-freeze.json')
    require(current == frozen['files'], 'Frozen source inventory changed')
    require(
        all(sha(p) == v for p, v in frozen['historical_inputs_sha256'].items()),
        'Historical input changed',
    )
    return frozen


def required_parts(excerpt, target):
    from music21 import pitch

    names = {'staff', 'bar'}
    ledger_counts = {}
    for event in excerpt['events']:
        ident = event['id']
        if event['kind'] == 'REST':
            names.add(ident + ':rest')
            continue
        p = pitch.Pitch(event['frozen'][target]['target_pitch'])
        names.update([ident + ':head', ident + ':stem'])
        positions = ledger_positions(p)
        ledger_counts[ident] = len(positions)
        if positions:
            names.add(ident + ':ledger')
    return names, ledger_counts


def row_bands(mask):
    rows = np.flatnonzero(np.asarray(mask).any(axis=1))
    bands = []
    for y in rows:
        if not bands or y > bands[-1][-1] + 1:
            bands.append([int(y)])
        else:
            bands[-1].append(int(y))
    return bands


def snapshot_parts(parts, expected, out):
    """Persist exact producer bitmaps; never infer components by bbox subtraction."""
    require(set(parts) == expected, 'Required recognized component missing/duplicated/unexpected')
    out.mkdir(parents=True, exist_ok=False)
    manifests = []
    size = next(iter(parts.values())).size
    for name, mask in sorted(parts.items()):
        require(
            mask.mode == 'L' and mask.size == size and mask.getbbox(), 'Invalid/empty component'
        )
        path = out / (name.replace(':', '_') + '.png')
        mask.save(path)
        manifests.append(
            {
                'component_id': name,
                'file': str(path.name),
                'mode': 'L',
                'page_size': list(size),
                'bounds': list(mask.getbbox()),
                'nonzero_alpha_pixels': int(np.count_nonzero(np.asarray(mask))),
                'alpha_bytes_sha256': __import__('hashlib').sha256(mask.tobytes()).hexdigest(),
                'png_sha256': sha(path),
                'geometry_is_original_page_coordinates': True,
            }
        )
    full = np.maximum.reduce([np.asarray(m) for m in parts.values()])
    moving = np.maximum.reduce(
        [np.asarray(m) for n, m in parts.items() if n not in {'staff', 'bar'}]
    )
    Image.fromarray(full).save(out / 'notation-alpha.png')
    Image.fromarray(moving).save(out / 'music-only-alpha.png')
    dump(
        out / 'manifest.json',
        {
            'components': manifests,
            'full_union_sha256': sha(out / 'notation-alpha.png'),
            'music_only_union_sha256': sha(out / 'music-only-alpha.png'),
            'source_ink_ownership_authorized': False,
            'component_origin': 'copies emitted by reused composer, not reconstructed from its union',
        },
    )
    return manifests, moving


def semantic_targets(score, excerpt, out):
    source_measure = list(score.parts[0].getElementsByClass(stream.Measure))[
        excerpt['events'][0]['omr_measure_index']
    ]
    source_sig = event_signature(source_measure)
    reports = {}
    updated = copy.deepcopy(excerpt)
    for name, shift in [('A', -1), ('G', -3)]:
        target = copy.deepcopy(score)
        summary = transpose_score(target, shift, 'key')
        memory = validate(score, target, shift, 'key', summary).to_dict()
        target.write('musicxml', fp=str(out / (name + '-transposed.musicxml')))
        serialized = converter.parse(str(out / (name + '-transposed.musicxml')))
        roundtrip = validate(score, serialized, shift, 'key', summary).to_dict()
        m = list(serialized.parts[0].getElementsByClass(stream.Measure))[
            excerpt['events'][0]['omr_measure_index']
        ]
        sig = event_signature(m)
        require(len(sig) == len(source_sig), 'Target event count changed')
        stable_fields = [
            'onset',
            'duration',
            'voice',
            'kind',
            'tie',
            'articulations',
            'expressions',
        ]
        stable = all(all(a[k] == b[k] for k in stable_fields) for a, b in zip(source_sig, sig))
        from music21 import pitch

        for row, a, b in zip(updated['events'], source_sig, sig):
            if row['kind'] == 'REST':
                continue
            target_pitch = pitch.Pitch(b['pitch'])
            source_pitch = pitch.Pitch(a['pitch'])
            require(target_pitch.midi - source_pitch.midi == shift, 'Pitch interval changed')
            x = row['frozen'][name]['detected_head_x']
            staff = excerpt['staff']
            target_y = (
                line_y(staff['lines'][2], x)
                + (35 - target_pitch.diatonicNoteNum) * staff['interline'] / 2
            )
            source_y = (
                line_y(staff['lines'][2], x)
                + (35 - source_pitch.diatonicNoteNum) * staff['interline'] / 2
            )
            require(
                b['pitch'] == row['frozen'][name]['target_pitch']
                and abs(target_y - row['frozen'][name]['absolute_target_staff_y']) < 1e-8,
                'Recomputed V3 pitch/staff coordinate differs from frozen source-derived prediction',
            )
            row['frozen'][name].update(
                absolute_target_staff_y=target_y,
                corrected_semantic_source_staff_y=source_y,
                target_pitch=b['pitch'],
            )
            expected_alter = key.Key('A' if name == 'A' else 'G').accidentalByStep(
                target_pitch.step
            )
            require(
                (target_pitch.accidental.alter if target_pitch.accidental else 0)
                == (expected_alter.alter if expected_alter else 0),
                'Unsupported required explicit accidental',
            )
        reports[name] = {
            'summary': summary,
            'in_memory_full_guard': memory,
            'serialized_full_guard': roundtrip,
            'voice_onset_duration_order_tie_articulation_preserved': stable,
            'selected_measure_target_signature': sig,
            'target_key_fifths': measure_context(m, key.KeySignature).sharps,
        }
    return updated, reports


def run(inputs, out):
    inputs = Path(inputs)
    out = Path(out)
    require(not out.exists(), 'New GT11 output required; historical outputs never overwritten')
    for root in [GT01, GT04, GT05, GT06, GT07, inputs]:
        require(
            root.resolve() not in [out.resolve(), *out.resolve().parents],
            'Output inside immutable evidence',
        )
    frozen = verify_inventory(inputs)
    inv = read(inputs / 'source-event-inventory.json')
    require(
        not inv['source_attachments'],
        'Unsupported required source notation; fixed measure cannot be substituted',
    )
    out.mkdir(parents=True)
    for filename in ['source-event-inventory.json', 'source-completeness-audit.json']:
        shutil.copyfile(inputs / filename, out / filename)
    source = converter.parse(str(GT01 / 'predictions/baseline-exec/source/recognized.musicxml'))
    spec = read(inputs / 'selection.json')
    excerpt, guards = semantic_targets(source, spec['excerpts'][0], out)
    dump(out / 'semantic-integrity.json', guards)
    all_integrity = all(
        v['in_memory_full_guard']['ok']
        and v['serialized_full_guard']['ok']
        and v['voice_onset_duration_order_tie_articulation_preserved']
        for v in guards.values()
    )
    if not all_integrity:
        dump(
            out / 'validation-summary.json',
            {
                'overall': 'COMPLETE_MEASURE_BLOCKED',
                'reason': 'Unchanged full integrity or supplementary identity failed',
                'guards': guards,
            },
        )
        return 'COMPLETE_MEASURE_BLOCKED'
    spec['excerpts'] = [excerpt]
    spec['guards'] = {k: g['serialized_full_guard'] for k, g in guards.items()}
    render_inputs = out / 'render-input'
    render_inputs.mkdir()
    dump(render_inputs / 'selection.json', spec)
    shutil.copyfile(inputs / 'source.png', render_inputs / 'source.png')
    recorded = {}
    counts = {}
    new_masks = {}

    def capture(number, target, parts):
        require(number == 3, 'Unexpected measure emitted')
        names, ledger_counts = required_parts(excerpt, target)
        manifests, moving = snapshot_parts(parts, names, out / 'components' / target)
        counts[target] = {
            'component_count': len(manifests),
            'music_component_count': len(manifests) - 2,
            'expected_ledger_lines': ledger_counts,
            'required_component_names': sorted(names),
            'actual_component_names': sorted(parts),
            'component_inventory_complete': True,
            'ledger_contacts': [],
        }
        for row in excerpt['events']:
            if row['kind'] == 'REST':
                continue
            ident = row['id']
            l = ident + ':ledger'
            if l in parts:
                bands = row_bands(parts[l])
                require(len(bands) == ledger_counts[ident], 'Missing or doubled ledger lines')
                stem = np.asarray(parts[ident + ':stem']) > 0
                led = np.asarray(parts[l]) > 0
                require(np.any(stem & led), 'Required ledger group disconnected from stem')
                counts[target]['ledger_contacts'].append(
                    {
                        'semantic_id': ident,
                        'row_bands': [[b[0], b[-1]] for b in bands],
                        'stem_contact_pixels': int(np.count_nonzero(stem & led)),
                        'head_contact_pixels': int(
                            np.count_nonzero((np.asarray(parts[ident + ':head']) > 0) & led)
                        ),
                    }
                )
        recorded[target] = manifests
        new_masks[target] = moving

    render(render_inputs, FONT, out / 'render-engine', glyph_renderer=glyph, parts_observer=capture)
    engine = read(out / 'render-engine/rendering-metrics.json')
    for filename in [
        'original-bb.png',
        'predicted-a.png',
        'predicted-g.png',
        'comparison-contact-sheet.png',
    ]:
        shutil.copyfile(out / 'render-engine' / filename, out / filename)
    for metric in engine['metrics']:
        target = metric['target']
        parts_dir = out / 'components' / target
        require(
            (parts_dir / 'notation-alpha.png').read_bytes()
            == (out / 'render-engine' / f'm3-{target}-notation-alpha.png').read_bytes(),
            'Component snapshot union differs from actual rendered bitmap',
        )
        # Historical m3 is a raster regression control, not a replacement reference score.
        require(
            sha(parts_dir / 'notation-alpha.png')
            == sha(GT05 / 'revised-visual-prototype' / f'm3-{target}-notation-alpha.png'),
            'Validated GT05 measure-3 raster regression changed',
        )
        require(
            [n['semantic_id'] for n in metric['events']]
            == [n['source_event_id'] for n in inv['events']],
            'Missing or reordered rendered event',
        )
        for info in metric['events']:
            name = info['semantic_id'] + (':head' if info['kind'] == 'NOTE' else ':rest')
            mask = Image.open(parts_dir / (name.replace(':', '_') + '.png'))
            # Independent pixel measurement, rather than trusting helper-reported residuals.
            anchor = info.get('requested_anchor', info['font_outline_anchor'])
            measurement = observe(mask, anchor)
            require(
                all(abs(v) <= 0.5 for v in measurement['residual']),
                'Raster placement exceeds unchanged .5px limit',
            )
            info['independently_computed_raster_measurement'] = measurement
        protected = np.zeros(new_masks[target].shape, bool)
        for region in spec['protected']:
            x0, y0, x1, y1 = region['bbox']
            protected[math.floor(y0) : math.ceil(y1), math.floor(x0) : math.ceil(x1)] = True
        metric['all_protected_envelope_contact_pixels'] = int(
            np.count_nonzero((new_masks[target] > 0) & protected)
        )
        metric['component_accounting'] = counts[target]
        metric['recognized_quarter_length_total'] = inv['recognized_quarter_length_total']
        metric['onsets'] = [e['onset'] for e in inv['events']]
        metric['voices'] = [e['voice'] for e in inv['events']]
        metric['GT05_m3_alpha_byte_regression'] = 'PASS'
    complete = all(
        m['missing_semantic_events'] == m['duplicated_semantic_events'] == 0
        and m['checks_pass']
        and m['component_accounting']['component_inventory_complete']
        for m in engine['metrics']
    )
    engine.update(
        {
            'study': 'GT11_FIXED_COMPLETE_RECOGNIZED_MEASURE_LAYER',
            'source_inventory_freeze_sha256': sha(inputs / 'source-inventory-freeze.json'),
            'completion_levels': {
                'SOURCE_RECOGNITION_COMPLETENESS': 'UNVERIFIED',
                'RENDERING_COMPLETENESS': 'COMPLETE' if complete else 'INCOMPLETE',
                'VISUAL_QUALITY': 'UNVERIFIED',
            },
            'overall': 'COMPLETE_MEASURE_INCOMPLETE',
            'full_integrity': guards,
            'all_integrity_passed': all_integrity,
            'component_masks_saved': True,
            'source_completeness_not_inferred_from_OMR_consistency': True,
            'completion_verdict_phase': 'PREDICTION_FREEZE_BEFORE_AGENT_VISUAL_INSPECTION',
            'new_visual_capability_claim': False,
            'measurable_progress': 'Four-event whole-measure accounting plus exact source/target identity and 9 moving component masks per target; no claimed pixel-quality improvement over GT05 m3',
        }
    )
    dump(out / 'rendering-metrics.json', engine)
    dump(
        out / 'unsupported-elements.json',
        {
            'required_recognized_music_layer_components_unrendered': [],
            'present_outside_authorized_layer': [
                'F chord candidate missing from source MusicXML',
                'Korean lyrics absent from target layers',
            ],
            'not_required_in_selected_recognized_stream': [
                'beams',
                'flags',
                'ties',
                'slurs',
                'articulations',
                'explicit accidentals',
            ],
            'context_only_not_engraved': [
                'G clef',
                'A/G key signatures (mid-system context supplied as text)',
            ],
            'unknown_source_omissions': 'No independent source completeness evidence',
            'no_lyric_composite': True,
            'no_source_music_removal': True,
            'generic_engine_limitations': 'render-engine/rendering-limitations.json describes the reused quarter composer, not all GT06/07 capabilities',
        },
    )
    verify_inventory(inputs)
    dump(
        out / 'prediction-freeze.json',
        {
            'phase': 'PREDICTIONS_FROZEN_BEFORE_VISUAL_REVIEW_OR_REFERENCE_ACCESS',
            'base': BASE,
            'source_inventory_freeze_sha256': sha(inputs / 'source-inventory-freeze.json'),
            'files': file_hashes(out),
            'reference_pages_accessed': False,
            'glyph_algorithm_sha256': sha(Path(__file__).with_name('gt05_raster_anchor.py')),
            'research_composer_sha256': sha(Path(__file__).with_name('gt04_visual.py')),
            'study_code_sha256': sha(Path(__file__)),
        },
    )
    return engine['overall']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare', 'render'])
    parser.add_argument('--inputs', type=Path, default=Path('gt11-input'))
    parser.add_argument('--out', type=Path, default=Path('gt11-output'))
    args = parser.parse_args()
    print(
        prepare(args.inputs)['SOURCE_RECOGNITION_COMPLETENESS']
        if args.phase == 'prepare'
        else run(args.inputs, args.out)
    )
