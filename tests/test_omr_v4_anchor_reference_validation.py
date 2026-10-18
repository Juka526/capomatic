"""Diagnostic algebra is tested; independent image-reference truth stays pending."""
import json
from types import SimpleNamespace

import pytest
from PIL import Image

from scripts.omr_v4.anchor_reference_validation import (
    PROTOCOL, blind_instructions, decompose, digest, export_case, select_cases, support_stats,
)
from scripts.omr_v4.geometry_locked_feasibility import verify_inputs


def staff(interline=21.3, lines=None):
    return SimpleNamespace(valid=True, interline=interline,
        lines=lines or ((), (), ((0, 501.5), (1000, 501.5)), (), ()))


def test_repair_and_recognition_residual_are_separate():
    row = decompose(staff(), 355, 558, 5, 6, 7, 568.65)
    assert row['raw_semantic_ideal_y'] == pytest.approx(554.75)
    assert row['corrected_semantic_ideal_y'] == pytest.approx(565.4)
    assert row['absolute_target_y'] == pytest.approx(576.05)
    assert row['semantic_repair_shift_px'] == pytest.approx(10.65)
    assert row['detected_minus_raw_ideal_px'] == pytest.approx(3.25)
    assert row['corrected_ideal_minus_detected_px'] == pytest.approx(7.4)
    assert row['absolute_minus_old_plan_px'] == pytest.approx(7.4)
    assert row['relative_formula_replay_y'] == pytest.approx(568.65)
    assert row['replacement_glyph_anchor'] == 'UNDEFINED_NOT_RENDERED'


def test_sloped_polyline_is_interpolated_and_staff_spacing_is_local():
    row = decompose(staff(20, ((), (), ((0, 500), (100, 502)), (), ())), 25, 555, 5, 6, 7, 565)
    assert row['raw_semantic_ideal_y'] == 550.5
    assert row['absolute_target_y'] == 570.5
    assert row['absolute_minus_old_plan_px'] == row['corrected_ideal_minus_detected_px'] == 5.5


@pytest.mark.parametrize('unknown', [None, float('nan'), float('inf')])
def test_unknown_coordinates_fail_closed(unknown):
    with pytest.raises(ValueError):
        decompose(staff(), 10, 558, 5, unknown, 7, 568.65)
    with pytest.raises(ValueError):
        decompose(staff(), 1001, 558, 5, 6, 7, 568.65)


def test_frozen_protocol_and_blind_instruction_allowlist():
    assert digest(PROTOCOL) == PROTOCOL.with_suffix('.sha256').read_text().strip()
    protocol = json.loads(PROTOCOL.read_text())
    protocol['expected_y'] = 565.4
    protocol['repair_id'] = 'p1:m0:n1'
    public = blind_instructions(protocol, digest(PROTOCOL))
    assert set(public) == {'protocol_sha256', 'annotation_instructions', 'coordinate_convention', 'reference_fields'}
    assert 'selection' not in public
    assert 'p1:m0:n1' not in json.dumps(public)
    assert '565.4' not in json.dumps(public)


def test_selection_deterministic_without_coordinate_outcomes():
    matches = {f'n{i}': {'status': 'MATCHED', 'y_error': i} for i in range(20)}
    repairs = [{'repaired_event': {'id': f'n{i}'}} for i in range(5)]
    chosen = select_cases(matches, repairs)
    altered = {k: {**v, 'y_error': -99999} for k, v in reversed(list(matches.items()))}
    assert chosen == select_cases(altered, list(reversed(repairs)))
    assert len(chosen) == 10 and set(f'n{i}' for i in range(5)) <= set(chosen)
    with pytest.raises(ValueError):
        select_cases(matches, repairs[:4])
    matches['n0']['status'] = 'AMBIGUOUS'
    with pytest.raises(ValueError):
        select_cases(matches, repairs)


def test_blind_export_native_pixels_hash_and_no_derived_labels(tmp_path):
    image = Image.new('RGB', (12, 10))
    image.putpixel((5, 4), (25, 80, 140))
    before = image.tobytes()
    source = tmp_path / 'source.png'
    image.save(source)
    packet = tmp_path / 'packet'
    packet.mkdir()
    first = export_case(image, packet, 'case-01', [2, 1, 10, 9], digest(source))
    encoded = (packet / 'case-01.png').read_bytes()
    assert first == export_case(image, packet, 'case-01', [2, 1, 10, 9], digest(source))
    assert encoded == (packet / 'case-01.png').read_bytes()
    assert Image.open(packet / 'case-01.png').tobytes() == image.crop((2, 1, 10, 9)).tobytes()
    assert image.tobytes() == before
    assert set(first) == {'case', 'image', 'crop_sha256', 'source_sha256', 'native_page_crop_half_open', 'coordinate_conversion'}
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'input_root': str(tmp_path), 'files': {'source.png': first['source_sha256']}}))
    verify_inputs(manifest)
    source.write_bytes(b'changed')
    with pytest.raises(ValueError, match='hash mismatch'):
        verify_inputs(manifest)
    with pytest.raises(ValueError):
        export_case(image, packet, 'case-../escape', [2, 1, 10, 9], first['source_sha256'])


def test_support_centroid_is_persisted_attribution_only():
    stats = support_stats([[4, 10, 12], [5, 11, 12]])
    assert stats['bounds_half_open'] == [10, 4, 12, 6]
    assert stats['pixel_index_centroid'] == pytest.approx([32/3, 13/3])
    assert 'NOT_PHYSICAL_HEAD_GROUND_TRUTH' in stats['interpretation']
    with pytest.raises(ValueError):
        support_stats([])


def test_five_historical_repair_decompositions_are_replayable():
    fixture = json.loads((PROTOCOL.parent / 'V4_ANCHOR_REFERENCE_DECOMPOSITION.json').read_text())
    assert fixture['status'] == 'DERIVED_DIAGNOSTIC_NOT_INDEPENDENT_REFERENCE'
    assert len(fixture['repairs']) == 5
    for case in fixture['repairs']:
        s = staff(case['interline'], ((), (), case['middle_polyline'], (), ()))
        row = decompose(s, *case['detected_xy'], *case['semantic_positions'], case['expected']['old_plan_target_y'])
        for name, value in case['expected'].items():
            assert row[name] == pytest.approx(value)
