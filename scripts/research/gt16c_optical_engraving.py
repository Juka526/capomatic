"""Optical layout of frozen generated layers, never original source pixels."""

import argparse
import copy
import math
import re
from dataclasses import dataclass, replace
from pathlib import Path

import cv2
import numpy as np
from music21 import converter, harmony, stream
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt11_complete_measure import FONT, read, require
from scripts.research.gt13a2_provisional import ink_distance
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.gt13a4_header import header
from scripts.research.gt13a_full_system import scaffold
from scripts.research.gt13a5_lyric_layout import union, verify_freeze
from scripts.research.gt14e_two_system_validation import (
    load_components,
    GT13A5,
    GT14A,
    GT14B,
    GT14D,
    GT13A6,
    GT13A4,
    HEADER,
    GT13A3,
    GT12,
)
from scripts.research.gt15_third_system import second_ending
from scripts.research.gt15b_confirmed_third_system import music_signature
from scripts.research.gt16_fourth_system import repeat_signature, SOURCE_DIR
from scripts.research.gt16b_confirmed_fourth_system import verify_owner
from scripts.research.paired_ground_truth_01 import dump, file_hashes, sha

ROOT = Path(__file__).resolve().parents[2]
BASE = Path('/private/tmp/capomatic-v4-gt16b/gt16b-final-output')
GT15B = Path('/private/tmp/capomatic-v4-gt15b/gt15b-final-output')
GT15 = Path('/private/tmp/capomatic-v4-gt15/gt15-final-output')
GT16 = Path('/private/tmp/capomatic-v4-gt16/gt16-final-output')
GT13A2 = Path('/private/tmp/capomatic-v4-gt13a2/gt13a2-final-output')
GT14 = Path('/private/tmp/capomatic-v4-gt14/gt14-final-output')
PROTOCOL = ROOT / 'docs/V4_GT16C_PROTOCOL_REVISION_2.json'
WARNING = 'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE — INCOMPLETE — NOT FOR PERFORMANCE OR PRINTING'


@dataclass
class Piece:
    id: str
    tile: Image.Image
    box: tuple
    system: int
    measure: int
    kind: str
    provenance: str = ''

    def moved(self, dy):
        return replace(self, box=(self.box[0], self.box[1] + dy, self.box[2], self.box[3] + dy))


def piece(name, image, system, measure, kind, provenance=''):
    b = image.getbbox()
    require(image.mode == 'L' and b is not None, 'Invalid component')
    return Piece(name, image.crop(b), tuple(b), system, measure, kind, provenance)


def compose(parts, size):
    result = np.zeros((size[1], size[0]), 'uint8')
    for p in parts:
        x0, y0, x1, y1 = p.box
        require(0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1], 'Component clipping')
        require(p.tile.size == (x1 - x0, y1 - y0), 'Tile geometry mismatch')
        result[y0:y1, x0:x1] = np.maximum(result[y0:y1, x0:x1], np.asarray(p.tile))
    return Image.fromarray(result)


def contact(a, b):
    box = (
        max(a.box[0], b.box[0]),
        max(a.box[1], b.box[1]),
        min(a.box[2], b.box[2]),
        min(a.box[3], b.box[3]),
    )
    if box[0] >= box[2] or box[1] >= box[3]:
        return 0

    def crop(p):
        return (
            np.asarray(p.tile)[
                box[1] - p.box[1] : box[3] - p.box[1], box[0] - p.box[0] : box[2] - p.box[0]
            ]
            > 0
        )

    return int(np.count_nonzero(crop(a) & crop(b)))


def pair_contacts(parts):
    return [
        {'a': a.id, 'b': b.id, 'pixels': n}
        for j, a in enumerate(parts)
        for b in parts[j + 1 :]
        if (n := contact(a, b))
    ]


def expand(image, size):
    require(image.width == size[0] and image.mode == 'L', 'Raster coordinate mismatch')
    b = image.getbbox()
    require(b is not None and b[3] <= size[1], 'Expansion clips ink')
    result = Image.new('L', size)
    result.paste(image.crop((0, 0, size[0], min(size[1], image.height))), (0, 0))
    return result


def load_text(target, size):
    old, _ = load_components(target, read(GT13A5 / 'lyric-layout-metrics.json')[target + '-local'])
    parts = []
    graph = read(SOURCE_DIR / 'visual-graph.json')
    measures = graph['measures']

    def measure_for(x, system):
        ms = [
            m
            for m in measures
            if m['system'] == f'sheet#1:system:{system}' and m['bounds'][0] <= x < m['bounds'][2]
        ]
        require(len(ms) == 1, 'Ambiguous generated text registration')
        return int(ms[0]['number'])

    first_associations = {
        e['event_id']: e
        for m in read(GT13A4 / 'lyric-association-audit.json')['measures']
        for e in m['events']
    }
    for name, p in old.items():
        b = p.getbbox()
        sys = 1 if name.startswith('first-') else 2
        kind = (
            'MARK' if any(v in name for v in ('continuation', 'extender', 'GT14C')) else 'SYLLABLE'
        )
        # The four first-system held-syllable marks retain the original helper IDs.
        if 'extend' in name:
            kind = 'MARK'
        if sys == 1 and (match := re.search(r'p1_m(\d+)_([nr]\d+)', name)):
            eid = f'p1:m{match[1]}:{match[2]}'
            if (
                eid in first_associations
                and first_associations[eid]['candidate_relation']
                == 'TIED_CONTINUATION_NO_NEW_SYLLABLE'
            ):
                kind = 'MARK'
        parts.append(
            piece(
                name, p, sys, measure_for((b[0] + b[2] - 1) / 2, sys), kind, 'GT14E load_components'
            )
        )
    del old
    for sys, directory in [(3, GT15B), (4, BASE)]:
        r = next(r for r in read(directory / 'rendering-validation.json') if r['target'] == target)
        for placement in r['placements']:
            name = placement['id']
            mark = 'syllable' not in name
            filename = f'{target}-{name.replace("/","_" if sys==3 else "-")}-alpha.png'
            path = directory / filename
            p = Image.open(path)
            parts.append(
                piece(
                    name,
                    p,
                    sys,
                    int(placement.get('printed_measure', placement.get('measure'))),
                    'MARK' if mark else 'SYLLABLE',
                    str(path),
                )
            )
    require(
        len(parts) == 112 and len({p.id for p in parts}) == 112,
        '112 unique text components required',
    )
    require(sum(p.kind == 'MARK' for p in parts) == 28, '28 continuation marks required')
    require(not pair_contacts(parts), 'Frozen text pair collision')
    frozen_checks = next(
        r for r in read(BASE / 'rendering-validation.json') if r['target'] == target
    )
    require(
        frozen_checks['lyric_layout']['lyric_music_contacts'] == 0
        and not frozen_checks['lyric_layout']['lyric_pair_contacts'],
        'Frozen fourth text safety mismatch',
    )
    frozen_checks3 = next(
        r for r in read(GT15B / 'rendering-validation.json') if r['target'] == target
    )
    require(
        frozen_checks3['lyric_layout']['lyric_music_contacts'] == 0
        and not frozen_checks3['lyric_layout']['lyric_pair_contacts'],
        'Frozen third text safety mismatch',
    )
    full = Image.open(BASE / f'{target}-combined-alpha.png')
    text = compose(parts, size)
    require(np.all(np.asarray(text) <= np.asarray(full)), 'Text absent from frozen preview')
    # These are known, generated, previously collision-checked layers, not source-ink classification.
    fixed = np.asarray(full).copy()
    fixed[np.asarray(text) > 0] = 0
    require(
        np.array_equal(np.maximum(fixed, np.asarray(text)), np.asarray(full)),
        'Lossless decomposition failed',
    )
    return parts, Image.fromarray(fixed)


class Distances:
    def __init__(self, fixed):
        self.support = np.asarray(fixed) > 0
        require(self.support.any(), 'No notation obstacles')
        self.field = ink_distance(fixed)

    def measure(self, parts):
        pts = []
        for p in parts:
            y, x = np.where(np.asarray(p.tile) > 0)
            pts.append(np.column_stack((x + p.box[0], y + p.box[1])))
        require(pts, 'No text in region')
        pts = np.concatenate(pts)
        distances = self.field[pts[:, 1], pts[:, 0]]
        approximate = float(distances.min())
        # Pixel-square edge distance can beat the nearest center by at most sqrt(2).
        # Exhaustively examine all local pairs within that provable bound; no scipy dependency.
        radius = math.ceil(approximate + math.sqrt(2) + 1e-5)
        edge = center = float('inf')
        edge_pair = center_pair = None
        for q in pts[distances <= approximate + math.sqrt(2) + 1e-5]:
            x0 = max(0, int(q[0]) - radius)
            y0 = max(0, int(q[1]) - radius)
            tile = self.support[y0 : int(q[1]) + radius + 1, x0 : int(q[0]) + radius + 1]
            yy, xx = np.where(tile)
            near = np.column_stack((xx + x0, yy + y0))
            delta = np.abs(near - q)
            dc = np.sqrt((delta * delta).sum(axis=1))
            de = np.sqrt((np.maximum(delta - 1, 0) ** 2).sum(axis=1))
            if len(dc) and dc.min() < center:
                k = int(np.argmin(dc))
                center = float(dc[k])
                center_pair = [q.tolist(), near[k].tolist()]
            if len(de) and de.min() < edge:
                k = int(np.argmin(de))
                edge = float(de[k])
                edge_pair = [q.tolist(), near[k].tolist()]
        return {
            'center_distance_px': center,
            'pixel_square_edge_distance_px': edge,
            'nearest_center_pixel_pair': center_pair,
            'nearest_edge_pixel_pair': edge_pair,
        }


def minimum_dy(parts, distance, bottom, goal):
    require(goal >= 2 and parts, 'Invalid optical goal/group')
    maximum = bottom - max(p.box[3] for p in parts)
    feasible = []
    for dy in range(maximum + 1):
        ok = True
        for p in parts:
            b = p.box
            field = distance[b[1] + dy : b[3] + dy, b[0] : b[2]]
            if float(field[np.asarray(p.tile) > 0].min()) + 1e-7 < goal:
                ok = False
                break
        if ok:
            feasible.append(dy)
    return {
        'maximum_dy': maximum,
        'feasible_dy': feasible,
        'selected_dy': feasible[0] if feasible else None,
    }


def layout(parts, fixed, allocations, goal, extra=0, lyric_bottoms=None):
    size = (fixed.width, fixed.height + len(allocations) * extra)
    fp = []
    moved = []
    domains = []
    for j, (top, bottom) in enumerate(allocations):
        band = Image.new('L', size)
        band.paste(fixed.crop((0, top, fixed.width, bottom)), (0, top + j * extra))
        fp.append(band)
    fixed2 = union(fp)
    distance = ink_distance(fixed2)
    for j, (top, bottom) in enumerate(allocations):
        group = [p.moved(j * extra) for p in parts if p.system == j + 1]
        lyric_bottom = lyric_bottoms[j] if lyric_bottoms else bottom
        domain = minimum_dy(group, distance, lyric_bottom + (j + 1) * extra, goal)
        domains.append(domain)
        if domain['selected_dy'] is None:
            return None, {
                'feasible': False,
                'failed_system': j + 1,
                'goal': goal,
                'extra': extra,
                'domains': domains,
            }
        moved.extend(p.moved(domain['selected_dy']) for p in group)
    text = compose(moved, size)
    hits = int(np.count_nonzero((np.asarray(text) > 0) & (np.asarray(fixed2) > 0)))
    pairs = pair_contacts(moved)
    require(hits == 0 and not pairs, 'Final text collision')
    require(
        len(moved) == len(parts)
        and all(
            a.tile.tobytes() == b.tile.tobytes() and a.box[0] == b.box[0]
            for a, b in zip(sorted(parts, key=lambda p: p.id), sorted(moved, key=lambda p: p.id))
        ),
        'Glyph/horizontal anchor changed',
    )
    return (moved, fixed2), {
        'feasible': True,
        'goal': goal,
        'extra': extra,
        'domains': domains,
        'system_offsets': [j * extra for j in range(len(allocations))],
        'canvas_height': size[1],
        'text_notation_contacts': hits,
        'text_pair_contacts': pairs,
        'lost_alpha_pixels': 0,
    }


def beam_candidate(spec, scale):
    """Fixed area samples in pixel-center coordinates; BOX average has no ringing."""
    require(scale in (2, 3, 4), 'Unsupported scale')
    (x0, y0), (x1, y1) = spec['line']
    w = spec['thickness']
    require(
        all(math.isfinite(v) for v in (x0, y0, x1, y1, w)) and x1 > x0 and w > 0,
        'Invalid beam geometry',
    )
    box = (
        math.floor(x0 - 1),
        math.floor(min(y0, y1) - w / 2 - 1),
        math.ceil(x1 + 2),
        math.ceil(max(y0, y1) + w / 2 + 2),
    )
    x = np.arange(box[0], box[2])
    y = np.arange(box[1], box[3])
    coverage = np.zeros((len(y), len(x)))
    for j in range(scale):
        yy = y[:, None] + (j + 0.5) / scale - 0.5
        for i in range(scale):
            xx = x[None, :] + (i + 0.5) / scale - 0.5
            center = y0 + (xx - x0) * (y1 - y0) / (x1 - x0)
            coverage += (
                (xx >= x0 - 0.5) & (xx < x1 + 0.5) & (yy >= center - w / 2) & (yy < center + w / 2)
            )
    tile = Image.fromarray(np.floor(coverage * 255 / (scale * scale) + 0.5).astype('uint8'))
    b = tile.getbbox()
    require(b is not None, 'Empty supersampled beam')
    return Piece(
        spec['id'],
        tile.crop(b),
        (box[0] + b[0], box[1] + b[1], box[0] + b[2], box[1] + b[3]),
        0,
        0,
        'BEAM',
    )


def beam_metrics(p, spec):
    a = np.asarray(p.tile).astype(float) / 255
    y = np.arange(p.box[1], p.box[3])[:, None]
    columns = a.sum(axis=0)
    x = np.arange(p.box[0], p.box[2])
    valid = (columns > 0) & (x > spec['line'][0][0] + 2) & (x < spec['line'][1][0] - 2)
    center = (a * y).sum(axis=0) / np.maximum(columns, 1e-10)
    (x0, y0), (x1, y1) = spec['line']
    error = (center - (y0 + (x - x0) * (y1 - y0) / (x1 - x0)))[valid]
    return {
        'detrended_coverage_centroid_rms_px': float(np.std(error)),
        'absolute_coverage_centroid_rms_px': float(np.sqrt(np.mean(error**2))),
        'coverage_centroid_bias_px': float(np.mean(error)),
        'nonzero_pixels': int(np.count_nonzero(a)),
        'coverage_area_px': float(a.sum()),
        'intermediate_alpha_pixels': int(np.count_nonzero((a > 0) & (a < 1))),
        'connected_components': cv2.connectedComponents((a > 0).astype('uint8'), 8)[0] - 1,
        'bbox': p.box,
    }


def beam_layers(target, fixed, size, graph, out, text_parts):
    baseline_pieces = []
    other_pieces = []
    selected = []
    rows = []
    specs = []
    for system, directory in [(3, GT15), (4, BASE)]:
        report = next(
            r
            for r in read((GT15 if system == 3 else GT16) / 'rendering-validation.json')
            if r['target'] == target
        )
        inv = read((GT15 if system == 3 else GT16) / 'source-event-inventory.json')
        allparts = {}
        for path in directory.glob(f'{target}-*alpha.png'):
            name = path.name[len(target) + 1 : -10]
            if name.startswith(('p1_', 'sheet#1_')):
                allparts[name] = piece(name, Image.open(path), system, 0, 'NOTATION', str(path))
        if system == 3:
            hp, _ = header(size, inv['staff'], target, FONT)
            context = {n: p for n, p in hp.items() if n == 'clef' or n.startswith('sharp')}
            ep, _ = second_ending(size, graph)
            context.update(ep)
            context['staff'] = scaffold(
                size,
                inv['staff'],
                [807, 1338, 1869, 2400],
                {2400: graph['symbols']['sheet#1:58']['geometry']['bbox']},
            )
            frozen = expand(Image.open(GT15 / f'{target}-third-system-alpha.png'), size)
        else:
            context = {
                p.stem: Image.open(p)
                for p in BASE.glob(f'{target}-*alpha.png')
                if any(
                    v in p.name
                    for v in [
                        'staff-and-bars',
                        '-clef-',
                        '-sharp-',
                        'first-ending',
                        'measure-number13',
                        '-chord-',
                    ]
                )
            }
            frozen = expand(Image.open(BASE / f'{target}-fourth-alpha.png'), size)
            lyric4 = [p for p in text_parts if p.system == 4]
            a = np.asarray(frozen).copy()
            a[np.asarray(compose(lyric4, size)) > 0] = 0
            frozen = Image.fromarray(a)
        ctx = [piece('context-' + n, p, system, 0, 'CONTEXT') for n, p in context.items()]
        require(
            compose(list(allparts.values()) + ctx, size).tobytes() == frozen.tobytes(),
            'Frozen notation/context reconstruction failed',
        )
        baseline_pieces.append(piece('old-system-core', frozen, system, 0, 'CORE'))
        diagonal = {
            b['id'].replace(':', '_'): b
            for b in report['beams']
            if b['line'][0][1] != b['line'][1][1]
        }
        others = [p for name, p in allparts.items() if name not in diagonal] + ctx
        other_pieces.extend(others)
        for name, spec in diagonal.items():
            old = allparts[name]
            oldm = beam_metrics(old, spec)
            stem_names = []
            for sid in spec['members']:
                ee = [e for m in inv['measures'] for e in m['events'] if sid in e['stem_ids']]
                require(len(ee) == 1, 'Stem lineage missing')
                stem_names.append((ee[0]['id'] + ':stem').replace(':', '_'))
            alternatives = []
            raster_panels = [picture(old.tile, 'Frozen beam mask: native resolution')]
            accepted = []
            for scale in (2, 3, 4):
                candidate = beam_candidate(spec, scale)
                candidate = replace(candidate, system=system)
                m = beam_metrics(candidate, spec)
                con = [{'stem': n, 'pixels': contact(candidate, allparts[n])} for n in stem_names]
                hits = []
                for n, p in allparts.items():
                    if n == name or n in stem_names:
                        continue
                    if contact(candidate, p):
                        hits.append({'component': n, 'pixels': contact(candidate, p)})
                context_new = []
                for p in ctx:
                    if contact(candidate, p) and not contact(old, p):
                        context_new.append(p.id)
                safe = (
                    all(c['pixels'] for c in con)
                    and not hits
                    and not context_new
                    and m['connected_components'] == 1
                )
                improves = (
                    m['detrended_coverage_centroid_rms_px']
                    < oldm['detrended_coverage_centroid_rms_px']
                )
                record = {
                    'scale': scale,
                    **m,
                    'stem_contacts': con,
                    'unrelated_contacts': hits,
                    'new_context_contact_pairs': context_new,
                    'safe': bool(safe),
                    'numeric_smoothness_improved': bool(improves),
                    'line_unchanged': True,
                    'members_unchanged': True,
                }
                alternatives.append(record)
                raster_panels.append(
                    picture(candidate.tile, f'{scale}x BOX coverage: native resolution')
                )
                info = PngInfo()
                info.add_text('Warning', WARNING)
                info.add_text(
                    'Role', 'Experimental alpha DATA mask; page bbox in beam-quality-metrics.json'
                )
                candidate.tile.save(out / f'{target}-beam-{name}-{scale}x-tile.png', pnginfo=info)
                if safe and improves:
                    accepted.append((scale, candidate))
            grid = raster_panels[0]
            for panel_image in raster_panels[1:]:
                grid = side(grid, panel_image, 'Beam mask alternatives; no source pixels')
            grid.save(out / f'{target}-beam-{name}-alternatives.png')
            chosen = max(accepted, key=lambda v: v[0]) if accepted else (1, old)
            selected.append(chosen[1])
            specs.append((old, chosen[1], spec))
            rows.append(
                {
                    'system': system,
                    'beam_id': spec['id'],
                    'line': spec['line'],
                    'members': spec['members'],
                    'baseline': oldm,
                    'alternatives': alternatives,
                    'selected_scale': chosen[0],
                }
            )
    # Replace only reconstructed generated cores; restore every nonbeam component explicitly.
    remaining = np.asarray(fixed).copy()
    for p in baseline_pieces:
        b = p.box
        v = remaining[b[1] : b[3], b[0] : b[2]]
        v[np.asarray(p.tile) > 0] = 0
    rebuilt = compose(other_pieces + [p[0] for p in specs], size)
    require(
        np.array_equal(np.maximum(remaining, np.asarray(rebuilt)), np.asarray(fixed)),
        'Baseline fixed recomposition failed',
    )
    refined = union([Image.fromarray(remaining), compose(other_pieces + selected, size)])
    changed = np.asarray(refined) != np.asarray(fixed)
    allowed = compose([p for pair in specs for p in pair[:2]], size)
    require(not np.any(changed & (np.asarray(allowed) == 0)), 'Nonbeam ink changed')
    return refined, rows, specs, allparts


def frame_rgb(im, title):
    width = max(480, im.width)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 18)
    lines = []
    for text in [
        WARNING,
        title,
        'Fixed semantics / newly typeset lyrics / optical heuristic experiment / no independent musician review',
    ]:
        line = ''
        for word in text.split():
            if line and font.getlength(line + ' ' + word) > width - 20:
                lines.append(line)
                line = word
            else:
                line = (line + ' ' + word).strip()
        lines.append(line)
    height = 15 + 25 * len(lines)
    out = Image.new('RGB', (width, im.height + height), 'white')
    draw = ImageDraw.Draw(out)
    for j, line in enumerate(lines):
        draw.text((10, 5 + j * 25), line, font=font, fill='black')
    out.paste(im, (0, height))
    return out


def picture(alpha, title):
    im = Image.composite(
        Image.new('RGB', alpha.size, 'black'), Image.new('RGB', alpha.size, 'white'), alpha
    )
    return frame_rgb(im, title)


def side(a, b, title):
    canvas = Image.new('RGB', (a.width + b.width, max(a.height, b.height)), 'white')
    canvas.paste(a, (0, 0))
    canvas.paste(b, (a.width, 0))
    return frame_rgb(canvas, title)


def regions(parts, distance, fixed, graph, allocations, target, phase, out):
    result = []
    for measure in read(PROTOCOL)['priority_measures']:
        group = [p for p in parts if p.measure == measure]
        require(group, 'Missing priority text')
        system = (measure - 1) // 4 + 1
        m = distance.measure(group)
        bounds = [
            min(p.box[0] for p in group),
            min(p.box[1] for p in group),
            max(p.box[2] for p in group),
            max(p.box[3] for p in group),
        ]
        point = m['nearest_center_pixel_pair'][1]
        nearest = []
        for directory in (GT13A2, GT14, GT15, BASE):
            for path in list(directory.glob(f'{target}-p1*')) + list(
                directory.glob(f'{target}-sheet#1*')
            ):
                if path.suffix != '.png':
                    continue
                im = Image.open(path)
                b = im.getbbox()
                if (
                    b
                    and b[0] <= point[0] < b[2]
                    and b[1] <= point[1] < b[3]
                    and im.getpixel(tuple(point))
                ):
                    nearest.append(path.name)
        result.append(
            {
                'measure': measure,
                'system': system,
                'staff_id': f'sheet#1:{system}',
                **m,
                'component_ids': [p.id for p in group],
                'event_ids_embedded_in_component_ids': sorted(
                    {
                        f'p1:m{v[0]}:{v[1]}'
                        for p in group
                        if (v := re.search(r'p1_m(\d+)_([nr]\d+)', p.id))
                    }
                ),
                'component_boxes': {p.id: p.box for p in group},
                'nearest_notation_components': nearest,
                'available_vertical_space_px': read(PROTOCOL)['lyric_allocation_bottoms'][
                    system - 1
                ]
                - bounds[3],
                'agent_readability': 'PENDING_ACTUAL_NATIVE_AND_REDUCED_INSPECTION',
            }
        )
        if phase == 'baseline':
            geo = next(
                m
                for m in graph['measures']
                if m['system'] == f'sheet#1:system:{system}' and m['number'] == str(measure)
            )
            box = (
                max(130, int(geo['bounds'][0]) - 20),
                max(310, bounds[1] - 120),
                min(2430, int(geo['bounds'][2]) + 20),
                bounds[3] + 15,
            )
            picture(
                union([fixed, compose(parts, fixed.size)]).crop(box),
                f'{target} frozen baseline m{measure}: native crowded region',
            ).save(out / f'{target}-m{measure}-baseline-native.png')
            picture(
                fixed.crop(box),
                f'{target} baseline m{measure}, notation only; text separately frozen',
            ).save(out / f'{target}-m{measure}-notation-diagnostic.png')
    return result


def run(out):
    require(not out.exists(), 'Fresh output identity required')
    protocol = read(PROTOCOL)
    size = tuple(protocol['size'])
    verify_owner()
    for n, h in read(ROOT / 'docs/V4_GT16B_VALIDATION.json')['artifact_sha256'].items():
        require(sha(BASE / n) == h, 'GT16B binding mismatch: ' + n)
    directories = (
        BASE,
        GT15B,
        GT15,
        GT16,
        GT13A2,
        GT14,
        GT13A5,
        GT13A4,
        HEADER,
        GT13A3,
        GT12,
        GT14A,
        GT14B,
        GT14D,
        GT13A6,
    )
    for p in directories:
        record = read(p / 'prediction-freeze.json')
        entries = record.get('files', record.get('output_files_sha256'))
        require(isinstance(entries, dict) and entries, 'Unknown or empty freeze schema')
        require(
            all(
                sha((p.parent if p == GT12 and 'output_files_sha256' in record else p) / n) == h
                for n, h in entries.items()
            ),
            'Historical freeze mismatch: ' + str(p),
        )
    expected = read(BASE / 'pre-render-freeze.json')['source_input_hashes']
    for name, key in [
        ('source.png', 'source_sha256'),
        ('recognized.omr', 'omr_sha256'),
        ('visual-graph.json', 'graph_sha256'),
    ]:
        require(sha(SOURCE_DIR / name) == expected[key], 'Original source binding changed')
    history = {str(p): file_hashes(p) for p in directories}
    out.mkdir()
    dump(
        out / 'input-freeze.json',
        {
            'base_sha': protocol['base_sha'],
            'history': history,
            'protocol_sha256': sha(PROTOCOL),
            'producer_sha256': sha(Path(__file__)),
        },
    )
    graph = read(SOURCE_DIR / 'visual-graph.json')
    summary = []
    beamreports = []
    guards = {}
    source = converter.parse(str(BASE / 'owner-augmented-source.musicxml'))
    scoped = list(source.parts[0].getElementsByClass(stream.Measure))[:16]
    from scripts.research.gt11_complete_measure import events_of

    require(
        sum(len(events_of(m)) for m in scoped) == 77
        and sum(len(n.lyrics) for m in scoped for n in events_of(m)) == 84
        and sum(len(list(m.getElementsByClass(harmony.ChordSymbol))) for m in scoped) == 10,
        'Confirmed scope counts changed',
    )
    guards['source_roundtrip'] = validate(
        source, converter.parse(str(BASE / 'owner-augmented-source.musicxml')), 0, 'key'
    ).to_dict()
    for target, shift in [('A', -1), ('G', -3)]:
        parts, fixed = load_text(target, size)
        before = Distances(fixed)
        baseline_regions = regions(
            parts, before, fixed, graph, protocol['system_allocations_y'], target, 'baseline', out
        )
        refined_fixed, br, specs, _ = beam_layers(target, fixed, size, graph, out, parts)
        beamreports.append({'target': target, 'beams': br})
        alternatives = []
        selected = None
        for goal in protocol['optical_targets_px']:
            candidate, report = layout(
                parts,
                refined_fixed,
                protocol['system_allocations_y'],
                goal,
                lyric_bottoms=protocol['lyric_allocation_bottoms'],
            )
            if candidate is None:
                alternatives.append(report)
                candidate, report = layout(
                    parts,
                    refined_fixed,
                    protocol['system_allocations_y'],
                    goal,
                    extra=120,
                    lyric_bottoms=protocol['lyric_allocation_bottoms'],
                )
            alternatives.append(report)
            if candidate is not None:
                moved, ff = candidate
                alpha = union([ff, compose(moved, ff.size)])
                picture(
                    alpha.crop((130, 310, 2430, ff.height)), f'{target} optical target{goal}px'
                ).save(out / f'{target}-alternative-{goal}px.png')
            if goal == 6:
                selected = (candidate, report)
        require(
            selected is not None and selected[0] is not None,
            '6px layout infeasible, explicit taller canvas proposal required',
        )
        (moved, ff), layoutreport = selected
        after = Distances(ff)
        refined_regions = regions(
            moved, after, ff, graph, protocol['system_allocations_y'], target, 'refined', out
        )
        alpha = union([ff, compose(moved, ff.size)])
        baseline = Image.open(BASE / f'{target}-combined-alpha.png')
        full = picture(
            alpha.crop((130, 310, 2430, ff.height)),
            f'{target} major / adaptive6px / 77 events,10 chords,84 syllables,28 marks',
        )
        support = np.asarray(alpha) > 0
        require(
            not support[:310].any() and not support[:, :130].any() and not support[:, 2430:].any(),
            'Native preview crops ink',
        )
        full.save(out / f'{target}-refined-four-systems.png')
        info = PngInfo()
        info.add_text('Warning', WARNING)
        info.add_text(
            'Role', 'Experimental generated-notation alpha DATA mask, not source ownership'
        )
        alpha.save(out / f'{target}-refined-alpha.png', pnginfo=info)
        historical_png = Image.open(BASE / f'{target}-four-systems.png')
        frozen_body = Image.composite(
            Image.new('RGB', baseline.size, 'black'),
            Image.new('RGB', baseline.size, 'white'),
            baseline,
        ).crop((130, 310, 2430, 1800))
        require(
            historical_png.crop((0, 180, historical_png.width, historical_png.height)).tobytes()
            == frozen_body.tobytes(),
            'Frozen PNG/mask body mismatch',
        )
        original = frame_rgb(
            frozen_body, f'{target} original frozen GT16B; presentation header only rewrapped'
        )
        side(original, full, 'Frozen GT16B versus GT16C').save(
            out / f'{target}-original-vs-refined.png'
        )
        full.resize((full.width // 2, full.height // 2), Image.Resampling.LANCZOS).save(
            out / f'{target}-refined-half-display.png'
        )
        for measure in protocol['priority_measures']:
            group = [p for p in parts if p.measure == measure]
            b = (
                min(p.box[0] for p in group) - 35,
                min(p.box[1] for p in group) - 100,
                max(p.box[2] for p in group) + 35,
                max(p.box[3] for p in group) + 35,
            )
            comparison = side(
                picture(baseline.crop(b), 'BEFORE'),
                picture(alpha.crop(b), 'AFTER'),
                'Native music/text region',
            )
            comparison.save(out / f'{target}-m{measure}-optical-detail.png')
            if target == 'G' and measure == 13:
                comparison.save(out / 'G-m13-lyric-clearance-detail.png')
        for k, (old, new, spec) in enumerate(specs):
            b = (
                min(old.box[0], new.box[0]) - 12,
                min(old.box[1], new.box[1]) - 18,
                max(old.box[2], new.box[2]) + 12,
                max(old.box[3], new.box[3]) + 35,
            )
            detail = side(
                picture(baseline.crop(b), 'Frozen beam'),
                picture(alpha.crop(b), 'Supersampled beam'),
                'Native beam comparison',
            )
            detail.save(out / f'{target}-diagonal-beam-{k}-before-after.png')
            if target == 'G' and k == 1:
                detail.save(out / 'diagonal-beam-before-after.png')
        score = copy.deepcopy(source)
        ts = transpose_score(score, shift, 'key')
        score.write('musicxml', fp=str(out / f'{target}-semantic.musicxml'))
        disk = converter.parse(str(out / f'{target}-semantic.musicxml'))
        frozen = converter.parse(str(BASE / f'{target}-transposed.musicxml'))
        guards[target] = {
            'in_memory': validate(source, score, shift, 'key', ts).to_dict(),
            'serialized': validate(source, disk, shift, 'key', ts).to_dict(),
        }
        require(
            all(g['ok'] for g in guards[target].values())
            and music_signature(disk) == music_signature(frozen)
            and full_lyric_signature(disk) == full_lyric_signature(frozen)
            and repeat_signature(disk) == repeat_signature(frozen),
            'Semantic guard/signature failed',
        )
        require(
            [
                [c.figure for c in p.recurse().getElementsByClass(harmony.ChordSymbol)]
                for p in disk.parts
            ]
            == [
                [c.figure for c in p.recurse().getElementsByClass(harmony.ChordSymbol)]
                for p in frozen.parts
            ],
            'Chord semantics changed',
        )
        summary.append(
            {
                'target': target,
                'before': baseline_regions,
                'after': refined_regions,
                'alternatives': alternatives,
                'selected_layout': layoutreport,
                'improved_regions': sum(
                    a['center_distance_px'] > b['center_distance_px']
                    for a, b in zip(refined_regions, baseline_regions)
                ),
                'unresolved_below6px': sum(a['center_distance_px'] < 6 for a in refined_regions),
                'beam_replacements': sum(b['selected_scale'] > 1 for b in br),
                'text_count': 112,
                'syllables': 84,
                'marks': 28,
                'unchanged_events': 77,
                'chords': 10,
                'note_anchor_max_residual_px': 0.5,
                'notehead_geometry': 'UNCHANGED_COMPONENT_BYTES_OR_LOSSLESS_SYSTEM_TRANSLATION',
                'source_staff_center_y': [s['lines'][2][0][1] for s in graph['staves'][:4]],
                'system_offsets': layoutreport['system_offsets'],
                'old_canvas_height': 1800,
                'new_canvas_height': ff.height,
                'pixel_coverage': 'NOT_PHYSICAL_PAGE_COMPLETE',
                'independent_musician_reviews': 0,
            }
        )
    require(guards['source_roundtrip']['ok'], 'Source guard failed')
    dump(out / 'optical-spacing-metrics.json', summary)
    dump(out / 'beam-quality-metrics.json', beamreports)
    dump(out / 'semantic-integrity.json', guards)
    require(
        all(file_hashes(Path(p)) == h for p, h in history.items()), 'Historical artifact mutation'
    )
    dump(
        out / 'preservation-verification.json',
        {
            'history_unchanged': True,
            'source_sha256': sha(SOURCE_DIR / 'source.png'),
            'owner_records_unchanged': True,
            'withheld_SIG_ids_unchanged': True,
            'repeat_playback_unresolved': True,
        },
    )
    dump(
        out / 'prediction-freeze.json',
        {
            'files': file_hashes(out),
            'phase': 'BEFORE_AGENT_VISUAL_INSPECTION_NO_TARGET_REFERENCE_ACCESS',
        },
    )


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    run(p.parse_args().out)
