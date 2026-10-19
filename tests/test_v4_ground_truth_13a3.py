"""Owner-source evidence boundaries and unchanged semantic transposition contracts."""

import copy
from fractions import Fraction

from music21 import harmony, key, note, stream
import pytest

from backend.omr_v3.chords import chord_text
from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt13a3_owner_verification import (
    EXPECTED,
    QUARTERS,
    confirmed_inventory,
    add_confirmed_chord,
    verify_events,
)


def rows(events, measure):
    return [
        {
            'event_id': f'm{measure}:{i}',
            'kind': 'NOTE' if p else 'REST',
            'pitch': p,
            'onset': o,
            'duration': d,
            'tie': t,
            'source_verification': 'UNVERIFIED',
            'render_evidence': 'OMR_PROVISIONAL',
        }
        for i, (p, o, d, t) in enumerate(events)
    ]


def inventory():
    return {
        'measures': [
            {
                'printed_measure': n,
                'events': rows(QUARTERS if n == 3 else EXPECTED[n], n),
                'original_confirmation_reference': 'GT12' if n == 3 else None,
            }
            for n in (1, 2, 3, 4)
        ],
        'owner_verified_measure_scope': [3],
    }


def test_owner_update_does_not_change_raw_rows_or_gt12_confirmation():
    old = inventory()
    before = copy.deepcopy(old)
    new = confirmed_inventory(old, 'actual-owner-message-hash')
    assert old == before
    assert new['measures'][2] == old['measures'][2]
    assert new['owner_verified_measure_scope'] == [1, 2, 3, 4]
    assert new['owner_verified_music_event_count'] == 26 and new['newly_verified_event_count'] == 22
    assert new['independent_ground_truth'] is False
    for i in (0, 1, 3):
        assert all(
            e['source_verification'] == 'OWNER_VERIFIED_SOURCE'
            for e in new['measures'][i]['events']
        )
        assert new['measures'][i]['lyric_note_associations'].startswith('UNVERIFIED')
        assert new['measures'][i]['lyric_strings_status'] == 'OWNER_CONFIRMED_LYRIC_TRANSCRIPTION'
    assert new['outgoing_tie']['destination'] == 'UNVERIFIED'


@pytest.mark.parametrize(
    'field,value',
    [('pitch', 'D4'), ('onset', '3/2'), ('duration', '1/2'), ('tie', 'start'), ('kind', 'REST')],
)
def test_wrong_music_content_cannot_inherit_approval(field, value):
    e = rows(QUARTERS, 1)
    e[1][field] = value
    with pytest.raises(ValueError, match='Owner'):
        verify_events(e, QUARTERS)


def test_missing_event_or_changed_local_tie_rejected():
    with pytest.raises(ValueError, match='count'):
        verify_events(rows(QUARTERS, 1)[:-1], QUARTERS)
    e = rows(EXPECTED[2], 2)
    e[5]['tie'] = None
    with pytest.raises(ValueError, match='tie'):
        verify_events(e, EXPECTED[2])


def test_duplicate_event_id_rejected():
    old = inventory()
    old['measures'][1]['events'][0]['event_id'] = old['measures'][0]['events'][0]['event_id']
    with pytest.raises(ValueError, match='Duplicate'):
        confirmed_inventory(old, 'hash')


def score():
    s = stream.Score()
    p = stream.Part()
    for n in (1, 2, 3, 4):
        m = stream.Measure(number=n)
        if n == 1:
            m.insert(0, key.KeySignature(-2))
        for written, o, d, t in QUARTERS if n == 3 else EXPECTED[n]:
            e = (
                note.Note(written, quarterLength=Fraction(d))
                if written
                else note.Rest(quarterLength=Fraction(d))
            )
            m.insert(Fraction(o), e)
        if n == 3:
            m.insert(0, harmony.ChordSymbol('F'))
        p.append(m)
    s.append(p)
    return s


@pytest.mark.parametrize('shift,target', [(-1, 'A'), (-3, 'G')])
def test_bb_chord_uses_existing_transposition_retains_context_and_no_added_m2_m4(shift, target):
    original = score()
    updated = add_confirmed_chord(original)
    assert not list(original.parts[0].measure(1).getElementsByClass(harmony.ChordSymbol))
    result = copy.deepcopy(updated)
    summary = transpose_score(result, shift, 'key')
    assert validate(updated, result, shift, 'key', summary).ok
    c = list(result.parts[0].measure(1).getElementsByClass(harmony.ChordSymbol))
    assert len(c) == 1 and chord_text(c[0]) == target and c[0].offset == 0
    assert (
        next(
            n for n in result.parts[0].measure(1).notes if not isinstance(n, harmony.ChordSymbol)
        ).offset
        == 1
    )
    assert not any(
        list(result.parts[0].measure(n).getElementsByClass(harmony.ChordSymbol)) for n in (2, 4)
    )
    assert (
        list(updated.parts[0].measure(3).getElementsByClass(harmony.ChordSymbol))[0].figure == 'F'
    )


def test_existing_harmony_cannot_be_overwritten():
    s = score()
    s.parts[0].measure(1).insert(0, harmony.ChordSymbol('C'))
    with pytest.raises(ValueError, match='existing'):
        add_confirmed_chord(s)
