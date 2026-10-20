"""Trust-boundary and interpretation checks; no recognition engine or reference pages."""

import copy

import pytest
from music21 import harmony, note, stream

from scripts.research.gt15b_confirmed_third_system import music_signature
from scripts.research.gt11_complete_measure import events_of
from scripts.research.gt16b_confirmed_fourth_system import WITHHELD, augment, interpretation


def inventory():
    return {
        'recognized_events': 18,
        'measures': [
            {
                'printed_measure': n,
                'candidate_status': 'AGENT_VISUAL_CANDIDATE',
                'events': [
                    {'render_evidence': 'OMR_PROVISIONAL', 'source_verification': 'UNVERIFIED'}
                ],
            }
            for n in range(13, 17)
        ],
        'ambiguous_SIG_objects': [{'symbol': {'id': n}} for n in sorted(WITHHELD)],
        'candidate_continuation_marks': [{'id': str(i)} for i in range(7)],
    }


def test_owner_interpretation_is_separate_and_withheld_objects_stay_unclassified():
    inv = inventory()
    old = copy.deepcopy(inv)
    layer = interpretation(inv, {'classification': 'OWNER_VERIFIED_SOURCE'})
    assert inv == old
    assert layer['independent_ground_truth'] is False
    assert layer['repeat_playback_route'] == 'EXPLICITLY_WITHHELD'
    assert all(
        r['interpretation_status'] == 'EXPLICITLY_WITHHELD_UNCLASSIFIED'
        for r in layer['ambiguous_SIG_objects']
    )
    assert all(
        m['events'][0]['source_verification'] == 'OWNER_VERIFIED_SOURCE'
        and m['events'][0]['historical_render_evidence'] == 'OMR_PROVISIONAL'
        for m in layer['measures']
    )


@pytest.mark.parametrize('bad', ['count', 'mark', 'SIG', 'candidate'])
def test_changed_frozen_candidate_scope_fails_closed(bad):
    inv = inventory()
    if bad == 'count':
        inv['recognized_events'] = 17
    if bad == 'mark':
        inv['candidate_continuation_marks'].pop()
    if bad == 'SIG':
        inv['ambiguous_SIG_objects'].pop()
    if bad == 'candidate':
        inv['measures'][0]['candidate_status'] = 'UNKNOWN'
    with pytest.raises(ValueError):
        interpretation(inv, {})


def score_and_layer():
    score = stream.Score()
    part = stream.Part()
    score.append(part)
    for j in range(1, 17):
        m = stream.Measure(number=j)
        n = note.Note('C4', quarterLength=4)
        n.addLyric('raw')
        m.append(n)
        part.append(m)
    ms = list(part.getElementsByClass(stream.Measure))
    ms[0].insert(0, harmony.ChordSymbol('B-'))
    ms[13].insert(0, harmony.ChordSymbol('Gm7'))
    layer = {'measures': []}
    for number, word, upper, lower in [
        (13, None, ['주'], ['주']),
        (14, 'Gm7', ['씀'], ['말']),
        (15, 'Bb/D', ['네'], []),
        (16, 'Eb', [], []),
    ]:
        layer['measures'].append(
            {
                'printed_measure': number,
                'agent_candidates': {
                    'chord': word,
                    'upper': upper,
                    'lower': lower,
                    'upper_onsets': ['0'] * len(upper),
                    'lower_onsets': ['0'] * len(lower),
                },
            }
        )
    return score, layer


def test_augmented_source_preserves_all_events_prior_lyrics_and_no_lyrics_on_blank_rows():
    source, layer = score_and_layer()
    new = augment(source, layer)
    assert music_signature(source) == music_signature(new)
    oldms = list(source.parts[0].getElementsByClass(stream.Measure))
    ms = list(new.parts[0].getElementsByClass(stream.Measure))
    assert [n.lyric for n in events_of(oldms[0])] == [n.lyric for n in events_of(ms[0])] == ['raw']
    assert [c.figure for c in oldms[0].getElementsByClass(harmony.ChordSymbol)] == ['B-']
    assert not list(ms[12].getElementsByClass(harmony.ChordSymbol))
    assert [c.figure for c in ms[14].getElementsByClass(harmony.ChordSymbol)] == ['B-/D']
    assert [(l.number, l.text) for l in events_of(ms[14])[0].lyrics] == [(1, '네')]
    assert not events_of(ms[15])[0].lyrics
    assert ms[12].notes[0].lyric != oldms[12].notes[0].lyric


def test_unexpected_existing_harmony_is_not_silently_duplicated():
    source, layer = score_and_layer()
    list(source.parts[0].getElementsByClass(stream.Measure))[14].insert(0, harmony.ChordSymbol('C'))
    with pytest.raises(ValueError, match='Unexpected prior'):
        augment(source, layer)


def test_invalid_association_does_not_silently_choose_nearest_note():
    source, layer = score_and_layer()
    layer['measures'][0]['agent_candidates']['upper_onsets'] = ['1']
    with pytest.raises(ValueError, match='lyric note missing'):
        augment(source, layer)


def test_owner_binding_rejects_changed_submission_and_false_independence(tmp_path):
    import hashlib
    import json
    from scripts.research.gt16b_confirmed_fourth_system import verify_owner

    packet = tmp_path / 'owner-review'
    packet.mkdir()
    (packet / 'packet-freeze.json').write_text('{"files":{}}')
    submission = tmp_path / 'approval.txt'
    submission.write_text('actual owner instruction\n')
    binding = {
        'classification': 'OWNER_VERIFIED_SOURCE',
        'independent_ground_truth': False,
        'source_ink_replacement_authorized': False,
        'withheld_SIG_ids': sorted(WITHHELD),
        'repeat_playback_route': 'EXPLICITLY_WITHHELD',
        'files': {str(submission): hashlib.sha256(submission.read_bytes()).hexdigest()},
    }
    path = tmp_path / 'binding.json'
    path.write_text(json.dumps(binding))
    assert verify_owner(path, tmp_path) == binding
    submission.write_text('changed\n')
    with pytest.raises(ValueError, match='context changed'):
        verify_owner(path, tmp_path)
    binding['independent_ground_truth'] = True
    path.write_text(json.dumps(binding))
    with pytest.raises(ValueError, match='approval scope'):
        verify_owner(path, tmp_path)
