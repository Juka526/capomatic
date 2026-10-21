"""Bounded provisional up/down stems and source-backed beam groups, research only."""

import math
import xml.etree.ElementTree as ET
from fractions import Fraction

import numpy as np
from music21 import stream
from PIL import Image, ImageDraw

from scripts.research.gt04_visual import HEAD, REST
from scripts.research.gt05_raster_anchor import glyph
from scripts.research.gt07_flags import FLAG, flag_mask
from scripts.research.gt11_complete_measure import events_of, require
from scripts.research.gt13a2_provisional import EIGHTH_REST, linked, curve_mask, translated_curve
from scripts.research.gt13a4_header import font_units
from scripts.research.gt13a5_lyric_layout import contacts
from scripts.research.gt13a6_tie_rendering import calibrated_whole_head
from scripts.research.gt14a_notation import whole_rest
from scripts.research.gt15_notation import font_contract, half_symbol
from scripts.research.paired_ground_truth_01 import line_y


def y_for(staff, x, pitch):
    return line_y(staff['lines'][2], x) + (35 - pitch.diatonicNoteNum) * staff['interline'] / 2


def down_flag(size, font, tip, units, scale):
    """Vertical reflection of the validated single-flag bitmap; right-side stem attachment."""
    up, meta = flag_mask(size, font, (100, 100), units, scale)
    b = up.getbbox()
    tile = up.crop(b).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    ay = tile.height - 1 - meta['flag_attachment_local'][1]
    xy = (round(tip[0]), round(tip[1]) - ay)
    require(
        0 <= xy[0]
        and 0 <= xy[1]
        and xy[0] + tile.width <= size[0]
        and xy[1] + tile.height <= size[1],
        'Down-flag clipping',
    )
    p = Image.new('L', size)
    p.paste(tile, xy)
    require(p.getpixel((round(tip[0]), round(tip[1]))) > 0, 'Detached down flag')
    return p, {
        'method': 'VERTICAL_REFLECTION_VALIDATED_FLAG1_BITMAP',
        'requested_tip': tip,
        'attachment_residual': [round(tip[i]) - tip[i] for i in (0, 1)],
        'flag_count': 1,
    }


def beam_groups(nodes, symbols, relations, inter):
    """Assign beam levels from the persisted group, then preserve source slope/separation."""
    beams = {
        s['id']: s
        for s in symbols.values()
        if s['kind'] in ('beam', 'beam-hook')
        and any(x in nodes for x in linked(relations, 'beam-stem', s['id']))
    }
    memberships = {bid: set(linked(relations, 'beam-stem', bid)) for bid in beams}
    for bid, members in memberships.items():
        require(members and members <= nodes.keys(), 'Missing beam stem')
    todo = set().union(*memberships.values()) if memberships else set()
    results = []
    tips = {}
    allowed = set()
    while todo:
        group = {next(iter(todo))}
        while True:
            extended = group | set().union(*(v for v in memberships.values() if v & group))
            if extended == group:
                break
            group = extended
        todo -= group
        signs = {nodes[s]['sign'] for s in group}
        require(len(signs) == 1, 'Mixed stem-direction group unsupported')
        sign = signs.pop()
        candidates = [
            beams[bid]
            for bid, m in memberships.items()
            if m == group and beams[bid]['kind'] == 'beam'
        ]
        require(candidates, 'Missing full primary beam')
        primary = min(candidates, key=lambda b: sign * sum(p[1] for p in b['geometry']['line']) / 2)
        src = primary['geometry']['line']
        require(len(src) == 2 and src[1][0] > src[0][0], 'Invalid beam median')
        slope = (src[1][1] - src[0][1]) / (src[1][0] - src[0][0])
        ordered = sorted(group, key=lambda s: nodes[s]['x'])
        x0 = nodes[ordered[0]]['x']
        require(
            [nodes[s]['event']['beams'][0]['type'] for s in ordered]
            == ['start'] + ['continue'] * (len(ordered) - 2) + ['stop'],
            'Primary semantic order mismatch',
        )
        base_values = [
            nodes[s]['y'] - sign * 3.5 * inter - slope * (nodes[s]['x'] - x0) for s in group
        ]
        y0 = min(base_values) if sign == 1 else max(base_values)
        for s in group:
            tips[s] = y0 + slope * (nodes[s]['x'] - x0)
        for bid, members in memberships.items():
            if not members <= group:
                continue
            b = beams[bid]
            line = b['geometry']['line']
            thick = round(b['geometry']['thickness'])
            require(
                len(line) == 2 and line[1][0] > line[0][0] and 0 < thick < inter,
                'Unsupported beam geometry',
            )
            cx = sum(p[0] for p in line) / 2
            separation = sum(p[1] for p in line) / 2 - (src[0][1] + slope * (cx - src[0][0]))
            level = 1 if bid == primary['id'] else 2
            require(
                level == 1 or 0.5 * inter <= sign * separation <= inter,
                'Secondary level separation mismatch',
            )
            bs = sorted(members, key=lambda s: nodes[s]['x'])
            for s in bs:
                require(
                    any(v['number'] == level for v in nodes[s]['event']['beams']),
                    'Missing semantic beam level',
                )
            if b['kind'] == 'beam-hook':
                require(len(bs) == 1, 'Multiple-owner hook')
                bm = next(v for v in nodes[bs[0]]['event']['beams'] if v['number'] == level)
                require(
                    bm['type'] == 'partial' and bm['direction'] in ('left', 'right'),
                    'Unknown hook direction',
                )
                start = nodes[bs[0]]['x']
                end = start + (1 if bm['direction'] == 'right' else -1) * (line[1][0] - line[0][0])
                lo, hi = sorted((start, end))
                require(
                    nodes[ordered[0]]['x'] <= lo < hi <= nodes[ordered[-1]]['x'],
                    'Hook escapes primary',
                )
            else:
                lo, hi = nodes[bs[0]]['x'], nodes[bs[-1]]['x']
            require(lo < hi, 'Degenerate beam')
            results.append(
                {
                    'id': bid,
                    'members': bs,
                    'level': level,
                    'sign': sign,
                    'kind': b['kind'],
                    'source_slope': slope,
                    'line': [
                        [lo, y0 + slope * (lo - x0) + separation],
                        [hi, y0 + slope * (hi - x0) + separation],
                    ],
                    'thickness': thick,
                }
            )
    for s, n in nodes.items():
        actual = [bid for bid, m in memberships.items() if s in m]
        require(len(actual) == len(n['event']['beams']), 'Unrepresented/missing semantic beam')
        if actual:
            require(
                Fraction(n['event']['duration']) in (Fraction(1, 2), Fraction(1, 4)),
                'Unsupported beamed rhythm',
            )
    return results, tips, allowed


def render(inv, score, target, graph, size, all_events):
    st = inv['staff']
    inter = st['interline']
    tt, font, scale = font_contract(inter)
    mm = list(score.parts[0].getElementsByClass(stream.Measure))
    relations = graph['relations']
    parts = {}
    owners = {}
    nodes = {}
    metrics = []
    heads = {}
    allowed = set()
    gaps = []

    def add(name, p, owner):
        require(name not in parts and p.getbbox(), 'Duplicate/empty component')
        b = p.getbbox()
        require(0 < b[0] < b[2] < size[0] and 0 < b[1] < b[3] < size[1], 'Canvas clipping')
        parts[name] = p
        owners[name] = owner

    for m in inv['measures']:
        ns = events_of(mm[m['printed_measure'] - 1])
        require(len(ns) == len(m['events']), 'Event inventory mismatch')
        for e, n in zip(m['events'], ns):
            b = e['source_bbox']
            x = (b[0] + b[2]) / 2
            dur = Fraction(e['duration'])
            require(dur == Fraction(n.quarterLength), 'Duration changed')
            if n.isRest:
                if dur == 4:
                    require(
                        n.fullMeasure is True
                        and graph['symbols'][e['symbol_id']]['shape'] == 'WHOLE_REST',
                        'Unverified full rest lineage',
                    )
                    p, info = whole_rest(size, st, x)
                elif dur == 2:
                    require(
                        graph['symbols'][e['symbol_id']]['shape'] == 'HALF_REST',
                        'Half-rest lineage mismatch',
                    )
                    p, info = half_symbol(size, inter, (x, (b[1] + b[3]) / 2), rest=True)
                else:
                    require(dur in (1, Fraction(1, 2)), 'Unsupported rest')
                    char = REST if dur == 1 else EIGHTH_REST
                    p, info = glyph(
                        size, font, char, (x, (b[1] + b[3]) / 2), font_units(tt, char), scale
                    )
                add(e['id'] + ':rest', p, e['id'])
            else:
                require(
                    not n.duration.tuplets and not n.duration.isGrace, 'Tuplet/grace unsupported'
                )
                require(
                    dur in (4, 3, 2, 1, Fraction(1, 2), Fraction(1, 4)), 'Unsupported note duration'
                )
                expected = ({'F': 1, 'C': 1, 'G': 1} if target == 'A' else {'F': 1}).get(
                    n.pitch.step, 0
                )
                require(
                    (n.pitch.accidental.alter if n.pitch.accidental else 0) == expected,
                    'Explicit non-key accidental unsupported',
                )
                y = y_for(st, x, n.pitch)
                if dur == 4:
                    require(
                        not e['stem_ids']
                        and graph['symbols'][e['symbol_id']]['shape'] == 'WHOLE_NOTE',
                        'Whole-note lineage mismatch',
                    )
                    p, info = calibrated_whole_head(size, st, x, n.pitch.nameWithOctave)
                elif dur in (2, 3):
                    require(
                        graph['symbols'][e['symbol_id']]['shape'] == 'NOTEHEAD_VOID',
                        'Half-note glyph lineage mismatch',
                    )
                    require(
                        (dur == 3 and n.duration.type == 'half' and n.duration.dots == 1)
                        or (dur == 2 and not n.duration.dots),
                        'Half/dot duration mismatch',
                    )
                    p, info = half_symbol(size, inter, (x, y))
                else:
                    p, info = glyph(size, font, HEAD, (x, y), font_units(tt, HEAD), scale)
                add(e['id'] + ':head', p, e['id'])
                require(max(map(abs, info['anchor_residual'])) <= 0.5, 'Notehead residual exceeded')
                heads[e['symbol_id']] = {
                    'event': e,
                    'pitch': n.pitch.nameWithOctave,
                    'y': y,
                    'bbox': p.getbbox(),
                }
                pos = 35 - n.pitch.diatonicNoteNum
                led = Image.new('L', size)
                d = ImageDraw.Draw(led)
                for pp in list(range(6, pos + 1, 2)) + list(range(-6, pos - 1, -2)):
                    yy = line_y(st['lines'][2], x) + pp * inter / 2
                    d.line([(p.getbbox()[0] - 4, yy), (p.getbbox()[2] + 3, yy)], fill=255, width=2)
                if led.getbbox():
                    add(e['id'] + ':ledger', led, e['id'])
                if dur == 3:
                    dots = linked(relations, 'augmentation', e['symbol_id'])
                    # Audiveris augmentation relations target the head-chord in some stages.
                    if not dots:
                        chords = linked(relations, 'contains', e['symbol_id'])
                        dots = [
                            t
                            for c in chords
                            for t in linked(relations, 'augmentation', c)
                            if graph['symbols'].get(t, {}).get('kind') == 'augmentation-dot'
                        ]
                    require(len(dots) == 1, 'Dotted duration lacks exact augmentation lineage')
                    dot = Image.new('L', size)
                    xx = p.getbbox()[2] + inter * 0.45
                    yy = y - inter / 2 if pos % 2 == 0 else y
                    ImageDraw.Draw(dot).ellipse(
                        (round(xx) - 3, round(yy) - 3, round(xx) + 3, round(yy) + 3), fill=255
                    )
                    add(e['id'] + ':dot', dot, e['id'])
                if dur != 4:
                    require(
                        len(e['stem_ids']) == 1 and e['stem_direction'] in ('up', 'down'),
                        'Unsupported stem lineage',
                    )
                    sid = e['stem_ids'][0]
                    sign = 1 if e['stem_direction'] == 'up' else -1
                    rel = [
                        r
                        for r in relations
                        if r['kind'] == 'head-stem'
                        and r['source'] == e['symbol_id']
                        and r['target'] == sid
                    ]
                    require(
                        len(rel) == 1
                        and dict(rel[0]['attributes']).get('head-side')
                        == ('RIGHT' if sign == 1 else 'LEFT'),
                        'Stem side mismatch',
                    )
                    pixels = np.argwhere(np.asarray(p) > 0)
                    edge = int(pixels[:, 1].max() - 1 if sign == 1 else pixels[:, 1].min() + 1)
                    attach = float(np.median(pixels[pixels[:, 1] == edge, 0]))
                    line = graph['symbols'][sid]['geometry']['line']
                    require(len(line) == 2, 'Missing stem line')
                    length = max(
                        3.5 * inter,
                        abs(
                            (b[1] + b[3]) / 2
                            - (min(q[1] for q in line) if sign == 1 else max(q[1] for q in line))
                        ),
                    )
                    nodes[sid] = {
                        'x': edge,
                        'y': y,
                        'attachment': attach,
                        'tip': y - sign * length,
                        'sign': sign,
                        'event': e,
                    }
                info.update(
                    target_staff_coordinate=[x, y],
                    target_pitch=n.pitch.nameWithOctave,
                    physical_source_center=e['physical_source_center'],
                )
            metrics.append(
                {
                    'event_id': e['id'],
                    'measure': m['printed_measure'],
                    'kind': e['kind'],
                    'duration': e['duration'],
                    **info,
                }
            )
    specs, tips, _ = beam_groups(nodes, graph['symbols'], relations, inter)
    for sid, tip in tips.items():
        nodes[sid]['tip'] = tip
    for sid, node in nodes.items():
        e = node['event']
        flags = linked(relations, 'flag-stem', sid)
        if flags:
            require(
                len(flags) == 1 and not e['beams'] and e['duration'] == '1/2',
                'Unsupported flag count',
            )
            expected = 'FLAG_1' if node['sign'] == 1 else 'FLAG_1_DOWN'
            require(graph['symbols'][flags[0]]['shape'] == expected, 'Flag direction mismatch')
            # Down flags extend back across the head: derive stem clearance from bitmap span.
            if node['sign'] == -1:
                probe, _ = down_flag(size, font, (100, 100), font_units(tt, FLAG), scale)
                span = 100 - probe.getbbox()[1]
                head_bottom = parts[e['id'] + ':head'].getbbox()[3] - 1
                node['tip'] = max(node['tip'], head_bottom + span + inter / 2)
            tip = (node['x'], round(node['tip']))
            node['tip'] = tip[1]
            if node['sign'] == 1:
                p, fi = flag_mask(size, font, tip, font_units(tt, FLAG), scale)
            else:
                p, fi = down_flag(size, font, tip, font_units(tt, FLAG), scale)
            add(e['id'] + ':flag', p, e['id'])
        elif not e['beams']:
            require(Fraction(e['duration']) >= 1, 'Missing required flag')
        p = Image.new('L', size)
        ImageDraw.Draw(p).line(
            [(node['x'], node['attachment']), (node['x'], node['tip'])], fill=255, width=2
        )
        add(e['id'] + ':stem', p, e['id'])
    for spec in specs:
        p = Image.new('L', size)
        ImageDraw.Draw(p).line([tuple(q) for q in spec['line']], fill=255, width=spec['thickness'])
        add(spec['id'], p, spec['id'])
        for s in spec['members']:
            allowed.add(frozenset((spec['id'], nodes[s]['event']['id'] + ':stem')))
    curves = []
    for c in graph['symbols'].values():
        if c['system'] != st['system'] or c['kind'] != 'slur':
            continue
        raw = ET.fromstring(c['source_xml'])
        rs = [r for r in relations if r['source'] == c['id'] and r['kind'] == 'slur-head']
        if raw.get('tie') != 'true' or not rs:
            gaps.append({'id': c['id'], 'reason': 'NON_TIE_OR_NO_ENDPOINT_LINEAGE'})
            continue
        # A reciprocal extension is a pair of distinct segments, never an inter-system bridge.
        extension = raw.get('right-extension') or raw.get('left-extension')
        if extension:
            other = graph['all_symbols'].get('sheet#1:' + extension)
            require(other is not None, 'Missing extension object')
            back = ET.fromstring(other['source_xml'])
            require(
                (back.get('left-extension') or back.get('right-extension')) == c['source_id'],
                'Nonreciprocal tie extension',
            )
            ors = [r for r in relations if r['source'] == other['id'] and r['kind'] == 'slur-head']
            require(len(rs) == len(ors) == 1, 'Ambiguous cross-system endpoints')
            a = all_events[rs[0]['target']]
            b = all_events[ors[0]['target']]
            require(
                a['pitch'] == b['pitch'] and {a['tie'], b['tie']} == {'start', 'stop'},
                'Cross-system pitch/role mismatch',
            )
        elif len(rs) != 2:
            gaps.append({'id': c['id'], 'reason': 'INCOMPLETE_LOCAL_TIE'})
            continue
        if not extension and len({heads[r['target']]['pitch'] for r in rs}) != 1:
            gaps.append({'id': c['id'], 'reason': 'UNEQUAL_TARGET_PITCH'})
            continue
        deltas = []
        for r in sorted(rs, key=lambda r: dict(r['attributes']).get('side', '')):
            h = heads[r['target']]
            e = h['event']
            dy = h['y'] - (e['source_bbox'][1] + e['source_bbox'][3]) / 2
            deltas.append(dy)
        cp = translated_curve(c['geometry']['curve'], deltas[0], deltas[-1])
        add(c['id'], curve_mask(size, cp), c['id'])
        curves.append(
            {
                'id': c['id'],
                'extension': extension,
                'curve': cp,
                'endpoint_ids': [r['target'] for r in rs],
                'endpoint_events': [
                    {
                        k: all_events[r['target']].get(k)
                        for k in ('id', 'printed_measure', 'onset', 'pitch', 'tie')
                    }
                    for r in rs
                ],
                'classification': 'OMR_PROVISIONAL',
            }
        )
    connections = []
    for sid, node in nodes.items():
        name = node['event']['id'] + ':stem'
        for neighbor in (
            [node['event']['id'] + ':head']
            + [s['id'] for s in specs if sid in s['members']]
            + ([node['event']['id'] + ':flag'] if node['event']['id'] + ':flag' in parts else [])
        ):
            b = parts[name].getbbox()
            q = parts[neighbor].getbbox()
            box = (max(b[0], q[0]), max(b[1], q[1]), min(b[2], q[2]), min(b[3], q[3]))
            count = (
                int(
                    np.count_nonzero(
                        (np.asarray(parts[name].crop(box)) > 0)
                        & (np.asarray(parts[neighbor].crop(box)) > 0)
                    )
                )
                if box[0] < box[2] and box[1] < box[3]
                else 0
            )
            connections.append({'a': name, 'b': neighbor, 'contact_pixels': count})
    unexpected = []
    for c in contacts(parts):
        pair = frozenset((c['a'].split(':')[-1], c['b'].split(':')[-1]))
        intentional = owners[c['a']] == owners[c['b']] and pair in [
            frozenset(('head', 'stem')),
            frozenset(('head', 'ledger')),
            frozenset(('stem', 'ledger')),
            frozenset(('stem', 'flag')),
        ]
        if not intentional and frozenset((c['a'], c['b'])) not in allowed:
            unexpected.append(c)
    return parts, {
        'events': metrics,
        'beams': specs,
        'curves': curves,
        'connections': connections,
        'missing_connections': [c for c in connections if not c['contact_pixels']],
        'unexpected_contacts': unexpected,
        'rendering_gaps': gaps,
        'max_head_residual': max(
            max(map(abs, e['anchor_residual'])) for e in metrics if e['kind'] == 'NOTE'
        ),
        'classification': 'OMR_PROVISIONAL',
        'clipping': [],
    }
