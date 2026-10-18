"""Source review preparation must not manufacture human confirmation."""

import copy
from PIL import Image
import pytest

from scripts.research import gt12_measure_context as gt


def inventory():
    return {
        'printed_measure': 3,
        'events': [
            {
                'source_event_id': f'event-{i}',
                'kind': 'REST' if i == 0 else 'NOTE',
                'written_pitch': p,
                'onset': str(i),
                'duration': '1',
                'voice': None,
                'physical_detected_center': [50 + i * 20, 80],
            }
            for i, p in enumerate([None, 'B-3', 'C4', 'F4'])
        ],
    }


def test_omr_agreement_and_agent_readings_cannot_become_human_confirmation():
    inv = inventory()
    before = copy.deepcopy(inv)
    record = gt.checklist(inv, 'a' * 64)
    assert inv == before
    assert len(record['omr_observations']) == 4
    assert record['owner_review']['actual_submission'] is None
    assert record['provenance_boundary']['independent_labels_collected'] == 0
    report = gt.review_gate(record)
    assert report['combined_rendering'] == 'BLOCKED'
    assert report['owner_confirmed_events'] == []
    assert report['source_recognition_completeness'] == 'UNVERIFIED'


def test_fixed_measure_cannot_be_replaced():
    inv = inventory()
    inv['printed_measure'] = 32
    with pytest.raises(ValueError, match='fixed printed measure'):
        gt.checklist(inv, 'x')


def test_preparation_tool_does_not_authenticate_filled_forms_as_human_source():
    record = gt.checklist(inventory(), 'a' * 64)
    for k in record['owner_review']:
        record['owner_review'][k] = 'synthetic test input, not a human submission'
    assert gt.review_gate(record)['combined_rendering'] == 'BLOCKED'


def test_crop_and_sheet_keep_source_pixels_and_dimensions(tmp_path):
    source = tmp_path / 'source.png'
    im = Image.new('RGB', (100, 120), 'white')
    im.putpixel((49, 89), (10, 60, 110))
    im.save(source)
    original = source.read_bytes()
    out = tmp_path / 'out'
    out.mkdir()
    bbox = (10, 20, 70, 110)
    gt.review_images(source, out, bbox)
    with Image.open(out / 'original-bb.png') as crop:
        assert crop.size == (60, 90)
        assert crop.tobytes() == im.crop(bbox).tobytes()
    assert source.read_bytes() == original
    first = {p.name: p.read_bytes() for p in out.iterdir()}
    gt.review_images(source, out, bbox)
    assert {p.name: p.read_bytes() for p in out.iterdir()} == first


@pytest.mark.parametrize('bbox', [(-1, 0, 10, 10), (0, 0, 101, 10), (10, 10, 9, 20)])
def test_invalid_review_geometry_rejected(tmp_path, bbox):
    source = tmp_path / 'source.png'
    Image.new('RGB', (100, 100)).save(source)
    with pytest.raises(ValueError, match='Invalid crop'):
        gt.review_images(source, tmp_path, bbox)


def test_source_mode_is_explicit_no_conversion(tmp_path):
    source = tmp_path / 'gray.png'
    Image.new('L', (100, 100)).save(source)
    with pytest.raises(ValueError, match='Explicit RGB'):
        gt.review_images(source, tmp_path, (0, 0, 10, 10))


def test_prepare_never_overwrites_existing_evidence(tmp_path):
    with pytest.raises(ValueError, match='fresh output directory'):
        gt.prepare(tmp_path)


def test_real_candidate_bytes_are_preserved_without_confirmation(tmp_path):
    candidate = tmp_path / 'received.txt'
    original = 'OWNER_REVIEW_CANDIDATE\n주 / 님 / 의\nPENDING_VISUAL_CONFIRMATION'.encode()
    candidate.write_bytes(original)
    out = tmp_path / 'review'
    out.mkdir()
    record = gt.checklist(inventory(), 'a' * 64)
    gt.retain_candidate(record, candidate, out)
    assert candidate.read_bytes() == (out / 'owner-review-candidate.txt').read_bytes() == original
    owner = record['owner_review']
    assert owner['events'] is None and owner['exact_lyric_rows'] is None
    assert not owner['actual_submission']['source_verified']
    assert gt.review_gate(record)['combined_rendering'] == 'BLOCKED'
    assert record['provenance_boundary']['independent_labels_collected'] == 0
