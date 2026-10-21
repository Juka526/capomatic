"""New glyph rendering of nine systems, bounded optical refinements, no source ink edits."""

import copy
from pathlib import Path
import gc
import math
import xml.etree.ElementTree as ET

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from music21 import harmony, stream

from backend.omr_v3.chords import chord_text
from scripts.research.gt11_complete_measure import FONT, require, events_of
from scripts.research.gt12_render_context import KOREAN_FONT, text_mask, canonical_box
from scripts.research.gt13a2_provisional import curve_mask, translated_curve, ink_distance
from scripts.research.gt13a4_header import header
from scripts.research.gt13a5_lyric_layout import contacts
from scripts.research.gt16c_optical_engraving import beam_candidate, beam_metrics, piece
from scripts.research.gt17b_full_score import (
    localize,
    context,
    combine,
    shift,
    export_pdf,
    expected_tie_barline,
)
from scripts.research.gt17b_notation import render
from scripts.research.gt17b_owner_integration import CURVES, permitted_curve_contact, BASE
from scripts.research.gt17c_accuracy_audit import OWNER
from scripts.research.gt15b_confirmed_third_system import section_label
from scripts.research.paired_ground_truth_01 import dump, sha
from scripts.research.gt11_complete_measure import read
from scripts.research.gt12_render_context import ink_bbox
from scripts.research.gt17b_owner_integration import SOURCE_DIR

SIZE = (2520, 3564)
WARNING = 'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING'


def smooth_curve(size, points, scale=4):
    require(scale == 4 and len(points) == 4, 'Curve sampling contract')
    box = (
        math.floor(min(p[0] for p in points)) - 3,
        math.floor(min(p[1] for p in points)) - 3,
        math.ceil(max(p[0] for p in points)) + 4,
        math.ceil(max(p[1] for p in points)) + 4,
    )
    require(
        0 <= box[0] < box[2] <= size[0] and 0 <= box[1] < box[3] <= size[1],
        'Curve viewport clipping',
    )
    tile = Image.new('L', ((box[2] - box[0]) * scale, (box[3] - box[1]) * scale))
    path = []
    for t in np.linspace(0, 1, 201):
        q = [
            (1 - t) ** 3 * points[0][k]
            + 3 * (1 - t) ** 2 * t * points[1][k]
            + 3 * (1 - t) * t * t * points[2][k]
            + t**3 * points[3][k]
            for k in (0, 1)
        ]
        path.append(tuple((q[k] - box[k] + 0.5) * scale - 0.5 for k in (0, 1)))
    ImageDraw.Draw(tile).line(path, fill=255, width=2 * scale)
    tile = tile.resize((box[2] - box[0], box[3] - box[1]), Image.Resampling.BOX)
    out = Image.new('L', size)
    out.paste(tile, (box[0], box[1]))
    return out


def overlap(a, b):
    box = (
        max(a.getbbox()[0], b.getbbox()[0]),
        max(a.getbbox()[1], b.getbbox()[1]),
        min(a.getbbox()[2], b.getbbox()[2]),
        min(a.getbbox()[3], b.getbbox()[3]),
    )
    return (
        0
        if box[0] >= box[2] or box[1] >= box[3]
        else int(np.count_nonzero((np.asarray(a.crop(box)) > 0) & (np.asarray(b.crop(box)) > 0)))
    )


def refine(parts, metrics, size):
    baseline = {frozenset((h['a'], h['b'])) for h in contacts(parts)}
    report = []
    for spec in metrics['beams']:
        cand = beam_candidate(spec, 4)
        p = Image.new('L', size)
        p.paste(cand.tile, cand.box[:2])

        links = [c for c in metrics['connections'] if c['b'] == spec['id']]
        connected = all(overlap(p, parts[c['a']]) > 0 for c in links) and bool(links)
        unexpected = [
            k
            for k, q in parts.items()
            if k != spec['id'] and overlap(p, q) and frozenset((k, spec['id'])) not in baseline
        ]
        approved = connected and not unexpected
        old = piece(spec['id'], parts[spec['id']], 0, 0, 'BEAM')
        report.append(
            {
                'id': spec['id'],
                'kind': 'beam',
                'accepted_4x': approved,
                'before': beam_metrics(old, spec),
                'after_candidate': beam_metrics(cand, spec),
                'endpoints_unchanged': True,
                'unexpected_candidate_contacts': unexpected,
                'stem_connections_preserved': connected,
            }
        )
        if approved:
            parts[spec['id']] = p
    for spec in metrics['curves']:
        name = spec['id']
        p = smooth_curve(size, spec['curve'])
        unexpected = [
            k
            for k, q in parts.items()
            if k != name and overlap(p, q) and frozenset((k, name)) not in baseline
        ]
        connected = cv2.connectedComponents((np.asarray(p) > 0).astype('uint8'))[0] == 2
        accept = connected and not unexpected
        report.append(
            {
                'id': name,
                'kind': 'curve',
                'accepted_4x': accept,
                'control_points_unchanged': True,
                'unexpected_candidate_contacts': unexpected,
                'single_component': connected,
            }
        )
        if accept:
            parts[name] = p
    require(
        not any(not overlap(parts[c['a']], parts[c['b']]) for c in metrics['connections']),
        'Refinement broke attachment',
    )
    return report


def extra_context(sys, graph, size, top, target):
    parts, structure, hm = context(sys, graph, size, top, target)
    if sys['system'] == 1:
        inv, _, _ = localize(sys, graph)
        hp, hm = header(size, inv['staff'], target, FONT)
        parts = hp
        structure = {k: p for k, p in structure.items() if k == 'staff' or p.getbbox()[0] > 380}
    ending_numbers = {'5201': '1.', '5193': '2.', '5203': '1.', '5195': '2.'}
    for sid, number in ending_numbers.items():
        obj = graph['symbols']['sheet#1:' + sid]
        if obj['system'] != sys['staff']['system']:
            continue
        raw = ET.fromstring(obj['source_xml'])
        p = Image.new('L', size)
        draw = ImageDraw.Draw(p)
        for name in ['left-leg', 'line', 'right-leg']:
            a = raw.find(name)
            if a is not None:
                draw.line(
                    [
                        (float(a.find(q).get('x')), float(a.find(q).get('y')) - top)
                        for q in ['p1', 'p2']
                    ],
                    fill=255,
                    width=2,
                )
        parts['ending-' + sid] = p
        b = obj['geometry']['bbox']
        parts['ending-number-' + sid], _ = text_mask(
            size, ImageFont.truetype(str(FONT), 40), number, left_top=(b[0] + 15, b[1] + 12 - top)
        )
    if sys['system'] == 3:
        box = graph['symbols']['sheet#1:4183']['geometry']['bbox']
        parts['Pre-Chorus'], _ = section_label(
            size, ImageFont.truetype(str(FONT), 34), 'Pre-Chorus', (box[0], box[1] - top)
        )
    return parts, structure, hm


def lyric_components(sys, inventory, score, marks, size, top):
    font = ImageFont.truetype(str(KOREAN_FONT), 44)
    desc = canonical_box(font, '주')[3] - 2 * font.size
    cy = sys['staff']['lines'][2][0][1]
    source_baselines = {
        1: read(
            '/private/tmp/capomatic-v4-gt13a4/gt13a4-final-output/aligned-lyric-validation.json'
        )[0]['baselines'],
        2: read('/private/tmp/capomatic-v4-gt14a/gt14a-output/rendering-validation.json')[0][
            'lyric_baselines'
        ],
        3: read('/private/tmp/capomatic-v4-gt15b/gt15b-final-output/rendering-validation.json')[0][
            'initial_lyric_baselines'
        ],
        4: read('/private/tmp/capomatic-v4-gt16b/gt16b-final-output/rendering-validation.json')[0][
            'initial_baselines'
        ],
        5: [1994 - desc, 2039 - desc],
    }
    baselines = [
        round(y - top)
        for y in source_baselines.get(sys['system'], [cy + 112.5 - desc, cy + 157.5 - desc])
    ]
    parts = {}
    placements = []
    ms = list(score.parts[0].getElementsByClass(stream.Measure))
    for m in sys['measures']:
        for e, n in zip(m['events'], events_of(ms[m['printed_measure'] - 1])):
            for l in n.lyrics:
                if not l.text:
                    continue
                ident = f'lyric-m{m["printed_measure"]}-r{l.number}-o{e["onset"]}'
                p, info = text_mask(
                    size,
                    font,
                    l.text,
                    center_x=e['physical_source_center'][0],
                    baseline=baselines[l.number - 1],
                )
                parts[ident] = p
                placements.append(
                    {
                        'id': ident,
                        'measure': m['printed_measure'],
                        'row': l.number,
                        'text': l.text,
                        'event_id': e['id'],
                        'onset': e['onset'],
                        'horizontal_anchor': e['physical_source_center'][0],
                        **info,
                    }
                )
    for mark in marks:
        if mark['measure'] not in sys['printed_measures']:
            continue
        b = mark['source_bbox']
        if b is None:
            e = next(e for e in inventory['events'] if e['id'] == mark['event_id'])
            p, _ = text_mask(
                size,
                font,
                '—',
                center_x=e['physical_source_center'][0],
                baseline=baselines[mark['row'] - 1],
            )
        else:
            p = Image.new('L', size)
            y = round((b[1] + b[3] - 1) / 2 - top)
            ImageDraw.Draw(p).line([(b[0], y), (b[2] - 1, y)], fill=255, width=2)
        parts[mark['id']] = p
        placements.append(
            {
                'id': mark['id'],
                'measure': mark['measure'],
                'row': mark['row'],
                'continuation': True,
                'source_extent_status': (
                    'PERSISTED_DIAGNOSTIC_BBOX'
                    if b
                    else 'TYPOGRAPHIC_FROM_PRIOR_APPROVED_UNDERLAY_NOT_SOURCE_PIXEL_EXTENT'
                ),
            }
        )
    return parts, placements


def place_lyrics(parts, placements, fixed, goal=6, prior_goals=None):
    require(not contacts(parts), 'Lyric baseline components overlap')
    prior_goals = prior_goals or {}
    distance = ink_distance(fixed)
    edge_distance = ink_distance(
        Image.fromarray(
            cv2.dilate((np.asarray(fixed) > 0).astype('uint8'), np.ones((3, 3), 'uint8')) * 255
        )
    )
    groups = []
    for m in sorted({p['measure'] for p in placements}):
        names = [p['id'] for p in placements if p['measure'] == m]
        group = combine([parts[n] for n in names], fixed.size)
        b = group.getbbox()
        support = np.asarray(group.crop(b)) > 0
        groups.append(
            (
                m,
                b,
                support,
                float(distance[b[1] : b[3], b[0] : b[2]][support].min()),
                max(goal, prior_goals.get(m, goal)),
            )
        )
    selected = None
    for dy in range(49):
        if all(
            b[3] + dy < fixed.height
            and float(distance[b[1] + dy : b[3] + dy, b[0] : b[2]][support].min()) >= required
            for _, b, support, _, required in groups
        ):
            selected = dy
            break
    require(selected is not None, 'No safe uniform system lyric allocation; do not lower clearance')
    dy = selected
    moved = {k: shift(p, dy) for k, p in parts.items()}
    require(not contacts(moved), 'Final lyric pair contact')
    metrics = []
    for m, b, support, before, required in groups:
        gap = float(distance[b[1] + dy : b[3] + dy, b[0] : b[2]][support].min())
        metrics.append(
            {
                'measure': m,
                'dy': dy,
                'minimum_ink_center_before_px': before,
                'minimum_ink_center_after_px': gap,
                'required_clearance_px': required,
                'pixel_edge_lower_bound_after_px': max(0, gap - math.sqrt(2)),
                'minimum_pixel_square_edge_distance_after_px': float(
                    edge_distance[b[1] + dy : b[3] + dy, b[0] : b[2]][support].min()
                ),
                'actual_contacts': 0,
                'horizontal_delta': 0,
                'row_separation_preserved': True,
                'glyph_pixels_lost': 0,
                'layout_contract': 'UNIFORM_BOTH_ROWS_AND_ALL_MEASURES_WITHIN_SYSTEM',
            }
        )
    return moved, metrics


def framed(mask, title):
    image = (
        Image.composite(
            Image.new('RGB', mask.size, 'black'), Image.new('RGB', mask.size, 'white'), mask
        )
        if mask.mode == 'L'
        else mask.copy()
    )
    out = Image.new('RGB', (image.width, image.height + 140), 'white')
    out.paste(image, (0, 140))
    d = ImageDraw.Draw(out)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 22)
    for i, t in enumerate(
        [
            WARNING,
            title,
            '169 owner-confirmed recognized events / 24 chords / 167 syllable-onset associations; not independent ground truth.',
            'Printed continuation strokes retained; m28 ancestry and complete repeat playback remain unresolved.',
            'Standalone newly typeset score; no original-pixel replacement. Source completeness UNVERIFIED.',
        ]
    ):
        d.text((15, 6 + 26 * i), t, font=font, fill='black')
    return out


def approved_chord_anchors():
    from scripts.research.gt14e_two_system_validation import GT13A3, GT14A

    result = {1: read(GT13A3 / 'rendering-report.json')[0]['new_chord']['source_bbox']}
    protocol = read(Path(__file__).resolve().parents[2] / 'docs/V4_GT12_RENDER_PROTOCOL.json')
    result[3] = ink_bbox(
        Image.open(SOURCE_DIR / 'source.png'), protocol['source_chord_measurement_window']
    )
    for directory in [
        GT14A,
        Path('/private/tmp/capomatic-v4-gt15b/gt15b-final-output'),
        Path('/private/tmp/capomatic-v4-gt16b/gt16b-final-output'),
    ]:
        for c in read(directory / 'rendering-validation.json')[0]['new_chords']:
            result[c['measure']] = c.get('source_box', c['rendered_bounds'])
    # Exact already-frozen GT17B source-derived fifth-system print anchors.
    result.update({17: [335, 1770], 18: [1383, 1770]})
    return result


def frozen_later_clearances(target, sys, inventory, evidence):
    from scripts.research.gt17b_full_score import SIZE as original_size

    top = sys['view'][1]
    size = (2520, sys['view'][3] - top)
    folder = BASE / f'{target}-system-{sys["system"]}-components'
    records = read(folder / 'component-map.json')
    text_ids = {r['id']: r['measure'] for r in inventory['lyrics'] + inventory['continuations']}
    music = Image.new('L', size)
    text = {}
    for r in records:
        require(sha(folder / r['file']) == r['sha256'], 'Frozen optical input hash mismatch')
        tile = Image.open(folder / r['file'])
        p = Image.new('L', size)
        p.paste(tile, r['bbox_local'][:2])
        if r['id'] in text_ids:
            text.setdefault(text_ids[r['id']], []).append(p)
        else:
            music = combine([music, p], size)
    for c in evidence:
        if c['system'] == sys['system']:
            path = OWNER / (target + '-' + c['case'].replace('/', '_') + '-alpha.png')
            music = combine([music, Image.open(path).crop((0, top, 2520, top + size[1]))], size)
    center = ink_distance(music)
    edge = ink_distance(
        Image.fromarray(
            cv2.dilate((np.asarray(music) > 0).astype('uint8'), np.ones((3, 3), 'uint8')) * 255
        )
    )
    rows = []
    for m, parts in text.items():
        joined = combine(parts, size)
        support = np.asarray(joined) > 0
        rows.append(
            {
                'measure': m,
                'frozen_owner_preview_center_distance_px': float(center[support].min()),
                'frozen_owner_preview_pixel_square_edge_distance_px': float(edge[support].min()),
                'frozen_owner_preview_actual_contacts': int(
                    np.count_nonzero(support & (np.asarray(music) > 0))
                ),
            }
        )
    return {
        'measurement': 'Recomputed from frozen GT17B component alpha and owner-integrated curve alpha; not regenerated old predictions',
        'component_map_sha256': sha(folder / 'component-map.json'),
        'measures': rows,
    }


def render_score(target, score, inventory, graph, marks, evidence, out):
    systems = []
    reports = []
    all_events = {e['symbol_id']: e for e in inventory['events']}
    ms = list(score.parts[0].getElementsByClass(stream.Measure))
    for sys in inventory['systems']:
        local, lg, top = localize(sys, graph)
        size = (2520, sys['view'][3] - top + 64)
        parts, metrics = render(local, score, target, lg, size, all_events)
        require(
            not metrics['unexpected_contacts'] and not metrics['missing_connections'],
            'Baseline renderer failure',
        )
        old_curves = {c['id']: parts[c['id']].copy() for c in metrics['curves']}
        refinement = refine(parts, metrics, size)
        for c in evidence:
            if c['system'] != sys['system']:
                continue
            ends = [
                next(e for e in inventory['events'] if e['id'] == eid)
                for eid in c['endpoint_event_ids']
            ]
            deltas = [
                next(e for e in metrics['events'] if e['event_id'] == end['id'])[
                    'target_staff_coordinate'
                ][1]
                + top
                - end['physical_source_center'][1]
                for end in ends
            ]
            pts = translated_curve(c['points'], *deltas)
            pts = [[x, y - top] for x, y in pts]
            base = curve_mask(size, pts)
            old_curves[c['case']] = base
            p = smooth_curve(size, pts)
            bad = [k for k, q in parts.items() if overlap(p, q)]
            require(not bad, 'New approved curve/music contact ' + str(bad))
            parts[c['case']] = p
            metrics['curves'].append(
                {
                    'id': c['case'],
                    'curve': pts,
                    'kind': c['kind'],
                    'endpoint_ids': c['endpoint_source_ids'],
                }
            )
            refinement.append(
                {
                    'id': c['case'],
                    'kind': 'curve',
                    'accepted_4x': True,
                    'control_points_unchanged': True,
                }
            )
        contextparts, scaffold, hm = extra_context(sys, graph, size, top, target)
        endpoint_metrics = []
        for c in metrics['curves']:
            for sid in c['endpoint_ids']:
                event = all_events[sid]
                h = parts[event['id'] + ':head']
                hp = np.argwhere(np.asarray(h) > 0)
                center_x = event['physical_source_center'][0]
                endpoint = min([c['curve'][0], c['curve'][-1]], key=lambda p: abs(p[0] - center_x))
                gap = float(
                    np.sqrt(((hp - np.array([endpoint[1], endpoint[0]])) ** 2).sum(axis=1)).min()
                )
                require(
                    0 < gap <= sys['staff']['interline'] * 1.5,
                    'Curve endpoint outside validated head clearance',
                )
                endpoint_metrics.append(
                    {
                        'curve_id': c['id'],
                        'source_head_id': sid,
                        'event_id': event['id'],
                        'endpoint': endpoint,
                        'minimum_endpoint_head_ink_center_distance_px': gap,
                    }
                )
        connection_metrics = [
            {**c, 'after_contact_pixels': overlap(parts[c['a']], parts[c['b']])}
            for c in metrics['connections']
        ]
        musicparts = {**parts, **contextparts}
        baseline_contacts = contacts(musicparts)
        require(
            not [h for h in baseline_contacts if h['a'] in contextparts or h['b'] in contextparts],
            'Header/music collision',
        )
        structure_hits = []
        bad = []
        for k, p in parts.items():
            for name, q in scaffold.items():
                n = overlap(p, q)
                if not n:
                    continue
                kind = graph['symbols'].get(name, {}).get('kind')
                allowed = name == 'staff' or expected_tie_barline(k, name, graph, all_events, sys)
                if k in {c['case'] for c in evidence} and kind == 'barline':
                    c = next(c for c in evidence if c['case'] == k)
                    source_measure = next(
                        m
                        for m in sys['measures']
                        if m['printed_measure'] == c['source_case']['measure']
                    )
                    allowed = permitted_curve_contact(
                        c['kind'],
                        kind,
                        c['source_case']['measure'],
                        c['source_case']['to_measure'],
                        source_measure['omr_bounds'][2],
                        graph['symbols'][name]['geometry']['bbox'],
                    )
                hit = {'a': k, 'b': name, 'pixels': n, 'intentional': allowed}
                structure_hits.append(hit)
                if not allowed:
                    bad.append(hit)
        require(not bad, 'Unexpected structural contact ' + str(bad))
        fixed = combine([*musicparts.values(), *scaffold.values()], size)
        chords = {}
        chordmetrics = []
        for m in sys['measures']:
            for ch in ms[m['printed_measure'] - 1].getElementsByClass(harmony.ChordSymbol):
                # Serialized semantic harmony offset is independent from original visual placement.
                candidates = [
                    c for c in inventory['chords'] if c['measure'] == m['printed_measure']
                ]
                if candidates:
                    xy = (
                        candidates[0]['source_window'][0],
                        candidates[0]['source_window'][1] - top,
                    )
                else:
                    boxes = approved_chord_anchors()
                    require(m['printed_measure'] in boxes, 'Missing approved chord placement')
                    bx = boxes[m['printed_measure']]
                    xy = (bx[0], bx[1] - top)

                p, info = text_mask(
                    size, ImageFont.truetype(str(FONT), 40), chord_text(ch), left_top=xy
                )
                require(not overlap(p, fixed), 'Chord/music contact')
                ident = f'chord-{m["printed_measure"]}'
                chords[ident] = p
                chordmetrics.append(
                    {
                        'measure': m['printed_measure'],
                        'text': chord_text(ch),
                        'bbox': p.getbbox(),
                        **info,
                    }
                )
        require(not contacts(chords), 'Chord pair contact')
        fixed = combine([fixed, *chords.values()], size)
        text, placements = lyric_components(sys, inventory, score, marks, size, top)
        prior_clearance = (
            frozen_later_clearances(target, sys, inventory, evidence)
            if sys['system'] >= 6
            else None
        )
        if prior_clearance:
            goals = {
                r['measure']: r['frozen_owner_preview_center_distance_px']
                for r in prior_clearance['measures']
            }
        else:
            optical = next(
                t
                for t in read(
                    '/private/tmp/capomatic-v4-gt16c/gt16c-final-output/optical-spacing-metrics.json'
                )
                if t['target'] == target
            )
            goals = {
                r['measure']: r['center_distance_px']
                for r in optical['after']
                if r['system'] == sys['system']
            }
        moved, lm = place_lyrics(text, placements, fixed, prior_goals=goals)
        final = combine([fixed, *moved.values()], size)
        b = final.getbbox()
        require(b[0] > 0 and b[1] > 0 and b[2] < size[0] and b[3] < size[1], 'System clipping')
        final.crop(b).save(out / f'{target}-system-{sys["system"]}-rendered.png')
        music = combine([*parts.values(), *contextparts.values(), *scaffold.values()], size)
        music.save(out / f'{target}-system-{sys["system"]}-music-alpha.png')
        component_dir = out / f'{target}-system-{sys["system"]}-components'
        component_dir.mkdir()
        component_map = []
        for ident, p in {**parts, **contextparts, **scaffold, **chords, **moved}.items():
            file = ident.replace(':', '_').replace('/', '_') + '.png'
            p.crop(p.getbbox()).save(component_dir / file)
            component_map.append(
                {
                    'id': ident,
                    'file': file,
                    'bbox_local': list(p.getbbox()),
                    'source_page_origin_y': top,
                    'sha256': sha(component_dir / file),
                    'size_bytes': (component_dir / file).stat().st_size,
                }
            )
        dump(
            component_dir / 'component-map.json',
            {
                'system': sys['system'],
                'coordinate_contract': 'Integer crop-local pixel centers, right/bottom-exclusive bbox; final y = local y + source_page_origin_y + declared system dy + outer warning header 140',
                'components': component_map,
            },
        )
        systems.append((sys['system'], final.crop(b), [b[0], b[1] + top, b[2], b[3] + top]))
        curve_staff = sum(
            h['pixels']
            for h in structure_hits
            if h['b'] == 'staff' and h['a'] in {c['id'] for c in metrics['curves']}
        )
        reports.append(
            {
                'system': sys['system'],
                'printed_measures': sys['printed_measures'],
                'events': metrics['events'],
                'max_head_anchor_residual': metrics['max_head_residual'],
                'missing_connections': metrics['missing_connections'],
                'refinements': refinement,
                'lyric_layout': lm,
                'syllables': sum(not p.get('continuation', False) for p in placements),
                'continuation_strokes': sum(p.get('continuation', False) for p in placements),
                'chords': chordmetrics,
                'structure_contacts': structure_hits,
                'intentional_curve_staff_contact_pixels': curve_staff,
                'unexpected_contacts': 0,
                'clipping': False,
                'curve_endpoints': metrics['curves'],
                'actual_endpoint_validation': endpoint_metrics,
                'frozen_prior_clearance': prior_clearance,
                'post_refinement_connection_validation': connection_metrics,
                'curve_staff_contact_pixels_before_sampling': sum(
                    overlap(p, scaffold['staff']) for p in old_curves.values()
                ),
            }
        )
        print(target, 'system', sys['system'], 'rendered', flush=True)
        del parts, musicparts, scaffold, contextparts, chords, text, moved, fixed, final, music
        gc.collect()
    transforms = []
    prior_bottom = 0
    for system, tile, box in systems:
        dy = max(0, prior_bottom + 24 - box[1])
        transforms.append({'system': system, 'source_registered_bbox': box, 'dy': dy, 'x_delta': 0})
        prior_bottom = box[3] + dy
    height = max(3564, prior_bottom + 60)
    alpha = Image.new('L', (2520, height))
    registered = Image.new('L', (2520, 3564))
    for (system, tile, b), t in zip(systems, transforms):
        alpha.paste(tile, (b[0], b[1] + t['dy']))
        require(b[3] <= 3564, 'Source registered crop exceeds declared page')
        region = registered.crop(b)
        registered.paste(Image.fromarray(np.maximum(np.asarray(region), np.asarray(tile))), b[:2])
    title_font = ImageFont.truetype(str(KOREAN_FONT), 64)
    title_text = '주님의 마음 있는 곳'
    title_width = title_font.getbbox(title_text)[2]
    title_mask, title_metrics = section_label(
        alpha.size, title_font, title_text, ((2520 - title_width) / 2, 124)
    )
    require(not overlap(title_mask, alpha), 'Metadata title overlaps notation')
    alpha = combine([alpha, title_mask], alpha.size)
    image = framed(
        alpha,
        f'{target} major / nine systems / 37 printed measures / final standalone research engraving',
    )
    image.save(out / f'{target}-final-full-score.png')
    framed(registered, f'{target} source-registered diagnostic').save(
        out / f'{target}-source-registered.png'
    )
    pdf = export_pdf(image, out / f'{target}-final-full-score.pdf')
    return image, {
        'target': target,
        'systems': reports,
        'events_rendered': sum(len(r['events']) for r in reports),
        'syllables_rendered': sum(r['syllables'] for r in reports),
        'chords_rendered': sum(len(r['chords']) for r in reports),
        'continuation_strokes_rendered': sum(r['continuation_strokes'] for r in reports),
        'transforms': transforms,
        'canvas_size': list(image.size),
        'pdf': pdf,
        'metadata_title': {
            'text': title_text,
            'basis': 'User-provided score identity, newly typeset research heading; not OCR-derived independent source evidence',
            **title_metrics,
        },
        'renderer': 'Fresh existing calibrated glyph renderer for all 9 systems; no old PNG copy',
    }
