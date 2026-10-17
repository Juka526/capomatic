"""One frozen Phase 1.9c pass over existing source/OMR evidence. No recognition."""

from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from backend.omr_v4.ink import pixels_from_runs
from backend.omr_v4.source_ink import (
    COMPLETE,
    PARTIAL,
    REJECTED,
    coverage,
    isolate_source_ink,
    read_processed_bundle,
)
from backend.omr_v4.masks import plan_masks, validate_pixel_integrity
from backend.omr_v4.visual_graph import load_visual_graph


def inspect_source_ink(artifacts: Path, out: Path):
    if out.exists() and any(out.iterdir()):
        raise ValueError('New/empty output required')
    names = (
        'source.png',
        'recognized.omr',
        'plan.json',
        'graph-summary.json',
        'semantic-report.json',
    )
    hashes = {n: hashlib.sha256((artifacts / n).read_bytes()).hexdigest() for n in names}
    # Recorded forensic binding is a prerequisite, not an inferred registration.
    provenance = json.loads((artifacts / 'ink-forensics/ink-forensics-summary.json').read_text())
    if (
        provenance['source']['file_sha256'] != hashes['source.png']
        or provenance['omr_sha256'] != hashes['recognized.omr']
        or not provenance['supplementary_measurements']['raster_reproduction'][
            'native_pixels_identical'
        ]
    ):
        raise ValueError('Source/OMR forensic coordinate provenance not established')
    with Image.open(artifacts / 'source.png') as im:
        source = im.copy()
    graph = load_visual_graph(artifacts / 'recognized.omr')
    bundle = read_processed_bundle(artifacts / 'recognized.omr', graph)
    evidence = isolate_source_ink(source, graph, *bundle)
    owned = evidence.owned(source)
    layout = json.loads((artifacts / 'plan.json').read_text())
    mask_plan, masks = plan_masks(source, graph, layout, owned)
    images = {
        name: Image.new('L', source.size)
        for name in (
            'processed-support-mask.png',
            'verified-core-mask.png',
            'fringe-mask.png',
            'unknown-crossing-mask.png',
            'complete-ownership-mask.png',
            'rejected-support-mask.png',
        )
    }
    for r in evidence.processed:
        for p in pixels_from_runs(r.runs):
            if 0 <= p[0] < source.width and 0 <= p[1] < source.height:
                images['processed-support-mask.png'].putpixel(p, 255)
    for g in evidence.groups:
        for name, runs in [
            ('verified-core-mask.png', g.core_union),
            ('fringe-mask.png', g.fringe_union),
            ('unknown-crossing-mask.png', g.unknown_crossing),
            ('complete-ownership-mask.png', g.source_union if g.status == COMPLETE else ()),
        ]:
            for p in pixels_from_runs(runs):
                images[name].putpixel(p, 255)
        if g.status == REJECTED:
            for r in evidence.processed:
                if r.symbol_id in g.members:
                    for p in pixels_from_runs(r.runs):
                        if 0 <= p[0] < source.width and 0 <= p[1] < source.height:
                            images['rejected-support-mask.png'].putpixel(p, 255)
    if np.any(
        (np.asarray(masks.approved) != 0) & (np.asarray(images['complete-ownership-mask.png']) == 0)
    ):
        raise ValueError('Approved mask outside complete ownership')
    summary = coverage(evidence)
    summary.update(
        {
            'input_sha256': hashes,
            'phase18_injected_symbol_views': len(owned),
            'mask_metrics': dict(mask_plan.metrics),
            'source_integrity': validate_pixel_integrity(source, source.copy(), masks.approved),
            'decision': (
                'READY_FOR_MASK_REFINEMENT'
                if any(g.status == COMPLETE for g in evidence.groups)
                else 'NEEDS_INK_ISOLATION_FIXES'
            ),
            'group_completeness_is_propagated_to_candidate_status': True,
            'phase18_geometry_compatibility_is_separate_no_clipping': True,
        }
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / 'ink-evidence.json').write_text(evidence.to_json())
    (out / 'ink-summary.json').write_text(
        json.dumps(summary, sort_keys=True, indent=2, allow_nan=False) + '\n'
    )
    (out / 'mask-summary.json').write_text(mask_plan.to_json())
    images['approved-mask.png'] = masks.approved
    for name, im in images.items():
        im.save(out / name)
    overlay = source.convert('RGBA')
    for name, color in [
        ('verified-core-mask.png', '#00ad44'),
        ('fringe-mask.png', '#004cff'),
        ('unknown-crossing-mask.png', '#e7a000'),
        ('rejected-support-mask.png', '#cc0044'),
    ]:
        tint = Image.new('RGBA', source.size, color)
        tint.putalpha(images[name].point(lambda v: 100 if v else 0))
        overlay = Image.alpha_composite(overlay, tint)
    canvas = Image.new('RGB', (source.width + 480, source.height), 'white')
    canvas.paste(overlay.convert('RGB'), (0, 0))
    draw = ImageDraw.Draw(canvas)
    for i, line in enumerate(
        [
            'PHASE 1.9c - DIAGNOSTIC ONLY',
            summary['decision'],
            'green: non-crossing verified core',
            'blue: bounded fringe',
            'orange: unknown crossing / RESTORE_REQUIRED',
            'red: rejected processed support',
            'PARTIAL IS NOT AN EDIT MASK',
            'NO SOURCE SCORE PIXELS EDITED',
        ]
    ):
        draw.text((source.width + 10, 15 + i * 24), line, fill='black')
    canvas.save(out / 'ink-ownership-overlay.png')
    if any(
        hashlib.sha256((artifacts / n).read_bytes()).hexdigest() != v for n, v in hashes.items()
    ):
        raise ValueError('Input evidence changed')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inspect_source_ink(args.artifacts, args.out), sort_keys=True, indent=2))
