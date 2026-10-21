"""Bounded owner interpretation integration, using frozen standalone layers only."""

import argparse
import copy
from fractions import Fraction
from pathlib import Path

import numpy as np
from music21 import converter, harmony, spanner, stream, tie
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.chords import chord_text
from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt11_complete_measure import events_of, read, require
from scripts.research.gt13a2_provisional import curve_mask, translated_curve, ink_distance
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.gt16_fourth_system import repeat_signature
from scripts.research.gt17_fifth_system import SOURCE_DIR
from scripts.research.gt17b_full_score import binding, page, combine, export_pdf
from scripts.research.gt17b_post_audit import candidate_semantics, EXPECTED
from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes

ROOT = Path(__file__).resolve().parents[2]
BASE = Path('/private/tmp/capomatic-v4-gt17b/gt17b-final-output')
START = '1c532c4a6cfa332a50e889740088aed064511996'
SIZE = (2520, 3564)
# Agent-measured cubic centerlines from source-only native crops, not glyph ownership.
# Their identities/interpretations are owner-approved; numerical geometry is diagnostic.
CURVES = [
    {
        'case': 'missing-tie-m21-15/4',
        'kind': 'tie',
        'system': 6,
        'points': [[1206, 2208], [1222, 2191], [1259, 2191], [1275, 2208]],
    },
    {
        'case': 'missing-tie-m31-5/2',
        'kind': 'slur',
        'system': 8,
        'points': [[1144, 2909], [1160, 2892], [1200, 2892], [1216, 2909]],
    },
    {
        'case': 'missing-tie-m33-5/2',
        'kind': 'tie',
        'system': 8,
        'points': [[2186, 2909], [2202, 2892], [2241, 2892], [2257, 2909]],
    },
    {
        'case': 'missing-tie-m35-11/4',
        'kind': 'tie',
        'system': 9,
        'points': [[1321, 3259], [1337, 3242], [1376, 3242], [1392, 3259]],
    },
]


def core_signature(score):
    return [
        [
            (
                str(Fraction(n.getOffsetInHierarchy(m))),
                str(Fraction(n.quarterLength)),
                n.pitch.nameWithOctave if n.isNote else 'REST',
            )
            for n in events_of(m)
        ]
        for m in score.parts[0].getElementsByClass(stream.Measure)
    ]


def at(score, measure, onset):
    m = list(score.parts[0].getElementsByClass(stream.Measure))[measure - 1]
    notes = [n for n in events_of(m) if Fraction(n.getOffsetInHierarchy(m)) == Fraction(onset)]
    require(len(notes) == 1 and notes[0].isNote, 'Nonunique endpoint')
    return notes[0]


def verify_endpoint_pair(score, inventory, graph, case, spec):
    """Fail closed on conflicting identity, staff registration, role or adjacency."""
    ends = [
        next(e for e in inventory['events'] if e['symbol_id'] == sid)
        for sid in case['endpoint_source_ids']
    ]
    require(len({e['symbol_id'] for e in ends}) == 2, 'Duplicate endpoint')
    addresses = [(case['measure'], case['onset']), (case['to_measure'], case['to_onset'])]
    notes = [at(score, m, o) for m, o in addresses]
    for index, (e, n, address) in enumerate(zip(ends, notes, addresses)):
        require((e['printed_measure'], e['onset']) == address, 'Endpoint address mismatch')
        require(e['pitch'] == n.pitch.nameWithOctave, 'Endpoint pitch mismatch')
        require(n.tie is None and e['tie'] is None, 'Conflicting existing tie role')
        s = graph['symbols'][e['symbol_id']]
        require(
            s['kind'] == 'head' and s['geometry']['bbox'] == e['source_bbox'],
            'Original head identity/bounds mismatch',
        )
        require(s['system'] == f'sheet#1:system:{spec["system"]}', 'Wrong endpoint system')
        staff = next(s for s in graph['staves'] if s['id'] == e['source_symbol']['staff'])
        require(
            s['pitch_position'] == 35 - n.pitch.diatonicNoteNum,
            'Written pitch contradicts persisted staff position',
        )
        require(staff['system'] == s['system'], 'Staff identity mismatch')
        p = spec['points'][0 if index == 0 else -1]
        b = e['source_bbox']
        require(
            b[0] <= p[0] < b[2] and 0 < b[1] - p[1] <= staff['interline'] * 1.5,
            'Curve endpoint not locally above its source head',
        )
    require(ends[0]['voice'] == ends[1]['voice'], 'Different endpoint voices')
    ordered = [e['symbol_id'] for e in inventory['events']]
    require(
        ordered.index(ends[1]['symbol_id']) == ordered.index(ends[0]['symbol_id']) + 1,
        'Intervening event / ambiguous endpoint pairing',
    )
    x0, y0, x1, y1 = case['source_window']
    require(
        all(x0 <= x < x1 and y0 <= y < y1 for x, y in spec['points']),
        'Curve escapes reviewed source window',
    )
    require(spec['points'][0][0] < spec['points'][-1][0], 'Reversed curve')
    if spec['kind'] == 'tie':
        require(notes[0].pitch == notes[1].pitch, 'Unequal pitch cannot be a tie')
    else:
        require(
            spec['kind'] == 'slur' and case['measure'] == case['to_measure'],
            'Unsupported slur context',
        )
    return ends, notes


def integrate(source, inventory, graph):
    revised, added = candidate_semantics(source, inventory)
    evidence = []
    for spec in CURVES:
        case = next(c for c in inventory['unresolved_objects'] if c['id'] == spec['case'])
        ends, notes = verify_endpoint_pair(revised, inventory, graph, case, spec)
        if spec['kind'] == 'tie':
            notes[0].tie, notes[1].tie = tie.Tie('start'), tie.Tie('stop')
            notes[0].tie.placement = notes[1].tie.placement = 'above'
        else:
            curve = spanner.Slur(*notes)
            curve.placement = 'above'
            revised.insert(0, curve)
        evidence.append(
            {
                **spec,
                'source_case': copy.deepcopy(case),
                'endpoint_event_ids': [e['id'] for e in ends],
                'endpoint_source_ids': [e['symbol_id'] for e in ends],
                'recognized_source_pitches': [e['pitch'] for e in ends],
                'classification': 'OWNER_VERIFIED_CURVE_INTERPRETATION',
                'endpoint_validation': 'PASS_SOURCE_ID_STAFF_GEOMETRY_AND_ADJACENCY',
                'geometry_classification': 'AGENT_MEASURED_SOURCE_CUBIC_NOT_INDEPENDENT',
                'original_persisted_curve_id': None,
                'source_omr_modified': False,
            }
        )
    require(core_signature(source) == core_signature(revised), 'Changed pitch/rhythm/event core')
    require(repeat_signature(source) == repeat_signature(revised), 'Changed repeat semantics')
    return revised, evidence, added


def relationship_signature(score, evidence):
    result = []
    for c in evidence:
        src = c['source_case']
        a = at(score, src['measure'], src['onset'])
        b = at(score, src['to_measure'], src['to_onset'])
        if c['kind'] == 'tie':
            require(
                a.pitch == b.pitch
                and a.tie
                and b.tie
                and (a.tie.type, b.tie.type) == ('start', 'stop'),
                'Serialized tie changed',
            )
        else:
            matches = [
                s
                for s in score.recurse().getElementsByClass(spanner.Slur)
                if list(s.getSpannedElements()) == [a, b]
            ]
            require(len(matches) == 1 and not a.tie and not b.tie, 'Serialized slur changed')
        result.append(
            {
                'case': c['case'],
                'kind': c['kind'],
                'pitches': [a.pitch.nameWithOctave, b.pitch.nameWithOctave],
                'roles': [a.tie.type if a.tie else None, b.tie.type if b.tie else None],
            }
        )
    return result


def interpret_inventory(inventory):
    inv = copy.deepcopy(inventory)
    for c in inv['chords']:
        c['classification'] = 'OWNER_VERIFIED_SOURCE_CHORD_AND_PLACEMENT'
    for l in inv['lyrics']:
        l['wording_and_row_status'] = 'OWNER_VERIFIED_SOURCE'
        l['association_status'] = 'OMR_PROVISIONAL_NOT_OWNER_VERIFIED'
        l['classification'] = 'OWNER_VERIFIED_TEXT_WITH_PROVISIONAL_ONSET'
    for c in inv['continuations']:
        c['classification'] = 'AGENT_VISUAL_CANDIDATE'
        c['association_status'] = 'NOT_NEWLY_OWNER_VERIFIED'
    inv['repeat_playback'] = 'UNRESOLVED'
    inv['independent_ground_truth'] = 0
    return inv


def verify_manifest(folder, filename):
    manifest = read(folder / filename)
    for name, digest in manifest['files'].items():
        require(sha(folder / name) == digest, f'Frozen evidence mismatch: {folder / name}')
    return sha(folder / filename)


def component_masks(target, system):
    folder = BASE / f'{target}-system-{system}-components'
    masks = {}
    for item in read(folder / 'component-map.json'):
        require(sha(folder / item['file']) == item['sha256'], 'Component hash mismatch')
        b = item['bbox_local']
        box = (b[0], b[1] + item['page_origin_y'], b[2], b[3] + item['page_origin_y'])
        masks[item['id']] = (Image.open(folder / item['file']).copy(), box)
    return masks


def permitted_curve_contact(
    kind, object_kind, source_measure, destination_measure, boundary_x, obstacle_bbox
):
    return (
        object_kind == 'barline'
        and kind == 'tie'
        and destination_measure == source_measure + 1
        and obstacle_bbox[0] <= boundary_x <= obstacle_bbox[2]
    )


def new_curve_layers(target, inventory, evidence, report, graph):
    layers, metrics = {}, []
    target_events = {e['event_id']: e for s in report['systems'] for e in s['events']}
    components = {}
    for c in evidence:
        sys = c['system']
        if sys not in components:
            components[sys] = component_masks(target, sys)
        ends = [
            next(e for e in inventory['events'] if e['id'] == eid)
            for eid in c['endpoint_event_ids']
        ]
        deltas = [
            target_events[e['id']]['target_staff_coordinate_page'][1]
            - e['physical_source_center'][1]
            for e in ends
        ]
        points = translated_curve(c['points'], *deltas)
        p = curve_mask(SIZE, points)
        b = p.getbbox()
        require(
            b and b[0] > 0 and b[1] > 0 and b[2] < SIZE[0] and b[3] < SIZE[1], 'New curve clipped'
        )
        hits = []
        for name, (mask, box) in components[sys].items():
            count = int(np.count_nonzero((np.asarray(p.crop(box)) > 0) & (np.asarray(mask) > 0)))
            if not count:
                continue
            # A curve can cross staff ink; a barline only for its adjacent-measure tie.
            allowed = name == 'staff'
            if graph['symbols'].get(name, {}).get('kind') == 'barline' and c['kind'] == 'tie':
                src = c['source_case']
                system = next(s for s in inventory['systems'] if s['system'] == sys)
                m = next(m for m in system['measures'] if m['printed_measure'] == src['measure'])
                allowed = permitted_curve_contact(
                    c['kind'],
                    graph['symbols'][name]['kind'],
                    src['measure'],
                    src['to_measure'],
                    m['omr_bounds'][2],
                    box,
                )
            require(allowed, f'Unexpected new curve collision: {c["case"]}/{name}/{count}')
            hits.append(
                {
                    'component': name,
                    'pixels': count,
                    'classification': 'INTENTIONAL_STAFF_OR_OWN_BARLINE',
                }
            )
        require(
            not any(np.any((np.asarray(p) > 0) & (np.asarray(q) > 0)) for q in layers.values()),
            'New curve/curve collision',
        )
        layers[c['case']] = p
        gaps = []
        for e, endpoint in zip(ends, [points[0], points[-1]]):
            h, box = components[sys][e['id'] + ':head']
            pixels = np.argwhere(np.asarray(h) > 0)
            pixels = pixels + np.array([box[1], box[0]])
            gaps.append(
                float(
                    np.sqrt(
                        ((pixels - np.array([round(endpoint[1]), round(endpoint[0])])) ** 2).sum(
                            axis=1
                        )
                    ).min()
                )
            )
            # Curves conventionally detach from heads. Bound the gap to local staff spacing.
            staff = next(s['staff'] for s in inventory['systems'] if s['system'] == sys)
            require(0 < gaps[-1] <= staff['interline'] * 1.5, 'Detached/overlapping curve endpoint')
        metrics.append(
            {
                'case': c['case'],
                'kind': c['kind'],
                'target_curve': points,
                'endpoint_head_center_clearances_px': gaps,
                'actual_contacts': hits,
                'unexpected_contacts': 0,
                'clipped': False,
                'endpoint_geometry': 'PRESERVED_SOURCE_RELATIVE_OFFSETS',
            }
        )
    return layers, metrics


def run(out):
    require(not out.exists(), 'Fresh output directory required')
    out.mkdir(parents=True)
    baseline_hashes = file_hashes(BASE)
    freeze = verify_manifest(BASE, 'prediction-freeze.json')
    verify_manifest(BASE / 'post-freeze-semantic-audit', 'audit-freeze.json')
    history, src_hashes = binding(out)
    original_owner = read(out / 'owner-interpretation-layer.json')
    inventory = read(BASE / 'full-source-event-inventory.json')
    graph = read(SOURCE_DIR / 'visual-graph.json')
    source = converter.parse(str(BASE / 'owner-augmented-source.musicxml'))
    revised, evidence, added = integrate(source, inventory, graph)
    inv = interpret_inventory(inventory)
    for c in evidence:
        for index, eid in enumerate(c['endpoint_event_ids']):
            e = next(e for e in inv['events'] if e['id'] == eid)
            e['owner_approved_curve_case'] = c['case']
            e['interpreted_tie_role'] = (
                ('start' if index == 0 else 'stop') if c['kind'] == 'tie' else None
            )
            e['interpreted_slur_endpoint'] = c['kind'] == 'slur'
            e['event_core_verification_unchanged'] = True
    approval_file = ROOT / 'docs/V4_GT17B_OWNER_APPROVAL.txt'
    layer = {
        'classification': 'SCOPED_OWNER_VERIFIED_SOURCE_INTERPRETATION',
        'independent_ground_truth': 0,
        'approval_verbatim': approval_file.read_text(),
        'approval_origin': 'Actual current user instruction; no separate reply, signature or timestamp invented',
        'starting_sha': START,
        'prior_owner_layer': original_owner,
        'preceding_review_scope': (
            read(BASE / 'owner-review/full-source-owner-review-checklist.json')
            if (BASE / 'owner-review/full-source-owner-review-checklist.json').exists()
            else read(BASE / 'full-source-owner-review-checklist.json')
        ),
        'evidence_hashes': {
            n: sha(BASE / n)
            for n in [
                'full-source-owner-review-sheet.png',
                'full-source-owner-review-checklist.json',
                'full-source-event-inventory.json',
                'unresolved-source-objects.json',
                'owner-review/packet-freeze.json',
            ]
        },
        'source_hashes': src_hashes,
        'frozen_prediction_manifest_sha256': freeze,
        'chords': inv['chords'],
        'lyric_wording_and_rows': inv['lyrics'],
        'curve_interpretations': evidence,
        'approved_section_labels': ['Chorus', 'Tag'],
        'visible_repeat_ending_locations_approved': True,
        'playback_route_approved': False,
        'event_core_verification': {'owner_verified': 86, 'provisional': 83},
        'syllable_onset_verification': {'owner_verified': 88, 'provisional': 79},
        'continuation_verification': {'owner_verified': 30, 'provisional': 20},
    }
    dump(out / 'owner-interpretation-layer.json', layer)
    dump(out / 'source-event-inventory.json', inv)
    dump(
        out / 'source-correction-and-uncertainty.json',
        {
            'curve_changes': evidence,
            'newly_added_chords': added,
            'all_new_region_chords_now_owner_approved': 12,
            'note_rest_events_promoted': 0,
            'onset_associations_promoted': 0,
            'continuation_strokes_promoted': 0,
            'source_completeness': 'UNVERIFIED',
        },
    )
    revised.write('musicxml', fp=str(out / 'owner-augmented-source.musicxml'))
    parsed_source = converter.parse(str(out / 'owner-augmented-source.musicxml'))
    relationship_signature(parsed_source, evidence)
    guards = {'source_roundtrip': validate(revised, parsed_source, 0, 'key').to_dict()}
    reports, pics = [], []
    baseline_reports = read(BASE / 'full-score-rendering-validation.json')['targets']
    for target, semitones in [('A', -1), ('G', -3)]:
        score = copy.deepcopy(revised)
        summary = transpose_score(score, semitones, 'key')
        score.write('musicxml', fp=str(out / f'{target}-transposed.musicxml'))
        parsed = converter.parse(str(out / f'{target}-transposed.musicxml'))
        guards[target] = {
            'in_memory': validate(revised, score, semitones, 'key', summary).to_dict(),
            'serialized': validate(revised, parsed, semitones, 'key', summary).to_dict(),
        }
        relationships = relationship_signature(parsed, evidence)
        require(
            full_lyric_signature(parsed) == full_lyric_signature(parsed_source),
            'Lyric lineage changed',
        )
        require(repeat_signature(revised) == repeat_signature(parsed), 'Repeat changed in target')
        measures = list(parsed.parts[0].getElementsByClass(stream.Measure))
        chords = []
        for c in inventory['chords']:
            actual = [
                chord_text(x)
                for x in measures[c['measure'] - 1].getElementsByClass(harmony.ChordSymbol)
            ]
            require(actual == [EXPECTED[c['text']][target]], 'Approved chord transpose mismatch')
            chords.append(
                {'id': c['id'], 'measure': c['measure'], 'source': c['text'], 'target': actual[0]}
            )
        baseline = Image.open(BASE / f'{target}-full-alpha.png')
        report = next(r for r in baseline_reports if r['target'] == target)
        layers, cm = new_curve_layers(target, inventory, evidence, report, graph)
        for name, mask in layers.items():
            mask.save(out / (target + '-' + name.replace('/', '_') + '-alpha.png'))
        additions = combine(layers.values(), SIZE)
        final = combine([baseline, additions], SIZE)
        contact_union = int(
            np.count_nonzero((np.asarray(additions) > 0) & (np.asarray(baseline) > 0))
        )
        require(
            np.array_equal(
                np.asarray(final)[np.asarray(baseline) > 0],
                np.asarray(baseline)[np.asarray(baseline) > 0],
            ),
            'Old alpha pixels changed',
        )
        final.save(out / f'{target}-full-alpha.png')
        # Existing provisional event/text layer color is retained by using the baseline RGB image.
        pic = Image.open(BASE / f'{target}-full-score.png').copy()
        region = Image.composite(
            Image.new('RGB', SIZE, '#3057a0'), pic.crop((0, 140, 2520, 3704)), additions
        )
        pic.paste(region, (0, 140))
        ImageDraw.Draw(pic).rectangle((0, 0, 2520, 140), fill='white')
        draw = ImageDraw.Draw(pic)
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 22)
        for index, text in enumerate(
            [
                'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING',
                f'{target}: owner-approved chords/text wording; 86 verified + 83 provisional event cores.',
                '79 lyric onsets and 20 continuation marks remain provisional. 3 ties + 1 slur added with diagnostic geometry.',
                'Unresolved SIG, full repeat playback and MusicXML lyric extenders remain open. Independent ground truth: 0.',
                'Standalone newly typeset notation/text; no original ink removal or original-pixel preservation claim.',
            ]
        ):
            draw.text((15, 6 + index * 26), text, font=font, fill='black')
        pic.save(out / f'{target}-full-score.png')
        pics.append(pic)
        pdf = export_pdf(pic, out / f'{target}-full-score-experimental.pdf')
        anchors = [
            e['anchor_residual']
            for s in report['systems']
            for e in s['events']
            if 'anchor_residual' in e
        ]
        reports.append(
            {
                'target': target,
                'recognized_displayed_events': 169,
                'owner_verified_events': 86,
                'provisional_event_cores': 83,
                'owner_verified_chords': 24,
                'owner_verified_lyric_wording': 167,
                'verified_lyric_onsets': 88,
                'provisional_lyric_onsets': 79,
                'verified_marks': 30,
                'provisional_marks': 20,
                'inherited_geometry_checks': report,
                'new_curves': cm,
                'relationships': relationships,
                'approved_chord_transpositions': chords,
                'new_unexpected_alpha_contacts': 0,
                'new_intentional_contact_union_pixels': contact_union,
                'max_unchanged_anchor_residual': max(abs(v) for a in anchors for v in a),
                'pdf': pdf,
                'full_score_complete': False,
            }
        )
    require(
        guards['source_roundtrip']['ok']
        and all(g['ok'] for t in ['A', 'G'] for g in guards[t].values()),
        'V3 full guard failed',
    )
    original = page(Image.open(SOURCE_DIR / 'source.png'), title='ORIGINAL Bb source only')
    comp = Image.new('RGB', (3000, round(pics[0].height * 1000 / 2520)), 'white')
    for j, p in enumerate([original, *pics]):
        comp.paste(p.resize((1000, comp.height), Image.Resampling.LANCZOS), (j * 1000, 0))
    comp.save(out / 'Bb-A-G-full-score-comparison.png')
    coverage = copy.deepcopy(read(BASE / 'full-source-coverage-matrix.json'))
    for row in coverage:
        if row['measure'] >= 20:
            row['chord_interpretation_status'] = 'OWNER_VERIFIED_SOURCE'
            row['lyric_wording_and_row_status'] = 'OWNER_VERIFIED_SOURCE'
            row['syllable_onset_status'] = 'OMR_PROVISIONAL'
            row['continuation_status'] = 'AGENT_VISUAL_CANDIDATE'
            row['event_core_status'] = 'OMR_PROVISIONAL'
            row['curve_interpretations'] = [
                c['case']
                for c in evidence
                if row['measure'] in (c['source_case']['measure'], c['source_case']['to_measure'])
            ]
    dump(out / 'source-coverage-matrix.json', coverage)
    dump(
        out / 'semantic-integrity.json',
        {
            'guards': guards,
            'core_events_unchanged': core_signature(source) == core_signature(revised),
            'source_event_count': 169,
            'harmonies': 24,
            'source_slurs': len(revised.recurse().getElementsByClass(spanner.Slur)),
            'lyric_extender_serialization': 'INCOMPLETE_NOT_SOLVED',
            'independent_ground_truth': 0,
        },
    )
    dump(out / 'rendering-validation.json', {'targets': reports})
    remaining = [
        u for u in inventory['unresolved_objects'] if u['id'] not in {c['case'] for c in evidence}
    ]
    dump(
        out / 'remaining-unresolved-items.json',
        {
            'source_objects': remaining,
            'event_cores_unverified': 83,
            'syllable_onsets_unverified': 79,
            'continuation_strokes_unverified': 20,
            'repeat_playback': 'UNRESOLVED',
            'source_completeness': 'UNVERIFIED',
        },
    )
    dump(
        out / 'before-after-musical-correction-comparison.json',
        {
            'core_events_before_after': [169, 169],
            'frozen_harmonies_before_after': [16, 24],
            'new_ties': 3,
            'new_slurs': 1,
            'no_m31_tie': True,
            'changes': evidence,
            'lyric_wording_approval_not_onset_approval': True,
        },
    )
    require(file_hashes(BASE) == baseline_hashes, 'Historical GT17B directory changed')
    require(
        all(file_hashes(Path(k)) == v for k, v in history.items()), 'Historical directory changed'
    )
    dump(
        out / 'preservation-verification.json',
        {
            'GT17B_manifest': freeze,
            'GT17B_all_files_unchanged': True,
            'historical_directories_unchanged': list(history),
            'source_hashes': src_hashes,
            'original_omr_sig_protection_masks_unchanged': True,
        },
    )
    dump(
        out / 'prediction-freeze.json',
        {
            'files': file_hashes(out),
            'before_agent_visual_review': True,
            'code_sha256': sha(Path(__file__)),
            'approval_sha256': sha(approval_file),
        },
    )
    print('Owner integration frozen:', out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
