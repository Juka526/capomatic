"""Synthetic evidence-state and MusicXML controls, with no OMR execution."""

import copy
from fractions import Fraction

import pytest

from scripts.research.gt17c_accuracy_audit import (
    candidate_status,
    source_duration,
    continuation_review,
    xml_lyric_extension_audit,
)


@pytest.mark.parametrize(
    'checks,pending,expected',
    [
        ({'a': True}, False, 'PASS_CANDIDATE'),
        ({'a': True}, True, 'UNRESOLVED'),
        ({'a': None}, False, 'UNRESOLVED'),
        ({'a': True, 'b': False}, False, 'DISAGREEMENT'),
    ],
)
def test_candidate_status_never_becomes_owner_verification(checks, pending, expected):
    assert candidate_status(checks, pending) == expected
    assert 'OWNER_VERIFIED' not in candidate_status(checks, pending)


@pytest.mark.parametrize(
    'shape,duration',
    [('QUARTER_REST', 1), ('EIGHTH_REST', Fraction(1, 2)), ('WHOLE_REST', 4), ('WHOLE_NOTE', 4)],
)
def test_raw_shape_duration_independent_of_serialized_duration(shape, duration):
    e = {'symbol_id': 'h'}
    graph = {'symbols': {'h': {'shape': shape}}}
    assert source_duration(e, graph)[0] == duration


@pytest.mark.parametrize('level,expected', [(0, 1), (1, Fraction(1, 2)), (2, Fraction(1, 4))])
def test_typed_beam_membership_determines_duration(level, expected):
    e = {'symbol_id': 'h', 'stem_ids': ['s']}
    graph = {'symbols': {'h': {'shape': 'NOTEHEAD_BLACK'}}, 'relations': []}
    for j in range(level):
        graph['symbols'][f'b{j}'] = {'kind': 'beam' if j == 0 else 'beam-hook'}
        graph['relations'].append({'kind': 'beam-stem', 'source': f'b{j}', 'target': 's'})
    assert source_duration(e, graph)[0] == expected


def test_conflicting_beam_and_flag_is_not_silently_accepted():
    e = {'symbol_id': 'h', 'stem_ids': ['s']}
    graph = {
        'symbols': {
            'h': {'shape': 'NOTEHEAD_BLACK'},
            'b': {'kind': 'beam'},
            'f': {'kind': 'flag', 'shape': 'FLAG_1'},
        },
        'relations': [
            {'kind': 'beam-stem', 'source': 'b', 'target': 's'},
            {'kind': 'flag-stem', 'source': 'f', 'target': 's'},
        ],
    }
    with pytest.raises(ValueError):
        source_duration(e, graph)


def test_head_chord_dot_lineage_yields_dotted_half_without_guessing():
    e = {'symbol_id': 'h'}
    graph = {
        'symbols': {'h': {'shape': 'NOTEHEAD_VOID'}, 'dot': {'kind': 'augmentation-dot'}},
        'relations': [
            {'kind': 'contains', 'source': 'ch', 'target': 'h'},
            {'kind': 'augmentation', 'source': 'dot', 'target': 'ch'},
        ],
    }
    assert source_duration(e, graph) == (3, ['dot'])


@pytest.mark.parametrize('kind', ['start', 'continue', 'stop', None])
def test_xml_extend_is_explicit_semantic_record_not_visual_dash(kind):
    attr = f' type="{kind}"' if kind else ''
    xml = f'<score-partwise><part><measure number="1"><note><lyric number="2"><text>의</text><extend{attr}/></lyric></note></measure></part></score-partwise>'
    report = xml_lyric_extension_audit(xml)
    assert report['count'] == 1 and report['records'][0]['row'] == '2'
    assert report['records'][0]['type'] == (kind or 'legacy-start')
    assert report['completeness'].startswith('UNVERIFIED')


def test_ordinary_printed_dash_is_not_an_xml_extender():
    xml = '<score-partwise><part><measure number="1"><note><lyric><text>—</text></lyric></note></measure></part></score-partwise>'
    assert xml_lyric_extension_audit(xml)['count'] == 0
    with pytest.raises(ValueError):
        xml_lyric_extension_audit(xml.replace('<text>—</text>', '<extend type="guessed"/>'))


def test_second_ending_does_not_inherit_preceding_printed_lyric(monkeypatch):
    monkeypatch.setattr('scripts.research.gt17c_accuracy_audit.crop_reference', lambda n: None)
    inv = {
        'lyrics': [{'id': 'last', 'row': 1, 'measure': 27, 'onset': '0', 'text': '로'}],
        'events': [{'id': 'e', 'symbol_id': 'head', 'printed_measure': 28, 'onset': '0'}],
        'continuations': [
            {
                'id': 'mark',
                'measure': 28,
                'row': 1,
                'onset': '0',
                'source_dark_bbox': [0, 0, 10, 2],
                'event_id': 'e',
                'held_syllable_candidate': '곳',
                'owner_answer': None,
            }
        ],
    }
    old = copy.deepcopy(inv)
    result = continuation_review(inv)[0]
    assert result['status'] == 'UNRESOLVED' and result['held_syllable_candidate'] == '곳'
    assert result['owner_answer'] is None and inv == old


def test_sound_and_notation_tie_roles_are_audited_separately():
    from scripts.research.gt17c_accuracy_audit import xml_curve_audit

    xml = '<score-partwise><part><measure number="21"><note><tie type="start"/><notations><tied type="stop"/><slur number="1" type="start"/></notations></note></measure></part></score-partwise>'
    report = xml_curve_audit(xml)
    assert len(report['tie_sound_notation_disagreements']) == 1
    assert report['slur_records'][0]['measure_xml'] == '21'
    clean = xml.replace('<tied type="stop"/>', '<tied type="start"/>')
    assert not xml_curve_audit(clean)['tie_sound_notation_disagreements']
