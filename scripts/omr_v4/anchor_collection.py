"""Offline fixed-packet preparation and separate, immutable annotation freezes."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from datetime import datetime
from pathlib import Path

from PIL import Image

PROTOCOL = Path(__file__).resolve().parents[2] / 'docs/V4_ANCHOR_REFERENCE_PROTOCOL.json'
PROTOCOL_SHA = '25057996c46ceec83720fe95bc447015002b9bf826e83924e16b8f359181d085'
CASES_SHA = '7b56a156b9cc0ba0263fa97ad8738ce4071d9a3219c2116e01db6b21f7f37a4e'
IDS = [f'case-{i:02d}' for i in range(1, 11)]
FIELDS = json.loads(PROTOCOL.read_text())['reference_fields']
OBSERVATIONS = FIELDS[:5]
PRIOR_NAMES = {'cases.json', 'instructions.json', 'empty-reference-A.json', 'empty-reference-B.json', *(f'{i}.png' for i in IDS)}
FORM_INSTRUCTIONS = {
    'submission': 'Retain all draft fields, IDs and hashes. Set status SIGNED_INDEPENDENT_OBSERVATION, signer to your identity, signed_at to timezone-bearing ISO-8601, independence_attestation true only after independent source observation. Each case requires annotator_signed_at and uncertainty_and_visibility_reason.',
    'unknowns': 'Any geometry field may be null with unresolved_reason identifying unknown features and reasons. Entirely unknown but observed/explained/signed cases are valid. [] for ledgers means observed none. Do not infer invisible features or semantic pitch.',
    'interval': 'Every interval is [finite low, finite high], low <= high. All geometry uses page pixel-index-center coordinates, never local pointer coordinates.',
    'staff_polyline_fields': ['middle_staff_polyline_page', 'bottom_staff_polyline_page'],
    'polyline': 'Two or more {x_interval:[low,high], y_interval:[low,high]} points. Each x_interval high must be strictly below the next x_interval low.',
    'head_body_bounds_page': '{left:[low,high], top:[low,high], right:[low,high], bottom:[low,high]}; left high < right low and top high < bottom low.',
    'physical_pivot_xy_intervals_page': '{x:[low,high], y:[low,high]}; observed plausible geometric center of visible head body only, after distinguishing attached strokes where possible.',
    'ledger_centerlines_and_y_intervals_page': 'List of polylines in the same interval-point format.',
    'viewer_coordinate_convention_and_conversion': [
        {'convention': 'pixel-index-center', 'conversion': 'page=local+crop_origin', 'declared_before_marking': True},
        {'convention': 'outer-pixel-edge', 'conversion': 'page=local-0.5+crop_origin', 'declared_before_marking': True},
    ],
    'viewer_check': 'Before marking, establish convention from viewer documentation or a known pixel probe at native resolution: the first sample center is (0,0) for index-center and (0.5,0.5) for outer-edge coordinates. If convention is unknown, stop and resolve it before marking. No posthoc half-pixel adjustment.',
}
PACKET_NAMES = PRIOR_NAMES | {'form-instructions.json'}



def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def require(ok, message):
    if not ok:
        raise ValueError(message)


def write_new(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    path.chmod(0o444)


def verify_inputs(manifest):
    data = read(manifest)
    root = Path(data['input_root'])
    require(len(data['files']) == 28, 'Expected shared 28-file manifest')
    for name, expected in data['files'].items():
        require(digest(root / name) == expected, f'Input changed: {name}')
    require(digest(PROTOCOL) == PROTOCOL_SHA, 'Frozen protocol changed')
    return root, digest(manifest)


def page_point(local, crop, convention):
    require(convention in ('pixel-index-center', 'outer-pixel-edge'), 'Unknown viewer convention')
    require(len(local) == 2 and all(type(v) in (int, float) and math.isfinite(v) for v in local), 'Invalid point')
    shift = 0.5 if convention == 'outer-pixel-edge' else 0
    return [local[0] - shift + crop[0], local[1] - shift + crop[1]]


def verify_packet(packet, source=None, prepared=False):
    require(not packet.is_symlink(), 'Symlink packet forbidden')
    require({p.name for p in packet.iterdir()} == (PACKET_NAMES if prepared else PRIOR_NAMES), 'Unexpected/missing packet filename')
    require(all(p.is_file() and not p.is_symlink() for p in packet.iterdir()), 'Nonregular packet entry')
    require(digest(PROTOCOL) == PROTOCOL_SHA, 'Frozen protocol changed')
    require(digest(packet / 'cases.json') == CASES_SHA, 'Fixed case selection changed')
    if prepared:
        require(read(packet / 'form-instructions.json') == FORM_INSTRUCTIONS, 'Form instructions changed')
    cases = read(packet / 'cases.json')
    protocol = read(PROTOCOL)
    require(read(packet / 'instructions.json') == {'protocol_sha256': PROTOCOL_SHA, **{k: protocol[k] for k in ('annotation_instructions', 'coordinate_convention', 'reference_fields')}}, 'Instructions changed')
    require([c['case'] for c in cases] == IDS, 'Fixed case IDs changed')
    image = Image.open(source) if source else None
    for c in cases:
        path = packet / c['image']
        require(c['image'] == c['case'] + '.png' and digest(path) == c['crop_sha256'], 'Crop hash changed')
        crop = c['native_page_crop_half_open']
        with Image.open(path) as saved:
            require(saved.size == (crop[2] - crop[0], crop[3] - crop[1]), 'Crop dimensions changed')
            if image:
                require(digest(source) == c['source_sha256'], 'Source binding changed')
                expected = image.crop(crop)
                require(saved.mode == expected.mode and saved.tobytes() == expected.tobytes(), 'Source crop pixels changed')
        require(page_point([0, 0], crop, 'pixel-index-center') == page_point([0.5, 0.5], crop, 'outer-pixel-edge'), 'Coordinate conversion changed')
    for role in ('A', 'B'):
        expected = {'protocol_sha256': PROTOCOL_SHA, 'annotator': role, 'status': 'PENDING_INDEPENDENT_ANNOTATION', 'cases': [{'case': i, **dict.fromkeys(FIELDS)} for i in IDS]}
        require(read(packet / f'empty-reference-{role}.json') == expected, 'Nonblank/unexpected original form')
    return {name: digest(packet / name) for name in sorted(PACKET_NAMES if prepared else PRIOR_NAMES)}


def prepare(manifest, prior, out):
    root, manifest_sha = verify_inputs(manifest)
    hashes = verify_packet(prior, root / 'source.png')
    resolved = out.resolve()
    require(not resolved.is_relative_to(root.resolve()) and not resolved.is_relative_to(prior.parent.resolve()), 'Output overlaps immutable evidence/prior output')
    require(not out.exists(), 'New output required')
    out.mkdir(parents=True)
    packet = out / 'blind-packet'
    packet.mkdir()
    for name in sorted(PRIOR_NAMES):
        shutil.copyfile(prior / name, packet / name)
    require(verify_packet(packet, root / 'source.png') == hashes, 'Packet copy differs')
    write_new(packet / 'form-instructions.json', FORM_INSTRUCTIONS)
    prepared_hashes = verify_packet(packet, root / 'source.png', prepared=True)
    binding = {'protocol_sha256': PROTOCOL_SHA, 'cases_sha256': CASES_SHA, 'packet_files': prepared_hashes, 'input_manifest_sha256': manifest_sha}
    write_new(out / 'binding.json', binding)
    for role in ('A', 'B'):
        session = out / role
        session.mkdir()
        form = read(packet / f'empty-reference-{role}.json')
        form.update(binding_sha256=digest(out / 'binding.json'), signer=None, signed_at=None, independence_attestation=None)
        # Drafts remain editable; only signed exports are frozen.
        (session / 'submission.json').write_text(json.dumps(form, indent=2) + '\n')
    require(verify_inputs(manifest)[1] == manifest_sha, 'Manifest changed during preparation')
    write_new(out / 'readiness.json', {'status': 'TECHNICALLY_READY', 'cases': 10, 'independent_reference_count': 0, 'external_roster': 'PENDING', 'verified_files_before_after': 28, 'binding_sha256': digest(out / 'binding.json')})
    return read(out / 'readiness.json')


def verify_binding(out):
    binding = read(out / 'binding.json')
    require(binding['protocol_sha256'] == PROTOCOL_SHA and binding['cases_sha256'] == CASES_SHA, 'Binding mismatch')
    require(verify_packet(out / 'blind-packet', prepared=True) == binding['packet_files'], 'Packet binding mismatch')
    return digest(out / 'binding.json')


def text_value(value):
    return isinstance(value, str) and bool(value.strip())


def signed_time(value):
    require(text_value(value), 'Signature timestamp required')
    try:
        require(datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is not None, 'Timezone required')
    except (ValueError, TypeError) as exc:
        raise ValueError('Invalid signed timestamp') from exc


def interval(value):
    require(isinstance(value, list) and len(value) == 2 and all(type(v) in (int, float) and math.isfinite(v) for v in value) and value[0] <= value[1], 'Finite ordered interval required')


def polyline(value):
    require(isinstance(value, list) and len(value) >= 2, 'Polyline requires two or more points')
    for point in value:
        require(isinstance(point, dict) and set(point) == {'x_interval', 'y_interval'}, 'Polyline interval fields required')
        interval(point['x_interval'])
        interval(point['y_interval'])
    require(all(a['x_interval'][1] < b['x_interval'][0] for a, b in zip(value, value[1:])), 'Polyline x intervals must be ordered and disjoint')


def validate_submission(data, role, binding_sha):
    require(set(data) == {'protocol_sha256', 'annotator', 'status', 'cases', 'binding_sha256', 'signer', 'signed_at', 'independence_attestation'}, 'Unexpected/missing submission field')
    require(data['protocol_sha256'] == PROTOCOL_SHA and data['binding_sha256'] == binding_sha and data['annotator'] == role, 'Submission hash/role mismatch')
    require(data['status'] == 'SIGNED_INDEPENDENT_OBSERVATION', 'Signed observation status required')
    require(text_value(data['signer']) and data['independence_attestation'] is True, 'Signer and independence attestation required')
    signed_time(data['signed_at'])
    require(isinstance(data['cases'], list) and [c['case'] for c in data['cases']] == IDS, 'All ten fixed IDs required exactly once in order')
    for c in data['cases']:
        require(set(c) == {'case', *FIELDS}, 'Unexpected/missing case field')
        signed_time(c['annotator_signed_at'])
        require(text_value(c['uncertainty_and_visibility_reason']), 'Visibility/uncertainty reason required')
        viewer = c['viewer_coordinate_convention_and_conversion']
        require(isinstance(viewer, dict) and set(viewer) == {'convention', 'conversion', 'declared_before_marking'}, 'Viewer declaration required')
        convention = viewer['convention']
        expected = {'pixel-index-center': 'page=local+crop_origin', 'outer-pixel-edge': 'page=local-0.5+crop_origin'}
        require(convention in expected and viewer['conversion'] == expected[convention] and viewer['declared_before_marking'] is True, 'Viewer conversion must be declared before marking')
        if any(c[k] is None for k in OBSERVATIONS):
            require(text_value(c['unresolved_reason']), 'Unknown observation requires unresolved reason')
        else:
            require(c['unresolved_reason'] is None or text_value(c['unresolved_reason']), 'Invalid unresolved reason')
        for k in OBSERVATIONS[:2]:
            if c[k] is not None:
                polyline(c[k])
        box = c['head_body_bounds_page']
        if box is not None:
            require(isinstance(box, dict) and set(box) == {'left', 'top', 'right', 'bottom'}, 'Body bounds require edge intervals')
            for edge in box.values():
                interval(edge)
            require(box['left'][1] < box['right'][0] and box['top'][1] < box['bottom'][0], 'Body bounds inverted')
        pivot = c['physical_pivot_xy_intervals_page']
        if pivot is not None:
            require(isinstance(pivot, dict) and set(pivot) == {'x', 'y'}, 'Physical center requires x/y intervals')
            interval(pivot['x'])
            interval(pivot['y'])
        ledgers = c['ledger_centerlines_and_y_intervals_page']
        if ledgers is not None:
            require(isinstance(ledgers, list), 'Ledger list required (empty means observed none)')
            for line in ledgers:
                polyline(line)


def freeze(out, role, submission):
    require(role in ('A', 'B'), 'Primary role required')
    binding_sha = verify_binding(out)
    raw = submission.read_bytes()
    data = json.loads(raw)
    validate_submission(data, role, binding_sha)
    session = out / role
    require(not (session / 'frozen.json').exists() and not (session / 'receipt.json').exists(), 'Freeze is immutable')
    # Preserve the submitted bytes, not a normalized or adjudicated replacement.
    with (session / 'frozen.json').open('xb') as stream:
        stream.write(raw)
    (session / 'frozen.json').chmod(0o444)
    write_new(session / 'receipt.json', {'sha256': digest(session / 'frozen.json'), 'binding_sha256': binding_sha, 'role': role})
    return read(session / 'receipt.json')


def both_frozen(out):
    binding_sha = verify_binding(out)
    labels, hashes = {}, {}
    for role in ('A', 'B'):
        session = out / role
        require((session / 'frozen.json').is_file() and (session / 'receipt.json').is_file(), 'Both primary freezes required before views or adjudication')
        receipt = read(session / 'receipt.json')
        require(receipt == {'sha256': digest(session / 'frozen.json'), 'binding_sha256': binding_sha, 'role': role}, 'Frozen primary tampered')
        labels[role] = read(session / 'frozen.json')
        validate_submission(labels[role], role, binding_sha)
        hashes[role] = receipt['sha256']
    require(labels['A']['signer'] != labels['B']['signer'], 'Distinct primary signers required')
    return labels, hashes


def compare(out):
    labels, hashes = both_frozen(out)
    return {'primary_hashes': hashes, 'consensus': 'NOT_INFERRED', 'cases': [{'case': a['case'], 'A': a, 'B': b, 'differing_fields': [k for k in OBSERVATIONS if a[k] != b[k]]} for a, b in zip(labels['A']['cases'], labels['B']['cases'])]}


def adjudicate(out, submission):
    labels, hashes = both_frozen(out)
    data = read(submission)
    require(set(data) == {'primary_hashes', 'reference', 'reason'}, 'Adjudication envelope required')
    require(data['primary_hashes'] == hashes and text_value(data['reason']), 'Adjudication must bind both frozen primaries and explain decisions')
    validate_submission(data['reference'], 'ADJUDICATOR', verify_binding(out))
    require(data['reference']['signer'] not in {labels[r]['signer'] for r in ('A', 'B')}, 'Independent second-pass adjudicator required')
    write_new(out / 'adjudication.json', data)
    return {'adjudication_sha256': digest(out / 'adjudication.json'), 'primary_hashes': hashes, 'unresolved_preserved_in_primaries': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prep = commands.add_parser('prepare')
    prep.add_argument('--inputs', type=Path, required=True)
    prep.add_argument('--prior-packet', type=Path, required=True)
    prep.add_argument('--out', type=Path, required=True)
    for command in ('freeze', 'compare', 'adjudicate'):
        sub = commands.add_parser(command)
        sub.add_argument('--out', type=Path, required=True)
        if command != 'compare':
            sub.add_argument('--submission', type=Path, required=True)
        if command == 'freeze':
            sub.add_argument('--role', choices=('A', 'B'), required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        result = prepare(args.inputs, args.prior_packet, args.out)
    elif args.command == 'freeze':
        result = freeze(args.out, args.role, args.submission)
    elif args.command == 'compare':
        result = compare(args.out)
    else:
        result = adjudicate(args.out, args.submission)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
