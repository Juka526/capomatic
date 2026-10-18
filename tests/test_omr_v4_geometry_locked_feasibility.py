"""Focused tests for independent B1 geometry and immutable evidence binding."""

import hashlib
import json
from types import SimpleNamespace

import pytest

from scripts.omr_v4.geometry_locked_feasibility import (
    absolute_target_y,
    changed_pixel_count,
    line_y,
    overlap,
    validate_output_directory,
    verify_inputs,
)


def test_absolute_target_uses_corrected_pitch_not_relative_plan_delta():
    staff = SimpleNamespace(
        lines=((), (), ((83.0, 501.5), (2398.0, 501.5)), (), ()), interline=21.3, valid=True
    )
    target = absolute_target_y(staff, 355.0, 7)
    assert target == pytest.approx(576.05)
    existing_relative_plan = 558.0 + 21.3 / 2
    assert target - existing_relative_plan == pytest.approx(7.4)


def test_original_staff_polyline_interpolation_and_bounds():
    assert line_y(((0.0, 10.0), (10.0, 20.0), (20.0, 15.0)), 15.0) == 17.5
    with pytest.raises(ValueError):
        line_y(((0.0, 10.0), (10.0, 20.0)), 11.0)
    with pytest.raises(ValueError):
        absolute_target_y(SimpleNamespace(), 1, None)


def test_bbox_overlap_is_positive_area_not_touch_or_ink_claim():
    assert overlap((0, 0, 5, 5), (4, 4, 6, 6))
    assert not overlap((0, 0, 5, 5), (5, 1, 8, 3))


def test_input_hash_verification_rejects_tamper(tmp_path):
    evidence = tmp_path / 'source'
    evidence.write_bytes(b'original')
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(
        json.dumps(
            {
                'input_root': str(tmp_path),
                'files': {'source': hashlib.sha256(b'original').hexdigest()},
            }
        )
    )
    assert verify_inputs(manifest)[1]['verified_files'] == 1
    evidence.write_bytes(b'changed')
    with pytest.raises(ValueError, match='Input hash mismatch'):
        verify_inputs(manifest)


@pytest.mark.parametrize(
    'points,x',
    [
        (((0.0, 1.0), (1.0, float('nan'))), 0.5),
        (((1.0, 1.0), (0.0, 2.0)), 0.5),
        (((0.0, 1.0), (1.0, 2.0)), float('inf')),
    ],
)
def test_staff_polyline_rejects_invalid_geometry(points, x):
    with pytest.raises(ValueError):
        line_y(points, x)


@pytest.mark.parametrize('interline', [float('nan'), float('inf'), 0, -1])
def test_absolute_target_rejects_nonfinite_or_invalid_staff_spacing(interline):
    staff = SimpleNamespace(
        lines=((), (), ((0.0, 1.0), (1.0, 1.0)), (), ()), interline=interline, valid=True
    )
    with pytest.raises(ValueError):
        absolute_target_y(staff, 0.5, 1)


def test_output_cannot_alias_evidence(tmp_path):
    evidence = tmp_path / 'evidence'
    evidence.mkdir()
    for output in (evidence, evidence / 'nested', tmp_path):
        with pytest.raises(ValueError):
            validate_output_directory(output, evidence)
    alias = tmp_path / 'alias'
    alias.symlink_to(evidence, target_is_directory=True)
    with pytest.raises(ValueError):
        validate_output_directory(alias, evidence)
    output = tmp_path / 'output'
    output.mkdir()
    (output / 'summary.json').symlink_to(evidence / 'source')
    with pytest.raises(ValueError):
        validate_output_directory(output, evidence)


def test_exact_pixel_comparison_detects_one_blue_channel_change():
    from PIL import Image

    original = Image.new('RGB', (2, 2), (0, 0, 0))
    annotated = original.copy()
    annotated.putpixel((0, 0), (0, 0, 1))
    assert changed_pixel_count(original, annotated) == 1
    assert changed_pixel_count(original, original.copy()) == 0


def test_committed_registration_is_exact_pre_measurement_protocol():
    from pathlib import Path

    fixture = Path(__file__).parents[1] / 'docs' / 'V4_GEOMETRY_LOCKED_EXCERPTS.json'
    assert (
        hashlib.sha256(fixture.read_bytes()).hexdigest()
        == '71d3e2012c86e83880b768498d6ac3b6b8a2a0d33f05be262cded7067b0abbfb'
    )
    registration = json.loads(fixture.read_text())
    assert [e['measure_number'] for e in registration['excerpts']] == ['1', '2', '3']
    assert len({i for e in registration['excerpts'] for i in e['semantic_ids']}) == 30
