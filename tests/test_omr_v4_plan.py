import json
from dataclasses import FrozenInstanceError, replace
from xml.etree import ElementTree as ET

import pytest
from PIL import Image

from backend.omr_v4.diagnostic import write_diagnostics
from backend.omr_v4.matcher import match_notes, read_semantics
from backend.omr_v4.plan import build_plan
from backend.omr_v4.visual_graph import load_visual_graph
from omr_v4_fixtures import book, musicxml, sheet_xml, transposed


def inputs(tmp_path, shift=1, xml=None):
    graph = load_visual_graph(book(tmp_path, xml))
    source_xml = musicxml(tmp_path)
    source = read_semantics(source_xml)
    target = read_semantics(transposed(tmp_path, source_xml, shift))
    return graph, source, target, match_notes(source, graph)


@pytest.mark.parametrize('shift,steps', [(1, 1), (-1, 0), (2, 1), (-2, -1)])
def test_v3_spelling_drives_diatonic_pixel_displacement(tmp_path, shift, steps):
    plan = build_plan(*inputs(tmp_path, shift))
    assert len(plan.note_moves) == 2
    move = plan.note_moves[0]
    assert move.diatonic_steps == steps
    assert move.target_y == move.source_y - steps * 5
    assert move.target_x == move.source_x
    if shift == -1:
        assert move.source_pitch == 'F#4' and move.target_pitch == 'F4'
    assert plan.beam_groups[0].status == 'UNIFORM_DELTA'
    assert plan.slurs[0].linked and plan.slurs[0].tie
    assert {e[0] for e in plan.slurs[0].endpoints} == {'LEFT', 'RIGHT'}
    assert plan.key_signatures[0].status == 'MAPPED'


def test_mixed_beam_delta_requires_reconstruction(tmp_path):
    graph, source, target, matches = inputs(tmp_path)
    # The planner consumes target semantics per note; it cannot assume a page interval.
    changed = replace(target.notes[1], diatonic_number=source.notes[1].diatonic_number + 2)
    plan = build_plan(graph, source, replace(target, notes=(target.notes[0], changed)), matches)
    assert [m.target_y - m.source_y for m in plan.note_moves] == [-5, -10]
    assert plan.beam_groups[0].status == 'RECONSTRUCT_REQUIRED'
    assert dict(plan.metrics)['mixed_delta_beam_groups'] == 1
    assert [e[4] for e in plan.slurs[0].endpoints] == [-5, -10]


def test_unmatched_heads_make_groups_and_slurs_unresolved(tmp_path):
    args = inputs(tmp_path, xml=sheet_xml().replace('pitch="2"', 'pitch="7"'))
    plan = build_plan(*args)
    assert plan.beam_groups[0].uniform_delta is None
    assert plan.beam_groups[0].status == 'UNRESOLVED'
    assert not plan.slurs[0].linked
    assert dict(plan.metrics)['unmatched_semantic_count'] == 1


def test_protected_intersections_include_connected_ledgers_and_target_sweep(tmp_path):
    plan = build_plan(*inputs(tmp_path, -2))
    move = plan.note_moves[0]
    connected = dict(move.connected_symbols)
    assert {
        'head',
        'stem',
        'beam',
        'beam-hook',
        'alter',
        'augmentation-dot',
        'flag',
        'ledger',
        'slur',
    } <= connected.keys()
    assert plan.intersections and dict(plan.metrics)['protected_region_intersection_count'] > 0
    assert any(i.protected_id == 'sheet#1:61' for i in plan.intersections)
    assert any('ledger' in reason for reason in move.blockers)


def test_serialization_is_deterministic_and_plan_immutable(tmp_path):
    args = inputs(tmp_path)
    plan = build_plan(*args)
    assert plan.to_json() == build_plan(*args).to_json()
    with pytest.raises(FrozenInstanceError):
        plan.diagnostic_only = False
    root = ET.fromstring(sheet_xml())
    for path in ('.//inters', './/relations'):
        el = root.find(path)
        el[:] = list(reversed(list(el)))
    graph = load_visual_graph(book(tmp_path, ET.tostring(root), 'shuffled.omr'))
    assert (
        plan.to_json() == build_plan(graph, args[1], args[2], match_notes(args[1], graph)).to_json()
    )
    assert json.loads(plan.to_json())['diagnostic_only'] is True


def test_structural_target_changes_rejected(tmp_path):
    graph, source, target, matches = inputs(tmp_path)
    target = replace(target, notes=(replace(target.notes[0], duration=2), target.notes[1]))
    with pytest.raises(ValueError, match='correspondence'):
        build_plan(graph, source, target, matches)


def test_missing_key_geometry_is_unmapped(tmp_path):
    xml = sheet_xml().replace('source="70" target="71"', 'source="10" target="71"')
    plan = build_plan(*inputs(tmp_path, xml=xml))
    assert dict(plan.metrics)['key_regions_mapped'] == 0
    assert all(k.status == 'UNMAPPED' for k in plan.key_signatures)


def test_diagnostic_writes_files_without_mutating_source(tmp_path):
    graph, source, target, matches = inputs(tmp_path)
    plan = build_plan(graph, source, target, matches)
    image_path = tmp_path / 'source.png'
    Image.new('RGB', (400, 300), '#dddddd').save(image_path)
    before = image_path.read_bytes()
    out = tmp_path / 'diagnostic'
    summary = write_diagnostics(image_path, graph, plan, out)
    assert summary['matched_count'] == 2
    assert image_path.read_bytes() == before
    assert json.loads((out / 'graph-summary.json').read_text())['visual_head_count'] == 2
    assert (out / 'plan.json').read_text() == plan.to_json()
    with Image.open(out / 'diagnostic-overlay.png') as overlay:
        assert overlay.getpixel((0, 0)) == (221, 221, 221)
        assert overlay.getpixel((100, 115)) != (221, 221, 221)
    with Image.open(out / 'diagnostic-annotations.png') as annotation:
        assert annotation.getpixel((0, 0))[3] == 0


def test_wrong_raster_size_rejected(tmp_path):
    graph, source, target, matches = inputs(tmp_path)
    image_path = tmp_path / 'small.png'
    Image.new('RGB', (40, 30)).save(image_path)
    with pytest.raises(ValueError, match='dimensions'):
        write_diagnostics(
            image_path, graph, build_plan(graph, source, target, matches), tmp_path / 'out'
        )


def test_offline_inspector_reuses_v3_semantics_without_external_tools(tmp_path):
    from scripts.omr_v4.inspect_layout import inspect_recognized

    raster = tmp_path / 'raster.png'
    Image.new('L', (400, 300), 255).save(raster)
    out = tmp_path / 'inspect'
    summary = inspect_recognized(raster, book(tmp_path), musicxml(tmp_path), -1, out)
    report = json.loads((out / 'semantic-report.json').read_text())
    assert all(p['ok'] for p in report['integrity'])
    assert report['transposition']['semitones'] == -1
    assert summary['matched_count'] == 2
    assert (out / 'diagnostic-overlay.png').is_file()


def test_cross_system_slur_extensions_are_not_claimed_linked(tmp_path):
    xml = sheet_xml().replace('<slur id="50"', '<slur left-extension="999" id="50"')
    plan = build_plan(*inputs(tmp_path, xml=xml))
    assert not plan.slurs[0].linked
    assert any('cross-system' in b for b in plan.blockers)


def test_invalid_geometry_inspection_skips_v3_spatial_repair(tmp_path):
    from scripts.omr_v4.inspect_layout import inspect_recognized

    raster = tmp_path / 'raster.png'
    Image.new('L', (400, 300), 255).save(raster)
    xml = sheet_xml().replace('left="20"', 'left="bad"')
    summary = inspect_recognized(
        raster, book(tmp_path, xml), musicxml(tmp_path), 1, tmp_path / 'out'
    )
    assert summary['nonfinite_invalid_geometry_count'] == 1
    assert summary['matched_count'] == 0


def test_repeated_offline_inspection_has_identical_plan_json(tmp_path):
    from scripts.omr_v4.inspect_layout import inspect_recognized

    raster = tmp_path / 'raster.png'
    Image.new('L', (400, 300), 255).save(raster)
    omr, xml = book(tmp_path), musicxml(tmp_path)
    for name in ('first', 'second'):
        inspect_recognized(raster, omr, xml, -1, tmp_path / name)
    assert (tmp_path / 'first/plan.json').read_bytes() == (
        tmp_path / 'second/plan.json'
    ).read_bytes()
