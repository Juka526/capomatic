"""Synthetic composition of validated whole/half/quarter glyphs at a new page region."""

import copy

import pytest
from music21 import note, stream
from PIL import Image, ImageFont

from scripts.research.gt15_third_system import render_music
from scripts.research.gt13a6_tie_rendering import whole_head
from scripts.research.gt04_visual import REST
from scripts.research.gt05_raster_anchor import glyph
from scripts.research.gt13a4_header import font_units
from scripts.research.gt15_notation import font_contract


def fixture():
    score = stream.Score()
    part = stream.Part()
    score.append(part)
    records = []
    symbols = {}
    for number, (duration, pitch, bbox) in enumerate(
        [
            (1, None, [303, 1502, 325, 1559]),
            (2, None, [400, 1522, 422, 1533]),
            (4, 'A3', [500, 1584, 534, 1604]),
        ],
        1,
    ):
        m = stream.Measure(number=number)
        n = note.Note(pitch) if pitch else note.Rest()
        n.quarterLength = duration
        m.append(n)
        part.append(m)
        sid = f's{number}'
        e = {
            'id': f'e{number}',
            'symbol_id': sid,
            'source_bbox': bbox,
            'physical_source_center': [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2],
            'kind': 'NOTE' if pitch else 'REST',
            'duration': str(duration),
            'pitch': 'B-3' if pitch else None,
            'stem_direction': None,
            'stem_ids': [],
            'articulations': [],
            'expressions': [],
            'beams': [],
        }
        records.append({'printed_measure': number, 'events': [e]})
        symbols[sid] = {
            'system': 'four',
            'kind': 'head' if pitch else 'rest',
            'shape': 'WHOLE_NOTE' if pitch else 'REST',
        }
    staff = {
        'system': 'four',
        'interline': 18,
        'lines': [[[159, 1495.5 + 18 * j], [2399, 1495.5 + 18 * j]] for j in range(5)],
    }
    return (
        {'staff': staff, 'measures': records, 'ambiguous_SIG_objects': []},
        score,
        {'symbols': symbols, 'relations': []},
    )


def test_whole_and_rest_components_reuse_existing_contracts_exactly():
    inv, score, g = fixture()
    size = (2520, 1800)
    parts, r = render_music(inv, score, 'A', g, size=size, viewport=(130, 1395, 2430, 1740))
    whole, _ = whole_head(size, inv['staff'], 517, 'A3')
    assert parts['e3:head'].tobytes() == whole.tobytes()
    tt, font, scale = font_contract(18)
    rest, _ = glyph(size, font, REST, (314, 1530.5), font_units(tt, REST), scale)
    assert parts['e1:rest'].tobytes() == rest.tobytes()
    assert 'e3:stem' not in parts and 'e3:ledger' in parts
    assert r['recognized_events'] == 3 and r['displayed_note_rest_cores'] == 3
    assert r['max_head_residual'] <= 0.5 and not r['clipping'] and not r['unexpected_intersections']
    assert r['owner_verified_new_events'] == 0
    assert r['third_lyric_music_contacts'].startswith('NOT_EVALUABLE')


def test_new_size_and_viewport_do_not_change_music_positions():
    inv, score, g = fixture()
    a, ra = render_music(inv, score, 'A', g, size=(2520, 1800), viewport=(130, 1395, 2430, 1740))
    b, rb = render_music(inv, score, 'A', g, size=(2520, 1900), viewport=(130, 1395, 2430, 1740))
    for name in a:
        assert a[name].getbbox() == b[name].getbbox()
        assert a[name].tobytes() == b[name].crop((0, 0, 2520, 1800)).tobytes()
    assert ra == rb


def test_viewport_clipping_is_reported_not_hidden():
    inv, score, g = fixture()
    _, r = render_music(inv, score, 'A', g, size=(2520, 1800), viewport=(130, 1395, 2430, 1580))
    assert 'e3:head' in r['clipping']


@pytest.mark.parametrize('bad', ['stem', 'shape', 'pitch'])
def test_whole_note_fails_closed_on_unsupported_evidence(bad):
    inv, score, g = fixture()
    if bad == 'stem':
        inv['measures'][2]['events'][0]['stem_ids'] = ['unrelated']
    elif bad == 'shape':
        g['symbols']['s3']['shape'] = 'UNKNOWN'
    else:
        list(score.parts[0].getElementsByClass(stream.Measure))[2].notes[
            0
        ].pitch.nameWithOctave = 'C4'
    with pytest.raises(ValueError):
        render_music(inv, score, 'A', g, size=(2520, 1800), viewport=(130, 1395, 2430, 1740))


def test_repeat_signature_detects_changed_backward_repeat_and_ending_scope():
    from music21 import bar, spanner
    from scripts.research.gt16_fourth_system import repeat_signature

    score = stream.Score()
    part = stream.Part()
    score.append(part)
    for j in range(1, 4):
        part.append(stream.Measure(number=j))
    ms = list(part.getElementsByClass(stream.Measure))
    ms[0].leftBarline = bar.Repeat(direction='start')
    ms[1].rightBarline = bar.Repeat(direction='end')
    part.insert(0, spanner.RepeatBracket(ms[1], number=1))
    old = repeat_signature(score)
    altered = copy.deepcopy(score)
    list(altered.parts[0].getElementsByClass(stream.Measure))[1].rightBarline = bar.Barline(
        'regular'
    )
    assert repeat_signature(altered) != old
    altered = copy.deepcopy(score)
    list(altered.recurse().getElementsByClass(spanner.RepeatBracket))[0].number = 2
    assert repeat_signature(altered) != old
    assert repeat_signature(copy.deepcopy(score)) == old
