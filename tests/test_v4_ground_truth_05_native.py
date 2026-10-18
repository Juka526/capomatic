"""Configuration-only controls: no model imports, inference or external inputs."""

import ast
from pathlib import Path

import pytest

from scripts.research.gt05_native_probe import configuration


def test_baseline_and_omp_case_have_identical_constructor_options():
    assert (
        configuration('recognizer-baseline-trace')
        == configuration('recognizer-omp1')
        == {'enable_mkldnn': False}
    )


def test_predictor_thread_control_changes_only_one_constructor_field():
    base = configuration('recognizer-baseline-trace')
    one = configuration('recognizer-cpu1')
    assert one == base | {'cpu_threads': 1}
    assert 'engine_config' not in one


def test_ir_control_preserves_thread_and_backend_defaults_without_combination():
    expected = {
        'enable_mkldnn': False,
        'engine_config': {
            'paddle_static': {
                'run_mode': 'paddle',
                'cpu_threads': 10,
                'enable_cinn': False,
                'enable_new_ir': False,
            }
        },
    }
    assert configuration('recognizer-newir-off') == expected
    assert configuration('detector-newir-off') == expected


def test_unknown_or_combined_cases_fail_closed():
    for case in ['anything', 'recognizer-omp1-cpu1', 'recognizer-cpu1-newir-off']:
        with pytest.raises(ValueError, match='Unregistered'):
            configuration(case)


def test_probe_has_no_production_ocr_or_score_recognition_path():
    path = Path('scripts/research/gt05_native_probe.py')
    text = path.read_text()
    tree = ast.parse(text)
    assert 'recognized.musicxml' not in text and 'source.png' not in text
    assert not any(
        isinstance(n, ast.ImportFrom) and n.module and n.module.startswith('backend.')
        for n in ast.walk(tree)
    )
