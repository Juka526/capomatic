"""Controls for owner interpretation, exact bounded additions and no duplicate lyrics."""

import copy
import json

import numpy as np
import pytest
from music21 import note, stream, tie
from PIL import Image

from scripts.research import gt14b_lyric_extenders as gt


@pytest.mark.parametrize('bbox', [[5, 10, 42, 16], [50, 25, 88, 31]])
@pytest.mark.parametrize('dy', [0, 8])
def test_extender_retains_source_x_width_row_phase_and_determinism(bbox, dy):
    a = gt.extender((100, 100), bbox, dy, (0, 0, 100, 100))
    b = gt.extender((100, 100), bbox, dy, (0, 0, 100, 100))
    assert a.tobytes() == b.tobytes()
    x0, y0, x1, y1 = a.getbbox()
    assert [x0, x1] == [bbox[0], bbox[2]] and y1 - y0 == 2
    assert (y0 + y1 - 1) / 2 == (bbox[1] + bbox[3] - 1) / 2 + dy
    assert np.count_nonzero(np.asarray(a)) == (bbox[2] - bbox[0]) * 2


@pytest.mark.parametrize(
    'bbox,dy', [([0, 99, 5, 105], 0), ([0, 0, 5, 6], -1), ([5, 5, 5, 9], 0), ([0.5, 1, 4, 6], 0)]
)
def test_clipping_empty_and_noninteger_geometry_rejected(bbox, dy):
    with pytest.raises(ValueError):
        gt.extender((100, 100), bbox, dy, (0, 0, 100, 100))


def test_exact_alpha_contacts_and_unchanged_pixels_are_distinct():
    line = gt.extender((100, 100), [20, 40, 40, 46], 0, (0, 0, 100, 100))
    base = Image.new('L', (100, 100))
    base.putpixel((20, 42), 1)  # Even very faint alpha must count.
    lyric = Image.new('L', base.size)
    lyric.putpixel((70, 80), 255)
    r = gt.safety({'line': line}, base, {'lyric': lyric})
    assert r['extender_to_music_contacts'] == 1
    assert r['existing_alpha_preserved']
    r = gt.safety({'line': line}, base, {'lyric': base})
    assert r['extender_to_lyric_contacts'] == 1
    assert r['lyric_lyric_and_extender_pairs'][0]['pixels'] == 1


def source_fixture():
    s = stream.Score()
    p = stream.Part()
    s.append(p)
    for i in range(1, 8):
        p.append(stream.Measure(number=i))
    ms = list(p.getElementsByClass(stream.Measure))
    for index, onset, kind in [(5, 2.75, 'start'), (5, 3, 'stop')]:
        n = note.Note('C4', quarterLength=0.25)
        n.tie = tie.Tie(kind)
        if kind == 'start':
            n.addLyric('원', lyricNumber=1)
        ms[index].insert(onset, n)
    n = note.Note('B-3', quarterLength=0.5)
    n.addLyric('하', lyricNumber=1)
    ms[5].insert(3.25, n)
    return s


def test_related_hold_has_no_new_syllable_and_original_sig_is_retained():
    r = gt.read(gt.PROTOCOL)['interpretations'][1]
    s = source_fixture()
    g = {
        'symbols': {
            r['symbol_id']: {'shape': 'TENUTO', 'geometry': {'bbox': r['source_bbox']}},
            r['tie_relation']: {'id': r['tie_relation']},
        },
        'relations': [{'source': 'chord', 'target': r['symbol_id'], 'kind': 'chord-articulation'}],
    }
    before = copy.deepcopy(g)
    result = gt.context(r, g, s)
    assert result['new_syllables'] == 0 and result['held_note_pitch'] == 'C4'
    assert result['original_relations'] == g['relations'] and g == before
    assert result['interpretation'] == 'LYRIC_EXTENDER'
    gt.event(s, 6, '3').pitch.name = 'D'
    with pytest.raises(ValueError, match='endpoints differ'):
        gt.context(r, g, s)


def test_korean_stroke_reuses_existing_ha_not_an_extra_music_or_lyric_glyph():
    r = gt.read(gt.PROTOCOL)['interpretations'][2]
    s = source_fixture()
    g = {
        'symbols': {
            r['symbol_id']: {'shape': 'FERMATA_BELOW', 'geometry': {'bbox': r['source_bbox']}}
        },
        'relations': [{'source': r['symbol_id'], 'target': 'chord', 'kind': 'fermata-chord'}],
    }
    result = gt.context(r, g, s)
    assert result['new_glyph'] is False
    assert gt.event(s, 6, '13/4').lyrics[0].text == '하'
    gt.event(s, 6, '13/4').lyrics[0].text = 'X'
    with pytest.raises(ValueError, match='하 missing'):
        gt.context(r, g, s)


def test_binding_fails_closed_on_changed_approval_or_false_independence(tmp_path):
    (tmp_path / 'approval.txt').write_text('actual message')
    p = tmp_path / 'binding.json'
    data = {
        'classification': 'OWNER_VERIFIED_SOURCE',
        'independent_ground_truth': False,
        'approval_file': 'approval.txt',
        'approval_sha256': gt.sha(tmp_path / 'approval.txt'),
        'files': {},
    }
    p.write_text(json.dumps(data))
    assert gt.verify_binding(p) == data
    data['independent_ground_truth'] = True
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='Not independent'):
        gt.verify_binding(p)
    data['independent_ground_truth'] = False
    p.write_text(json.dumps(data))
    (tmp_path / 'approval.txt').write_text('changed')
    with pytest.raises(ValueError, match='Approval changed'):
        gt.verify_binding(p)


def test_fixed_scope_three_distinct_lines_and_four_original_objects():
    p = gt.read(gt.PROTOCOL)
    rows = p['interpretations']
    assert len(rows) == 4
    ext = [r for r in rows if r['interpretation'] == 'LYRIC_EXTENDER']
    assert len(ext) == 3 and len({r['symbol_id'] for r in ext}) == 3
    assert [(r['measure'], r['row']) for r in ext] == [(5, 2), (6, 1), (7, 1)]
    assert p['stroke_width_px'] == 2
