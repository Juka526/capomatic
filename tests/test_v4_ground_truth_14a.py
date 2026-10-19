"""Synthetic controls for newly supported notation and narrowly scoped approval."""

import copy
import json
from fractions import Fraction

import numpy as np
import pytest
from music21 import stream, note, tie, bar, spanner, harmony

from scripts.research.gt14a_notation import whole_rest, ending_repeat
from scripts.research import gt14a_confirmed_context as gt
from scripts.research.gt13a5_lyric_layout import contacts
from scripts.research.gt11_complete_measure import FONT, events_of
from scripts.research.paired_ground_truth_01 import sha


def staff(inter, phase):
    return {
        'interline': inter,
        'lines': [
            [[0, 200 + i * inter + phase], [1200, 200 + i * inter + phase + 0.4]] for i in range(5)
        ],
    }


@pytest.mark.parametrize('inter', [14, 18, 24])
@pytest.mark.parametrize('phase', [0, 0.25, 0.5, 0.75])
def test_whole_rest_hangs_from_fourth_line_and_is_deterministic(inter, phase):
    if not FONT.exists():
        pytest.skip('Pinned FreeSerif unavailable')
    st = staff(inter, phase)
    a, r = whole_rest((1200, 600), st, 400 + phase)
    b, rr = whole_rest((1200, 600), st, 400 + phase)
    assert a.tobytes() == b.tobytes() and r == rr
    assert max(map(abs, r['semantic_anchor_residual'])) <= 0.5
    line = r['requested_semantic_anchor'][1]
    pix = np.asarray(a)
    assert pix[round(line)].any()
    assert np.any(pix[round(line) + 2 :])
    assert a.getbbox()[1] >= line - 3
    assert r['staff_line_index'] == 1 and r['duration'] == '4'


def structural_fixture():
    e = {
        'id': 'ending',
        'source_xml': '<ending><left-leg><p1 x="800" y="100"/><p2 x="800" y="147"/></left-leg><line><p1 x="802" y="102"/><p2 x="1098" y="102"/></line><right-leg><p1 x="1100" y="100"/><p2 x="1100" y="147"/></right-leg></ending>',
    }
    bars = [
        {'id': 'thin', 'shape': 'THIN_BARLINE', 'geometry': {'bbox': [1095, 200, 1098, 275]}},
        {'id': 'thick', 'shape': 'THICK_BARLINE', 'geometry': {'bbox': [1112, 200, 1122, 275]}},
    ]
    dots = [
        {'id': 'dot1', 'geometry': {'bbox': [1070, 223, 1077, 231]}},
        {'id': 'dot2', 'geometry': {'bbox': [1070, 241, 1077, 249]}},
    ]
    return e, bars, dots


def test_connected_ending_one_and_correct_backward_repeat():
    e, b, d = structural_fixture()
    before = copy.deepcopy([e, b, d])
    p, r = ending_repeat((1200, 600), e, b, d, (812, 114))
    again, rr = ending_repeat((1200, 600), e, b, d, (812, 114))
    assert len(p) == 6 and r['ending_number'] == '1' and r['repeat_direction'] == 'end'
    assert all(p[n].tobytes() == again[n].tobytes() for n in p) and r == rr
    assert contacts(p) == [] and [e, b, d] == before
    import cv2

    count, _ = cv2.connectedComponents((np.asarray(p['ending1-bracket']) > 0).astype('uint8'))
    assert count == 2


@pytest.mark.parametrize('failure', ['forward', 'missing-dot', 'clipping', 'missing-bracket'])
def test_invalid_repeat_or_bracket_is_not_silently_rendered(failure):
    e, b, d = structural_fixture()
    size = (1200, 600)
    if failure == 'forward':
        d[0]['geometry']['bbox'] = [1130, 223, 1137, 231]
    if failure == 'missing-dot':
        d.pop()
    if failure == 'clipping':
        size = (1100, 600)
    if failure == 'missing-bracket':
        e['source_xml'] = '<ending/>'
    with pytest.raises(ValueError):
        ending_repeat(size, e, b, d, (812, 114))


def score_fixture():
    s = stream.Score()
    p = stream.Part()
    s.append(p)
    for i in range(1, 9):
        p.append(stream.Measure(number=i))
    mm = list(p.getElementsByClass(stream.Measure))
    m = mm[5]
    durations = [1, 0.5, 0.25, 0.25, 0.5, 0.25, 0.25, 0.25, 0.5, 0.25]
    names = [None, None, 'B-3', 'C4', 'D4', 'C4', 'C4', 'C4', 'B-3', 'B-3']
    for j, (name, duration) in enumerate(zip(names, durations)):
        n = note.Note(name, quarterLength=duration) if name else note.Rest(quarterLength=duration)
        if j in [6, 7]:
            n.tie = tie.Tie('start' if j == 6 else 'stop')
        m.append(n)
    m.insert(0, gt.chord_symbol_from_text('Bb/D'))
    mm[7].rightBarline = bar.Repeat(direction='end')
    p.insert(0, spanner.RepeatBracket(mm[7], number='1'))
    return s


def test_exact_lyric_associations_no_new_tied_token_or_ambiguous_extender():
    source = score_fixture()
    original = [gt.event_signature(m) for m in source.parts[0].getElementsByClass(stream.Measure)]
    s = gt.augment(source)
    ms = list(s.parts[0].getElementsByClass(stream.Measure))
    m = ms[5]
    lyric_notes = [n for n in events_of(m) if n.lyrics]
    assert [str(Fraction(n.getOffsetInHierarchy(m))) for n in lyric_notes] == gt.ONSETS
    assert [[l.text for l in n.lyrics] for n in lyric_notes] == list(map(list, zip(*gt.LYRICS)))
    assert not next(n for n in events_of(m) if n.offset == 3).lyrics
    assert not events_of(source.parts[0].getElementsByClass(stream.Measure)[5])[2].lyrics
    assert [gt.event_signature(m) for m in ms] == original
    assert [
        gt.chord_text(list(ms[i].getElementsByClass(harmony.ChordSymbol))[0]) for i in (4, 5, 6)
    ] == ['Gm', 'Bb/D', 'Eb']
    assert not list(ms[7].getElementsByClass(harmony.ChordSymbol))


def test_conflicting_existing_chord_or_missing_repeat_fails_closed():
    source = score_fixture()
    source.parts[0].getElementsByClass(stream.Measure)[7].rightBarline = None
    with pytest.raises((ValueError, AttributeError)):
        gt.augment(source)
    source = score_fixture()
    source.parts[0].getElementsByClass(stream.Measure)[4].insert(0, gt.chord_symbol_from_text('C'))
    with pytest.raises(ValueError, match='differs'):
        gt.augment(source)


def test_approval_binding_rejects_exclusion_promotion(tmp_path, monkeypatch):
    p = tmp_path / 'binding.json'
    p.write_text(
        json.dumps(
            {
                'classification': 'OWNER_VERIFIED_SOURCE',
                'independent_ground_truth': False,
                'excluded_objects': [],
            }
        )
    )
    with pytest.raises(ValueError, match='exclusions'):
        gt.owner_binding(p, tmp_path)
    p.write_text(
        json.dumps(
            {
                'classification': 'ASSISTANT_VISUAL_REVIEW',
                'independent_ground_truth': False,
                'excluded_objects': gt.EXCLUDED,
            }
        )
    )
    with pytest.raises(ValueError, match='classification'):
        gt.owner_binding(p, tmp_path)
