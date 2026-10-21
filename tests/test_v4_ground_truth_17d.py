"""Synthetic exact-span mutation controls. No recognition or real score dependency."""

import copy
import xml.etree.ElementTree as ET

import pytest
from music21 import note, spanner, stream, tie

from scripts.research.gt17d_owner_correction import (
    remove_exact_slur,
    tree_fingerprint,
    relationship_inventory,
)


def fixture():
    root = ET.fromstring(
        '''<score-partwise><part id="p"><measure number="21">
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><notations><tied type="stop"/><slur type="start" number="1" placement="below"/></notations><lyric number="1"><text>을</text></lyric></note>
      <note><pitch><step>B</step><alter>-1</alter><octave>4</octave></pitch><duration>2</duration><notations><slur type="stop" number="1"/></notations><lyric number="1"><text>되</text></lyric></note>
      </measure><measure number="31"><note><notations><slur number="2" type="start"/></notations></note><note><notations><slur number="2" type="stop"/></notations></note></measure></part></score-partwise>'''
    )
    return root, {'part_id': 'p', 'measure_xml_number': '21', 'note_indices': [0, 1]}


def test_only_exact_slur_pair_removed_and_original_unmodified():
    root, mapping = fixture()
    original = ET.tostring(root)
    revised, record = remove_exact_slur(root, mapping)
    assert ET.tostring(root) == original
    assert record['removed_relationships'] == 1 and record['removed_notation_nodes'] == 2
    assert len(revised.findall('.//slur')) == 2
    assert [s.get('number') for s in revised.findall('.//slur')] == ['2', '2']
    assert revised.find('.//tied').get('type') == 'stop'
    assert [t.text for t in revised.findall('.//lyric/text')] == ['을', '되']
    expected = copy.deepcopy(root)
    for n in expected.findall('./part/measure')[0].findall('note'):
        p = n.find('notations')
        for slur in p.findall('slur'):
            p.remove(slur)
    assert tree_fingerprint(expected) == tree_fingerprint(revised)


@pytest.mark.parametrize(
    'bad',
    ['wrong-part', 'wrong-measure', 'wrong-end', 'wrong-number', 'duplicate-pair', 'no-start'],
)
def test_nonunique_or_wrong_mapping_fails_before_mutation(bad):
    root, m = fixture()
    if bad == 'wrong-part':
        m['part_id'] = 'other'
    if bad == 'wrong-measure':
        m['measure_xml_number'] = '22'
    if bad == 'wrong-end':
        root.findall('.//slur')[1].set('type', 'start')
    if bad == 'wrong-number':
        root.findall('.//slur')[1].set('number', '9')
    if bad == 'duplicate-pair':
        for n, role in zip(root.findall('./part/measure')[0].findall('note'), ['start', 'stop']):
            ET.SubElement(n.find('notations'), 'slur', {'type': role, 'number': '5'})
    if bad == 'no-start':
        root.findall('.//slur')[0].set('type', 'continue')
    before = ET.tostring(root)
    with pytest.raises(ValueError):
        remove_exact_slur(root, m)
    assert ET.tostring(root) == before


def test_relationship_signature_tracks_all_ties_and_endpoint_order():
    score = stream.Score()
    part = stream.Part()
    score.append(part)
    m = stream.Measure(number=21)
    part.append(m)
    a, b = note.Note('C5'), note.Note('B-4')
    m.append([a, b])
    a.tie = tie.Tie('stop')
    score.insert(0, spanner.Slur(a, b))
    sig = relationship_inventory(score)
    assert sig['ties'][0][1] == 'stop'
    assert sig['slurs'][0][0] == ((0, 1, '0'), (0, 1, '1'))


def test_source_stroke_overlap_is_link_only_not_a_duplicate_independent_question():
    from scripts.research.gt17d_owner_correction import stroke_overlap_links

    raw = [
        {
            'id': 'raw',
            'proposed_interpretation': 'LYRIC_CONTINUATION_STROKE_CANDIDATE',
            'source_bbox': [10, 10, 30, 14],
        }
    ]
    marks = [{'id': 'mark', 'source_dark_bbox': [11, 10, 29, 14]}]
    result = stroke_overlap_links(raw, marks)
    assert result['unambiguous_region_links'] == [
        {'raw_sig_case': 'raw', 'continuation_case': 'mark'}
    ]
    assert result['classification_or_answers_propagated'] is False


def test_ambiguous_overlap_does_not_merge_two_questions():
    from scripts.research.gt17d_owner_correction import stroke_overlap_links

    raw = [
        {
            'id': 'raw',
            'proposed_interpretation': 'LYRIC_CONTINUATION_STROKE_CANDIDATE',
            'source_bbox': [10, 10, 30, 14],
        }
    ]
    marks = [{'id': x, 'source_dark_bbox': [11, 10, 29, 14]} for x in ['a', 'b']]
    result = stroke_overlap_links(raw, marks)
    assert not result['unambiguous_region_links'] and len(result['ambiguous_region_links']) == 2


@pytest.mark.parametrize(
    'bbox,kind',
    [
        ([100, 100, 120, 104], 'LYRIC_CONTINUATION_STROKE_CANDIDATE'),
        ([10, 10, 30, 14], 'KOREAN_LYRIC_GLYPH_STROKE_CANDIDATE'),
    ],
)
def test_neighbor_or_glyph_is_not_silently_merged_into_extender(bbox, kind):
    from scripts.research.gt17d_owner_correction import stroke_overlap_links

    result = stroke_overlap_links(
        [{'id': 'raw', 'proposed_interpretation': kind, 'source_bbox': bbox}],
        [{'id': 'm', 'source_dark_bbox': [11, 10, 29, 14]}],
    )
    assert not result['unambiguous_region_links']
