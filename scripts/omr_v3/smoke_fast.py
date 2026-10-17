"""Three fixed, gated regression cases for PRs; no acceptance accuracy claims."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.omr_v3.core import ScoreError, process
from scripts.omr_v3.evaluate import EVAL, _chord_only_renderer, _paddle_detector

CASES = (
    ('clean', 'synthetic/dev/syn101/clean.pdf', 'full_score'),
    ('ordinary', 'synthetic/dev/syn101/ordinary.pdf', 'full_score'),
    ('fallback', 'scores/naui.jpg', 'chord_only'),
)


def run(out: Path) -> None:
    """Fail on unexpected modes/integrity; allow an explicit coverage rejection."""
    out.mkdir(parents=True, exist_ok=True)
    detector, renderer = _paddle_detector(), _chord_only_renderer()
    runs = []
    for name, filename, expected in CASES:
        source = EVAL / filename
        row = {'case': name, 'source': filename}
        try:
            result = process(source.read_bytes(), source.suffix, 2, 'key',
                             chord_detector=detector, chord_only_renderer=renderer)
        except ScoreError as exc:
            row.update(mode='error', status=exc.status, reason=str(exc))
            assert (expected == 'chord_only' and exc.status == 422
                    and str(exc).startswith('chord_only:insufficient_chord_coverage')), row
        else:
            row.update(mode=result.mode, integrity=result.report.get('integrity'),
                       decision=result.report.get('decision'), stages_ms=result.stages_ms)
            assert result.mode == expected, row
            if expected == 'full_score':
                assert result.report.get('integrity', {}).get('ok') is True, row
        finally:
            runs.append(row)
            (out / 'smoke-summary.json').write_text(json.dumps({'tier': 'regression-smoke', 'runs': runs}, indent=2))
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.out)
