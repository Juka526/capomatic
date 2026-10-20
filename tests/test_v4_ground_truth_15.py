"""Synthetic new symbol contracts; no Audiveris or score reference dependency."""

import copy

import numpy as np
import pytest
from PIL import ImageDraw

from scripts.research import gt15_notation as gt
from scripts.research.gt07_flags import flag_mask, FLAG
from scripts.research.gt13a4_header import font_units
from scripts.research.gt05_raster_anchor import glyph
from scripts.research.gt04_visual import HEAD


@pytest.mark.parametrize('phase', [0, 0.125, 0.5, 0.875])
@pytest.mark.parametrize('interline', [16, 18, 20])
def test_void_head_and_half_rest_preserve_anchor_and_hole(phase, interline):
    for rest in (False, True):
        a, r = gt.half_symbol((500, 500), interline, (200 + phase, 250 + phase), rest=rest)
        b, rr = gt.half_symbol((500, 500), interline, (200 + phase, 250 + phase), rest=rest)
        assert max(map(abs, r['anchor_residual'])) <= 0.5 and a.tobytes() == b.tobytes() and r == rr
        if not rest:
            assert r['transparent_hole_pixels'] > 0
            bbox = a.getbbox()
            x = bbox[2] - 2
            px = np.argwhere(np.asarray(a) > 0)
            y = int(np.median(px[px[:, 1] == x, 0]))
            attached = a.copy()
            ImageDraw.Draw(attached).line([(x, y), (x, y - 60)], fill=255, width=2)
            assert gt.hole_pixels(attached) > 0


def beam_fixture(n):
    nodes = {
        str(i): {
            'x': 100 + i * 60,
            'y': 250 - (i % 2) * 9,
            'event': {
                'duration': '1/2',
                'stem_direction': 'up',
                'beams': [
                    {
                        'number': 1,
                        'type': ('start' if i == 0 else 'stop' if i == n - 1 else 'continue'),
                    }
                ],
            },
        }
        for i in range(n)
    }
    return nodes, {
        'id': 'beam',
        'geometry': {'line': [[100, 120], [100 + 60 * (n - 1), 116]], 'thickness': 7},
    }


@pytest.mark.parametrize('n', [2, 4])
def test_simple_beam_preserves_source_slope_and_stem_tips(n):
    nodes, beam = beam_fixture(n)
    before = copy.deepcopy((nodes, beam))
    b, t = gt.single_beam(nodes, beam, 18)
    assert (b['line'][1][1] - b['line'][0][1]) / (
        b['line'][1][0] - b['line'][0][0]
    ) == pytest.approx(-4 / (60 * (n - 1)))
    assert set(t) == set(nodes) and (nodes, beam) == before
    for sid, y in t.items():
        assert y <= nodes[sid]['y'] - 3.5 * 18
    assert (b, t) == gt.single_beam(nodes, beam, 18)


@pytest.mark.parametrize(
    'fault', ['members', 'rhythm', 'level', 'direction', 'nonfinite', 'thickness']
)
def test_unsupported_group_fails_closed(fault):
    nodes, beam = beam_fixture(4)
    if fault == 'members':
        nodes.pop('0')
    if fault == 'rhythm':
        nodes['0']['event']['duration'] = '1/4'
    if fault == 'level':
        nodes['0']['event']['beams'].append({'number': 2, 'type': 'start'})
    if fault == 'direction':
        nodes['0']['event']['stem_direction'] = 'down'
    if fault == 'nonfinite':
        beam['geometry']['line'][1][1] = float('nan')
    if fault == 'thickness':
        beam['geometry']['thickness'] = 0
    with pytest.raises(ValueError):
        gt.single_beam(nodes, beam, 18)


@pytest.mark.parametrize('phase', [0, 0.125, 0.5, 0.875])
def test_reused_flag_has_real_stem_contact_without_head_overlap(phase):
    tt, font, scale = gt.font_contract(18)
    h, r = glyph((500, 500), font, HEAD, (200 + phase, 300 + phase), font_units(tt, HEAD), scale)
    pixels = np.argwhere(np.asarray(h) > 0)
    x = int(pixels[:, 1].max() - 1)
    y = int(np.median(pixels[pixels[:, 1] == x, 0]))
    tip = (x, 190)
    flag, meta = flag_mask((500, 500), font, tip, font_units(tt, FLAG), scale)
    stem = h.copy()
    ImageDraw.Draw(stem).line([(x, y), tip], fill=255, width=2)
    assert np.any((np.asarray(stem) > 0) & (np.asarray(flag) > 0))
    assert not np.any((np.asarray(h) > 0) & (np.asarray(flag) > 0))
    assert max(map(abs, meta['flag_attachment_residual'])) <= 0.5


def test_provisional_renderer_reuses_half_flag_beam_and_tie_contracts_together():
    from music21 import stream, note, tie
    from scripts.research.gt15_third_system import render_music

    s = stream.Score()
    p = stream.Part()
    s.append(p)
    for i in range(1, 11):
        p.append(stream.Measure(number=i))
    mm = list(p.getElementsByClass(stream.Measure))
    symbol = {}
    relations = []
    records = []
    values = [
        (9, 0, 2, None, [303, 1172, 325, 1183], None),
        (9, 2, 0.5, None, [490, 1166, 509, 1201], None),
        (9, 2.5, 0.5, 'F3', [570, 1262, 595, 1281], None),
        (9, 3, 0.5, 'F4', [649, 1198, 674, 1218], None),
        (9, 3.5, 0.5, 'F4', [729, 1198, 754, 1218], 'start'),
        (10, 0, 2, 'F4', [837, 1198, 862, 1218], 'stop'),
        (10, 2, 2, None, [1100, 1172, 1122, 1183], None),
    ]
    for i, (m, on, dur, pitch, b, role) in enumerate(values):
        n = note.Note(pitch, quarterLength=dur) if pitch else note.Rest(quarterLength=dur)
        if pitch:
            n.stemDirection = 'up'
        if role:
            n.tie = tie.Tie(role)
        if i in (3, 4):
            n.beams.fill('eighth', 'start' if i == 3 else 'stop')
        mm[m - 1].insert(on, n)
        sid = f's{i}'
        head = f'h{i}'
        e = {
            'id': f'e{i}',
            'symbol_id': head,
            'onset': str(on),
            'duration': str(gt_fraction(dur)),
            'kind': 'NOTE' if pitch else 'REST',
            'pitch': pitch,
            'source_bbox': b,
            'physical_source_center': [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2],
            'stem_direction': 'up' if pitch else None,
            'stem_ids': [sid] if pitch else [],
            'beams': [{'number': 1, 'type': 'start' if i == 3 else 'stop'}] if i in (3, 4) else [],
            'tie': role,
            'articulations': [],
            'expressions': [],
            'source_verification': 'UNVERIFIED',
        }
        records.append((m, e))
        if pitch:
            symbol[sid] = {'geometry': {'line': [[b[2] - 1, b[1] - 60], [b[2] - 1, b[3] - 1]]}}
            relations.append(
                {
                    'source': head,
                    'target': sid,
                    'kind': 'head-stem',
                    'attributes': [['head-side', 'RIGHT']],
                }
            )
    symbol['flag'] = {'shape': 'FLAG_1'}
    relations.append({'source': 'flag', 'target': 's2', 'kind': 'flag-stem', 'attributes': []})
    symbol['beam'] = {
        'id': 'beam',
        'system': 'staff3',
        'kind': 'beam',
        'geometry': {'line': [[673, 1149.5], [753, 1149.5]], 'thickness': 7},
    }
    for sid in ('s3', 's4'):
        relations.append({'source': 'beam', 'target': sid, 'kind': 'beam-stem', 'attributes': []})
    symbol['tie'] = {
        'id': 'tie',
        'system': 'staff3',
        'kind': 'slur',
        'source_xml': '<slur tie="true"/>',
        'geometry': {'curve': [[742, 1222], [775, 1239], [813, 1239], [846, 1222]]},
    }
    for head, side in [('h4', 'LEFT'), ('h5', 'RIGHT')]:
        relations.append(
            {'source': 'tie', 'target': head, 'kind': 'slur-head', 'attributes': [['side', side]]}
        )
    for v in symbol.values():
        v.setdefault('system', 'staff3')
        v.setdefault('kind', 'stem')
    inv = {
        'staff': {
            'system': 'staff3',
            'interline': 18,
            'lines': [[[159, 1145.5 + j * 18], [2399, 1145.5 + j * 18]] for j in range(5)],
        },
        'measures': [
            {'printed_measure': m, 'events': [e for number, e in records if number == m]}
            for m in (9, 10)
        ],
        'ambiguous_SIG_objects': [],
    }
    transposed = s.transpose(-1)
    parts, r = render_music(inv, transposed, 'A', {'symbols': symbol, 'relations': relations})
    assert (
        r['displayed_note_rest_cores'] == 7
        and len(r['flags']) == 1
        and len(r['ties']) == 1
        and len(r['beams']) == 1
    )
    assert (
        r['max_head_residual'] <= 0.5
        and not r['missing_connections']
        and not r['unexpected_intersections']
    )
    assert r['new_lyric_syllables_rendered'] == 0 and r['owner_verified_new_events'] == 0
    assert parts['e5:head'].getbbox() and r['third_lyric_music_contacts'].startswith(
        'NOT_EVALUABLE'
    )


def gt_fraction(value):
    from fractions import Fraction

    return Fraction(value)
