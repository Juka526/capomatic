"""Synthetic partial-system admission and unchanged coordinate contracts."""

import copy

from music21 import note, stream
from PIL import Image
import pytest

from scripts.research import gt13a_full_system as gt


def fixture(number):
    m = stream.Measure(number=number)
    for n in [note.Rest(quarterLength=1), note.Note('B-3'), note.Note('C4'), note.Note('F4')]:
        m.append(n)
    rows = [
        {
            'id': f'm{number}-{i}',
            'symbol_id': f's{i}',
            'omr_measure_index': number - 1,
            'local_offset': str(i),
            'duration': '1',
            'kind': 'REST' if n.isRest else 'NOTE',
            'pitch': None if n.isRest else n.pitch.nameWithOctave,
            'voice': None,
            'bbox': [10 + i * 20, 20, 20 + i * 20, 30],
        }
        for i, n in enumerate(m.notesAndRests)
    ]
    geometry = {'printed_measure': number, 'left': {'x': 100}, 'right': {'x': 500}}
    graph_measure = {'bounds': [101, 20, 501, 60]}
    return m, rows, geometry, graph_measure


def test_confirmation_never_propagates_to_other_measures_or_same_melody():
    assert gt.eligible(3, {3})
    assert not any(gt.eligible(i, {3}) for i in [1, 2, 4])
    m, rows, g, gm = fixture(1)
    result = gt.measure_inventory(m, rows, g, gm, {3})
    assert result['content_status'] == 'UNVERIFIED'
    assert all(r['recognition'] == 'OMR_RECOGNIZED' for r in result['events'])
    assert result['render_action'] == 'EXPLICIT_GAP_NO_NOTATION_OR_LYRIC_GUESS'


def test_owner_verified_m3_scope_and_one_pixel_disagreement_remain_explicit():
    args = fixture(3)
    result = gt.measure_inventory(*args, {3})
    assert result['content_status'] == 'OWNER_VERIFIED'
    assert result['omr_minus_physical_candidate_px'] == [1, 1]
    assert not result['boundary_independent_ground_truth']
    assert result['recognized_duration_total'] == '4'


def test_source_timing_mismatch_fails_closed():
    m, rows, g, gm = fixture(2)
    rows[1]['duration'] = '1/2'
    with pytest.raises(ValueError, match='timing correspondence'):
        gt.measure_inventory(m, rows, g, gm, {3})


def test_source_pitch_mismatch_fails_closed():
    m, rows, g, gm = fixture(2)
    rows[1]['pitch'] = 'C4'
    with pytest.raises(ValueError, match='written pitch'):
        gt.measure_inventory(m, rows, g, gm, {3})


def test_staff_polyline_intermediate_vertices_are_not_flattened():
    staff = {'lines': [[[10, y], [50, y + 5], [90, y]] for y in [10, 20, 30, 40, 50]]}
    before = copy.deepcopy(staff)
    a = gt.scaffold((100, 80), staff, [10, 90])
    assert a.getpixel((50, 15)) > 0
    assert a.getpixel((50, 10)) == 0
    assert staff == before
    assert a.tobytes() == gt.scaffold((100, 80), staff, [10, 90]).tobytes()


def test_nonfinite_geometry_rejected():
    staff = {'lines': [[[10, y], [90, y]] for y in [10, 20, 30, 40, 50]]}
    staff['lines'][0][0][0] = float('nan')
    with pytest.raises(ValueError, match='nonfinite'):
        gt.scaffold((100, 80), staff, [10, 90])


def test_outside_staff_domain_requires_explicit_persisted_barline_bounds():
    staff = {'lines': [[[10, y], [89, y]] for y in [10, 20, 30, 40, 50]]}
    with pytest.raises(ValueError, match='explicit persisted barline'):
        gt.scaffold((100, 80), staff, [90])
    mask = gt.scaffold((100, 80), staff, [90], {90: [88, 9, 92, 52]})
    assert mask.getpixel((90, 9)) > 0 and mask.getpixel((90, 52)) > 0
    with pytest.raises(ValueError, match='explicit persisted barline'):
        gt.scaffold((100, 80), staff, [90], {90: [10, 9, 20, 52]})


def test_source_panel_preserves_original_crop_pixels():
    crop = Image.new('RGB', (2300, 410), (120, 130, 140))
    labeled = gt.label(crop, 'Synthetic test')
    assert labeled.crop((0, 100, 2300, 510)).tobytes() == crop.tobytes()
