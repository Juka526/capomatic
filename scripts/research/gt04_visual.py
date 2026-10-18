"""Source-selected, font-anchored notation on NEW canvases, never source editing."""

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

from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes, line_y

LABEL = 'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE'
WARNING = 'INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING'
HEAD = chr(0x1D158)
REST = chr(0x1D13D)


def choose(regions, events, moves, graph):
    """Earliest two supported measures; preserve rejection evidence, no result-based swap."""
    selected, decisions = [], []
    for region in regions:
        number = region['printed_measure']
        rows = [r for r in events if r['printed_measures'] == [number]]
        notes = [r for r in rows if r['kind'] == 'NOTE']
        reasons = []
        if region['within_system'] == 1:
            reasons.append('SYSTEM_INITIAL_CONTEXT_NOT_SUPPORTED')
        if region['repeat_ending_context']['literal'] != 'No coordinator-noted ending mark':
            reasons.append('REPEAT_OR_ENDING_CONTEXT_NOT_SUPPORTED')
        if not notes or len(rows) != 4 or {r['local_offset'] for r in rows} != {'0', '1', '2', '3'}:
            reasons.append('NOT_COMPLETE_QUARTER_STREAM')
        if any(
            r['status'] != 'MATCHED'
            or Fraction(r['duration']) != 1
            or r.get('chord_continuation')
            or r.get('chord_size', 1) != 1
            for r in rows
        ):
            reasons.append('UNSUPPORTED_RHYTHM_OR_OWNERSHIP')
        owned = set()
        for note in notes:
            if note['id'] not in moves:
                reasons.append('MISSING_FROZEN_MOVE')
                continue
            for kind, ids in moves[note['id']]['connected_symbols']:
                owned.update(ids)
                if kind not in {'head', 'head-chord', 'stem', 'ledger'}:
                    reasons.append('UNSUPPORTED_CONNECTED_' + kind)
        for relation in graph['relations']:
            if (relation['source'] in owned or relation['target'] in owned) and any(
                word in relation['kind'] for word in ['slur', 'articulation', 'fermata']
            ):
                reasons.append('UNSUPPORTED_MOVING_ATTACHMENT')
        decisions.append({'printed_measure': number, 'blockers': sorted(set(reasons))})
        if not reasons:
            selected.append(number)
        if len(selected) == 2:
            break
    return selected, decisions


def prepare(gt01, gt02, out):
    from music21 import converter, stream, harmony
    from backend.omr_v3.music_guard import validate
    from scripts.research.ground_truth_02 import verify_inputs

    if out.exists():
        raise ValueError('New render-input directory required')
    for root in [gt01, gt02]:
        if root.resolve() == out.resolve() or root.resolve() in out.resolve().parents:
            raise ValueError('Output inside immutable evidence')
    binding = verify_inputs(gt01)
    baseline = gt01 / 'predictions/baseline-exec'
    graph = json.loads((baseline / 'source/visual-graph.json').read_text())
    registration = json.loads((gt02 / 'measure-registration.json').read_text())['pages']['Bb']
    events = json.loads((gt02 / 'note-correspondence-diagnostic.json').read_text())['events']['Bb']
    source = converter.parse(str(baseline / 'source/recognized.musicxml'))
    source_measures = list(source.parts[0].getElementsByClass(stream.Measure))
    plans = {k: json.loads((baseline / k / 'plan.json').read_text()) for k in ['A', 'G']}
    anchors = {
        k: {
            n['semantic_id']: n
            for n in json.loads((baseline / k / 'track-b-geometry.json').read_text())['notes']
        }
        for k in ['A', 'G']
    }
    moves = {n['semantic_id']: n for n in plans['A']['note_moves']}
    selected, decisions = choose(registration['measures'], events, moves, graph)
    if len(selected) != 2:
        raise ValueError('No two eligible measures; record blockers, do not reselect')
    guards = {}
    for key, interval in [('A', -1), ('G', -3)]:
        target = converter.parse(str(baseline / key / 'transposed.musicxml'))
        guards[key] = validate(source, target, interval, 'key').to_dict()
        if not guards[key]['ok']:
            raise ValueError('Unchanged full guard failed')
    out.mkdir(parents=True)
    shutil.copyfile(baseline / 'source/source.png', out / 'source.png')
    excerpts = []
    for number in selected:
        region = next(m for m in registration['measures'] if m['printed_measure'] == number)
        rows = [r for r in events if r['printed_measures'] == [number]]
        staff_ids = {graph['symbols'][r['symbol_id']]['staff'] for r in rows}
        if len(staff_ids) != 1:
            raise ValueError('Unknown staff lineage')
        staff = next(s for s in graph['staves'] if s['id'] in staff_ids)
        semantic = list(source_measures[number - 1].recurse().notesAndRests)
        semantic = [n for n in semantic if not isinstance(n, harmony.ChordSymbol)]
        if len(semantic) != 4 or any(
            n.duration.type != 'quarter'
            or n.duration.dots
            or n.duration.isGrace
            or n.duration.tuplets
            for n in semantic
        ):
            raise ValueError('Unsupported notation; no replacement excerpt')
        for row in rows:
            if row['kind'] == 'NOTE':
                row['frozen'] = {k: anchors[k][row['id']] for k in ['A', 'G']}
                if any('blocked' in v for v in row['frozen'].values()):
                    raise ValueError('Unresolved target coordinate')
        excerpts.append(
            {
                'number': number,
                'system': region['system'],
                'left': region['left']['x'],
                'right': region['right']['x'],
                'staff': staff,
                'events': rows,
                'source_key_context': 'Bb major; G clef',
                'recognized_harmonies': [
                    str(c.figure)
                    for c in source_measures[number - 1]
                    .recurse()
                    .getElementsByClass(harmony.ChordSymbol)
                ],
            }
        )
    dump(
        out / 'selection.json',
        {
            'binding': binding,
            'selected': selected,
            'decisions': decisions,
            'source_sha256': sha(out / 'source.png'),
            'guards': guards,
            'excerpts': excerpts,
            'protected': graph['text_protected_regions'],
            'reference_notation_used_for_selection': False,
            'human_verified': False,
        },
    )
    return selected


def glyph(mask_size, font, char, xy, units, scale):
    """Font outline bbox-center anchor; baseline is explicit, not a detected head center."""
    if not all(math.isfinite(v) for v in (*xy, *units, scale)) or scale <= 0:
        raise ValueError('Invalid/nonfinite glyph geometry')
    x0, y0, x1, y1 = units
    offset = ((x0 + x1) * scale / 2, (y0 + y1) * scale / 2)
    baseline = (xy[0] - offset[0], xy[1] + offset[1])
    mask = Image.new('L', mask_size)
    ImageDraw.Draw(mask).text(baseline, char, font=font, fill=255, anchor='ls', stroke_width=0)
    box = mask.getbbox()
    if box is None:
        raise ValueError('Missing rendered glyph')
    center = ((box[0] + box[2] - 1) / 2, (box[1] + box[3] - 1) / 2)
    return mask, {
        'font_outline_anchor': list(xy),
        'baseline': baseline,
        'rendered_bounds': box,
        'raster_ink_bbox_center': center,
        'anchor_residual': [center[i] - xy[i] for i in [0, 1]],
    }


def ink_intersections(parts):
    result = []
    for (a, ma), (b, mb) in itertools.combinations(parts.items(), 2):
        overlap = np.count_nonzero((np.asarray(ma) > 0) & (np.asarray(mb) > 0))
        if overlap:
            same_note = a.rsplit(':', 1)[0] == b.rsplit(':', 1)[0]
            intentional = 'staff' in [a, b] or (
                same_note and any(k in a or k in b for k in ['stem', 'ledger'])
            )
            # Barline-to-staff endpoints are structural by design.
            intentional = bool(intentional or ('bar' in [a, b] and 'staff' in [a, b]))
            result.append(
                {'a': a, 'b': b, 'pixels': int(overlap), 'intentional_contact': intentional}
            )
    return result


def panel_label(image, title):
    canvas = Image.new('RGB', (max(image.width, 720), image.height + 84), 'white')
    d = ImageDraw.Draw(canvas)
    for y, text in [
        (4, LABEL),
        (23, WARNING),
        (42, title),
        (61, 'MUSIC-ONLY contextual layer; lyrics remain in untouched original panel'),
    ]:
        d.text((8, y), text, fill='black', font_size=14)
    canvas.paste(image, (0, 84))
    return canvas


def render(inputs, font_path, out, *, glyph_renderer=None, parts_observer=None):
    from fontTools.ttLib import TTFont
    from music21 import pitch

    place_glyph = glyph if glyph_renderer is None else glyph_renderer

    if (
        out.exists()
        or inputs.resolve() in out.resolve().parents
        or inputs.resolve() == out.resolve()
    ):
        raise ValueError('New prototype output directory required')
    spec = json.loads((inputs / 'selection.json').read_text())
    if sha(inputs / 'source.png') != spec['source_sha256']:
        raise ValueError('Source changed')
    start = time.monotonic()
    source = Image.open(inputs / 'source.png')
    size = source.size
    tt = TTFont(font_path)
    cmap = tt.getBestCmap()
    upm = tt['head'].unitsPerEm
    bounds = {}
    for char in [HEAD, REST]:
        if ord(char) not in cmap:
            raise ValueError('RENDER_BLOCKED_UNSUPPORTED_NOTATION: font lacks glyph')
        g = tt['glyf'][cmap[ord(char)]]
        bounds[char] = (g.xMin, g.yMin, g.xMax, g.yMax)
    out.mkdir(parents=True)
    rendered = {'original': [], 'A': [], 'G': []}
    metrics = []
    for excerpt in spec['excerpts']:
        staff = excerpt['staff']
        inter = staff['interline']
        left = excerpt['left']
        right = excerpt['right']
        viewport = (
            math.floor(left) - 8,
            math.floor(staff['lines'][0][0][1]) - 130,
            math.ceil(right) + 9,
            math.ceil(staff['lines'][-1][0][1]) + 140,
        )
        raw = source.crop(viewport)
        rendered['original'].append(
            panel_label(raw, f'Unchanged Bb source, printed {excerpt["number"]}')
        )
        for key in ['A', 'G']:
            parts = {}
            head_rows = []
            sf = Image.new('L', size)
            draw = ImageDraw.Draw(sf)
            for poly in staff['lines']:
                points = (
                    [(left, line_y(poly, left))]
                    + [tuple(p) for p in poly if left < p[0] < right]
                    + [(right, line_y(poly, right))]
                )
                draw.line(points, fill=255, width=2)
            parts['staff'] = sf
            bars = Image.new('L', size)
            d = ImageDraw.Draw(bars)
            for x in [left, right]:
                d.line(
                    [(x, line_y(staff['lines'][0], x)), (x, line_y(staff['lines'][-1], x))],
                    fill=255,
                    width=2,
                )
            parts['bar'] = bars
            fontsize = round(1.25 * inter * upm / (bounds[HEAD][2] - bounds[HEAD][0]))
            font = ImageFont.truetype(str(font_path), fontsize)
            scale = fontsize / upm
            for event in excerpt['events']:
                ident = event['id']
                if event['kind'] == 'REST':
                    b = event['bbox']
                    xy = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
                    parts[ident + ':rest'], info = place_glyph(
                        size, font, REST, xy, bounds[REST], scale
                    )
                    head_rows.append(
                        {
                            'semantic_id': ident,
                            'kind': 'REST',
                            'duration': event['duration'],
                            **info,
                        }
                    )
                    continue
                frozen = event['frozen'][key]
                x = frozen['detected_head_x']
                y = frozen['absolute_target_staff_y']
                target = pitch.Pitch(frozen['target_pitch'])
                staff_pos = 35 - target.diatonicNoteNum
                expected = line_y(staff['lines'][2], x) + staff_pos * inter / 2
                if abs(y - expected) > 1e-8:
                    raise ValueError(
                        'Frozen target does not satisfy semantic pitch-to-staff contract'
                    )
                # This run supports in-key notes only: never silently omit required accidentals.
                expected_alter = {'A': {'F': 1, 'C': 1, 'G': 1}, 'G': {'F': 1}}[key].get(
                    target.step, 0
                )
                if (target.accidental.alter if target.accidental else 0) != expected_alter:
                    raise ValueError('RENDER_BLOCKED_UNSUPPORTED_NOTATION: accidental required')
                head, info = place_glyph(size, font, HEAD, (x, y), bounds[HEAD], scale)
                parts[ident + ':head'] = head
                pixels = np.argwhere(np.asarray(head) > 0)
                up = staff_pos > 0
                edge = int(pixels[:, 1].max() - 1 if up else pixels[:, 1].min() + 1)
                ys = pixels[pixels[:, 1] == edge, 0]
                attachment_y = float(np.median(ys))
                stem = Image.new('L', size)
                ImageDraw.Draw(stem).line(
                    [(edge, attachment_y), (edge, y + (-3.5 if up else 3.5) * inter)],
                    fill=255,
                    width=2,
                )
                parts[ident + ':stem'] = stem
                ledger = Image.new('L', size)
                ld = ImageDraw.Draw(ledger)
                positions = (
                    range(6, staff_pos + 1, 2)
                    if staff_pos >= 6
                    else range(-6, staff_pos - 1, -2) if staff_pos <= -6 else []
                )
                for position in positions:
                    ly = line_y(staff['lines'][2], x) + position * inter / 2
                    ld.line([(x - 0.875 * inter, ly), (x + 0.875 * inter, ly)], fill=255, width=2)
                if ledger.getbbox():
                    parts[ident + ':ledger'] = ledger
                head_rows.append(
                    {
                        'semantic_id': ident,
                        'kind': 'NOTE',
                        'duration': event['duration'],
                        'source_pitch': frozen['source_pitch'],
                        'target_pitch': frozen['target_pitch'],
                        'physical_detected_center': [x, frozen['detected_head_y']],
                        'semantic_source_y': frozen['corrected_semantic_source_staff_y'],
                        'semantic_target_y': y,
                        'expected_displacement': frozen['expected_diatonic_delta_y'],
                        'notehead_x_deviation': info.get(
                            'requested_anchor', info['font_outline_anchor']
                        )[0]
                        - x,
                        'target_pitch_y_deviation': y - expected,
                        'stem_head_shared_ink': int(
                            np.count_nonzero((np.asarray(head) > 0) & (np.asarray(stem) > 0))
                        ),
                        **info,
                    }
                )
            # Research observers receive copies and cannot change the rendered layer.
            if parts_observer is not None:
                parts_observer(excerpt['number'], key, {n: m.copy() for n, m in parts.items()})
            intersections = ink_intersections(parts)
            ink = np.maximum.reduce([np.array(p) for p in parts.values()])
            music = np.maximum.reduce(
                [np.array(p) for n, p in parts.items() if n not in ['staff', 'bar']]
            )
            protected = np.zeros((size[1], size[0]), bool)
            for region in spec['protected']:
                x0, y0, x1, y1 = region['bbox']
                protected[
                    max(0, math.floor(y0)) : min(size[1], math.ceil(y1)),
                    max(0, math.floor(x0)) : min(size[0], math.ceil(x1)),
                ] = True
            original_dark = np.array(source.convert('L')) < 127
            protected_pixels = int(np.count_nonzero((music > 0) & protected & original_dark))
            box = Image.fromarray(ink).getbbox()
            clipping = bool(
                box
                and (
                    box[0] < viewport[0]
                    or box[1] < viewport[1]
                    or box[2] > viewport[2]
                    or box[3] > viewport[3]
                )
            )
            max_anchor = max(
                abs(v) for n in head_rows if n['kind'] == 'NOTE' for v in n['anchor_residual']
            )
            # On a separate white canvas, no original pixel is removed or copied into targets.
            layer = Image.fromarray(255 - ink).convert('RGB')
            rendered[key].append(
                panel_label(
                    layer.crop(viewport),
                    f'{key} major, G clef context; printed {excerpt["number"]}; no chord/lyric layer',
                )
            )
            Image.fromarray(ink).save(out / f'm{excerpt["number"]}-{key}-notation-alpha.png')
            metrics.append(
                {
                    'measure': excerpt['number'],
                    'target': key,
                    'viewport_page_coordinates': viewport,
                    'staff_geometry_deviation': 0,
                    'measure_boundary_deviation': 0,
                    'font_size': fontsize,
                    'font_outline_bounds': {hex(ord(k)): v for k, v in bounds.items()},
                    'events': head_rows,
                    'event_count': len(head_rows),
                    'head_count': sum(n['kind'] == 'NOTE' for n in head_rows),
                    'missing_semantic_events': len(excerpt['events']) - len(head_rows),
                    'duplicated_semantic_events': len(head_rows)
                    - len({n['semantic_id'] for n in head_rows}),
                    'ink_intersections': intersections,
                    'unexpected_collision_pairs': sum(
                        not c['intentional_contact'] for c in intersections
                    ),
                    'new_music_vs_protected_source_dark_pixels': protected_pixels,
                    'protected_intersection_is_not_verified_text_ownership': True,
                    'max_notehead_raster_anchor_residual': max_anchor,
                    'page_or_viewport_clipping': clipping,
                    'chord_coverage': 'INCOMPLETE_MUSIC_ONLY',
                    'chord_rendered_text_width': 'NOT_APPLICABLE_NO_RECOGNIZED_HARMONIES_IN_SELECTED_SCOPE',
                    'beam_slur_endpoint_continuity': 'NOT_APPLICABLE_NONE_IN_SELECTED_SCOPE',
                    'checks_pass': not clipping
                    and max_anchor <= 0.5
                    and protected_pixels == 0
                    and not any(not c['intentional_contact'] for c in intersections)
                    and all(n.get('stem_head_shared_ink', 1) > 0 for n in head_rows),
                }
            )
    outputs = {}
    for key, panels in rendered.items():
        sheet = Image.new(
            'RGB',
            (max(p.width for p in panels), sum(p.height for p in panels) + 12 * (len(panels) - 1)),
            'white',
        )
        y = 0
        for panel in panels:
            sheet.paste(panel, (0, y))
            y += panel.height + 12
        name = {'original': 'original-bb.png', 'A': 'predicted-a.png', 'G': 'predicted-g.png'}[key]
        sheet.save(out / name)
        outputs[key] = sheet
    contact = Image.new(
        'RGB',
        (sum(i.width for i in outputs.values()) + 24, max(i.height for i in outputs.values())),
        'white',
    )
    x = 0
    for image in outputs.values():
        contact.paste(image, (x, 0))
        x += image.width + 12
    contact.save(out / 'comparison-contact-sheet.png')
    # Verify untouched crop bytes in the original panel, including lyric evidence.
    equal = True
    for excerpt, panel in zip(spec['excerpts'], rendered['original']):
        metric = next(m for m in metrics if m['measure'] == excerpt['number'])
        crop = source.crop(metric['viewport_page_coordinates'])
        equal &= panel.crop((0, 84, crop.width, 84 + crop.height)).tobytes() == crop.tobytes()
    result = {
        'source_sha256': sha(inputs / 'source.png'),
        'font_sha256': sha(font_path),
        'font_method': (
            'FreeSerif fixed-phase raster bbox pixel-index anchor; no score-tuned offset'
            if glyph_renderer is not None
            else 'FreeSerif Unicode musical glyph outline bbox-center anchor, baseline explicitly transformed; no source/reference center calibration'
        ),
        'glyph_renderer_module': place_glyph.__module__,
        'selected_measures': spec['selected'],
        'full_integrity': spec['guards'],
        'metrics': metrics,
        'lyric_original_crop_pixel_equality': bool(equal),
        'lyric_composite_produced': False,
        'source_was_edited': False,
        'seconds': time.monotonic() - start,
        'decision': (
            'VISUAL_POC_RENDERED_WITH_LIMITATIONS'
            if equal and all(m['checks_pass'] for m in metrics)
            else 'VISUAL_POC_NEEDS_REFINEMENT'
        ),
    }
    dump(out / 'rendering-metrics.json', result)
    dump(
        out / 'rendering-limitations.json',
        {
            'standalone_score': False,
            'label': WARNING,
            'music_only': True,
            'independent_human_labels': 0,
            'chords': 'missing source candidates NOT invented',
            'unsupported': [
                'beams',
                'flags',
                'curves',
                'explicit accidentals',
                'key-signature glyphs',
                'clefs',
                'repeat/ending glyphs',
                'moving articulations',
                'fermatas',
            ],
            'context': 'Mid-system excerpts; G clef and key supplied as external text, not standalone score context.',
            'lyric_composition': 'NOT_ATTEMPTED; unchanged source crop alongside independent new notation',
            'reference_accuracy_denominator': 0,
            'mask_authorization': 'NONE',
            'original_pixel_erasure': 'NOT_PERMITTED',
            'optical_anchor_independence': 'Font design contract only; independent physical/music-quality validation pending',
        },
    )
    dump(
        out / 'prototype-freeze.json',
        {
            'files': file_hashes(out),
            'selection_sha256': sha(inputs / 'selection.json'),
            'reference_comparison_started': False,
            'code_sha256': sha(Path(__file__)),
        },
    )
    return result['decision']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--gt01', type=Path, required=True)
    p.add_argument('--gt02', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('render')
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--font', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = parser.parse_args()
    print(
        prepare(a.gt01, a.gt02, a.out)
        if a.command == 'prepare'
        else render(a.inputs, a.font, a.out)
    )


if __name__ == '__main__':
    main()
