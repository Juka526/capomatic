"""Synthetic ink ownership and safety checks; no Audiveris or real score edits."""

import copy
import json
import math
from dataclasses import replace

import numpy as np
import pytest
from PIL import Image, ImageDraw

from backend.omr_v4.masks import (
    MaskState,
    OwnedInk,
    plan_masks,
    raster_digest,
    validate_pixel_integrity,
)
from backend.omr_v4.visual_graph import load_visual_graph
from omr_v4_fixtures import book


def fixture(tmp_path, extra='', relations=''):
    lines = ''.join(
        f'<line><point x="5" y="{y}"/><point x="195" y="{y}"/></line>' for y in (40, 50, 60, 70, 80)
    )
    xml = f'''<sheet><picture width="200" height="160"/><scale><interline main="10"/></scale>
    <page id="1"><system id="1"><stack id="1" left="5" right="195" duration="1/2"/>
    <part id="1"><staff id="1"><lines>{lines}</lines></staff><measure id="1"><head-chords>10 20</head-chords></measure></part>
    <sig><inters>
    <head id="1" staff="1" pitch="0"><bounds x="40" y="58" w="8" h="6"/></head>
    <head id="2" staff="1" pitch="0"><bounds x="80" y="58" w="8" h="6"/></head>
    <head-chord id="10" staff="1" stem="11"><notes>1</notes></head-chord>
    <head-chord id="20" staff="1" stem="21"><notes>2</notes></head-chord>
    <stem id="11"><bounds x="47" y="25" w="1" h="36"/></stem>
    <stem id="21"><bounds x="87" y="25" w="1" h="36"/></stem>
    <beam id="30" height="3"><median><p1 x="47" y="25"/><p2 x="87" y="25"/></median></beam>
    {extra}</inters><relations>
    <relation source="30" target="11"><beam-stem/></relation>
    <relation source="30" target="21"><beam-stem/></relation>
    {relations}</relations></sig></system></page></sheet>'''
    graph = load_visual_graph(book(tmp_path, xml))
    source = Image.new('L', (200, 160), 255)
    draw = ImageDraw.Draw(source)
    for y in (40, 50, 60, 70, 80):
        draw.line((5, y, 195, y), fill=0)
    glyphs = {}
    for ident in ('1', '2', '11', '21', '30'):
        layer = Image.new('L', source.size)
        d = ImageDraw.Draw(layer)
        if ident in ('1', '2'):
            x = 40 if ident == '1' else 80
            d.ellipse((x, 58, x + 7, 63), fill=255)
        elif ident == '30':
            d.rectangle((47, 24, 87, 26), fill=255)
        else:
            x = 47 if ident == '11' else 87
            d.line((x, 25, x, 60), fill=255)
        source.paste(0, mask=layer)
        glyphs['sheet#1:' + ident] = layer
    digest = raster_digest(source)
    evidence = []
    for ident, layer in glyphs.items():
        array = np.asarray(layer)
        runs = []
        for y in range(source.height):
            xs = np.flatnonzero(array[y])
            if len(xs):
                runs.append((y, int(xs[0]), int(xs[-1]) + 1))
        evidence.append(OwnedInk(ident, digest, tuple(runs), 'known synthetic glyph construction'))
    moves = []
    matches = []
    for ident, x in (('1', 44), ('2', 84)):
        moves.append(
            {
                'source_head_id': 'sheet#1:' + ident,
                'source_x': x,
                'source_y': 61,
                'target_x': x,
                'target_y': 71,
                'staff': 'sheet#1:1',
                'source_pitch': 'B4',
                'target_pitch': 'G4',
            }
        )
        matches.append(
            {'head_id': 'sheet#1:' + ident, 'status': 'MATCHED', 'ownership_basis': 'DIRECT'}
        )
    plan = {
        'note_moves': moves,
        'matches': {'notes': matches},
        'beam_groups': [
            {'id': 'sheet#1:30', 'heads': ['sheet#1:1', 'sheet#1:2'], 'status': 'UNIFORM_DELTA'}
        ],
        'slurs': [],
    }
    return source, graph, plan, tuple(evidence)


def test_source_mask_and_target_envelope_are_distinct_and_complete_group_is_atomic(tmp_path):
    source, graph, layout, ink = fixture(tmp_path)
    result, masks = plan_masks(source, graph, layout, ink)
    assert all(n.state == MaskState.APPROVED for n in result.notes)
    assert result.beam_groups[0].disposition == 'APPROVABLE_AS_GROUP'
    assert result.notes[0].target_envelope[1] == result.notes[0].source_envelope[1] + 10
    assert masks.approved.getpixel((44, 60)) == 255
    assert masks.target.getpixel((44, 73)) == 255
    assert masks.approved.getpixel((44, 73)) == 0
    assert result.to_json() == plan_masks(source, graph, layout, ink)[0].to_json()


def test_protected_text_collision_blocks_atomic_group_and_keeps_nested_protection(tmp_path):
    extra = (
        '<lyric-line id="60"/><lyric-item id="61"><bounds x="40" y="58" w="8" h="6"/></lyric-item>'
    )
    rel = '<relation source="60" target="61"><containment/></relation>'
    source, graph, layout, ink = fixture(tmp_path, extra, rel)
    result, masks = plan_masks(source, graph, layout, ink)
    assert all(MaskState.PROTECTED in n.blockers for n in result.notes)
    assert len(result.protected_regions) == 2 and len(result.nested_protection) == 1
    assert set(result.notes[0].source_protected_ids) == {'sheet#1:60', 'sheet#1:61'}
    assert masks.protected.getpixel((44, 60)) == 255
    assert not np.any(np.asarray(masks.approved))


def test_source_safe_target_text_collision_blocks(tmp_path):
    source, graph, layout, ink = fixture(
        tmp_path, '<word id="60"><bounds x="40" y="70" w="8" h="5"/></word>'
    )
    result, _ = plan_masks(source, graph, layout, ink)
    assert not result.notes[0].source_protected_ids
    assert result.notes[0].target_protected_ids == ('sheet#1:60',)
    assert MaskState.TARGET in result.notes[0].blockers


def test_structural_barline_collision_blocks(tmp_path):
    source, graph, layout, ink = fixture(
        tmp_path, '<barline id="70"><bounds x="43" y="58" w="1" h="10"/></barline>'
    )
    result, _ = plan_masks(source, graph, layout, ink)
    assert all(MaskState.STRUCTURAL in n.blockers for n in result.notes)
    assert result.symbol_policies[0].policy == 'STRUCTURAL_PROTECTED'


def test_staff_polyline_crossings_require_restoration(tmp_path):
    source, graph, layout, ink = fixture(tmp_path)
    result, masks = plan_masks(source, graph, layout, ink)
    crossings = result.notes[0].staff_crossings
    assert any(c.line_number == 3 and c.status == 'RESTORE_REQUIRED' for c in crossings)
    assert any(c.start[1] == c.end[1] == 60 for c in crossings)
    assert np.any(np.asarray(masks.staff_restore))
    assert result.notes[0].state == MaskState.APPROVED


def test_missing_exact_ink_blocks_instead_of_using_bounding_boxes(tmp_path):
    source, graph, layout, _ = fixture(tmp_path)
    result, masks = plan_masks(source, graph, layout)
    assert all(MaskState.UNKNOWN in n.blockers for n in result.notes)
    assert not np.any(np.asarray(masks.approved))
    assert np.any(np.asarray(masks.blocked))


def test_incomplete_beam_blocks_all_members(tmp_path):
    source, graph, layout, ink = fixture(tmp_path)
    layout['beam_groups'][0]['heads'].append('sheet#1:999')
    layout['beam_groups'][0]['status'] = 'UNRESOLVED'
    result, _ = plan_masks(source, graph, layout, ink)
    assert all(MaskState.INCOMPLETE in n.blockers for n in result.notes)
    assert result.beam_groups[0].disposition == 'BLOCKED'


def test_unsupported_moving_articulation_blocks_even_with_explicit_attachment(tmp_path):
    extra = '<articulation id="80"><bounds x="42" y="12" w="4" h="4"/></articulation>'
    rel = '<relation source="10" target="80"><chord-articulation/></relation>'
    source, graph, layout, ink = fixture(tmp_path, extra, rel)
    result, _ = plan_masks(source, graph, layout, ink)
    assert result.symbol_policies[0].policy == 'ATTACHED_MAY_MOVE'
    assert all(MaskState.ATTACHMENT in n.blockers for n in result.notes)


def test_dynamics_and_pedal_are_preserved_never_included_as_source_objects(tmp_path):
    extra = '<dynamics id="80"><bounds x="130" y="120" w="5" h="8"/></dynamics><pedal id="81"><bounds x="150" y="120" w="5" h="8"/></pedal>'
    rel = '<relation source="10" target="80"><chord-dynamics/></relation><relation source="10" target="81"><chord-pedal/></relation>'
    source, graph, layout, ink = fixture(tmp_path, extra, rel)
    result, masks = plan_masks(source, graph, layout, ink)
    assert all(p.policy == 'PRESERVE_IN_PLACE' for p in result.symbol_policies)
    assert all(
        'sheet#1:80' not in n.source_object_ids and 'sheet#1:81' not in n.source_object_ids
        for n in result.notes
    )
    assert masks.protected.getpixel((132, 122)) == 255
    assert all(n.state == MaskState.APPROVED for n in result.notes)


def test_pixel_integrity_inside_only_accepted_outside_fatal():
    original = Image.new('RGB', (10, 10), 'white')
    mask = Image.new('L', original.size)
    mask.putpixel((2, 2), 255)
    candidate = original.copy()
    candidate.putpixel((2, 2), (0, 0, 0))
    assert validate_pixel_integrity(original, candidate, mask)['changed_pixels'] == 1
    candidate.putpixel((3, 3), (0, 0, 0))
    with pytest.raises(ValueError, match='outside approved mask'):
        validate_pixel_integrity(original, candidate, mask)


@pytest.mark.parametrize('damage', ['size', 'mode', 'mask-size', 'nonbinary'])
def test_integrity_rejects_implicit_alignment_changes(damage):
    original = Image.new('RGB', (10, 10), 'white')
    candidate = original.copy()
    mask = Image.new('L', original.size)
    if damage == 'size':
        candidate = Image.new('RGB', (9, 10))
    elif damage == 'mode':
        candidate = candidate.convert('L')
    elif damage == 'mask-size':
        mask = Image.new('L', (9, 10))
    else:
        mask.putpixel((0, 0), 128)
    with pytest.raises(ValueError):
        validate_pixel_integrity(original, candidate, mask)


def test_nonfinite_and_wrong_raster_geometry_rejected(tmp_path):
    source, graph, layout, ink = fixture(tmp_path)
    layout['note_moves'][0]['target_y'] = float('nan')
    with pytest.raises(ValueError, match='Nonfinite'):
        plan_masks(source, graph, layout, ink)
    with pytest.raises(ValueError, match='dimensions'):
        plan_masks(source.resize((100, 80)), graph, layout)


def test_direct_and_repaired_provenance_use_identical_ownership_rules(tmp_path):
    source, graph, layout, ink = fixture(tmp_path)
    direct, _ = plan_masks(source, graph, layout, ink)
    layout['matches']['notes'][0]['ownership_basis'] = 'REPAIRED_PROVENANCE'
    repaired, _ = plan_masks(source, graph, layout, ink)
    assert all(n.state == MaskState.APPROVED for n in direct.notes + repaired.notes)
    assert dict(direct.metrics) == dict(repaired.metrics)
    blocked, _ = plan_masks(source, graph, layout)
    assert all(n.state == MaskState.UNKNOWN for n in blocked.notes)


def test_unlinked_curve_blocks_larger_explicit_group(tmp_path):
    extra = '<slur id="90" right-extension="91"><curve x1="45" y1="65" ctrlx1="50" ctrly1="70" ctrlx2="60" ctrly2="70" x2="65" y2="65"/></slur>'
    rel = '<relation source="90" target="1"><slur-head side="LEFT"/></relation>'
    source, graph, layout, ink = fixture(tmp_path, extra, rel)
    layout['slurs'] = [
        {
            'id': 'sheet#1:90',
            'endpoints': [['LEFT', 'sheet#1:1', None, None, None]],
            'linked': False,
        }
    ]
    result, _ = plan_masks(source, graph, layout, ink)
    assert all(MaskState.INCOMPLETE in n.blockers for n in result.notes)
    assert result.curve_groups[0].disposition == 'BLOCKED'


def test_ink_evidence_must_be_bound_to_original_pixels(tmp_path):
    source, graph, layout, ink = fixture(tmp_path)
    with pytest.raises(ValueError, match='Unbound'):
        plan_masks(source, graph, layout, (replace(ink[0], source_digest='wrong'),) + ink[1:])


def test_target_overlap_with_unrelated_unmoved_head_blocks(tmp_path):
    extra = '<head id="99" staff="1" pitch="2"><bounds x="42" y="70" w="4" h="4"/></head>'
    source, graph, layout, ink = fixture(tmp_path, extra)
    result, _ = plan_masks(source, graph, layout, ink)
    assert all(MaskState.TARGET in n.blockers for n in result.notes)
    assert any('unrelated note' in r for r in result.notes[0].reasons)


def test_missing_fermata_attachment_remains_unresolved_and_protected(tmp_path):
    extra = '<fermata id="90"><bounds x="42" y="59" w="4" h="4"/></fermata>'
    source, graph, layout, ink = fixture(tmp_path, extra)
    result, masks = plan_masks(source, graph, layout, ink)
    assert result.symbol_policies[0].policy == 'UNRESOLVED'
    assert all(MaskState.UNKNOWN in n.blockers for n in result.notes)
    assert masks.protected.getpixel((43, 60)) == 255


def test_mixed_beam_target_geometry_is_not_approved_as_translation(tmp_path):
    source, graph, layout, ink = fixture(tmp_path)
    layout['beam_groups'][0]['status'] = 'RECONSTRUCT_REQUIRED'
    result, _ = plan_masks(source, graph, layout, ink)
    assert all(MaskState.INCOMPLETE in n.blockers for n in result.notes)


def test_owned_ink_is_symbol_level_not_filled_box(tmp_path):
    source, graph, layout, ink = fixture(tmp_path)
    result, masks = plan_masks(source, graph, layout, ink)
    # Known synthetic ellipse has a white bbox corner, which is never approved.
    assert masks.approved.getpixel((40, 58)) == 0
    assert masks.approved.getpixel((44, 60)) == 255
    assert all(c.basis == 'VERIFIED_SOURCE_INK' for n in result.notes for c in n.staff_crossings)


def test_changed_accidental_and_new_ledger_occupancy_fail_closed(tmp_path):
    source, graph, layout, ink = fixture(tmp_path)
    layout['note_moves'][0]['target_pitch'] = 'G#4'
    result, _ = plan_masks(source, graph, layout, ink)
    assert all(MaskState.UNKNOWN in n.blockers for n in result.notes)
    layout['note_moves'][0]['target_pitch'] = 'G4'
    layout['note_moves'][0]['target_y'] = 101
    result, _ = plan_masks(source, graph, layout, ink)
    assert all(MaskState.UNKNOWN in n.blockers for n in result.notes)


def test_developer_writer_outputs_binary_masks_without_touching_evidence(tmp_path):
    from scripts.omr_v4.inspect_masks import inspect_masks

    source, graph, layout, _ = fixture(tmp_path)
    layout['intersections'] = []
    source.save(tmp_path / 'source.png')
    (tmp_path / 'recognized.omr').write_bytes((tmp_path / 'score.omr').read_bytes())
    (tmp_path / 'plan.json').write_text(json.dumps(layout))
    (tmp_path / 'graph-summary.json').write_text('{}')
    (tmp_path / 'semantic-report.json').write_text(
        json.dumps({'semantic_integrity': {'overall': 'pass'}})
    )
    before = (tmp_path / 'source.png').read_bytes()
    out = tmp_path / 'masks'
    summary = inspect_masks(tmp_path, out)
    assert summary['decision'] == 'NEEDS_MASK_SAFETY_FIXES'
    assert summary['metrics']['approved_note_masks'] == 0
    for name in (
        'approved-mask.png',
        'blocked-mask.png',
        'protected-mask.png',
        'staff-restore-mask.png',
        'target-envelope.png',
    ):
        with Image.open(out / name) as image:
            assert image.mode == 'L' and image.size == source.size
            assert set(np.unique(np.asarray(image))) <= {0, 255}
    assert (out / 'mask-overlay.png').is_file() and (out / 'mask-summary.json').is_file()
    assert (tmp_path / 'source.png').read_bytes() == before
    with pytest.raises(ValueError, match='empty/new'):
        inspect_masks(tmp_path, out)
