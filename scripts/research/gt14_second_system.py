"""Second-system source audit and explicitly provisional standalone music expansion."""

import argparse
import copy
import itertools
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

import numpy as np
from fontTools.ttLib import TTFont
from music21 import converter, harmony, pitch, stream
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt04_visual import HEAD, REST
from scripts.research.gt05_raster_anchor import glyph
from scripts.research.gt06_extended import beam_geometry, semantic_check
from scripts.research.gt11_complete_measure import FONT, events_of, require, read
from scripts.research.gt13a2_provisional import (
    EIGHTH_REST,
    linked,
    mixed_layout,
    curve_mask,
    translated_curve,
    ink_distance,
)
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.gt13a_full_system import scaffold
from scripts.research.gt13a5_lyric_layout import union, verify_freeze, SOURCE, OLD
from scripts.research.gt13a6_tie_review import SOURCE_DIR, GT02, endpoint_pair
from scripts.research.gt13a6_tie_rendering import (
    confirmed_record,
    PACKET,
    ORIGINAL_RECORD,
    whole_head,
)
from scripts.research.paired_ground_truth_01 import dump, file_hashes, line_y, sha

ROOT = Path(__file__).resolve().parents[2]
PRIOR = Path('/private/tmp/capomatic-v4-gt13a6/gt13a6-phase2-output')
PROTOCOL = ROOT / 'docs/V4_GT14_PROTOCOL.json'
SIZE = (2520, 1100)
VIEW = (130, 700, 2430, 1030)
CANDIDATES = {
    5: {'chord': 'Gm', 'upper': ['—'], 'lower': ['—']},
    6: {
        'chord': 'Bb/D',
        'upper': ['내', '가', '있', '길', '원', '—', '하', '네'],
        'lower': ['주', '의', '놀', '라', '운', '—', '손', '길'],
    },
    7: {'chord': 'Eb', 'upper': ['—'], 'lower': ['—']},
    8: {'chord': None, 'upper': [], 'lower': []},
}


def system_inventory(score, graph, rows, registration):
    staff = next(s for s in graph['staves'] if s['id'] == 'sheet#1:2')
    source_measures = list(score.parts[0].getElementsByClass(stream.Measure))
    records = []
    for number in (5, 6, 7, 8):
        m = source_measures[number - 1]
        r = sorted(
            [r for r in rows if r['omr_measure_index'] == number - 1],
            key=lambda r: Fraction(r['local_offset']),
        )
        notes = events_of(m)
        require(len(notes) == len(r), 'Event mapping count differs')
        geometry = next(
            g
            for g in graph['measures']
            if g['system'] == staff['system'] and g['number'] == str(number)
        )
        printed = next(p for p in registration['measures'] if p['printed_measure'] == number)
        omr_voices = [v.get('id') for v in ET.fromstring(geometry['source_xml']).findall('voice')]
        events = []
        for n, v in zip(notes, r):
            require(
                v['printed_measures'] == [number]
                and Fraction(v['local_offset']) == Fraction(n.getOffsetInHierarchy(m))
                and Fraction(v['duration']) == Fraction(n.quarterLength)
                and (n.isRest or n.pitch.nameWithOctave == v['pitch']),
                'Nonunique physical/semantic correspondence',
            )
            verified = number == 5 and v['symbol_id'] == 'sheet#1:1923'
            if verified:
                require(
                    n.isNote
                    and n.pitch.nameWithOctave == 'B-3'
                    and n.quarterLength == 4
                    and n.tie is not None
                    and n.tie.type == 'stop',
                    'Confirmed m5 identity changed',
                )
            symbol = graph['symbols'][v['symbol_id']]
            events.append(
                {
                    'id': v['id'],
                    'symbol_id': v['symbol_id'],
                    'printed_measure': number,
                    'onset': str(Fraction(n.getOffsetInHierarchy(m))),
                    'duration': str(Fraction(n.quarterLength)),
                    'kind': 'NOTE' if n.isNote else 'REST',
                    'pitch': n.pitch.nameWithOctave if n.isNote else None,
                    'voice': (
                        v.get('voice')
                        if v.get('voice') is not None
                        else (omr_voices[0] if len(omr_voices) == 1 else 'UNRESOLVED')
                    ),
                    'voice_provenance': 'Persisted OMR voice; default MusicXML voice may be omitted',
                    'source_bbox': v['bbox'],
                    'grade': symbol['grade'],
                    'ctx_grade': symbol['contextual_grade'],
                    'stem_direction': n.stemDirection if n.isNote else None,
                    'tie': getattr(n.tie, 'type', None),
                    'beams': (
                        [
                            {'number': b.number, 'type': b.type, 'direction': b.direction}
                            for b in n.beams
                        ]
                        if n.isNote
                        else []
                    ),
                    'accidental': (
                        n.pitch.accidental.name if n.isNote and n.pitch.accidental else None
                    ),
                    'omr_lyrics': [
                        {'row': l.number, 'text': l.text, 'syllabic': l.syllabic} for l in n.lyrics
                    ],
                    'articulations': [type(a).__name__ for a in n.articulations],
                    'expressions': [type(a).__name__ for a in n.expressions],
                    'recognition': 'OMR_RECOGNIZED',
                    'source_verification': 'OWNER_VERIFIED_SOURCE' if verified else 'UNVERIFIED',
                    'render_evidence': 'OWNER_VERIFIED_SOURCE' if verified else 'OMR_PROVISIONAL',
                }
            )
        records.append(
            {
                'printed_measure': number,
                'omr_bounds': geometry['bounds'],
                'physical_candidate_bounds': [printed['left']['x'], printed['right']['x']],
                'boundary_evidence': 'GT02_COORDINATOR_REGISTRATION_NOT_INDEPENDENT_GROUND_TRUTH',
                'duration_total': str(sum((Fraction(e['duration']) for e in events), Fraction(0))),
                'events': events,
                'recognized_harmonies': [
                    c.figure for c in m.getElementsByClass(harmony.ChordSymbol)
                ],
                'agent_visual_candidates': CANDIDATES[number],
                'candidate_classification': 'AGENT_VISUAL_CANDIDATE',
                'lyrics_and_associations': 'UNVERIFIED_NOT_RENDERED',
                'chords': 'UNVERIFIED_NOT_RENDERED',
            }
        )
    ids = {s['id'] for s in graph['symbols'].values() if s['system'] == staff['system']}
    rel = [r for r in graph['relations'] if r['source'] in ids or r['target'] in ids]
    attached = [
        s
        for s in graph['symbols'].values()
        if s['id'] in ids and s['kind'] in ('articulation', 'fermata', 'ending', 'repeat-dot')
    ]
    return {
        'source_sha256': sha(SOURCE),
        'staff': staff,
        'measures': records,
        'notation_relations': rel,
        'related_symbols': [s for s in graph['symbols'].values() if s['id'] in ids],
        'potential_attachments_and_structures': attached,
        'SOURCE_RECOGNITION_COMPLETENESS': 'UNVERIFIED',
        'owner_verified_events': 1,
        'recognition_note': 'Internal MusicXML duration/guard agreement does not prove printed completeness',
        'independent_ground_truth': False,
    }


def local_tie(curve, relations, heads):
    rs = [r for r in relations if r['source'] == curve['id'] and r['kind'] == 'slur-head']
    require(len(rs) == 2, 'Incomplete local tie lineage')
    ends = {dict(r['attributes'])['side']: heads[r['target']] for r in rs}
    require(set(ends) == {'LEFT', 'RIGHT'}, 'Missing local tie side')
    a, b = ends['LEFT'], ends['RIGHT']
    require(
        a['event']['tie'] == 'start'
        and b['event']['tie'] == 'stop'
        and a['target_pitch'] == b['target_pitch'],
        'Tie semantic mismatch',
    )
    cp = translated_curve(
        curve['geometry']['curve'],
        a['bbox'][3] - a['event']['source_bbox'][3],
        b['bbox'][3] - b['event']['source_bbox'][3],
    )
    residuals = []
    for i, h in [(0, a), (-1, b)]:
        source = h['event']['source_bbox']
        target = h['bbox']
        source_ref = [(source[0] + source[2]) / 2, source[3]]
        target_ref = [(target[0] + target[2] - 1) / 2, target[3]]
        offset = [curve['geometry']['curve'][i][k] - source_ref[k] for k in (0, 1)]
        res = [cp[i][k] - (target_ref[k] + offset[k]) for k in (0, 1)]
        require(max(map(abs, res)) <= 0.5, 'Local tie attachment exceeds 0.5px')
        residuals.append(res)
    return cp, {
        'curve_id': curve['id'],
        'head_ids': [r['target'] for r in rs],
        'source_verification': 'UNVERIFIED_OMR_PROVISIONAL',
        'attachment_residuals': residuals,
        'curve': cp,
    }


def render_music(inv, source_score, target_score, target, graph):
    staff = inv['staff']
    inter = staff['interline']
    parts = {}
    owners = {}
    heads = {}
    nodes = {}
    metrics = []
    blocked = []

    def add(name, mask, owner):
        require(name not in parts and mask.getbbox(), 'Duplicate or empty component')
        parts[name] = mask
        owners[name] = owner

    tt = TTFont(FONT)
    upm = tt['head'].unitsPerEm
    chars = (HEAD, REST, EIGHTH_REST)
    units = {
        c: tuple(
            getattr(tt['glyf'][tt.getBestCmap()[ord(c)]], k)
            for k in ['xMin', 'yMin', 'xMax', 'yMax']
        )
        for c in chars
    }
    fs = round(1.25 * inter * upm / (units[HEAD][2] - units[HEAD][0]))
    font = ImageFont.truetype(str(FONT), fs)
    measures = list(target_score.parts[0].getElementsByClass(stream.Measure))
    source_measures = list(source_score.parts[0].getElementsByClass(stream.Measure))
    rel = inv['notation_relations']
    symbols = graph['symbols']
    semantic = {}
    for m in inv['measures']:
        number = m['printed_measure']
        notes = events_of(measures[number - 1])
        require(len(notes) == len(m['events']), 'Target event count changed')
        for e, n in zip(m['events'], notes):
            semantic[e['id']] = n
            b = e['source_bbox']
            x = (b[0] + b[2]) / 2
            if number == 5:
                head = Image.open(PRIOR / f'{target}-whole-note-alpha.png').copy()
                add(e['id'] + ':head', head, e['id'])
                add(
                    e['id'] + ':ledger',
                    Image.open(PRIOR / f'{target}-whole-ledger-alpha.png').copy(),
                    e['id'],
                )
                info = read(PRIOR / 'endpoint-rendering-validation.json')
                meta = next(r for r in info if r['target'] == target)['incoming_whole_note']
            elif e['kind'] == 'REST':
                if e['duration'] not in ('1', '1/2'):
                    blocked.append(
                        {
                            'event_id': e['id'],
                            'reason': 'WHOLE_REST_NOT_VALIDATED',
                            'displayed': False,
                        }
                    )
                    continue
                ch = REST if e['duration'] == '1' else EIGHTH_REST
                head, meta = glyph(SIZE, font, ch, (x, (b[1] + b[3]) / 2), units[ch], fs / upm)
                add(e['id'] + ':rest', head, e['id'])
            elif e['duration'] == '4':
                head, meta = whole_head(SIZE, staff, x, n.pitch.nameWithOctave)
                add(e['id'] + ':head', head, e['id'])
                ledger = Image.new('L', SIZE)
                d = ImageDraw.Draw(ledger)
                hb = head.getbbox()
                for pos in range(6, meta['staff_position'] + 1, 2):
                    y = line_y(staff['lines'][2], x) + pos * inter / 2
                    d.line([(hb[0] - 4, y), (hb[2] + 3, y)], fill=255, width=2)
                add(e['id'] + ':ledger', ledger, e['id'])
            else:
                require(
                    n.isNote and e['stem_direction'] == 'up' and not e['articulations'],
                    'Unsupported note/direction',
                )
                expected = {'A': {'F': 1, 'C': 1, 'G': 1}, 'G': {'F': 1}}[target].get(
                    n.pitch.step, 0
                )
                require(
                    (n.pitch.accidental.alter if n.pitch.accidental else 0) == expected,
                    'Explicit accidental unsupported',
                )
                pos = 35 - n.pitch.diatonicNoteNum
                y = line_y(staff['lines'][2], x) + pos * inter / 2
                head, meta = glyph(SIZE, font, HEAD, (x, y), units[HEAD], fs / upm)
                add(e['id'] + ':head', head, e['id'])
                px = np.argwhere(np.asarray(head) > 0)
                edge = int(px[:, 1].max() - 1)
                attach = float(np.median(px[px[:, 1] == edge, 0]))
                stems = linked(rel, 'head-stem', e['symbol_id'])
                require(len(stems) == 1, 'Stem relation missing')
                nodes[stems[0]] = {
                    'x': edge,
                    'y': y,
                    'attachment': attach,
                    'event': e,
                    'tip': y - 3.5 * inter,
                }
                ledger = Image.new('L', SIZE)
                d = ImageDraw.Draw(ledger)
                for pp in range(6, pos + 1, 2):
                    ly = line_y(staff['lines'][2], x) + pp * inter / 2
                    d.line([(x - 0.875 * inter, ly), (x + 0.875 * inter, ly)], fill=255, width=2)
                if ledger.getbbox():
                    add(e['id'] + ':ledger', ledger, e['id'])
            require(max(map(abs, meta['anchor_residual'])) <= 0.5, 'Anchor criterion failed')
            metrics.append(
                {
                    'event_id': e['id'],
                    'measure': number,
                    'source_verification': e['source_verification'],
                    'kind': e['kind'],
                    'target_pitch': n.pitch.nameWithOctave if n.isNote else None,
                    **meta,
                }
            )
            if e['kind'] == 'NOTE':
                heads[e['symbol_id']] = {
                    'event': e,
                    'bbox': head.getbbox(),
                    'target_pitch': n.pitch.nameWithOctave,
                }
    pair_events = [
        e
        for m in inv['measures']
        for e in m['events']
        if m['printed_measure'] == 6 and e['onset'] in ('3/2', '7/4')
    ]
    require(len(pair_events) == 2, 'Explicit sixteenth pair missing')
    for i, e in enumerate(pair_events):
        semantic_check(events_of(source_measures[5])[2 + i], i, e['pitch'])
        semantic_check(semantic[e['id']], i, semantic[e['id']].pitch.nameWithOctave)
    pair_ids = {s for s, v in nodes.items() if v['event']['id'] in {e['id'] for e in pair_events}}
    beams = [
        s
        for s in inv['related_symbols']
        if s['kind'] == 'beam' and set(linked(rel, 'beam-stem', s['id'])) == pair_ids
    ]
    require(len(beams) == 2, 'Incomplete double-beam pair')
    br = beam_geometry([(nodes[s]['x'], nodes[s]['y']) for s in pair_ids], beams, inter, True)
    for s in pair_ids:
        nodes[s]['tip'] = line_y(br[0]['line'], nodes[s]['x'])
    others = {s: n for s, n in nodes.items() if s not in pair_ids}
    # Existing mixed_layout consumes event_id, while the new audit's canonical key is id.
    compatible = copy.deepcopy(others)
    for v in compatible.values():
        v['event']['event_id'] = v['event']['id']
    mixed, tips = mixed_layout(compatible, symbols, rel, inter)
    for s, y in tips.items():
        nodes[s]['tip'] = y
    br = [
        {
            'id': b['symbol_id'],
            'line': b['line'],
            'thickness': b['thickness'],
            'members': sorted(pair_ids),
        }
        for b in br
    ] + mixed
    allowed = set()
    for s, node in nodes.items():
        mask = Image.new('L', SIZE)
        ImageDraw.Draw(mask).line(
            [(node['x'], node['attachment']), (node['x'], node['tip'])], fill=255, width=2
        )
        add(node['event']['id'] + ':stem', mask, node['event']['id'])
        require(
            not linked(rel, 'flag-stem', s), 'Unexpected flag not in this supported source system'
        )
    for b in br:
        mask = Image.new('L', SIZE)
        ImageDraw.Draw(mask).line([tuple(p) for p in b['line']], fill=255, width=b['thickness'])
        add(b['id'], mask, b['id'])
        for s in b['members']:
            allowed.add(frozenset((b['id'], nodes[s]['event']['id'] + ':stem')))
    curves = []
    incoming = Image.open(PRIOR / f'{target}-incoming-tie-alpha.png').copy()
    add('confirmed-incoming-tie', incoming, 'confirmed-incoming-tie')
    for c in inv['related_symbols']:
        if c['kind'] == 'slur' and c['id'] != 'sheet#1:4798':
            cp, ci = local_tie(c, rel, heads)
            add(c['id'], curve_mask(SIZE, cp), c['id'])
            curves.append(ci)
    collisions = []
    for a, b in itertools.combinations(parts, 2):
        aa = parts[a]
        bb = parts[b]
        ba = aa.getbbox()
        bc = bb.getbbox()
        box = (max(ba[0], bc[0]), max(ba[1], bc[1]), min(ba[2], bc[2]), min(ba[3], bc[3]))
        if box[0] < box[2] and box[1] < box[3]:
            count = int(
                np.count_nonzero((np.asarray(aa.crop(box)) > 0) & (np.asarray(bb.crop(box)) > 0))
            )
            if count:
                collisions.append(
                    {
                        'a': a,
                        'b': b,
                        'pixels': count,
                        'intentional': owners[a] == owners[b] or frozenset((a, b)) in allowed,
                    }
                )
    connections = []
    for s, v in nodes.items():
        stem = parts[v['event']['id'] + ':stem']
        partners = [v['event']['id'] + ':head'] + [b['id'] for b in br if s in b['members']]
        for p in partners:
            count = int(np.count_nonzero((np.asarray(stem) > 0) & (np.asarray(parts[p]) > 0)))
            connections.append({'stem': s, 'component': p, 'contact_pixels': count})
    clipping = [
        n
        for n, m in parts.items()
        if m.getbbox()[0] < VIEW[0]
        or m.getbbox()[2] > VIEW[2]
        or m.getbbox()[1] < VIEW[1]
        or m.getbbox()[3] > VIEW[3]
    ]
    return parts, {
        'target': target,
        'recognized_events': 13,
        'owner_verified_events': 1,
        'actually_rendered_events': len(metrics),
        'owner_verified_rendered': sum(
            m['source_verification'] == 'OWNER_VERIFIED_SOURCE' for m in metrics
        ),
        'provisional_rendered': sum(
            m['source_verification'] != 'OWNER_VERIFIED_SOURCE' for m in metrics
        ),
        'unrendered_events': blocked,
        'event_metrics': metrics,
        'beam_geometry': br,
        'ties': curves,
        'intersections': collisions,
        'unexpected_intersections': [c for c in collisions if not c['intentional']],
        'connections': connections,
        'missing_connections': [c for c in connections if not c['contact_pixels']],
        'clipping': clipping,
        'max_head_anchor_residual': max(
            max(map(abs, m['anchor_residual'])) for m in metrics if m['kind'] == 'NOTE'
        ),
        'missing_chords': 3,
        'missing_lyric_rows': 2,
        'new_lyric_music_contacts': None,
        'lyric_clearance': 'NOT_EVALUABLE_UNVERIFIED_TEXT_WITHHELD',
        'new_unsupported_attachments': inv['potential_attachments_and_structures'],
        'SOURCE_RECOGNITION_COMPLETENESS': 'UNVERIFIED',
        'RENDERING_COMPLETENESS': 'INCOMPLETE',
    }


def panel(native, title):
    im = Image.new('RGB', (native.width, native.height + 155), 'white')
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20)
    lines = [
        'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING',
        title,
        'BLACK: confirmed m5 endpoint + OMR geometry context. AMBER: OMR_PROVISIONAL music.',
        'WITHHELD: all new chords/lyrics; whole rest m8; ending1/final repeat; disputed articulation/fermata support',
    ]
    for i, text in enumerate(lines):
        d.text((10, 8 + i * 30), text, font=f, fill='black')
    im.paste(native, (0, 155))
    return im


def paint(black, amber):
    im = Image.new('RGB', SIZE, 'white')
    im.paste('black', (0, 0, *SIZE), black)
    im.paste((150, 85, 0), (0, 0, *SIZE), amber)
    return im


def run(out):
    require(
        out.exists() and sorted(p.name for p in out.iterdir()) == ['original-second-system.png'],
        'Source-review-only directory required; never overwrite target predictions',
    )
    verify_freeze(PRIOR)
    verify_freeze(OLD)
    owner = confirmed_record(ORIGINAL_RECORD, PACKET)
    require(sha(FONT) == read(PRIOR / 'input-freeze.json')['font_sha256'], 'Pinned font changed')
    require(
        sha(ORIGINAL_RECORD) == read(PRIOR / 'source-verification.json')['confirmation_sha256'],
        'Confirmed record identity changed',
    )
    source_hash = sha(SOURCE)
    require(source_hash == owner['source_sha256'], 'Source hash mismatch')
    protocol = read(PROTOCOL)
    histories = {str(p): file_hashes(p) for p in (PRIOR, OLD, PACKET)}
    graph = read(SOURCE_DIR / 'visual-graph.json')
    require(
        sha(SOURCE_DIR / 'visual-graph.json')
        == read(PACKET / 'tie-source-evidence.json')['graph_sha256'],
        'Graph binding mismatch',
    )
    source_score = converter.parse(str(OLD / 'owner-associated-source.musicxml'))
    endpoint_pair(source_score, 'B-3')
    rows = read(GT02 / 'note-correspondence-diagnostic.json')['events']['Bb']
    registration = read(GT02 / 'measure-registration.json')['pages']['Bb']
    inv = system_inventory(source_score, graph, rows, registration)
    require(sum(len(m['events']) for m in inv['measures']) == 13, 'Recognized count mismatch')
    dump(out / 'source-event-inventory.json', inv)
    source = Image.open(SOURCE)
    require(
        source.crop(VIEW).tobytes() == Image.open(out / 'original-second-system.png').tobytes(),
        'Source crop differs',
    )
    review = Image.new('RGB', (2350, 1500), 'white')
    draw = ImageDraw.Draw(review)
    f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 22)
    draw.text(
        (20, 10),
        'SOURCE-ONLY OWNER REVIEW - ORIGINAL Bb PAGE2 / SYSTEM2 - native crop pixels',
        font=f,
        fill='black',
    )
    review.paste(source.crop(VIEW), (20, 55))
    crops = []
    y = 430
    for m in inv['measures']:
        n = m['printed_measure']
        left, right = m['physical_candidate_bounds']
        box = (max(130, int(left) - 10), 700, min(2430, int(right) + 10), 1030)
        native = source.crop(box)
        name = f'source-measure-{n}.png'
        native.save(out / name)
        if n in (5, 7):
            x = 20
        else:
            x = 650 if n == 6 else 650
        yy = y if n in (5, 6) else y + 400
        draw.text((x, yy), f'Printed measure {n} / native source pixels', font=f, fill='black')
        review.paste(native, (x, yy + 35))
        crops.append({'measure': n, 'file': name, 'bbox': box, 'sha256': sha(out / name)})
    review.save(out / 'source-second-system-review-sheet.png')
    checklist = {
        'status': 'PENDING_OWNER_REVIEW',
        'source_sha256': source_hash,
        'review_sheet_sha256': sha(out / 'source-second-system-review-sheet.png'),
        'scope': 'No duplicate request for confirmed m4->m5 endpoint; all candidates below need source review',
        'OMR_RECOGNIZED': [
            {
                'measure': m['printed_measure'],
                'events': m['events'],
                'harmonies': m['recognized_harmonies'],
            }
            for m in inv['measures']
        ],
        'AGENT_VISUAL_CANDIDATE': CANDIDATES,
        'OWNER_VERIFIED_SOURCE': ['m5 Bb3 whole note STOP, linked to m4'],
        'UNVERIFIED': [
            'All m6/m7/m8 events',
            'Gm/Bb/D/Eb chord identity and placement',
            'Both lyric strings and exact tied-note/extender associations',
            'Ending1/final repeat and apparent OMR articulation/fermata classifications',
        ],
        'questions': [
            'Confirm/correct m6 recognized rhythm/pitches, m7 Bb3 whole-note STOP and m8 whole rest; report extra or missing musical content.',
            'Confirm/correct source chord candidates m5 Gm, m6 Bb/D, m7 Eb; do not infer a new m8 chord.',
            'Confirm/correct upper 내/가/있/길/원/(hold)/하/네 and lower 주/의/놀/라/운/(hold)/손/길; m6 onsets1.5,1.75,2,2.5,2.75,3(hold),3.25,3.75 and m7 held continuation are candidates only.',
            'Are the OMR TENUTO/FERMATA objects actually lyric dashes/syllables or musical marks? Confirm ending1 and final backward repeat.',
        ],
        'actual_new_owner_answers': None,
        'independent_ground_truth': False,
        'crop_binding': crops,
    }
    dump(out / 'source-review-checklist.json', checklist)
    unsupported = {
        'unrendered_events': [
            {'event_id': 'p1:m7:r0', 'measure': 8, 'reason': 'WHOLE_REST_NOT_VALIDATED'}
        ],
        'symbols': [
            {
                'id': s['id'],
                'shape': s['shape'],
                'bbox': s['geometry']['bbox'],
                'reason': 'SOURCE_INTERPRETATION_AND_RENDER_CONTRACT_UNVERIFIED',
                'rendered': False,
            }
            for s in inv['potential_attachments_and_structures']
        ],
        'chords': {
            'candidate': 3,
            'recognized': 1,
            'unrecognized_candidate': 2,
            'rendered': 0,
            'owner_verified': 0,
        },
        'lyrics': {'rows': 2, 'OMR_lyric_tokens': 0, 'owner_confirmed': 0, 'rendered': 0},
        'warning': 'Underlying note display does not complete an atomic notation group with unresolved attached support; no edit ownership authorized',
    }
    dump(out / 'unsupported-elements.json', unsupported)
    dump(
        out / 'source-audit-freeze.json',
        {
            'files': file_hashes(out),
            'protocol_sha256': sha(PROTOCOL),
            'phase': 'BEFORE_TARGET_PREDICTIONS',
        },
    )
    all_reports = []
    guards = {}
    images = []
    for target, shift in [('A', -1), ('G', -3)]:
        score = copy.deepcopy(source_score)
        summary = transpose_score(score, shift, 'key')
        mem = validate(source_score, score, shift, 'key', summary).to_dict()
        frozen = converter.parse(str(OLD / f'{target}-transposed.musicxml'))
        disk = validate(source_score, frozen, shift, 'key').to_dict()
        require(
            mem['ok']
            and disk['ok']
            and full_lyric_signature(source_score) == full_lyric_signature(frozen),
            'Full guard/lyric preservation failed',
        )
        guards[target] = {'in_memory': mem, 'frozen_serialized': disk}
        parts, report = render_music(inv, source_score, score, target, graph)
        # The imported confirmed endpoint is not rerasterized, and new material is separately colored.
        black = Image.open(PRIOR / f'{target}-two-system-alpha.png').copy()
        scaffold_mask = scaffold(
            SIZE,
            inv['staff'],
            [639, 1598, 1961, 2397],
            {2397: graph['symbols']['sheet#1:26']['geometry']['bbox']},
        )
        black = union([black, scaffold_mask])
        provisional = union(
            [
                m
                for n, m in parts.items()
                if not n.startswith('p1:m4:') and n != 'confirmed-incoming-tie'
            ]
        )
        # Bound all new ink away from existing confirmed material; staff crossings are intentional.
        inherited = Image.open(PRIOR / f'{target}-two-system-alpha.png')
        contacts = int(
            np.count_nonzero((np.asarray(provisional) > 0) & (np.asarray(inherited) > 0))
        )
        report['new_music_to_confirmed_context_contacts'] = contacts
        report['frozen_m5_head_byte_identical'] = (
            parts['p1:m4:n0:head'].tobytes()
            == Image.open(PRIOR / f'{target}-whole-note-alpha.png').tobytes()
        )
        report['frozen_incoming_tie_byte_identical'] = (
            parts['confirmed-incoming-tie'].tobytes()
            == Image.open(PRIOR / f'{target}-incoming-tie-alpha.png').tobytes()
        )
        require(
            report['frozen_m5_head_byte_identical']
            and report['frozen_incoming_tie_byte_identical'],
            'Confirmed evidence changed',
        )
        near = []
        for a, b in itertools.combinations(parts, 2):
            if owners_different(a, b, report):
                aa = parts[a]
                bb = parts[b]
                ba = aa.getbbox()
                bc = bb.getbbox()
                # Measure nearby unrelated components only; report the tested subset explicitly.
                if max(ba[0] - bc[2], bc[0] - ba[2], ba[1] - bc[3], bc[1] - ba[3]) > 40:
                    continue
                dist = ink_distance(bb)
                near.append(float(dist[np.asarray(aa) > 0].min()))
        report['minimum_nearby_distinct_component_center_distance_px'] = min(near) if near else None
        envelope = np.zeros((SIZE[1], SIZE[0]), bool)
        pair_count = 0
        mm = np.asarray(union(list(parts.values()))) > 0
        for region in graph['text_protected_regions']:
            box = region.get('bbox')
            if box is None:
                continue
            l, t, r, b = map(int, box)
            l = max(0, l)
            r = min(SIZE[0], r)
            t = max(0, t)
            b = min(SIZE[1], b)
            if l >= r or t >= b:
                continue
            if mm[t:b, l:r].any():
                pair_count += 1
                envelope[t:b, l:r] |= mm[t:b, l:r]
        report['source_protected_envelope_diagnostic'] = {
            'pairs': pair_count,
            'unique_pixels': int(envelope.sum()),
            'actual_text_ink_contact': 'UNKNOWN_NOT_COMPOSITION_AUTHORIZATION',
        }
        report['VISUAL_QUALITY'] = 'PENDING_POST_FREEZE_INSPECTION'
        report['unexpected_contacts_invalidate_complete_claim'] = bool(
            report['unexpected_intersections']
            or report['missing_connections']
            or report['clipping']
            or contacts
        )
        canvas = paint(black, provisional)
        image = panel(
            canvas.crop(VIEW),
            f'{target} major / 12 of13 recognized events displayed; only m5 is owner-verified',
        )
        image.save(out / f'predicted-{target.lower()}-second-system.png')
        images.append(image)
        preview = panel(
            canvas.crop((130, 310, 2430, 1030)),
            f'{target} first+second SYSTEM DIAGNOSTIC PREVIEW / second-system source unverified',
        )
        preview.save(out / f'{target}-first-plus-second-provisional-preview.png')
        provisional.save(out / f'{target}-provisional-music-alpha.png')
        union(list(parts.values())).save(out / f'{target}-second-system-music-alpha.png')
        for name, mask in parts.items():
            mask.save(out / f'{target}-{name.replace(":","_")}-alpha.png')
        all_reports.append(report)
    sheet = Image.new('RGB', (images[0].width, sum(i.height for i in images) + 485), 'white')
    original = panel(source.crop(VIEW), 'Unchanged original Bb source; source-only comparison')
    sheet.paste(original, (0, 0))
    y = original.height
    for image in images:
        sheet.paste(image, (0, y))
        y += image.height
    sheet.save(out / 'second-system-comparison.png')
    dump(out / 'rendering-validation.json', all_reports)
    dump(out / 'semantic-integrity.json', guards)
    require(
        sha(SOURCE) == source_hash and all(file_hashes(Path(p)) == h for p, h in histories.items()),
        'Historical/source change',
    )
    dump(
        out / 'validation-summary.json',
        {
            'SOURCE_RECOGNITION_COMPLETENESS': 'UNVERIFIED_WITH_OBSERVED_OMR_OMISSIONS',
            'OWNER_VERIFICATION_COVERAGE': '1/13 events; no new chords/lyrics verified',
            'RENDERING_COMPLETENESS': 'INCOMPLETE',
            'VISUAL_QUALITY': 'PENDING_POST_FREEZE_INSPECTION',
            'recognized_events': 13,
            'displayed_events': 12,
            'owner_verified_rendered': 1,
            'provisional_rendered': 11,
            'unrendered_events': 1,
            'status': 'SECOND_SYSTEM_INCOMPLETE',
            'new_owner_labels': 0,
            'historical_files_unchanged': True,
            'full_V3_guard': 'PASS_BOTH_TARGETS',
            'preview_scope': 'DIAGNOSTIC_ONLY / provisional second system / not a complete score',
        },
    )
    dump(
        out / 'input-freeze.json',
        {
            'history_files': histories,
            'source_sha256': source_hash,
            'graph_sha256': sha(SOURCE_DIR / 'visual-graph.json'),
            'source_musicxml_sha256': sha(OLD / 'owner-associated-source.musicxml'),
            'protocol_sha256': sha(PROTOCOL),
            'producer_sha256': sha(Path(__file__)),
            'owner_record_sha256': sha(ORIGINAL_RECORD),
        },
    )
    dump(
        out / 'prediction-freeze.json',
        {'files': file_hashes(out), 'phase': 'BEFORE_AGENT_VISUAL_INSPECTION_NO_REFERENCE_ACCESS'},
    )


def owners_different(a, b, report):
    # Exclude explicitly related contact pairs and same-event head/stem/ledger components.
    if a.startswith('p1:') and b.startswith('p1:') and a.rsplit(':', 1)[0] == b.rsplit(':', 1)[0]:
        return False
    return not any({c['a'], c['b']} == {a, b} and c['intentional'] for c in report['intersections'])


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    run(p.parse_args().out)
