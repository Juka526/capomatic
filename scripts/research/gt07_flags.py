"""One isolated upward eighth flag on a new canvas; not a complete measure."""

import argparse
import json
import math
from fractions import Fraction
from pathlib import Path
import shutil
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

from scripts.research.gt04_visual import HEAD, panel_label
from scripts.research.gt05_raster_anchor import glyph
from scripts.research.gt06_extended import contacts, measure_anchor, semantic_note
from scripts.research.paired_ground_truth_01 import sha, dump, file_hashes, line_y
from scripts.research.ground_truth_02 import verify_inputs

FLAG = chr(0x1D16E)
DESIGN = Path(__file__).resolve().parents[2] / 'docs/V4_GT07_FLAG_PREREGISTRATION.json'


def flag_evidence(row, move, graph, note, *, expected_pitch=None):
    reasons = []
    connected = {k: ids for k, ids in move['connected_symbols']}
    if (
        row['status'] != 'MATCHED'
        or row.get('chord_size') != 1
        or row.get('chord_continuation')
        or Fraction(row['duration']) != Fraction(1, 2)
    ):
        reasons.append('UNSUPPORTED_EVENT')
    if any(k not in {'head', 'head-chord', 'stem', 'flag', 'ledger'} for k in connected):
        reasons.append('UNSUPPORTED_CONNECTED_SYMBOL')
    if (
        not note.isNote
        or note.nameWithOctave != (row['pitch'] if expected_pitch is None else expected_pitch)
        or note.duration.type != 'eighth'
        or note.duration.dots
        or note.duration.tuplets
        or note.duration.isGrace
        or note.stemDirection != 'up'
        or note.tie
        or note.articulations
        or note.expressions
        or len(note.beams)
    ):
        reasons.append('UNSUPPORTED_SEMANTICS_OR_DIRECTION')
    owned = {i for ids in connected.values() for i in ids}
    if any(
        (r['source'] in owned or r['target'] in owned)
        and any(k in r['kind'] for k in ['slur', 'articulation', 'fermata'])
        for r in graph['relations']
    ):
        reasons.append('UNSUPPORTED_ATTACHMENT')
    stems = connected.get('stem', [])
    flags = connected.get('flag', [])
    edges = []
    if len(stems) != 1 or len(flags) != 1:
        reasons.append('INCOMPLETE_FLAG_GROUP')
    else:
        for kind, source in [('head-stem', row['symbol_id']), ('flag-stem', flags[0])]:
            rs = [
                r
                for r in graph['relations']
                if r['kind'] == kind and r['source'] == source and r['target'] == stems[0]
            ]
            if len(rs) != 1 or (
                kind == 'head-stem' and dict(rs[0]['attributes']).get('head-side') != 'RIGHT'
            ):
                reasons.append('MISSING_OR_WRONG_TYPED_RELATION')
            else:
                edges.append(rs[0]['id'])
        if graph['symbols'][flags[0]]['shape'] != 'FLAG_1':
            reasons.append('UNSUPPORTED_FLAG_COUNT_OR_DIRECTION')
        for ident in [row['symbol_id'], stems[0], flags[0]]:
            g = graph['symbols'][ident]['geometry']
            if not g['valid'] or not g['bbox'] or any(not math.isfinite(v) for v in g['bbox']):
                reasons.append('INVALID_GEOMETRY')
        if len(graph['symbols'][stems[0]]['geometry']['line']) != 2:
            reasons.append('STEM_LINE_MISSING')
    return sorted(set(reasons)), sorted(edges)


def select(events, moves, graph, source):
    decisions = []
    rows = sorted(
        [
            r
            for r in events
            if r['kind'] == 'NOTE' and 'flag' in dict(moves[r['id']]['connected_symbols'])
        ],
        key=lambda r: (min(r['printed_measures']), Fraction(r['local_offset']), r['id']),
    )
    for row in rows:
        reasons, edges = flag_evidence(row, moves[row['id']], graph, semantic_note(source, row))
        decisions.append({'id': row['id'], 'measure': row['printed_measures'], 'blockers': reasons})
        if not reasons:
            return row, edges, decisions
    raise ValueError('FLAG_VISUAL_POC_BLOCKED: no eligible supported source flag')


def flag_mask(size, font, tip, units, scale, *, char=FLAG):
    """Explicit glyph-specific attachment; do not treat bbox center as a stem tip."""
    if not all(math.isfinite(v) for v in tip):
        raise ValueError('Nonfinite stem tip')
    tile, _ = glyph(
        (6 * font.size, 6 * font.size), font, char, (3 * font.size, 3 * font.size), units, scale
    )
    bitmap = tile.crop(tile.getbbox())
    pixels = np.argwhere(np.asarray(bitmap) > 0)
    attach_y = int(pixels[pixels[:, 1] == 0, 0].min())
    anchor = (0, attach_y)
    center = (tip[0] + (bitmap.width - 1) / 2, tip[1] + (bitmap.height - 1) / 2 - attach_y)
    mask, info = glyph(size, font, char, center, units, scale)
    box = mask.getbbox()
    actual = (box[0], box[1] + attach_y)
    info.update(
        {
            'flag_attachment_local': anchor,
            'requested_stem_tip': tip,
            'actual_flag_attachment': actual,
            'flag_attachment_residual': [actual[i] - tip[i] for i in [0, 1]],
            'flag_count': 1,
            'flag_glyph': f'U+{ord(char):05X}',
        }
    )
    return mask, info


def prepare(gt01, gt02, gt06, out):
    from music21 import converter
    from backend.omr_v3.music_guard import validate

    if out.exists() or any(
        r.resolve() == out.resolve() or r.resolve() in out.resolve().parents
        for r in [gt01, gt02, gt06]
    ):
        raise ValueError('New isolated input directory required')
    verify_inputs(gt01)
    b = gt01 / 'predictions/baseline-exec'
    frozen = json.loads((gt06 / 'gt06-output/prototype-freeze.json').read_text())
    now = file_hashes(gt06 / 'gt06-output')
    now.pop('prototype-freeze.json')
    if now != frozen['files']:
        raise ValueError('GT06 changed')
    graph = json.loads((b / 'source/visual-graph.json').read_text())
    plan = json.loads((b / 'A/plan.json').read_text())
    events = json.loads((gt02 / 'note-correspondence-diagnostic.json').read_text())['events']['Bb']
    moves = {n['semantic_id']: n for n in plan['note_moves']}
    source = converter.parse(str(b / 'source/recognized.musicxml'))
    row, edges, decisions = select(events, moves, graph, source)
    guards = {}
    for key, shift in [('A', -1), ('G', -3)]:
        target = converter.parse(str(b / key / 'transposed.musicxml'))
        guards[key] = validate(source, target, shift, 'key').to_dict()
        if not guards[key]['ok']:
            raise ValueError('Full V3 guard failed')
        note = semantic_note(target, row)
        anchors = {
            n['semantic_id']: n
            for n in json.loads((b / key / 'track-b-geometry.json').read_text())['notes']
        }
        a = anchors[row['id']]
        if flag_evidence(row, moves[row['id']], graph, note, expected_pitch=a['target_pitch'])[0]:
            raise ValueError('Target semantic flag evidence mismatch')
        if note.nameWithOctave != a['target_pitch']:
            raise ValueError('Target pitch mismatch')
        row.setdefault('frozen', {})[key] = a
    connected = dict(moves[row['id']]['connected_symbols'])
    stem = graph['symbols'][connected['stem'][0]]
    staff = next(
        s for s in graph['staves'] if s['id'] == graph['symbols'][row['symbol_id']]['staff']
    )
    measure = row['printed_measures'][0]
    reg = json.loads((gt02 / 'measure-registration.json').read_text())['pages']['Bb']['measures']
    region = next(r for r in reg if r['printed_measure'] == measure)
    out.mkdir(parents=True)
    shutil.copyfile(b / 'source/source.png', out / 'source.png')
    spec = {
        'event': row,
        'stem': stem,
        'flag': graph['symbols'][connected['flag'][0]],
        'relation_ids': edges,
        'decisions': decisions,
        'staff': staff,
        'left': region['left']['x'],
        'right': region['right']['x'],
        'measure': measure,
        'guards': guards,
        'protected': graph['text_protected_regions'],
        'source_sha256': sha(out / 'source.png'),
        'protocol_sha256': sha(DESIGN),
        'source_omr_sha256': sha(b / 'source/recognized.omr'),
        'source_graph_sha256': sha(b / 'source/visual-graph.json'),
        'semantic_hashes': {k: sha(b / k / 'transposed.musicxml') for k in ['A', 'G']},
        'excluded_events': [
            r['id'] for r in events if r['printed_measures'] == [measure] and r['id'] != row['id']
        ],
    }
    dump(out / 'selection.json', spec)
    return spec


def synthetic_controls(font_path, out):
    if out.exists():
        raise ValueError('New source-free control directory required')
    if sha(font_path) != json.loads(DESIGN.read_text())['font_sha256']:
        raise ValueError('Font changed')
    tt = TTFont(font_path)
    units = {
        char: tuple(
            getattr(tt['glyf'][tt.getBestCmap()[ord(char)]], k)
            for k in ['xMin', 'yMin', 'xMax', 'yMax']
        )
        for char in [HEAD, FLAG]
    }
    font = ImageFont.truetype(str(font_path), 94)
    rows = []
    for phase in [0, 0.125, 0.5, 0.875]:
        xy = (180 + phase, 230 + phase)
        head, _ = glyph((512, 512), font, HEAD, xy, units[HEAD], 94 / tt['head'].unitsPerEm)
        pix = np.argwhere(np.asarray(head) > 0)
        edge = int(pix[:, 1].max() - 1)
        tip = (edge, 140)
        flag, info = flag_mask(head.size, font, tip, units[FLAG], 94 / tt['head'].unitsPerEm)
        stem = Image.new('L', head.size)
        ImageDraw.Draw(stem).line(
            [tip, (edge, float(np.median(pix[pix[:, 1] == edge, 0])))], fill=255, width=2
        )
        shared = lambda a, b: int(np.count_nonzero((np.asarray(a) > 0) & (np.asarray(b) > 0)))
        residual = measure_anchor(head, xy)['measured_anchor_residual']
        rows.append(
            {
                'phase': phase,
                'head_residual': residual,
                'head_stem_contact': shared(head, stem),
                'stem_flag_contact': shared(stem, flag),
                'head_flag_collision': shared(head, flag),
                'flag_attachment_residual': info['flag_attachment_residual'],
            }
        )
    result = {
        'rows': rows,
        'passed': all(
            max(abs(v) for v in r['head_residual']) <= 0.5
            and r['head_stem_contact'] > 0
            and r['stem_flag_contact'] > 0
            and r['head_flag_collision'] == 0
            and r['flag_attachment_residual'] == [0, 0]
            for r in rows
        ),
        'font_sha256': sha(font_path),
        'protocol_sha256': sha(DESIGN),
        'glyph_algorithm_sha256': sha(Path(__file__).with_name('gt05_raster_anchor.py')),
        'code_sha256': sha(Path(__file__)),
    }
    dump(out / 'flag-controls.json', result)
    return result


def render(inputs, font_path, out, controls):
    from music21 import pitch

    if out.exists() or inputs.resolve() in out.resolve().parents:
        raise ValueError('New output directory required')
    if controls is None:
        raise ValueError('Source-free flag controls required')
    gate = json.loads((controls / 'flag-controls.json').read_text())
    if (
        not gate['passed']
        or gate['font_sha256'] != sha(font_path)
        or gate['protocol_sha256'] != sha(DESIGN)
        or gate['code_sha256'] != sha(Path(__file__))
        or gate['glyph_algorithm_sha256'] != sha(Path(__file__).with_name('gt05_raster_anchor.py'))
    ):
        raise ValueError('Source-free flag controls failed or changed')
    spec = json.loads((inputs / 'selection.json').read_text())
    design = json.loads(DESIGN.read_text())
    if (
        spec['protocol_sha256'] != sha(DESIGN)
        or sha(font_path) != design['font_sha256']
        or sha(inputs / 'source.png') != spec['source_sha256']
    ):
        raise ValueError('Frozen inputs changed')
    if not all(g['ok'] for g in spec['guards'].values()):
        raise ValueError('Full integrity required')
    start = time.monotonic()
    source = Image.open(inputs / 'source.png')
    size = source.size
    event = spec['event']
    staff = spec['staff']
    inter = staff['interline']
    left, right = spec['left'], spec['right']
    ident = event['id']
    viewport = (
        math.floor(left) - 8,
        math.floor(staff['lines'][0][0][1]) - 130,
        math.ceil(right) + 9,
        math.ceil(staff['lines'][-1][0][1]) + 140,
    )
    tt = TTFont(font_path)
    units = {
        char: tuple(
            getattr(tt['glyf'][tt.getBestCmap()[ord(char)]], k)
            for k in ['xMin', 'yMin', 'xMax', 'yMax']
        )
        for char in [HEAD, FLAG]
    }
    upm = tt['head'].unitsPerEm
    fontsize = round(1.25 * inter * upm / (units[HEAD][2] - units[HEAD][0]))
    font = ImageFont.truetype(str(font_path), fontsize)
    protected = np.zeros((size[1], size[0]), bool)
    for r in spec['protected']:
        x0, y0, x1, y1 = r['bbox']
        protected[
            max(0, math.floor(y0)) : min(size[1], math.ceil(y1)),
            max(0, math.floor(x0)) : min(size[0], math.ceil(x1)),
        ] = True
    out.mkdir(parents=True)
    scope = f'm{spec["measure"]} offset {event["local_offset"]} ONLY; one eighth flag'
    panels = [panel_label(source.crop(viewport), 'Unchanged Bb source; target ' + scope)]
    panels[0].save(out / 'original-bb.png')
    metrics = []
    for key in ['A', 'G']:
        a = event['frozen'][key]
        x = a['detected_head_x']
        y = a['absolute_target_staff_y']
        p = pitch.Pitch(a['target_pitch'])
        pos = 35 - p.diatonicNoteNum
        expected = line_y(staff['lines'][2], x) + pos * inter / 2
        if abs(y - expected) > 1e-8:
            raise ValueError('Semantic target y mismatch')
        alter = {'A': {'F': 1, 'C': 1, 'G': 1}, 'G': {'F': 1}}[key].get(p.step, 0)
        if (p.accidental.alter if p.accidental else 0) != alter:
            raise ValueError('Unsupported explicit accidental')
        parts = {}
        sf = Image.new('L', size)
        d = ImageDraw.Draw(sf)
        for line in staff['lines']:
            d.line(
                [(left, line_y(line, left))]
                + [tuple(p) for p in line if left < p[0] < right]
                + [(right, line_y(line, right))],
                fill=255,
                width=2,
            )
        parts['staff'] = sf
        bar = Image.new('L', size)
        d = ImageDraw.Draw(bar)
        for bx in [left, right]:
            d.line(
                [(bx, line_y(staff['lines'][0], bx)), (bx, line_y(staff['lines'][-1], bx))],
                fill=255,
                width=2,
            )
        parts['bar'] = bar
        head, info = glyph(size, font, HEAD, (x, y), units[HEAD], fontsize / upm)
        info.update(measure_anchor(head, (x, y)))
        parts['head'] = head
        pix = np.argwhere(np.asarray(head) > 0)
        edge = int(pix[:, 1].max() - 1)
        attach = float(np.median(pix[pix[:, 1] == edge, 0]))
        source_tip = min(p[1] for p in spec['stem']['geometry']['line'])
        length = max(3.5 * inter, a['corrected_semantic_source_staff_y'] - source_tip)
        tip = (edge, math.floor(y - length + 0.5))
        stem = Image.new('L', size)
        ImageDraw.Draw(stem).line([(edge, attach), tip], fill=255, width=2)
        parts['stem'] = stem
        flag, flag_info = flag_mask(size, font, tip, units[FLAG], fontsize / upm)
        parts['flag'] = flag
        ledger = Image.new('L', size)
        d = ImageDraw.Draw(ledger)
        positions = (
            range(6, pos + 1, 2) if pos >= 6 else range(-6, pos - 1, -2) if pos <= -6 else []
        )
        for q in positions:
            ly = line_y(staff['lines'][2], x) + q * inter / 2
            d.line([(x - 0.875 * inter, ly), (x + 0.875 * inter, ly)], fill=255, width=2)
        if ledger.getbbox():
            parts['ledger'] = ledger
        allowed = {
            frozenset(pair)
            for pair in [('head', 'stem'), ('stem', 'flag'), ('head', 'ledger'), ('stem', 'ledger')]
        }
        hits = contacts(parts, allowed)
        music = np.maximum.reduce(
            [np.asarray(v) for k, v in parts.items() if k not in {'staff', 'bar'}]
        )
        ink = np.maximum.reduce([np.asarray(v) for v in parts.values()])
        bbox = Image.fromarray(ink).getbbox()
        clipped = (
            not bbox
            or bbox[0] < max(0, viewport[0])
            or bbox[1] < max(0, viewport[1])
            or bbox[2] > min(size[0], viewport[2])
            or bbox[3] > min(size[1], viewport[3])
        )
        shared = lambda aa, bb: int(np.count_nonzero((np.asarray(aa) > 0) & (np.asarray(bb) > 0)))
        hc = shared(head, stem)
        fc = shared(flag, stem)
        hf = shared(head, flag)
        pc = int(np.count_nonzero((music > 0) & protected))
        pd = int(
            np.count_nonzero((music > 0) & protected & (np.asarray(source.convert('L')) < 127))
        )
        maxres = max(abs(v) for v in info['measured_anchor_residual'])
        unexpected = [h for h in hits if not h['intentional']]
        record = {
            'measure': spec['measure'],
            'target': key,
            'viewport_page_coordinates': viewport,
            'events': [
                {
                    'semantic_id': ident,
                    'kind': 'NOTE',
                    'duration': event['duration'],
                    'source_pitch': a['source_pitch'],
                    'target_pitch': a['target_pitch'],
                    'physical_detected_center': [x, a['detected_head_y']],
                    'corrected_semantic_source_y': a['corrected_semantic_source_staff_y'],
                    'target_semantic_y': y,
                    **info,
                }
            ],
            'flag': flag_info,
            'head_stem_contact_pixels': hc,
            'stem_flag_contact_pixels': fc,
            'head_flag_collision_pixels': hf,
            'flag_count': 1,
            'semantic_duration': '1/2',
            'stem_direction': 'up',
            'stem_tip': tip,
            'stem_length_rule_px': length,
            'max_notehead_raster_anchor_residual': maxres,
            'requested_x_deviation': 0,
            'target_pitch_y_deviation': y - expected,
            'staff_geometry_deviation': 0,
            'measure_boundary_deviation': 0,
            'missing_semantic_events': 0,
            'duplicate_semantic_events': 0,
            'ink_intersections': hits,
            'unexpected_ink_collision_pairs': len(unexpected),
            'protected_envelope_contact_pixels': pc,
            'protected_source_dark_contact_pixels': pd,
            'confirmed_text_contact_pixels': 'UNKNOWN',
            'clipping': bool(clipped),
            'checks_pass': maxres <= 0.5
            and hc > 0
            and fc > 0
            and hf == 0
            and not unexpected
            and not clipped
            and pc == 0,
        }
        metrics.append(record)
        Image.fromarray(ink).save(out / f'{key}-notation-alpha.png')
        Image.fromarray(music).save(out / f'{key}-music-only-alpha.png')
        panel = panel_label(
            Image.fromarray(255 - ink).convert('RGB').crop(viewport), key + ' major; ' + scope
        )
        panel.save(out / ('predicted-a.png' if key == 'A' else 'predicted-g.png'))
        panels.append(panel)
    sheet = Image.new(
        'RGB', (sum(p.width for p in panels) + 24, max(p.height for p in panels)), 'white'
    )
    cx = 0
    for panel in panels:
        sheet.paste(panel, (cx, 0))
        cx += panel.width + 12
    sheet.save(out / 'comparison-contact-sheet.png')
    raw = source.crop(viewport)
    equal = panels[0].crop((0, 84, raw.width, 84 + raw.height)).tobytes() == raw.tobytes()
    result = {
        'decision': (
            'FLAG_VISUAL_POC_PASS'
            if equal and all(m['checks_pass'] for m in metrics)
            else 'FLAG_VISUAL_POC_NEEDS_REFINEMENT'
        ),
        'source_sha256': spec['source_sha256'],
        'selection_sha256': sha(inputs / 'selection.json'),
        'font_sha256': sha(font_path),
        'glyph_algorithm_sha256': sha(Path(__file__).with_name('gt05_raster_anchor.py')),
        'full_integrity': spec['guards'],
        'source_crop_pixel_equality': equal,
        'lyric_composite': False,
        'metrics': metrics,
        'seconds': time.monotonic() - start,
        'peak_memory': 'NOT_MEASURED',
    }
    dump(out / 'rendering-metrics.json', result)
    dump(
        out / 'rendering-limitations.json',
        {
            'scope': 'SINGLE_NOTE_NOT_FULL_MEASURE',
            'excluded_events': spec['excluded_events'],
            'unsupported': [
                'double flags',
                'downward flags',
                'curves',
                'explicit accidentals',
                'moving attachments',
                'full chords',
                'lyric composition',
                'standalone clef/key/time',
            ],
            'chords': 'INCOMPLETE: source 7 harmonies / 24 coordinator candidates, no new OCR',
            'human_labels': 0,
            'edit_authorization': 'NONE',
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


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['prepare', 'controls', 'render'])
    p.add_argument('--inputs', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--controls', type=Path)
    a = p.parse_args()
    if a.mode == 'prepare':
        r = prepare(
            Path('/private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output'),
            Path('/private/tmp/capomatic-v4-ground-truth-02/ground-truth-02-output'),
            Path('/private/tmp/capomatic-v4-gt06-extended'),
            a.out,
        )
        print(r['event']['id'])
    elif a.mode == 'controls':
        r = synthetic_controls(
            Path('/private/tmp/capomatic-v4-gt04-visual/ground-truth-04-output/font/FreeSerif.ttf'),
            a.out,
        )
        print({'passed': r['passed']})
    else:
        r = render(
            a.inputs,
            Path('/private/tmp/capomatic-v4-gt04-visual/ground-truth-04-output/font/FreeSerif.ttf'),
            a.out,
            a.controls,
        )
        print(r['decision'])
