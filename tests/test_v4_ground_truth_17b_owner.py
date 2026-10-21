"""Synthetic scoped-approval and endpoint controls; no external recognition execution."""

import copy
from fractions import Fraction

import pytest
from music21 import note, stream

from scripts.research.gt17b_owner_integration import (
    verify_endpoint_pair,
    interpret_inventory,
    relationship_signature,
    core_signature,
)


def pair(kind='tie'):
    score = stream.Score()
    part = stream.Part()
    score.append(part)
    m = stream.Measure(number=1)
    part.append(m)
    notes = [note.Note('C5'), note.Note('C5' if kind == 'tie' else 'B-4')]
    for j, n in enumerate(notes):
        m.insert(j, n)
    inv = {
        'events': [],
        'chords': [{'classification': 'AGENT_VISUAL_CANDIDATE'}],
        'lyrics': [{'classification': 'AGENT_VISUAL_CANDIDATE'}],
        'continuations': [{'classification': 'AGENT_VISUAL_CANDIDATE'}],
    }
    graph = {
        'symbols': {},
        'staves': [{'id': 'staff1', 'system': 'sheet#1:system:1', 'interline': 18}],
    }
    for j, n in enumerate(notes):
        sid = f'h{j}'
        b = [100 + j * 60, 100, 125 + j * 60, 120]
        inv['events'].append(
            {
                'id': f'e{j}',
                'symbol_id': sid,
                'printed_measure': 1,
                'onset': str(j),
                'pitch': n.pitch.nameWithOctave,
                'tie': None,
                'source_bbox': b,
                'voice': '1',
                'source_verification': 'UNVERIFIED',
                'source_symbol': {'staff': 'staff1'},
            }
        )
        graph['symbols'][sid] = {
            'id': sid,
            'kind': 'head',
            'geometry': {'bbox': b},
            'system': 'sheet#1:system:1',
            'pitch_position': 35 - n.pitch.diatonicNoteNum,
        }
    case = {
        'endpoint_source_ids': ['h0', 'h1'],
        'measure': 1,
        'onset': '0',
        'to_measure': 1,
        'to_onset': '1',
        'source_window': [90, 60, 190, 130],
    }
    spec = {'kind': kind, 'system': 1, 'points': [[112, 90], [130, 70], [150, 70], [172, 90]]}
    return score, inv, graph, case, spec


@pytest.mark.parametrize('kind', ['tie', 'slur'])
def test_exact_ids_staff_pitch_and_geometry_can_bind_a_reviewed_pair(kind):
    score, inv, graph, case, spec = pair(kind)
    ends, notes = verify_endpoint_pair(score, inv, graph, case, spec)
    assert [e['symbol_id'] for e in ends] == ['h0', 'h1']
    assert len(notes) == 2


@pytest.mark.parametrize(
    'bad',
    [
        'unequal-tie',
        'wrong-id',
        'wrong-address',
        'wrong-pitch',
        'wrong-staff-position',
        'wrong-system',
        'wrong-bbox',
        'wrong-voice',
        'existing-tie',
        'remote-geometry',
        'reversed',
        'intervening-event',
    ],
)
def test_unresolved_or_conflicting_endpoints_fail_closed(bad):
    score, inv, graph, case, spec = pair()
    if bad == 'unequal-tie':
        score.parts[0].measure(1).notes[1].pitch.name = 'D'
        inv['events'][1]['pitch'] = 'D5'
        graph['symbols']['h1']['pitch_position'] = (
            35 - score.parts[0].measure(1).notes[1].pitch.diatonicNoteNum
        )
    if bad == 'wrong-id':
        case['endpoint_source_ids'][1] = 'h0'
    if bad == 'wrong-address':
        inv['events'][1]['onset'] = '2'
    if bad == 'wrong-pitch':
        inv['events'][1]['pitch'] = 'D5'
    if bad == 'wrong-staff-position':
        graph['symbols']['h1']['pitch_position'] += 1
    if bad == 'wrong-system':
        graph['symbols']['h1']['system'] = 'sheet#1:system:2'
    if bad == 'wrong-bbox':
        graph['symbols']['h1']['geometry']['bbox'] = [0, 0, 10, 10]
    if bad == 'wrong-voice':
        inv['events'][1]['voice'] = '2'
    if bad == 'existing-tie':
        from music21 import tie

        score.parts[0].measure(1).notes[0].tie = tie.Tie('stop')
    if bad == 'remote-geometry':
        spec['points'][0][0] = 10
    if bad == 'reversed':
        spec['points'].reverse()
    if bad == 'intervening-event':
        inv['events'].insert(1, {'symbol_id': 'other'})
    with pytest.raises(ValueError):
        verify_endpoint_pair(score, inv, graph, case, spec)


def test_wording_approval_does_not_promote_event_onset_or_continuation():
    _, inv, _, _, _ = pair()
    old = copy.deepcopy(inv)
    result = interpret_inventory(inv)
    assert inv == old
    assert result['events'][0]['source_verification'] == 'UNVERIFIED'
    assert result['lyrics'][0]['association_status'] == 'OMR_PROVISIONAL_NOT_OWNER_VERIFIED'
    assert result['lyrics'][0]['wording_and_row_status'] == 'OWNER_VERIFIED_SOURCE'
    assert result['continuations'][0]['classification'] == 'AGENT_VISUAL_CANDIDATE'
    assert result['repeat_playback'] == 'UNRESOLVED'
    assert result['independent_ground_truth'] == 0


def test_slur_roundtrip_requires_precise_ordered_endpoints_and_never_ties(tmp_path):
    from music21 import converter, spanner, tie

    score, _, _, case, _ = pair('slur')
    notes = score.parts[0].measure(1).notes
    score.insert(0, spanner.Slur(*notes))
    evidence = [{'source_case': case, 'kind': 'slur', 'case': 'reviewed-slur'}]
    score.write('musicxml', fp=tmp_path / 'source.musicxml')
    parsed = converter.parse(tmp_path / 'source.musicxml')
    assert relationship_signature(parsed, evidence)[0]['roles'] == [None, None]
    assert core_signature(score) == core_signature(parsed)
    parsed.parts[0].measure(1).notes[0].tie = tie.Tie('start')
    with pytest.raises(ValueError):
        relationship_signature(parsed, evidence)


@pytest.mark.parametrize(
    'kind,obj,src,dst,x,bbox,expected',
    [
        ('tie', 'barline', 21, 22, 1240, [1236, 2100, 1240, 2300], True),
        ('slur', 'barline', 21, 22, 1240, [1236, 2100, 1240, 2300], False),
        ('tie', 'barline', 21, 21, 1240, [1236, 2100, 1240, 2300], False),
        ('tie', 'barline', 21, 23, 1240, [1236, 2100, 1240, 2300], False),
        ('tie', 'barline', 21, 22, 1200, [1236, 2100, 1240, 2300], False),
        ('tie', 'head', 21, 22, 1240, [1236, 2100, 1240, 2300], False),
    ],
)
def test_only_own_adjacent_boundary_tie_contact_is_permitted(
    kind, obj, src, dst, x, bbox, expected
):
    from scripts.research.gt17b_owner_integration import permitted_curve_contact

    assert permitted_curve_contact(kind, obj, src, dst, x, bbox) is expected
