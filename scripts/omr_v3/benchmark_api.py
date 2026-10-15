"""Measure real endpoint latency on one score. Accuracy is NOT measured here
(see scripts/omr_v3/evaluate.py, which compares against reference MusicXML).

Usage: python scripts/omr_v3/benchmark_api.py http://localhost:7860 score.pdf --runs 3 [--mode capo --semitones -2] [--token JWT]
Upload, server work and download are all included in the timing.
"""
import argparse
import math
import statistics
import time
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('url')
    ap.add_argument('file', type=Path)
    ap.add_argument('--runs', type=int, default=3)
    ap.add_argument('--semitones', type=int, default=2)
    ap.add_argument('--mode', choices=('key', 'capo'), default='key')
    ap.add_argument('--token', help='Auth0 access token when the API requires login')
    args = ap.parse_args()
    import requests

    headers = {'Authorization': f'Bearer {args.token}'} if args.token else {}
    samples = []
    for i in range(args.runs):
        start = time.perf_counter()
        with args.file.open('rb') as f:
            resp = requests.post(args.url.rstrip('/') + '/api/v3/score/transpose.pdf', headers=headers,
                                 files={'file': (args.file.name, f)},
                                 data={'semitones': str(args.semitones), 'mode': args.mode}, timeout=900)
        ms = (time.perf_counter() - start) * 1000
        print(f'run={i + 1} status={resp.status_code} elapsed_ms={ms:.1f} '
              f'server_ms={resp.headers.get("X-OMR-Total-Ms", "-")} warnings={resp.headers.get("X-OMR-Review-Warnings", "-")}')
        if resp.status_code == 200 and resp.content.startswith(b'%PDF-'):
            samples.append(ms)
        else:
            print('FAILED: not counted as a success')
    if samples:
        values = sorted(samples)
        p95 = values[max(0, math.ceil(0.95 * len(values)) - 1)]
        print(f'completed={len(samples)}/{args.runs} p50_ms={statistics.median(samples):.1f} '
              f'p95_nearest_rank_ms={p95:.1f} max_ms={max(samples):.1f}')
    print('Accuracy is NOT measured by this script; see scripts/omr_v3/evaluate.py.')


if __name__ == '__main__':
    main()
