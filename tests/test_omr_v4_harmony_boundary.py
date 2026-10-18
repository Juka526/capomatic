"""Strict written normal form is not library realization or production acceptance."""

from dataclasses import replace
from xml.etree import ElementTree as ET

import pytest
from scripts.omr_v4.harmony_boundary_diagnostic import canonical_xml, diagnose, normalize


def h(
    kind='suspended-fourth', degrees=((7, 0, 'add'),), root='C', root_alter=0, bass=None, text=None
):
    node = ET.Element('harmony')
    r = ET.SubElement(node, 'root')
    ET.SubElement(r, 'root-step').text = root
    ET.SubElement(r, 'root-alter').text = str(root_alter)
    k = ET.SubElement(node, 'kind')
    k.text = kind
    if text is not None:
        k.set('text', text)
    if bass:
        b = ET.SubElement(node, 'bass')
        ET.SubElement(b, 'bass-step').text = bass[0]
        ET.SubElement(b, 'bass-alter').text = str(bass[1])
    for value, alter, mode in degrees:
        degree = ET.SubElement(node, 'degree')
        for tag, content in [('value', value), ('alter', alter), ('type', mode)]:
            ET.SubElement(degree, 'degree-' + tag).text = str(content)
    return ET.tostring(node)


def test_equivalent_sus_constructions_have_same_written_normal_form():
    a = normalize(h(text='7sus4'))
    b = normalize(h('dominant', ((3, 0, 'subtract'), (4, 0, 'add')), text='7sus4'))
    assert a == b
    assert a.degrees == ((1, 0), (4, 0), (5, 0), (7, 0))
    assert normalize(canonical_xml(a)) == a


@pytest.mark.parametrize(
    'kwargs',
    [
        {'kind': 'major', 'degrees': ()},
        {'kind': 'minor', 'degrees': ()},
        {'kind': 'dominant', 'degrees': (), 'bass': ('E', 0)},
        {'kind': 'major-seventh', 'degrees': (), 'root': 'D', 'root_alter': -1},
        {'kind': 'minor-seventh', 'degrees': ()},
        {'kind': 'suspended-second', 'degrees': ()},
        {'kind': 'major', 'degrees': ((5, -1, 'alter'), (9, -1, 'add'))},
    ],
)
def test_roundtrip_preserves_root_bass_degrees_and_alterations(kwargs):
    value = normalize(h(**kwargs))
    assert normalize(canonical_xml(value)) == value
    assert canonical_xml(value) == canonical_xml(normalize(canonical_xml(value)))


@pytest.mark.parametrize(
    'left,right',
    [
        (h('major', ()), h('minor', ())),
        (h('dominant', ()), h('major-seventh', ())),
        (h('major', (), bass=('E', 0)), h('major', (), bass=('G', 0))),
        (h(), h(degrees=((7, 1, 'add'),))),
        (h('major', ()), h('major', (), root='D')),
    ],
)
def test_genuine_harmonic_changes_remain_distinct(left, right):
    assert normalize(left) != normalize(right)


def test_written_identity_not_collapsed_by_pitch_class_equivalence():
    csharp = normalize(h('major', (), root_alter=1))
    dflat = normalize(h('major', (), root='D', root_alter=-1))
    assert csharp.pitch_classes == dflat.pitch_classes and csharp != dflat
    second = normalize(h('major', ((2, 0, 'add'),)))
    ninth = normalize(h('major', ((9, 0, 'add'),)))
    assert second.pitch_classes == ninth.pitch_classes and second != ninth


@pytest.mark.parametrize(
    'payload',
    [
        h('Neapolitan', ()),
        h('dominant-seventh', ()),
        h(root_alter='0.5'),
        h(degrees=((7, 0, 'add'), (7, 1, 'alter'))),
        h(degrees=((3, 0, 'alter'),)),
        h(degrees=((14, 0, 'add'),)),
        h('major', (), text='m'),
        h('major', (), text='unrecognized'),
        h('other', ((3, 0, 'add'),)),
        b'<!DOCTYPE harmony [<!ENTITY x "C">]><harmony/>',
    ],
)
def test_unsupported_and_ambiguous_encodings_reject(payload):
    with pytest.raises(ValueError):
        normalize(payload)


def test_duplicate_roots_and_inversion_contradictions_reject():
    node = ET.fromstring(h('major', ()))
    node.append(ET.fromstring('<root><root-step>D</root-step></root>'))
    with pytest.raises(ValueError):
        normalize(ET.tostring(node))
    node = ET.fromstring(h('major', (), bass=('G', 0)))
    ET.SubElement(node, 'inversion').text = '1'
    with pytest.raises(ValueError):
        normalize(ET.tostring(node))


def test_written_equivalence_does_not_claim_pitch_realization_or_guard_pass():
    d = diagnose(h(text='7sus4'))
    assert d['xml_roundtrip_preserves_written_harmony']
    assert d['spec_pitch_classes'] == [0, 5, 7, 10]
    assert d['production_approval'] is False
    assert d['printed_equivalence'] == 'NOT_VALIDATED'
    # Dependency fix must not invalidate a diagnostic test; record disagreement.
    assert d['original_realization_matches_spec_pitch_classes'] == (
        d['original_music21'].get('pitch_classes') == d['spec_pitch_classes']
    )


def test_declared_controls_distinguish_semantic_change_from_equivalence():
    from scripts.omr_v4.harmony_boundary_diagnostic import conformance_controls

    rows = conformance_controls()
    assert len(rows) == 12
    assert all(r['met_expectation'] for r in rows)
    assert sum(r['category'] == 'GENUINE_HARMONIC_CHANGE' for r in rows) == 6
    assert next(r for r in rows if r['name'] == 'equivalent_sus_encoding')['observed_written_equal']


def test_ambiguous_inversion_cannot_drop_written_degree_identity():
    node = ET.fromstring(h('other', ((1, 0, 'add'), (2, 0, 'add'), (9, 0, 'add')), bass=('D', 0)))
    ET.SubElement(node, 'inversion').text = '1'
    with pytest.raises(ValueError, match='Ambiguous inversion'):
        normalize(ET.tostring(node))


def test_accepted_input_must_be_representable_within_normal_form_scope():
    with pytest.raises(ValueError, match='normalized degree alteration'):
        normalize(h('major-seventh', ((7, 2, 'alter'),)))


def test_realization_comparison_ignores_order_but_retains_duplicates_and_octaves(monkeypatch):
    from scripts.omr_v4 import harmony_boundary_diagnostic as module

    def compare(first, second):
        rows = iter([first, second])
        monkeypatch.setattr(
            module,
            'realization',
            lambda _: {'status': 'OBSERVED', 'pitch_classes': [], 'pitches': next(rows)},
        )
        return module.diagnose(h('major', ()))['realized_spelled_pitches_and_octaves_equal']

    assert compare([('C4', 60), ('E4', 64)], [('E4', 64), ('C4', 60)])
    assert not compare([('C4', 60)], [('C4', 60), ('C4', 60)])
    assert not compare([('C4', 60)], [('C5', 72)])
