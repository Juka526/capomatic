"""Source-independent flag attachment geometry and fail-closed eligibility."""

import copy
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from music21 import note, tie, articulations
import pytest

from scripts.research.gt07_flags import flag_evidence, flag_mask


def fixture():
    row = {
        'status': 'MATCHED',
        'chord_size': 1,
        'chord_continuation': False,
        'duration': '1/2',
        'symbol_id': 'h',
        'pitch': 'F3',
    }
    move = {'connected_symbols': [['head', ['h']], ['stem', ['s']], ['flag', ['f']]]}
    geometry = {'valid': True, 'bbox': [0, 0, 20, 30], 'line': [[0, 0], [0, 30]]}
    graph = {
        'symbols': {
            k: {'geometry': copy.deepcopy(geometry), 'shape': 'FLAG_1' if k == 'f' else k}
            for k in ['h', 's', 'f']
        },
        'relations': [
            {
                'id': 'hs',
                'kind': 'head-stem',
                'source': 'h',
                'target': 's',
                'attributes': [['head-side', 'RIGHT']],
            },
            {'id': 'fs', 'kind': 'flag-stem', 'source': 'f', 'target': 's', 'attributes': []},
        ],
    }
    n = note.Note('F3', quarterLength=0.5)
    n.stemDirection = 'up'
    return row, move, graph, n


def test_eighth_duration_and_two_explicit_relations_define_one_flag():
    args = fixture()
    before = copy.deepcopy(args[:3])
    reasons, edges = flag_evidence(*args)
    assert reasons == [] and edges == ['fs', 'hs'] and args[:3] == before


@pytest.mark.parametrize(
    'bad',
    [
        'duration',
        'double_flag',
        'down',
        'wrong_side',
        'missing_edge',
        'articulation',
        'tie',
        'curve',
        'ambiguous',
        'bad_geometry',
        'pitch',
    ],
)
def test_unsupported_required_notation_is_blocked(bad):
    row, move, g, n = fixture()
    if bad == 'duration':
        n.duration.quarterLength = 0.25
    if bad == 'double_flag':
        g['symbols']['f']['shape'] = 'FLAG_2'
    if bad == 'down':
        n.stemDirection = 'down'
    if bad == 'wrong_side':
        g['relations'][0]['attributes'] = [['head-side', 'LEFT']]
    if bad == 'missing_edge':
        g['relations'].pop()
    if bad == 'articulation':
        n.articulations = [articulations.Staccato()]
    if bad == 'tie':
        n.tie = tie.Tie('start')
    if bad == 'curve':
        g['relations'].append({'kind': 'slur-head', 'source': 'curve', 'target': 'h'})
    if bad == 'ambiguous':
        row['status'] = 'AMBIGUOUS'
    if bad == 'bad_geometry':
        g['symbols']['f']['geometry']['valid'] = False
    if bad == 'pitch':
        n.nameWithOctave = 'G3'
    assert flag_evidence(row, move, g, n)[0]


@pytest.mark.parametrize('phase', [0, 0.125, 0.5, 0.875])
def test_flag_attachment_is_glyph_specific_not_bbox_center_and_deterministic(phase):
    font = ImageFont.load_default(size=40)
    tip = (90 + phase, 100 + phase)
    mask, info = flag_mask((300, 300), font, tip, (0, 0, 20, 40), 0.04, char='f')
    assert max(abs(v) for v in info['flag_attachment_residual']) <= 0.5
    assert info['actual_flag_attachment'] != info['raster_ink_bbox_center']
    again, _ = flag_mask((300, 300), font, tip, (0, 0, 20, 40), 0.04, char='f')
    assert mask.tobytes() == again.tobytes()
    stem = Image.new('L', mask.size)
    point = info['actual_flag_attachment']
    ImageDraw.Draw(stem).line([point, (point[0], point[1] + 70)], fill=255, width=2)
    assert np.count_nonzero((np.asarray(stem) > 0) & (np.asarray(mask) > 0)) > 0


def test_flag_clipping_and_nonfinite_fail_closed():
    font = ImageFont.load_default(size=40)
    with pytest.raises(ValueError):
        flag_mask((100, 100), font, (99, 99), (0, 0, 20, 40), 0.04, char='f')
    with pytest.raises(ValueError):
        flag_mask((100, 100), font, (math.nan, 20), (0, 0, 20, 40), 0.04, char='f')
