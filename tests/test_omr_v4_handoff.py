"""Analysis admission must never confer edit ownership."""

from dataclasses import asdict, replace
import copy
import pytest
from PIL import ImageDraw
from backend.omr_v4.handoff import classify_handoff, ELIGIBLE, BLOCKED
from backend.omr_v4.ink import pixels_from_runs, rle
from backend.omr_v4.masks import raster_digest
from backend.omr_v4.source_ink import COMPLETE, PARTIAL
from backend.omr_v4.visual_graph import Relation, ProtectedRegion
from test_omr_v4_source_ink import fixture, with_staff, run
from test_omr_v4_ink import symbol


def scene(staff=False, mutate=None):
    data = fixture()
    if staff:
        data = with_staff(data)
        ImageDraw.Draw(data[0]).line((0, 22, 79, 22), fill=0)
    if mutate:
        data = mutate(data)
    source, graph, points, metadata, binary = data
    evidence = run(data)
    payload = asdict(evidence)
    for g in payload['groups']:
        if g['status'] == COMPLETE:
            g['status'] = PARTIAL
            g['blockers'] = ('UNCERTAIN_ANTIALIAS_BOUNDARY',)
            for row in payload['ownership']:
                if row['atomic_group_id'] == g['id']:
                    row['status'] = PARTIAL
    support = set().union(*points.values())
    staff_points = {(x, 22) for x in range(80)} - support if staff else set()
    return source, graph, payload, points, staff_points


def test_partial_is_analysis_only_and_deterministic():
    data = scene()
    before = copy.deepcopy(data[2])
    h = classify_handoff(*data)
    assert h.decision == 'READY_FOR_MASK_REFINEMENT_ANALYSIS'
    assert h.groups[0].refinement_eligibility == ELIGIBLE
    assert not h.groups[0].edit_authorized and not hasattr(h, 'owned')
    assert data[2] == before
    assert h.to_json() == classify_handoff(*data).to_json()
    assert h.groups[0].max_support_distance == 2


def test_bounded_staff_with_two_sides_can_enter_analysis():
    h = classify_handoff(*scene(True))
    assert h.groups[0].refinement_eligibility == ELIGIBLE
    assert h.groups[0].staff
    assert all(s.status == 'STAFF_REFINEMENT_ELIGIBLE' for s in h.groups[0].staff)
    assert all(len(s.left_evidence) >= 3 and len(s.right_evidence) >= 3 for s in h.groups[0].staff)


def test_missing_side_staff_evidence_blocks():
    source, graph, evidence, points, staff = scene(True)
    h = classify_handoff(source, graph, evidence, points, {p for p in staff if p[0] < 18})
    assert h.groups[0].refinement_eligibility == BLOCKED
    assert any(b.startswith('STAFF:') for b in h.groups[0].blockers)


def test_unbounded_staff_geometry_blocks():
    source, graph, evidence, points, staff = scene(True)
    graph = replace(
        graph,
        staves=(replace(graph.staves[0], source_xml='<staff><lines><line/></lines></staff>'),),
    )
    h = classify_handoff(source, graph, evidence, points, staff)
    assert h.groups[0].refinement_eligibility == BLOCKED


def test_local_antialias_boundary_refinable_without_ownership():
    def mutate(data):
        data[0].putpixel((19, 22), 250)
        return data

    h = classify_handoff(*scene(mutate=mutate))
    g = h.groups[0]
    assert g.refinement_eligibility == ELIGIBLE
    assert g.antialias_status == 'ANTIALIAS_BOUNDARY_REFINABLE'
    assert (19, 22) in pixels_from_runs(g.bounded_unknown)
    assert (19, 22) not in pixels_from_runs(g.known_core) | pixels_from_runs(g.known_fringe)


@pytest.mark.parametrize('kind', ['text', 'barline'])
def test_protected_or_structural_region_blocks(kind):
    source, graph, evidence, points, staff = scene()
    if kind == 'text':
        graph = replace(
            graph,
            text_protected_regions=(
                ProtectedRegion('p', 'sheet#1', 'lyric', (18, 20, 19, 24), (), 'text'),
            ),
        )
    else:
        s = symbol('9', 'barline', (18, 20, 19, 24))
        graph = replace(graph, symbols={**graph.symbols, s.id: s})
    h = classify_handoff(source, graph, evidence, points, staff)
    assert h.groups[0].refinement_eligibility == BLOCKED
    assert any(
        b.startswith('PROTECTED:' if kind == 'text' else 'STRUCTURAL:')
        for b in h.groups[0].blockers
    )


def test_explicit_moving_attachment_may_enter_but_not_be_owned():
    source, graph, evidence, points, staff = scene()
    art = symbol('8', 'articulation', (28, 20, 30, 22))
    chord = symbol('9', 'head-chord', None)
    graph = replace(
        graph,
        symbols={**graph.symbols, art.id: art, chord.id: chord},
        relations=graph.relations
        + (
            Relation('contains', 'contains', chord.id, 'sheet#1:1'),
            Relation('art', 'chord-articulation', chord.id, art.id),
        ),
    )
    h = classify_handoff(source, graph, evidence, points, staff)
    assert h.groups[0].refinement_eligibility == ELIGIBLE
    assert h.groups[0].attachments[0].disposition == 'ATTACHMENT_IDENTIFIED_NEEDS_REFINEMENT'
    assert (28, 20) in pixels_from_runs(h.groups[0].bounded_unknown)
    assert not h.groups[0].edit_authorized


def test_ambiguous_attachment_blocks():
    source, graph, evidence, points, staff = scene()
    art = symbol('8', 'fermata', (28, 20, 30, 22))
    graph = replace(graph, symbols={**graph.symbols, art.id: art})
    h = classify_handoff(source, graph, evidence, points, staff)
    assert h.groups[0].refinement_eligibility == BLOCKED
    assert h.groups[0].attachments[0].disposition == 'ATTACHMENT_AMBIGUOUS_BLOCK'


def test_missing_lineage_blocks():
    data = scene()
    data[2]['processed'][0]['relation_ids'] = ()
    h = classify_handoff(*data)
    assert any(b.startswith('MISSING_LINEAGE:') for b in h.groups[0].blockers)


def test_local_continuation_classification_and_remote_detection():
    def local(data):
        data[0].putpixel((19, 22), 200)
        data[0].putpixel((18, 22), 200)
        return data

    h = classify_handoff(*scene(mutate=local))
    assert h.groups[0].refinement_eligibility == ELIGIBLE
    categories = {k: pixels_from_runs(v) for k, v in h.groups[0].continuation}
    assert (18, 22) in categories['UNKNOWN_LOCAL']

    def remote(data):
        ImageDraw.Draw(data[0]).line((24, 18, 40, 18), fill=0)
        return data

    h = classify_handoff(*scene(mutate=remote))
    assert h.groups[0].refinement_eligibility == BLOCKED
    assert h.groups[0].remote_continuation
    assert any('UNKNOWN_REMOTE_CONTINUATION' in b for b in h.groups[0].blockers)


def test_unrelated_group_proximity_blocks():
    source, graph, evidence, points, staff = scene()
    other = symbol('8', 'head', (27, 20, 29, 22))
    graph = replace(graph, symbols={**graph.symbols, other.id: other})
    row = copy.deepcopy(evidence['processed'][0])
    row['symbol_id'] = other.id
    row['runs'] = rle({(27, 20), (27, 21), (27, 22)})
    evidence['processed'] += (row,)
    own = copy.deepcopy(evidence['ownership'][0])
    own['symbol_id'] = other.id
    own['atomic_group_id'] = 'other'
    own['status'] = COMPLETE
    evidence['ownership'] += (own,)
    g = copy.deepcopy(evidence['groups'][0])
    g['id'] = 'other'
    g['members'] = (other.id,)
    g['status'] = COMPLETE
    evidence['groups'] += (g,)
    h = classify_handoff(source, graph, evidence, points, staff)
    original = next(r for r in h.groups if r.group_id != 'other')
    assert original.refinement_eligibility == BLOCKED
    assert any(b.startswith('UNRELATED_OWNERSHIP:') for b in original.blockers)


def test_complete_evidence_behavior_unchanged():
    data = fixture()
    e = run(data)
    before = e.owned(data[0])
    h = classify_handoff(data[0], data[1], asdict(e), data[2], set())
    assert h.groups[0].ownership_evidence_status == COMPLETE
    assert h.groups[0].refinement_eligibility == 'COMPLETE_ANALYSIS_INPUT'
    assert e.owned(data[0]) == before


def test_source_digest_mismatch_fatal():
    data = scene()
    data[0].putpixel((0, 0), 0)
    with pytest.raises(ValueError, match='digest'):
        classify_handoff(*data)


def test_missing_cached_member_identity_blocks_without_promoting():
    source, graph, evidence, points, staff = scene()
    evidence['ownership'] = tuple(r for r in evidence['ownership'] if r['symbol_id'] != 'sheet#1:1')
    h = classify_handoff(source, graph, evidence, points, staff)
    assert h.groups[0].refinement_eligibility == BLOCKED
    assert 'MISSING_LINEAGE:GROUP_IDENTITY' in h.groups[0].blockers
