"""Lightweight orchestration checks; never start OMR or Docker."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.omr_v3.core import ScoreError
from scripts.omr_v3 import smoke_fast

ROOT = Path(__file__).resolve().parents[1]


def test_workflows_separate_pr_smoke_from_manual_acceptance():
    yaml = pytest.importorskip('yaml')
    fast = yaml.load((ROOT / '.github/workflows/omr-v3-fast.yml').read_text(), Loader=yaml.BaseLoader)
    full = yaml.load((ROOT / '.github/workflows/omr-v3-eval.yml').read_text(), Loader=yaml.BaseLoader)
    assert set(fast['on']) == {'pull_request'}
    assert set(full['on']) == {'workflow_dispatch'}
    assert full['on']['workflow_dispatch']['inputs']['publish']['default'] == 'false'
    assert full['on']['workflow_dispatch']['inputs']['fresh_holdout']['default'] == 'true'
    assert fast['jobs']['smoke']['timeout-minutes'] == '20'
    commands = '\n'.join(step.get('run', '') for step in fast['jobs']['smoke']['steps'])
    for expensive in ('scripts.omr_v3.evaluate', 'scripts.omr_v3.synth', 'benchmark_api',
                      'review_bundle', 'smoke_multipage', 'gate=False'):
        assert expensive not in commands
    assert 'python -m pytest -q' in commands
    assert '/detect' in commands and '/api/v3/score/transpose.zip' in commands
    assert 'inputs.publish' in full['jobs']['publish']['if']


@pytest.fixture
def processor(monkeypatch):
    def convert(data, suffix, semitones, mode, **kwargs):
        assert semitones == 2 and mode == 'key'
        assert kwargs.get('gate', True) is True
        result_mode = 'chord_only' if suffix == '.jpg' else 'full_score'
        return SimpleNamespace(mode=result_mode, report={'integrity': {'ok': True}}, stages_ms={})
    mock = Mock(side_effect=convert)
    monkeypatch.setattr(smoke_fast, 'process', mock)
    monkeypatch.setattr(smoke_fast, '_paddle_detector', lambda: Mock())
    monkeypatch.setattr(smoke_fast, '_chord_only_renderer', lambda: Mock())
    return mock


def test_fast_smoke_runs_exactly_three_fixed_gated_cases(processor, tmp_path):
    smoke_fast.run(tmp_path)
    assert processor.call_count == 3
    report = json.loads((tmp_path / 'smoke-summary.json').read_text())
    assert [r['case'] for r in report['runs']] == ['clean', 'ordinary', 'fallback']
    assert all('holdout' not in r['source'] for r in report['runs'])


def test_fast_smoke_accepts_explicit_coverage_failure(processor, tmp_path):
    convert = processor.side_effect
    processor.side_effect = lambda *a, **kw: (
        _reject_coverage() if a[1] == '.jpg' else convert(*a, **kw))
    smoke_fast.run(tmp_path)
    report = json.loads((tmp_path / 'smoke-summary.json').read_text())
    assert report['runs'][-1]['status'] == 422
    assert processor.call_count == 3


def _reject_coverage():
    raise ScoreError('chord_only:insufficient_chord_coverage: Please upload a clearer PDF/image')


@pytest.mark.parametrize('failure', ['mode', 'integrity', 'service'])
def test_fast_smoke_fails_closed_without_ungated_retry(processor, tmp_path, failure):
    if failure == 'service':
        processor.side_effect = ScoreError('tool unavailable', 503)
    else:
        processor.side_effect = None
        processor.return_value = SimpleNamespace(
            mode='chord_only' if failure == 'mode' else 'full_score',
            report={'integrity': {'ok': failure != 'integrity'}}, stages_ms={})
    with pytest.raises(AssertionError):
        smoke_fast.run(tmp_path)
    assert processor.call_count == 1
    assert (tmp_path / 'smoke-summary.json').exists()


@pytest.mark.parametrize('fresh,seeds,expected', [
    ('true', '', ['492', '493', '494', '495']),
    ('true', '9001 9002', ['9001', '9002']),
    ('false', '', []),
])
def test_manual_holdout_configuration_is_reproducible(fresh, seeds, expected, tmp_path):
    import os
    import subprocess
    import sys

    yaml = pytest.importorskip('yaml')
    workflow = yaml.load((ROOT / '.github/workflows/omr-v3-eval.yml').read_text(), Loader=yaml.BaseLoader)
    step = next(s for s in workflow['jobs']['evaluate']['steps']
                if s.get('name') == 'End-to-end evaluation (PaddleOCR chords)')
    assert step['env'] == {'FRESH_HOLDOUT': '${{ inputs.fresh_holdout }}',
                           'HOLDOUT_SEEDS': '${{ inputs.holdout_seeds }}'}
    binaries = tmp_path / 'bin'
    binaries.mkdir()
    docker = binaries / 'docker'
    docker.write_text(f'#!{sys.executable}\nimport json,sys\n'
                      'from pathlib import Path\n'
                      'Path("docker-args.json").write_text(json.dumps(sys.argv[1:]))\n')
    docker.chmod(0o755)
    git = binaries / 'git'
    git.write_text('#!/bin/sh\nprintf "fixture-revision\\n"\n')
    git.chmod(0o755)
    subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', step['run']], cwd=tmp_path,
                   env={**os.environ, 'PATH': str(binaries) + os.pathsep + os.environ['PATH'],
                        'GITHUB_RUN_ID': '123', 'FRESH_HOLDOUT': fresh, 'HOLDOUT_SEEDS': seeds},
                   check=True)
    args = json.loads((tmp_path / 'docker-args.json').read_text())
    if expected:
        assert args[args.index('--fresh-holdout-seeds') + 1:] == expected
    else:
        assert '--fresh-holdout-seeds' not in args
    assert (tmp_path / 'omr-v3-evidence/source-revision.txt').read_text().strip() == 'fixture-revision'


def test_full_acceptance_is_manual_only_and_retains_artifacts():
    yaml = pytest.importorskip('yaml')
    workflow = yaml.load((ROOT / '.github/workflows/omr-v3-eval.yml').read_text(), Loader=yaml.BaseLoader)
    # Excludes push and every PR action, including opened/synchronize/labeled.
    assert set(workflow['on']) == {'workflow_dispatch'}
    evaluate = workflow['jobs']['evaluate']
    assert 'if' not in evaluate
    assert evaluate['timeout-minutes'] == '150'
    assert 'ref' not in evaluate['steps'][0].get('with', {})
    assert 'pull_request' not in str(workflow)
    assert workflow['jobs']['publish']['if'] == (
        "${{ always() && github.event_name == 'workflow_dispatch' && inputs.publish == true }}")
    assert any(step.get('uses') == 'actions/upload-artifact@v4'
               and step['if'] == 'always()' for step in evaluate['steps'])
