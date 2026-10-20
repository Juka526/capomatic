"""Source-only third-system audit and explicitly provisional music-only preview."""

import argparse
import copy
import math
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

import numpy as np
from fontTools.ttLib import TTFont
from music21 import converter, harmony, stream, spanner
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt04_visual import HEAD
from scripts.research.gt05_raster_anchor import glyph
from scripts.research.gt07_flags import FLAG, flag_mask
from scripts.research.gt11_complete_measure import FONT, read, require, events_of, event_signature
from scripts.research.gt12_render_context import text_mask
from scripts.research.gt13a2_provisional import EIGHTH_REST, linked, curve_mask
from scripts.research.gt13a4_header import header, font_units
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.gt13a5_lyric_layout import union, contacts
from scripts.research.gt13a_full_system import scaffold
from scripts.research.gt13a6_tie_review import SOURCE, SOURCE_DIR, GT02
from scripts.research.gt14_second_system import local_tie
from scripts.research.gt14c_continuation_audit import dark_support_bbox, save_native
from scripts.research.gt14e_two_system_validation import GT14A
from scripts.research.gt15_notation import half_symbol, font_contract, single_beam
from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes, line_y

ROOT = Path(__file__).resolve().parents[2]
PRIOR = Path('/private/tmp/capomatic-v4-gt14e/gt14e-final-output')
PROTOCOL = ROOT / 'docs/V4_GT15_PROTOCOL.json'
SIZE = (2520, 1450)
VIEW = (130, 1015, 2430, 1390)
CANDIDATES = {
    9: {
        'chord': None,
        'upper': ['풀', '은', '마'],
        'lower': ['전', '능', '하'],
        'onsets': ['5/2', '3', '7/2'],
    },
    10: {'chord': 'Eb', 'upper': ['르', '고'], 'lower': ['신', '주'], 'onsets': ['1/2', '3/2']},
    11: {
        'chord': None,
        'upper': ['꽃', '을', '시'],
        'lower': ['거', '룩', '하'],
        'onsets': ['5/2', '3', '7/2'],
    },
    12: {'chord': 'F', 'upper': ['드', '나'], 'lower': ['신', '왕'], 'onsets': ['1/2', '3/2']},
}


def inventory(score, graph, rows, source):
    staff = next(s for s in graph['staves'] if s['id'] == 'sheet#1:3')
    mm = list(score.parts[0].getElementsByClass(stream.Measure))
    records = []
    for number in (9, 10, 11, 12):
        measure = mm[number - 1]
        rr = sorted(
            [r for r in rows if r['omr_measure_index'] == number - 1],
            key=lambda r: Fraction(r['local_offset']),
        )
        geometry = next(
            m
            for m in graph['measures']
            if m['system'] == staff['system'] and m['number'] == str(number)
        )
        require(
            len(events_of(measure)) == len(rr) == 5,
            'Five recognized events required per printed measure',
        )
        events = []
        for n, r in zip(events_of(measure), rr):
            require(
                r['printed_measures'] == [number]
                and r['status'] == 'MATCHED'
                and Fraction(r['local_offset']) == Fraction(n.getOffsetInHierarchy(measure))
                and Fraction(r['duration']) == Fraction(n.quarterLength)
                and (n.isRest or n.pitch.nameWithOctave == r['pitch']),
                'Source correspondence mismatch',
            )
            sym = graph['symbols'][r['symbol_id']]
            stems = linked(graph['relations'], 'head-stem', r['symbol_id']) if n.isNote else []
            events.append(
                {
                    'id': r['id'],
                    'symbol_id': r['symbol_id'],
                    'printed_measure': number,
                    'onset': str(Fraction(n.getOffsetInHierarchy(measure))),
                    'duration': str(Fraction(n.quarterLength)),
                    'kind': 'NOTE' if n.isNote else 'REST',
                    'pitch': n.pitch.nameWithOctave if n.isNote else None,
                    'source_bbox': r['bbox'],
                    'physical_source_center': [
                        (r['bbox'][0] + r['bbox'][2]) / 2,
                        (r['bbox'][1] + r['bbox'][3]) / 2,
                    ],
                    'voice': '1',
                    'voice_provenance': 'Single persisted OMR voice; default MusicXML voice may be absent',
                    'stem_direction': n.stemDirection if n.isNote else None,
                    'stem_ids': stems,
                    'beams': (
                        [
                            {'number': b.number, 'type': b.type, 'direction': b.direction}
                            for b in n.beams
                        ]
                        if n.isNote
                        else []
                    ),
                    'tie': getattr(n.tie, 'type', None),
                    'accidental': (
                        n.pitch.accidental.name if n.isNote and n.pitch.accidental else None
                    ),
                    'articulations': [type(a).__name__ for a in n.articulations],
                    'expressions': [type(a).__name__ for a in n.expressions],
                    'omr_lyrics': [
                        {'row': l.number, 'text': l.text, 'syllabic': l.syllabic} for l in n.lyrics
                    ],
                    'raw_symbol': sym,
                    'recognition': 'OMR_RECOGNIZED_FROZEN_GT01_V3_POST_LEDGER',
                    'source_verification': 'UNVERIFIED',
                    'render_evidence': 'OMR_PROVISIONAL',
                    'required_capabilities': (
                        ['HALF_REST' if n.quarterLength == 2 else 'EIGHTH_REST']
                        if n.isRest
                        else (
                            [
                                'VOID_HEAD' if n.quarterLength == 2 else 'BLACK_HEAD',
                                'UP_STEM',
                                'LEDGER_AS_REQUIRED',
                                (
                                    'SINGLE_BEAM'
                                    if len(n.beams)
                                    else (
                                        'FLAG_1'
                                        if linked(graph['relations'], 'flag-stem', stems[0])
                                        else 'UNBEAMED_STEM'
                                    )
                                ),
                            ]
                            if len(stems) == 1
                            else ['MISSING_STEM_LINEAGE']
                        )
                    ),
                }
            )
        require(sum(Fraction(e['duration']) for e in events) == 4, 'Measure duration mismatch')
        records.append(
            {
                'printed_measure': number,
                'omr_bounds': geometry['bounds'],
                'source_visual_registration': 'AGENT_SOURCE_RASTER_REVIEW_NOT_INDEPENDENT_BOUNDARY_GROUND_TRUTH',
                'events': events,
                'recognized_harmonies': [
                    c.figure for c in measure.getElementsByClass(harmony.ChordSymbol)
                ],
                'agent_candidates': CANDIDATES[number],
                'candidate_status': 'AGENT_VISUAL_CANDIDATE',
                'new_chord_printing': (
                    'NONE_NEW_OBSERVED_AGENT_CANDIDATE'
                    if number in (9, 11)
                    else 'VISIBLE_CANDIDATE_MISSING_FROM_OMR'
                ),
            }
        )
    attached = [
        s
        for s in graph['symbols'].values()
        if s['system'] == staff['system'] and s['kind'] in ('articulation', 'fermata')
    ]
    marks = []
    # Each window was individually inspected in the original raster; the upper m10 onset-1 blank is not mirrored.
    for m, row, onset, x in [
        (10, 1, '0', 848),
        (10, 1, '2', 1165),
        (10, 2, '0', 848),
        (10, 2, '1', 1006),
        (10, 2, '2', 1165),
        (12, 1, '0', 1909),
        (12, 1, '1', 2069),
        (12, 1, '2', 2227),
        (12, 2, '0', 1909),
        (12, 2, '1', 2069),
        (12, 2, '2', 2227),
    ]:
        cy = 1307 if row == 1 else 1352
        window = [x - 25, cy - 9, x + 25, cy + 9]
        marks.append(
            {
                'measure': m,
                'row': row,
                'onset_candidate': onset,
                'source_window': window,
                'source_bbox_dark_support': dark_support_bbox(source, window),
                'classification': 'AGENT_VISUAL_CANDIDATE',
                'owner_response': None,
                'rendered': False,
            }
        )
    brackets = [
        {'number': str(s.number), 'measures': [m.number for m in s.getSpannedElements()]}
        for s in score.recurse().getElementsByClass(spanner.RepeatBracket)
        if any(m.number in (8, 9) for m in s.getSpannedElements())
    ]
    return {
        'source_sha256': sha(SOURCE),
        'staff': staff,
        'measures': records,
        'recognized_events': 20,
        'new_owner_verified_events': 0,
        'new_recognition_completeness': 'UNVERIFIED',
        'ambiguous_SIG_objects': [
            {
                'symbol': s,
                'status': 'UNRESOLVED_NOT_RENDERED_NOT_DISCARDED',
                'relations': [
                    r for r in graph['relations'] if s['id'] in (r['source'], r['target'])
                ],
            }
            for s in attached
        ],
        'continuation_candidates': marks,
        'candidate_syllables': 20,
        'visible_continuation_candidates': 11,
        'explicit_negative_observation': {
            'measure': 10,
            'row': 1,
            'onset': '1',
            'observation': 'No visible dash observed; held 르 is a semantic/visual candidate, not an invented mirrored mark',
        },
        'repeat_context': {
            'm1_forward_repeat': str(mm[0].leftBarline),
            'm8_backward_repeat': str(mm[7].rightBarline),
            'serialized_brackets': brackets,
            'second_ending_symbol': graph['symbols']['sheet#1:5193'],
            'raw_relations': [r for r in graph['relations'] if r['source'] == 'sheet#1:5193'],
            'interpretation': 'AGENT_VISUAL_CANDIDATE: second pass skips first ending m8 and proceeds from m7 to m9; first-pass return uses existing opening repeat',
            'playback_expansion': 'NOT_PERFORMED_OR_OWNER_CONFIRMED_IN_THIS_STUDY',
        },
        'new_text_rendering': 'WITHHELD_PENDING_OWNER_REVIEW',
        'independent_ground_truth': False,
    }


def render_music(inv, score, target, graph):
    st = inv['staff']
    inter = st['interline']
    tt, font, scale = font_contract(inter)
    rel = graph['relations']
    parts = {}
    owners = {}
    heads = {}
    nodes = {}
    metrics = []
    allowed = set()
    mm = list(score.parts[0].getElementsByClass(stream.Measure))

    def add(name, p, owner):
        require(name not in parts and p.getbbox() is not None, 'Duplicate or empty component')
        parts[name] = p
        owners[name] = owner

    for m in inv['measures']:
        for e, n in zip(m['events'], events_of(mm[m['printed_measure'] - 1])):
            b = e['source_bbox']
            x = (b[0] + b[2]) / 2
            if n.isRest:
                if e['duration'] == '2':
                    p, info = half_symbol(SIZE, inter, (x, (b[1] + b[3]) / 2), rest=True)
                else:
                    require(e['duration'] == '1/2', 'Unsupported rest')
                    p, info = glyph(
                        SIZE,
                        font,
                        EIGHTH_REST,
                        (x, (b[1] + b[3]) / 2),
                        font_units(tt, EIGHTH_REST),
                        scale,
                    )
                add(e['id'] + ':rest', p, e['id'])
            else:
                require(
                    e['stem_direction'] == 'up' and not e['articulations'] and not e['expressions'],
                    'Unsupported note stream attachment/direction',
                )
                expected = ({'F': 1, 'C': 1, 'G': 1} if target == 'A' else {'F': 1}).get(
                    n.pitch.step, 0
                )
                require(
                    (n.pitch.accidental.alter if n.pitch.accidental else 0) == expected,
                    'Explicit accidental unsupported',
                )
                pos = 35 - n.pitch.diatonicNoteNum
                y = line_y(st['lines'][2], x) + pos * inter / 2
                if e['duration'] == '2':
                    p, info = half_symbol(SIZE, inter, (x, y))
                else:
                    require(e['duration'] == '1/2', 'Unsupported note duration')
                    p, info = glyph(SIZE, font, HEAD, (x, y), font_units(tt, HEAD), scale)
                add(e['id'] + ':head', p, e['id'])
                require(len(e['stem_ids']) == 1, 'One explicit stem required')
                sid = e['stem_ids'][0]
                hs = [
                    r
                    for r in rel
                    if r['source'] == e['symbol_id']
                    and r['target'] == sid
                    and r['kind'] == 'head-stem'
                ]
                require(
                    len(hs) == 1 and dict(hs[0]['attributes']).get('head-side') == 'RIGHT',
                    'Unsupported head-stem attachment',
                )
                px = np.argwhere(np.asarray(p) > 0)
                edge = int(px[:, 1].max() - 1)
                attach = float(np.median(px[px[:, 1] == edge, 0]))
                source_line = graph['symbols'][sid]['geometry']['line']
                require(len(source_line) == 2, 'Missing persisted stem line')
                length = max(3.5 * inter, (b[1] + b[3]) / 2 - min(v[1] for v in source_line))
                tip = y - length
                nodes[sid] = {'x': edge, 'y': y, 'attachment': attach, 'tip': tip, 'event': e}
                heads[e['symbol_id']] = {
                    'event': e,
                    'bbox': p.getbbox(),
                    'target_pitch': n.pitch.nameWithOctave,
                }
                led = Image.new('L', SIZE)
                d = ImageDraw.Draw(led)
                for pp in range(6, pos + 1, 2):
                    yy = line_y(st['lines'][2], x) + pp * inter / 2
                    d.line([(x - 0.875 * inter, yy), (x + 0.875 * inter, yy)], fill=255, width=2)
                if led.getbbox():
                    add(e['id'] + ':ledger', led, e['id'])
                info.update(
                    target_staff_coordinate=[x, y],
                    physical_source_center=e['physical_source_center'],
                )
            require(max(map(abs, info['anchor_residual'])) <= 0.5, 'Raster anchor limit exceeded')
            metrics.append(
                {
                    'event_id': e['id'],
                    'measure': m['printed_measure'],
                    'kind': e['kind'],
                    'source_pitch': e['pitch'],
                    'target_pitch': n.pitch.nameWithOctave if n.isNote else None,
                    'evidence': 'OMR_PROVISIONAL',
                    **info,
                }
            )
    beams = []
    beamed = set()
    for beam in graph['symbols'].values():
        if beam['system'] != st['system'] or beam['kind'] not in ('beam', 'beam-hook'):
            continue
        members = linked(rel, 'beam-stem', beam['id'])
        require(
            beam['kind'] == 'beam' and members and all(s in nodes for s in members),
            'Incomplete or unsupported beam group',
        )
        require(
            not (set(members) & beamed),
            'Multiple beams unsupported in this single-level source scope',
        )
        spec, tips = single_beam({s: nodes[s] for s in members}, beam, inter)
        for sid, yy in tips.items():
            nodes[sid]['tip'] = yy
        beamed.update(members)
        beams.append(spec)
    flags = []
    for sid, node in nodes.items():
        e = node['event']
        tip = node['tip']
        flagids = linked(rel, 'flag-stem', sid)
        if not e['beams']:
            require(
                (e['duration'] == '2' and not flagids)
                or (e['duration'] == '1/2' and len(flagids) == 1),
                'Required flag count/duration mismatch',
            )
        if flagids:
            require(
                not e['beams']
                and len(flagids) == 1
                and graph['symbols'][flagids[0]]['shape'] == 'FLAG_1',
                'Unsupported flag relation',
            )
            tip = math.floor(tip + 0.5)
            node['tip'] = tip
            p, info = flag_mask(SIZE, font, (node['x'], tip), font_units(tt, FLAG), scale)
            add(e['id'] + ':flag', p, e['id'])
            flags.append({'event_id': e['id'], 'symbol_id': flagids[0], **info})
        stem = Image.new('L', SIZE)
        ImageDraw.Draw(stem).line(
            [(node['x'], node['attachment']), (node['x'], tip)], fill=255, width=2
        )
        add(e['id'] + ':stem', stem, e['id'])
    for b in beams:
        p = Image.new('L', SIZE)
        ImageDraw.Draw(p).line([tuple(q) for q in b['line']], fill=255, width=b['thickness'])
        add(b['id'], p, b['id'])
        for s in b['members']:
            allowed.add(frozenset((b['id'], nodes[s]['event']['id'] + ':stem')))
    curves = []
    for c in graph['symbols'].values():
        if c['system'] == st['system'] and c['kind'] == 'slur':
            require('tie="true"' in c['source_xml'], 'Unsupported non-tie slur')
            cp, info = local_tie(c, rel, heads)
            add(c['id'], curve_mask(SIZE, cp), c['id'])
            curves.append(info)
    connections = []
    for s, node in nodes.items():
        stem = parts[node['event']['id'] + ':stem']
        neighbors = [node['event']['id'] + ':head'] + [b['id'] for b in beams if s in b['members']]
        if node['event']['id'] + ':flag' in parts:
            neighbors.append(node['event']['id'] + ':flag')
        for n in neighbors:
            connections.append(
                {
                    'stem': s,
                    'component': n,
                    'contact_pixels': int(
                        np.count_nonzero((np.asarray(stem) > 0) & (np.asarray(parts[n]) > 0))
                    ),
                }
            )
    collisions = contacts(parts)
    for c in collisions:
        c['intentional'] = (
            owners[c['a']] == owners[c['b']]
            and frozenset((c['a'].split(':')[-1], c['b'].split(':')[-1]))
            in {
                frozenset(('head', 'stem')),
                frozenset(('head', 'ledger')),
                frozenset(('stem', 'ledger')),
                frozenset(('stem', 'flag')),
            }
        ) or frozenset((c['a'], c['b'])) in allowed
    clip = [
        n
        for n, p in parts.items()
        if p.getbbox()[0] < VIEW[0]
        or p.getbbox()[2] > VIEW[2]
        or p.getbbox()[1] < VIEW[1]
        or p.getbbox()[3] > VIEW[3]
    ]
    return parts, {
        'target': target,
        'recognized_events': 20,
        'displayed_note_rest_cores': len(metrics),
        'owner_verified_new_events': 0,
        'provisional_events': len(metrics),
        'event_metrics': metrics,
        'beams': beams,
        'flags': flags,
        'ties': curves,
        'connections': connections,
        'missing_connections': [c for c in connections if not c['contact_pixels']],
        'actual_component_intersections': collisions,
        'unexpected_intersections': [c for c in collisions if not c['intentional']],
        'clipping': clip,
        'max_head_residual': max(
            max(map(abs, m['anchor_residual'])) for m in metrics if m['kind'] == 'NOTE'
        ),
        'third_lyric_music_contacts': 'NOT_EVALUABLE_NEW_LYRICS_WITHHELD_NOT_ZERO',
        'new_chords_rendered': 0,
        'new_lyric_syllables_rendered': 0,
        'new_lyric_continuation_marks_rendered': 0,
        'required_unknown_attachments': inv['ambiguous_SIG_objects'],
        'rendering_completeness': 'INCOMPLETE_MUSIC_CORE_PROVISIONAL_TEXT_AND_DISPUTED_ATTACHMENTS_WITHHELD',
    }


def second_ending(size, graph):
    e = graph['symbols']['sheet#1:5193']
    raw = ET.fromstring(e['source_xml'])

    def xy(path):
        p = raw.find(path)
        require(p is not None, 'Missing ending geometry')
        return (float(p.get('x')), float(p.get('y')))

    pts = [xy('left-leg/p2'), xy('left-leg/p1'), xy('line/p1'), xy('line/p2')]
    require(raw.find('right-leg') is None, 'Unexpected closed second ending')
    p = Image.new('L', size)
    ImageDraw.Draw(p).line(pts, fill=255, width=2)
    num, meta = text_mask(size, ImageFont.truetype(str(FONT), 40), '2.', left_top=(287, 1087))
    return {'provisional-ending2-bracket': p, 'provisional-ending2-number': num}, {
        'source_id': e['id'],
        'path': pts,
        'number': meta,
        'classification': 'OMR_PROVISIONAL_NOT_OWNER_CONFIRMED',
        'playback_expanded': False,
    }


def frame(image, title, scope):
    out = Image.new('RGB', (image.width, image.height + 180), 'white')
    d = ImageDraw.Draw(out)
    f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20)
    for i, t in enumerate(
        [
            'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING',
            title,
            scope,
            'System 3: MUSIC-ONLY / OMR_PROVISIONAL; 2 chord candidates, 20 lyric syllables and 11 continuation marks WITHHELD.',
            'Disputed TENUTO/ACCENT SIG objects unresolved. No source ink editing or original lyric-pixel composition.',
        ]
    ):
        d.text((10, 8 + i * 30), t, font=f, fill='black')
    out.paste(image, (0, 180))
    return out


def run(out):
    require(not out.exists(), 'Fresh output required')
    protocol = read(PROTOCOL)
    require(sha(SOURCE) == protocol['source_sha256'], 'Source hash mismatch')
    for n, h in read(PRIOR / 'prediction-freeze.json')['files'].items():
        require(sha(PRIOR / n) == h, 'GT14E freeze mismatch')
    history = {str(PRIOR): file_hashes(PRIOR), str(GT14A): file_hashes(GT14A)}
    original = Image.open(SOURCE)
    graph = read(SOURCE_DIR / 'visual-graph.json')
    source = converter.parse(str(GT14A / 'owner-augmented-source.musicxml'))
    rows = read(GT02 / 'note-correspondence-diagnostic.json')['events']['Bb']
    inv = inventory(source, graph, rows, original)
    out.mkdir()
    dump(out / 'source-event-inventory.json', inv)
    crops = [save_native(original, list(VIEW), out / 'source-third-system-native.png')]
    for m in inv['measures']:
        box = [
            max(130, int(m['omr_bounds'][0]) - 15),
            1030,
            min(2430, int(m['omr_bounds'][2]) + 15),
            1390,
        ]
        crops.append(save_native(original, box, out / f'source-measure-{m["printed_measure"]}.png'))
    review = frame(
        original.crop(VIEW),
        'SOURCE-ONLY ORIGINAL Bb / third printed system, measures 9-12',
        'OWNER REVIEW PENDING / no target predictions or corrected answers in the source pixels',
    )
    review.save(out / 'source-third-system-review-sheet.png')
    transition = Image.new('RGB', (1300, 560), 'white')
    d = ImageDraw.Draw(transition)
    d.text(
        (10, 10),
        'SOURCE-ONLY: m8 ending 1/backward repeat and m9 ending 2; interpretation pending',
        fill='black',
        font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20),
    )
    transition.paste(original.crop((1920, 700, 2430, 1020)), (10, 60))
    transition.paste(original.crop((130, 1030, 850, 1390)), (560, 60))
    transition.save(out / 'source-ending-transition-review.png')
    checklist = {
        'classification': 'OWNER_REVIEW_PENDING_NOT_INDEPENDENT_GROUND_TRUTH',
        'source_sha256': sha(SOURCE),
        'source_review_sheet_sha256': sha(out / 'source-third-system-review-sheet.png'),
        'instructions_ko': '9–12마디의 음표·쉼표·리듬·붙임줄, 코드와 두 가사 줄/음절 대응, 2번 괄호를 각각 확인하거나 수정해 주세요. 원본 관찰과 OMR/에이전트 후보는 독립 정답이 아닙니다. 불확실한 항목은 보류하세요.',
        'measures': [
            {
                'printed_measure': m['printed_measure'],
                'events': m['events'],
                'candidate_text': m['agent_candidates'],
                'source_image': f'source-measure-{m["printed_measure"]}.png',
                'music_answer': None,
                'chord_answer': None,
                'lyrics_answer': None,
                'association_answer': None,
                'corrections': None,
            }
            for m in inv['measures']
        ],
        'continuations': inv['continuation_candidates'],
        'ambiguous_objects': inv['ambiguous_SIG_objects'],
        'repeat_ending_answer': None,
        'repeat_candidate': inv['repeat_context'],
        'new_owner_confirmations': 0,
    }
    dump(out / 'owner-review-checklist.json', checklist)
    dump(out / 'source-review-crop-map.json', crops)
    dump(
        out / 'input-freeze.json',
        {
            'history_files': history,
            'source_sha256': sha(SOURCE),
            'omr_sha256': sha(SOURCE_DIR / 'recognized.omr'),
            'graph_sha256': sha(SOURCE_DIR / 'visual-graph.json'),
            'source_rows_sha256': sha(GT02 / 'note-correspondence-diagnostic.json'),
            'font_sha256': sha(FONT),
            'protocol_sha256': sha(PROTOCOL),
            'producer_sha256': sha(Path(__file__)),
            'notation_helper_sha256': sha(ROOT / 'scripts/research/gt15_notation.py'),
        },
    )
    guards = {
        'source_roundtrip': validate(
            source, converter.parse(str(GT14A / 'owner-augmented-source.musicxml')), 0, 'key'
        ).to_dict()
    }
    reports = []
    images = []
    for target, shift in [('A', -1), ('G', -3)]:
        score = copy.deepcopy(source)
        summary = transpose_score(score, shift, 'key')
        score.write('musicxml', fp=str(out / f'{target}-semantic.musicxml'))
        parsed = converter.parse(str(out / f'{target}-semantic.musicxml'))
        frozen = converter.parse(str(GT14A / f'{target}-transposed.musicxml'))
        guards[target] = {
            'in_memory': validate(source, score, shift, 'key', summary).to_dict(),
            'serialized': validate(source, parsed, shift, 'key', summary).to_dict(),
            'existing_frozen_target': validate(source, frozen, shift, 'key', summary).to_dict(),
        }
        require(all(r['ok'] for r in guards[target].values()), 'Full V3 semantic guard failed')
        require(
            full_lyric_signature(source) == full_lyric_signature(parsed),
            'Existing lyric signature changed',
        )
        require(
            [event_signature(m) for m in parsed.parts[0].getElementsByClass(stream.Measure)]
            == [event_signature(m) for m in frozen.parts[0].getElementsByClass(stream.Measure)],
            'Frozen target events changed',
        )
        parts, report = render_music(inv, score, target, graph)
        hp, hm = header(SIZE, inv['staff'], target, FONT)
        context = {
            f'provisional-header-{n}': p
            for n, p in hp.items()
            if n == 'clef' or n.startswith('sharp')
        }
        ep, em = second_ending(SIZE, graph)
        context.update(ep)
        context['staff-and-barlines'] = scaffold(
            SIZE,
            inv['staff'],
            [807, 1338, 1869, 2400],
            {2400: graph['symbols']['sheet#1:58']['geometry']['bbox']},
        )
        music = union(list(parts.values()))
        alpha = union([music, *context.values()])
        require(
            not np.asarray(alpha)[:1030].any(),
            'Third-system ink intrudes into frozen first two systems',
        )
        image = Image.composite(
            Image.new('RGB', SIZE, '#3057a0'), Image.new('RGB', SIZE, 'white'), alpha
        )
        shown = frame(
            image.crop(VIEW),
            f'{target} major third system / printed 9-12 / {len(report["event_metrics"])} of 20 recognized event cores',
            'BLUE NOTATION = OMR_PROVISIONAL; no new source-owner confirmation',
        )
        shown.save(out / f'predicted-{target.lower()}-third-system.png')
        images.append(shown)
        alpha.save(out / f'{target}-third-system-alpha.png')
        for n, p in parts.items():
            p.save(out / f'{target}-{n.replace(":","_")}-alpha.png')
        old = Image.open(PRIOR / f'{target}-integrated-alpha.png')
        base = Image.new('L', SIZE)
        base.paste(old, (0, 0))
        merged = union([base, alpha])
        require(
            merged.crop((0, 0, SIZE[0], 1030)).tobytes()
            == base.crop((0, 0, SIZE[0], 1030)).tobytes(),
            'First two system pixels changed',
        )
        overlap = int(np.count_nonzero((np.asarray(base) > 0) & (np.asarray(alpha) > 0)))
        require(overlap == 0, 'New/old system alpha collision')
        canvas = Image.composite(
            Image.new('RGB', SIZE, 'black'), Image.new('RGB', SIZE, 'white'), base
        )
        canvas = Image.composite(Image.new('RGB', SIZE, '#3057a0'), canvas, alpha)
        frame(
            canvas.crop((130, 310, 2430, 1390)),
            f'{target} major first-through-third-system preview',
            'BLACK systems 1-2 = existing OWNER_VERIFIED scoped source; BLUE system 3 = OMR_PROVISIONAL / MUSIC-ONLY',
        ).save(out / f'{target}-three-systems.png')
        report.update(
            {
                'header_context': 'SOURCE_SUPPORTED_CLEF_KEY_ONLY_PROVISIONAL',
                'ending2': em,
                'context_event_contact_pairs': contacts(
                    {**parts, **{k: v for k, v in context.items() if k != 'staff-and-barlines'}}
                ),
                'first_two_systems_unchanged': True,
                'new_old_system_contact_pixels': overlap,
                'retained_confirmed_events': 39,
                'retained_confirmed_chords': 5,
                'retained_confirmed_syllables': 50,
                'retained_confirmed_continuation_marks': 10,
                'total_displayed_event_cores': 39 + len(report['event_metrics']),
                'source_verification': 'UNVERIFIED_NEW_SYSTEM_OMR_PROVISIONAL',
                'visual_quality': 'PENDING_POST_FREEZE_AGENT_INSPECTION',
            }
        )
        reports.append(report)
    source_panel = frame(
        original.crop(VIEW),
        'Unchanged original Bb third-system evidence',
        'Source comparison only; no A/G reference page accessed',
    )
    sheet = Image.new('RGB', (source_panel.width, source_panel.height * 3), 'white')
    for i, p in enumerate([source_panel, *images]):
        sheet.paste(p, (0, i * source_panel.height))
    sheet.save(out / 'third-system-comparison.png')
    dump(out / 'rendering-validation.json', reports)
    dump(out / 'semantic-integrity.json', guards)
    require(guards['source_roundtrip']['ok'], 'Source full guard failed')
    require(
        all(file_hashes(Path(p)) == h for p, h in history.items())
        and sha(SOURCE) == protocol['source_sha256'],
        'Historical or source mutation',
    )
    dump(
        out / 'validation-summary.json',
        {
            'status': 'PROVISIONAL_MUSIC_ONLY_THIRD_SYSTEM_PENDING_VISUAL_REVIEW',
            'new_recognized_events': 20,
            'new_owner_verified_events': 0,
            'new_chord_candidates': 2,
            'new_lyric_syllable_candidates': 20,
            'new_continuation_candidates': 11,
            'unresolved_SIG_objects': len(inv['ambiguous_SIG_objects']),
            'new_text_rendered': False,
            'old_two_systems_preserved': True,
            'full_V3_guards': 'PASS',
            'independent_labels': 0,
        },
    )
    dump(
        out / 'prediction-freeze.json',
        {
            'files': file_hashes(out),
            'phase': 'BEFORE_AGENT_VISUAL_REVIEW_NO_TARGET_REFERENCE_ACCESS',
        },
    )


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    run(p.parse_args().out)
