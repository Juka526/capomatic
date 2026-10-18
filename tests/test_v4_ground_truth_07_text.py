"""Synthetic diagnostic categories and blinded packet boundaries; no source scores."""

import json
import numpy as np
from PIL import Image
import pytest

from scripts.research.gt07_text import descendants, classify, mask_of, neutral_packet, verify_freeze


def test_support_categories_are_disjoint_and_do_not_claim_source_ownership():
    text = np.array([[False, True, False, True]])
    music = np.array([[False, False, True, True]])
    assert classify(text, music).tolist() == [[0, 1, 2, 3]]
    with pytest.raises(ValueError):
        classify(text, np.zeros((2, 2), bool))


def test_raw_containment_traversal_retains_descendants_and_missing_lineage_fails():
    graph = {
        'symbols': {'parent': {}, 'word': {}},
        'relations': [{'kind': 'contains', 'source': 'parent', 'target': 'word'}],
    }
    assert descendants(graph, 'parent') == ['parent', 'word']
    graph['symbols'].pop('word')
    with pytest.raises(ValueError):
        descendants(graph, 'parent')


@pytest.mark.parametrize('pixel', [(-1, 0), (0, -1), (4, 0), (0, 4)])
def test_page_coordinate_escape_fails_closed(pixel):
    with pytest.raises(ValueError):
        mask_of((4, 4), [pixel])


def test_pixel_masks_do_not_fill_bounding_box_voids():
    m = mask_of((5, 5), [(0, 0), (4, 4)])
    assert int(m.sum()) == 2 and not m[2, 2]


def test_packet_source_only_pixels_separate_readers_no_suggested_answers(tmp_path):
    source = Image.new('RGB', (40, 40), (23, 55, 77))
    before = source.tobytes()
    mapping = neutral_packet(source, [('private-parent-id', (4, 6, 14, 16))], tmp_path / 'packet')
    a = json.loads((tmp_path / 'packet/blank-A.json').read_text())
    b = json.loads((tmp_path / 'packet/blank-B.json').read_text())
    assert a['reader'] == 'A' and b['reader'] == 'B'
    assert a['independence_attestation'] is None
    assert a['cases'][0]['observation_label'] is None
    assert {'UNKNOWN', 'MIXED'} <= set(a['cases'][0]['allowed_labels'])
    assert 'private-parent-id' not in json.dumps(a)
    image = Image.open(tmp_path / 'packet' / a['cases'][0]['image'])
    assert image.size == (10, 10) and image.tobytes() == source.crop((4, 6, 14, 16)).tobytes()
    assert source.tobytes() == before and mapping[0]['source_object'] == 'private-parent-id'
    mapping2 = neutral_packet(source, [('private-parent-id', (4, 6, 14, 16))], tmp_path / 'other')
    assert mapping == mapping2


def test_changed_frozen_prediction_fails_before_analysis(tmp_path):
    (tmp_path / 'prototype-freeze.json').write_text(
        json.dumps({'files': {'predicted-a.png': 'wrong'}})
    )
    with pytest.raises(ValueError, match='Frozen'):
        verify_freeze(tmp_path)
