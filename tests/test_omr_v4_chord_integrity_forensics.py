"""Independent XML degree semantics do not waive the unchanged production guard."""

from fractions import Fraction
from xml.etree import ElementTree as ET

import pytest
from music21 import harmony
from music21.musicxml.xmlToM21 import MeasureParser
from backend.omr_v3.chords import chord_symbol_from_text
from scripts.omr_v4.chord_integrity_forensics import equivalent_shift, spec_profile, xml_harmonies


def h(
    root='C',
    kind='suspended-fourth',
    degrees='<degree><degree-value>7</degree-value><degree-alter>0</degree-alter><degree-type>add</degree-type></degree>',
):
    return ET.fromstring(
        f'<harmony><root><root-step>{root}</root-step></root><kind>{kind}</kind>{degrees}</harmony>'
    )


def test_musicxml_add_seven_zero_is_minor_seventh_not_major():
    profile = spec_profile(h())
    assert profile['degree_profile'] == [(1, 0), (4, 5), (5, 7), (7, 10)]
    assert profile['pitch_classes'] == [0, 5, 7, 10]
    sharp = h(
        degrees='<degree><degree-value>7</degree-value><degree-alter>1</degree-alter><degree-type>add</degree-type></degree>'
    )
    assert spec_profile(sharp)['pitch_classes'] == [0, 5, 7, 11]


def test_noncanonical_sus_add7_and_dominant_omit3_add4_are_equivalent():
    target = ET.fromstring(
        '''<harmony><root><root-step>B</root-step><root-alter>-1</root-alter></root><kind>dominant</kind><degree><degree-value>3</degree-value><degree-alter>0</degree-alter><degree-type>subtract</degree-type></degree><degree><degree-value>4</degree-value><degree-alter>0</degree-alter><degree-type>add</degree-type></degree></harmony>'''
    )
    assert equivalent_shift(h(), target, -2)
    target.find('degree/degree-type').text = 'alter'
    assert not equivalent_shift(h(), target, -2)


def test_slash_bass_and_degree_identity_not_only_pitch_class_set():
    a, b = h(kind='major', degrees=''), h(kind='major', degrees='')
    assert equivalent_shift(a, b, 0)
    ET.SubElement(b, 'bass').append(ET.fromstring('<bass-step>C</bass-step>'))
    assert not equivalent_shift(a, b, 0)
    a, b = h(), h(
        degrees='<degree><degree-value>14</degree-value><degree-alter>0</degree-alter><degree-type>add</degree-type></degree>'
    )
    with pytest.raises(ValueError):
        equivalent_shift(a, b, 0)


@pytest.mark.parametrize(
    'xml',
    [
        '<harmony><kind>other</kind></harmony>',
        '<harmony><root><root-step>C</root-step><root-alter>0.5</root-alter></root><kind>major</kind></harmony>',
    ],
)
def test_unknown_or_microtonal_cases_fail_closed(xml):
    with pytest.raises(ValueError):
        spec_profile(ET.fromstring(xml))


def test_onsets_preserve_backup_and_fractional_offsets():
    payload = b'''<score-partwise><part id="p"><measure number="32"><attributes><divisions>4</divisions></attributes><note><duration>4</duration></note><backup><duration>4</duration></backup><harmony><root><root-step>C</root-step></root><kind>major</kind><offset>3</offset></harmony></measure></part></score-partwise>'''
    assert list(xml_harmonies(payload)) == [(32, Fraction(3, 4))]
    with pytest.raises(ValueError):
        xml_harmonies(b'<!DOCTYPE score-partwise [<!ENTITY x "x">]><score-partwise/>')


def test_library_realization_is_recorded_separately_from_xml_oracle():
    cs = MeasureParser().xmlToChordSymbol(h())
    # Do not make a future upstream fix fail this diagnostic test.
    realized = sorted({p.pitchClass for p in cs.pitches})
    assert realized in ([0, 5, 7, 10], [0, 5, 7, 11])
    assert spec_profile(h())['pitch_classes'] == [0, 5, 7, 10]


def test_dominant_alias_normalizes_on_harmony_export_read():
    from music21.musicxml.m21ToXml import MeasureExporter

    original = chord_symbol_from_text('G7/B')
    assert original.chordKind == 'dominant'
    xml = MeasureExporter().chordSymbolToXml(original)
    reread = MeasureParser().xmlToChordSymbol(xml)
    assert reread.chordKind == 'dominant-seventh'
    assert {p.pitchClass for p in original.pitches} == {p.pitchClass for p in reread.pitches}


def test_genuine_added_seventh_change_is_not_equivalent():
    sharp = h(
        degrees='<degree><degree-value>7</degree-value><degree-alter>1</degree-alter><degree-type>add</degree-type></degree>'
    )
    assert not equivalent_shift(h(), sharp, 0)


def test_frozen_protocol_and_source_guard_remain_bound():
    import hashlib
    import json
    from pathlib import Path
    from scripts.omr_v4.chord_integrity_forensics import LOCATIONS, RAW_MXL_SHA

    root = Path(__file__).resolve().parents[1]
    protocol = root / 'docs/V4_CHORD_REFERENCE_PROTOCOL.json'
    assert (
        hashlib.sha256(protocol.read_bytes()).hexdigest()
        == protocol.with_suffix('.sha256').read_text().strip()
    )
    p = json.loads(protocol.read_text())
    assert p['fixed_locations_quarter_lengths'] == [[n, str(o)] for n, o in LOCATIONS]
    assert p['raw_audiveris_mxl_sha256'] == RAW_MXL_SHA
    assert p['full_guard_waiver'] is False
    assert (
        hashlib.sha256((root / 'backend/omr_v3/music_guard.py').read_bytes()).hexdigest()
        == '9f27db149414fe38991b86230f4c15fae90c2ecd1bb5205ecfd56892fa992b43'
    )
