import numpy as np
import pytest
from scripts.research.gt07_flag_contacts import contact_pixels


def test_actual_ink_contact_excludes_empty_envelope_and_reconciles_union():
    mask = np.zeros((10, 10), bool)
    mask[4, 4] = True
    assert contact_pixels(mask, {(3, 3), (4, 4)}) == {(4, 4)}
    assert contact_pixels(mask, {(3, 3)}) == set()
    with pytest.raises(ValueError):
        contact_pixels(mask, {(10, 0)})


def test_contact_report_cannot_write_into_frozen_evidence(tmp_path):
    from scripts.research.gt07_flag_contacts import audit

    with pytest.raises(ValueError, match='New contact'):
        audit(
            tmp_path / 'gt01',
            tmp_path / 'inputs',
            tmp_path / 'prototype',
            tmp_path / 'prototype/report.json',
        )
