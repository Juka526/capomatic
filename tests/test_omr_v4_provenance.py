"""Repair lineage is exact evidence, not an alternate fuzzy matcher."""

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from backend.omr_v3 import cleanup
from backend.omr_v4.matcher import SemanticScore, match_notes, read_semantics
from backend.omr_v4.plan import build_plan
from backend.omr_v4.provenance import (
    LEDGER_REPAIR,
    RepairProvenance,
    capture_ledger_repairs,
    match_with_provenance,
)
from backend.omr_v4.visual_graph import load_visual_graph
from omr_v4_fixtures import book, musicxml, sheet_xml
from scripts.omr_v4.inspect_layout import inspect_recognized


def inputs(tmp_path):
    graph = load_visual_graph(book(tmp_path, sheet_xml().replace('pitch="3"', 'pitch="5"')))
    raw = read_semantics(musicxml(tmp_path, ('D4', 'G4')))
    fixed = replace(raw.notes[0], pitch='C4', diatonic_number=29, staff_pitch=6)
    repaired = replace(raw, notes=(fixed, raw.notes[1]))
    raw_matches = match_notes(raw, graph)
    records = capture_ledger_repairs(raw, repaired, raw_matches, 1)
    return raw, repaired, graph, raw_matches, records


def test_unique_raw_d4_to_repaired_c4_transfers_ownership(tmp_path):
    raw, repaired, graph, evidence, records = inputs(tmp_path)
    assert evidence.notes[0].status == 'MATCHED'
    assert match_notes(repaired, graph).notes[0].status == 'UNMATCHED'
    result = match_with_provenance(raw, repaired, graph, evidence, records)
    first, direct = result.notes
    assert first.status == 'MATCHED' and first.head_id == 'sheet#1:1'
    assert first.ownership_basis == 'REPAIRED_PROVENANCE'
    assert first.provenance.raw_event.pitch == 'D4'
    assert first.provenance.raw_event.staff_pitch == 5
    assert first.provenance.repaired_event.pitch == 'C4'
    assert first.provenance.repaired_event.staff_pitch == 6
    assert first.provenance.repair_kind == LEDGER_REPAIR
    assert direct == match_notes(repaired, graph).notes[1]
    assert direct.ownership_basis == 'DIRECT'
    assert result.summary()['direct_matches'] == result.summary()['provenance_matches'] == 1
    assert not result.unmatched_visual_ids
    # Corrected C4 -> Bb3 is one step down. It must not use raw D4 -> Bb3 (two).
    target = replace(
        repaired,
        notes=(replace(repaired.notes[0], pitch='B-3', diatonic_number=28), repaired.notes[1]),
    )
    plan = build_plan(graph, repaired, target, result)
    assert plan.note_moves[0].diatonic_steps == -1
    assert plan.note_moves[0].target_y - plan.note_moves[0].source_y == 5
    assert plan.beam_groups[0].status == 'RECONSTRUCT_REQUIRED'
    assert plan.slurs[0].linked
    assert plan.to_json() == build_plan(graph, repaired, target, result).to_json()
    encoded = json.loads(plan.to_json())['matches']['notes'][0]
    assert encoded['ownership_basis'] == 'REPAIRED_PROVENANCE'
    assert encoded['provenance']['raw_event']['pitch'] == 'D4'
    with pytest.raises(FrozenInstanceError):
        records[0].repair_kind = 'other'


def test_no_provenance_does_not_relax_pitch_matching(tmp_path):
    raw, repaired, graph, evidence, _ = inputs(tmp_path)
    result = match_with_provenance(raw, repaired, graph, evidence, ())
    assert result.notes[0].status == 'UNMATCHED'
    assert result.notes[0].head_id is None
    assert result.notes[1].status == 'MATCHED'


@pytest.mark.parametrize(
    'field,value',
    [
        ('measure', '2'),
        ('staff', 2),
        ('offset', Fraction(1, 2)),
        ('duration', Fraction(2)),
        ('chord_size', 2),
        ('member', 1),
        ('voice', '2'),
        ('part', '2'),
    ],
)
def test_structural_changes_cannot_inherit_ownership(tmp_path, field, value):
    raw, repaired, graph, evidence, records = inputs(tmp_path)
    changed = replace(repaired.notes[0], **{field: value})
    repaired = replace(repaired, notes=(changed, repaired.notes[1]))
    assert not capture_ledger_repairs(raw, repaired, evidence, 1)
    forged = replace(records[0], repaired_event=changed)
    result = match_with_provenance(raw, repaired, graph, evidence, (forged,))
    assert result.notes[0].status != 'MATCHED'


def test_ambiguous_raw_match_never_transfers(tmp_path):
    raw, repaired, graph, evidence, _ = inputs(tmp_path)
    first = evidence.notes[0]
    bad = replace(
        first,
        status='AMBIGUOUS',
        head_id=None,
        candidate_ids=('sheet#1:1', 'sheet#1:2'),
        ownership_basis=None,
    )
    ambiguous = replace(evidence, notes=(bad, evidence.notes[1]))
    records = capture_ledger_repairs(raw, repaired, ambiguous, 1)
    result = match_with_provenance(raw, repaired, graph, ambiguous, records)
    assert result.notes[0].status == 'AMBIGUOUS' and result.notes[0].head_id is None


@pytest.mark.parametrize(
    'damage', ['duplicate-record', 'second-target', 'duplicate-head', 'wrong-kind', 'wrong-count']
)
def test_duplicate_or_unproven_records_fail_closed(tmp_path, damage):
    raw, repaired, graph, evidence, records = inputs(tmp_path)
    if damage == 'duplicate-record':
        records *= 2
    elif damage == 'second-target':
        records += (replace(records[0], repaired_event=repaired.notes[1]),)
    elif damage == 'duplicate-head':
        # Two claimed raw ownership records cannot authorize one visual head.
        second = replace(records[0], raw_event=raw.notes[1], repaired_event=repaired.notes[1])
        records += (second,)
    elif damage == 'wrong-kind':
        records = (replace(records[0], repair_kind='UNVERIFIED_PITCH_CHANGE'),)
    else:
        records = capture_ledger_repairs(raw, repaired, evidence, 2)
        assert not records
    result = match_with_provenance(raw, repaired, graph, evidence, records)
    assert result.notes[0].status != 'MATCHED'
    assert not result.notes[0].head_id


def test_two_repaired_events_claiming_one_raw_event_fail_closed(tmp_path):
    raw, repaired, graph, evidence, records = inputs(tmp_path)
    repaired = replace(repaired, notes=(repaired.notes[0], repaired.notes[0]))
    result = match_with_provenance(raw, repaired, graph, evidence, records)
    assert all(m.head_id is None for m in result.notes)


def test_raw_ownership_must_be_valid_for_this_graph(tmp_path):
    raw, repaired, graph, evidence, records = inputs(tmp_path)
    symbols = dict(graph.symbols)
    symbols['sheet#1:1'] = replace(symbols['sheet#1:1'], pitch_position=4)
    graph = replace(graph, symbols=symbols)
    result = match_with_provenance(raw, repaired, graph, evidence, records)
    assert result.notes[0].status != 'MATCHED'


def test_unchanged_notes_are_identical_direct_matches(tmp_path):
    raw, _, graph, evidence, _ = inputs(tmp_path)
    assert match_with_provenance(raw, raw, graph, evidence, ()) == evidence


@pytest.mark.parametrize('fifths,expected_pitch', [(-1, 'C4'), (2, 'C#4')])
def test_cli_captures_boundary_uses_existing_v3_repair_and_serializes_deterministically(
    tmp_path, fifths, expected_pitch
):
    raw_path = musicxml(tmp_path, ('D4', 'G4'))
    raw_path.write_text(
        raw_path.read_text().replace('<fifths>2</fifths>', f'<fifths>{fifths}</fifths>')
    )
    omr = book(tmp_path, sheet_xml().replace('pitch="3"', 'pitch="5"'))
    raster = tmp_path / 'raster.png'
    Image.new('L', (400, 300), 255).save(raster)
    # Exercise the actual unchanged repair algorithm while supplying its pixel
    # predicate in this tiny fixture; no pitch correction is implemented by V4.
    with patch.object(cleanup, '_has_ledger', return_value=True):
        for name in ('first', 'second'):
            summary = inspect_recognized(raster, omr, raw_path, -2, tmp_path / name)
            assert summary['provenance_matches'] == summary['direct_matches'] == 1
            semantic = json.loads((tmp_path / name / 'semantic-report.json').read_text())
            assert semantic['repair_capture']['count_consistent']
            assert semantic['repair_provenance'][0]['raw_event']['pitch'] == 'D4'
            assert semantic['repair_provenance'][0]['repaired_event']['pitch'] == expected_pitch
    for filename in ('plan.json', 'graph-summary.json', 'semantic-report.json'):
        assert (tmp_path / 'first' / filename).read_bytes() == (
            tmp_path / 'second' / filename
        ).read_bytes()


def test_v3_ledger_repair_source_is_frozen():
    assert (
        hashlib.sha256(Path(cleanup.__file__).read_bytes()).hexdigest()
        == '0ed31d45e4bf092c1325282deabf0b87f15c9e6a1f0240fcd2468c33ec4f3031'
    )


def test_real_duplicate_raw_pitch_candidates_are_not_inherited(tmp_path):
    raw, repaired, _, _, _ = inputs(tmp_path)
    xml = sheet_xml().replace('pitch="3"', 'pitch="5"')
    xml = xml.replace(
        '</inters>',
        '<head id="90" staff="1" pitch="5" grade="1"><bounds x="98" y="111" w="10" h="8"/></head><head-chord id="91" staff="1"/></inters>',
    )
    xml = xml.replace('<head-chords>10 20</head-chords>', '<head-chords>10 20 91</head-chords>')
    xml = xml.replace(
        '</relations>', '<relation source="91" target="90"><containment/></relation></relations>'
    )
    xml = xml.replace(
        '</slots>', '<entry><key>1</key><value chord="91" status="BEGIN"/></entry></slots>'
    )
    graph = load_visual_graph(book(tmp_path, xml, 'ambiguous.omr'))
    evidence = match_notes(raw, graph)
    assert evidence.notes[0].status == 'AMBIGUOUS'
    records = capture_ledger_repairs(raw, repaired, evidence, 1)
    result = match_with_provenance(raw, repaired, graph, evidence, records)
    assert result.notes[0].status == 'AMBIGUOUS'
    assert result.notes[0].head_id is None
