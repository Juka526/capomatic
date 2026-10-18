"""Toy owner observations; no score annotations or prediction regeneration."""

import itertools
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from scripts.research import gt10_owner_collision as audit
from scripts.research.gt09_owner_review import encoded, sha, COORDINATES, VERSION


def row(ident, label, width=3, height=2):
    return {
        'case_id': ident,
        'width': width,
        'height': height,
        'image_sha256': '0' * 64,
        'runs': [[y, 0, width, label] for y in range(height)],
        'finalized': True,
        'uncertainty_acknowledged': True,
    }


@pytest.fixture
def owner_export(tmp_path, monkeypatch):
    packet = tmp_path / 'packet'
    packet.mkdir()
    (packet / 'instructions.txt').write_text('Synthetic only')
    cases = []
    rows = []
    for i in range(5):
        ident = f'{i:020x}'
        p = packet / (ident + '.png')
        Image.new('RGB', (3, 2), 'white').save(p)
        case = {
            'case_id': ident,
            'image': p.name,
            'width': 3,
            'height': 2,
            'sha256': sha(p.read_bytes()),
        }
        cases.append(case)
        r = row(ident, 'UNKNOWN')
        r['image_sha256'] = case['sha256']
        rows.append(r)
    (packet / 'packet.json').write_bytes(
        encoded(
            {
                'version': 'gt08-text-review/1',
                'coordinate_system': COORDINATES,
                'cases': cases,
                'instructions_sha256': sha((packet / 'instructions.txt').read_bytes()),
            }
        )
    )
    digest = sha((packet / 'packet.json').read_bytes())
    monkeypatch.setattr(audit, 'EXPECTED_PACKET', digest)
    data = {
        'version': VERSION,
        'review_type': 'OWNER_REVIEW',
        'evidence_status': 'NOT_INDEPENDENT_GROUND_TRUTH',
        'packet_sha256': digest,
        'coordinate_system': COORDINATES,
        'cases': rows,
        'coverage': {
            r['case_id']: {'TEXT': 0, 'NON_TEXT': 0, 'MIXED': 0, 'UNKNOWN': 6, 'UNREVIEWED': 0}
            for r in rows
        },
        'composition_authorized': False,
        'protection_masks_modified': False,
    }
    p = tmp_path / 'owner.json'
    p.write_bytes(encoded(data))
    return p, packet, data


def test_owner_export_verified_unchanged_and_not_independent(owner_export):
    p, packet, data = owner_export
    before = p.read_bytes()
    result, coverage = audit.validate_owner(p, packet)
    assert result == data and p.read_bytes() == before
    assert len(coverage) == 5 and result['evidence_status'] == 'NOT_INDEPENDENT_GROUND_TRUTH'


@pytest.mark.parametrize(
    'change',
    ['duplicate', 'gap', 'wrong_hash', 'not_finalized', 'independent', 'permission', 'coverage'],
)
def test_invalid_or_misrepresented_owner_export_rejected(owner_export, change):
    p, packet, d = owner_export
    if change == 'duplicate':
        d['cases'][1] = d['cases'][0]
    elif change == 'gap':
        d['cases'][0]['runs'].pop()
    elif change == 'wrong_hash':
        d['cases'][0]['image_sha256'] = '1' * 64
    elif change == 'not_finalized':
        d['cases'][0]['finalized'] = False
    elif change == 'independent':
        d['evidence_status'] = 'INDEPENDENT_GROUND_TRUTH'
    elif change == 'permission':
        d['composition_authorized'] = True
    elif change == 'coverage':
        d['coverage'][d['cases'][0]['case_id']]['UNKNOWN'] = 5
    p.write_bytes(encoded(d))
    with pytest.raises(ValueError):
        audit.validate_owner(p, packet)


def test_explicit_sha_selection_never_uses_newest(tmp_path):
    a = tmp_path / 'old.json'
    a.write_bytes(b'completed review')
    (tmp_path / 'new.json').write_bytes(b'not selected')
    chosen, _ = audit.find_export(tmp_path, sha(a.read_bytes()))
    assert chosen == a
    (tmp_path / 'copy.json').write_bytes(a.read_bytes())
    with pytest.raises(ValueError):
        audit.find_export(tmp_path, sha(a.read_bytes()))
    with pytest.raises(ValueError):
        audit.find_export(tmp_path, '0' * 64)


def test_mapping_retains_conflicts_all_labels_and_unmapped():
    rows = [row('a', 'TEXT'), row('b', 'NON_TEXT'), row('c', 'MIXED'), row('d', 'UNKNOWN')]
    mapping = [{'case_id': r['case_id'], 'page_bbox': [i, 0, i + 3, 2]} for i, r in enumerate(rows)]
    bits, cats = audit.map_owner(rows, mapping, (8, 3))
    assert cats[0].tolist() == [1, 5, 5, 5, 5, 4, 0, 0]
    assert bits[0, 2] == 1 | 2 | 4 and bits[0, 3] == 2 | 4 | 8
    assert not bits[2].any()
    # Equal repeated answers remain one category, never multiple counted contacts.
    same = [row('a', 'TEXT'), row('b', 'TEXT')]
    bits, cats = audit.map_owner(
        same, [{'case_id': r['case_id'], 'page_bbox': [0, 0, 3, 2]} for r in same], (3, 2)
    )
    assert np.all(cats == 1)


@pytest.mark.parametrize('box', [[0, 0, 4, 2], [-1, 0, 2, 2], [0, 0, 3.0, 2]])
def test_mapping_invalid_dimensions_and_coordinates_block(box):
    with pytest.raises(ValueError):
        audit.map_owner([row('a', 'TEXT')], [{'case_id': 'a', 'page_bbox': box}], (5, 5))


def test_region_dark_and_omr_are_three_distinct_metrics():
    mask = np.ones((1, 6), bool)
    owner = np.array([[1, 1, 2, 3, 4, 5]], dtype='uint8')
    gray = np.array([[255, 0, 0, 255, 255, 0]], dtype='uint8')
    text = np.array([[False, False, True, False, False, False]])
    music = np.array([[False, True, False, False, False, False]])
    r = audit.summarize(mask, owner, gray, text, music)
    assert r['unique_pixels'] == 6 and sum(r['owner_categories'].values()) == 6
    assert r['owner_categories']['OWNER_TEXT_REGION'] == 2
    assert r['original_dark_within_owner_text_region'] == 1
    assert r['owner_text_region_without_dark_support'] == 1
    assert r['omr_text_support_candidates'] == 1
    assert r['omr_music_support_candidates'] == 1
    assert r['coordinate_runs'] == [[0, 0, 6]]


def test_nested_envelopes_union_does_not_double_count():
    m = audit.protected_union((5, 5), [{'bbox': [0, 0, 4, 4]}, {'bbox': [1, 1, 3, 3]}])
    assert m.sum() == 16
    with pytest.raises(ValueError):
        audit.protected_union((5, 5), [{'bbox': [0, 0, float('nan'), 1]}])


def test_superset_bounds_never_pretend_to_be_exact():
    buckets = {'TEXT': 2, 'OTHER': 3}
    bounds = audit.subset_bounds(3, buckets)
    assert bounds == {'TEXT': [0, 2], 'OTHER': [1, 3]}
    for subset in itertools.combinations(['TEXT', 'TEXT', 'OTHER', 'OTHER', 'OTHER'], 3):
        for label, (low, high) in bounds.items():
            assert low <= subset.count(label) <= high


def test_no_mask_rescale_or_mode_substitution(tmp_path):
    p = tmp_path / 'mask.png'
    Image.new('L', (3, 2), 255).save(p)
    assert audit.read_mask(p, (3, 2)).sum() == 6
    with pytest.raises(ValueError):
        audit.read_mask(p, (2, 3))
    Image.new('RGB', (3, 2), 'white').save(p)
    with pytest.raises(ValueError):
        audit.read_mask(p, (3, 2))


def test_diagnostic_annotation_does_not_mutate_source():
    source = Image.new('RGB', (3, 2), 'white')
    before = source.tobytes()
    image = audit.painted(source, (0, 0, 3, 2), [(np.ones((2, 3), bool), (255, 0, 0), 0.5)])
    assert source.tobytes() == before and image.tobytes() != before


def test_exact_47_style_details_keep_case_disagreements_and_component_uncertainty():
    rows = [row('a', 'TEXT'), row('b', 'NON_TEXT')]
    mapping = [{'case_id': r['case_id'], 'page_bbox': [0, 0, 3, 2]} for r in rows]
    bits, owner = audit.map_owner(rows, mapping, (3, 2))
    hit = np.zeros((2, 3), bool)
    hit[1, 1] = True
    metric = {
        'events': [{'rendered_bounds': [0, 0, 3, 2], 'requested_anchor': [1, 1]}],
        'flag': {'rendered_bounds': [0, 10, 3, 15]},
        'stem_tip': [2, 0],
    }
    d = audit.detail_rows(
        hit,
        bits,
        owner,
        np.ones((2, 3), dtype='uint8') * 200,
        {(1, 1): ['text:1']},
        {},
        rows,
        mapping,
        metric,
        {'staff': {'interline': 1}},
    )
    assert len(d) == 1 and d[0]['owner_category'] == 'OWNER_CONFLICT'
    assert d[0]['retained_labels'] == ['TEXT', 'NON_TEXT']
    assert d[0]['original_gray'] == 200 and len(d[0]['case_observations']) == 2
    assert d[0]['predicted_notation_component']['exact_component'].startswith('UNRESOLVED')
    assert encoded(d) == encoded(
        audit.detail_rows(
            hit,
            bits,
            owner,
            np.ones((2, 3), dtype='uint8') * 200,
            {(1, 1): ['text:1']},
            {},
            rows,
            mapping,
            metric,
            {'staff': {'interline': 1}},
        )
    )


def test_gt06_homogeneous_superset_proves_aggregate_not_pixel_set():
    counts = {k: 0 for k in audit.BUCKETS}
    counts['OWNER_NON_TEXT_REGION'] = 10
    previous = {
        'target': 'A',
        'all_protections_union_intersections': 4,
        'original_dark_in_union': 2,
        'regions': [
            {
                'id': 'sheet#1:4134',
                'broad_envelope_pixels': 4,
                'text_support_only_candidates': 0,
                'music_support_only_candidates': 3,
                'shared_or_ambiguous': 0,
            }
        ],
    }
    result = audit.gt06_partial_result(
        'A', 4, {'protected_source_dark_contact_pixels': 2}, {'owner_categories': counts}, previous
    )
    assert result['logically_determined_owner_counts']['OWNER_NON_TEXT_REGION'] == 4
    assert result['exact_owner_counts_from_reconstructed_contact_coordinates'] is None
    assert result['historical_omr_music_support_candidates'] == 3
    counts['OWNER_NON_TEXT_REGION'] = 5
    counts['OWNER_TEXT_REGION'] = 5
    result = audit.gt06_partial_result(
        'A', 4, {'protected_source_dark_contact_pixels': 2}, {'owner_categories': counts}, previous
    )
    assert result['logically_determined_owner_counts']['OWNER_TEXT_REGION'] is None
    with pytest.raises(ValueError):
        audit.gt06_partial_result(
            'G',
            4,
            {'protected_source_dark_contact_pixels': 2},
            {'owner_categories': counts},
            previous,
        )


def test_output_cannot_write_into_historical_evidence(tmp_path, monkeypatch):
    historical = tmp_path / 'history'
    historical.mkdir()
    monkeypatch.setattr(audit, 'GT06', historical)
    monkeypatch.setattr(
        audit, 'find_export', lambda *args: pytest.fail('Must reject before reading actual input')
    )
    with pytest.raises(ValueError, match='Output inside historical evidence'):
        audit.audit(historical / 'new-audit')
    assert not list(historical.iterdir())
