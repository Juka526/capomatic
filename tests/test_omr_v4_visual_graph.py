import zipfile
from xml.etree import ElementTree as ET

import pytest

from backend.omr_v4.visual_graph import GraphError, load_visual_graph
from omr_v4_fixtures import book, sheet_xml


def test_sig_ids_geometry_and_relations(tmp_path):
    graph = load_visual_graph(book(tmp_path))
    assert graph.pages[0].width == 400
    assert graph.staves[0].lines[0] == ((20, 80), (300, 82))
    assert graph.staves[0].interline == 10
    assert graph.systems[0].bounds == (20, 80, 300, 122)
    assert graph.measures[0].slots[1].offset == 1
    assert graph.measures[0].onsets == (('sheet#1:10', '1', '1'), ('sheet#1:20', '2', '1'))
    head = graph.symbols['sheet#1:1']
    assert head.source_id == '1' and head.confidence == 0.9
    assert head.geometry.center == (100, 115)
    assert head.relation_ids
    assert 'sheet#1:1' in graph.neighbors('sheet#1:10', {'contains'})
    assert graph.symbols['sheet#1:10'].geometry.bbox == head.geometry.bbox
    assert graph.symbols['sheet#1:21'].geometry.line == ((205, 72), (205, 110))
    assert graph.symbols['sheet#1:30'].geometry.thickness == 4
    assert graph.symbols['sheet#1:30'].geometry.line == ((105, 70), (205, 72))
    assert {'alter-head', 'augmentation', 'flag-stem', 'beam-stem', 'head-stem', 'slur-head'} <= {
        r.kind for r in graph.relations
    }
    assert graph.symbols['sheet#1:43'].kind == 'ledger'
    assert graph.symbols['sheet#1:50'].geometry.curve == (
        (100, 120),
        (125, 140),
        (175, 140),
        (200, 115),
    )
    assert not graph.invalid_geometry_count


def test_text_protection_and_roles(tmp_path):
    graph = load_visual_graph(book(tmp_path))
    regions = {r.id: r for r in graph.text_protected_regions}
    assert regions['sheet#1:60'].kind == 'lyrics'
    assert regions['sheet#1:62'].kind == 'Title'
    assert regions['sheet#1:64'].kind == 'non-chord-text'
    assert regions['sheet#1:63'].bbox == (100, 20, 170, 35)
    assert 'sheet#1:66' not in regions
    assert graph.symbols['sheet#1:63'].geometry.location == (100, 32)


@pytest.mark.parametrize(
    'old,new,symbol',
    [
        ('x="95"', 'x="NaN"', '1'),
        ('w="10" h="8"', 'w="-10" h="8"', '1'),
        ('x="100" y="115"', 'x="inf" y="115"', '1'),
        ('ctrlx1="125"', 'ctrlx1="-Infinity"', '50'),
        ('height="4"', 'height="bad"', '30'),
        ('x="105" y="70"', 'x="1e309" y="70"', '11'),
    ],
)
def test_invalid_geometry_is_quarantined(tmp_path, old, new, symbol):
    graph = load_visual_graph(book(tmp_path, sheet_xml().replace(old, new, 1)))
    assert graph.invalid_geometry_count == 1
    geometry = graph.symbols[f'sheet#1:{symbol}'].geometry
    assert not geometry.valid and geometry.region is None and geometry.center is None


def test_optional_geometry_and_unknown_construct_retained(tmp_path):
    xml = sheet_xml().replace(
        '</inters>', '<ornament id="90" shape="TR"/><word id="91" value="unlocated"/></inters>'
    )
    graph = load_visual_graph(book(tmp_path, xml))
    assert graph.unsupported_constructs == ('ornament',)
    assert 'shape="TR"' in graph.symbols['sheet#1:90'].source_xml
    assert graph.summary()['protected_regions_without_bounds'] == 1
    assert graph.invalid_geometry_count == 0


def test_invalid_staff_and_stack_fail_closed(tmp_path):
    xml = sheet_xml().replace('x="20" y="80"', 'x="20" y="NaN"').replace('left="20"', 'left="inf"')
    graph = load_visual_graph(book(tmp_path, xml))
    assert not graph.staves[0].valid
    assert graph.measures[0].bounds is None
    assert graph.invalid_geometry_count == 2


def test_legacy_lists_and_dangling_references(tmp_path):
    xml = sheet_xml().replace(
        '<head-chord id="10" staff="1"/>',
        '<head-chord id="10" staff="1" stem="11"><notes>1</notes><beams>30 999</beams></head-chord>',
    )
    graph = load_visual_graph(book(tmp_path, xml))
    assert 'sheet#1:11' in graph.neighbors('sheet#1:10', {'chord-stem'})
    assert any('dangling relation' in issue for issue in graph.issues)


def test_sheet_scoped_ids(tmp_path):
    path = book(tmp_path)
    with zipfile.ZipFile(path, 'a') as z:
        z.writestr('sheet#2/sheet#2.xml', sheet_xml())
    graph = load_visual_graph(path)
    assert len(graph.pages) == 2
    assert 'sheet#1:1' in graph.symbols and 'sheet#2:1' in graph.symbols


@pytest.mark.parametrize(
    'xml',
    [
        '<!DOCTYPE sheet [<!ENTITY x "bad">]><sheet/>',
        '<!DOCTYPE sheet SYSTEM "file:///etc/passwd"><sheet/>',
        '<sheet/>'.encode('utf-16'),
        '<sheet>',
        sheet_xml().replace('width="400"', 'width="999999999"'),
        sheet_xml().replace('<head id="2"', '<head id="1"'),
    ],
)
def test_unsafe_books_rejected(tmp_path, xml):
    with pytest.raises(GraphError):
        load_visual_graph(book(tmp_path, xml))


def test_archive_limits(tmp_path, monkeypatch):
    from backend.omr_v4 import visual_graph

    monkeypatch.setattr(visual_graph, 'MAX_XML_BYTES', 20)
    with pytest.raises(GraphError, match='too large'):
        load_visual_graph(book(tmp_path))


def test_xml_order_does_not_control_links(tmp_path):
    root = ET.fromstring(sheet_xml())
    for path in ('.//inters', './/relations', './/slots', './/lines'):
        el = root.find(path)
        el[:] = list(reversed(list(el)))
    a = load_visual_graph(book(tmp_path))
    b = load_visual_graph(book(tmp_path, ET.tostring(root), 'shuffled.omr'))
    assert a.relations == b.relations and a.staves[0].lines == b.staves[0].lines
    assert a.symbols == b.symbols
