from dataclasses import replace
from fractions import Fraction

import pytest

from backend.omr_v4.matcher import match_notes, read_semantics
from backend.omr_v4.visual_graph import load_visual_graph
from omr_v4_fixtures import book, musicxml, sheet_xml


def test_match_uses_measure_staff_slot_chord_pitch(tmp_path):
    graph = load_visual_graph(book(tmp_path))
    semantic = read_semantics(musicxml(tmp_path))
    result = match_notes(semantic, graph)
    assert [n.offset for n in semantic.notes] == [Fraction(0), Fraction(1)]
    assert [n.staff_pitch for n in semantic.notes] == [3, 2]
    assert [m.head_id for m in result.notes] == ['sheet#1:1', 'sheet#1:2']
    assert result.summary()['match_rate'] == 1
    assert result.notes[0].confidence == 0.9


def test_duplicate_pitch_is_ambiguous_even_with_different_grade(tmp_path):
    xml = sheet_xml().replace(
        '</inters>',
        '''<head id="3" staff="1" pitch="3" grade="1"><bounds x="95" y="111" w="10" h="8"/></head><head-chord id="40" staff="1"/></inters>''',
    )
    # Avoid colliding with the accidental ID.
    xml = xml.replace('<head-chord id="40"', '<head-chord id="44"')
    xml = xml.replace('<head-chords>10 20</head-chords>', '<head-chords>10 20 44</head-chords>')
    xml = xml.replace(
        '</relations>', '<relation source="44" target="3"><containment/></relation></relations>'
    )
    xml = xml.replace(
        '</slots>', '<entry><key>1</key><value chord="44" status="BEGIN"/></entry></slots>'
    )
    result = match_notes(read_semantics(musicxml(tmp_path)), load_visual_graph(book(tmp_path, xml)))
    assert result.notes[0].status == 'AMBIGUOUS'
    assert result.notes[0].head_id is None and len(result.notes[0].candidate_ids) == 2
    assert result.summary()['ambiguous_count'] == 1
    assert result.summary()['unmatched_visual_count'] == 2


def test_semantic_collision_never_greedily_claims_a_head(tmp_path):
    source = read_semantics(musicxml(tmp_path))
    duplicate = replace(source.notes[0], id='duplicate', chord='duplicate-chord')
    result = match_notes(
        replace(source, notes=source.notes + (duplicate,)), load_visual_graph(book(tmp_path))
    )
    assert result.notes[0].status == result.notes[-1].status == 'AMBIGUOUS'
    assert result.notes[1].status == 'MATCHED'


@pytest.mark.parametrize(
    'change',
    ['missing-time', 'continue', 'wrong-part', 'bad-head', 'bad-staff', 'missing-measure', 'pitch'],
)
def test_missing_or_conflicting_evidence_does_not_guess(tmp_path, change):
    xml = sheet_xml()
    if change == 'missing-time':
        xml = xml.replace(' time-offset="0"', '')
    elif change == 'continue':
        xml = xml.replace('chord="10" status="BEGIN"', 'chord="10" status="CONTINUE"')
    elif change == 'wrong-part':
        xml = xml.replace('<part id="1">', '<part id="2">')
    elif change == 'bad-head':
        xml = xml.replace('x="95"', 'x="NaN"')
    elif change == 'bad-staff':
        xml = xml.replace('x="20" y="80"', 'x="20" y="NaN"')
    elif change == 'missing-measure':
        xml = xml.replace('<measure id="1">', '<measure id="9">')
    else:
        xml = xml.replace('pitch="3"', 'pitch="4"')
    result = match_notes(read_semantics(musicxml(tmp_path)), load_visual_graph(book(tmp_path, xml)))
    assert result.notes[0].status != 'MATCHED'
    assert result.notes[0].head_id is None
    assert 'sheet#1:1' in result.unmatched_visual_ids


def test_chord_members_and_backup_staff_timing(tmp_path):
    path = tmp_path / 'multi.musicxml'
    path.write_text(
        '''<score-partwise><part id="P1"><measure number="1">
      <attributes><divisions>4</divisions><staves>2</staves>
        <clef number="1"><sign>G</sign><line>2</line></clef>
        <clef number="2"><sign>F</sign><line>4</line></clef></attributes>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>4</duration><voice>1</voice><staff>1</staff></note>
      <note><chord/><pitch><step>E</step><octave>5</octave></pitch><duration>4</duration><voice>1</voice><staff>1</staff></note>
      <backup><duration>4</duration></backup>
      <note><pitch><step>D</step><octave>3</octave></pitch><duration>4</duration><voice>2</voice><staff>2</staff></note>
      </measure></part></score-partwise>'''
    )
    notes = read_semantics(path).notes
    assert [n.offset for n in notes] == [0, 0, 0]
    assert [n.staff for n in notes] == [1, 1, 2]
    assert [n.chord_size for n in notes] == [2, 2, 1]
    assert [n.staff_pitch for n in notes] == [-1, -3, 0]
    assert notes[0].chord == notes[1].chord != notes[2].chord


def test_chord_requires_all_members(tmp_path):
    source = read_semantics(musicxml(tmp_path))
    first, second = source.notes
    source = replace(
        source,
        notes=(
            replace(first, chord_size=2),
            replace(second, chord=first.chord, chord_size=2, member=1, offset=Fraction(0)),
        ),
    )
    xml = sheet_xml().replace('<head-chords>10 20</head-chords>', '<head-chords>10</head-chords>')
    xml = xml.replace('source="20" target="2"', 'source="10" target="2"')
    result = match_notes(source, load_visual_graph(book(tmp_path, xml)))
    assert all(m.status == 'MATCHED' for m in result.notes)
    broken = sheet_xml()
    assert all(
        m.status != 'MATCHED'
        for m in match_notes(source, load_visual_graph(book(tmp_path, broken))).notes
    )


def test_dangling_chord_member_prevents_confident_match(tmp_path):
    xml = sheet_xml().replace(
        '</relations>', '<relation source="10" target="999"><containment/></relation></relations>'
    )
    result = match_notes(read_semantics(musicxml(tmp_path)), load_visual_graph(book(tmp_path, xml)))
    assert result.notes[0].status == 'AMBIGUOUS'


def test_midmeasure_key_does_not_retroactively_change_initial_region(tmp_path):
    path = tmp_path / 'keys.musicxml'
    path.write_text(
        '''<score-partwise><part id="P1"><measure number="1">
      <attributes><divisions>1</divisions><key><fifths>2</fifths></key></attributes>
      <forward><duration>4</duration></forward></measure><measure number="2">
      <forward><duration>2</duration></forward>
      <attributes><key><fifths>0</fifths></key></attributes>
      </measure></part></score-partwise>'''
    )
    keys = read_semantics(path).keys
    assert [(k.measure, k.offset, k.fifths) for k in keys] == [
        ('1', 0, 2),
        ('2', 0, 2),
        ('2', 2, 0),
    ]


def test_same_pitch_at_distinct_slots_uses_timing_not_geometry(tmp_path):
    xml = sheet_xml().replace('pitch="2"', 'pitch="3"')
    result = match_notes(
        read_semantics(musicxml(tmp_path, ('F#4', 'F#4'))), load_visual_graph(book(tmp_path, xml))
    )
    assert [m.head_id for m in result.notes] == ['sheet#1:1', 'sheet#1:2']


def test_explicit_part_id_beats_xml_part_order_and_unknown_multi_part_abstains(tmp_path):
    path = tmp_path / 'parts.musicxml'
    note = '<measure number="1"><attributes><divisions>1</divisions><clef><sign>G</sign><line>2</line></clef></attributes><note><pitch><step>F</step><alter>1</alter><octave>4</octave></pitch><duration>1</duration></note></measure>'
    path.write_text(
        f'<score-partwise><part id="P2">{note}</part><part id="P1">{note}</part></score-partwise>'
    )
    semantic = read_semantics(path)
    assert [n.part for n in semantic.notes] == ['2', '1']
    result = match_notes(semantic, load_visual_graph(book(tmp_path)))
    assert [m.status for m in result.notes] == ['UNMATCHED', 'MATCHED']
    path.write_text(
        path.read_text().replace('id="P1"', 'id="random1"').replace('id="P2"', 'id="random2"')
    )
    result = match_notes(read_semantics(path), load_visual_graph(book(tmp_path)))
    assert all(m.status == 'UNMATCHED' for m in result.notes)
