"""One-pass developer ownership audit of existing evidence; no OMR invocation."""

from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from backend.omr_v4.ink import isolate_ink, glyphs_from_omr, coverage, pixels_from_runs
from backend.omr_v4.masks import plan_masks, validate_pixel_integrity
from backend.omr_v4.visual_graph import load_visual_graph


def inspect_ink(artifacts: Path, out: Path):
    if out.exists() and any(out.iterdir()):
        raise ValueError('Output must be new/empty')
    names = (
        'source.png',
        'recognized.omr',
        'plan.json',
        'graph-summary.json',
        'semantic-report.json',
    )
    hashes = {n: hashlib.sha256((artifacts / n).read_bytes()).hexdigest() for n in names}
    with Image.open(artifacts / 'source.png') as image:
        source = image.copy()
    graph = load_visual_graph(artifacts / 'recognized.omr')
    layout = json.loads((artifacts / 'plan.json').read_text())
    evidence = isolate_ink(source, graph, glyphs_from_omr(artifacts / 'recognized.omr'))
    mask_plan, masks = plan_masks(source, graph, layout, evidence.owned(source))
    approved = np.asarray(masks.approved) != 0
    verified = Image.new('L', source.size)
    rejected = Image.new('L', source.size)
    staff = Image.new('L', source.size)
    for record in evidence.records:
        for x, y in pixels_from_runs(record.runs):
            verified.putpixel((x, y), 255)
        if record.status != 'VERIFIED':
            box = graph.symbols[record.symbol_id].geometry.region
            if box:
                ImageDraw.Draw(rejected).rectangle(box, fill=255)
        for x, y in pixels_from_runs(record.staff_overlap_runs):
            staff.putpixel((x, y), 255)
    if np.any(approved & (np.asarray(verified) == 0)):
        raise ValueError('Approved mask contains unverified pixels')
    summary = coverage(evidence)
    summary['mask_metrics'] = dict(mask_plan.metrics)
    summary['complete_note_groups'] = sum(
        g.disposition == 'APPROVABLE_AS_GROUP' for g in mask_plan.groups
    )
    verified_ids = {r.symbol_id for r in evidence.records if r.status == 'VERIFIED'}
    # This counts complete source-object coverage independently of target safety.
    summary['fully_verified_atomic_groups'] = sum(
        all(
            set(n.source_object_ids) <= verified_ids
            for n in mask_plan.notes
            if n.atomic_group == g.id
        )
        for g in mask_plan.groups
    )
    summary['fully_verified_beam_groups'] = sum(
        all(
            set(n.source_object_ids) <= verified_ids
            for n in mask_plan.notes
            if n.head_id in g.head_ids
        )
        for g in mask_plan.beam_groups
    )
    summary['input_sha256'] = hashes
    summary['integrity'] = validate_pixel_integrity(source, source.copy(), masks.approved)
    summary['decision'] = (
        'READY_FOR_MASK_REFINEMENT' if summary['verified_symbols'] else 'NEEDS_INK_ISOLATION_FIXES'
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / 'ink-evidence.json').write_text(evidence.to_json())
    (out / 'ink-summary.json').write_text(
        json.dumps(summary, sort_keys=True, indent=2, allow_nan=False) + '\n'
    )
    (out / 'mask-summary.json').write_text(mask_plan.to_json())
    for name, image in [
        ('verified-ink-mask.png', verified),
        ('rejected-ink-mask.png', rejected),
        ('staff-overlap-mask.png', staff),
        ('approved-mask.png', masks.approved),
    ]:
        image.save(out / name)
    overlay = source.convert('RGBA')
    for image, color in [(rejected, '#f0a000'), (verified, '#00bb44'), (staff, '#00bbee')]:
        tint = Image.new('RGBA', source.size, color)
        tint.putalpha(image.point(lambda v: 100 if v else 0))
        overlay = Image.alpha_composite(overlay, tint)
    canvas = Image.new('RGB', (source.width + 420, source.height), 'white')
    canvas.paste(overlay.convert('RGB'), (0, 0))
    draw = ImageDraw.Draw(canvas)
    for i, text in enumerate(
        [
            'INK OWNERSHIP - DIAGNOSTIC ONLY',
            summary['decision'],
            'green: VERIFIED exact pixels',
            'orange: REJECTED window (not ink)',
            'cyan: uncertain staff overlap',
            'NO SCORE PIXELS REMOVED OR REPLACED',
        ]
    ):
        draw.text((source.width + 10, 15 + 25 * i), text, fill='black')
    canvas.save(out / 'ink-ownership-overlay.png')
    if any(
        hashlib.sha256((artifacts / n).read_bytes()).hexdigest() != h for n, h in hashes.items()
    ):
        raise ValueError('Input evidence changed')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect_ink(args.artifacts, args.out), indent=2, sort_keys=True))
