"""Synthetic research controls; no copyrighted score or Audiveris execution."""

from dataclasses import replace
from fractions import Fraction
from types import SimpleNamespace

import pytest

from backend.omr_v4.visual_graph import Staff
from scripts.research import paired_ground_truth_01 as experiment


def staff():
    return Staff(
        's',
        '1',
        'p',
        'sys',
        '1',
        1,
        10,
        tuple(((0, y), (50, y + 5), (100, y + 5)) for y in (10, 20, 30, 40, 50)),
        True,
        '',
    )


def test_original_polyline_and_corrected_semantics_define_absolute_coordinate():
    s = staff()
    assert experiment.line_y(s.lines[2], 25) == 32.5
    # Corrected source pitch +6 and target +7 are separate from any glyph center.
    source_y = experiment.absolute_y(s, 25, 6)
    target_y = experiment.absolute_y(s, 25, 7)
    assert source_y == 62.5 and target_y == 67.5
    detected_y = 55.1
    assert detected_y + (target_y - source_y) != target_y
    assert experiment.line_y(s.lines[2], 75) == 35


@pytest.mark.parametrize(
    'points,x', [(((0, 0), (0, 1)), 0), (((0, 0), (10, 1)), 11), (((0, 0), (10, float('nan'))), 2)]
)
def test_invalid_or_extrapolated_geometry_fails_closed(points, x):
    with pytest.raises(ValueError):
        experiment.line_y(points, x)


def test_invalid_staff_and_unknown_pitch_fail_closed():
    for s, p in [
        (replace(staff(), valid=False), 0),
        (replace(staff(), interline=0), 0),
        (staff(), None),
    ]:
        with pytest.raises(ValueError):
            experiment.absolute_y(s, 25, p)


def test_frozen_predictions_reject_changed_added_or_missing_file(tmp_path):
    root = tmp_path / 'predictions'
    root.mkdir()
    a = root / 'a.json'
    a.write_text('{}')
    expected = experiment.file_hashes(root)
    experiment.verify_files(root, expected)
    a.write_text('{"altered":true}')
    with pytest.raises(ValueError):
        experiment.verify_files(root, expected)
    a.write_text('{}')
    extra = root / 'new'
    extra.write_text('added')
    with pytest.raises(ValueError):
        experiment.verify_files(root, expected)
    extra.unlink()
    a.unlink()
    with pytest.raises(ValueError):
        experiment.verify_files(root, expected)


def test_symlink_prediction_evidence_rejected(tmp_path):
    (tmp_path / 'source').write_text('x')
    (tmp_path / 'alias').symlink_to(tmp_path / 'source')
    with pytest.raises(ValueError):
        experiment.file_hashes(tmp_path)


def test_deterministic_fraction_serialization_and_nonfinite_rejection(tmp_path):
    a, b = tmp_path / 'a.json', tmp_path / 'b.json'
    value = {'onset': Fraction(3, 4), 'nested': [{'staff': staff()}]}
    experiment.dump(a, value)
    experiment.dump(b, value)
    assert a.read_bytes() == b.read_bytes()
    with pytest.raises(ValueError):
        experiment.dump(a, {'bad': float('nan')})


def test_reference_cannot_overwrite_prediction_directory(tmp_path):
    root = tmp_path / 'predictions'
    root.mkdir()
    freeze = tmp_path / 'freeze.json'
    experiment.dump(freeze, {'phase': 'SOURCE_ONLY_PREDICTIONS_FROZEN', 'prediction_files': {}})
    with pytest.raises(ValueError, match='separate'):
        experiment.evaluate(tmp_path / 'source.png', root / 'ref', freeze, root)
    assert not (root / 'ref').exists()


def test_reference_not_started_before_prediction_freeze(tmp_path, monkeypatch):
    root = tmp_path / 'predictions'
    root.mkdir()
    freeze = tmp_path / 'freeze.json'
    experiment.dump(freeze, {'phase': 'UNFROZEN', 'prediction_files': {}})
    monkeypatch.setattr(
        experiment, 'recognize', lambda *_: pytest.fail('Reference accessed too early')
    )
    with pytest.raises(ValueError, match='must freeze'):
        experiment.evaluate(tmp_path / 'source.png', tmp_path / 'ref', freeze, root)


def test_collision_is_envelope_only_and_does_not_establish_ownership():
    assert experiment.overlap((0, 0, 10, 10), (9, 9, 12, 12))
    assert not experiment.overlap((0, 0, 10, 10), (10, 0, 12, 2))
    assert not experiment.overlap(None, (0, 0, 1, 1))
