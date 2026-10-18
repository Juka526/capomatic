"""Synthetic checks for source-only selection and isolated glyph/ink contracts."""

from pathlib import Path
import ast
import copy
import json

import pytest
from PIL import Image, ImageDraw

from scripts.research.gt04_visual import choose, glyph, ink_intersections, panel_label, render


def sample():
    regions = [
        {
            'printed_measure': i,
            'within_system': i,
            'repeat_ending_context': {'literal': 'No coordinator-noted ending mark'},
        }
        for i in [1, 2, 3]
    ]
    rows = []
    moves = {}
    for m in [1, 2, 3]:
        for n in range(4):
            ident = f'p1:m{m}:n{n}'
            rows.append(
                {
                    'printed_measures': [m],
                    'id': ident,
                    'kind': 'NOTE',
                    'status': 'MATCHED',
                    'duration': '1',
                    'local_offset': str(n),
                    'chord_size': 1,
                }
            )
            moves[ident] = {'connected_symbols': [['head', [f'h{m}-{n}']], ['stem', [f's{m}-{n}']]]}
    return regions, rows, moves, {'relations': []}


def test_earliest_supported_selection_fixed_before_results_and_does_not_mutate_inputs():
    args = sample()
    before = copy.deepcopy(args)
    selected, decisions = choose(*args)
    assert selected == [2, 3] and decisions[0]['blockers'] == [
        'SYSTEM_INITIAL_CONTEXT_NOT_SUPPORTED'
    ]
    assert args == before


@pytest.mark.parametrize('change', ['curve', 'beam', 'ending', 'unmatched', 'rhythm'])
def test_unsupported_required_notation_or_uncertainty_blocks_selection(change):
    regions, rows, moves, graph = sample()
    if change == 'curve':
        graph['relations'] = [{'source': 'h2-0', 'target': 'curve', 'kind': 'slur-head'}]
    if change == 'beam':
        moves['p1:m2:n0']['connected_symbols'].append(['beam', ['b']])
    if change == 'ending':
        regions[1]['repeat_ending_context']['literal'] = 'Ending 1'
    if change == 'unmatched':
        rows[4]['status'] = 'AMBIGUOUS'
    if change == 'rhythm':
        rows[4]['duration'] = '1/2'
    assert 2 not in choose(regions, rows, moves, graph)[0]


def rectangle(box):
    image = Image.new('L', (30, 30))
    ImageDraw.Draw(image).rectangle(box, fill=255)
    return image


def test_actual_ink_overlap_not_bbox_overlap_and_ownership_is_per_semantic_note():
    left = rectangle((2, 2, 4, 4))
    right = rectangle((10, 10, 12, 12))
    assert ink_intersections({'p1:m2:n0:head': left, 'p1:m2:n1:head': right}) == []
    collision = ink_intersections({'p1:m2:n0:head': left, 'p1:m2:n1:stem': left})
    assert collision[0]['pixels'] == 9 and not collision[0]['intentional_contact']
    attached = ink_intersections({'p1:m2:n0:head': left, 'p1:m2:n0:stem': left})
    assert attached[0]['intentional_contact']


def test_font_outline_anchor_is_explicit_and_nonfinite_rejected(monkeypatch):
    calls = []

    def text(draw, xy, value, **kwargs):
        calls.append((xy, kwargs))
        draw.rectangle((8, 8, 12, 12), fill=255)

    monkeypatch.setattr(ImageDraw.ImageDraw, 'text', text)
    mask, result = glyph((30, 30), None, 'x', (10.0, 10.0), (-2, -4, 2, 4), 1.0)
    assert calls[0][0] == (10.0, 10.0) and calls[0][1]['anchor'] == 'ls'
    assert result['anchor_residual'] == [0.0, 0.0] and mask.getbbox() == (8, 8, 13, 13)
    with pytest.raises(ValueError, match='nonfinite'):
        glyph((30, 30), None, 'x', (float('nan'), 10), (-2, -4, 2, 4), 1.0)


def test_source_crop_is_untouched_under_labels_and_no_composite_is_implied():
    source = Image.new('RGB', (40, 50), 'white')
    source.putpixel((1, 1), (16, 42, 18))
    before = source.tobytes()
    panel = panel_label(source, 'Synthetic source only')
    assert panel.crop((0, 84, 40, 134)).tobytes() == before and source.tobytes() == before


def test_render_rejects_output_inside_input_before_any_font_access(tmp_path):
    inputs = tmp_path / 'source'
    inputs.mkdir()
    with pytest.raises(ValueError, match='New prototype'):
        render(inputs, Path('nonexistent-font'), inputs / 'bad')


def test_probe_calls_existing_production_factory_without_score_inputs():
    source = Path('scripts/research/gt04_native_probe.py').read_text()
    tree = ast.parse(source)
    imports = [
        name.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == 'backend.ocr.paddle_ocr'
        for name in node.names
    ]
    assert imports == ['get_ocr']
    assert 'recognized.musicxml' not in source and 'source.png' not in source
