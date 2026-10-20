"""Synthetic provenance/layout/beam controls, no OMR execution or human labels."""

import copy
from pathlib import Path

import numpy as np
import pytest
from music21 import note, stream
from PIL import Image, ImageDraw
import subprocess, json, hashlib

from scripts.research.gt17b_notation import beam_groups, render, down_flag
from scripts.research.gt17b_full_score import layout_text, export_pdf, localize
from scripts.research.gt15_notation import font_contract
from scripts.research.gt13a4_header import font_units
from scripts.research.gt07_flags import FLAG
from scripts.research.gt13a2_provisional import ink_distance
from scripts.research.gt17b_source import owner_augmented


def double_beam(sign=1):
    nodes = {}
    for i in range(2):
        nodes[f's{i}'] = {
            'x': 100 + i * 50,
            'y': 150,
            'sign': sign,
            'event': {
                'duration': '1/4',
                'beams': [
                    {'number': 1, 'type': 'start' if i == 0 else 'stop'},
                    {'number': 2, 'type': 'start' if i == 0 else 'stop'},
                ],
            },
        }
    symbols = {}
    relations = []
    for j in range(2):
        y = 80 + j * 14 * sign if sign == 1 else 220 - j * 14
        symbols[f'b{j}'] = {
            'id': f'b{j}',
            'kind': 'beam',
            'geometry': {'line': [[100, y], [150, y + 3]], 'thickness': 10},
        }
        relations.extend({'source': f'b{j}', 'target': s, 'kind': 'beam-stem'} for s in nodes)
    return nodes, symbols, relations


@pytest.mark.parametrize('sign', [1, -1])
def test_bidirectional_double_beams_preserve_source_levels_slope_and_membership(sign):
    ns, sy, rs = double_beam(sign)
    specs, tips, _ = beam_groups(ns, sy, rs, 18)
    assert len(specs) == 2 and {p['level'] for p in specs} == {1, 2}
    assert set(tips) == set(ns)
    assert all(p['source_slope'] == pytest.approx(0.06) for p in specs)
    assert sign * (specs[1]['line'][0][1] - specs[0]['line'][0][1]) == pytest.approx(14)
    assert specs == beam_groups(ns, sy, rs, 18)[0]


@pytest.mark.parametrize(
    'bad', ['missing-stem', 'wrong-count', 'wrong-direction', 'wrong-separation', 'missing-level']
)
def test_beam_provenance_fails_closed(bad):
    ns, sy, rs = double_beam()
    if bad == 'missing-stem':
        del ns['s1']
    if bad == 'wrong-count':
        ns['s1']['event']['beams'].append({'number': 3})
    if bad == 'wrong-direction':
        ns['s1']['sign'] = -1
    if bad == 'wrong-separation':
        sy['b1']['geometry']['line'] = [[100, 200], [150, 203]]
    if bad == 'missing-level':
        ns['s0']['event']['beams'][1]['number'] = 3
    with pytest.raises(ValueError):
        beam_groups(ns, sy, rs, 18)


@pytest.mark.parametrize('sign', [1, -1])
def test_hook_requires_explicit_direction_and_stays_inside_primary(sign):
    ns, sy, rs = double_beam(sign)
    # Three-node primary with a single partial second-level hook on middle stem.
    ns['s2'] = copy.deepcopy(ns['s1'])
    ns['s2']['x'] = 200
    ns['s0']['event']['duration'] = '1/2'
    ns['s0']['event']['beams'] = [{'number': 1, 'type': 'start'}]
    ns['s1']['event']['beams'] = [
        {'number': 1, 'type': 'continue'},
        {'number': 2, 'type': 'partial', 'direction': 'right'},
    ]
    ns['s2']['event']['duration'] = '1/2'
    ns['s2']['event']['beams'] = [{'number': 1, 'type': 'stop'}]
    primary_y = 80 if sign == 1 else 220
    sy['b0']['geometry']['line'] = [[100, primary_y], [200, primary_y]]
    sy['b1']['kind'] = 'beam-hook'
    sy['b1']['geometry']['line'] = [[150, primary_y + 14 * sign], [175, primary_y + 14 * sign]]
    rs = [{'source': 'b0', 'target': s, 'kind': 'beam-stem'} for s in ns] + [
        {'source': 'b1', 'target': 's1', 'kind': 'beam-stem'}
    ]
    specs, _, _ = beam_groups(ns, sy, rs, 18)
    assert next(p for p in specs if p['kind'] == 'beam-hook')['line'][1][0] == 175
    ns['s1']['event']['beams'][1]['direction'] = None
    with pytest.raises(ValueError):
        beam_groups(ns, sy, rs, 18)


def fixture(x=200.5):
    st = {
        'system': 'six',
        'interline': 18,
        'lines': [[[50, 100 + i * 18], [700, 100 + i * 18]] for i in range(5)],
    }
    s = stream.Score()
    p = stream.Part()
    m = stream.Measure(number=1)
    s.append(p)
    p.append(m)
    n = note.Note('A4')
    n.quarterLength = 0.5
    n.stemDirection = 'down'
    m.append(n)
    e = {
        'id': 'e1',
        'symbol_id': 'h',
        'source_bbox': [x - 12, 135, x + 12, 155],
        'physical_source_center': [x, 145],
        'pitch': 'A4',
        'stem_ids': ['stem'],
        'stem_direction': 'down',
        'beams': [],
        'duration': '1/2',
        'kind': 'NOTE',
        'onset': '0',
    }
    graph = {
        'symbols': {
            'h': {'shape': 'NOTEHEAD_BLACK', 'kind': 'head', 'system': 'six'},
            'stem': {
                'kind': 'stem',
                'system': 'six',
                'geometry': {'line': [[x - 10, 145], [x - 10, 208]]},
            },
            'flag': {'kind': 'flag', 'shape': 'FLAG_1_DOWN', 'system': 'six'},
        },
        'relations': [
            {
                'kind': 'head-stem',
                'source': 'h',
                'target': 'stem',
                'attributes': [['head-side', 'LEFT']],
            },
            {'kind': 'flag-stem', 'source': 'flag', 'target': 'stem'},
        ],
        'all_symbols': {},
    }
    return {'staff': st, 'measures': [{'printed_measure': 1, 'events': [e]}]}, s, graph


@pytest.mark.parametrize('x', [200, 200.25, 200.5, 200.75])
def test_down_flag_attaches_without_touching_head_at_fractional_phases(x):
    inv, s, g = fixture(x)
    parts, metrics = render(inv, s, 'A', g, (800, 420), {'h': inv['measures'][0]['events'][0]})
    assert not metrics['unexpected_contacts'] and not metrics['missing_connections']
    assert metrics['max_head_residual'] <= 0.5
    assert float(ink_distance(parts['e1:head'])[np.asarray(parts['e1:flag']) > 0].min()) >= 8
    assert parts['e1:stem'].getbbox()[3] > 208


@pytest.mark.parametrize(
    'bad', ['stem-side', 'missing-flag', 'flag-direction', 'explicit-accidental', 'duration']
)
def test_new_single_flag_source_lineage_failure(bad):
    inv, s, g = fixture()
    if bad == 'stem-side':
        g['relations'][0]['attributes'] = [['head-side', 'RIGHT']]
    if bad == 'missing-flag':
        g['relations'] = g['relations'][:1]
    if bad == 'flag-direction':
        g['symbols']['flag']['shape'] = 'FLAG_2'
    if bad == 'explicit-accidental':
        list(s.recurse().notes)[0].pitch.name = 'A#'
    if bad == 'duration':
        inv['measures'][0]['events'][0]['duration'] = '1/4'
    with pytest.raises(ValueError):
        render(inv, s, 'A', g, (800, 420), {})


def test_whole_coupled_lyric_rows_move_minimally_without_horizontal_changes():
    music = Image.new('L', (100, 80))
    music.putpixel((30, 20), 255)
    a = Image.new('L', music.size)
    a.putpixel((30, 20), 255)
    b = Image.new('L', music.size)
    b.putpixel((30, 35), 255)
    moved, r = layout_text({'upper': a, 'lower': b}, music)
    assert r['dy'] == 2 and r['actual_contacts'] == 0
    assert moved['upper'].getbbox() == (30, 22, 31, 23)
    assert moved['lower'].getbbox() == (30, 37, 31, 38)
    assert sum(np.count_nonzero(np.asarray(p)) for p in moved.values()) == 2


def test_lyric_layout_blocks_instead_of_clipping_or_dropping_pixels():
    music = Image.new('L', (100, 80), 255)
    a = Image.new('L', music.size)
    a.putpixel((20, 70), 255)
    moved, r = layout_text({'a': a}, music)
    assert not moved and r['status'] == 'BLOCKED_NO_SAFE_LOCAL_SPACE'


def test_lossless_pdf_dimensions_image_bytes_and_visible_warning(tmp_path):
    im = Image.new('RGB', (200, 300), 'white')
    ImageDraw.Draw(im).text((8, 8), 'INCOMPLETE', fill='black')
    path = tmp_path / 'experimental.pdf'
    r = export_pdf(im, path)
    proc = subprocess.run(
        [
            '/opt/anaconda3/bin/python',
            str(Path(__file__).resolve().parents[1] / 'scripts/research/gt17b_pdf.py'),
            '--inspect',
            str(path),
        ],
        capture_output=True,
        check=True,
    )
    info = json.loads(proc.stdout)
    assert info['pages'] == 1 and info['page_size_points'] == [48.0, 72.0]
    assert info['rgb_sha256'] == hashlib.sha256(im.tobytes()).hexdigest()
    assert info['encoding'] == '/FlateDecode' and 'INCOMPLETE' in info['title']


def test_key_group_translation_is_minimal_lossless_and_does_not_move_staff_or_notes():
    from scripts.research.gt17b_full_score import key_clearance

    obstacle = Image.new('L', (100, 80))
    ImageDraw.Draw(obstacle).rectangle((70, 10, 72, 60), fill=255)
    key = Image.new('L', obstacle.size)
    ImageDraw.Draw(key).rectangle((68, 20, 73, 30), fill=255)
    moved, r = key_clearance({'sharp': key}, obstacle)
    assert r['dx'] == -5 and r['dy'] == 0 and r['actual_contacts'] == 0
    assert (
        moved['sharp'].crop(moved['sharp'].getbbox()).tobytes() == key.crop(key.getbbox()).tobytes()
    )
    with pytest.raises(ValueError):
        key_clearance({'sharp': key}, Image.new('L', obstacle.size, 255))


def test_dotted_half_requires_void_head_and_explicit_augmentation_support():
    inv, s, g = fixture()
    n = list(s.recurse().notes)[0]
    n.quarterLength = 3
    inv['measures'][0]['events'][0]['duration'] = '3'
    g['symbols']['h']['shape'] = 'NOTEHEAD_VOID'
    g['symbols'].pop('flag')
    g['relations'] = g['relations'][:1]
    g['symbols']['dot'] = {'kind': 'augmentation-dot', 'system': 'six'}
    g['relations'].append({'kind': 'augmentation', 'source': 'dot', 'target': 'h'})
    ps, r = render(inv, s, 'A', g, (800, 420), {'h': inv['measures'][0]['events'][0]})
    assert 'e1:dot' in ps and r['max_head_residual'] <= 0.5 and not r['unexpected_contacts']
    assert r['events'][0]['transparent_hole_pixels'] > 0
    g['relations'].pop()
    with pytest.raises(ValueError, match='augmentation lineage'):
        render(inv, s, 'A', g, (800, 420), {})


def test_only_explicit_equal_pitch_ties_may_cross_their_own_shared_barline():
    from scripts.research.gt17b_full_score import expected_tie_barline

    g = {
        'symbols': {
            'curve': {'kind': 'slur', 'source_xml': '<slur tie="true"/>'},
            'bar': {'kind': 'barline', 'geometry': {'bbox': [100, 0, 102, 100]}},
        },
        'relations': [
            {'kind': 'slur-head', 'source': 'curve', 'target': 'a'},
            {'kind': 'slur-head', 'source': 'curve', 'target': 'b'},
        ],
    }
    es = {
        'a': {'printed_measure': 1, 'pitch': 'C5', 'tie': 'start'},
        'b': {'printed_measure': 2, 'pitch': 'C5', 'tie': 'stop'},
    }
    sys = {'measures': [{'printed_measure': 1, 'omr_bounds': [0, 0, 101, 100]}]}
    assert expected_tie_barline('curve', 'bar', g, es, sys)
    for bad in ['pitch', 'role', 'measure', 'bar', 'not-a-tie']:
        gg = copy.deepcopy(g)
        ee = copy.deepcopy(es)
        if bad == 'pitch':
            ee['b']['pitch'] = 'D5'
        if bad == 'role':
            ee['b']['tie'] = None
        if bad == 'measure':
            ee['b']['printed_measure'] = 1
        if bad == 'bar':
            gg['symbols']['bar']['geometry']['bbox'] = [50, 0, 52, 100]
        if bad == 'not-a-tie':
            gg['symbols']['curve']['source_xml'] = '<slur/>'
        assert not expected_tie_barline('curve', 'bar', gg, ee, sys)


def test_post_freeze_candidate_semantics_is_separate_and_preserves_music():
    from scripts.research.gt17b_post_audit import candidate_semantics
    from scripts.research.gt15b_confirmed_third_system import music_signature
    from music21 import harmony

    s = stream.Score()
    p = stream.Part()
    s.append(p)
    for num in range(1, 21):
        m = stream.Measure(number=num)
        if num == 20:
            r = note.Rest()
            r.quarterLength = 1
            m.append(r)
            for pitch in ['C4', 'D4', 'E4']:
                m.append(note.Note(pitch, quarterLength=1))
        else:
            m.append(note.Rest(quarterLength=4))
        p.append(m)
    inv = {
        'chords': [{'id': 'c20', 'measure': 20, 'text': 'Bb'}],
        'lyrics': [{'measure': 20, 'onset': '1', 'text': '나', 'row': 1}],
    }
    candidate, added = candidate_semantics(s, inv)
    assert added == ['c20'] and music_signature(s) == music_signature(candidate)
    assert not list(s.recurse().getElementsByClass(harmony.ChordSymbol))
    assert len(list(candidate.recurse().getElementsByClass(harmony.ChordSymbol))) == 1
    from scripts.research.gt11_complete_measure import events_of

    last = list(candidate.parts[0].getElementsByClass(stream.Measure))[-1]
    assert next(n for n in events_of(last) if n.isNote).lyrics[0].text == '나'
    bad = copy.deepcopy(inv)
    bad['lyrics'][0]['onset'] = '1/2'
    with pytest.raises(ValueError, match='Ambiguous provisional lyric'):
        candidate_semantics(s, bad)
