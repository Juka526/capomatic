"""Human text-review schema and byte-preserving custody. No label generation or editing."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess

import numpy as np
from PIL import Image

from scripts.research.gt02_reference_packet import require, exact, nonempty
from scripts.research.paired_ground_truth_01 import sha, file_hashes

VERSION = 'gt08-text-review/1'
COORDINATES = 'crop-local pixel-index centers; (0,0) first center; x right/y down; native size; RLE [y,left,right_exclusive]'
CATEGORIES = ('CONFIRMED_TEXT', 'CONFIRMED_NON_TEXT', 'MIXED', 'UNKNOWN')
INDEPENDENCE = {
    'project_or_coordinator_participation': False,
    'predictions_omr_or_coordinator_material_seen': False,
    'ai_or_automated_classification_used': False,
    'reader_labels_seen_before_both_freezes': False,
    'human_source_inspection': True,
}


def read_json(path):
    path = Path(path)
    require(
        path.is_file() and not path.is_symlink() and path.stat().st_size <= 32 * 1024 * 1024,
        'Missing/symlink/oversized JSON',
    )

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON field')
            result[key] = value
        return result

    def invalid(value):
        raise ValueError('Nonfinite JSON number')

    return json.loads(path.read_bytes(), object_pairs_hook=pairs, parse_constant=invalid)


def exclusive(path, content):
    path = Path(path)
    require(
        not any(p.is_symlink() for p in [path, *path.parents]), 'Symlink custody path forbidden'
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(content)


def write_json(path, data):
    exclusive(path, (json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())


def utc(value):
    require(isinstance(value, str), 'Explicit UTC timestamp required')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('Invalid UTC timestamp') from exc
    require(
        result.utcoffset() is not None and result.utcoffset().total_seconds() == 0,
        'Timestamp must be UTC',
    )
    require(result <= datetime.now(timezone.utc), 'Future timestamp forbidden')
    return result


def token(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{3,80}', value) is not None


def digest(value):
    return isinstance(value, str) and re.fullmatch(r'[a-f0-9]{64}', value) is not None


def verify_packet(packet):
    packet = Path(packet)
    require(not packet.is_symlink(), 'Symlink packet forbidden')
    data = read_json(packet / 'packet.json')
    exact(data, {'version', 'coordinate_system', 'cases', 'instructions_sha256'})
    require(
        data['version'] == VERSION and data['coordinate_system'] == COORDINATES,
        'Packet coordinate/version mismatch',
    )
    require(
        sha(packet / 'instructions.txt') == data['instructions_sha256'],
        'Neutral instructions changed',
    )
    require(
        isinstance(data['cases'], list) and len(data['cases']) == 5,
        'Historical five cases required',
    )
    cases = {}
    expected = {'packet.json', 'instructions.txt'}
    for case in data['cases']:
        exact(case, {'case_id', 'image', 'sha256', 'width', 'height'})
        ident = case['case_id']
        require(
            isinstance(ident, str) and re.fullmatch(r'[a-f0-9]{20}', ident) and ident not in cases,
            'Case identity mismatch',
        )
        require(case['image'] == ident + '.png', 'Unsafe image path')
        require(
            all(type(case[k]) is int and 0 < case[k] <= 10000 for k in ['width', 'height'])
            and case['width'] * case['height'] <= 2_000_000,
            'Invalid case dimensions',
        )
        image = packet / case['image']
        require(sha(image) == case['sha256'], 'Source-only image bytes changed')
        require(
            Image.open(image).size == (case['width'], case['height']), 'Implicit resizing forbidden'
        )
        cases[ident] = case
        expected.add(case['image'])
    require(set(file_hashes(packet)) == expected, 'Unexpected/missing reviewer packet files')
    return cases


def template(packet, role):
    cases = verify_packet(packet)
    data = {
        'version': VERSION,
        'packet_sha256': sha(Path(packet) / 'packet.json'),
        'coordinate_system': COORDINATES,
        'role': role,
        'person_id': None,
        'origin': None,
        'signed_at': None,
        'expertise': None,
        'independence': {**dict.fromkeys(INDEPENDENCE), 'other_reader_labels_seen': None},
        'cases': [
            {
                'case_id': ident,
                'category_runs': [],
                'uncertainty_status': None,
                'uncertainty_note': None,
            }
            for ident in cases
        ],
    }
    if role == 'ADJUDICATOR':
        data['reader_freezes'] = {'A': None, 'B': None}
    return data


def custody_template(packet):
    """A blank private form, never a human attestation or an accepted receipt."""
    verify_packet(packet)
    return {
        'version': 'gt08-human-custody/1',
        'packet_sha256': sha(Path(packet) / 'packet.json'),
        **dict.fromkeys(
            [
                'submission_sha256',
                'role',
                'person_id',
                'custodian_id',
                'verified_at',
                'human_identity_verified',
                'independence_exclusions_verified',
                'non_automated_observations_verified',
                'verification_evidence_sha256',
            ]
        ),
    }


def decode_case(row, case):
    exact(row, {'case_id', 'category_runs', 'uncertainty_status', 'uncertainty_note'})
    require(nonempty(row['uncertainty_note']), 'Explicit uncertainty explanation required')
    require(
        row['uncertainty_status'] in ['PRESENT', 'NONE_OBSERVED'],
        'Explicit unknown/boundary status required',
    )
    require(
        isinstance(row['category_runs'], list) and 0 < len(row['category_runs']) <= 4,
        'No blank/default observations; explicit category runs required',
    )
    mask = np.zeros((case['height'], case['width']), dtype='uint8')
    seen = set()
    for region in row['category_runs']:
        exact(region, {'category', 'runs'})
        kind = region['category']
        require(kind in CATEGORIES and kind not in seen, 'Invalid/duplicate category')
        seen.add(kind)
        runs = region['runs']
        require(
            isinstance(runs, list) and 0 < len(runs) <= 1_000_000,
            'Explicit bounded pixel runs required',
        )
        previous = None
        for run in runs:
            require(
                isinstance(run, list) and len(run) == 3 and all(type(v) is int for v in run),
                'Integer [y,left,right_exclusive] required',
            )
            y, left, right = run
            require(
                0 <= y < case['height'] and 0 <= left < right <= case['width'],
                'Run outside native crop',
            )
            require(
                previous is None or tuple(run) > previous, 'Runs must be in deterministic order'
            )
            require(not np.any(mask[y, left:right]), 'Overlapping category observations')
            mask[y, left:right] = CATEGORIES.index(kind) + 1
            previous = tuple(run)
    require(np.all(mask), 'Unobserved pixels: never silently fill')
    uncertain = bool(np.any(mask >= 3))
    require(
        (row['uncertainty_status'] == 'PRESENT') == uncertain,
        'Unknown/mixed regions must be explicit and consistent',
    )
    return mask


def validate_submission(data, packet, role):
    fields = {
        'version',
        'packet_sha256',
        'coordinate_system',
        'role',
        'person_id',
        'origin',
        'signed_at',
        'expertise',
        'independence',
        'cases',
    }
    if role == 'ADJUDICATOR':
        fields.add('reader_freezes')
    exact(data, fields)
    cases = verify_packet(packet)
    require(role in {'A', 'B', 'ADJUDICATOR'} and data['role'] == role, 'Wrong reviewer role')
    require(
        data['version'] == VERSION
        and data['coordinate_system'] == COORDINATES
        and data['packet_sha256'] == sha(Path(packet) / 'packet.json'),
        'Wrong packet/version/coordinates',
    )
    require(
        token(data['person_id']) and data['origin'] == 'HUMAN_SOURCE_REVIEW',
        'Actual human origin and pseudonymous identity required; blank/AI labels rejected',
    )
    utc(data['signed_at'])
    require(nonempty(data['expertise']), 'Human expertise/eligibility context required')
    expected = {**INDEPENDENCE, 'other_reader_labels_seen': role == 'ADJUDICATOR'}
    exact(data['independence'], expected)
    require(
        all(
            type(data['independence'][k]) is bool and data['independence'][k] == v
            for k, v in expected.items()
        ),
        'Ineligible/exposed/automated review',
    )
    require(
        isinstance(data['cases'], list) and len(data['cases']) == len(cases),
        'Complete five-case coverage required',
    )
    masks = {}
    for row in data['cases']:
        require(
            isinstance(row, dict) and row.get('case_id') in cases and row['case_id'] not in masks,
            'Missing/duplicate/wrong case',
        )
        masks[row['case_id']] = decode_case(row, cases[row['case_id']])
    require(set(masks) == set(cases), 'Complete case coverage required')
    if role == 'ADJUDICATOR':
        exact(data['reader_freezes'], {'A', 'B'})
        require(
            all(digest(v) for v in data['reader_freezes'].values()),
            'Both frozen primary hashes required',
        )
    return masks


def signed_custody(submission, receipt, signature, public_key, pin, packet, role):
    require(
        digest(pin) and sha(public_key) == pin,
        'Externally pinned custodian key required; no self-selected key',
    )
    check = subprocess.run(
        [
            'openssl',
            'dgst',
            '-sha256',
            '-verify',
            str(public_key),
            '-signature',
            str(signature),
            str(receipt),
        ],
        capture_output=True,
        timeout=15,
    )
    require(check.returncode == 0, 'Custodian signature verification failed')
    data = read_json(submission)
    attest = read_json(receipt)
    exact(
        attest,
        {
            'version',
            'packet_sha256',
            'submission_sha256',
            'role',
            'person_id',
            'custodian_id',
            'verified_at',
            'human_identity_verified',
            'independence_exclusions_verified',
            'non_automated_observations_verified',
            'verification_evidence_sha256',
        },
    )
    require(
        attest['version'] == 'gt08-human-custody/1'
        and attest['packet_sha256'] == sha(Path(packet) / 'packet.json')
        and attest['submission_sha256'] == sha(submission)
        and attest['role'] == role
        and attest['person_id'] == data['person_id'],
        'Custody is not bound to this raw submission/role/packet',
    )
    require(
        token(attest['custodian_id'])
        and attest['custodian_id'] != data['person_id']
        and digest(attest['verification_evidence_sha256']),
        'External custodian and verification reference required',
    )
    require(
        all(
            attest[k] is True
            for k in [
                'human_identity_verified',
                'independence_exclusions_verified',
                'non_automated_observations_verified',
            ]
        ),
        'External human verification incomplete',
    )
    require(
        utc(attest['verified_at']) >= utc(data['signed_at']),
        'Verification predates human submission',
    )
    return data, attest


def policy(root, packet):
    p = read_json(Path(root) / 'collection-policy.json')
    require(
        p['version'] == VERSION and p['packet_sha256'] == sha(Path(packet) / 'packet.json'),
        'Wrong collection root/packet',
    )
    require(
        digest(p['trusted_custodian_key_sha256']),
        'WAITING_FOR_HUMAN_REVIEW: external trusted custodian key not registered',
    )
    return p


def frozen(root, role, packet, pin):
    directory = (
        Path(root) / ('adjudication' if role == 'ADJUDICATOR' else 'submitted-labels') / role
    )
    record = read_json(directory / 'freeze.json')
    exact(
        record,
        {
            'version',
            'role',
            'person_id',
            'trusted_key_sha256',
            'packet_sha256',
            'frozen_at',
            'files',
            'reader_freezes',
        },
    )
    require(
        record['version'] == VERSION
        and record['packet_sha256'] == sha(Path(packet) / 'packet.json'),
        'Frozen packet metadata changed',
    )
    files = file_hashes(directory)
    files.pop('freeze.json')
    require(
        files == record['files'] and record['trusted_key_sha256'] == pin and record['role'] == role,
        'Frozen raw bytes or custody changed',
    )
    data, attest = signed_custody(
        directory / 'raw-submission.json',
        directory / 'human-custody.json',
        directory / 'human-custody.sig',
        directory / 'custodian-public.pem',
        pin,
        packet,
        role,
    )
    validate_submission(data, packet, role)
    require(data['person_id'] == record['person_id'], 'Frozen reviewer identity changed')
    utc(record['frozen_at'])
    return data, attest, record, directory


def freeze_submission(root, packet, submission, receipt, signature, public_key, role):
    root, packet = Path(root), Path(packet)
    p = policy(root, packet)
    pin = p['trusted_custodian_key_sha256']
    data = read_json(submission)
    validate_submission(data, packet, role)
    data, attest = signed_custody(submission, receipt, signature, public_key, pin, packet, role)
    references = {}
    others = []
    for other in ['A', 'B']:
        other_dir = root / 'submitted-labels' / other
        if other == role:
            continue
        if role == 'ADJUDICATOR' or other_dir.exists():
            od, oa, record, directory = frozen(root, other, packet, pin)
            others.extend([od['person_id'], oa['custodian_id']])
            references[other] = sha(directory / 'freeze.json')
            require(oa['custodian_id'] == attest['custodian_id'], 'Custodian identity inconsistent')
            if role == 'ADJUDICATOR':
                require(
                    utc(data['signed_at']) >= utc(record['frozen_at']),
                    'Adjudication predates primary freezes',
                )
    require(data['person_id'] not in others, 'Reviewer/adjudicator identities must be separate')
    if role == 'ADJUDICATOR':
        require(
            data['reader_freezes'] == references,
            'Adjudication is not bound to both actual primary freezes',
        )
    destination = root / ('adjudication' if role == 'ADJUDICATOR' else 'submitted-labels') / role
    require(not destination.exists(), 'Never overwrite a raw submission/freeze')
    require(
        not any(x.is_symlink() for x in [destination, *destination.parents]),
        'Symlink destination forbidden',
    )
    destination.mkdir(parents=True, exist_ok=False)
    originals = {
        Path(submission): sha(submission),
        Path(receipt): sha(receipt),
        Path(signature): sha(signature),
        Path(public_key): sha(public_key),
    }
    for source, name in [
        (submission, 'raw-submission.json'),
        (receipt, 'human-custody.json'),
        (signature, 'human-custody.sig'),
        (public_key, 'custodian-public.pem'),
    ]:
        exclusive(destination / name, Path(source).read_bytes())
    require(all(sha(src) == h for src, h in originals.items()), 'Input changed during freeze')
    record = {
        'version': VERSION,
        'role': role,
        'person_id': data['person_id'],
        'trusted_key_sha256': pin,
        'packet_sha256': sha(packet / 'packet.json'),
        'frozen_at': datetime.now(timezone.utc).isoformat(),
        'files': file_hashes(destination),
        'reader_freezes': references,
    }
    write_json(destination / 'freeze.json', record)
    frozen(root, role, packet, pin)
    return {
        'status': 'EXTERNALLY_ATTESTED_RAW_FROZEN_NOT_PIXEL_TRUTH',
        'role': role,
        'freeze_sha256': sha(destination / 'freeze.json'),
    }


def overlap_conflicts(masks, links):
    """Count overlapping-case contradictions without silently choosing a winner."""
    ids = list(masks)
    points = set()
    for i, a in enumerate(ids):
        ax, ay, ar, ab = links[a]
        require(masks[a].shape == (ab - ay, ar - ax), 'Private coordinate linkage mismatch')
        for b in ids[i + 1 :]:
            bx, by, br, bb = links[b]
            left, top, right, bottom = max(ax, bx), max(ay, by), min(ar, br), min(ab, bb)
            if left >= right or top >= bottom:
                continue
            aa = masks[a][top - ay : bottom - ay, left - ax : right - ax]
            bc = masks[b][top - by : bottom - by, left - bx : right - bx]
            ys, xs = np.nonzero(aa != bc)
            points.update((left + int(x), top + int(y)) for y, x in zip(ys, xs))
    return len(points)


def collection_status(root, packet):
    root = Path(root)
    verify_packet(packet)
    primaries = [r for r in ['A', 'B'] if (root / 'submitted-labels' / r).exists()]
    adjud = (root / 'adjudication/ADJUDICATOR').exists()
    unvalidated = sum(
        1
        for parent, allowed in [
            (root / 'submitted-labels', {'A', 'B'}),
            (root / 'adjudication', {'ADJUDICATOR'}),
        ]
        for child in parent.iterdir()
        if child.name not in allowed
    )
    if not primaries and not adjud:
        return {
            'decision': 'WAITING_FOR_HUMAN_REVIEW',
            'actual_verified_primary_submissions': 0,
            'actual_adjudications': 0,
            'confirmed_text_contacts': 'UNKNOWN',
            'collision_audit_executed': False,
            'composition_authorized': False,
            'unvalidated_artifacts': unvalidated,
        }
    p = policy(root, packet)
    pin = p['trusted_custodian_key_sha256']
    people = []
    for role in primaries:
        data, attest, _, _ = frozen(root, role, packet, pin)
        people.append(data['person_id'])
    require(len(people) == len(set(people)), 'Same person cannot supply A and B')
    result = {
        'decision': 'WAITING_FOR_HUMAN_REVIEW',
        'actual_verified_primary_submissions': len(people),
        'actual_adjudications': 0,
        'confirmed_text_contacts': 'UNKNOWN',
        'collision_audit_executed': False,
        'composition_authorized': False,
        'unvalidated_artifacts': unvalidated,
    }
    if adjud:
        require(len(primaries) == 2, 'Both independent frozen readers required')
        data, _, _, _ = frozen(root, 'ADJUDICATOR', packet, pin)
        require(data['person_id'] not in people, 'Independent adjudicator required')
        for role in ['A', 'B']:
            _, _, r, d = frozen(root, role, packet, pin)
            require(
                data['reader_freezes'][role] == sha(d / 'freeze.json')
                and utc(data['signed_at']) >= utc(r['frozen_at']),
                'Adjudication linkage/chronology changed',
            )
        masks = validate_submission(data, packet, 'ADJUDICATOR')
        mapping = read_json(root / 'custodian-case-map.json')
        require(
            sha(root / 'custodian-case-map.json') == p['case_map_sha256'],
            'Private case linkage changed',
        )
        links = {r['case_id']: r['page_bbox'] for r in mapping}
        require(set(links) == set(masks), 'Private case coverage mismatch')
        conflicts = overlap_conflicts(masks, links)
        uncertain = sum(int(np.count_nonzero(m >= 3)) for m in masks.values())
        confirmed = sum(int(np.count_nonzero(m <= 2)) for m in masks.values())
        result.update(
            actual_adjudications=1,
            overlapping_case_conflict_pixels=conflicts,
            per_case_uncertain_pixels=uncertain,
            decision=(
                'TEXT_EXTENTS_UNRESOLVED'
                if confirmed == 0
                else (
                    'TEXT_EXTENTS_PARTIALLY_ADJUDICATED'
                    if uncertain or conflicts
                    else 'TEXT_EXTENTS_ADJUDICATED'
                )
            ),
            post_adjudication_collision_audit='REQUIRES_SEPARATE_EXECUTION_WITH_FROZEN_EVIDENCE',
        )
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['validate', 'freeze', 'status'])
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--packet', type=Path, required=True)
    p.add_argument('--role', choices=['A', 'B', 'ADJUDICATOR'])
    p.add_argument('--submission', type=Path)
    p.add_argument('--receipt', type=Path)
    p.add_argument('--signature', type=Path)
    p.add_argument('--public-key', type=Path)
    a = p.parse_args()
    if a.mode == 'validate':
        masks = validate_submission(read_json(a.submission), a.packet, a.role)
        result = {'status': 'SCHEMA_VALID_NOT_HUMAN_AUTHENTICATED', 'cases': len(masks)}
    elif a.mode == 'freeze':
        result = freeze_submission(
            a.root, a.packet, a.submission, a.receipt, a.signature, a.public_key, a.role
        )
    else:
        result = collection_status(a.root, a.packet)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
