"""Developer audit preserves evidence without authorizing a new match."""

import hashlib
import json

from PIL import Image

from backend.omr_v4.matcher import match_notes, read_semantics
from backend.omr_v4.plan import build_plan
from backend.omr_v4.visual_graph import load_visual_graph
from omr_v4_fixtures import book, musicxml, sheet_xml, transposed
from scripts.omr_v4.audit_mapping import candidate_audit, draw_gap, intersection_audit


def test_audit_keeps_pitch_mismatch_and_other_slot_candidates(tmp_path):
    graph = load_visual_graph(book(tmp_path, sheet_xml().replace('pitch="3"', 'pitch="4"')))
    path = musicxml(tmp_path)
    source = read_semantics(path)
    target = read_semantics(transposed(tmp_path, path, 1))
    matches = match_notes(source, graph)
    plan = json.loads(build_plan(graph, source, target, matches).to_json())
    report = candidate_audit(source.notes[0], graph, plan)
    assert len(report['candidates']) == 2
    exact = next(c for c in report['candidates'] if c['checks']['exact_onset'])
    assert exact['id'] == 'sheet#1:1'
    assert exact['rejected_checks'] == ['staff_pitch_agrees']
    assert exact['in_relevant_slot_region']
    assert exact['voice_slot_evidence'][0]['status'] == 'BEGIN'
    assert any(r['kind'] == 'beam-stem' for r in exact['relations'])
    assert exact['existing_match_owner'] is None
    assert not next(c for c in report['candidates'] if c['id'] == 'sheet#1:2')['checks'][
        'exact_onset'
    ]
    # The report is deterministic and does not alter the frozen matching result.
    assert report == candidate_audit(source.notes[0], graph, plan)
    assert matches.notes[0].status == 'UNMATCHED'


def test_nested_protection_is_reported_without_deleting_pairs(tmp_path):
    graph = load_visual_graph(book(tmp_path))
    pairs = [
        {'edit_id': 'e', 'page': 'sheet#1', 'protected_id': 'sheet#1:60', 'region': [1, 2, 3, 4]},
        {'edit_id': 'e', 'page': 'sheet#1', 'protected_id': 'sheet#1:61', 'region': [1, 2, 3, 4]},
        {
            'edit_id': 'f',
            'page': 'sheet#1',
            'protected_id': 'sheet#1:63',
            'region': [20, 20, 30, 30],
        },
    ]
    result = intersection_audit({'intersections': pairs}, graph)
    assert result['pair_count'] == 3
    assert result['nested_duplicate_pair_numbers'] == [2]
    assert len(result['unique_intersection_components']) == 2
    assert result['pairs'] == pairs


def test_gap_crop_preserves_source_and_has_distinct_annotation_panel(tmp_path):
    graph = load_visual_graph(book(tmp_path))
    semantic = read_semantics(musicxml(tmp_path))
    plan = {'matches': {'notes': []}}
    audit = candidate_audit(semantic.notes[0], graph, plan)
    source = Image.new('RGB', (400, 300), '#dddddd')
    before = hashlib.sha256(source.tobytes()).hexdigest()
    out = tmp_path / 'gap.png'
    draw_gap(source, graph, audit, out)
    assert hashlib.sha256(source.tobytes()).hexdigest() == before
    with Image.open(out) as output:
        assert output.width > source.width
        # The left panel is an untouched source crop, including its staff area.
        assert output.getpixel((40, 100)) == (221, 221, 221)
