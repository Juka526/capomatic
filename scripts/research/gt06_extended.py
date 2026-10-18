"""Bounded double-beam research layer; no source erasure or production integration."""

import argparse
from fractions import Fraction
import itertools
import json
import math
from pathlib import Path
import shutil
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

from scripts.research.gt04_visual import HEAD, panel_label
from scripts.research.gt05_raster_anchor import glyph
from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes, line_y

BASE = '16c43394b3b63aa19e08bd35ae333a7da148d11c'
DESIGN = Path(__file__).resolve().parents[2] / 'docs/V4_GT06_PREREGISTRATION.json'


def group_evidence(group, rows, moves, graph):
    """Require complete explicit SIG ownership, not geometrical proximity."""
    reasons = []
    if len(rows) != 2 or {r['symbol_id'] for r in rows} != set(group['heads']):
        reasons.append('INCOMPLETE_HEAD_GROUP')
    if len(group['beams']) != 2 or len(group['stems']) != 2:
        reasons.append('NOT_TWO_FULL_BEAMS_TWO_STEMS')
    if any(
        r['status'] != 'MATCHED'
        or r['kind'] != 'NOTE'
        or Fraction(r['duration']) != Fraction(1, 4)
        or r.get('chord_size') != 1
        or r.get('chord_continuation')
        for r in rows
    ):
        reasons.append('UNSUPPORTED_SEMANTIC_EVENT')
    if len({tuple(r['printed_measures']) for r in rows}) != 1:
        reasons.append('CROSS_MEASURE_GROUP')
    owned = {
        s
        for r in rows
        for _, ids in moves.get(r['id'], {}).get('connected_symbols', [])
        for s in ids
    }
    if any(
        k not in {'head', 'head-chord', 'stem', 'beam', 'ledger'}
        for r in rows
        for k, _ in moves.get(r['id'], {}).get('connected_symbols', [])
    ):
        reasons.append('UNSUPPORTED_CONNECTED_SYMBOL')
    if any(
        (r['source'] in owned or r['target'] in owned)
        and any(k in r['kind'] for k in ['slur', 'articulation', 'fermata'])
        for r in graph['relations']
    ):
        reasons.append('UNSUPPORTED_ATTACHMENT')
    lineage = []
    stems = []
    for row in rows:
        hs = [
            r
            for r in graph['relations']
            if r['kind'] == 'head-stem'
            and r['source'] == row['symbol_id']
            and r['target'] in group['stems']
        ]
        if len(hs) != 1:
            reasons.append('HEAD_STEM_LINEAGE_MISSING')
            continue
        stem = hs[0]['target']
        side = dict(hs[0]['attributes']).get('head-side')
        if side not in {'RIGHT', 'LEFT'}:
            reasons.append('UNKNOWN_STEM_SIDE')
        stems.append((row['id'], stem, side))
        lineage.append(hs[0]['id'])
        for beam in group['beams']:
            rels = [
                r
                for r in graph['relations']
                if r['kind'] == 'beam-stem' and r['source'] == beam and r['target'] == stem
            ]
            if len(rels) != 1:
                reasons.append('BEAM_STEM_LINEAGE_MISSING')
            else:
                lineage.append(rels[0]['id'])
    if len({s for _, s, _ in stems}) != 2 or len({s for _, _, s in stems}) != 1:
        reasons.append('INCOMPATIBLE_STEM_LINEAGE')
    for beam in group['beams']:
        symbol = graph['symbols'][beam]
        geom = symbol['geometry']
        if (
            symbol['kind'] != 'beam'
            or not geom['valid']
            or len(geom['line']) != 2
            or not geom['thickness']
        ):
            reasons.append('UNSUPPORTED_BEAM_GEOMETRY')
    return sorted(set(reasons)), stems, sorted(lineage)


def choose(groups, events, moves, graph):
    decisions = []
    ordered = []
    for group in groups:
        rows = sorted(
            [r for r in events if r['symbol_id'] in group['heads']],
            key=lambda r: Fraction(r['local_offset']),
        )
        if rows:
            ordered.append(
                (
                    min(rows[0]['printed_measures']),
                    Fraction(rows[0]['local_offset']),
                    group['id'],
                    group,
                    rows,
                )
            )
    for measure, _, _, group, rows in sorted(ordered):
        reasons, stems, lineage = group_evidence(group, rows, moves, graph)
        decisions.append({'group': group['id'], 'measure': measure, 'blockers': reasons})
        if not reasons:
            return group, rows, stems, lineage, decisions
    raise ValueError('RENDER_BLOCKED_UNSUPPORTED_NOTATION: no supported complete atomic group')


def semantic_note(score, event):
    from music21 import stream, harmony

    measures = list(score.parts[event['part_index'] - 1].getElementsByClass(stream.Measure))
    measure = measures[event['omr_measure_index']]
    notes = [n for n in measure.recurse().notes if not isinstance(n, harmony.ChordSymbol)]
    result = notes[int(event['id'].rsplit(':n', 1)[1])]
    if Fraction(result.getOffsetInHierarchy(measure)) != Fraction(event['offset']) or Fraction(
        result.duration.quarterLength
    ) != Fraction(event['duration']):
        raise ValueError('Semantic onset/duration correspondence changed')
    return result


def semantic_check(note, index, pitch_name):
    if (
        not note.isNote
        or note.nameWithOctave != pitch_name
        or note.duration.type != '16th'
        or note.duration.dots
        or note.duration.tuplets
        or note.duration.isGrace
        or note.tie
        or note.articulations
        or note.expressions
        or [(b.number, b.type) for b in note.beams]
        != [(1, ['start', 'stop'][index]), (2, ['start', 'stop'][index])]
    ):
        raise ValueError('RENDER_BLOCKED_UNSUPPORTED_NOTATION: semantic beam/attachment mismatch')


def prepare(gt01, gt02, gt04, gt05, out):
    from music21 import converter
    from backend.omr_v3.music_guard import validate
    from scripts.research.ground_truth_02 import verify_inputs

    if out.exists():
        raise ValueError('New input directory required')
    if any(
        root.resolve() == out.resolve() or root.resolve() in out.resolve().parents
        for root in [gt01, gt02, gt04, gt05]
    ):
        raise ValueError('Output inside immutable evidence')
    verify_inputs(gt01)
    for historical in [gt04 / 'visual-prototype', gt05 / 'revised-visual-prototype']:
        frozen = json.loads((historical / 'prototype-freeze.json').read_text())
        current = file_hashes(historical)
        current.pop('prototype-freeze.json')
        if current != frozen['files']:
            raise ValueError('Historical visual evidence changed')
    gate = json.loads((gt05 / 'independent-tests/gate.json').read_text())
    if not gate['passed'] or gate['algorithm_sha256'] != sha(
        Path(__file__).with_name('gt05_raster_anchor.py')
    ):
        raise ValueError('GT05 placement gate changed')
    b = gt01 / 'predictions/baseline-exec'
    graph = json.loads((b / 'source/visual-graph.json').read_text())
    plans = {k: json.loads((b / k / 'plan.json').read_text()) for k in ['A', 'G']}
    events = json.loads((gt02 / 'note-correspondence-diagnostic.json').read_text())['events']['Bb']
    registration = json.loads((gt02 / 'measure-registration.json').read_text())['pages']['Bb']
    moves = {n['semantic_id']: n for n in plans['A']['note_moves']}
    group, rows, stems, relations, decisions = choose(
        plans['A']['beam_groups'], events, moves, graph
    )
    measure = rows[0]['printed_measures'][0]
    region = next(r for r in registration['measures'] if r['printed_measure'] == measure)
    staff_ids = {graph['symbols'][r['symbol_id']]['staff'] for r in rows}
    if len(staff_ids) != 1:
        raise ValueError('Staff lineage ambiguous')
    staff = next(s for s in graph['staves'] if s['id'] in staff_ids)
    source = converter.parse(str(b / 'source/recognized.musicxml'))
    guards = {}
    for key, shift in [('A', -1), ('G', -3)]:
        target = converter.parse(str(b / key / 'transposed.musicxml'))
        guards[key] = validate(source, target, shift, 'key').to_dict()
        if not guards[key]['ok']:
            raise ValueError('Full V3 musical integrity failure')
        anchors = {
            n['semantic_id']: n
            for n in json.loads((b / key / 'track-b-geometry.json').read_text())['notes']
        }
        for index, row in enumerate(rows):
            n = semantic_note(source, row)
            semantic_check(n, index, row['pitch'])
            a = anchors[row['id']]
            semantic_check(semantic_note(target, row), index, a['target_pitch'])
            row.setdefault('frozen', {})[key] = a
    for row in rows:
        row['stem_id'], row['stem_side'] = next(
            (s, side) for ident, s, side in stems if ident == row['id']
        )
    out.mkdir(parents=True)
    shutil.copyfile(b / 'source/source.png', out / 'source.png')
    spec = {
        'design_sha256': sha(DESIGN),
        'source_sha256': sha(out / 'source.png'),
        'selected': [measure],
        'scope': 'ATOMIC_GROUP_ONLY_NOT_COMPLETE_MEASURE',
        'group': group,
        'relation_ids': relations,
        'decisions': decisions,
        'events': rows,
        'excluded_events': [
            r['id']
            for r in events
            if r['printed_measures'] == [measure] and r['id'] not in {n['id'] for n in rows}
        ],
        'staff': staff,
        'left': region['left']['x'],
        'right': region['right']['x'],
        'beams': [graph['symbols'][i] for i in group['beams']],
        'protected': graph['text_protected_regions'],
        'guards': guards,
        'input_hashes': {
            'source_graph': sha(b / 'source/visual-graph.json'),
            'source_musicxml': sha(b / 'source/recognized.musicxml'),
            'A_musicxml': sha(b / 'A/transposed.musicxml'),
            'G_musicxml': sha(b / 'G/transposed.musicxml'),
            'gt04_selection': sha(gt04 / 'render-input/selection.json'),
        },
    }
    dump(out / 'selection.json', spec)
    return spec


def beam_geometry(stems, beams, interline, up):
    """Preserve source beam slope/separation, re-anchor to actual stem columns."""
    if len(stems) != 2 or len(beams) != 2 or not math.isfinite(interline) or interline <= 0:
        raise ValueError('Incomplete beam group')
    stems = sorted(stems)
    x0, x1 = stems[0][0], stems[-1][0]
    if not all(math.isfinite(v) for s in stems for v in s) or x1 <= x0:
        raise ValueError('Invalid stem geometry')
    beams = sorted(beams, key=lambda b: sum(p[1] for p in b['geometry']['line']), reverse=not up)
    primary = beams[0]['geometry']['line']
    if len(primary) != 2 or primary[1][0] <= primary[0][0]:
        raise ValueError('Invalid beam line')
    slope = (primary[1][1] - primary[0][1]) / (primary[1][0] - primary[0][0])
    at = lambda line, x: line_y(line, x)
    # Source lines need not cover the newly rasterized attachment columns; extend only
    # their two-point slope, never sample reference notation or alter note x/y.
    source_mid_x = (primary[0][0] + primary[1][0]) / 2
    separation = abs(at(beams[1]['geometry']['line'], source_mid_x) - at(primary, source_mid_x))
    thicknesses = [round(b['geometry']['thickness']) for b in beams]
    if (
        not all(math.isfinite(v) for v in [slope, separation, *thicknesses])
        or not 0.5 * interline <= separation <= interline
        or any(t <= 0 or t >= separation for t in thicknesses)
    ):
        raise ValueError('Unsupported beam thickness/separation')
    sign = -1 if up else 1
    intercepts = [y + sign * 3.5 * interline - slope * (x - x0) for x, y in stems]
    intercept = min(intercepts) if up else max(intercepts)
    result = []
    for i, (beam, thick) in enumerate(zip(beams, thicknesses)):
        y0 = intercept - sign * i * separation
        y1 = y0 + slope * (x1 - x0)
        result.append(
            {
                'symbol_id': beam['id'],
                'line': [[x0, y0], [x1, y1]],
                'thickness': thick,
                'slope': slope,
            }
        )
    return result


def contacts(parts, allowed):
    found = []
    for (a, aa), (b, bb) in itertools.combinations(parts.items(), 2):
        count = int(np.count_nonzero((np.asarray(aa) > 0) & (np.asarray(bb) > 0)))
        if count:
            found.append(
                {
                    'a': a,
                    'b': b,
                    'pixels': count,
                    'intentional': 'staff' in {a, b} or frozenset((a, b)) in allowed,
                }
            )
    return found


def measure_anchor(mask, requested):
    """Score actual nonzero raster pixels separately from placement metadata."""
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError('Missing raster head')
    center = [(bbox[i] + bbox[i + 2] - 1) / 2 for i in [0, 1]]
    return {
        'measured_raster_center': center,
        'measured_anchor_residual': [center[i] - requested[i] for i in [0, 1]],
    }


def render(inputs, font_path, out):
    from music21 import pitch

    if out.exists() or inputs.resolve() in out.resolve().parents:
        raise ValueError('New output directory required')
    spec = json.loads((inputs / 'selection.json').read_text())
    if sha(inputs / 'source.png') != spec['source_sha256'] or sha(DESIGN) != spec['design_sha256']:
        raise ValueError('Input/design changed')
    if sha(font_path) != json.loads(DESIGN.read_text())['font_sha256']:
        raise ValueError('Font identity changed')
    if not all(g['ok'] for g in spec['guards'].values()):
        raise ValueError('Full integrity required')
    start = time.monotonic()
    scope = f'{spec["events"][0]["local_offset"]}-{Fraction(spec["events"][-1]["local_offset"])+Fraction(spec["events"][-1]["duration"])}'
    source = Image.open(inputs / 'source.png')
    size = source.size
    staff = spec['staff']
    inter = staff['interline']
    left, right = spec['left'], spec['right']
    viewport = (
        math.floor(left) - 8,
        math.floor(staff['lines'][0][0][1]) - 130,
        math.ceil(right) + 9,
        math.ceil(staff['lines'][-1][0][1]) + 140,
    )
    tt = TTFont(font_path)
    g = tt['glyf'][tt.getBestCmap()[ord(HEAD)]]
    units = (g.xMin, g.yMin, g.xMax, g.yMax)
    upm = tt['head'].unitsPerEm
    fontsize = round(1.25 * inter * upm / (g.xMax - g.xMin))
    font = ImageFont.truetype(str(font_path), fontsize)
    protected = np.zeros((size[1], size[0]), bool)
    for r in spec['protected']:
        x0, y0, x1, y1 = r['bbox']
        protected[
            max(0, math.floor(y0)) : min(size[1], math.ceil(y1)),
            max(0, math.floor(x0)) : min(size[0], math.ceil(x1)),
        ] = True
    dark = np.asarray(source.convert('L')) < 127
    out.mkdir(parents=True)
    panels = [
        panel_label(
            source.crop(viewport),
            f'Unchanged Bb measure {spec["selected"][0]}; target scope ONLY offset {scope}',
        )
    ]
    panels[0].save(out / 'original-bb.png')
    rows = []
    for key in ['A', 'G']:
        parts = {}
        allowed = set()
        infos = []
        heads = []
        sf = Image.new('L', size)
        d = ImageDraw.Draw(sf)
        for line in staff['lines']:
            points = (
                [(left, line_y(line, left))]
                + [tuple(p) for p in line if left < p[0] < right]
                + [(right, line_y(line, right))]
            )
            d.line(points, fill=255, width=2)
        parts['staff'] = sf
        bar = Image.new('L', size)
        d = ImageDraw.Draw(bar)
        for x in [left, right]:
            d.line(
                [(x, line_y(staff['lines'][0], x)), (x, line_y(staff['lines'][-1], x))],
                fill=255,
                width=2,
            )
        parts['bar'] = bar
        for event in spec['events']:
            ident = event['id']
            a = event['frozen'][key]
            x = a['detected_head_x']
            y = a['absolute_target_staff_y']
            p = pitch.Pitch(a['target_pitch'])
            pos = 35 - p.diatonicNoteNum
            if abs(y - (line_y(staff['lines'][2], x) + pos * inter / 2)) > 1e-8:
                raise ValueError('Semantic pitch y mismatch')
            alter = {'A': {'F': 1, 'C': 1, 'G': 1}, 'G': {'F': 1}}[key].get(p.step, 0)
            if (p.accidental.alter if p.accidental else 0) != alter:
                raise ValueError('RENDER_BLOCKED_UNSUPPORTED_NOTATION: explicit accidental')
            mask, info = glyph(size, font, HEAD, (x, y), units, fontsize / upm)
            info.update(measure_anchor(mask, (x, y)))
            parts[ident + ':head'] = mask
            pixels = np.argwhere(np.asarray(mask) > 0)
            up = event['stem_side'] == 'RIGHT'
            edge = int(pixels[:, 1].max() - 1 if up else pixels[:, 1].min() + 1)
            attach = float(np.median(pixels[pixels[:, 1] == edge, 0]))
            heads.append((event, x, y, edge, attach, up))
            led = Image.new('L', size)
            ld = ImageDraw.Draw(led)
            positions = (
                range(6, pos + 1, 2) if pos >= 6 else range(-6, pos - 1, -2) if pos <= -6 else []
            )
            for position in positions:
                ly = line_y(staff['lines'][2], x) + position * inter / 2
                ld.line([(x - 0.875 * inter, ly), (x + 0.875 * inter, ly)], fill=255, width=2)
            if led.getbbox():
                parts[ident + ':ledger'] = led
                allowed.add(frozenset((ident + ':head', ident + ':ledger')))
                allowed.add(frozenset((ident + ':stem', ident + ':ledger')))
            infos.append(
                {
                    'semantic_id': ident,
                    'kind': 'NOTE',
                    'source_pitch': a['source_pitch'],
                    'target_pitch': a['target_pitch'],
                    'duration': event['duration'],
                    'physical_detected_center': [x, a['detected_head_y']],
                    'corrected_semantic_source_y': a['corrected_semantic_source_staff_y'],
                    'target_semantic_y': y,
                    'notehead_x_deviation': info['requested_anchor'][0] - x,
                    'target_pitch_y_deviation': y
                    - (line_y(staff['lines'][2], x) + pos * inter / 2),
                    **info,
                }
            )
        up = heads[0][-1]
        geometry = beam_geometry([(h[3], h[2]) for h in heads], spec['beams'], inter, up)
        for event, x, y, edge, attach, _ in heads:
            ident = event['id']
            primary = geometry[0]
            end = line_y(primary['line'], edge) + (-1 if up else 1) * primary['thickness'] / 2
            stem = Image.new('L', size)
            ImageDraw.Draw(stem).line([(edge, attach), (edge, end)], fill=255, width=2)
            parts[ident + ':stem'] = stem
            allowed.add(frozenset((ident + ':head', ident + ':stem')))
        for beam in geometry:
            mask = Image.new('L', size)
            d = ImageDraw.Draw(mask)
            (x0, y0), (x1, y1) = beam['line']
            h = beam['thickness'] / 2
            d.polygon([(x0, y0 - h), (x1 + 1, y1 - h), (x1 + 1, y1 + h), (x0, y0 + h)], fill=255)
            name = beam['symbol_id'] + ':beam'
            parts[name] = mask
            for event, *_ in heads:
                allowed.add(frozenset((event['id'] + ':stem', name)))
        hits = contacts(parts, allowed)
        connectivity = []
        for event, *_ in heads:
            ident = event['id']
            for other in [ident + ':head'] + [b['symbol_id'] + ':beam' for b in geometry]:
                n = int(
                    np.count_nonzero(
                        (np.asarray(parts[ident + ':stem']) > 0) & (np.asarray(parts[other]) > 0)
                    )
                )
                connectivity.append({'stem': ident + ':stem', 'other': other, 'contact_pixels': n})
        music = np.maximum.reduce(
            [np.array(m) for n, m in parts.items() if n not in {'staff', 'bar'}]
        )
        ink = np.maximum.reduce([np.array(m) for m in parts.values()])
        box = Image.fromarray(ink).getbbox()
        clipped = (
            not box
            or box[0] < max(0, viewport[0])
            or box[1] < max(0, viewport[1])
            or box[2] > min(size[0], viewport[2])
            or box[3] > min(size[1], viewport[3])
        )
        envelope = int(np.count_nonzero((music > 0) & protected))
        protected_dark = int(np.count_nonzero((music > 0) & protected & dark))
        maxres = max(abs(v) for i in infos for v in i['measured_anchor_residual'])
        unexpected = [h for h in hits if not h['intentional']]
        metric = {
            'measure': spec['selected'][0],
            'viewport_page_coordinates': viewport,
            'target': key,
            'events': infos,
            'beam_geometry': geometry,
            'required_connection_checks': connectivity,
            'ink_intersections': hits,
            'max_notehead_raster_anchor_residual': maxres,
            'unexpected_ink_collision_pairs': len(unexpected),
            'protected_envelope_contact_pixels': envelope,
            'protected_source_dark_contact_pixels': protected_dark,
            'page_or_crop_clipping': bool(clipped),
            'missing_semantic_events': len(spec['events']) - len(infos),
            'duplicate_semantic_events': len(infos) - len({i['semantic_id'] for i in infos}),
            'staff_geometry_deviation': 0,
            'measure_boundary_deviation': 0,
            'beam_count': len(geometry),
            'checks_pass': maxres <= 0.5
            and not clipped
            and not unexpected
            and envelope == 0
            and all(c['contact_pixels'] > 0 for c in connectivity),
        }
        rows.append(metric)
        Image.fromarray(ink).save(out / f'{key}-notation-alpha.png')
        layer = Image.fromarray(255 - ink).convert('RGB').crop(viewport)
        panel = panel_label(
            layer, f'{key} major; m{spec["selected"][0]} offset {scope} ONLY; 2 sixteenths, 2 beams'
        )
        panel.save(out / ('predicted-a.png' if key == 'A' else 'predicted-g.png'))
        panels.append(panel)
    contact = Image.new(
        'RGB', (sum(p.width for p in panels) + 24, max(p.height for p in panels)), 'white'
    )
    x = 0
    for panel in panels:
        contact.paste(panel, (x, 0))
        x += panel.width + 12
    contact.save(out / 'comparison-contact-sheet.png')
    raw = source.crop(viewport)
    equal = panels[0].crop((0, 84, raw.width, 84 + raw.height)).tobytes() == raw.tobytes()
    verdict = (
        'EXTENDED_VISUAL_POC_PASS'
        if equal and all(r['checks_pass'] for r in rows)
        else 'EXTENDED_VISUAL_POC_NEEDS_REFINEMENT'
    )
    result = {
        'decision': verdict,
        'study': 'GT06-extended-notation-01',
        'source_sha256': spec['source_sha256'],
        'selection_sha256': sha(inputs / 'selection.json'),
        'font_sha256': sha(font_path),
        'glyph_algorithm_sha256': sha(Path(__file__).with_name('gt05_raster_anchor.py')),
        'scope': spec['scope'],
        'metrics': rows,
        'full_integrity': spec['guards'],
        'source_crop_pixel_equality': equal,
        'lyric_composite_produced': False,
        'seconds': time.monotonic() - start,
        'peak_memory': 'NOT_MEASURED',
        'optical_quality': 'REQUIRES_SEPARATE_REVIEW',
    }
    dump(out / 'rendering-metrics.json', result)
    dump(
        out / 'rendering-limitations.json',
        {
            'complete_score': False,
            'complete_measure': False,
            'excluded_event_ids': spec['excluded_events'],
            'unsupported': [
                'flags',
                'curves',
                'explicit accidentals',
                'moving attachments',
                'key/clef/time glyphs',
                'full chords',
                'lyric composition',
            ],
            'chord_coverage': 'INCOMPLETE: 7 recognized of 24 coordinator candidates, no new OCR or fabrication',
            'annotation_labels_collected': 0,
            'source_edit_authorization': 'NONE',
        },
    )
    dump(
        out / 'prototype-freeze.json',
        {
            'files': file_hashes(out),
            'reference_comparison_started': False,
            'code_sha256': sha(Path(__file__)),
            'selection_sha256': sha(inputs / 'selection.json'),
        },
    )
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['prepare', 'render'])
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--inputs', type=Path)
    p.add_argument('--font', type=Path)
    args = p.parse_args()
    if args.mode == 'prepare':
        result = prepare(
            Path('/private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output'),
            Path('/private/tmp/capomatic-v4-ground-truth-02/ground-truth-02-output'),
            Path('/private/tmp/capomatic-v4-gt04-visual/ground-truth-04-output'),
            Path('/private/tmp/capomatic-v4-gt05-anchor/gt05-anchor-output'),
            args.out,
        )
        print({'selected': result['selected'], 'group': result['group']['id']})
    else:
        result = render(args.inputs, args.font, args.out)
        print(result['decision'])


if __name__ == '__main__':
    main()
