"""Aggregate measured HTTP evidence and frozen source-only negative checks.

This reporting command is offline. Review data must never enter recognition or
rendering. Source-reader disagreement is not adjudicated musical ground truth.
"""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

import numpy as np
from PIL import Image

from scripts.scan_review_compare import compare, sig_location


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', required=True, type=Path)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    root = args.results
    http = json.loads((root/'verified-http/evaluation.json').read_text())
    baseline = {s['index']: s for s in json.loads(args.baseline.read_text())['scans']}
    decisions = json.loads((root/'source-review/admission.json').read_text())
    captures = {json.loads((p/'coordinates.json').read_text())['png_sha256']: p
                for p in (root/'verified-source-evidence').iterdir()}
    assert len(http['rows']) == 15
    assert {(r['index'], r['shift']) for r in http['rows']} == {(i, s) for i in range(1, 6) for s in (0, 1, -1)}
    scans, comparisons = [], []
    for index in range(1, 6):
        rows = [r for r in http['rows'] if r['index'] == index]
        assert all(r['source_sha256'] == baseline[index]['source_sha256'] and r['source_unchanged'] for r in rows)
        page = next(r for r in rows if r['shift'] == 1)['report']['pages'][0]
        meta = page['source_coordinates']
        folder = captures[meta['png_sha256']]
        ownership = json.loads((folder/'ownership.json').read_text())
        analysis = ownership['component_analysis']
        source_read = root/'source-review'/f'review-{index}.txt'
        source_image = root/'source-review'/f'source-{index}.png'
        assert sha(source_image) == sha(folder/'source.png')
        checks_file = root/'source-review'/f'checks-{index}.json'
        checks = json.loads(checks_file.read_text())
        xml = root/'verified-http'/f'score-{index}'/'recognized.musicxml'
        try:
            review = compare(xml.read_bytes(), checks)
        except ValueError as exc:
            review = {'status': 'REVIEW_MAPPING_UNSUPPORTED', 'error': str(exc), 'full_page_accuracy': None}
        check = checks[0]
        review['sig_reference'] = sig_location((folder/'recognition.omr').read_bytes(), str(check['measure']), check.get('event_index', 0))
        review.update(input_index=index, source_read_sha256=sha(source_read),
                      source_image_sha256=sha(source_image), checks_sha256=sha(checks_file),
                      recognized_sha256=sha(xml), runtime_injected=False,
                      admission=decisions[str(index)])
        comparisons.append(review)
        with zipfile.ZipFile(folder/'ink-masks.zip') as masks:
            with Image.open(io.BytesIO(masks.read('component_coverage.png'))) as image:
                coverage = np.asarray(image).copy() > 0
            with Image.open(io.BytesIO(masks.read('protected.png'))) as image:
                protected = np.asarray(image).copy() > 0
        assert coverage.shape == protected.shape == (meta['height'], meta['width'])
        assert np.all(coverage != protected)
        assert int(coverage.sum()) == analysis['source_component_coverage_pixels']
        assert int(protected.sum()) == analysis['protected_pixels']
        codes = Counter(code for b in analysis['blockers'] for code in b['codes'])
        scans.append({'index': index, 'name': rows[0]['name'],
            'source_sha256': rows[0]['source_sha256'], 'raster_size': meta['raster_size'],
            'raster_identity_ready': ownership['raster_identity_ready'],
            'geometry_ready': ownership['geometry_ready'],
            'semantic_ready': page['semantic_ready'], 'lyric_layer_ready': page['lyric_layer_ready'],
            'render_ready': page['render_ready'], 'admission': decisions[str(index)],
            'selection_eligible': False, 'direction_selected': None,
            'component_coverage_pixels': analysis['source_component_coverage_pixels'],
            'protected_pixels': analysis['protected_pixels'],
            'unresolved_contact_pixels': analysis['ambiguous_pixels'],
            'raw_component_blocker_count': len(analysis['blockers']),
            'raw_component_blocker_codes': dict(codes),
            'structure_issues': analysis['structure_issues'],
            'protected_residual_candidates_not_verified_lyrics': len(analysis['lyric_candidates']),
            'object_regions': len(analysis['object_regions']),
            'mask_partition_verified': True,
            'evidence_path': str(folder.relative_to(root)),
            'first_blocker': next(r for r in rows if r['shift'] == 1)['report'].get('first_blocker'),
            'secondary_blockers': page['reasons'][1:],
            'measurements': page['measurements'],
            'missing_persisted_source_images': False,
            'genuine_unavoidable_collisions': None,
            'unsupported_required_notation_count': None})
    test_log = root/'final-full-pytest.log'
    test_text = test_log.read_text()
    totals = re.search(r'(\d+) passed, (\d+) skipped', test_text)
    if totals is None:
        raise ValueError('Complete regression summary missing')
    skips = [line for line in test_text.splitlines() if line.startswith('SKIPPED ')]
    if len(skips) != int(totals.group(2)):
        raise ValueError('Skip summary incomplete')
    result = {'status': 'FUNCTIONALLY_INCOMPLETE', 'base_commit': 'e4fb603fae2edaa5ce405cb3ae955a6d659d7d4d',
        'branch': 'feature/ordinary-scan-first-real-success', 'raw_artifacts': str(root),
        'dataset': 'five existing development scans; not hidden validation',
        'counts': {'detect_http_200': sum(r['detect_http'] == 200 for r in http['rows'][::3]),
            'identity_pdf_success': sum(r.get('identity_only', False) for r in http['rows']),
            'nonzero_pdf_http_success': sum(r['shift'] != 0 and r['pdf_http'] == 200 for r in http['rows']),
            'nonzero_pdf_http_422': sum(r['shift'] != 0 and r['pdf_http'] == 422 for r in http['rows']),
            'nonzero_png_http_422': sum(r.get('png_http') == 422 for r in http['rows']),
            'verified_nonzero_preservation_pass': 0, 'output_music_review_pass': 0},
        'selection': {'status': 'NO_VERIFIED_ELIGIBLE_CANDIDATE', 'input': None, 'shift': None,
            'recognition_correction_out_of_scope': True,
            'unresolved_required_semantic_counts': 'UNKNOWN; selected checks are lower-bound evidence only',
            'target_collision_counts': 'UNKNOWN; no admissible full-page target plan'},
        'validation': {'full_suite_passed': int(totals.group(1)),
            'full_suite_skipped': int(totals.group(2)), 'skipped_cases': skips,
            'test_log_sha256': sha(test_log), 'targeted_counts_not_added': True},
        'recognition_accuracy': None, 'music_review_status': 'SOURCE_ONLY_READINGS; NO_VALIDATED_NONZERO_OUTPUT',
        'scans': scans, 'source_review_comparisons': comparisons,
        'http_rows': [{k:v for k,v in r.items() if k != 'report'} for r in http['rows']],
        'http_code_sha256': json.loads((root/'http-code-hashes.json').read_text()),
        'offline_tool_sha256': {name: sha(Path(__file__).resolve().parent/name)
            for name in ('first_real_report.py', 'scan_review_compare.py')},
        'artifact_sha256': {str(p.relative_to(root)): sha(p)
            for base in ('verified-http', 'verified-source-evidence', 'source-review')
            for p in sorted((root/base).rglob('*')) if p.is_file()}}
    for name in ('run_final_eval.py', 'http-code-hashes.json', 'verified-http.log',
                 'final-full-pytest.log', 'resumed-pytest.log', 'review-fix-tests.log',
                 'code-review.txt', 'report-review.txt'):
        if (root/name).exists():
            result['artifact_sha256'][name] = sha(root/name)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result['counts']))


if __name__ == '__main__':
    main()
