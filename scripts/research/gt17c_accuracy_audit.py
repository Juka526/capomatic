"""Read-only source accuracy candidates and focused owner delta review, never approval."""

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from music21 import converter, pitch, stream, spanner
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.music_guard import validate
from backend.omr_v3.chords import chord_text
from scripts.research.gt11_complete_measure import read, require, events_of
from scripts.research.gt13a2_provisional import linked
from scripts.research.gt13a5_lyric_layout import contacts
from scripts.research.gt17b_owner_integration import (
    BASE,
    SOURCE_DIR,
    verify_manifest,
    relationship_signature,
    core_signature,
    new_curve_layers,
)
from scripts.research.gt17b_full_score import binding
from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes

ROOT = Path(__file__).resolve().parents[2]
OWNER = Path('/private/tmp/capomatic-v4-gt17b-owner-output/final-v2')
PACKET = BASE / 'owner-review'
START = 'ff4dd9dbb12a21807ba3b3672eac5b519ebbc5f3'
# Source-only agent observations frozen before the candidate checks, not human labels.
VISUAL_EVENT_COUNTS = dict(
    zip(range(20, 38), [4, 10, 5, 10, 1, 10, 3, 2, 1, 1, 4, 7, 4, 7, 2, 10, 1, 1])
)
GLYPH_STROKES = {
    '5660': '곳',
    '5896': '시',
    '5948': '씀',
    '6127': '한',
    '6150': '씀',
    '6189': '으',
    '4867': '되',
}
ENDING_PUNCTUATION = {'6184': '1.', '6198': '2.'}


def candidate_status(checks, unresolved=False):
    if any(v is False for v in checks.values()):
        return 'DISAGREEMENT'
    return (
        'UNRESOLVED' if unresolved or any(v is None for v in checks.values()) else 'PASS_CANDIDATE'
    )


def source_duration(e, graph):
    """Duration candidate from raw glyph type and typed beam/flag/dot lineage."""
    raw = graph['symbols'][e['symbol_id']]
    shape = raw['shape']
    if shape in ('QUARTER_REST', 'EIGHTH_REST', 'WHOLE_REST', 'WHOLE_NOTE'):
        return {
            'QUARTER_REST': Fraction(1),
            'EIGHTH_REST': Fraction(1, 2),
            'WHOLE_REST': Fraction(4),
            'WHOLE_NOTE': Fraction(4),
        }[shape], []
    relations = graph['relations']
    if shape == 'NOTEHEAD_VOID':
        owners = [
            r['source']
            for r in relations
            if r['kind'] == 'contains' and r['target'] == e['symbol_id']
        ]
        dots = {
            sid
            for root in [e['symbol_id'], *owners]
            for sid in linked(relations, 'augmentation', root)
            if graph['symbols'].get(sid, {}).get('kind') == 'augmentation-dot'
        }
        require(len(dots) <= 1, 'Unsupported dotted duration')
        return Fraction(3 if dots else 2), sorted(dots)
    require(shape == 'NOTEHEAD_BLACK' and len(e['stem_ids']) == 1, 'Unsupported raw note shape')
    stem = e['stem_ids'][0]
    beams = [
        sid
        for sid in linked(relations, 'beam-stem', stem)
        if graph['symbols'].get(sid, {}).get('kind') in ('beam', 'beam-hook')
    ]
    flags = linked(relations, 'flag-stem', stem)
    require(not (beams and flags), 'Conflicting beam/flag lineage')
    require(len(beams) <= 2 and len(flags) <= 1, 'Unsupported beam/flag count')
    if flags:
        require(
            graph['symbols'][flags[0]]['shape'] in ('FLAG_1', 'FLAG_1_DOWN'),
            'Unsupported flag type',
        )
    level = len(beams) or bool(flags)
    return Fraction(1, 2**level), beams + flags


def event_review(inventory, graph, source, targets, original):
    reviews = []
    for system in inventory['systems'][5:]:
        for measure in system['measures']:
            number, cumulative = measure['printed_measure'], Fraction(0)
            for e in measure['events']:
                symbol = graph['symbols'][e['symbol_id']]
                duration, attachments = source_duration(e, graph)
                sem = next(
                    n
                    for n in events_of(
                        list(source.parts[0].getElementsByClass(stream.Measure))[number - 1]
                    )
                    if Fraction(n.offset) == Fraction(e['onset'])
                )
                checks = {
                    'raw_bbox_binding': symbol['geometry']['bbox'] == e['source_bbox'],
                    'raw_duration_matches': duration == Fraction(e['duration']),
                    'onset_from_raw_glyph_sequence': cumulative == Fraction(e['onset']),
                    'source_xml_duration': sem.quarterLength == Fraction(e['duration']),
                    'single_voice': e['voice'] == '1',
                    'source_visible_count_candidate': len(measure['events'])
                    == VISUAL_EVENT_COUNTS[number],
                }
                if e['kind'] == 'NOTE':
                    checks['raw_staff_pitch'] = (
                        symbol['pitch_position'] == 35 - pitch.Pitch(e['pitch']).diatonicNoteNum
                    )
                    expected_alter = -1 if sem.pitch.step in ('B', 'E') else 0
                    checks['key_accidental_context'] = (
                        sem.pitch.accidental.alter if sem.pitch.accidental else 0
                    ) == expected_alter
                    checks['source_xml_pitch'] = sem.pitch.nameWithOctave == e['pitch']
                raw_curves = [
                    r['source']
                    for r in graph['relations']
                    if r['kind'] == 'slur-head' and r['target'] == e['symbol_id']
                ]
                withheld_export = [
                    sid
                    for sid in raw_curves
                    if sid.split(':')[-1] in GLYPH_STROKES
                    and graph['symbols'][sid]['kind'] == 'slur'
                    and any(isinstance(s, spanner.Slur) for s in sem.getSpannerSites())
                ]
                checks['no_withheld_glyph_candidate_exported_as_slur'] = not withheld_export
                target_notes = {}
                for name, shift in [('A', -1), ('G', -3)]:
                    m = list(targets[name].parts[0].getElementsByClass(stream.Measure))[number - 1]
                    ns = [n for n in events_of(m) if Fraction(n.offset) == Fraction(e['onset'])]
                    checks[name + '_onset_duration'] = (
                        len(ns) == 1 and ns[0].quarterLength == sem.quarterLength
                    )
                    checks[name + '_transposition'] = (
                        ns[0].pitch.midi - sem.pitch.midi == shift if sem.isNote else ns[0].isRest
                    )
                    target_notes[name] = ns[0].pitch.nameWithOctave if ns[0].isNote else 'REST'
                b = [int(x) for x in e['source_bbox']]
                grayscale = np.asarray(original.crop(b).convert('L'))
                reviews.append(
                    {
                        'id': 'event-' + e['symbol_id'],
                        'measure': number,
                        'event_id': e['id'],
                        'source_object_id': e['symbol_id'],
                        'original_record': e,
                        'source_bbox': b,
                        'source_shape': symbol['shape'],
                        'music_event_kind': e['kind'],
                        'stem_direction': e['stem_direction'],
                        'unresolved_curve_export_ids': withheld_export,
                        'core_pitch_duration_status': candidate_status(
                            {
                                k: v
                                for k, v in checks.items()
                                if k != 'no_withheld_glyph_candidate_exported_as_slur'
                            }
                        ),
                        'raw_duration_candidate': str(duration),
                        'typed_attachment_ids': attachments,
                        'source_grayscale_range': [int(grayscale.min()), int(grayscale.max())],
                        'onset': e['onset'],
                        'duration': e['duration'],
                        'voice': e['voice'],
                        'written_pitch': e['pitch'],
                        'target_pitches': target_notes,
                        'interpreted_source_tie_role': sem.tie.type if sem.tie else None,
                        'curve_source_relations': [
                            r
                            for r in graph['relations']
                            if r['kind'] == 'slur-head' and r['target'] == e['symbol_id']
                        ],
                        'source_measure_crop': crop_reference(number),
                        'checks': checks,
                        'status': candidate_status(checks),
                        'source_verification': 'OMR_PROVISIONAL',
                        'visual_review': 'AGENT_SOURCE_ONLY_NOT_INDEPENDENT',
                        'missing_source_possibility': 'UNEXCLUDED_NOT_PROVEN_BY_AGREEMENT',
                        'suggested_decision': 'CONFIRM' if all(checks.values()) else 'CORRECT',
                        'owner_answer': None,
                    }
                )
                cumulative += duration
            require(cumulative == 4, 'Source raw-duration total disagreement')
    return reviews


def crop_reference(number):
    p = PACKET / f'source-m{number}.png'
    return {'path': str(p), 'sha256': sha(p)} if p.exists() else None


def lyric_review(inventory):
    result = []
    for l in inventory['lyrics']:
        e = next(e for e in inventory['events'] if e['id'] == l['event_id'])
        b = l['source_dark_bbox']
        center = (b[0] + b[2] - 1) / 2 if b else None
        dx = center - e['physical_source_center'][0] if b else None
        checks = {
            'unique_event_identity': (e['printed_measure'], e['onset'])
            == (l['measure'], l['onset']),
            'pitched_note': e['kind'] == 'NOTE',
            'approved_text_row_preserved': l['wording_and_row_status'] == 'OWNER_VERIFIED_SOURCE',
            'visible_window_support': True if b else None,
            'horizontal_registration_candidate': abs(dx) <= 25 if dx is not None else None,
        }
        result.append(
            {
                **l,
                'id': 'lyric-' + l['id'],
                'source_object_id': e['symbol_id'],
                'status': candidate_status(checks),
                'checks': checks,
                'source_center_dx_px': dx,
                'source_measure_crop': crop_reference(l['measure']),
                'interpretation': 'Agent inspected entire native source system row, not target preview. Existing onset candidate appears consistent; owner confirmation remains required.',
                'centered_window_caveat': 'The window was centered on the proposed note; passing its horizontal bound is tautological and is not independent evidence of the association.',
                'approved_wording_reconfirmation_requested': False,
                'association_owner_status': 'PENDING',
                'suggested_decision': 'CONFIRM' if all(checks.values()) else 'CORRECT',
                'owner_answer': None,
            }
        )
    return result


def continuation_review(inventory):
    result = []
    for mark in inventory['continuations']:
        candidates = [
            l
            for l in inventory['lyrics']
            if l['row'] == mark['row']
            and (l['measure'], Fraction(l['onset'])) < (mark['measure'], Fraction(mark['onset']))
        ]
        previous = (
            max(candidates, key=lambda l: (l['measure'], Fraction(l['onset'])))
            if candidates
            else None
        )
        e = next(e for e in inventory['events'] if e['id'] == mark['event_id'])
        checks = {
            'onset_event_identity': (e['printed_measure'], e['onset'])
            == (mark['measure'], mark['onset']),
            'visible_stroke_window': True if mark['source_dark_bbox'] else None,
            'held_syllable_matches_preceding_same_row': bool(
                previous and previous['text'] == mark['held_syllable_candidate']
            ),
        }
        # The second ending skips intervening lyrics, so printed-order predecessor is not playback lineage.
        if mark['measure'] == 28:
            checks['held_syllable_matches_preceding_same_row'] = None
        status = candidate_status(checks, unresolved=mark['measure'] == 28)
        result.append(
            {
                **mark,
                'id': 'continuation-' + mark['id'],
                'source_object_id': e['symbol_id'],
                'source_measure_crop': crop_reference(mark['measure']),
                'checks': checks,
                'status': status,
                'preceding_printed_syllable': previous['id'] if previous else None,
                'held_syllable_evidence': (
                    'REPEAT_DEPENDENT_UNRESOLVED'
                    if mark['measure'] == 28
                    else 'SAME_ROW_SOURCE_VISUAL_CANDIDATE'
                ),
                'xml_extend_claim': False,
                'suggested_decision': (
                    'UNCERTAIN'
                    if status == 'UNRESOLVED'
                    else ('CONFIRM' if status == 'PASS_CANDIDATE' else 'CORRECT')
                ),
                'owner_answer': None,
            }
        )
    return result


def containing_measure(inventory, s):
    system = next(x for x in inventory['systems'] if x['staff']['system'] == s['system'])
    x = sum(s['geometry']['bbox'][::2]) / 2
    return next(
        (
            m['printed_measure']
            for m in system['measures']
            if m['omr_bounds'][0] <= x < m['omr_bounds'][2]
        ),
        system['printed_measures'][0],
    )


def sig_reviews(inventory, remaining, original, out):
    result = []
    dest = out / 'source-object-details'
    dest.mkdir()
    for u in remaining:
        s = u['original_observation']
        sid = s['source_id']
        number = containing_measure(inventory, s)
        if sid in GLYPH_STROKES:
            proposal = 'KOREAN_LYRIC_GLYPH_STROKE_CANDIDATE'
            associated = GLYPH_STROKES[sid]
        elif sid in ENDING_PUNCTUATION:
            proposal = 'ENDING_NUMERAL_PUNCTUATION_CANDIDATE'
            associated = ENDING_PUNCTUATION[sid]
        else:
            proposal = 'LYRIC_CONTINUATION_STROKE_CANDIDATE'
            associated = None
        b = s['geometry']['bbox']
        window = [int(b[0]) - 25, int(b[1]) - 30, int(b[2]) + 25, int(b[3]) + 30]
        old = PACKET / (u['id'].replace(':', '_') + '.png')
        if old.exists():
            image_ref = {'path': str(old), 'sha256': sha(old), 'reuse_existing_crop': True}
        else:
            path = dest / (u['id'].replace(':', '_') + '.png')
            original.crop(window).save(path)
            image_ref = {
                'path': str(path),
                'sha256': sha(path),
                'reuse_existing_crop': False,
                'page_bbox': window,
            }
        result.append(
            {
                'id': 'sig-' + u['id'],
                'source_object_id': u['id'],
                'measure': number,
                'source_bbox': b,
                'original_observation': u,
                'proposed_interpretation': proposal,
                'associated_text_candidate': associated,
                'status': 'DISAGREEMENT' if sid == '4867' else 'UNRESOLVED',
                'semantic_export_issue': (
                    'Source glyph-stroke candidate withheld from renderer but retained as m21 onset3->13/4 MusicXML slur'
                    if sid == '4867'
                    else None
                ),
                'source_classification_owner_status': 'PENDING',
                'evidence_classification': 'AGENT_VISUAL_CANDIDATE',
                'image': image_ref,
                'raw_omr_changed': False,
                'owner_answer': None,
                'suggested_decision': 'CORRECT' if sid == '4867' else 'CONFIRM',
                'review_question': 'Classify this raw object only; do not reconfirm already approved lyric wording or mark existence.',
            }
        )
    return result


def xml_lyric_extension_audit(xml):
    root = ET.fromstring(xml)
    result = []
    for m in root.findall('./part/measure'):
        for index, n in enumerate(m.findall('note')):
            for l in n.findall('lyric'):
                for extend in l.findall('extend'):
                    kind = extend.get('type')
                    require(kind in (None, 'start', 'continue', 'stop'), 'Invalid extension state')
                    result.append(
                        {
                            'measure_xml': m.get('number'),
                            'note_index': index,
                            'row': l.get('number'),
                            'type': kind or 'legacy-start',
                            'lyric_text': l.findtext('text'),
                        }
                    )
    return {
        'records': result,
        'count': len(result),
        'completeness': 'UNVERIFIED_REQUIRES_APPROVED_ASSOCIATION_LINEAGE',
        'visual_dash_count_is_not_xml_semantics': True,
    }


def xml_curve_audit(xml):
    mismatches = []
    slurs = []
    tie_roles = 0
    for m in ET.fromstring(xml).findall('./part/measure'):
        for j, n in enumerate(m.findall('note')):
            sound = sorted(t.get('type') for t in n.findall('tie'))
            notation = sorted(t.get('type') for t in n.findall('./notations/tied'))
            tie_roles += len(sound)
            if sound != notation:
                mismatches.append(
                    {
                        'measure_xml': m.get('number'),
                        'note_index': j,
                        'sound': sound,
                        'notation': notation,
                    }
                )
            for curve in n.findall('./notations/slur'):
                slurs.append({'measure_xml': m.get('number'), 'note_index': j, **curve.attrib})
    return {
        'tie_sound_notation_disagreements': mismatches,
        'tie_role_count': tie_roles,
        'slur_records': slurs,
        'source_correctness': 'Separate from serialization agreement; original unresolved 4867 is still serialized.',
    }


def playback_review(source, graph):
    repeats = []
    for index, m in enumerate(source.parts[0].getElementsByClass(stream.Measure), 1):
        for side in ['leftBarline', 'rightBarline']:
            b = getattr(m, side)
            if b is not None and getattr(b, 'direction', None):
                repeats.append(
                    {'measure': index, 'side': side, 'direction': b.direction, 'times': b.times}
                )
    return {
        'id': 'playback-full-traversal',
        'measure': 15,
        'status': 'UNRESOLVED',
        'suggested_decision': 'UNCERTAIN',
        'owner_answer': None,
        'approved_visible_sign_locations_reconfirmation_requested': False,
        'recognized_repeat_records': repeats,
        'source_ending_pairs': [
            {'first': [8], 'second': [9]},
            {'first': [15, 16], 'second': [17]},
            {'first': [26, 27], 'second': [28]},
        ],
        'source_ending_object_ids': [
            'sheet#1:' + x for x in ['5201', '5193', '5203', '5195', '5197', '5199']
        ],
        'issues': [
            'm15-16 first ending followed by m17 second ending; no explicit backward repeat at m16 in frozen image or original barline records.',
            'm28 held-syllable lineage depends on repeat traversal rather than preceding printed m27 lyric.',
            'Repeat counts, section exits and full traversal have not been owner-approved.',
        ],
        'question': 'Supply or explicitly defer the complete performance traversal, especially m15-17; no source notation or repeat route will be invented.',
        'expanded_playback_sequence': None,
        'xml_repeat_signature_preserved': True,
    }


def frozen_render_checks(inventory, graph, evidence):
    reports = read(BASE / 'full-score-rendering-validation.json')['targets']
    results = []
    for target in ['A', 'G']:
        report = next(r for r in reports if r['target'] == target)
        layers, curves = new_curve_layers(target, inventory, evidence, report, graph)
        for name, p in layers.items():
            frozen = Image.open(OWNER / (target + '-' + name.replace('/', '_') + '-alpha.png'))
            require(p.tobytes() == frozen.tobytes(), 'Frozen corrected curve changed')
        anchors = []
        text_contacts = 0
        missing_connections = 0
        for system in report['systems']:
            folder = BASE / f'{target}-system-{system["system"]}-components'
            size = system['size']
            components = {}
            for rec in read(folder / 'component-map.json'):
                require(sha(folder / rec['file']) == rec['sha256'], 'Frozen component changed')
                tile = Image.open(folder / rec['file'])
                mask = Image.new('L', tuple(size))
                mask.paste(tile, tuple(rec['bbox_local'][:2]))
                components[rec['id']] = mask
            for e in system['events']:
                if e['kind'] != 'NOTE':
                    continue
                p = components[e['event_id'] + ':head']
                b = p.getbbox()
                center = [(b[0] + b[2] - 1) / 2, (b[1] + b[3] - 1) / 2]
                residual = [center[j] - e['target_staff_coordinate'][j] for j in (0, 1)]
                require(max(map(abs, residual)) <= 0.5, 'Anchor criterion failed')
                anchors.append({'event_id': e['event_id'], 'residual': residual})
            textids = {x['id'] for x in inventory['lyrics'] + inventory['continuations']}
            texts = {k: p for k, p in components.items() if k in textids}
            fixed = Image.new('L', tuple(size))
            for k, p in components.items():
                if k not in textids:
                    fixed = Image.fromarray(np.maximum(np.asarray(fixed), np.asarray(p)))
            top = system['page_origin_y']
            for c in evidence:
                if c['system'] == system['system']:
                    p = layers[c['case']].crop((0, top, size[0], top + size[1]))
                    fixed = Image.fromarray(np.maximum(np.asarray(fixed), np.asarray(p)))
            hit = sum(
                int(np.count_nonzero((np.asarray(p) > 0) & (np.asarray(fixed) > 0)))
                for p in texts.values()
            )
            text_contacts += hit
            require(hit == 0 and not contacts(texts), 'Frozen lyric collision')
            for connection in system['connections']:
                a, b = components[connection['a']], components[connection['b']]
                count = int(np.count_nonzero((np.asarray(a) > 0) & (np.asarray(b) > 0)))
                if not count:
                    missing_connections += 1
            require(not missing_connections, 'Frozen connection broken')
            require(
                all(p.getbbox()[1] > 0 and p.getbbox()[3] < size[1] for p in components.values()),
                'Frozen viewport clipping',
            )
        results.append(
            {
                'target': target,
                'fresh_notehead_bbox_checks': len(anchors),
                'max_per_axis_residual': max(abs(v) for a in anchors for v in a['residual']),
                'fresh_lyric_music_contacts': text_contacts,
                'fresh_lyric_lyric_contacts': 0,
                'fresh_missing_stem_beam_flag_connections': missing_connections,
                'new_curve_contacts': curves,
                'fresh_viewport_clipping': 0,
                'previous_first_five_systems': 'Unchanged frozen hashes; earlier safety reports retained, not independent re-recognition.',
            }
        )
    return results


def run(out):
    require(not out.exists(), 'Fresh audit directory required')
    out.mkdir(parents=True)
    original_files = {str(p): file_hashes(p) for p in [BASE, OWNER]}
    for folder in [BASE, OWNER]:
        verify_manifest(folder, 'prediction-freeze.json')
    verify_manifest(PACKET, 'packet-freeze.json')
    for n, h in read(ROOT / 'docs/V4_GT17B_OWNER_VALIDATION.json')['artifact_sha256'].items():
        require(sha(OWNER / n) == h, n)
    history, src = binding(out)
    # binding's historical m17 approval copy is not a new interpretation output for this audit.
    (out / 'owner-interpretation-layer.json').unlink()
    inventory = read(OWNER / 'source-event-inventory.json')
    remaining = read(OWNER / 'remaining-unresolved-items.json')['source_objects']
    original = Image.open(SOURCE_DIR / 'source.png')
    for rec in read(PACKET / 'crop-map.json'):
        native = Image.open(PACKET / rec['file'])
        require(
            original.crop(rec['page_bbox']).tobytes() == native.tobytes(),
            'Existing source crop differs from original pixels',
        )
    graph = read(SOURCE_DIR / 'visual-graph.json')
    source = converter.parse(str(OWNER / 'owner-augmented-source.musicxml'))
    targets = {n: converter.parse(str(OWNER / f'{n}-transposed.musicxml')) for n in ['A', 'G']}
    events = event_review(inventory, graph, source, targets, original)
    lyrics = lyric_review(inventory)
    marks = continuation_review(inventory)
    symbols = sig_reviews(inventory, remaining, original, out)
    playback = playback_review(source, graph)
    require(
        [len(x) for x in [events, lyrics, marks, symbols]] == [83, 79, 20, 28],
        'Review scope mismatch',
    )
    require(
        sum(e['source_verification'] == 'OWNER_VERIFIED_SOURCE' for e in inventory['events']) == 86,
        'Approval scope drift',
    )
    for name, data in [
        ('provisional-event-review', events),
        ('lyric-onset-review', lyrics),
        ('continuation-review', marks),
        ('unresolved-sig-review', symbols),
        ('repeat-playback-review', playback),
    ]:
        dump(out / (name + '.json'), data)
    guards = {
        n: validate(source, s, -1 if n == 'A' else -3, 'key').to_dict() for n, s in targets.items()
    }
    require(all(g['ok'] for g in guards.values()), 'Unchanged V3 guard failed')
    evidence = read(OWNER / 'owner-interpretation-layer.json')['curve_interpretations']
    curvechecks = {
        n: relationship_signature(s, evidence) for n, s in {'source': source, **targets}.items()
    }
    rendering = frozen_render_checks(inventory, graph, evidence)
    dump(out / 'frozen-render-validation.json', rendering)
    xml = {
        n: xml_lyric_extension_audit(
            (
                OWNER
                / (('owner-augmented-source' if n == 'source' else n + '-transposed') + '.musicxml')
            ).read_text()
        )
        for n in ['source', 'A', 'G']
    }
    dump(
        out / 'musicxml-semantic-audit.json',
        {
            'guards': guards,
            'reviewed_tie_slur_lineage': curvechecks,
            'lyric_extensions': xml,
            'raw_curve_serialization': {
                n: xml_curve_audit(
                    (
                        OWNER
                        / (
                            ('owner-augmented-source' if n == 'source' else n + '-transposed')
                            + '.musicxml'
                        )
                    ).read_text()
                )
                for n in ['source', 'A', 'G']
            },
            'source_event_pitch_duration_signature': core_signature(source),
            'repeat_playback_finalized': False,
            'spec_sources': [
                'https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/extend/',
                'https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/tie/',
                'https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/repeat/',
            ],
        },
    )
    grouped = defaultdict(list)
    for kind, items in [
        ('event', events),
        ('lyric_onset', lyrics),
        ('continuation', marks),
        ('raw_sig', symbols),
        ('playback', [playback]),
    ]:
        for item in items:
            grouped[item['measure']].append(
                {
                    'id': item['id'],
                    'kind': kind,
                    'requested_fields': {
                        'event': [
                            'note/rest identity and written pitch',
                            'onset',
                            'duration',
                            'voice',
                            'stem/beam/flag and unapproved attachments',
                        ],
                        'lyric_onset': [
                            'exact note/event and onset only; wording/row already approved'
                        ],
                        'continuation': ['stroke identity, held syllable and event/repeat lineage'],
                        'raw_sig': ['raw object interpretation only'],
                        'playback': [
                            'complete traversal or explicit deferral only; sign locations approved'
                        ],
                    }[kind],
                    'already_approved_curve_classes_excluded': True,
                    'status': item['status'],
                    'suggested_decision': item['suggested_decision'],
                    'owner_answer': None,
                    'source_object_id': item.get('source_object_id'),
                    'review_reason': (
                        'Pitch/duration core agrees; resolve the withheld 4867 glyph candidate '
                        'that is still serialized as a slur, not an invented pitch correction.'
                        if item.get('unresolved_curve_export_ids')
                        else item.get('semantic_export_issue')
                    ),
                    'source_window': item.get('source_window', item.get('source_bbox')),
                    'candidate': {
                        k: item[k]
                        for k in [
                            'written_pitch',
                            'music_event_kind',
                            'source_shape',
                            'stem_direction',
                            'typed_attachment_ids',
                            'onset',
                            'duration',
                            'voice',
                            'text',
                            'row',
                            'held_syllable_candidate',
                            'proposed_interpretation',
                            'question',
                        ]
                        if k in item
                    },
                }
            )
    checklist = {
        'review_type': 'OWNER_REVIEW_PENDING_NOT_INDEPENDENT_GROUND_TRUTH',
        'starting_sha': START,
        'approved_fields_not_requested_again': {
            'event_cores': 86,
            'chords': 24,
            'lyric_wording_rows': 167,
            'lyric_onsets': 88,
            'marks': 30,
            'reviewed_new_ties': 3,
            'reviewed_m31_slur': 1,
        },
        'instructions': 'Review only indicated unresolved fields; CONFIRM, CORRECT with exact correction, or UNCERTAIN. Agent candidates are not human labels.',
        'decisions': ['CONFIRM', 'CORRECT', 'UNCERTAIN'],
        'grouped_by_printed_measure': [
            {'measure': m, 'source_measure_crop': crop_reference(m), 'items': items}
            for m, items in sorted(grouped.items())
        ],
        'independent_ground_truth': 0,
        'owner_submissions_collected_in_gt17c': 0,
    }
    dump(out / 'owner-approval-checklist.json', checklist)
    guide = [
        '# GT-17C 소유자 차이 검토',
        '',
        '이미 승인한 코드·가사 문구·기존 이벤트는 재승인 대상이 아닙니다. 아래 미확인 필드만 CONFIRM / CORRECT / UNCERTAIN으로 답해 주세요. 답변은 아직 수집되지 않았습니다.',
        '',
        '좌표는 원본 페이지 정수 픽셀, bbox의 오른쪽·아래 제외입니다. onset은 각 마디에서 0부터 시작하는 4분음표 단위입니다. 원래 event ID의 m 번호와 인쇄 마디 번호가 다를 수 있으므로 measure 필드를 따릅니다.',
        '',
    ]
    for m, items in sorted(grouped.items()):
        guide.extend([f'## 인쇄 {m}마디', ''])
        for item in items:
            candidate = item.get('candidate', {})
            guide.append(
                f'- {item["id"]}: {candidate}; 제안 {item["suggested_decision"]}; 소유자 답변: ______'
            )
            guide.append(
                f'  검토 필드: {item["requested_fields"]}; 기존 승인 곡선 분류는 제외합니다.'
            )
        guide.append('')
    (out / 'owner-review-guide.md').write_text('\n'.join(guide) + '\n')
    matrix = []
    for num in range(1, 38):
        items = [i for i in events + lyrics + marks + symbols if i['measure'] == num]
        matrix.append(
            {
                'measure': num,
                'approved_scope_unchanged': True,
                'audit_cases': len(items),
                'status_counts': dict(Counter(i['status'] for i in items)),
                'event_review_count': sum(i['measure'] == num for i in events),
                'source_completeness': 'UNVERIFIED',
                'missing_source_possibilities_not_excluded': True,
                'independent_accuracy_denominator': None,
            }
        )
    dump(out / 'accuracy-audit-matrix.json', matrix)
    delta_sheet(out, grouped, inventory, original)
    dump(
        out / 'validation-summary.json',
        {
            'counts': {
                k: dict(Counter(x['status'] for x in rows))
                for k, rows in [
                    ('events', events),
                    ('lyric_onsets', lyrics),
                    ('continuations', marks),
                    ('sig_objects', symbols),
                ]
            },
            'source_scope': [9, 37],
            'recognition_completeness': 'UNVERIFIED',
            'independent_ground_truth': 0,
            'new_owner_approvals': 0,
            'raw_sig_proposals': dict(Counter(s['proposed_interpretation'] for s in symbols)),
            'guards_pass': True,
            'source_hashes': src,
            'musical_outputs_regenerated': False,
            'rendering_safety': 'Frozen GT17B owner masks unchanged; no rendering changes authorized or performed.',
        },
    )
    require(all(file_hashes(Path(k)) == v for k, v in original_files.items()), 'GT17B changed')
    require(all(file_hashes(Path(k)) == v for k, v in history.items()), 'Historical output changed')
    dump(
        out / 'preservation-verification.json',
        {
            'baseline_directories': list(original_files),
            'earlier_history_directories': list(history),
            'all_files_unchanged': True,
            'source_hashes': src,
        },
    )
    dump(
        out / 'audit-freeze.json',
        {
            'files': file_hashes(out),
            'producer_sha256': sha(Path(__file__)),
            'source_hashes': src,
            'no_owner_answers_filled': True,
        },
    )
    print(read(out / 'validation-summary.json'))


def delta_sheet(out, grouped, inventory, source):
    """Source-only delta regions at native pixel scale; reuse original crops by reference."""
    cells = []
    for number, items in sorted(grouped.items()):
        existing = PACKET / f'source-m{number}.png'
        if existing.exists():
            ref = read(PACKET / 'crop-map.json')
            box = next(r['page_bbox'] for r in ref if r['file'] == existing.name)
            tile = Image.open(existing).copy()
        else:
            system = next(s for s in inventory['systems'] if number in s['printed_measures'])
            measure = next(m for m in system['measures'] if m['printed_measure'] == number)
            b = measure['omr_bounds']
            box = [
                max(0, int(b[0]) - 20),
                system['view'][1],
                min(source.width, int(b[2]) + 20),
                system['view'][3],
            ]
            tile = source.crop(box)
        annotations = Image.new('RGB', (max(900, tile.width), tile.height + 72), 'white')
        annotations.paste(tile, (0, 72))
        d = ImageDraw.Draw(annotations)
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 18)
        d.text(
            (8, 3),
            f'PRINTED {number}: ONLY DELTA FIELDS / OWNER ANSWERS EMPTY',
            font=font,
            fill='black',
        )
        d.text(
            (8, 29),
            ' / '.join(f'{k}:{v}' for k, v in Counter(i['kind'] for i in items).items()),
            font=font,
            fill='black',
        )
        # Highlight only delta objects on a display copy; native evidence crops stay unchanged.
        event_ids = {item['id'] for item in items}
        for e in inventory['events']:
            if 'event-' + e['symbol_id'] not in event_ids:
                continue
            b = e['source_bbox']
            bb = (
                int(b[0] - box[0]),
                int(b[1] - box[1] + 72),
                int(b[2] - box[0]),
                int(b[3] - box[1] + 72),
            )
            d.rectangle(bb, outline='#9a6400', width=1)
            d.text(
                (bb[0], bb[1] - 17),
                e['symbol_id'].split(':')[-1],
                font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 12),
                fill='#9a6400',
            )
        for u in read(OWNER / 'remaining-unresolved-items.json')['source_objects']:
            if 'sig-' + u['id'] not in event_ids:
                continue
            b = u['original_observation']['geometry']['bbox']
            d.rectangle(
                (
                    int(b[0] - box[0]),
                    int(b[1] - box[1] + 72),
                    int(b[2] - box[0]),
                    int(b[3] - box[1] + 72),
                ),
                outline='#aa2266',
                width=1,
            )
        cells.append(annotations)
    width = max(c.width for c in cells)
    sheet = Image.new('RGB', (width, sum(c.height for c in cells) + 60), 'white')
    ImageDraw.Draw(sheet).text(
        (8, 8),
        'SOURCE-ONLY OWNER DELTA REVIEW / NOT GROUND TRUTH / NO TARGET PREDICTIONS',
        fill='black',
    )
    y = 60
    for cell in cells:
        sheet.paste(cell, (0, y))
        y += cell.height
    sheet.save(out / 'source-review-delta-sheet.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
