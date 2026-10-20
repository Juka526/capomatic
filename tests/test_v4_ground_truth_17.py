"""Synthetic fifth-system coordinate coverage, lineage and frozen-layer controls."""

import copy

import numpy as np
import pytest
from music21 import note, stream
from PIL import Image

from scripts.research.gt13a6_tie_rendering import calibrated_whole_head, whole_head
from scripts.research.gt14a_notation import whole_rest
from scripts.research.gt15_third_system import render_music
from scripts.research.gt17_fifth_system import second_ending, panel, CANDIDATES


def staff():
    return {
        'system': 'five',
        'interline': 18,
        'lines': [[[159, 1845.5 + i * 18], [2399, 1845.5 + i * 18]] for i in range(5)],
    }


def fixture(target_pitch='F#4'):
    score = stream.Score()
    part = stream.Part()
    score.append(part)
    records = []
    symbols = {}
    for number in range(1, 20):
        m = stream.Measure(number=number)
        if number >= 18:
            n = note.Note(target_pitch) if number == 18 else note.Rest()
            n.quarterLength = 4
            if n.isRest:
                n.fullMeasure = True
            m.append(n)
        part.append(m)
    for number, x, kind in [(18, 1405.5, 'NOTE'), (19, 2126.5, 'REST')]:
        e = {
            'id': f'e{number}',
            'symbol_id': f's{number}',
            'kind': kind,
            'duration': '4',
            'source_bbox': [x - 17, 1889, x + 17, 1909],
            'physical_source_center': [x, 1899],
            'pitch': 'G4' if kind == 'NOTE' else None,
            'stem_direction': None,
            'stem_ids': [],
            'articulations': [],
            'expressions': [],
            'beams': [],
        }
        records.append({'printed_measure': number, 'events': [e]})
        symbols[e['symbol_id']] = {
            'shape': 'WHOLE_NOTE' if kind == 'NOTE' else 'WHOLE_REST',
            'system': 'five',
            'kind': 'head' if kind == 'NOTE' else 'rest',
        }
    return (
        {'staff': staff(), 'measures': records, 'ambiguous_SIG_objects': []},
        score,
        {'symbols': symbols, 'relations': []},
    )


@pytest.mark.parametrize('name', ['F#4', 'E4', 'A3', 'G3'])
@pytest.mark.parametrize('x', [1405, 1405.5, 1405.25])
def test_calibrated_whole_pitch_coordinate_hole_and_anchor(name, x):
    p, r = calibrated_whole_head((2520, 2110), staff(), x, name)
    assert r['transparent_hole_pixels'] > 0
    assert max(map(abs, r['measured_residual'])) <= 0.5
    assert np.asarray(p).any()
    assert p.tobytes() == calibrated_whole_head((2520, 2110), staff(), x, name)[0].tobytes()


def test_existing_tie_wrapper_remains_fail_closed_and_identical():
    with pytest.raises(ValueError, match='Unsupported endpoint'):
        whole_head((2520, 2110), staff(), 1405.5, 'F#4')
    for name in ['A3', 'G3']:
        assert (
            whole_head((2520, 2110), staff(), 1405.5, name)[0].tobytes()
            == calibrated_whole_head((2520, 2110), staff(), 1405.5, name)[0].tobytes()
        )


def test_new_whole_note_and_rest_use_existing_glyph_contracts():
    inv, s, g = fixture()
    parts, r = render_music(
        inv,
        s,
        'A',
        g,
        size=(2520, 2110),
        viewport=(130, 1740, 2430, 2050),
        whole_note_renderer=calibrated_whole_head,
    )
    assert (
        parts['e18:head'].tobytes()
        == calibrated_whole_head((2520, 2110), staff(), 1405.5, 'F#4')[0].tobytes()
    )
    assert parts['e19:rest'].tobytes() == whole_rest((2520, 2110), staff(), 2126.5)[0].tobytes()
    assert not r['clipping'] and not r['unexpected_intersections']
    assert r['owner_verified_new_events'] == 0 and r['displayed_note_rest_cores'] == 2
    assert r['third_lyric_music_contacts'].startswith('NOT_EVALUABLE')
    assert 'e18:stem' not in parts


@pytest.mark.parametrize('bad', ['rest-shape', 'full-measure', 'whole-shape', 'stem'])
def test_missing_lineage_blocks(bad):
    inv, s, g = fixture()
    if bad == 'rest-shape':
        g['symbols']['s19']['shape'] = 'UNKNOWN'
    if bad == 'full-measure':
        list(s.parts[0].getElementsByClass(stream.Measure))[-1].notesAndRests[0].fullMeasure = False
    if bad == 'whole-shape':
        g['symbols']['s18']['shape'] = 'UNKNOWN'
    if bad == 'stem':
        inv['measures'][0]['events'][0]['stem_ids'] = ['unrelated']
    with pytest.raises(ValueError):
        render_music(
            inv,
            s,
            'A',
            g,
            size=(2520, 2110),
            viewport=(130, 1740, 2430, 2050),
            whole_note_renderer=calibrated_whole_head,
        )


def test_inherited_four_system_viewport_reports_clipping():
    inv, s, g = fixture()
    _, r = render_music(
        inv,
        s,
        'A',
        g,
        size=(2520, 2110),
        viewport=(130, 310, 2430, 1800),
        whole_note_renderer=calibrated_whole_head,
    )
    assert set(r['clipping']) == {'e18:head', 'e19:rest'}


def test_source_ending_preserves_open_geometry_and_numeral():
    g = {
        'symbols': {
            'sheet#1:5195': {
                'source_xml': '<ending><left-leg><p1 x="276" y="1758"/><p2 x="276" y="1805"/></left-leg><line><p1 x="279" y="1760"/><p2 x="1358" y="1760"/></line></ending>'
            },
            'sheet#1:4269': {
                'source_xml': '<word value="2."/>',
                'geometry': {'bbox': [287, 1773, 317, 1801]},
            },
        }
    }
    parts, r = second_ending((2520, 2110), g)
    assert r['path'][-1] == (1358, 1760)
    assert set(parts) == {'ending2', 'ending2-number'}
    bad = copy.deepcopy(g)
    bad['symbols']['sheet#1:4269']['source_xml'] = '<word value="1."/>'
    with pytest.raises(ValueError):
        second_ending((2520, 2110), bad)


def test_no_mirrored_lower_lyrics_or_chord_insertion():
    assert all(not v['lower'] for v in CANDIDATES.values())
    assert CANDIDATES[17]['chord'] == 'Bb/D' and CANDIDATES[19]['chord'] is None
    image = Image.new('RGB', (2300, 310), 'white')
    annotated = panel(image, 'OMR_PROVISIONAL')
    assert annotated.crop((0, 130, 2300, 440)).tobytes() == image.tobytes()


def test_event_count_mismatch_never_silently_truncates_zip():
    inv, s, g = fixture()
    inv['measures'][0]['events'] = []
    with pytest.raises(ValueError, match='event-count mismatch'):
        render_music(inv, s, 'A', g, size=(2520, 2110), whole_note_renderer=calibrated_whole_head)
