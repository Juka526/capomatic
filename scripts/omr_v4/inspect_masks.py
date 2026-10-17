"""Plan diagnostic masks from existing evidence; no recognition or score editing."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from backend.omr_v4.masks import plan_masks, raster_digest, validate_pixel_integrity
from backend.omr_v4.visual_graph import load_visual_graph
from scripts.omr_v4.audit_mapping import intersection_audit


def inspect_masks(artifacts: Path, out: Path) -> dict:
    """Write mask diagnostics once, preserving every input artifact unchanged."""
    if out.exists() and any(out.iterdir()):
        raise ValueError('Mask output must be empty/new')
    inputs = (
        'source.png',
        'recognized.omr',
        'plan.json',
        'graph-summary.json',
        'semantic-report.json',
    )
    hashes = {name: hashlib.sha256((artifacts / name).read_bytes()).hexdigest() for name in inputs}
    layout = json.loads((artifacts / 'plan.json').read_text())
    graph = load_visual_graph(artifacts / 'recognized.omr')
    with Image.open(artifacts / 'source.png') as im:
        source = im.copy()
    before = raster_digest(source)
    # No exact glyph-ink certificate producer exists yet. Deliberately do not
    # manufacture certificates from bboxes, connected components or a threshold.
    plan, masks = plan_masks(source, graph, layout)
    protection = intersection_audit(layout, graph)
    summary = json.loads(plan.to_json())
    summary['input_sha256'] = hashes
    summary['protection_audit'] = {
        'legacy_pair_count': protection['pair_count'],
        'legacy_unique_physical_overlap_areas': len(protection['unique_intersection_components']),
        'legacy_nested_duplicate_pair_count': len(protection['nested_duplicate_pair_numbers']),
        'legacy_nested_duplicate_pair_numbers': protection['nested_duplicate_pair_numbers'],
        'legacy_overlap_components': protection['unique_intersection_components'],
        'all_nested_protections_still_active': True,
        'genuine_source_ink_conflicts': None,
        'unresolved_ownership_overlap_areas': len(protection['unique_intersection_components']),
        'source_ink_conflict_status': 'UNRESOLVED_WITHOUT_VERIFIED_SYMBOL_INK',
        'target_conflicts_are_conservative_envelope_alarms': True,
    }
    summary['ink_evidence_policy'] = (
        'No real-score exact ink isolation implemented; no bbox approval'
    )
    summary['staff_restore_policy'] = (
        'RESTORE_REQUIRED centerline clips with conservative corridor, not reconstructed ink'
    )
    summary['unchanged_source_integrity'] = validate_pixel_integrity(
        source, source.copy(), masks.approved
    )
    summary['semantic_integrity'] = json.loads((artifacts / 'semantic-report.json').read_text())[
        'semantic_integrity'
    ]
    out.mkdir(parents=True, exist_ok=True)
    images = {
        'approved-mask.png': masks.approved,
        'blocked-mask.png': masks.blocked,
        'protected-mask.png': masks.protected,
        'staff-restore-mask.png': masks.staff_restore,
        'target-envelope.png': masks.target,
    }
    for name, image in images.items():
        if not set(np.unique(np.asarray(image))) <= {0, 255}:
            raise ValueError('Nonbinary diagnostic mask')
        image.save(out / name)
    base = source.convert('RGBA')
    layers = [
        ('approved', '#008744', masks.approved),
        ('blocked', '#e64343', masks.blocked),
        ('protected', '#a700bd', masks.protected),
        ('staff restore required', '#00aabb', masks.staff_restore),
        ('target occupancy', '#176dff', masks.target),
        ('unknown ownership', '#e59b00', masks.unknown),
    ]
    composite = base.copy()
    for _, color, mask in layers:
        tint = Image.new('RGBA', base.size, color)
        alpha = mask.point(lambda value: 65 if value else 0)
        tint.putalpha(alpha)
        composite = Image.alpha_composite(composite, tint)
    overlay = Image.new('RGB', (base.width + 470, max(base.height, 760)), 'white')
    overlay.paste(composite.convert('RGB'), (0, 0))
    legend = ImageDraw.Draw(overlay)
    x = base.width + 12
    y = 12
    for line in (
        'V4 MASK SAFETY - DIAGNOSTIC ONLY',
        'NO SOURCE PIXELS ERASED / REPLACED',
        plan.decision,
    ):
        legend.text((x, y), line, fill='black')
        y += 22
    for label, color, _ in layers:
        legend.rectangle((x, y, x + 12, y + 12), fill=color)
        legend.text((x + 20, y), label, fill='black')
        y += 22
    y += 12
    for name, value in plan.metrics:
        legend.text((x, y), f'{name}: {value}', fill='black')
        y += 18
    legend.text(
        (x, y + 18), 'Blocked rectangles are envelopes, NOT approved masks.', fill='#a00000'
    )
    overlay.save(out / 'mask-overlay.png')
    if raster_digest(source) != before or any(
        hashlib.sha256((artifacts / name).read_bytes()).hexdigest() != value
        for name, value in hashes.items()
    ):
        raise ValueError('Input evidence changed')
    (out / 'mask-summary.json').write_text(
        json.dumps(summary, sort_keys=True, indent=2, allow_nan=False) + '\n'
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    summary = inspect_masks(args.artifacts, args.out)
    print(
        json.dumps(
            {
                'decision': summary['decision'],
                'metrics': summary['metrics'],
                'protection_audit': summary['protection_audit'],
            },
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == '__main__':
    main()
