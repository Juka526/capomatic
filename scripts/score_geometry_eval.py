"""Exercise a running score API with development inputs, over real HTTP.

This checks contracts and refusal behavior, not independent musical accuracy.
No original PDF, raster, OMR or protection mask is changed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('api_url')
    parser.add_argument('files', nargs=5, type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, help='Existing JSON mapping NFC filenames to SHA-256')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    baseline = json.loads(args.baseline.read_text()) if args.baseline else {}
    import unicodedata
    bound = []
    for path in args.files:
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        name = unicodedata.normalize('NFC', path.name)
        if name in baseline and baseline[name] != sha:
            raise SystemExit('Historical source hash mismatch: ' + name)
        bound.append((path, data, sha, 'MATCH' if name in baseline else 'UNVERIFIED'))
    rows = []
    with httpx.Client(base_url=args.api_url, timeout=900) as client:
        client.get('/health').raise_for_status()
        for number, (path, data, sha, historical) in enumerate(bound, 1):
            folder = args.out / f'score-{number}'; folder.mkdir()
            started = time.monotonic()
            detected = client.post('/detect', files={'image': (path.name, data, 'application/pdf')})
            (folder / 'detect.json').write_bytes(detected.content)
            print('DETECT', number, detected.status_code, flush=True)
            detection = detected.json()
            if detected.status_code == 422:
                detection = detection.get('detail', {})
            for shift in [0, 1, -1]:
                record = {'score': number, 'name': unicodedata.normalize('NFC', path.name),
                          'source_sha256': sha, 'historical_hash_match': historical,
                          'shift': shift, 'detect_http': detected.status_code,
                          'recognition_accuracy': 'UNVERIFIED',
                          'visual_review': 'NOT_APPLICABLE_NO_OUTPUT',
                          'fixed_anchor_displacement_px': None, 'note_raster_error_xy_px': None,
                          'lyric_pixel_difference': None, 'ink_replacement_safety': 'UNVERIFIED',
                          'alpha_collisions': None, 'disconnected_relations': None,
                          'duplicate_symbols': None, 'clipping': None}
                if detection.get('detection_id'):
                    response = client.post('/render', data={
                        'detection_id': detection['detection_id'], 'semitones': shift,
                        'mode': 'key', 'output_format': 'pdf'})
                    record['render_http'] = response.status_code
                    if response.status_code == 200:
                        (folder / f'{shift:+d}.pdf').write_bytes(response.content)
                        record['output_sha256'] = hashlib.sha256(response.content).hexdigest()
                        record['visual_review'] = 'PENDING'
                        record['identity_only'] = response.headers.get('X-Capomatic-Identity') == 'true'
                        if record['identity_only']:
                            assert shift == 0 and response.content == data
                            record['all_original_bytes_preserved'] = True
                    else:
                        detail = response.json().get('detail', {})
                        report = detail.get('report', {}) if isinstance(detail, dict) else {}
                        if not isinstance(detail, dict):
                            record['error'] = detail
                        record['report'] = report
                        for key in ('semantic_ready', 'geometry_ready', 'lyric_layer_ready', 'render_ready'):
                            record[key] = report.get(key)
                    if shift != 0:
                        png = client.post('/render', data={
                            'detection_id': detection['detection_id'], 'semitones': shift,
                            'mode': 'key', 'output_format': 'png'})
                        record['png_http'] = png.status_code
                        (folder / f'{shift:+d}.png-response').write_bytes(png.content)
                        record['png_response_sha256'] = hashlib.sha256(png.content).hexdigest()
                    (folder / f'{shift:+d}-response.bin').write_bytes(response.content)
                    record['response_sha256'] = hashlib.sha256(response.content).hexdigest()
                else:
                    record.update(render_http=None, report=detection)
                record['seconds_since_detect_start'] = round(time.monotonic()-started, 2)
                record['source_unchanged'] = hashlib.sha256(path.read_bytes()).hexdigest() == sha
                rows.append(record)
                summary = {'dataset': 'development; no independent hidden validation set',
                           'recognition_accuracy': 'UNVERIFIED',
                           'verified_end_to_end_success_rate': None, 'rows': rows,
                           'http_200_count': sum(r.get('render_http') == 200 for r in rows),
                           'nonzero_http_200_count': sum(r.get('render_http') == 200
                               and r['shift'] != 0 for r in rows),
                           'identity_http_200_count': sum(r.get('identity_only', False) for r in rows),
                           'contract_pass_count': 0,
                           'intended_422_count': sum(r.get('render_http') == 422
                               and r.get('report', {}).get('render_ready') is False for r in rows)}
                (args.out / 'evaluation.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
                print('RENDER', number, shift, record['render_http'], flush=True)
    if len(rows) != 15 or any(r.get('render_http') not in {200, 422} for r in rows):
        raise SystemExit('Evaluation incomplete or unexpected API failures')


if __name__ == '__main__':
    main()
