"""Offline audit controls must test the predicate without asserting ownership."""

import hashlib
from pathlib import Path

import cv2
import numpy as np
import pytest

from scripts.audit_continuation_guard import (
    PROTOCOL_SHA,
    cc_measure,
    choose_controls,
    control_origins,
    guard,
    measure,
    stencil,
    translate,
    verify_inputs,
    validate_output,
)


def scene():
    gray = np.full((40, 40), 255, dtype=np.uint8)
    support = {(20, 20)}
    unknown, outer = stencil(support, support, set(), (40, 40))
    return gray, support, unknown, outer, np.zeros_like(gray, dtype=bool)


def test_white_blank_and_one_gray_level_and_dark_connected_tails():
    gray, support, unknown, outer, excluded = scene()
    assert not guard(gray, support, unknown, outer, excluded)[1]
    for level in (254, 40):
        gray[20, 22:24] = level
        background, points, _ = guard(gray, support, unknown, outer, excluded)
        assert background == 255 and points == {(23, 20)}
        measurement = measure(points, gray, np.full_like(gray, 255), {}, background)
        category = 'LOW_CONTRAST_BACKGROUND_CANDIDATE' if level == 254 else 'SOURCE_ONLY_UNRESOLVED'
        assert measurement['categories'] == {category: 1}
        excluded[20, 23] = True
        assert not guard(gray, support, unknown, outer, excluded)[1]
        excluded[20, 23] = False


def test_geometry_only_controls_reject_entire_ring_and_are_deterministic():
    exclusion = np.zeros((70, 70), bool)
    origins = control_origins(exclusion, (20, 20, 22, 22))
    exclusion[3, 3] = True  # in 5px ring around origin (8,8)
    eligible = control_origins(exclusion, (20, 20, 22, 22))
    assert (8, 8) in origins and (8, 8) not in eligible
    selected = choose_controls(eligible, (20, 20, 22, 22))
    assert selected == choose_controls(eligible, (20, 20, 22, 22))
    assert len(selected) == 6 and len({p for _, p in selected}) == 6


def test_exact_stencil_translates_and_adjacency_is_required():
    gray, support, unknown, outer, excluded = scene()
    gray[20, 23] = 254
    assert not guard(gray, support, unknown, outer, excluded)[1]
    shifted = tuple(translate(ps, 2, 3) for ps in (support, unknown, outer))
    assert stencil(shifted[0], shifted[0], set(), (40, 40)) == shifted[1:]


def test_staff_bridge_component_is_topology_not_ownership():
    mask = np.zeros((12, 12), np.uint8)
    mask[5, 2:10] = 1
    remote, support, staff = {(9, 5)}, {(2, 5)}, {(5, 5)}
    _, labels = cv2.connectedComponents(mask, connectivity=8)
    assert cc_measure(remote, support, staff, labels)['connected_to_both'] == 1
    mask[5, 5] = 0
    _, labels = cv2.connectedComponents(mask, connectivity=8)
    assert cc_measure(remote, support, staff, labels)['connected_to_group_support'] == 0


def test_categories_have_support_precedence_and_never_claim_ground_truth():
    gray = np.full((4, 4), 254, np.uint8)
    binary = np.full((4, 4), 255, np.uint8)
    binary[1, 1] = 0
    result = measure({(1, 1), (2, 2)}, gray, binary, {'slur': {(2, 2)}}, 255)
    assert result['categories'] == {
        'PERSISTED_SYMBOL_SUPPORT': 1,
        'UNSUPPORTED_BINARY_INK_CANDIDATE': 1,
    }


def test_preregistered_protocol_and_input_binding(tmp_path):
    protocol = Path(__file__).resolve().parents[1] / 'docs/V4_CONTINUATION_GUARD_PROTOCOL.json'
    assert hashlib.sha256(protocol.read_bytes()).hexdigest() == PROTOCOL_SHA
    (tmp_path / 'source').write_bytes(b'bound')
    binding = {
        'input_root': str(tmp_path),
        'files': {'source': hashlib.sha256(b'bound').hexdigest()},
    }
    assert verify_inputs(binding) == binding['files']
    (tmp_path / 'source').write_bytes(b'changed')
    with pytest.raises(ValueError, match='hash mismatch'):
        verify_inputs(binding)


def test_output_paths_fail_closed():
    root = Path('/private/tmp/evidence').resolve()
    with pytest.raises(ValueError, match='evidence root'):
        validate_output(root / 'nested', root)
    with pytest.raises(ValueError, match='this worktree'):
        validate_output(Path('/private/tmp/unrelated'), root)
    own = Path(__file__).resolve().parents[1] / 'dual-track-a-output'
    validate_output(own, root)


def test_distinct_contrast_preserves_pixel_specific_background():
    gray = np.full((4, 4), 247, np.uint8)
    binary = np.full_like(gray, 255)
    result = measure({(1, 1), (2, 2)}, gray, binary, {}, {(1, 1): 254, (2, 2): 255})
    assert result['contrast_histogram'] == {7: 1, 8: 1}
    assert result['categories'] == {
        'LOW_CONTRAST_BACKGROUND_CANDIDATE': 1,
        'SOURCE_ONLY_UNRESOLVED': 1,
    }
