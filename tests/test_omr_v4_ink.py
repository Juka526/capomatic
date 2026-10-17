"""Glyph-backed ownership tests, no Audiveris required."""

from dataclasses import replace
from pathlib import Path
import zipfile
import numpy as np
import pytest
from PIL import Image, ImageDraw
from backend.omr_v4.ink import isolate_ink, rle, pixels_from_runs, glyphs_from_omr
from backend.omr_v4.visual_graph import (
    VisualScoreGraph,
    VisualSymbol,
    Geometry,
    Page,
    Relation,
    ProtectedRegion,
    Staff,
)


def symbol(ident, kind, box, glyph=True):
    return VisualSymbol(
        'sheet#1:' + ident,
        ident,
        kind,
        'sheet#1',
        's',
        None,
        None,
        None,
        None,
        None,
        Geometry(bbox=box),
        (),
        (('glyph', ident),) if glyph else (),
        '',
    )


def scene(kind='head', open_head=False):
    image = Image.new('L', (80, 60), 255)
    layer = Image.new('L', image.size)
    d = ImageDraw.Draw(layer)
    d.ellipse((20, 20, 29, 27), fill=255)
    if open_head:
        d.ellipse((23, 22, 26, 25), fill=0)
    pixels = {(int(x), int(y)) for y, x in np.argwhere(np.asarray(layer) != 0)}
    image.paste(0, mask=layer)
    head = symbol('1', kind, (20, 20, 29, 27))
    container = symbol(
        '9',
        {
            'head': 'head-chord',
            'stem': 'head',
            'beam': 'stem',
            'flag': 'stem',
            'alter': 'head',
            'augmentation-dot': 'head',
        }[kind],
        None,
        False,
    )
    relation_kind = {
        'head': 'contains',
        'stem': 'head-stem',
        'beam': 'beam-stem',
        'alter': 'alter-head',
        'flag': 'flag-stem',
        'augmentation-dot': 'augmentation',
    }[kind]
    graph = VisualScoreGraph(
        (Page('sheet#1', 80, 60, 10),),
        (),
        (),
        (),
        {head.id: head, container.id: container},
        (Relation('r', relation_kind, head.id, container.id),),
        (),
        (),
        0,
        (),
    )
    return image, graph, {head.id: frozenset(pixels)}


def test_isolated_head_and_open_center():
    for hollow in (False, True):
        image, graph, glyphs = scene(open_head=hollow)
        result = isolate_ink(image, graph, glyphs)
        assert next(r for r in result.records if r.symbol_id == 'sheet#1:1').status == 'VERIFIED'
        assert pixels_from_runs(result.records[0].runs) == set(glyphs['sheet#1:1'])
        if hollow:
            assert (24, 23) not in pixels_from_runs(result.records[0].runs)
        assert result.to_json() == isolate_ink(image, graph, glyphs).to_json()


@pytest.mark.parametrize('kind', ['stem', 'beam', 'flag', 'alter', 'augmentation-dot'])
def test_relevant_relation_required(kind):
    image, graph, glyphs = scene(kind)
    assert isolate_ink(image, graph, glyphs).records[0].status == 'VERIFIED'
    assert (
        'RELATION_MISSING'
        in isolate_ink(image, replace(graph, relations=()), glyphs).records[0].reasons
    )


def test_staff_crossing_is_not_silently_certified():
    image, graph, glyphs = scene()
    staff = Staff('staff', '1', 'sheet#1', 's', 'p', 1, 10, (((0, 24), (79, 24)),), True, '')
    ImageDraw.Draw(image).line((0, 24, 79, 24), fill=0)
    record = isolate_ink(image, replace(graph, staves=(staff,)), glyphs).records[0]
    assert record.restore_required and record.staff_overlap_runs
    assert 'STAFF_OWNERSHIP_UNCLEAR' in record.reasons
    assert record.status == 'REJECTED'


@pytest.mark.parametrize('kind', ['head', 'stem'])
def test_unrelated_touch_and_escaping_component(kind):
    image, graph, glyphs = scene(kind)
    ImageDraw.Draw(image).line((25, 25, 55, 25), fill=0)
    assert 'COMPONENT_ESCAPES_WINDOW' in isolate_ink(image, graph, glyphs).records[0].reasons


@pytest.mark.parametrize('protection', ['text', 'barline'])
def test_protection_rejected(protection):
    image, graph, glyphs = scene()
    if protection == 'text':
        graph = replace(
            graph,
            text_protected_regions=(
                ProtectedRegion('text', 'sheet#1', 'lyric', (19, 19, 30, 28), (), 'word'),
            ),
        )
        reason = 'TEXT_COLLISION'
    else:
        s = symbol('5', 'barline', (24, 19, 26, 28), False)
        graph = replace(graph, symbols={**graph.symbols, s.id: s})
        reason = 'STRUCTURAL_COLLISION'
    assert reason in isolate_ink(image, graph, glyphs).records[0].reasons


def test_duplicate_claim_rejected_and_digest_bound():
    image, graph, glyphs = scene()
    original = isolate_ink(image, graph, glyphs)
    changed = image.copy()
    changed.putpixel((0, 0), 0)
    with pytest.raises(ValueError, match='digest'):
        original.owned(changed)
    other = symbol('2', 'head', (20, 20, 29, 27))
    graph = replace(
        graph,
        symbols={**graph.symbols, other.id: other},
        relations=graph.relations + (Relation('r2', 'contains', other.id, 'sheet#1:9'),),
    )
    result = isolate_ink(image, graph, {**glyphs, other.id: glyphs['sheet#1:1']})
    assert all('MULTI_OWNER_COMPONENT' in r.reasons for r in result.records if r.kind == 'head')
    assert not result.owned(image)


def test_rle_preserves_holes_and_is_deterministic():
    points = [(4, 2), (1, 1), (2, 1), (4, 1)]
    assert rle(points) == ((1, 1, 3), (1, 4, 5), (2, 4, 5))
    assert rle(reversed(points)) == rle(points)


def test_glyph_decoder_both_orientations_and_malformed(tmp_path):
    for orientation in ('HORIZONTAL', 'VERTICAL'):
        path = tmp_path / (orientation + '.omr')
        xml = f'<sheet><glyph-index><glyph id="1" left="5" top="7"><run-table orientation="{orientation}" width="3" height="3"><runs>0 1 2</runs><runs>1 1 1</runs><runs>3</runs></run-table></glyph></glyph-index></sheet>'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('sheet#1/sheet#1.xml', xml)
        decoded = glyphs_from_omr(path)['sheet#1:1']
        assert len(decoded) == 7
        assert (5, 7) not in decoded
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('sheet#1/sheet#1.xml', xml.replace('0 1 2', '99'))
        assert glyphs_from_omr(path)['sheet#1:1'] is None


def test_complete_and_incomplete_explicit_beam_component():
    image = Image.new('L', (80, 60), 255)
    definitions = [
        ('1', 'head', (20, 35, 25, 39)),
        ('2', 'stem', (25, 21, 25, 34)),
        ('3', 'beam', (25, 18, 40, 20)),
    ]
    symbols, glyphs = {}, {}
    for ident, kind, box in definitions:
        s = symbol(ident, kind, box)
        symbols[s.id] = s
        pts = {(x, y) for y in range(box[1], box[3] + 1) for x in range(box[0], box[2] + 1)}
        glyphs[s.id] = pts
        for p in pts:
            image.putpixel(p, 0)
    graph = VisualScoreGraph(
        (Page('sheet#1', 80, 60, 10),),
        (),
        (),
        (),
        symbols,
        (
            Relation('hs', 'head-stem', 'sheet#1:1', 'sheet#1:2'),
            Relation('bs', 'beam-stem', 'sheet#1:3', 'sheet#1:2'),
        ),
        (),
        (),
        0,
        (),
    )
    result = isolate_ink(image, graph, glyphs)
    assert len(result.owned(image)) == 3
    bad = isolate_ink(image, graph, {i: p for i, p in glyphs.items() if i != 'sheet#1:3'})
    assert not bad.owned(image)
