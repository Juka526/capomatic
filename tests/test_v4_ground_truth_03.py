"""Synthetic workflow checks; no human observations, models or Audiveris."""

import json
from pathlib import Path

import pytest

from scripts.research.gt03_pilot import prepare, PILOT
from scripts.research.gt03_chord_run import run
from scripts.research.paired_ground_truth_01 import dump, file_hashes, sha


def fixture(tmp):
    packet = tmp / 'gt02' / 'packet'
    packet.mkdir(parents=True)
    links = [
        {
            'case_id': f'test-{page}-{i:02}',
            'coordinator_page_label': page,
            'printed_measure_candidate': i,
        }
        for page in ['A', 'Bb', 'G']
        for i in range(1, 38)
    ]
    dump(packet / 'cases.json', {'cases': [{'case_id': x['case_id']} for x in links]})
    for role in ['A', 'B']:
        dump(
            packet / f'blank-{role}.json',
            {
                'status': 'PENDING',
                'cases': [{'case_id': x['case_id'], 'status': 'PENDING'} for x in links],
            },
        )
    index = tmp / 'gt02' / 'private.json'
    dump(index, {'case_linkage': links, 'packet_file_hashes': file_hashes(packet)})
    return packet, index


def test_pilot_keeps_all_111_cases_and_blank_forms_unchanged(tmp_path):
    packet, index = fixture(tmp_path)
    before = file_hashes(packet)
    result = prepare(packet, index, tmp_path / 'gt03')
    assert len(result['priority_case_ids']) == 14
    assert len(result['all_case_ids']) == 111
    expected = {f'test-{p}-{i:02}' for p, ns in PILOT.items() for i in ns}
    assert set(result['priority_case_ids']) == expected
    assert file_hashes(packet) == before
    assert result['packet_cases_sha256'] == sha(packet / 'cases.json')
    private = json.loads((tmp_path / 'gt03/custodian-only.json').read_text())
    assert private['actual_independent_labels'] == 0


def test_schedule_has_no_answer_or_coordinator_fields_and_is_deterministic(tmp_path):
    packet, index = fixture(tmp_path)
    prepare(packet, index, tmp_path / 'one')
    prepare(packet, index, tmp_path / 'two')
    assert file_hashes(tmp_path / 'one') == file_hashes(tmp_path / 'two')
    schedule = json.loads((tmp_path / 'one/reader-schedule.json').read_text())
    assert set(schedule) == {
        'version',
        'packet_cases_sha256',
        'priority_case_ids',
        'all_case_ids',
        'instructions',
    }


def test_modified_packet_or_private_lineage_fails_closed(tmp_path):
    packet, index = fixture(tmp_path)
    data = json.loads(index.read_text())
    data['case_linkage'][0]['printed_measure_candidate'] = 2
    dump(index, data)
    with pytest.raises(ValueError, match='linkage'):
        prepare(packet, index, tmp_path / 'bad')
    (packet / 'injected-answer.json').write_text('{}')
    with pytest.raises(ValueError, match='unexpected'):
        prepare(packet, index, tmp_path / 'bad')


def test_never_overwrites_gt02_or_existing_workflow(tmp_path):
    packet, index = fixture(tmp_path)
    with pytest.raises(ValueError, match='GT-02'):
        prepare(packet, index, packet.parent / 'new')
    prepare(packet, index, tmp_path / 'out')
    with pytest.raises(ValueError, match='New output'):
        prepare(packet, index, tmp_path / 'out')


def test_ocr_rejects_changed_or_extra_inputs_before_loading_models(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    for name in ['source.png', 'audiveris.mxl', 'recognized.omr']:
        (source / name).write_bytes(b'synthetic')
    expected = file_hashes(source)
    (source / 'source.png').write_bytes(b'changed')
    with pytest.raises(ValueError, match='binding mismatch'):
        run(source, tmp_path / 'out', expected)
    with pytest.raises(ValueError, match='preregistered'):
        run(source, tmp_path / 'out', expected | {'reference.png': 'not-allowed'})
    with pytest.raises(ValueError, match='immutable'):
        run(source, source / 'out', expected)
