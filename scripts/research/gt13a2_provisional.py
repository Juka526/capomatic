"""Standalone provisional first-system notation; frozen source inputs are read-only."""

import argparse
import copy
import itertools
import math
from fractions import Fraction
from pathlib import Path

import numpy as np
from fontTools.ttLib import TTFont
from music21 import converter, pitch, stream
from PIL import Image, ImageDraw, ImageFont
import cv2

from backend.omr_v3.music_guard import validate
from scripts.research.gt04_visual import HEAD, REST
from scripts.research.gt05_raster_anchor import glyph
from scripts.research.gt07_flags import FLAG, flag_mask
from scripts.research.gt11_complete_measure import FONT, GT01, events_of, read, require
from scripts.research.gt12_render_context import KOREAN_FONT, GT11, canonical_box, text_mask
from scripts.research.gt13a_full_system import CANDIDATES, CROP, GT12
from scripts.research.paired_ground_truth_01 import dump, file_hashes, line_y, sha

PRIOR = Path('/private/tmp/capomatic-v4-gt13a/gt13a-output')
PREVIOUS = Path(__file__).resolve().parents[2] / 'gt13a2-output'
PROTOCOL = Path(__file__).resolve().parents[2] / 'docs/V4_GT13A2_PROTOCOL.json'
EIGHTH_REST = chr(0x1D13E)


def linked(relations, kind, ident):
    return [
        r['target'] if r['source'] == ident else r['source']
        for r in relations
        if r['kind'] == kind and ident in (r['source'], r['target'])
    ]


def mixed_layout(nodes, symbols, relations, inter):
    """Return source-backed up-stem mixed beams, rejecting missing/extra memberships."""
    beams = {
        s['id']: s
        for s in symbols.values()
        if s['kind'] in ('beam', 'beam-hook')
        and any(t in nodes for t in linked(relations, 'beam-stem', s['id']))
    }
    require(math.isfinite(inter) and inter > 0, 'Invalid staff spacing')
    for b in beams.values():
        require(
            all(t in nodes for t in linked(relations, 'beam-stem', b['id'])),
            'Incomplete beam group',
        )
        require(all(math.isfinite(v) for p in b['geometry']['line'] for v in p), 'Nonfinite beam')
    for sid, node in nodes.items():
        duration = node['event'].get('duration')
        if duration is not None:
            require(
                (duration, len(node['event']['beams'])) in [('1/2', 1), ('1/4', 2)],
                'Duration and beam level disagree',
            )
        actual = {b for b in beams if sid in linked(relations, 'beam-stem', b)}
        require(
            len(actual) == len(node['event']['beams']), 'Beam count does not match duration levels'
        )
    # A primary spans all stems of each connected beam group; source vertical order breaks no ownership ties.
    primaries = [
        b
        for b in beams.values()
        if b['kind'] == 'beam' and len(linked(relations, 'beam-stem', b['id'])) >= 3
    ]
    require(len(primaries) * 3 == len(nodes), 'Unsupported primary group topology')
    result, tips = [], {}
    for primary in sorted(primaries, key=lambda b: b['id']):
        members = linked(relations, 'beam-stem', primary['id'])
        members.sort(key=lambda s: nodes[s]['x'])
        require(
            [nodes[s]['event']['beams'][0]['type'] for s in members]
            == ['start', 'continue', 'stop'],
            'Invalid primary rhythm linkage',
        )
        line = primary['geometry']['line']
        require(len(line) == 2 and line[1][0] > line[0][0], 'Invalid primary geometry')
        slope = (line[1][1] - line[0][1]) / (line[1][0] - line[0][0])
        x0 = nodes[members[0]]['x']
        y0 = min(nodes[s]['y'] - 3.5 * inter - slope * (nodes[s]['x'] - x0) for s in members)
        for s in members:
            tips[s] = y0 + slope * (nodes[s]['x'] - x0)
        group = [
            b
            for b in beams.values()
            if set(linked(relations, 'beam-stem', b['id'])) <= set(members)
        ]
        for b in group:
            bs = sorted(linked(relations, 'beam-stem', b['id']), key=lambda s: nodes[s]['x'])
            bl = b['geometry']['line']
            require(len(bl) == 2 and bl[1][0] > bl[0][0], 'Invalid secondary geometry')
            thick = round(b['geometry']['thickness'])
            require(0 < thick < inter, 'Invalid beam thickness')
            srcx = sum(p[0] for p in bl) / 2
            # Source support separation, extrapolating only the explicit straight primary median.
            separation = (bl[0][1] + bl[1][1]) / 2 - (line[0][1] + slope * (srcx - line[0][0]))
            level = 1 if b['id'] == primary['id'] else 2
            if level == 2:
                require(0.5 * inter <= separation <= inter, 'Unsupported secondary beam spacing')
            for s in bs:
                bm = next((v for v in nodes[s]['event']['beams'] if v['number'] == level), None)
                require(bm is not None, 'SIG beam lacks semantic level')
            if b['kind'] == 'beam-hook':
                require(len(bs) == 1, 'Hook ownership ambiguous')
                bm = next(v for v in nodes[bs[0]]['event']['beams'] if v['number'] == 2)
                require(
                    bm['type'] == 'partial' and bm['direction'] in ('left', 'right'),
                    'Hook direction missing',
                )
                start = nodes[bs[0]]['x']
                end = start + (1 if bm['direction'] == 'right' else -1) * (bl[1][0] - bl[0][0])
                lo, hi = sorted((start, end))
                require(
                    nodes[members[0]]['x'] <= lo < hi <= nodes[members[-1]]['x'],
                    'Hook escapes group',
                )
            else:
                lo, hi = nodes[bs[0]]['x'], nodes[bs[-1]]['x']
                require(lo < hi, 'Beam needs two stems')
            result.append(
                {
                    'id': b['id'],
                    'members': bs,
                    'level': level,
                    'kind': b['kind'],
                    'line': [
                        [lo, y0 + slope * (lo - x0) + separation],
                        [hi, y0 + slope * (hi - x0) + separation],
                    ],
                    'thickness': thick,
                }
            )
    require(len(result) == len(beams), 'Unrepresented beam')
    return result, tips


def translated_curve(curve, left_delta, right_delta):
    require(len(curve) == 4 and curve[-1][0] > curve[0][0], 'Invalid cubic')
    require(
        all(math.isfinite(v) for p in curve for v in p)
        and all(math.isfinite(v) for v in (left_delta, right_delta)),
        'Nonfinite curve',
    )
    x0, x1 = curve[0][0], curve[-1][0]
    return [
        [x, y + left_delta + (right_delta - left_delta) * (x - x0) / (x1 - x0)] for x, y in curve
    ]


def curve_mask(size, curve):
    mask = Image.new('L', size)
    points = []
    for t in np.linspace(0, 1, 65):
        points.append(
            tuple(
                sum(
                    c[k] * w
                    for c, w in zip(
                        curve, [(1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t**3]
                    )
                )
                for k in (0, 1)
            )
        )
    ImageDraw.Draw(mask).line(points, fill=255, width=2)
    return mask


def ink_distance(mask):
    """Existing OpenCV exact Euclidean transform (float32 output), pixel-center units."""
    return cv2.distanceTransform(
        (np.asarray(mask) == 0).astype('uint8'), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
    )


def annotation_metrics(mask, music, distance, viewport):
    """Measure actual nonzero alpha pixels in one explicit output coordinate system."""
    require(
        mask.mode == music.mode == 'L' and mask.size == music.size,
        'Annotation/musical mask alignment mismatch',
    )
    pixels = np.asarray(mask) > 0
    require(pixels.any() and np.asarray(music).any(), 'Missing annotation or musical ink')
    x0, y0, x1, y1 = viewport
    inside = int(np.count_nonzero(pixels[y0:y1, x0:x1]))
    center_distance = float(distance[pixels].min())
    return {
        'bbox': list(mask.getbbox()),
        'annotation_pixels': int(pixels.sum()),
        'notation_region_pixels': inside,
        'ink_contacts': int(np.count_nonzero(pixels & (np.asarray(music) > 0))),
        'min_pixel_center_distance_px': center_distance,
        # Unit-pixel squares extend half a diagonal from their center. This is a lower bound,
        # not an optical legibility score or an antialias threshold.
        'pixel_square_clearance_lower_bound_px': max(0.0, center_distance - math.sqrt(2)),
    }


def panel(image, title, *, target=None, music=None, score_ink=None):
    """Keep all diagnostics in separate margins; retain the native source crop unscaled."""
    header, footer = 250, 160
    size = (image.width, image.height + header + footer)
    result = Image.new('RGB', size, 'white')
    result.paste(image, (0, header))
    viewport = (0, header, image.width, header + image.height)
    annotations = []
    aggregate = Image.new('L', size)
    musical = Image.new('L', size)
    all_score = Image.new('L', size)
    if music is not None:
        require(
            music.size == image.size and score_ink.size == image.size,
            'Panel mask coordinate mismatch',
        )
        musical.paste(music, (0, header))
        all_score.paste(score_ink, (0, header))
        distance = ink_distance(musical)
        score_distance = ink_distance(all_score)

    def write(xy, text, *, fill='black', font=None):
        mask = Image.new('L', size)
        ImageDraw.Draw(mask).text(xy, text, font=font, fill=255)
        require(mask.getbbox() is not None, 'Empty annotation')
        result.paste(fill, (0, 0, *size), mask)
        aggregate.paste(255, (0, 0, *size), mask)
        if music is not None:
            metrics = annotation_metrics(mask, musical, distance, viewport)
            metrics['all_score_ink'] = annotation_metrics(mask, all_score, score_distance, viewport)
            require(
                metrics['notation_region_pixels'] == 0
                and metrics['ink_contacts'] == 0
                and metrics['all_score_ink']['ink_contacts'] == 0,
                'Diagnostic annotation intrudes into notation',
            )
            annotations.append({'text': text, **metrics})

    lines = [
        'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / FULL_SYSTEM_INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING',
        title,
        'BLUE: OMR_PROVISIONAL m1/2/4 | BLACK m3: unchanged GT12 OWNER_VERIFIED',
        '26 recognized / 26 displayed events: 4 OWNER_VERIFIED + 22 OMR_PROVISIONAL. Source completeness UNVERIFIED.',
        'OWNER_CONFIRMED_LYRIC_TRANSCRIPTION: m1/2/4 strings only; lyric associations remain UNVERIFIED.',
        'm1 syllable placement is provisional; m2/4 transcription below is NOT aligned lyric engraving.',
        'Missing header engraving: clef/key/time/forward repeat. Target key appears as caption only.',
        'm1 Bb source chord candidate: UNVERIFIED / NOT ENGRAVED. Only verified m3 E/D chord is rendered.',
        'm4 outgoing tie: UNSUPPORTED_OR_UNRESOLVED. No stub or destination note fabricated.',
    ]
    for i, text in enumerate(lines):
        write((8, 5 + 22 * i), text)
    if target is not None:
        lyric_font = ImageFont.truetype(str(KOREAN_FONT), 22)
        for column, number in enumerate((2, 4)):
            x = 10 + column * (image.width // 2)
            write(
                (x, header + image.height + 20),
                f'm{number}: OWNER_CONFIRMED_LYRIC_TRANSCRIPTION / association withheld',
                fill=(25, 65, 150),
            )
            for row, key in enumerate(('upper', 'lower')):
                write(
                    (x, header + image.height + 50 + 40 * row),
                    ' / '.join(CANDIDATES[number][key]),
                    font=lyric_font,
                    fill=(25, 65, 150),
                )
    return (
        result,
        {
            'coordinate_system': 'native panel pixel-index centers, no scaling; source crop origin translated only',
            'source_viewport': list(viewport),
            'header_height': header,
            'footer_height': footer,
            'annotations': annotations,
            'minimum_musical_ink_clearance_px': min(
                (m['min_pixel_center_distance_px'] for m in annotations), default=None
            ),
            'minimum_all_score_ink_clearance_px': min(
                (m['all_score_ink']['min_pixel_center_distance_px'] for m in annotations),
                default=None,
            ),
        },
        aggregate,
    )


def run(out):
    require(not out.exists(), 'Fresh output directory required')
    histories = {str(p): file_hashes(p) for p in (PRIOR, GT12, PREVIOUS, GT11 / 'gt11-output')}
    previous_freeze = read(PREVIOUS / 'prediction-freeze.json')
    require(
        all(sha(PREVIOUS / p) == h for p, h in previous_freeze['files'].items()),
        'Prior GT13A2 prediction changed',
    )
    for root, freeze, key in [
        (PRIOR, PRIOR / 'prediction-freeze.json', 'files'),
        (GT12, GT12 / 'confirmed-context/prediction-freeze.json', 'output_files_sha256'),
    ]:
        frozen = read(freeze)
        require(
            all(sha(root / p) == h for p, h in frozen[key].items()), 'Frozen prediction changed'
        )
    inv = read(PRIOR / 'source-system-inventory.json')
    source_path = GT01 / 'predictions/baseline-exec/source/source.png'
    require(
        sha(source_path) == read(PRIOR / 'input-and-inventory-freeze.json')['source_sha256'],
        'Source hash mismatch',
    )
    original = Image.open(source_path)
    size = (original.width, 750)
    staff = inv['staff']
    inter = staff['interline']
    symbols = {s['id']: s for s in inv['related_symbols']}
    relations = inv['notation_relations']
    source = converter.parse(str(GT01 / 'predictions/baseline-exec/source/recognized.musicxml'))
    tt = TTFont(FONT)
    cmap = tt.getBestCmap()
    upm = tt['head'].unitsPerEm
    units = {}
    for ch in (HEAD, REST, EIGHTH_REST, FLAG):
        require(ord(ch) in cmap, 'Font lacks required glyph')
        g = tt['glyf'][cmap[ord(ch)]]
        units[ch] = (g.xMin, g.yMin, g.xMax, g.yMax)
    fontsize = round(1.25 * inter * upm / (units[HEAD][2] - units[HEAD][0]))
    font = ImageFont.truetype(str(FONT), fontsize)
    scale = fontsize / upm
    lyrics_font = ImageFont.truetype(str(KOREAN_FONT), 44)
    out.mkdir()
    inventory = copy.deepcopy(inv)
    for m in inventory['measures']:
        m['render_action'] = 'EXACT_GT12_REUSE' if m['printed_measure'] == 3 else 'OMR_PROVISIONAL'
        m['lyric_strings_status'] = (
            'OWNER_VERIFIED' if m['printed_measure'] == 3 else 'OWNER_CONFIRMED_LYRIC_TRANSCRIPTION'
        )
        for e in m['events']:
            e['render_evidence'] = (
                'OWNER_VERIFIED' if m['printed_measure'] == 3 else 'OMR_PROVISIONAL'
            )
    dump(out / 'source-event-inventory.json', inventory)
    dump(
        out / 'input-freeze.json',
        {
            'source': sha(source_path),
            'historical_files': histories,
            'font': sha(FONT),
            'korean_font': sha(KOREAN_FONT),
            'protocol': sha(PROTOCOL),
            'inventory': sha(out / 'source-event-inventory.json'),
        },
    )
    original.crop(CROP).save(out / 'original-bb.png')
    panels = [panel(original.crop(CROP), 'Original Bb; source-only context')[0]]
    reports = []
    guards = {}
    for target, shift in [('A', -1), ('G', -3)]:
        target_score = converter.parse(
            str(GT01 / f'predictions/baseline-exec/{target}/transposed.musicxml')
        )
        guards[target] = validate(source, target_score, shift, 'key').to_dict()
        augmented = converter.parse(str(GT12 / 'confirmed-context/owner-augmented-source.musicxml'))
        confirmed_target = converter.parse(
            str(GT12 / f'confirmed-context/{target}-transposed.musicxml')
        )
        guards[target + '_GT12'] = validate(augmented, confirmed_target, shift, 'key').to_dict()
        require(
            guards[target]['ok'] and guards[target + '_GT12']['ok'], 'Full semantic guard failed'
        )
        measures = list(target_score.parts[0].getElementsByClass(stream.Measure))
        parts = {}
        owners = {}
        allowed = set()
        event_metrics = []
        nodes = {}
        heads = {}
        event_targets = {}

        def add(name, mask, owner):
            require(
                name not in parts and mask.getbbox() is not None,
                'Duplicate/missing rendered component',
            )
            parts[name] = mask
            owners[name] = owner

        for m in inv['measures']:
            number = m['printed_measure']
            if number == 3:
                continue
            target_events = events_of(measures[number - 1])
            require(len(target_events) == len(m['events']), 'Event count changed')
            for e, n in zip(m['events'], target_events):
                ident = e['event_id']
                b = e['source_bbox']
                x = (b[0] + b[2]) / 2
                require(Fraction(n.quarterLength) == Fraction(e['duration']), 'Duration changed')
                require(
                    Fraction(n.getOffsetInHierarchy(measures[number - 1])) == Fraction(e['onset']),
                    'Onset changed',
                )
                if e['kind'] == 'REST':
                    require(n.isRest and e['duration'] in ('1', '1/2'), 'Unsupported rest')
                    ch = REST if e['duration'] == '1' else EIGHTH_REST
                    mask, info = glyph(size, font, ch, (x, (b[1] + b[3]) / 2), units[ch], scale)
                    add(ident + ':rest', mask, ident)
                else:
                    require(
                        n.isNote and n.pitch.midi - pitch.Pitch(e['pitch']).midi == shift,
                        'Pitch interval changed',
                    )
                    require(
                        e['stem_direction'] == 'up' and not e['articulations'],
                        'Unsupported source attachment/direction',
                    )
                    pos = 35 - n.pitch.diatonicNoteNum
                    y = line_y(staff['lines'][2], x) + pos * inter / 2
                    expected = {'A': {'F': 1, 'C': 1, 'G': 1}, 'G': {'F': 1}}[target].get(
                        n.pitch.step, 0
                    )
                    require(
                        (n.pitch.accidental.alter if n.pitch.accidental else 0) == expected,
                        'Explicit accidental unsupported',
                    )
                    head, info = glyph(size, font, HEAD, (x, y), units[HEAD], scale)
                    require(max(map(abs, info['anchor_residual'])) <= 0.5, 'Anchor gate failed')
                    add(ident + ':head', head, ident)
                    pixels = np.argwhere(np.asarray(head) > 0)
                    edge = int(pixels[:, 1].max() - 1)
                    attachment = float(np.median(pixels[pixels[:, 1] == edge, 0]))
                    stems = linked(relations, 'head-stem', e['symbol_id'])
                    require(len(stems) == 1, 'Missing unique head-stem relation')
                    node = {
                        'x': edge,
                        'y': y,
                        'attachment': attachment,
                        'event': e,
                        'tip': y - 3.5 * inter,
                    }
                    nodes[stems[0]] = node
                    heads[e['symbol_id']] = {
                        'event': e,
                        'target': n,
                        'delta': (pitch.Pitch(e['pitch']).diatonicNoteNum - n.pitch.diatonicNoteNum)
                        * inter
                        / 2,
                    }
                    event_targets[ident] = [x, y]
                    ledger = Image.new('L', size)
                    d = ImageDraw.Draw(ledger)
                    positions = (
                        range(6, pos + 1, 2)
                        if pos >= 6
                        else range(-6, pos - 1, -2) if pos <= -6 else []
                    )
                    for p in positions:
                        ly = line_y(staff['lines'][2], x) + p * inter / 2
                        d.line(
                            [(x - 0.875 * inter, ly), (x + 0.875 * inter, ly)], fill=255, width=2
                        )
                    if ledger.getbbox():
                        add(ident + ':ledger', ledger, ident)
                    info.update(
                        source_pitch=e['pitch'],
                        target_pitch=n.pitch.nameWithOctave,
                        physical_source_center=[x, (b[1] + b[3]) / 2],
                        target_staff=[x, y],
                    )
                event_metrics.append(
                    {
                        'id': ident,
                        'measure': number,
                        'kind': e['kind'],
                        'evidence': 'OMR_PROVISIONAL',
                        **info,
                    }
                )
        beamed = {s: n for s, n in nodes.items() if n['event']['beams']}
        beam_rows, tips = mixed_layout(beamed, symbols, relations, inter)
        for s, y in tips.items():
            nodes[s]['tip'] = y
        for s, node in nodes.items():
            e = node['event']
            ident = e['event_id']
            stem = Image.new('L', size)
            ImageDraw.Draw(stem).line(
                [(node['x'], node['attachment']), (node['x'], node['tip'])], fill=255, width=2
            )
            add(ident + ':stem', stem, ident)
            flags = linked(relations, 'flag-stem', s)
            if not e['beams'] and e['duration'] == '1/2':
                require(
                    len(flags) == 1 and symbols[flags[0]]['shape'] == 'FLAG_1',
                    'Missing explicit single flag',
                )
                mask, fi = flag_mask(size, font, (node['x'], node['tip']), units[FLAG], scale)
                add(ident + ':flag', mask, ident)
            else:
                require(not flags, 'Unexpected flag')
        for b in beam_rows:
            mask = Image.new('L', size)
            ImageDraw.Draw(mask).line([tuple(p) for p in b['line']], fill=255, width=b['thickness'])
            add(b['id'], mask, b['id'])
            for s in b['members']:
                allowed.add(frozenset((b['id'], nodes[s]['event']['event_id'] + ':stem')))
        curves = []
        unresolved = []
        for c in inv['curves']:
            rs = [r for r in inv['curve_relations'] if r['source'] == c['id']]
            if len(rs) != 2:
                unresolved.append(
                    {
                        'symbol': c['id'],
                        'reason': 'UNSUPPORTED_OR_UNRESOLVED',
                        'detail': 'CROSS_SYSTEM_DESTINATION_UNRESOLVED',
                        'rendered_stub': False,
                        'source_cubic': c['geometry']['curve'],
                        'source_attributes': c['attributes'],
                        'source_heads': [r['target'] for r in rs],
                    }
                )
                continue
            ends = {dict(r['attributes'])['side']: heads[r['target']] for r in rs}
            require(set(ends) == {'LEFT', 'RIGHT'}, 'Curve endpoints ambiguous')
            l, r = ends['LEFT'], ends['RIGHT']
            require(
                l['event']['tie'] == 'start'
                and r['event']['tie'] == 'stop'
                and l['target'].pitch == r['target'].pitch,
                'Tie semantics disagree',
            )
            cp = translated_curve(c['geometry']['curve'], l['delta'], r['delta'])
            add(c['id'], curve_mask(size, cp), c['id'])
            curves.append({'id': c['id'], 'curve': cp, 'head_ids': [v['target'] for v in rs]})
        # GT12 m1 lyric contract is reused; confirmed strings do not certify this provisional association.
        row_boxes = [[1480, 588, 1730, 632], [1480, 635, 1730, 688]]
        from scripts.research.gt12_render_context import ink_bbox

        descent = max(canonical_box(lyrics_font, c)[3] - 2 * lyrics_font.size for c in '주님의사막')
        baselines = [ink_bbox(original, w)[3] - descent for w in row_boxes]
        first = [e for e in inv['measures'][0]['events'] if e['kind'] == 'NOTE']
        for row, syllables in enumerate((CANDIDATES[1]['upper'], CANDIDATES[1]['lower'])):
            for syllable, e in zip(syllables, first):
                mask, _ = text_mask(
                    size,
                    lyrics_font,
                    syllable,
                    center_x=event_targets[e['event_id']][0],
                    baseline=baselines[row],
                )
                add(f'lyric:{row}:{e["event_id"]}', mask, 'lyric')
        intersections = []
        for a, b in itertools.combinations(parts, 2):
            ba, bb = parts[a].getbbox(), parts[b].getbbox()
            box = (max(ba[0], bb[0]), max(ba[1], bb[1]), min(ba[2], bb[2]), min(ba[3], bb[3]))
            if box[2] <= box[0] or box[3] <= box[1]:
                continue
            count = int(
                np.count_nonzero(
                    (np.asarray(parts[a].crop(box)) > 0) & (np.asarray(parts[b].crop(box)) > 0)
                )
            )
            if count:
                intersections.append(
                    {
                        'a': a,
                        'b': b,
                        'pixels': count,
                        'intentional': (owners[a] == owners[b] and owners[a] != 'lyric')
                        or frozenset((a, b)) in allowed,
                    }
                )
        clipping = [
            a
            for a, p in parts.items()
            if any(
                [
                    p.getbbox()[0] < CROP[0],
                    p.getbbox()[1] < CROP[1],
                    p.getbbox()[2] > CROP[2],
                    p.getbbox()[3] > CROP[3],
                ]
            )
        ]
        connections = []
        for s, node in nodes.items():
            ident = node['event']['event_id']
            names = (
                [ident + ':head']
                + ([ident + ':flag'] if ident + ':flag' in parts else [])
                + [b['id'] for b in beam_rows if s in b['members']]
            )
            for name in names:
                connections.append(
                    {
                        'stem': ident + ':stem',
                        'component': name,
                        'pixels': int(
                            np.count_nonzero(
                                (np.asarray(parts[ident + ':stem']) > 0)
                                & (np.asarray(parts[name]) > 0)
                            )
                        ),
                    }
                )
        require(all(c['pixels'] > 0 for c in connections), 'Disconnected required stem attachment')
        cached = Image.open(GT12 / f'confirmed-context/{target}-combined-alpha.png').crop(
            (0, 0, *size)
        )
        scaffold = Image.open(PRIOR / 'staff-and-boundary-scaffold.png').crop((0, 0, *size))
        canvas = Image.composite(
            Image.new('RGB', size, 'black'),
            Image.new('RGB', size, 'white'),
            Image.fromarray(np.maximum(np.asarray(cached), np.asarray(scaffold))),
        )
        provisional = Image.new('L', size)
        for name, mask in parts.items():
            provisional = Image.fromarray(np.maximum(np.asarray(provisional), np.asarray(mask)))
            mask.save(out / f'{target}-{name.replace(":","_")}.png')
        require(
            not provisional.crop((1374, 310, 1783, 720)).getbbox(),
            'Provisional ink invades verified m3',
        )
        canvas = Image.composite(Image.new('RGB', size, (25, 65, 150)), canvas, provisional)
        provisional.save(out / f'{target}-provisional-alpha.png')
        # Do not alter a single music/lyric mask while moving diagnostics into margins.
        for name, expected in previous_freeze['files'].items():
            if name.startswith(target + '-') and name.endswith('.png'):
                require(sha(out / name) == expected, 'Previous music/lyric raster changed: ' + name)
        canvas.crop(CROP).save(out / f'{target}-notation-viewport.png')
        music = Image.new('L', size)
        for name, mask in parts.items():
            if not name.startswith('lyric:'):
                music = Image.fromarray(np.maximum(np.asarray(music), np.asarray(mask)))
        music_path = GT11 / f'gt11-output/components/{target}/music-only-alpha.png'
        music_binding = read(GT11 / 'gt11-output/prediction-freeze.json')['files']
        require(
            sha(music_path) == music_binding[f'components/{target}/music-only-alpha.png'],
            'Cached verified musical-only mask changed',
        )
        cached_music = Image.open(music_path).crop((0, 0, *size))
        music = Image.fromarray(np.maximum(np.asarray(music), np.asarray(cached_music)))
        score_ink = Image.fromarray(
            np.maximum(
                np.asarray(provisional), np.maximum(np.asarray(cached), np.asarray(scaffold))
            )
        )
        panel_image, annotation_report, annotation_mask = panel(
            canvas.crop(CROP),
            f'{target} major; caption-only key context; music/lyric masks byte-identical to prior GT13A2',
            target=target,
            music=music.crop(CROP),
            score_ink=score_ink.crop(CROP),
        )
        annotation_mask.save(out / f'{target}-annotation-alpha.png')
        panel_image.save(out / f'predicted-{target.lower()}.png')
        panels.append(panel_image)
        reports.append(
            {
                'target': target,
                'recognized_events': 26,
                'owner_verified_rendered': 4,
                'provisional_rendered': len(event_metrics),
                'unrendered_events': 26 - 4 - len(event_metrics),
                'events_with_unresolved_required_components': [
                    inv['measures'][3]['events'][-1]['event_id']
                ],
                'event_metrics': event_metrics,
                'beams': beam_rows,
                'local_ties': curves,
                'outgoing_ties': unresolved,
                'connections': connections,
                'intersections': intersections,
                'unexpected_intersections': [c for c in intersections if not c['intentional']],
                'clipping': clipping,
                'diagnostic_caption_contacts': annotation_report,
                'previous_component_pngs_byte_identical': True,
                'overall': 'FULL_SYSTEM_INCOMPLETE',
                'max_head_residual': max(
                    abs(v)
                    for e in event_metrics
                    if e['kind'] == 'NOTE'
                    for v in e['anchor_residual']
                ),
                'GT12_cached_alpha_sha256': sha(
                    GT12 / f'confirmed-context/{target}-combined-alpha.png'
                ),
                'm3_provisional_ink_overlap': 0,
                'full_system_complete': False,
            }
        )
    sheet = Image.new('RGB', (panels[0].width, sum(p.height for p in panels)), 'white')
    for i, p in enumerate(panels):
        sheet.paste(p, (0, i * p.height))
    sheet.save(out / 'comparison-contact-sheet.png')
    dump(out / 'provisional-rendering-report.json', reports)
    dump(out / 'semantic-integrity.json', guards)
    dump(
        out / 'unsupported-symbols.json',
        {
            'unresolved': [
                'm4 final outgoing cross-system tie: UNSUPPORTED_OR_UNRESOLVED; no stub rendered',
                'clef/key/time/repeat glyph context',
                'm1 Bb chord candidate',
                'm2/4 exact lyric-to-note associations',
            ],
            'source_completeness': 'UNVERIFIED',
            'independent_ground_truth': False,
        },
    )
    require(
        all(file_hashes(Path(p)) == h for p, h in histories.items()), 'Historical evidence changed'
    )
    dump(
        out / 'prediction-freeze.json',
        {
            'base': read(PROTOCOL)['base'],
            'code_sha256': sha(Path(__file__)),
            'files': file_hashes(out),
            'phase': 'BEFORE_AGENT_VISUAL_INSPECTION',
        },
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    run(parser.parse_args().out)
