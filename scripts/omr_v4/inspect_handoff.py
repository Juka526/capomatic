"""Bounded analysis admission from existing 1.9c evidence; never re-isolates ink."""

from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw
from backend.omr_v4.handoff import classify_handoff, ELIGIBLE
from backend.omr_v4.ink import pixels_from_runs
from backend.omr_v4.source_ink import read_processed_bundle
from backend.omr_v4.visual_graph import load_visual_graph


def inspect_handoff(artifacts: Path, out: Path):
    if out.exists() and any(out.iterdir()):
        raise ValueError('New/empty output required')
    ink = artifacts / 'source-ink-1.9c'
    names = [artifacts / n for n in ('source.png', 'recognized.omr', 'plan.json')] + [
        ink / n for n in ('ink-evidence.json', 'ink-summary.json', 'mask-summary.json')
    ]
    hashes = {
        str(p.relative_to(artifacts)): hashlib.sha256(p.read_bytes()).hexdigest() for p in names
    }
    evidence = json.loads((ink / 'ink-evidence.json').read_text())
    previous = json.loads((ink / 'ink-summary.json').read_text())
    for name in ('source.png', 'recognized.omr', 'plan.json'):
        if hashes[name] != previous['input_sha256'][name]:
            raise ValueError('Historical input binding mismatch')
    with Image.open(artifacts / 'source.png') as im:
        source = im.copy()
    graph = load_visual_graph(artifacts / 'recognized.omr')
    glyphs, metadata, binary, staff, digest = read_processed_bundle(
        artifacts / 'recognized.omr', graph
    )
    if any(r['omr_digest'] != digest for r in evidence['processed']):
        raise ValueError('Processed OMR digest mismatch')
    result = classify_handoff(source, graph, evidence, glyphs, staff)
    eligible = {i for g in result.groups if g.refinement_eligibility == ELIGIBLE for i in g.members}
    layout = json.loads((artifacts / 'plan.json').read_text())
    summary = dict(result.metrics)
    summary.update(
        {
            'decision': result.decision,
            'input_sha256': hashes,
            'eligible_beam_groups': sum(
                bool(b['heads']) and set(b['heads']) <= eligible for b in layout['beam_groups']
            ),
            'eligible_isolated_simple_symbols': sum(
                len(g.members) == 1
                and graph.symbols[g.members[0]].kind
                in {'augmentation-dot', 'flag', 'alter', 'accidental'}
                for g in result.groups
                if g.refinement_eligibility == ELIGIBLE
            ),
            'phase18_metrics_unchanged': previous['mask_metrics'],
            'partial_sent_to_phase18': 0,
            'edit_authorized_by_handoff': 0,
            'ownership_evidence_unchanged': True,
        }
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / 'handoff.json').write_text(result.to_json())
    (out / 'handoff-summary.json').write_text(
        json.dumps(summary, sort_keys=True, indent=2, allow_nan=False) + '\n'
    )
    images = {
        name: Image.new('L', source.size)
        for name in (
            'known-core',
            'known-fringe',
            'bounded-unknown',
            'protected',
            'unrelated',
            'structural',
            'eligible',
            'blocked',
        )
    }
    for g in result.groups:
        for name, runs in [
            ('known-core', g.known_core),
            ('known-fringe', g.known_fringe),
            ('bounded-unknown', g.bounded_unknown),
            ('protected', g.protected),
            ('unrelated', g.unrelated),
            ('structural', g.structural),
            ('eligible' if g.refinement_eligibility == ELIGIBLE else 'blocked', g.bounded_unknown),
        ]:
            for p in pixels_from_runs(runs):
                images[name].putpixel(p, 255)
    for name, im in images.items():
        im.save(out / (name + '-mask.png'))
    overlay = source.convert('RGBA')
    for name, color in [
        ('known-core', '#008844'),
        ('eligible', '#00aacc'),
        ('blocked', '#ff9900'),
        ('protected', '#ac00ac'),
        ('unrelated', '#ff0033'),
    ]:
        layer = Image.new('RGBA', source.size, color)
        layer.putalpha(images[name].point(lambda v: 75 if v else 0))
        overlay = Image.alpha_composite(overlay, layer)
    canvas = Image.new('RGB', (source.width + 500, source.height), 'white')
    canvas.paste(overlay.convert('RGB'), (0, 0))
    draw = ImageDraw.Draw(canvas)
    for i, line in enumerate(
        [
            'PHASE 1.9d - ANALYSIS ONLY',
            result.decision,
            'green: known source core',
            'cyan: eligible bounded analysis region',
            'orange: blocked analysis region',
            'purple: protected collision',
            'red: unrelated proximity',
            'NO EDIT AUTHORIZATION / NO SOURCE EDITS',
        ]
    ):
        draw.text((source.width + 10, 15 + i * 24), line, fill='black')
    canvas.save(out / 'handoff-overlay.png')
    if any(
        hashlib.sha256((artifacts / name).read_bytes()).hexdigest() != value
        for name, value in hashes.items()
    ):
        raise ValueError('Historical evidence changed')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inspect_handoff(args.artifacts, args.out), sort_keys=True, indent=2))
