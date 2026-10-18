"""Synthetic collection labels only; these are never real reference exports."""
import json
from pathlib import Path

import pytest
from PIL import Image

from scripts.omr_v4 import anchor_collection as ac


@pytest.fixture
def collection(tmp_path, monkeypatch):
    source = tmp_path / 'evidence'
    source.mkdir()
    Image.new('L', (8, 8), 127).save(source / 'source.png')
    files = {'source.png': ac.digest(source / 'source.png')}
    for i in range(27):
        path = source / f'evidence-{i}.txt'
        path.write_text(str(i))
        files[path.name] = ac.digest(path)
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'input_root': str(source), 'files': files}))
    prior = tmp_path / 'prior' / 'blind-packet'
    prior.mkdir(parents=True)
    cases = []
    for ident in ac.IDS:
        Image.open(source / 'source.png').crop((1, 2, 5, 6)).save(prior / f'{ident}.png')
        cases.append({'case': ident, 'image': ident + '.png', 'crop_sha256': ac.digest(prior / f'{ident}.png'), 'source_sha256': files['source.png'], 'native_page_crop_half_open': [1, 2, 5, 6]})
    (prior / 'cases.json').write_text(json.dumps(cases))
    monkeypatch.setattr(ac, 'CASES_SHA', ac.digest(prior / 'cases.json'))
    protocol = ac.read(ac.PROTOCOL)
    (prior / 'instructions.json').write_text(json.dumps({'protocol_sha256': ac.PROTOCOL_SHA, **{k: protocol[k] for k in ('annotation_instructions', 'coordinate_convention', 'reference_fields')}}))
    for role in ('A', 'B'):
        (prior / f'empty-reference-{role}.json').write_text(json.dumps({'protocol_sha256': ac.PROTOCOL_SHA, 'annotator': role, 'status': 'PENDING_INDEPENDENT_ANNOTATION', 'cases': [{'case': i, **dict.fromkeys(ac.FIELDS)} for i in ac.IDS]}))
    out = tmp_path / 'prepared'
    ac.prepare(manifest, prior, out)
    return out, prior, manifest


def signed(out, role, visible=False):
    data = ac.read(out / role / 'submission.json')
    data.update(status='SIGNED_INDEPENDENT_OBSERVATION', signer=f'SYNTHETIC-{role}', signed_at='2026-10-18T12:00:00+09:00', independence_attestation=True)
    for c in data['cases']:
        c.update(annotator_signed_at=data['signed_at'], uncertainty_and_visibility_reason='SYNTHETIC fixture uncertainty', unresolved_reason='SYNTHETIC occluded body', viewer_coordinate_convention_and_conversion={'convention': 'pixel-index-center', 'conversion': 'page=local+crop_origin', 'declared_before_marking': True})
        if visible:
            line = [{'x_interval': [1, 1], 'y_interval': [2, 2.2]}, {'x_interval': [4, 4], 'y_interval': [2, 2.2]}]
            c.update(middle_staff_polyline_page=line, bottom_staff_polyline_page=line, head_body_bounds_page={'left': [1, 1.1], 'top': [2, 2.1], 'right': [3, 3.1], 'bottom': [4, 4.1]}, physical_pivot_xy_intervals_page={'x': [2, 2.1], 'y': [3, 3.1]}, ledger_centerlines_and_y_intervals_page=[], unresolved_reason=None)
    path = out / role / 'synthetic-signed.json'
    path.write_text(json.dumps(data))
    return path


def test_fixed_packet_readiness_and_pixel_identity(collection):
    out, prior, _ = collection
    assert ac.read(out / 'readiness.json')['independent_reference_count'] == 0
    prepared = ac.verify_packet(out / 'blind-packet', prepared=True)
    assert ac.verify_packet(prior) == {name: sha for name, sha in prepared.items() if name in ac.PRIOR_NAMES}
    assert ac.read(out / 'blind-packet' / 'form-instructions.json') == ac.FORM_INSTRUCTIONS
    assert set(p.name for p in (out / 'blind-packet').iterdir()) == ac.PACKET_NAMES


@pytest.mark.parametrize('convention,point', [('pixel-index-center', [0, 0]), ('outer-pixel-edge', [0.5, 0.5])])
def test_coordinate_conversion(convention, point):
    assert ac.page_point(point, [100, 200, 300, 400], convention) == [100, 200]


def test_unexpected_packet_filename_fails_closed(collection):
    out, _, _ = collection
    (out / 'blind-packet' / 'hidden-solution-key.json').write_text('{}')
    with pytest.raises(ValueError, match='filename'):
        ac.verify_binding(out)


def test_unsigned_empty_template_cannot_freeze(collection):
    out, _, _ = collection
    with pytest.raises(ValueError, match='Signed observation'):
        ac.freeze(out, 'A', out / 'A' / 'submission.json')


@pytest.mark.parametrize('visible', [False, True])
def test_signed_unknown_and_visible_observations_freeze(collection, visible):
    out, _, _ = collection
    submission = signed(out, 'A', visible)
    receipt = ac.freeze(out, 'A', submission)
    assert receipt['sha256'] == ac.digest(submission)
    assert (out / 'A' / 'frozen.json').read_bytes() == submission.read_bytes()
    with pytest.raises(ValueError, match='immutable'):
        ac.freeze(out, 'A', submission)
    with pytest.raises(ValueError, match='Both primary'):
        ac.compare(out)


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'nan', 'inverted', 'unsigned', 'unknown-no-reason', 'conversion', 'extra', 'binding', 'line-order'])
def test_invalid_submission_rejected(collection, mutation):
    out, _, _ = collection
    data = ac.read(signed(out, 'A', True))
    c = data['cases'][0]
    if mutation == 'missing': data['cases'].pop()
    elif mutation == 'duplicate': data['cases'][1]['case'] = 'case-01'
    elif mutation == 'nan': c['physical_pivot_xy_intervals_page']['x'] = [0, float('nan')]
    elif mutation == 'inverted': c['physical_pivot_xy_intervals_page']['y'] = [4, 3]
    elif mutation == 'unsigned': data['signer'] = ''
    elif mutation == 'unknown-no-reason': c.update(head_body_bounds_page=None, unresolved_reason=None)
    elif mutation == 'conversion': c['viewer_coordinate_convention_and_conversion']['conversion'] = 'page=local+0.5+crop_origin'
    elif mutation == 'extra': c['expected_pitch'] = 7
    elif mutation == 'binding': data['binding_sha256'] = '0' * 64
    elif mutation == 'line-order': c['middle_staff_polyline_page'].reverse()
    with pytest.raises(ValueError):
        ac.validate_submission(data, 'A', ac.verify_binding(out))


def test_both_freezes_comparison_no_consensus_and_tamper(collection):
    out, _, _ = collection
    for role in ('A', 'B'):
        ac.freeze(out, role, signed(out, role, role == 'B'))
    result = ac.compare(out)
    assert result['consensus'] == 'NOT_INFERRED'
    assert len(result['cases']) == 10
    assert result['cases'][0]['differing_fields']
    frozen = out / 'A' / 'frozen.json'
    frozen.chmod(0o644)
    frozen.write_text('{}')
    with pytest.raises(ValueError, match='tampered'):
        ac.compare(out)


def test_packet_and_source_tamper(collection):
    out, prior, manifest = collection
    source = Path(ac.read(manifest)['input_root'])
    (source / 'evidence-0.txt').write_text('changed')
    with pytest.raises(ValueError, match='Input changed'):
        ac.verify_inputs(manifest)
    image = out / 'blind-packet' / 'case-01.png'
    image.write_bytes(b'changed')
    with pytest.raises(ValueError, match='Crop hash'):
        ac.verify_binding(out)


def test_adjudication_waits_for_both_and_preserves_primaries(collection):
    out, _, _ = collection
    with pytest.raises(ValueError, match='Both primary'):
        ac.adjudicate(out, out / 'absent.json')
    for role in ('A', 'B'):
        ac.freeze(out, role, signed(out, role))
    _, hashes = ac.both_frozen(out)
    reference = ac.read(signed(out, 'A'))
    reference.update(annotator='ADJUDICATOR', signer='SYNTHETIC-independent-second-pass')
    adjudication = out / 'synthetic-adjudication-draft.json'
    adjudication.write_text(json.dumps({'primary_hashes': hashes, 'reference': reference, 'reason': 'SYNTHETIC unresolved; no forced consensus'}))
    ac.adjudicate(out, adjudication)
    assert ac.both_frozen(out)[1] == hashes
    with pytest.raises(FileExistsError):
        ac.adjudicate(out, adjudication)
