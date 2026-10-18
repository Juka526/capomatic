"""Extract already-produced V3 artifacts; no recognition, ownership or handoff run."""

import argparse
import json
from pathlib import Path
from PIL import Image

from backend.omr_v4.masks import raster_digest
from backend.omr_v4.source_ink import read_processed_bundle
from backend.omr_v4.v3_evidence import attribute_handoff, extract_evidence, json_bytes, sha
from backend.omr_v4.visual_graph import load_visual_graph


def extract(artifacts, out):
    previous = json.loads((artifacts / 'source-ink-1.9c/ink-summary.json').read_text())
    bindings = previous['input_sha256']
    # All optional semantic snapshots are copies, not regenerated semantics.
    semantic = json.loads((artifacts / 'semantic-report.json').read_text())
    handoff = json.loads((artifacts / 'refinement-handoff/handoff.json').read_text())
    evidence = json.loads((artifacts / 'source-ink-1.9c/ink-evidence.json').read_text())
    with Image.open(artifacts / 'source.png') as source:
        if handoff['source_digest'] != raster_digest(source):
            raise ValueError('Handoff source mismatch')
    if handoff['ownership_evidence_digest'] != sha(
        json.dumps(evidence, sort_keys=True, allow_nan=False).encode()
    ):
        raise ValueError('Handoff evidence mismatch')
    if any(r['omr_digest'] != bindings['recognized.omr'] for r in evidence['processed']):
        raise ValueError('Processed support OMR mismatch')
    # Read all external snapshots before creating the bundle.
    snapshots = {
        name: (artifacts / name).read_bytes()
        for name in ('pre-ledger.musicxml', 'recognized.musicxml')
    }
    graph = load_visual_graph(artifacts / 'recognized.omr')
    glyphs, _, binary, staff, _ = read_processed_bundle(artifacts / 'recognized.omr', graph)
    with Image.open(artifacts / 'source.png') as source:
        research = attribute_handoff(graph, glyphs, staff, binary, handoff, source)
    additional = {
        'pre-ledger.musicxml': (
            snapshots['pre-ledger.musicxml'],
            'EXTERNAL_V3_SNAPSHOT_COPY',
        ),
        'post-ledger.musicxml': (
            snapshots['recognized.musicxml'],
            'EXTERNAL_V3_SNAPSHOT_COPY',
        ),
        'ledger-repair-provenance.json': (
            json_bytes(semantic['repair_provenance']),
            'EXTERNAL_V4_CAPTURE_NOT_OMR',
        ),
        'integrity-report.json': (
            json_bytes(semantic),
            'EXTERNAL_V4_DIAGNOSTIC_REPORT_NOT_PRODUCTION_APPROVAL',
        ),
        'blocker-attribution.json': (
            json_bytes(research),
            'MEASURED_SUPPORT_INTERSECTIONS_NOT_OWNERSHIP',
        ),
    }
    manifest = extract_evidence(
        artifacts / 'source.png',
        artifacts / 'recognized.omr',
        out,
        expected_source_sha=bindings['source.png'],
        expected_omr_sha=bindings['recognized.omr'],
    )
    for name, (data, status) in additional.items():
        (out / name).write_bytes(data)
        manifest['files'][name] = {'sha256': sha(data), 'status': status}
    manifest['research_inputs'] = {
        str(p.relative_to(artifacts)): sha(p.read_bytes())
        for p in [
            artifacts / 'semantic-report.json',
            artifacts / 'refinement-handoff/handoff.json',
            artifacts / 'source-ink-1.9c/ink-evidence.json',
            artifacts / 'source-ink-1.9c/ink-summary.json',
        ]
    }
    (out / 'manifest.json').write_bytes(json_bytes(manifest))
    return research


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = extract(args.artifacts, args.out)
    print(json.dumps({k: v for k, v in result.items() if k != 'groups'}, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
