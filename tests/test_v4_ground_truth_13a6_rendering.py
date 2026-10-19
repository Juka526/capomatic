"""Preregistered whole-note phases and owner-binding negative controls; no Audiveris."""

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from scripts.research.gt11_complete_measure import FONT
from scripts.research.gt13a6_tie_rendering import (
    whole_head,
    segment_spec,
    confirmed_record,
    QUESTION,
)
from scripts.research.gt13a6_cross_system_tie import render_segments
from scripts.research.paired_ground_truth_01 import sha


def staff(inter):
    return {
        'interline': inter,
        'lines': [[[0, 200 + i * inter], [1000, 200 + i * inter + 0.5]] for i in range(5)],
    }


@pytest.mark.parametrize('inter', [14, 18, 24])
@pytest.mark.parametrize('phase', [0, 0.25, 0.5, 0.75])
@pytest.mark.parametrize('target', ['A3', 'G3'])
def test_open_whole_note_independent_raster_center_and_determinism(inter, phase, target):
    if not FONT.exists():
        pytest.skip('Frozen FreeSerif font unavailable')
    args = ((1000, 600), staff(inter), 400 + phase, target)
    head, r = whole_head(*args)
    again, rr = whole_head(*args)
    assert head.tobytes() == again.tobytes() and r == rr
    b = head.getbbox()
    center = [(b[0] + b[2] - 1) / 2, (b[1] + b[3] - 1) / 2]
    assert max(abs(a - t) for a, t in zip(center, r['requested_anchor'])) <= 0.5
    assert r['transparent_hole_pixels'] > 0
    # Translation must not change glyph size/coverage, including its transparent interior.
    shifted, s = whole_head((1000, 600), staff(inter), 440 + phase, target)
    assert head.crop(b).tobytes() == shifted.crop(shifted.getbbox()).tobytes()
    assert r['font_size'] == s['font_size']


def test_source_offsets_attached_to_target_raster_bounds_not_raw_center():
    a = segment_spec(
        'OUTGOING',
        [[180, 70], [190, 80], [210, 80], [220, 70]],
        [169, 50, 191, 67],
        [169, 59, 192, 76],
        [0, 0, 250, 110],
    )
    b = segment_spec(
        'INCOMING',
        [[20, 180], [30, 190], [50, 190], [60, 180]],
        [49, 160, 71, 177],
        [49, 169, 72, 186],
        [0, 140, 250, 250],
    )
    masks, r = render_segments((250, 260), a, b)
    assert a['dy'] == b['dy'] == 9
    assert all(max(map(abs, c['attachment_residual'])) <= 0.5 for c in r['segments'])
    assert all(not mask.crop((0, 110, 250, 140)).getbbox() for mask in masks.values())


def synthetic_binding(tmp):
    # Synthetic unit fixture only: never an owner submission or retained research evidence.
    packet = tmp / 'packet'
    packet.mkdir()
    (packet / 'source-tie-review-sheet.png').write_bytes(b'SYNTHETIC REVIEW BYTES')
    source = 'synthetic-source-digest'
    (packet / 'tie-owner-checklist.json').write_text(
        json.dumps(
            {
                'source_sha256': source,
                'review_sheet_sha256': sha(packet / 'source-tie-review-sheet.png'),
            }
        )
    )
    (packet / 'tie-source-evidence.json').write_text(json.dumps({'source_sha256': source}))
    (packet / 'review-freeze.json').write_text(
        json.dumps({'files': {p.name: sha(p) for p in packet.iterdir()}})
    )
    record = {
        'record_type': 'GT13A6_OWNER_SOURCE_CONFIRMATION',
        'status': 'OWNER_CONFIRMED',
        'owner_response_verbatim': '`OWNER_CONFIRMED`',
        'question': QUESTION,
        'response_origin': 'SYNTHETIC_UNIT_TEST_NOT_HUMAN_EVIDENCE',
        'source_sha256': source,
        'source_curves': ['sheet#1:4818', 'sheet#1:4798'],
        'base_sha': '20af28ea54d45d980da57ec3084790a2001b4d4e',
        'review_producer_commit_sha': '596c8d716301d5c5bfc927f9a9d63652b65fa38c',
    }
    for field, name in [
        ('review_sheet_sha256', 'source-tie-review-sheet.png'),
        ('checklist_sha256', 'tie-owner-checklist.json'),
        ('source_evidence_sha256', 'tie-source-evidence.json'),
        ('review_freeze_sha256', 'review-freeze.json'),
    ]:
        record[field] = sha(packet / name)
    path = tmp / 'synthetic-test-record.json'
    path.write_text(json.dumps(record))
    return path, packet, record


def test_confirmation_binding_is_read_only(tmp_path):
    p, packet, r = synthetic_binding(tmp_path)
    before = p.read_bytes()
    assert confirmed_record(p, packet) == r and p.read_bytes() == before
    (packet / 'source-tie-review-sheet.png').write_bytes(b'CHANGED')
    with pytest.raises(ValueError, match='hash mismatch'):
        confirmed_record(p, packet)


@pytest.mark.parametrize(
    'field,value',
    [
        ('status', 'OWNER_UNCERTAIN'),
        ('owner_response_verbatim', ''),
        ('question', 'another tie'),
        ('response_origin', ''),
        ('source_curves', []),
        ('review_producer_commit_sha', 'wrong revision'),
        ('source_sha256', 'wrong source'),
    ],
)
def test_confirmation_missing_or_mismatched_provenance_rejected(tmp_path, field, value):
    p, packet, r = synthetic_binding(tmp_path)
    r[field] = value
    p.write_text(json.dumps(r))
    with pytest.raises(ValueError):
        confirmed_record(p, packet)


def test_unavailable_confirmation_and_unsupported_whole_pitch_fail_closed(tmp_path):
    with pytest.raises(FileNotFoundError):
        confirmed_record(tmp_path / 'absent.json', tmp_path)
    with pytest.raises(ValueError, match='Unsupported'):
        whole_head((1000, 600), staff(18), 400, 'C3')
