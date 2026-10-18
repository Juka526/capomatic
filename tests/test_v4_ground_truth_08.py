"""Entirely synthetic toy images/identities/keys. Never real score labels or human evidence."""

import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image
import pytest

from scripts.research.gt08_review import (
    VERSION,
    COORDINATES,
    CATEGORIES,
    INDEPENDENCE,
    read_json,
    write_json,
    sha,
    template,
    verify_packet,
    validate_submission,
    freeze_submission,
    frozen,
    collection_status,
    overlap_conflicts,
)


def now():
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture
def packet(tmp_path):
    p = tmp_path / 'packet'
    p.mkdir()
    (p / 'instructions.txt').write_text(
        'Synthetic unit fixture only, no actual human observations.'
    )
    cases = []
    for i in range(5):
        ident = f'{i:020x}'
        image = p / (ident + '.png')
        Image.new('RGB', (4, 3), (i * 40, 50, 100)).save(image)
        cases.append(
            {'case_id': ident, 'image': image.name, 'sha256': sha(image), 'width': 4, 'height': 3}
        )
    write_json(
        p / 'packet.json',
        {
            'version': VERSION,
            'coordinate_system': COORDINATES,
            'cases': cases,
            'instructions_sha256': sha(p / 'instructions.txt'),
        },
    )
    return p


def observation(packet, role, category='UNKNOWN', person=None):
    d = template(packet, role)
    d.update(
        person_id=person or 'synthetic_' + role,
        origin='HUMAN_SOURCE_REVIEW',
        signed_at=now(),
        expertise='Synthetic unit fixture, no real reader or source data',
    )
    d['independence'] = {**INDEPENDENCE, 'other_reader_labels_seen': role == 'ADJUDICATOR'}
    for row in d['cases']:
        row.update(
            category_runs=[{'category': category, 'runs': [[y, 0, 4] for y in range(3)]}],
            uncertainty_status='PRESENT' if category in ['UNKNOWN', 'MIXED'] else 'NONE_OBSERVED',
            uncertainty_note='Synthetic fixture only, never accepted human observations',
        )
    return d


@pytest.fixture(scope='module')
def keys(tmp_path_factory):
    root = tmp_path_factory.mktemp('synthetic-custodian')
    private = root / 'private.pem'
    public = root / 'public.pem'
    subprocess.run(
        [
            'openssl',
            'genpkey',
            '-algorithm',
            'RSA',
            '-pkeyopt',
            'rsa_keygen_bits:2048',
            '-out',
            str(private),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ['openssl', 'pkey', '-in', str(private), '-pubout', '-out', str(public)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return private, public


def collection(tmp_path, packet, keys, pin=True):
    root = tmp_path / 'collection'
    root.mkdir()
    (root / 'submitted-labels').mkdir()
    (root / 'adjudication').mkdir()
    links = [
        {'case_id': c['case_id'], 'page_bbox': [0, 0, 4, 3]} for c in verify_packet(packet).values()
    ]
    write_json(root / 'custodian-case-map.json', links)
    write_json(
        root / 'collection-policy.json',
        {
            'version': VERSION,
            'packet_sha256': sha(packet / 'packet.json'),
            'trusted_custodian_key_sha256': sha(keys[1]) if pin else None,
            'case_map_sha256': sha(root / 'custodian-case-map.json'),
        },
    )
    return root


def export(tmp_path, data, packet, keys, role, tag=None):
    folder = tmp_path / (tag or role)
    folder.mkdir()
    raw = folder / 'original.json'
    # Preserve noncanonical whitespace as actual raw bytes in the custody test.
    raw.write_text(json.dumps(data, indent=1) + '\n\n')
    receipt = folder / 'custody.json'
    write_json(
        receipt,
        {
            'version': 'gt08-human-custody/1',
            'packet_sha256': sha(packet / 'packet.json'),
            'submission_sha256': sha(raw),
            'role': role,
            'person_id': data['person_id'],
            'custodian_id': 'synthetic_custodian',
            'verified_at': now(),
            'human_identity_verified': True,
            'independence_exclusions_verified': True,
            'non_automated_observations_verified': True,
            'verification_evidence_sha256': 'a' * 64,
        },
    )
    sig = folder / 'signature.bin'
    subprocess.run(
        ['openssl', 'dgst', '-sha256', '-sign', str(keys[0]), '-out', str(sig), str(receipt)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return raw, receipt, sig, keys[1]


def freeze_toy(tmp_path, root, packet, keys, role, **kwargs):
    data = observation(packet, role, **kwargs)
    if role == 'ADJUDICATOR':
        data['reader_freezes'] = {
            r: sha(root / 'submitted-labels' / r / 'freeze.json') for r in ['A', 'B']
        }
    paths = export(tmp_path, data, packet, keys, role)
    freeze_submission(root, packet, *paths, role)
    return data, paths


def test_blank_forms_are_not_labels_and_source_packet_is_immutable(packet):
    before = {p.name: sha(p) for p in packet.iterdir()}
    with pytest.raises(ValueError):
        validate_submission(template(packet, 'A'), packet, 'A')
    assert before == {p.name: sha(p) for p in packet.iterdir()}
    d = observation(packet, 'A')
    masks = validate_submission(d, packet, 'A')
    assert len(masks) == 5 and all(np.all(m == 4) for m in masks.values())


@pytest.mark.parametrize(
    'bad',
    [
        'packet',
        'coords',
        'missing_case',
        'duplicate_case',
        'category',
        'blank',
        'overlap',
        'gap',
        'float',
        'bool',
        'escape',
        'uncertainty',
        'unknown_omitted',
        'ai',
        'exposure',
        'person',
    ],
)
def test_no_missing_observations_or_unverified_machine_labels_are_silently_filled(packet, bad):
    d = observation(packet, 'A')
    row = d['cases'][0]
    if bad == 'packet':
        d['packet_sha256'] = 'b' * 64
    if bad == 'coords':
        d['coordinate_system'] = 'scaled edges'
    if bad == 'missing_case':
        d['cases'].pop()
    if bad == 'duplicate_case':
        d['cases'][1] = copy.deepcopy(row)
    if bad == 'category':
        row['category_runs'][0]['category'] = 'BACKGROUND'
    if bad == 'blank':
        row['category_runs'] = []
    if bad == 'overlap':
        row['category_runs'].append({'category': 'CONFIRMED_TEXT', 'runs': [[0, 0, 1]]})
    if bad == 'gap':
        row['category_runs'][0]['runs'].pop()
    if bad == 'float':
        row['category_runs'][0]['runs'][0][0] = 0.5
    if bad == 'bool':
        row['category_runs'][0]['runs'][0][0] = False
    if bad == 'escape':
        row['category_runs'][0]['runs'][0][2] = 5
    if bad == 'uncertainty':
        row['uncertainty_note'] = ''
    if bad == 'unknown_omitted':
        row['uncertainty_status'] = 'NONE_OBSERVED'
    if bad == 'ai':
        d['origin'] = 'AI_GENERATED'
    if bad == 'exposure':
        d['independence']['predictions_omr_or_coordinator_material_seen'] = True
    if bad == 'person':
        d['person_id'] = None
    with pytest.raises(ValueError):
        validate_submission(d, packet, 'A')


def test_nonfinite_duplicate_json_and_unexpected_packet_files_fail_closed(tmp_path, packet):
    p = tmp_path / 'bad.json'
    p.write_text('{"a":NaN}')
    with pytest.raises(ValueError):
        read_json(p)
    p.write_text('{"a":1,"a":2}')
    with pytest.raises(ValueError):
        read_json(p)
    (packet / 'prediction.json').write_text('{}')
    with pytest.raises(ValueError):
        verify_packet(packet)


def test_no_external_trust_no_freeze_even_if_json_claims_human(tmp_path, packet, keys):
    root = collection(tmp_path, packet, keys, pin=False)
    paths = export(tmp_path, observation(packet, 'A'), packet, keys, 'A')
    with pytest.raises(ValueError, match='trusted custodian'):
        freeze_submission(root, packet, *paths, 'A')
    assert list((root / 'submitted-labels').iterdir()) == []
    status = collection_status(root, packet)
    assert (
        status['decision'] == 'WAITING_FOR_HUMAN_REVIEW' and not status['collision_audit_executed']
    )


def test_raw_bytes_separate_freezes_and_tamper_detection(tmp_path, packet, keys):
    root = collection(tmp_path, packet, keys)
    _, paths = freeze_toy(tmp_path, root, packet, keys, 'A')
    before = paths[0].read_bytes()
    saved = root / 'submitted-labels/A/raw-submission.json'
    assert before == saved.read_bytes() and (saved.stat().st_mode & 0o222) == 0
    freeze_toy(tmp_path, root, packet, keys, 'B')
    assert sha(root / 'submitted-labels/A/freeze.json') != sha(
        root / 'submitted-labels/B/freeze.json'
    )
    with pytest.raises(ValueError, match='overwrite'):
        freeze_submission(root, packet, *paths, 'A')
    saved.chmod(0o644)
    saved.write_bytes(before + b' ')
    with pytest.raises(ValueError, match='raw bytes'):
        frozen(root, 'A', packet, sha(keys[1]))


def test_receipt_signature_and_raw_hash_are_required(tmp_path, packet, keys):
    root = collection(tmp_path, packet, keys)
    paths = export(tmp_path, observation(packet, 'A'), packet, keys, 'A')
    paths[0].write_text(paths[0].read_text() + ' ')
    with pytest.raises(ValueError, match='bound'):
        freeze_submission(root, packet, *paths, 'A')
    assert list((root / 'submitted-labels').iterdir()) == []


def test_same_person_cannot_be_two_independent_readers(tmp_path, packet, keys):
    root = collection(tmp_path, packet, keys)
    freeze_toy(tmp_path, root, packet, keys, 'A', person='same_synthetic')
    paths = export(tmp_path, observation(packet, 'B', person='same_synthetic'), packet, keys, 'B')
    with pytest.raises(ValueError, match='separate'):
        freeze_submission(root, packet, *paths, 'B')


def test_adjudicator_needs_both_frozen_readers_and_separate_identity(tmp_path, packet, keys):
    root = collection(tmp_path, packet, keys)
    d = observation(packet, 'ADJUDICATOR')
    d['reader_freezes'] = {'A': 'a' * 64, 'B': 'b' * 64}
    paths = export(tmp_path, d, packet, keys, 'ADJUDICATOR', tag='early')
    with pytest.raises(ValueError):
        freeze_submission(root, packet, *paths, 'ADJUDICATOR')
    freeze_toy(tmp_path, root, packet, keys, 'A')
    freeze_toy(tmp_path, root, packet, keys, 'B')
    d = observation(packet, 'ADJUDICATOR', person='synthetic_A')
    d['reader_freezes'] = {
        r: sha(root / 'submitted-labels' / r / 'freeze.json') for r in ['A', 'B']
    }
    paths = export(tmp_path, d, packet, keys, 'ADJUDICATOR', tag='not_separate')
    with pytest.raises(ValueError, match='separate'):
        freeze_submission(root, packet, *paths, 'ADJUDICATOR')


@pytest.mark.parametrize(
    'category,expected',
    [('UNKNOWN', 'TEXT_EXTENTS_UNRESOLVED'), ('CONFIRMED_NON_TEXT', 'TEXT_EXTENTS_ADJUDICATED')],
)
def test_even_adjudicated_synthetic_extents_never_authorize_composition(
    tmp_path, packet, keys, category, expected
):
    root = collection(tmp_path, packet, keys)
    freeze_toy(tmp_path, root, packet, keys, 'A')
    freeze_toy(tmp_path, root, packet, keys, 'B')
    freeze_toy(tmp_path, root, packet, keys, 'ADJUDICATOR', category=category)
    status = collection_status(root, packet)
    assert status['decision'] == expected and status['actual_verified_primary_submissions'] == 2
    assert (
        status['confirmed_text_contacts'] == 'UNKNOWN' and status['composition_authorized'] is False
    )
    assert not status['collision_audit_executed']


def test_overlapping_case_conflicts_are_not_resolved_by_choosing_a_case():
    assert (
        overlap_conflicts(
            {'a': np.ones((2, 2), np.uint8), 'b': np.full((2, 2), 2, np.uint8)},
            {'a': [0, 0, 2, 2], 'b': [1, 0, 3, 2]},
        )
        == 2
    )


@pytest.mark.parametrize('bad', ['wrong_key_pin', 'bad_signature'])
def test_self_selected_key_or_unsigned_custody_cannot_freeze_labels(tmp_path, packet, keys, bad):
    root = collection(tmp_path, packet, keys)
    paths = export(tmp_path, observation(packet, 'A'), packet, keys, 'A')
    if bad == 'wrong_key_pin':
        policy = root / 'collection-policy.json'
        d = read_json(policy)
        d['trusted_custodian_key_sha256'] = 'b' * 64
        policy.chmod(0o644)
        policy.write_text(json.dumps(d))
    else:
        paths[2].write_bytes(b'invalid synthetic signature')
    with pytest.raises(ValueError):
        freeze_submission(root, packet, *paths, 'A')
    assert list((root / 'submitted-labels').iterdir()) == []


@pytest.mark.parametrize('bad', ['wrong_freeze_hash', 'predates_freezes'])
def test_adjudication_hash_binding_and_order_are_not_optional(tmp_path, packet, keys, bad):
    root = collection(tmp_path, packet, keys)
    freeze_toy(tmp_path, root, packet, keys, 'A')
    freeze_toy(tmp_path, root, packet, keys, 'B')
    d = observation(packet, 'ADJUDICATOR')
    d['reader_freezes'] = {
        r: sha(root / 'submitted-labels' / r / 'freeze.json') for r in ['A', 'B']
    }
    if bad == 'wrong_freeze_hash':
        d['reader_freezes']['A'] = 'c' * 64
    else:
        d['signed_at'] = '2020-01-01T00:00:00+00:00'
    paths = export(tmp_path, d, packet, keys, 'ADJUDICATOR')
    with pytest.raises(ValueError):
        freeze_submission(root, packet, *paths, 'ADJUDICATOR')
    assert list((root / 'adjudication').iterdir()) == []


def test_partial_and_overlapping_uncertainty_survives_adjudication(tmp_path, packet, keys):
    root = collection(tmp_path, packet, keys)
    freeze_toy(tmp_path, root, packet, keys, 'A')
    freeze_toy(tmp_path, root, packet, keys, 'B')
    d = observation(packet, 'ADJUDICATOR', category='CONFIRMED_NON_TEXT')
    d['reader_freezes'] = {
        r: sha(root / 'submitted-labels' / r / 'freeze.json') for r in ['A', 'B']
    }
    d['cases'][0]['category_runs'][0]['category'] = 'UNKNOWN'
    d['cases'][0]['uncertainty_status'] = 'PRESENT'
    paths = export(tmp_path, d, packet, keys, 'ADJUDICATOR')
    freeze_submission(root, packet, *paths, 'ADJUDICATOR')
    status = collection_status(root, packet)
    assert status['decision'] == 'TEXT_EXTENTS_PARTIALLY_ADJUDICATED'
    assert (
        status['overlapping_case_conflict_pixels'] == 12
        and status['per_case_uncertain_pixels'] == 12
    )
    assert status['confirmed_text_contacts'] == 'UNKNOWN' and not status['composition_authorized']


def test_prepare_cannot_write_into_historical_evidence(tmp_path):
    from scripts.research.gt08_prepare import prepare

    with pytest.raises(ValueError, match='historical'):
        prepare(
            tmp_path / 'gt01', tmp_path / 'a', tmp_path / 'b', tmp_path / 'gt06', tmp_path / 'a/new'
        )
    occupied = tmp_path / 'existing'
    occupied.mkdir()
    with pytest.raises(ValueError, match='New non-symlink'):
        prepare(tmp_path / 'gt01', tmp_path / 'a', tmp_path / 'b', tmp_path / 'gt06', occupied)


def test_new_neutral_template_does_not_contain_suggested_answers_or_old_labels(packet):
    from scripts.research.gt08_prepare import INSTRUCTIONS

    d = template(packet, 'A')
    assert d['origin'] is None and d['person_id'] is None
    assert all(
        row['category_runs'] == [] and row['uncertainty_status'] is None for row in d['cases']
    )
    assert all(name in INSTRUCTIONS for name in CATEGORIES)
    assert all(
        value not in INSTRUCTIONS for value in ['1982', '2026', '233', '4135', '47 candidate']
    )


def test_private_custody_template_never_attests_to_a_human_or_observation(packet):
    from scripts.research.gt08_review import custody_template

    d = custody_template(packet)
    assert d['packet_sha256'] == sha(packet / 'packet.json')
    assert all(v is None for k, v in d.items() if k not in {'version', 'packet_sha256'})
