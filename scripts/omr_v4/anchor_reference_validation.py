"""Offline coordinate decomposition and source-only blinded annotation packet.

No reference labels are inferred and no runtime planning or pixels are changed.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from backend.omr_v4.ink import pixels_from_runs
from backend.omr_v4.matcher import read_semantics
from backend.omr_v4.plan import to_data
from backend.omr_v4.visual_graph import load_visual_graph
from scripts.omr_v4.geometry_locked_feasibility import (
    absolute_target_y, digest, line_y, validate_output_directory, verify_inputs, write_json,
)

PROTOCOL = Path(__file__).resolve().parents[2] / 'docs/V4_ANCHOR_REFERENCE_PROTOCOL.json'


def decompose(staff, x, detected_y, raw_position, corrected_position, target_position, old_y):
    if any(v is None or not math.isfinite(v) for v in (detected_y, raw_position, corrected_position, target_position, old_y)):
        raise ValueError('Unknown/nonfinite anchor or semantic coordinate')
    raw = absolute_target_y(staff, x, raw_position)
    corrected = absolute_target_y(staff, x, corrected_position)
    target = absolute_target_y(staff, x, target_position)
    return {
        'raw_semantic_ideal_y': raw,
        'corrected_semantic_ideal_y': corrected,
        'absolute_target_y': target,
        'detected_minus_raw_ideal_px': detected_y - raw,
        'semantic_repair_shift_px': corrected - raw,
        'corrected_ideal_minus_detected_px': corrected - detected_y,
        'corrected_to_target_step_px': target - corrected,
        'old_plan_target_y': old_y,
        'absolute_minus_old_plan_px': target - old_y,
        'relative_formula_replay_y': detected_y + target - corrected,
        'replacement_glyph_anchor': 'UNDEFINED_NOT_RENDERED',
    }


def select_cases(matches, repairs):
    """Five repairs plus five hash-ranked matched nonrepair controls; no y input."""
    import hashlib

    repair_ids = {r['repaired_event']['id'] for r in repairs}
    if len(repair_ids) != 5 or any(matches.get(i, {}).get('status') != 'MATCHED' for i in repair_ids):
        raise ValueError('Five matched historical repairs required')
    rank = lambda i: hashlib.sha256(('anchor-reference-v1:' + i).encode()).hexdigest()
    controls = sorted((i for i, m in matches.items() if m['status'] == 'MATCHED' and i not in repair_ids), key=rank)[:5]
    if len(controls) != 5:
        raise ValueError('Five matched controls required')
    return sorted(repair_ids | set(controls), key=rank)


def support_stats(runs):
    points = pixels_from_runs(runs)
    if not points:
        raise ValueError('Empty persisted support')
    xs, ys = zip(*points)
    return {
        'pixel_count': len(points),
        'bounds_half_open': [min(xs), min(ys), max(xs) + 1, max(ys) + 1],
        'pixel_index_centroid': [sum(xs) / len(points), sum(ys) / len(points)],
        'interpretation': 'PERSISTED_GLYPH_ATTRIBUTION_NOT_PHYSICAL_HEAD_GROUND_TRUTH',
    }


def export_case(image, out, case_id, crop, source_sha):
    """Explicit allowlist: no semantic IDs, expected coordinates or group labels."""
    if not re.fullmatch(r'case-[0-9]{2}', case_id) or any(v != int(v) for v in crop):
        raise ValueError('Invalid blind case')
    l, t, r, b = crop
    if not (0 <= l < r <= image.width and 0 <= t < b <= image.height):
        raise ValueError('Invalid native crop')
    path = out / f'{case_id}.png'
    image.crop(crop).save(path)
    return {
        'case': case_id, 'image': path.name, 'crop_sha256': digest(path),
        'source_sha256': source_sha, 'native_page_crop_half_open': crop,
        'coordinate_conversion': 'page_index_center=local_index_center+crop_origin; for edge-origin pointer subtract 0.5 first, as declared before annotation in instructions.json',
    }


def blind_instructions(protocol, protocol_hash):
    return {
        'protocol_sha256': protocol_hash,
        **{k: protocol[k] for k in ('annotation_instructions', 'coordinate_convention', 'reference_fields')},
    }


def run(manifest, out):
    from PIL import Image

    root, verified = verify_inputs(manifest)
    validate_output_directory(out, root)
    if out.exists() and any(out.iterdir()):
        raise ValueError('New/empty output directory required')
    protocol_hash = digest(PROTOCOL)
    if protocol_hash != PROTOCOL.with_suffix('.sha256').read_text().strip():
        raise ValueError('Frozen protocol hash mismatch')
    protocol = json.loads(PROTOCOL.read_text())
    graph = load_visual_graph(root / 'recognized.omr')
    plan = json.loads((root / 'plan.json').read_text())
    repairs = json.loads((root / 'v3-evidence/ledger-repair-provenance.json').read_text())
    matches = {m['note']['id']: m for m in plan['matches']['notes']}
    moves = {m['semantic_id']: m for m in plan['note_moves']}
    scores = [read_semantics(root / p) for p in ('pre-ledger.musicxml', 'recognized.musicxml', 'transposed.musicxml')]
    if any([n.identity for n in s.notes] != [n.identity for n in scores[0].notes] for s in scores[1:]):
        raise ValueError('Semantic identity changed')
    notes = [{n.id: n for n in s.notes} for s in scores]
    staves = {s.id: s for s in graph.staves}
    glyphs = {g['id']: g for g in json.loads((root / 'v3-evidence/glyph-support.json').read_text())}
    selected = select_cases(matches, repairs)
    repair_ids = {r['repaired_event']['id'] for r in repairs}
    image = Image.open(root / 'source.png')
    if len(graph.pages) != 1 or image.size != (graph.pages[0].width, graph.pages[0].height):
        raise ValueError('Source coordinate binding mismatch')
    out.mkdir(parents=True, exist_ok=True)
    blind = out / 'blind-packet'
    blind.mkdir()
    write_json(blind / 'instructions.json', blind_instructions(protocol, protocol_hash))
    rows, cases, key = [], [], []
    for index, ident in enumerate(selected, 1):
        match, move = matches[ident], moves[ident]
        head = graph.symbols[match['head_id']]
        if move['source_head_id'] != head.id or head.geometry.center is None or head.geometry.bbox is None:
            raise ValueError('Missing/mismatched persisted head geometry')
        staff = staves[head.staff]
        raw, corrected, target = [n[ident] for n in notes]
        x, detected_y = head.geometry.center
        attrs = dict(head.attributes)
        glyph_id = head.page + ':' + attrs['glyph'] if attrs.get('glyph') else None
        box = head.geometry.bbox
        case_id = f'case-{index:02d}'
        crop = [max(0, math.floor(x - 100)), max(0, math.floor(line_y(staff.lines[0], x) - 100)),
                min(image.width, math.ceil(x + 100)), min(image.height, math.ceil(max(box[3] + 60, line_y(staff.lines[-1], x) + 140)))]
        cases.append(export_case(image, blind, case_id, crop, digest(root / 'source.png')))
        key.append({'case': case_id, 'semantic_id': ident, 'head_id': head.id, 'is_historical_repair': ident in repair_ids})
        rows.append({
            'semantic_id': ident, 'case': case_id, 'head_id': head.id,
            'is_historical_repair': ident in repair_ids,
            'staff': to_data(staff), 'head_source_xml': head.source_xml,
            'detected_bbox': box, 'detected_bbox_center': [(box[0] + box[2])/2, (box[1]+box[3])/2],
            'persisted_pivot': head.geometry.pivot, 'geometry_center_used_by_old_plan': [x, detected_y],
            'glyph_id': glyph_id, 'persisted_glyph': support_stats(glyphs[glyph_id]['runs']) if glyph_id in glyphs else None,
            'raw_visual_pitch_position': head.pitch_position,
            'raw_semantic': to_data(raw), 'corrected_semantic': to_data(corrected), 'target_semantic': to_data(target),
            'clef_reference': 'Unchanged read_semantics reads MusicXML clef state; staff_pitch zero denotes middle staff line',
            'persisted_system_staff_clefs': [s.source_xml for s in graph.symbols.values() if s.kind == 'clef' and s.staff == head.staff],
            'local_middle_line_y': line_y(staff.lines[2], x),
            'local_bottom_line_y': line_y(staff.lines[4], x),
            **decompose(staff, x, detected_y, raw.staff_pitch, corrected.staff_pitch, target.staff_pitch, move['target_y']),
        })
    write_json(blind / 'cases.json', cases)
    for annotator in ('A', 'B'):
        write_json(blind / f'empty-reference-{annotator}.json', {
            'protocol_sha256': protocol_hash, 'annotator': annotator,
            'status': 'PENDING_INDEPENDENT_ANNOTATION',
            'cases': [{'case': c['case'], **{k: None for k in protocol['reference_fields']}} for c in cases],
        })
    write_json(out / 'hidden-solution-key.json', key)
    write_json(out / 'derived-candidate-coordinates.json', rows)
    _, after = verify_inputs(manifest)
    write_json(out / 'verification.json', {'before': verified, 'after': after, 'protocol_sha256': protocol_hash,
        'status': 'PENDING_INDEPENDENT_ANNOTATION', 'independent_reference_count': 0,
        'binding_limit': json.loads(manifest.read_text())['binding_limit']})
    return {'status': 'PENDING_INDEPENDENT_ANNOTATION', 'cases': len(cases), 'protocol_sha256': protocol_hash, 'verified_files_before_after': after['verified_files']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.inputs, args.out), indent=2))


if __name__ == '__main__':
    main()
