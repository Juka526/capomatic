"""Fail-closed, synthetic owner approval boundaries. No score files required."""

import copy

import pytest

from scripts.research.gt17e_owner_confirmation import (
    GROUP_COUNTS,
    approved_scope,
    lyric_scope,
    unique_by,
)


def fixture_scope():
    groups, events, systems = [], [], []
    for system, (group_id, count) in enumerate(GROUP_COUNTS.items(), 6):
        measure = {6: 20, 7: 25, 8: 30, 9: 34}[system]
        systems.append({'system': system, 'printed_measures': [measure]})
        items = []
        for index in range(count):
            sid = f'sheet#1:{system}-{index}'
            e = {
                'id': f'event-{system}-{index}',
                'symbol_id': sid,
                'printed_measure': measure,
                'part': 1,
                'voice': '1',
                'kind': 'NOTE',
                'pitch': 'C4',
                'onset': str(index),
                'duration': '1',
                'source_bbox': [index, 0, index + 1, 1],
                'source_verification': 'UNVERIFIED',
            }
            events.append(e)
            items.append(
                {
                    'id': 'event-' + sid,
                    'kind': 'event',
                    'source_object_id': sid,
                    'measure': measure,
                    'source_window': e['source_bbox'],
                    'candidate': {
                        'music_event_kind': 'NOTE',
                        'written_pitch': 'C4',
                        'onset': str(index),
                        'duration': '1',
                        'voice': '1',
                    },
                }
            )
        groups.append({'group_id': group_id, 'items': items})
    lyrics = []
    items = []
    for index in range(40):
        e = events[index % 30]
        row = 1 + index // 30
        lid = f'm20-r{row}-o{e["onset"]}'
        l = {
            'id': lid,
            'measure': 20,
            'event_id': e['id'],
            'row': row,
            'onset': e['onset'],
            'text': '가',
        }
        lyrics.append(l)
        items.append(
            {
                'id': 'lyric-' + lid,
                'kind': 'lyric_onset',
                'source_object_id': e['symbol_id'],
                'measure': 20,
                'candidate': {k: l[k] for k in ['onset', 'row', 'text']},
            }
        )
    groups.append({'group_id': 'SYS6_LYRIC_ONSET', 'items': items})
    return {'groups': groups}, {'events': events, 'systems': systems, 'lyrics': lyrics}


def test_exact_approval_does_not_mutate_candidates():
    plan, inv = fixture_scope()
    before = copy.deepcopy((plan, inv))
    assert len(approved_scope(plan, inv)) == 83
    assert len(lyric_scope(plan, inv)) == 40
    assert (plan, inv) == before


@pytest.mark.parametrize(
    'change',
    [
        'missing_group',
        'duplicate_group',
        'missing_case',
        'duplicate_case',
        'unknown_source',
        'wrong_measure',
        'wrong_pitch',
        'wrong_onset',
        'wrong_duration',
        'wrong_voice',
        'wrong_bbox',
        'duplicate_source',
        'duplicate_event_id',
        'already_approved',
    ],
)
def test_rejects_event_scope_errors(change):
    plan, inv = fixture_scope()
    item = plan['groups'][0]['items'][0]
    if change == 'missing_group':
        plan['groups'].pop(0)
    elif change == 'duplicate_group':
        plan['groups'].append(copy.deepcopy(plan['groups'][0]))
    elif change == 'missing_case':
        plan['groups'][0]['items'].pop()
    elif change == 'duplicate_case':
        plan['groups'][0]['items'][1] = copy.deepcopy(item)
    elif change == 'unknown_source':
        item['source_object_id'] = 'absent'
    elif change == 'wrong_measure':
        item['measure'] = 19
    elif change == 'wrong_pitch':
        item['candidate']['written_pitch'] = 'D4'
    elif change == 'wrong_onset':
        item['candidate']['onset'] = '1/2'
    elif change == 'wrong_duration':
        item['candidate']['duration'] = '1/2'
    elif change == 'wrong_voice':
        item['candidate']['voice'] = '2'
    elif change == 'wrong_bbox':
        item['source_window'] = [0, 0, 10, 10]
    elif change == 'duplicate_source':
        inv['events'].append(copy.deepcopy(inv['events'][0]))
    elif change == 'duplicate_event_id':
        inv['events'][1]['id'] = inv['events'][0]['id']
    elif change == 'already_approved':
        inv['events'][0]['source_verification'] = 'OWNER_VERIFIED_SOURCE'
    with pytest.raises(ValueError):
        approved_scope(plan, inv)


@pytest.mark.parametrize(
    'change',
    [
        'duplicate',
        'missing',
        'wrong_text',
        'wrong_row',
        'wrong_onset',
        'wrong_event',
        'rest',
        'other_system',
    ],
)
def test_lyric_approval_has_its_own_exact_boundary(change):
    plan, inv = fixture_scope()
    item = plan['groups'][-1]['items'][0]
    if change == 'duplicate':
        plan['groups'][-1]['items'][1] = copy.deepcopy(item)
    elif change == 'missing':
        plan['groups'][-1]['items'].pop()
    elif change == 'wrong_text':
        item['candidate']['text'] = '나'
    elif change == 'wrong_row':
        item['candidate']['row'] = 2
    elif change == 'wrong_onset':
        item['candidate']['onset'] = '1/4'
    elif change == 'wrong_event':
        inv['lyrics'][0]['event_id'] = 'absent'
    elif change == 'rest':
        inv['events'][0]['kind'] = 'REST'
    elif change == 'other_system':
        item['measure'] = 25
    with pytest.raises(ValueError):
        lyric_scope(plan, inv)


def test_empty_or_duplicate_identity_not_accepted():
    with pytest.raises(ValueError):
        unique_by([{'id': 'same'}, {'id': 'same'}], 'id')


def test_semantic_address_includes_rests_and_rejects_ambiguity():
    from music21 import note, stream
    from scripts.research.gt17e_owner_confirmation import semantic_event

    score, part, measure = stream.Score(), stream.Part(), stream.Measure(number=1)
    rest = note.Rest(quarterLength=1)
    measure.insert(0, rest)
    part.append(measure)
    score.append(part)
    assert semantic_event(score, 1, '0') is rest
    with pytest.raises(ValueError):
        semantic_event(score, 1, '2')
    measure.insert(0, note.Note('C4'))
    with pytest.raises(ValueError):
        semantic_event(score, 1, '0')


def test_event_core_approval_does_not_cover_notation_or_lyrics():
    from scripts.research.gt17e_owner_confirmation import CORE_FIELDS

    assert CORE_FIELDS == ['kind', 'pitch', 'onset', 'duration', 'voice', 'part']


def test_event_approval_does_not_require_or_imply_lyric_approval():
    plan, inv = fixture_scope()
    plan['groups'][-1]['items'][0]['candidate']['text'] = 'UNKNOWN'
    assert len(approved_scope(plan, inv)) == 83
    with pytest.raises(ValueError):
        lyric_scope(plan, inv)


def test_lyric_case_namespace_is_exact():
    plan, inv = fixture_scope()
    item = plan['groups'][-1]['items'][0]
    item['id'] = item['id'].removeprefix('lyric-')
    with pytest.raises(ValueError):
        lyric_scope(plan, inv)
