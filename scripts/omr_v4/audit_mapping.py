"""Read existing Phase 1 artifacts; enumerate evidence without making new matches."""

from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

from backend.omr_v4.matcher import SemanticNote, read_semantics
from backend.omr_v4.plan import to_data
from backend.omr_v4.visual_graph import VisualScoreGraph, load_visual_graph


def candidate_audit(note: SemanticNote, graph: VisualScoreGraph, plan: dict) -> dict:
    """Enumerate all heads in the measure/staff before any pitch filtering.

    Slot-region membership is context for the human audit, never a fallback
    assignment. Every candidate includes each independent rejection check.
    """
    symbols = graph.symbols
    staves = {s.id: s for s in graph.staves}
    owners = {m['head_id']: m['note']['id'] for m in plan['matches']['notes'] if m['head_id']}
    measures = [m for m in graph.measures if m.number == note.measure and m.part == note.part]
    output = {'semantic': to_data(note), 'measures': [], 'candidates': []}
    for measure in measures:
        slots = {s.id: s for s in measure.slots}
        exact = [s for s in slots.values() if s.offset == note.offset and s.x is not None]
        region = None
        if len(exact) == 1 and measure.bounds:
            x = exact[0].x
            xs = sorted(s.x for s in slots.values() if s.x is not None)
            left = max((v for v in xs if v < x), default=measure.bounds[0])
            right = min((v for v in xs if v > x), default=measure.bounds[2])
            region = ((left + x) / 2, (x + right) / 2)
        output['measures'].append(
            {
                'id': measure.id,
                'system': measure.system,
                'bounds': measure.bounds,
                'slots': to_data(measure.slots),
                'relevant_slot_region_x': region,
            }
        )
        raw = ET.fromstring(measure.source_xml)
        for head in symbols.values():
            staff = staves.get(head.staff)
            point = head.geometry.center
            if (
                head.kind != 'head'
                or not staff
                or staff.part != note.part
                or staff.number != note.staff
                or head.system != measure.system
            ):
                continue
            parents = [
                r.source
                for r in graph.relations
                if r.kind == 'contains'
                and r.target == head.id
                and symbols[r.source].kind in {'head-chord', 'small-chord'}
            ]
            membership = [c for c in parents if c in measure.symbol_ids]
            in_bounds = bool(
                point and measure.bounds and measure.bounds[0] <= point[0] <= measure.bounds[2]
            )
            if not membership and not in_bounds:
                continue
            voice_evidence = []
            for voice in raw.findall('voice'):
                for entry in voice.findall('slots/entry'):
                    value = entry.find('value')
                    if value is None or not any(
                        symbols[c].source_id == value.get('chord') for c in parents
                    ):
                        continue
                    slot_id = entry.findtext('key')
                    slot = slots.get(slot_id)
                    voice_evidence.append(
                        {
                            'voice': voice.get('id'),
                            'chord': value.get('chord'),
                            'status': value.get('status'),
                            'slot_id': slot_id,
                            'offset': (
                                str(slot.offset) if slot and slot.offset is not None else None
                            ),
                            'x': slot.x if slot else None,
                            'suspicious': slot.suspicious if slot else None,
                        }
                    )
            begin = [v for v in voice_evidence if v['status'] == 'BEGIN']
            checks = {
                'unique_measure': len(measures) == 1,
                'explicit_measure_membership': bool(membership),
                'unique_parent': len(parents) == 1,
                'unique_begin': len(begin) == 1,
                'exact_onset': len(begin) == 1 and begin[0]['offset'] == str(note.offset),
                'usable_slot': len(begin) == 1
                and begin[0]['x'] is not None
                and begin[0]['suspicious'] is False,
                'staff_pitch_agrees': head.pitch_position == note.staff_pitch,
                'geometry_valid': staff.valid and head.geometry.valid and point is not None,
            }
            members = sorted(
                {r.target for r in graph.relations if r.kind == 'contains' and r.source in parents}
            )
            checks['chord_size_agrees'] = len(members) == note.chord_size
            context = {head.id, *parents}
            context.update(graph.neighbors(head.id, {'head-stem'}))
            for parent in parents:
                context.update(graph.neighbors(parent, {'chord-stem'}))
            # Preserve real attachment edges, including links to curves/groups;
            # no traversal through slurs or beams into other note ownership.
            relations = [r for r in graph.relations if r.source in context or r.target in context]
            ledgers = [
                s.id
                for s in symbols.values()
                if s.kind == 'ledger'
                and s.staff == head.staff
                and s.geometry.region
                and head.geometry.bbox
                and s.geometry.region[0] <= head.geometry.bbox[2]
                and s.geometry.region[2] >= head.geometry.bbox[0]
            ]
            output['candidates'].append(
                {
                    'id': head.id,
                    'source_id': head.source_id,
                    'measure_stack': measure.id,
                    'staff_id': head.staff,
                    'xy': point,
                    'bbox': head.geometry.bbox,
                    'staff_pitch': head.pitch_position,
                    'grade': head.grade,
                    'ctx_grade': head.contextual_grade,
                    'parent_head_chords': parents,
                    'contained_member_ids': members,
                    'voice_slot_evidence': voice_evidence,
                    'in_relevant_slot_region': bool(
                        region and point and region[0] <= point[0] <= region[1]
                    ),
                    'checks': checks,
                    'rejected_checks': [k for k, v in checks.items() if not v],
                    'existing_match_owner': owners.get(head.id),
                    'relations': to_data(tuple(relations)),
                    'ledger_x_overlap_candidates_not_edges': ledgers,
                }
            )
    output['candidates'].sort(
        key=lambda c: (c['measure_stack'], c['xy'][0] if c['xy'] else -1, c['id'])
    )
    return output


def intersection_audit(plan: dict, graph: VisualScoreGraph) -> dict:
    """Report nesting and geometric components without constructing edit masks."""
    pairs = plan['intersections']
    parent = {
        r.target: r.source
        for r in graph.relations
        if r.kind == 'contains'
        and r.source in graph.symbols
        and graph.symbols[r.source].kind == 'lyric-line'
    }
    duplicates = []
    for index, pair in enumerate(pairs):
        if any(
            other['edit_id'] == pair['edit_id']
            and other['protected_id'] == parent.get(pair['protected_id'])
            for other in pairs
        ):
            duplicates.append(index + 1)
    remaining = set(range(len(pairs)))
    components = []
    while remaining:
        connected, pending = set(), [min(remaining)]
        while pending:
            i = pending.pop()
            if i in connected:
                continue
            connected.add(i)
            a = pairs[i]['region']
            for j in remaining - connected:
                b = pairs[j]['region']
                if (
                    pairs[i]['page'] == pairs[j]['page']
                    and max(a[0], b[0]) <= min(a[2], b[2])
                    and max(a[1], b[1]) <= min(a[3], b[3])
                ):
                    pending.append(j)
        remaining -= connected
        components.append(
            {
                'pair_numbers': [i + 1 for i in sorted(connected)],
                'bbox': [
                    (
                        min(pairs[i]['region'][d] for i in connected)
                        if d < 2
                        else max(pairs[i]['region'][d] for i in connected)
                    )
                    for d in range(4)
                ],
            }
        )
    return {
        'pair_count': len(pairs),
        'nested_duplicate_pair_numbers': duplicates,
        'unique_intersection_components': components,
        'unique_protected_ids': sorted({p['protected_id'] for p in pairs}),
        'pairs': pairs,
    }


def draw_gap(source: Image.Image, graph: VisualScoreGraph, audit: dict, out: Path) -> None:
    """Render an untouched source crop beside a separate annotation composite."""
    candidates, note = audit['candidates'], audit['semantic']
    if not candidates or len(audit['measures']) != 1:
        raise ValueError('A focused crop needs one measure with candidate geometry')
    measure = audit['measures'][0]
    staff_ids = {c['staff_id'] for c in candidates}
    lines = [line for s in graph.staves if s.id in staff_ids for line in s.lines]
    points = [p for line in lines for p in line]
    left, right = measure['bounds'][0], measure['bounds'][2]
    top = min(p[1] for p in points) - 55
    bottom = max(max(c['bbox'][3] for c in candidates), max(p[1] for p in points)) + 95
    crop_box = (
        max(0, int(left) - 20),
        max(0, int(top)),
        min(source.width, int(right) + 20),
        min(source.height, int(bottom)),
    )
    original = source.crop(crop_box).convert('RGB')
    layer = Image.new('RGBA', original.size)
    draw = ImageDraw.Draw(layer)

    def xy(p):
        return p[0] - crop_box[0], p[1] - crop_box[1]

    for line in lines:
        draw.line([xy(p) for p in line], fill='#00aaaa', width=1)
    for x in (left, right):
        draw.line([xy((x, top)), xy((x, bottom))], fill='#8000aa', width=2)
    for slot in measure['slots']:
        if slot['x'] is None:
            continue
        x = slot['x'] - crop_box[0]
        for y in range(20, original.height, 10):
            draw.line((x, y, x, y + 4), fill='#0066cc')
        draw.text((x, 2), slot['id'] + ':' + slot['offset'], fill='#004499')
    for candidate in candidates:
        color = '#d07800' if candidate['checks']['exact_onset'] else '#bb2233'
        b = candidate['bbox']
        draw.rectangle((*xy(b[:2]), *xy(b[2:])), outline=color, width=2)
        draw.text(xy((b[0], b[1] - 14)), candidate['source_id'], fill=color)
    annotated = Image.alpha_composite(original.convert('RGBA'), layer).convert('RGB')
    width = max(original.width * 2 + 30, 1200)
    canvas = Image.new('RGB', (width, original.height + 100 + len(candidates) * 22), 'white')
    d = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=14)
    d.text(
        (10, 8),
        f"{note['id']} | m{note['measure']} @{note['offset']} {note['pitch']} expected staff pitch {note['staff_pitch']}",
        fill='black',
        font=font,
    )
    d.text(
        (10, 32),
        'Source pixels (left); diagnostic annotations (right). Orange = exact onset, still rejected; red = other slot.',
        fill='black',
    )
    canvas.paste(original, (10, 60))
    canvas.paste(annotated, (20 + original.width, 60))
    for i, c in enumerate(candidates):
        reason = (
            ', '.join(c['rejected_checks'])
            or 'No failed static checks; consult original ownership/global matching.'
        )
        d.text(
            (10, 70 + original.height + i * 22),
            f"head {c['source_id']} pitch={c['staff_pitch']} | reject: {reason} | existing owner={c['existing_match_owner']}",
            fill='#8c3400' if c['checks']['exact_onset'] else '#992233',
            font=font,
        )
    canvas.save(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts', type=Path)
    args = parser.parse_args()
    root = args.artifacts
    plan = json.loads((root / 'plan.json').read_text())
    graph = load_visual_graph(root / 'recognized.omr')
    semantic = read_semantics(root / 'recognized.musicxml')
    ids = {m['note']['id'] for m in plan['matches']['notes'] if m['status'] != 'MATCHED'}
    if len(ids) > 32:
        raise ValueError('Bounded audit permits at most 32 unresolved semantic events')
    audits = [candidate_audit(n, graph, plan) for n in semantic.notes if n.id in ids]
    out = root / 'gaps'
    out.mkdir(exist_ok=True)
    before = hashlib.sha256((root / 'source.png').read_bytes()).hexdigest()
    with Image.open(root / 'source.png') as image:
        for i, audit in enumerate(audits, 1):
            draw_gap(image, graph, audit, out / f'gap-{i:02}.png')
    if hashlib.sha256((root / 'source.png').read_bytes()).hexdigest() != before:
        raise ValueError('Source pixels changed during audit')
    report = {
        'diagnostic_only': True,
        'gap_candidates': audits,
        'protected_intersections': intersection_audit(plan, graph),
        'unresolved_beams': [b for b in plan['beam_groups'] if b['status'] == 'UNRESOLVED'],
        'unlinked_curves': [s for s in plan['slurs'] if not s['linked']],
    }
    data = json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n'
    (out / 'candidate-audit.json').write_text(data)
    print(data, end='')


if __name__ == '__main__':
    main()
