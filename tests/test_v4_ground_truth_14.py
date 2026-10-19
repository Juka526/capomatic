"""Synthetic audit and provenance boundaries; component tests remain unchanged."""

import copy
from pathlib import Path

import pytest
from music21 import stream, note, tie

from scripts.research import gt14_second_system as gt


def fixture(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    source.write_bytes(b'SYNTHETIC_SOURCE')
    monkeypatch.setattr(gt, 'SOURCE', source)
    score = stream.Score()
    part = stream.Part()
    score.append(part)
    rows = []
    symbols = {}
    geom = []
    registration = []
    for number in range(1, 9):
        m = stream.Measure(number=number)
        part.append(m)
        if number < 5:
            continue
        n = note.Note('B-3', quarterLength=4)
        n.tie = tie.Tie('stop') if number in (5, 7) else None
        m.append(n)
        ident = 'sheet#1:1923' if number == 5 else f'synthetic:{number}'
        eid = f'p1:m{number-1}:n0'
        rows.append(
            {
                'id': eid,
                'symbol_id': ident,
                'omr_measure_index': number - 1,
                'printed_measures': [number],
                'local_offset': '0',
                'duration': '4',
                'pitch': 'B-3',
                'bbox': [number * 100, 100, number * 100 + 25, 120],
                'voice': None,
            }
        )
        symbols[ident] = {
            'id': ident,
            'system': 'system2',
            'kind': 'head',
            'grade': 0.8,
            'contextual_grade': 0.9,
        }
        geom.append(
            {
                'system': 'system2',
                'number': str(number),
                'bounds': [number * 100, 50, number * 100 + 90, 150],
                'source_xml': '<measure><voice id="1"/></measure>',
            }
        )
        registration.append(
            {
                'printed_measure': number,
                'left': {'x': number * 100},
                'right': {'x': number * 100 + 90},
            }
        )
    graph = {
        'staves': [{'id': 'sheet#1:2', 'system': 'system2'}],
        'symbols': symbols,
        'measures': geom,
        'relations': [],
    }
    return score, graph, rows, {'measures': registration}


def test_same_pitch_does_not_inherit_owner_confirmation(tmp_path, monkeypatch):
    inv = gt.system_inventory(*fixture(tmp_path, monkeypatch))
    events = [e for m in inv['measures'] for e in m['events']]
    assert [e['source_verification'] for e in events] == [
        'OWNER_VERIFIED_SOURCE',
        'UNVERIFIED',
        'UNVERIFIED',
        'UNVERIFIED',
    ]
    assert events[2]['tie'] == 'stop' and events[2]['render_evidence'] == 'OMR_PROVISIONAL'
    assert inv['SOURCE_RECOGNITION_COMPLETENESS'] == 'UNVERIFIED'
    assert all(e['voice'] == '1' for e in events)
    assert all(m['lyrics_and_associations'] == 'UNVERIFIED_NOT_RENDERED' for m in inv['measures'])


@pytest.mark.parametrize('mutation', ['offset', 'duration', 'pitch', 'mapping', 'confirmed-role'])
def test_inventory_identity_and_confirmed_endpoint_fail_closed(tmp_path, monkeypatch, mutation):
    args = list(fixture(tmp_path, monkeypatch))
    r = args[2][0]
    if mutation == 'offset':
        r['local_offset'] = '1'
    if mutation == 'duration':
        r['duration'] = '2'
    if mutation == 'pitch':
        r['pitch'] = 'C4'
    if mutation == 'mapping':
        r['printed_measures'] = [5, 6]
    if mutation == 'confirmed-role':
        args[0].parts[0].getElementsByClass(stream.Measure)[4].notes[0].tie = tie.Tie('start')
    with pytest.raises(ValueError):
        gt.system_inventory(*args)


def local_fixture():
    curve = {'id': 'c', 'geometry': {'curve': [[10, 33], [15, 40], [25, 40], [30, 33]]}}
    rel = [
        {'source': 'c', 'kind': 'slur-head', 'target': 'a', 'attributes': [['side', 'LEFT']]},
        {'source': 'c', 'kind': 'slur-head', 'target': 'b', 'attributes': [['side', 'RIGHT']]},
    ]
    heads = {
        'a': {
            'event': {'source_bbox': [0, 10, 20, 30], 'tie': 'start'},
            'bbox': [0, 20, 20, 40],
            'target_pitch': 'A3',
        },
        'b': {
            'event': {'source_bbox': [20, 10, 40, 30], 'tie': 'stop'},
            'bbox': [20, 20, 40, 40],
            'target_pitch': 'A3',
        },
    }
    return curve, rel, heads


def test_local_tie_uses_target_raster_bottom_and_keeps_provisional_status():
    cp, r = gt.local_tie(*local_fixture())
    assert cp[0][1] == 43 and cp[-1][1] == 43
    assert r['source_verification'] == 'UNVERIFIED_OMR_PROVISIONAL'
    assert max(abs(v) for p in r['attachment_residuals'] for v in p) <= 0.5


@pytest.mark.parametrize('change', ['pitch', 'role', 'missing', 'anchor'])
def test_local_tie_requires_explicit_correct_endpoints(change):
    c, r, h = local_fixture()
    if change == 'pitch':
        h['b']['target_pitch'] = 'G3'
    if change == 'role':
        h['b']['event']['tie'] = 'start'
    if change == 'missing':
        r.pop()
    if change == 'anchor':
        h['b']['bbox'] = [22, 20, 42, 40]
    with pytest.raises(ValueError):
        gt.local_tie(c, r, h)


def test_related_contact_exclusions_do_not_hide_different_beams():
    r = {'intersections': []}
    assert gt.owners_different('sheet#1:1230', 'sheet#1:1236', r)
    assert not gt.owners_different('p1:m5:n0:head', 'p1:m5:n0:stem', r)
    assert gt.owners_different('p1:m5:n0:head', 'p1:m5:n1:head', r)
