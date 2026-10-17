"""Layered evidence, explicit group ownership and fail-closed completeness."""

from dataclasses import replace
import numpy as np
import pytest
from PIL import Image
from backend.omr_v4.ink import pixels_from_runs
from backend.omr_v4.source_ink import COMPLETE, PARTIAL, REJECTED, isolate_source_ink
from backend.omr_v4.visual_graph import (
    VisualScoreGraph,
    Geometry,
    Page,
    Relation,
    ProtectedRegion,
    Staff,
)
from test_omr_v4_ink import symbol


def fixture(extra=False):
    source = Image.new('L', (80, 60), 255)
    head = symbol('1', 'head', (20, 20, 24, 24))
    stem = symbol('2', 'stem', (24, 12, 24, 24))
    symbols = {head.id: head, stem.id: stem}
    points = {
        head.id: {(x, y) for x in range(20, 25) for y in range(20, 25)},
        stem.id: {(24, y) for y in range(12, 25)},
    }
    relations = [Relation('hs', 'head-stem', head.id, stem.id)]
    if extra:
        beam = symbol('3', 'beam', (24, 12, 34, 14))
        dot = symbol('4', 'augmentation-dot', (29, 23, 31, 25))
        symbols.update({beam.id: beam, dot.id: dot})
        points[beam.id] = {(x, y) for x in range(24, 35) for y in range(12, 15)}
        points[dot.id] = {(x, y) for x in range(29, 32) for y in range(23, 26)}
        relations.extend(
            [
                Relation('bs', 'beam-stem', beam.id, stem.id),
                Relation('dot', 'augmentation', dot.id, head.id),
            ]
        )
    binary = Image.new('L', source.size, 255)
    for ps in points.values():
        for p in ps:
            source.putpixel(p, 200)
            binary.putpixel(p, 0)
    graph = VisualScoreGraph(
        (Page('sheet#1', 80, 60, 10),), (), (), (), symbols, tuple(relations), (), (), 0, ()
    )
    metadata = {i: (('groups', 'SYMBOL'),) for i in points}
    return source, graph, points, metadata, binary


def run(data, staff=frozenset()):
    return isolate_source_ink(*data, staff_points=staff)


def with_staff(data, y=22):
    source, graph, points, meta, binary = data
    xml = f'<staff><lines><line thickness="1"><point x="0" y="{y}"/><point x="79" y="{y}"/></line></lines></staff>'
    staff = Staff('s', '1', 'sheet#1', 'sys', 'p', 1, 10, (((0, y), (79, y)),), True, xml)
    return source, replace(graph, staves=(staff,)), points, meta, binary


def test_gray_above_127_is_valid_processed_support_and_owned_core():
    data = fixture()
    e = run(data)
    assert all(r.valid for r in e.processed)
    assert e.groups[0].status == COMPLETE
    assert all(r.status == COMPLETE for r in e.ownership)
    assert any(values == (200,) for r in e.ownership for values, count in r.source_value_histogram)
    assert e.owned(data[0])


def test_related_head_stem_shared_pixels_recorded_once():
    e = run(fixture())
    g = e.groups[0]
    union = pixels_from_runs(g.source_union)
    assert len(union) == 33
    assert len(pixels_from_runs(g.shared_intra_group)) == 5
    assert g.unrelated_collision_count == 0


def test_beam_stem_and_simple_isolated_dot_group_complete():
    e = run(fixture(True))
    assert len(e.groups) == 1 and e.groups[0].status == COMPLETE
    assert next(r for r in e.ownership if r.kind == 'augmentation-dot').status == COMPLETE
    assert len(pixels_from_runs(e.groups[0].shared_intra_group)) >= 7


def test_smaller_inter_bbox_does_not_reject_glyph_but_adapter_does_not_clip():
    data = fixture()
    src, g, pts, meta, binary = data
    small = replace(g.symbols['sheet#1:2'], geometry=Geometry(bbox=(24, 14, 24, 22)))
    g = replace(g, symbols={**g.symbols, small.id: small})
    e = run((src, g, pts, meta, binary))
    assert e.groups[0].status == COMPLETE
    assert not e.groups[0].phase18_compatible
    assert not e.owned(src)
    assert pixels_from_runs(e.processed[1].runs) == pts['sheet#1:2']


def test_page_escape_rejects_group():
    src, g, pts, meta, binary = fixture()
    pts['sheet#1:1'].add((-1, 22))
    e = run((src, g, pts, meta, binary))
    assert e.groups[0].status == REJECTED
    assert 'PAGE_BOUND_ESCAPE' in e.groups[0].blockers
    assert not e.owned(src)


def test_unrelated_group_pixel_overlap_fatal_both():
    src, g, pts, meta, binary = fixture()
    h = symbol('5', 'head', (20, 20, 24, 24))
    stem = symbol('6', 'stem', (24, 12, 24, 24))
    g = replace(
        g,
        symbols={**g.symbols, h.id: h, stem.id: stem},
        relations=g.relations + (Relation('other', 'head-stem', h.id, stem.id),),
    )
    pts.update({h.id: set(pts['sheet#1:1']), stem.id: set(pts['sheet#1:2'])})
    e = run((src, g, pts, meta, binary))
    assert len(e.groups) == 2 and all(r.status == REJECTED for r in e.groups)
    assert all('UNRELATED_GROUP_COLLISION' in r.blockers for r in e.groups)


def test_staff_source_component_continuation_not_absorbed():
    data = with_staff(fixture())
    src, g, pts, meta, binary = data
    for x in range(80):
        src.putpixel((x, 22), 0)
    e = run(data)
    assert e.groups[0].status == PARTIAL
    assert all(r.valid for r in e.processed)
    assert (0, 22) not in pixels_from_runs(e.groups[0].source_union)
    assert pixels_from_runs(e.groups[0].core_union)
    assert not e.owned(src)


def test_old_corridor_proximity_alone_does_not_block():
    # Head bottom y24 is two pixels from y26: within old corridor, outside
    # the fixed 1px logical uncertainty band for serialized thickness 1.
    e = run(with_staff(fixture(), 26))
    assert e.groups[0].status == COMPLETE


def test_explicit_staff_assignment_recorded_and_crossing_partial():
    e = run(fixture(), frozenset({(22, 22)}))
    assert e.groups[0].status == PARTIAL
    r = next(r for r in e.ownership if r.kind == 'head')
    assert pixels_from_runs(r.staff_attributed) == {(22, 22)}
    assert (22, 22) in pixels_from_runs(r.unknown_crossing)
    assert (22, 22) not in pixels_from_runs(r.source_core)
    assert not e.owned(fixture()[0])


@pytest.mark.parametrize('kind', ['text', 'structural'])
def test_protection_is_fatal(kind):
    src, g, pts, meta, binary = fixture()
    if kind == 'text':
        g = replace(
            g,
            text_protected_regions=(
                ProtectedRegion('p', 'sheet#1', 'lyrics', (20, 20, 22, 22), (), 'words'),
            ),
        )
    else:
        s = symbol('9', 'barline', (20, 20, 22, 22))
        g = replace(g, symbols={**g.symbols, s.id: s})
    e = run((src, g, pts, meta, binary))
    assert e.groups[0].status == REJECTED
    assert all(not r.source_core and not r.fringe for r in e.ownership)
    assert not e.owned(src)


def test_bounded_fringe_and_unknown_continuation():
    data = fixture()
    src, g, pts, meta, binary = data
    src.putpixel((19, 22), 200)
    e = run(data)
    assert (19, 22) in pixels_from_runs(e.groups[0].fringe_union)
    assert e.groups[0].status == COMPLETE
    src.putpixel((18, 22), 200)
    e = run(data)
    assert (18, 22) not in pixels_from_runs(e.groups[0].source_union)
    assert e.groups[0].status == PARTIAL
    assert 'UNACCOUNTED_LOCAL_CONTINUATION' in e.groups[0].blockers


def test_faint_uncertain_boundary_never_silently_complete():
    data = fixture()
    data[0].putpixel((19, 22), 250)
    e = run(data)
    assert e.groups[0].status == PARTIAL
    assert (19, 22) not in pixels_from_runs(e.groups[0].fringe_union)


def test_fringe_cannot_absorb_unrelated_core():
    src, g, pts, meta, binary = fixture()
    h = symbol('5', 'head', (18, 21, 19, 22))
    st = symbol('6', 'stem', (18, 15, 18, 22))
    g = replace(
        g,
        symbols={**g.symbols, h.id: h, st.id: st},
        relations=g.relations + (Relation('other', 'head-stem', h.id, st.id),),
    )
    pts[h.id] = {(18, 21), (19, 21), (18, 22), (19, 22)}
    pts[st.id] = {(18, y) for y in range(15, 23)}
    for i in (h.id, st.id):
        for p in pts[i]:
            src.putpixel(p, 200)
            binary.putpixel(p, 0)
    e = run((src, g, pts, meta, binary))
    assert not e.owned(src)
    assert any('UNRELATED_GROUP_COLLISION' in r.blockers for r in e.groups)


def test_unknown_processed_stage_and_bad_binary_fail_closed():
    src, g, pts, meta, binary = fixture(True)
    e = run((src, g, pts, {}, binary))
    assert e.groups[0].status == REJECTED
    binary.putpixel((20, 20), 255)
    e = run((src, g, pts, meta, binary))
    assert 'BINARY_SUPPORT_DISAGREEMENT' in e.groups[0].blockers


def test_deterministic_json_and_digest_and_complete_only_adapter():
    data = fixture(True)
    e = run(data)
    assert e.to_json() == run(data).to_json()
    assert e.owned(data[0])
    altered = data[0].copy()
    altered.putpixel((0, 0), 0)
    with pytest.raises(ValueError, match='digest'):
        e.owned(altered)
    partial = run(with_staff(data))
    assert partial.groups[0].status == PARTIAL
    assert not partial.owned(data[0])


def test_staff_classes_explicit_and_source_digest_immutable():
    data = fixture()
    e = run(data, frozenset({(22, 22), (19, 22)}))
    head = next(r for r in e.ownership if r.kind == 'head')
    classes = {key: pixels_from_runs(value) for key, value in head.staff_pixel_classes}
    assert (22, 22) in classes['SHARED_OR_INSEPARABLE']
    assert (19, 22) in classes['STAFF_ATTRIBUTED']
    assert (22, 22) not in classes['SYMBOL_CORE']
    assert classes['SYMBOL_CORE'].isdisjoint(classes['UNKNOWN'])


def test_white_processed_pixel_is_not_owned_core():
    data = fixture()
    data[0].putpixel((22, 22), 255)
    e = run(data)
    assert e.groups[0].status == PARTIAL
    assert (22, 22) not in pixels_from_runs(e.groups[0].core_union)


def test_unknown_attached_curve_blocks_complete_without_erasing_core():
    source, g, points, meta, binary = fixture()
    curve = symbol('8', 'slur', (30, 30, 40, 40))
    g = replace(
        g,
        symbols={**g.symbols, curve.id: curve},
        relations=g.relations + (Relation('curve', 'slur-head', curve.id, 'sheet#1:1'),),
    )
    e = run((source, g, points, meta, binary))
    assert e.groups[0].status == PARTIAL
    assert 'UNOWNED_MOVING_ATTACHMENT' in e.groups[0].blockers
    assert e.groups[0].core_union and not e.owned(source)


def test_incomplete_beam_group_never_partially_injected():
    source, g, points, meta, binary = fixture(True)
    points.pop('sheet#1:3')
    e = run((source, g, points, meta, binary))
    assert e.groups[0].status == REJECTED
    assert not e.owned(source)


def test_foreign_glyph_overlap_not_owned_even_without_geometry():
    source, g, points, meta, binary = fixture()
    foreign = symbol('8', 'articulation', None)
    g = replace(g, symbols={**g.symbols, foreign.id: foreign})
    points[foreign.id] = {(22, 22)}
    e = run((source, g, points, meta, binary))
    assert e.groups[0].status == PARTIAL
    assert (22, 22) not in pixels_from_runs(e.groups[0].source_union)


def test_fractional_skew_staff_band_preserves_polyline_geometry():
    from backend.omr_v4.source_ink import _staff_context

    source, g, points, meta, binary = fixture()
    staff = Staff(
        's',
        '1',
        'sheet#1',
        'sys',
        'p',
        1,
        10,
        (((0, 15), (79, 35)),),
        True,
        '<staff><lines><line thickness="1"/></lines></staff>',
    )
    g = replace(g, staves=(staff,))
    band, missing = _staff_context(g, source.size)
    assert not missing
    assert band[20, 20] and not band[20, 60]
    assert band[30, 60]


def test_owned_projections_reference_one_complete_union():
    from backend.omr_v4.ink import pixels_from_runs

    data = fixture()
    e = run(data)
    views = e.owned(data[0])
    assert len(views) == 2
    assert len(set(v.evidence for v in views)) == 1
    assert set().union(*(pixels_from_runs(v.runs) for v in views)) == pixels_from_runs(
        e.groups[0].source_union
    )


def test_missing_staff_width_never_silently_complete():
    source, g, points, meta, binary = with_staff(fixture())
    staff = replace(g.staves[0], source_xml='<staff><lines><line/></lines></staff>')
    e = run((source, replace(g, staves=(staff,)), points, meta, binary))
    assert e.groups[0].status == PARTIAL
    assert 'UNBOUNDED_STAFF_GEOMETRY' in e.groups[0].blockers


def test_cli_coordinate_provenance_hash_mismatch_fatal(tmp_path):
    import hashlib, json
    from scripts.omr_v4.inspect_source_ink import inspect_source_ink

    source = Image.new('L', (3, 3), 255)
    source.save(tmp_path / 'source.png')
    for name in ('recognized.omr', 'plan.json', 'graph-summary.json', 'semantic-report.json'):
        (tmp_path / name).write_text('{}')
    before = (tmp_path / 'source.png').read_bytes()
    forensic = tmp_path / 'ink-forensics'
    forensic.mkdir()
    (forensic / 'ink-forensics-summary.json').write_text(
        json.dumps(
            {
                'source': {'file_sha256': hashlib.sha256(before).hexdigest()},
                'omr_sha256': 'wrong',
                'supplementary_measurements': {
                    'raster_reproduction': {'native_pixels_identical': True}
                },
            }
        )
    )
    with pytest.raises(ValueError, match='provenance'):
        inspect_source_ink(tmp_path, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()
    assert (tmp_path / 'source.png').read_bytes() == before


def test_processed_bundle_pin_metadata_and_binary_validation(tmp_path):
    import io, zipfile
    from backend.omr_v4.source_ink import read_processed_bundle, PINNED_BUILD

    source, g, points, metadata, binary = fixture()
    payload = io.BytesIO()
    binary.save(payload, format='PNG')
    path = tmp_path / 'bundle.omr'

    def write(pin):
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('book.xml', f'<book software-build="{pin}"/>')
            z.writestr(
                'sheet#1/sheet#1.xml',
                '<sheet><glyph-index><glyph id="7" left="5" top="5" groups="SYMBOL"><run-table orientation="HORIZONTAL" width="2" height="1"><runs>2</runs></run-table></glyph></glyph-index></sheet>',
            )
            z.writestr('sheet#1/BINARY.png', payload.getvalue())

    write(PINNED_BUILD)
    glyphs, meta, saved, staff, digest = read_processed_bundle(path, g)
    assert glyphs['sheet#1:7'] == {(5, 5), (6, 5)}
    assert dict(meta['sheet#1:7'])['groups'] == 'SYMBOL'
    assert saved.size == source.size and isinstance(staff, frozenset)
    write('unverified')
    with pytest.raises(ValueError, match='revision'):
        read_processed_bundle(path, g)


def test_uniform_source_has_no_verified_core_merely_from_binary_label():
    source, g, points, meta, binary = fixture()
    source.paste(230, (0, 0, 80, 60))
    e = run((source, g, points, meta, binary))
    assert e.groups[0].status == PARTIAL
    assert not e.groups[0].core_union
    assert 'CORE_CONTRAST_UNCERTAIN' in e.groups[0].blockers


def test_unresolved_chord_endpoint_blocks_dot_ownership():
    source, g, points, meta, binary = fixture(True)
    container = symbol('9', 'head-chord', None)
    relations = tuple(r for r in g.relations if r.id != 'dot') + (
        Relation('dot', 'augmentation', 'sheet#1:4', container.id),
    )
    g = replace(g, symbols={**g.symbols, container.id: container}, relations=relations)
    e = run((source, g, points, meta, binary))
    dot = next(r for r in e.ownership if r.kind == 'augmentation-dot')
    assert dot.status == REJECTED
    assert 'UNRESOLVED_RELATION_ENDPOINT' in dot.blockers
