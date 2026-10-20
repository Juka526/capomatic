"""Synthetic controls for tightly bound approval and addition-only rendering."""

import copy
import json

import numpy as np
import pytest
from PIL import Image, ImageDraw

from scripts.research import gt14d_confirmed_extenders as gt


def approved_fixture(tmp_path):
    message = tmp_path / 'approval.txt'
    message.write_text('SYNTHETIC TEST APPROVAL; NOT A REAL SUBMISSION')
    packet = tmp_path / 'packet.json'
    packet.write_text('frozen synthetic context')
    path = tmp_path / 'binding.json'
    binding = {
        'classification': 'OWNER_VERIFIED_SOURCE',
        'independent_ground_truth': False,
        'source_ink_replacement_authorized': False,
        'approval_file': message.name,
        'approval_sha256': gt.sha(message),
        'packet_files': {str(packet): gt.sha(packet)},
        'approved_ids': ['a', 'b', 'c'],
    }
    candidates = [
        {
            'id': i,
            'classification': 'AGENT_VISUAL_CANDIDATE',
            'owner_response': None,
            'note_context': {'new_stroke_association_evidence': 'AGENT_VISUAL_CANDIDATE'},
        }
        for i in ['a', 'b', 'c']
    ]
    path.write_text(json.dumps(binding))
    return path, binding, candidates


def test_approval_separate_layer_preserves_historical_candidate_and_no_independence(tmp_path):
    p, _, c = approved_fixture(tmp_path)
    before = copy.deepcopy(c)
    records = gt.approved_records(p, c)
    assert c == before
    assert all(
        r['classification'] == 'OWNER_VERIFIED_SOURCE' and r['owner_response'] == 'OWNER_CONFIRMED'
        for r in records
    )
    assert all(
        not r['independent_ground_truth']
        and r['new_rendering_authorized'] == 'STANDALONE_EXPERIMENT_ONLY'
        for r in records
    )


@pytest.mark.parametrize(
    'failure',
    [
        'message',
        'packet',
        'independence',
        'ink-scope',
        'missing-case',
        'duplicate-case',
        'historical-promotion',
    ],
)
def test_approval_fails_closed_on_wrong_scope_identity_or_provenance(tmp_path, failure):
    p, b, c = approved_fixture(tmp_path)
    if failure == 'message':
        (tmp_path / 'approval.txt').write_text('changed')
    if failure == 'packet':
        (tmp_path / 'packet.json').write_text('changed')
    if failure == 'independence':
        b['independent_ground_truth'] = True
    if failure == 'ink-scope':
        b['source_ink_replacement_authorized'] = True
    if failure == 'missing-case':
        c.pop()
    if failure == 'duplicate-case':
        c[2]['id'] = 'a'
        b['approved_ids'][2] = 'a'
    if failure == 'historical-promotion':
        c[0]['classification'] = 'OWNER_VERIFIED_SOURCE'
    p.write_text(json.dumps(b))
    with pytest.raises(ValueError):
        gt.approved_records(p, c)


def fixture_masks():
    size = (150, 150)

    def dot(x, y):
        p = Image.new('L', size)
        p.putpixel((x, y), 255)
        return p

    lyrics = {f'lyric-{i}': dot(10 + i * 5, 110) for i in range(14)}
    old = {f'old-{i}': dot(20 + i * 40, 90) for i in range(3)}
    parts = {
        f'new-{i}': gt.extender(size, [20 + i * 40, 60, 30 + i * 40, 65], 0, (0, 0, 150, 150))
        for i in range(3)
    }
    music = Image.new('L', size)
    ImageDraw.Draw(music).line((5, 20, 140, 20), fill=255, width=2)
    base = gt.union([music, *lyrics.values(), *old.values()])
    return base, lyrics, old, parts


def test_additions_only_no_duplicates_no_old_pixel_change_and_determinism():
    base, lyrics, old, parts = fixture_masks()
    before = base.tobytes()
    a, r = gt.additions_metrics(parts, base, lyrics, old)
    b, rr = gt.additions_metrics(parts, base, lyrics, old)
    assert a.tobytes() == b.tobytes() and r == rr
    assert base.tobytes() == before and r['old_ink_intensities_unchanged']
    support = np.asarray(gt.union(list(parts.values()))) > 0
    assert np.array_equal(np.asarray(a)[~support], np.asarray(base)[~support])
    assert r['all_lyric_music_contact_pixels'] == 0 and r['all_text_component_contact_pairs'] == []


@pytest.mark.parametrize('obstacle', ['music', 'syllable', 'old-extender'])
def test_any_actual_alpha_contact_rejected_without_layout_change(obstacle):
    base, lyrics, old, parts = fixture_masks()
    xy = (parts['new-0'].getbbox()[0], parts['new-0'].getbbox()[1])
    if obstacle == 'syllable':
        lyrics['lyric-0'].putpixel(xy, 1)
    if obstacle == 'old-extender':
        old['old-0'].putpixel(xy, 1)
    base.putpixel(xy, 1)
    with pytest.raises(ValueError, match='Collision'):
        gt.additions_metrics(parts, base, lyrics, old)


def test_odd_support_box_reuses_existing_half_pixel_phase_without_offset_tuning():
    p = gt.extender((100, 100), [20, 40, 57, 45], 8, (0, 0, 100, 100))
    assert p.getbbox() == (20, 50, 57, 52)
    assert np.count_nonzero(np.asarray(p)) == 74
    assert (50 + 52 - 1) / 2 - (40 + 45 - 1) / 2 - 8 == 0.5
