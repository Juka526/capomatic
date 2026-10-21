"""Synthetic approval-scope negatives; no copyrighted source or external execution."""

import copy

import pytest

from scripts.research.gt17f_owner_lyric_confirmation import GROUPS, resolve_scope, integrate


def fixture_scope():
    groups, events, lyrics, associations = [], [], [], []
    for group, (count, measures) in GROUPS.items():
        items = []
        for j in range(count):
            measure = measures.start
            eid = f'event-{group}-{j}'
            sid = f'raw-{group}-{j}'
            lid = f'm{measure}-r1-o{j}'
            e = {
                'id': eid,
                'symbol_id': sid,
                'kind': 'NOTE',
                'printed_measure': measure,
                'onset': str(j),
            }
            l = {
                'id': lid,
                'event_id': eid,
                'measure': measure,
                'onset': str(j),
                'row': 1,
                'text': '가',
            }
            i = {
                'id': 'lyric-' + lid,
                'kind': 'lyric_onset',
                'source_object_id': sid,
                'measure': measure,
                'candidate': {k: l[k] for k in ['onset', 'row', 'text']},
            }
            events.append(e)
            lyrics.append(l)
            items.append(i)
            associations.append({'id': lid, 'event_id': eid, 'classification': 'OMR_PROVISIONAL'})
        groups.append({'group_id': group, 'items': items})
    old = [
        {
            'id': f'prior-{j}',
            'event_id': f'prior-event-{j}',
            'classification': 'OWNER_VERIFIED_SOURCE',
        }
        for j in range(40)
    ]
    coverage = {
        'new_scope_lyric_associations': old + associations,
        'prior_verified_lyric_onsets': 88,
        'event_cores': [{'id': 'sentinel', 'classification': 'OWNER_VERIFIED_SOURCE'}],
        'totals': {
            'verified_lyric_onsets': 128,
            'provisional_lyric_onsets': 39,
            'owner_confirmed_event_cores': 169,
            'approved_chords': 24,
            'verified_continuations': 30,
            'provisional_continuations': 20,
        },
    }
    layer = {
        'event_core_overrides': [{'id': 'sentinel'}],
        'lyric_onset_overrides': copy.deepcopy(old),
        'M28_CONTINUATION_LINEAGE': 'UNRESOLVED',
        'FULL_REPEAT_PLAYBACK': 'UNRESOLVED',
    }
    return {'groups': groups}, {'events': events, 'lyrics': lyrics}, coverage, layer


def test_exact_39_approval_preserves_all_previous_fields():
    plan, inv, coverage, layer = fixture_scope()
    before = copy.deepcopy((plan, inv, coverage, layer))
    selected = resolve_scope(plan, inv, coverage)
    assert len(selected) == 39
    updated, matrix = integrate(layer, coverage, selected)
    assert (plan, inv, coverage, layer) == before
    assert updated['lyric_onset_overrides'][:40] == layer['lyric_onset_overrides']
    assert updated['event_core_overrides'] == layer['event_core_overrides']
    assert updated['M28_CONTINUATION_LINEAGE'] == updated['FULL_REPEAT_PLAYBACK'] == 'UNRESOLVED'
    assert (
        matrix['new_scope_lyric_associations'][:40] == coverage['new_scope_lyric_associations'][:40]
    )
    assert all(
        a['classification'] == 'OWNER_VERIFIED_SOURCE'
        for a in matrix['new_scope_lyric_associations']
    )
    assert matrix['totals'] == {
        **coverage['totals'],
        'verified_lyric_onsets': 167,
        'provisional_lyric_onsets': 0,
    }


@pytest.mark.parametrize(
    'change',
    [
        'missing_group',
        'duplicate_group',
        'missing_case',
        'duplicate_case',
        'wrong_case_id',
        'wrong_measure',
        'wrong_text',
        'wrong_row',
        'wrong_onset',
        'missing_event',
        'duplicate_event',
        'duplicate_raw_identity',
        'rest',
        'wrong_raw_id',
        'prior_event_mismatch',
        'already_approved',
        'prior_approved_missing',
        'uncovered_pending',
        'duplicate_coverage',
    ],
)
def test_rejects_bad_scope_before_promotion(change):
    plan, inv, coverage, layer = fixture_scope()
    i = plan['groups'][0]['items'][0]
    if change == 'missing_group':
        plan['groups'].pop()
    elif change == 'duplicate_group':
        plan['groups'].append(copy.deepcopy(plan['groups'][0]))
    elif change == 'missing_case':
        plan['groups'][0]['items'].pop()
    elif change == 'duplicate_case':
        plan['groups'][0]['items'][1] = copy.deepcopy(i)
    elif change == 'wrong_case_id':
        i['id'] = i['id'].removeprefix('lyric-')
    elif change == 'wrong_measure':
        i['measure'] = 20
    elif change == 'wrong_text':
        i['candidate']['text'] = '나'
    elif change == 'wrong_row':
        i['candidate']['row'] = 2
    elif change == 'wrong_onset':
        i['candidate']['onset'] = '1/4'
    elif change == 'missing_event':
        inv['lyrics'][0]['event_id'] = 'absent'
    elif change == 'duplicate_event':
        inv['events'].append(copy.deepcopy(inv['events'][0]))
    elif change == 'duplicate_raw_identity':
        inv['events'][1]['symbol_id'] = inv['events'][0]['symbol_id']
    elif change == 'rest':
        inv['events'][0]['kind'] = 'REST'
    elif change == 'wrong_raw_id':
        i['source_object_id'] = 'unknown'
    elif change == 'prior_event_mismatch':
        coverage['new_scope_lyric_associations'][40]['event_id'] = 'other'
    elif change == 'already_approved':
        coverage['new_scope_lyric_associations'][40]['classification'] = 'OWNER_VERIFIED_SOURCE'
    elif change == 'prior_approved_missing':
        coverage['prior_verified_lyric_onsets'] = 87
    elif change == 'uncovered_pending':
        coverage['new_scope_lyric_associations'][0]['classification'] = 'OMR_PROVISIONAL'
    elif change == 'duplicate_coverage':
        coverage['new_scope_lyric_associations'][1] = copy.deepcopy(
            coverage['new_scope_lyric_associations'][0]
        )
    before = copy.deepcopy((plan, inv, coverage, layer))
    with pytest.raises(ValueError):
        resolve_scope(plan, inv, coverage)
    assert (plan, inv, coverage, layer) == before


def test_existing_override_cannot_be_added_twice():
    plan, inv, coverage, layer = fixture_scope()
    selected = resolve_scope(plan, inv, coverage)
    layer['lyric_onset_overrides'].append({'id': selected[0][2]['id']})
    with pytest.raises(ValueError):
        integrate(layer, coverage, selected)
