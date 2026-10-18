"""Synthetic beam/lineage checks; no copyrighted inputs or Audiveris execution."""

import copy
import math
from fractions import Fraction

import numpy as np
from PIL import Image, ImageDraw
import pytest
from music21 import note, beam

from scripts.research.gt06_extended import (
    beam_geometry,
    contacts,
    group_evidence,
    semantic_check,
    choose,
)
from scripts.research.paired_ground_truth_01 import line_y


def beams():
    return [
        {
            'id': str(i),
            'geometry': {
                'line': [[40, 60 + i * 14], [140, 65 + i * 14]],
                'thickness': 10,
                'valid': True,
            },
            'kind': 'beam',
        }
        for i in range(2)
    ]


@pytest.mark.parametrize('up', [True, False])
@pytest.mark.parametrize('delta', [0, 18, -18])
def test_pitch_dependent_beam_retains_slope_and_every_stem_minimum_length(up, delta):
    stems = [(50, 150 + delta), (130, 145 + delta)]
    result = beam_geometry(stems, beams(), 18, up)
    assert len(result) == 2
    for b in result:
        assert b['slope'] == pytest.approx(0.05)
    for x, y in stems:
        end = line_y(result[0]['line'], x)
        assert (y - end if up else end - y) >= 3.5 * 18 - 1e-8
    assert abs(result[1]['line'][0][1] - result[0]['line'][0][1]) == 14
    assert result == beam_geometry(stems, beams(), 18, up)


@pytest.mark.parametrize('bad', ['missing', 'nan', 'zero_span', 'thickness'])
def test_invalid_or_incomplete_geometry_fails_closed(bad):
    stems = [(50, 150), (130, 145)]
    bs = beams()
    if bad == 'missing':
        bs.pop()
    if bad == 'nan':
        stems[0] = (50, math.nan)
    if bad == 'zero_span':
        stems[1] = (50, 145)
    if bad == 'thickness':
        bs[0]['geometry']['thickness'] = 30
    with pytest.raises(ValueError):
        beam_geometry(stems, bs, 18, True)


def fixture():
    rows = [
        {
            'symbol_id': f'h{i}',
            'id': f'n{i}',
            'status': 'MATCHED',
            'kind': 'NOTE',
            'duration': '1/4',
            'chord_size': 1,
            'chord_continuation': False,
            'printed_measures': [6],
            'local_offset': str(Fraction(3, 2) + i * Fraction(1, 4)),
        }
        for i in range(2)
    ]
    group = {'heads': ['h0', 'h1'], 'stems': ['s0', 's1'], 'beams': ['0', '1'], 'id': 'group'}
    relations = []
    for i in range(2):
        relations.append(
            {
                'id': f'hs{i}',
                'kind': 'head-stem',
                'source': f'h{i}',
                'target': f's{i}',
                'attributes': [['head-side', 'RIGHT']],
            }
        )
        for j in range(2):
            relations.append(
                {
                    'id': f'bs{j}{i}',
                    'kind': 'beam-stem',
                    'source': str(j),
                    'target': f's{i}',
                    'attributes': [],
                }
            )
    moves = {
        f'n{i}': {
            'connected_symbols': [['head', [f'h{i}']], ['stem', [f's{i}']], ['beam', ['0', '1']]]
        }
        for i in range(2)
    }
    graph = {'relations': relations, 'symbols': {str(i): b for i, b in enumerate(beams())}}
    return group, rows, moves, graph


def test_complete_atomic_lineage_and_deterministic_earliest_selection():
    args = fixture()
    before = copy.deepcopy(args)
    reasons, stems, ids = group_evidence(*args)
    assert reasons == [] and len(stems) == 2 and len(ids) == 6
    selected = choose([args[0]], args[1], args[2], args[3])
    assert selected[0]['id'] == 'group' and args == before


@pytest.mark.parametrize(
    'bad', ['missing_edge', 'shared_stem', 'attachment', 'partial_heads', 'duration']
)
def test_incomplete_or_attached_groups_never_selected(bad):
    group, rows, moves, graph = fixture()
    if bad == 'missing_edge':
        graph['relations'].pop()
    if bad == 'shared_stem':
        graph['relations'][3]['target'] = 's0'
    if bad == 'attachment':
        graph['relations'].append({'kind': 'slur-head', 'source': 'slur', 'target': 'h0'})
    if bad == 'partial_heads':
        rows.pop()
    if bad == 'duration':
        rows[0]['duration'] = '1/2'
    with pytest.raises(ValueError, match='UNSUPPORTED'):
        choose([group], rows, moves, graph)


def test_semantic_sixteenth_beam_levels_are_not_silently_simplified():
    n = note.Note('C4', quarterLength=0.25)
    n.beams = beam.Beams()
    n.beams.append('start')
    n.beams.append('start')
    semantic_check(n, 0, 'C4')
    n.beams = beam.Beams()
    n.beams.append('start')
    with pytest.raises(ValueError):
        semantic_check(n, 0, 'C4')


def test_actual_ink_contacts_only_allow_explicit_related_stem_beam_pair():
    a = Image.new('L', (60, 60))
    ImageDraw.Draw(a).line([(25, 10), (25, 45)], fill=255, width=2)
    b = Image.new('L', a.size)
    ImageDraw.Draw(b).rectangle((20, 10, 45, 15), fill=255)
    parts = {'stem': a, 'beam': b}
    allow = {frozenset(('stem', 'beam'))}
    hit = contacts(parts, allow)[0]
    assert hit['pixels'] > 0 and hit['intentional']
    assert not contacts({'unrelated_head': a, 'beam': b}, allow)[0]['intentional']
    no = Image.new('L', a.size)
    ImageDraw.Draw(no).rectangle((2, 2, 4, 4), fill=255)
    assert contacts({'head': no, 'stem': a}, set()) == []


def test_independent_actual_raster_anchor_measurement_detects_wrong_translation():
    from scripts.research.gt06_extended import measure_anchor

    image = Image.new('L', (60, 60))
    ImageDraw.Draw(image).ellipse((10, 20, 30, 30), fill=255)
    assert measure_anchor(image, (20, 25))['measured_anchor_residual'] == [0, 0]
    assert measure_anchor(image, (21, 25))['measured_anchor_residual'] == [-1, 0]
    with pytest.raises(ValueError):
        measure_anchor(Image.new('L', image.size), (0, 0))
