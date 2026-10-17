"""Independent pinned-Java RunTable contract and measurement-only regressions."""

import zipfile
import numpy as np
import pytest
from backend.omr_v4.ink import glyphs_from_omr
from scripts.omr_v4.ink_forensics import agreement, sharing


@pytest.mark.parametrize('orientation', ['HORIZONTAL', 'VERTICAL'])
def test_java_documented_runsequence_literal_coordinates(tmp_path, orientation):
    # Audiveris 7a36078 RunTable.RunSequence documents this sequence; encode/Itr
    # define foreground runs [41,65], [146,147], [149,150], [231,255].
    # Expected points are independent literal coordinates, not our encoder output.
    width, height = (256, 1) if orientation == 'HORIZONTAL' else (1, 256)
    xml = f'''<sheet><glyph-index><glyph id="7" left="10" top="20">
    <run-table orientation="{orientation}" width="{width}" height="{height}">
    <runs>0 41 25 80 2 1 2 80 25</runs></run-table></glyph></glyph-index></sheet>'''
    path = tmp_path / 'java-contract.omr'
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('sheet#1/sheet#1.xml', xml)
    foreground = set(range(41, 66)) | {146, 147, 149, 150} | set(range(231, 256))
    expected = (
        {(10 + value, 20) for value in foreground}
        if orientation == 'HORIZONTAL'
        else {(10, 20 + value) for value in foreground}
    )
    actual = glyphs_from_omr(path)['sheet#1:7']
    assert actual == expected
    assert len(actual) == 54


def test_java_foreground_first_and_empty_sequences_nonsquare(tmp_path):
    xml = '''<sheet><glyph-index><glyph id="1" left="5" top="9">
    <run-table orientation="HORIZONTAL" width="7" height="3">
    <runs>2 2 1</runs><runs/><runs>0 6 1</runs>
    </run-table></glyph></glyph-index></sheet>'''
    path = tmp_path / 'nonsquare.omr'
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('sheet#1/sheet#1.xml', xml)
    assert glyphs_from_omr(path)['sheet#1:1'] == {(5, 9), (6, 9), (9, 9), (11, 11)}


def test_measurements_do_not_correct_pixels_or_drop_offpage_denominator():
    gray = np.array([[255, 0, 160], [255, 255, 255]], dtype='uint8')
    before = gray.copy()
    points = {(0, 0), (1, 0)}
    assert agreement(gray, points)['dark'] == 1
    assert agreement(gray, points, dx=1)['dark'] == 1
    assert agreement(gray, points, dx=1, threshold=192)['dark'] == 2
    assert agreement(gray, points, dx=-1)['total'] == 2
    assert np.array_equal(gray, before)
    assert points == {(0, 0), (1, 0)}


def test_sharing_separates_same_glyph_overlap_and_component_contact():
    candidates = {
        'a': ('g1', {(0, 0)}),
        'b': ('g1', {(0, 0)}),
        'c': ('g2', {(0, 0), (1, 0)}),
        'd': ('g3', {(2, 0)}),
    }
    groups = {
        'a': frozenset({'a', 'b'}),
        'b': frozenset({'a', 'b'}),
        'c': frozenset({'c'}),
        'd': frozenset({'d'}),
    }
    _, result = sharing(candidates, groups, np.array([[1, 1, 1]]))
    assert result['same_glyph_symbol_pairs'] == 1
    assert result['different_glyph_overlapping_pairs'] == 2
    assert result['sig_connected_overlapping_pairs'] == 1
    assert result['unrelated_overlapping_pairs'] == 2
    assert result['same_source_component_without_pixel_overlap_pairs'] == 3
    assert result['direct_8_neighbor_contact_without_overlap_pairs'] == 1
    assert result['direct_contact_unrelated_pairs'] == 1


def test_forensic_artifacts_are_deterministic_and_source_unchanged(tmp_path):
    import io
    import json
    from PIL import Image
    from scripts.omr_v4.ink_forensics import forensic, supplementary_metrics

    evidence = tmp_path / 'evidence'
    evidence.mkdir()
    source = Image.new('RGB', (80, 60), 'white')
    for y in range(20, 23):
        for x in range(20, 23):
            source.putpixel((x, y), (100, 100, 100))
    source.save(evidence / 'source.png')
    original = (evidence / 'source.png').read_bytes()
    binary = Image.new('L', source.size, 255)
    for y in range(20, 23):
        for x in range(20, 23):
            binary.putpixel((x, y), 0)
    payload = io.BytesIO()
    binary.save(payload, format='PNG')
    lines = ''.join(
        f'<line><point x="0" y="{y}"/><point x="79" y="{y}"/></line>' for y in (5, 10, 15, 30, 35)
    )
    xml = f'''<sheet><picture width="80" height="60"/>
    <scale><interline main="5"/></scale><page id="1"><system id="1">
    <stack id="1" left="0" right="79" duration="1/4"/>
    <part id="1"><staff id="1"><lines>{lines}</lines></staff>
    <measure id="1"><head-chords>2</head-chords></measure></part>
    <sig><inters><head id="1" staff="1" glyph="7"><bounds x="20" y="20" w="3" h="3"/></head>
    <head-chord id="2" staff="1"><notes>1</notes></head-chord></inters></sig>
    </system></page><glyph-index><glyph id="7" left="20" top="20">
    <run-table orientation="HORIZONTAL" width="3" height="3"><runs>3</runs><runs>3</runs><runs>3</runs></run-table>
    </glyph></glyph-index></sheet>'''
    with zipfile.ZipFile(evidence / 'recognized.omr', 'w') as z:
        z.writestr('sheet#1/sheet#1.xml', xml)
        z.writestr('sheet#1/BINARY.png', payload.getvalue())
        z.writestr(
            'book.xml',
            '<book software-build="test"><sheet><input><path>source.png</path></input></sheet></book>',
        )
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'samples': [{'symbol_id': 'sheet#1:1'}]}))
    first = forensic(evidence, tmp_path / 'out1', manifest)
    second = forensic(evidence, tmp_path / 'out2', manifest)
    assert first == second
    assert (tmp_path / 'out1/sample-01.png').read_bytes() == (
        tmp_path / 'out2/sample-01.png'
    ).read_bytes()
    assert first['samples'][0]['embedded_binary_agreement']['percentage'] == 100
    extra = supplementary_metrics(evidence, first, evidence / 'source.png')
    assert extra['raster_reproduction']['file_identical']
    assert extra['all_candidate_binary_agreement']['binary_exact_symbols'] == 1
    assert (evidence / 'source.png').read_bytes() == original
