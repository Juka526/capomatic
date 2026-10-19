"""Synthetic-only tie/semantic controls. No real owner submission is fabricated."""

import copy
import xml.etree.ElementTree as ET

import numpy as np
import pytest
from music21 import stream, note, tie
from PIL import Image

from scripts.research.gt13a6_cross_system_tie import render_segments, require_owner_confirmation
from scripts.research.gt13a6_tie_review import raw_evidence, endpoint_pair


def specs():
    return [
        {
            'role': 'OUTGOING',
            'source_curve': [[180, 70], [190, 80], [210, 80], [220, 70]],
            'dy': 0,
            'head_anchor': [180, 67],
            'attachment_offset': [0, 3],
            'system_bbox': [0, 0, 250, 110],
        },
        {
            'role': 'INCOMING',
            'source_curve': [[20, 180], [30, 190], [50, 190], [60, 180]],
            'dy': 0,
            'head_anchor': [60, 177],
            'attachment_offset': [0, 3],
            'system_bbox': [0, 140, 250, 240],
        },
    ]


@pytest.mark.parametrize('dy', [0, 0.25, 9, -9])
def test_two_separate_deterministic_segments_preserve_attachments(dy):
    a, b = specs()
    for s in (a, b):
        s['dy'] = dy
        s['head_anchor'][1] += dy
    before = copy.deepcopy([a, b])
    masks, r = render_segments((250, 250), a, b)
    again, rr = render_segments((250, 250), a, b)
    assert [a, b] == before and rr == r
    assert all(masks[k].tobytes() == again[k].tobytes() for k in masks)
    assert all(not m.crop((0, 110, 250, 140)).getbbox() for m in masks.values())
    assert all(max(map(abs, s['attachment_residual'])) <= 0.5 for s in r['segments'])
    assert r['gap_ink_pixels'] == 0


@pytest.mark.parametrize(
    'status',
    [
        'PENDING_OWNER_RESPONSE',
        'OWNER_UNCERTAIN',
        'OWNER_REJECTED',
        'OMR_SUPPORTED_CANDIDATE_PENDING_OWNER',
        None,
    ],
)
def test_no_implicit_owner_confirmation(status):
    with pytest.raises(ValueError, match='explicit owner'):
        require_owner_confirmation(status)


def test_collision_clipping_attachment_and_roles_fail_closed():
    a, b = specs()
    masks, _ = render_segments((250, 250), a, b)
    with pytest.raises(ValueError, match='collision'):
        render_segments((250, 250), a, b, masks['OUTGOING'])
    for change, match in [
        ('anchor', 'attachment'),
        ('clip', 'clipping'),
        ('role', 'roles'),
        ('above', 'below'),
        ('gap', 'separated'),
    ]:
        a, b = specs()
        if change == 'anchor':
            a['head_anchor'][0] += 1
        if change == 'clip':
            a['system_bbox'][2] = 220
        if change == 'role':
            b['role'] = 'OUTGOING'
        if change == 'above':
            a['attachment_offset'][1] = -3
        if change == 'gap':
            b['system_bbox'][1] = 100
        with pytest.raises(ValueError, match=match):
            render_segments((250, 250), a, b)


def fixture_xml():
    root = ET.Element('sheet')
    for ident, other, attr, head, side in [
        ('4818', '4798', 'right-extension', '1852', 'LEFT'),
        ('4798', '4818', 'left-extension', '1923', 'RIGHT'),
    ]:
        s = ET.SubElement(root, 'slur', {'id': ident, attr: other, 'tie': 'true', 'above': 'false'})
        ET.SubElement(s, 'curve', {'x1': '1'})
        ET.SubElement(root, 'head', {'id': head})
        r = ET.SubElement(root, 'relation', {'source': ident, 'target': head})
        ET.SubElement(r, 'slur-head', {'side': side})
    return root


def test_raw_reciprocal_and_endpoint_relations_required():
    root = fixture_xml()
    assert len(raw_evidence(ET.tostring(root))) == 2
    root.find('slur').set('right-extension', '999')
    with pytest.raises(ValueError, match='Nonreciprocal'):
        raw_evidence(ET.tostring(root))
    root = fixture_xml()
    root.find('relation/slur-head').set('side', 'RIGHT')
    with pytest.raises(ValueError, match='head relation'):
        raw_evidence(ET.tostring(root))


def score():
    s = stream.Score()
    p = stream.Part()
    s.append(p)
    for i in range(5):
        m = stream.Measure(number=i + 1)
        p.append(m)
        if i in (3, 4):
            n = note.Note('B-3', quarterLength=0.25 if i == 3 else 4)
            n.tie = tie.Tie('start' if i == 3 else 'stop')
            m.insert(3.75 if i == 3 else 0, n)
    return s


def test_semantic_endpoint_identity_duration_and_role():
    s = score()
    e = endpoint_pair(s, 'B-3')
    assert e[0]['onset'] == '15/4' and e[1]['duration'] == '4'
    for mutation in ('pitch', 'duration', 'role'):
        other = copy.deepcopy(s)
        n = list(other.parts[0].getElementsByClass(stream.Measure))[4].notes[0]
        if mutation == 'pitch':
            n.pitch.name = 'C'
        if mutation == 'duration':
            n.quarterLength = 2
        if mutation == 'role':
            n.tie = tie.Tie('start')
        with pytest.raises(ValueError, match='mismatch'):
            endpoint_pair(other, 'B-3')
