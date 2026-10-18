"""Synthetic source/renderer contracts; never independent score ground truth."""

from pathlib import Path
from types import SimpleNamespace
import copy
import json

import numpy as np
from PIL import Image, ImageFont
import pytest
from music21 import clef, key, note, stream

from scripts.research import gt11_complete_measure as gt
from scripts.research.gt04_visual import HEAD, REST, render
from scripts.research.gt05_raster_anchor import glyph
from scripts.research.paired_ground_truth_01 import dump, sha


def source_case():
    s = stream.Score()
    p = stream.Part()
    m = stream.Measure(number=3)
    m.insert(0, key.KeySignature(-2))
    m.insert(0, clef.TrebleClef())
    for n in [note.Rest(quarterLength=1), note.Note('B-3'), note.Note('C4'), note.Note('F4')]:
        m.append(n)
    p.append(m)
    s.append(p)
    staff = {
        'id': 'staff1',
        'interline': 10,
        'lines': [[[0, 200 + i * 10], [420, 200 + i * 10]] for i in range(5)],
    }
    excerpt = {'number': 3, 'staff': staff, 'system': 1, 'left': 50, 'right': 350, 'events': []}
    graph = {'symbols': {}, 'relations': []}
    moves = {}
    for i, n in enumerate(gt.events_of(m)):
        ident = f'p1:m0:{"r" if n.isRest else "n"}{i}'
        symbol = f'h{i}'
        x = 75 + i * 70
        y = 220 if n.isRest else 220 + (35 - n.pitch.diatonicNoteNum) * 5
        row = {
            'id': ident,
            'printed_measures': [3],
            'part_index': 1,
            'omr_measure_index': 0,
            'omr_number': '3',
            'kind': 'REST' if n.isRest else 'NOTE',
            'local_offset': str(i),
            'duration': '1',
            'status': 'MATCHED',
            'bbox': [x - 6, y - 5, x + 6, y + 5],
            'symbol_id': symbol,
        }
        if n.isNote:
            row.update(pitch=n.pitch.nameWithOctave, chord_size=1)
        excerpt['events'].append(row)
        graph['symbols'][symbol] = {
            'id': symbol,
            'kind': 'rest' if n.isRest else 'head',
            'geometry': {'valid': True, 'bbox': row['bbox']},
            'staff': 'staff1',
            'grade': 0.8,
            'contextual_grade': 0.9,
        }
        if n.isNote:
            sid = f's{i}'
            graph['relations'].append(
                {
                    'id': f'rel{i}',
                    'kind': 'head-stem',
                    'source': symbol,
                    'target': sid,
                    'attributes': [['head-side', 'RIGHT']],
                }
            )
            moves[ident] = {'connected_symbols': [['head', [symbol]], ['stem', [sid]]]}
            row['frozen'] = {}
            for target, names in [('A', ['A3', 'B3', 'E4']), ('G', ['G3', 'A3', 'D4'])]:
                tp = note.Note(names[i - 1]).pitch
                row['frozen'][target] = {
                    'detected_head_x': x,
                    'detected_head_y': y,
                    'source_pitch': n.pitch.nameWithOctave,
                    'target_pitch': tp.nameWithOctave,
                    'absolute_target_staff_y': 220 + (35 - tp.diatonicNoteNum) * 5,
                    'corrected_semantic_source_staff_y': y,
                    'expected_diatonic_delta_y': 220 + (35 - tp.diatonicNoteNum) * 5 - y,
                }
    return s, excerpt, graph, moves


def test_source_internal_agreement_never_becomes_independent_completeness():
    s, e, g, m = source_case()
    before = copy.deepcopy(e)
    result = gt.source_inventory(s, e, g, m)
    assert result['SOURCE_RECOGNITION_COMPLETENESS'] == 'UNVERIFIED'
    assert result['written_key_fifths'] == -2 and result['clef'] == 'TrebleClef'
    assert len(result['events']) == 4 and result['recognized_quarter_length_total'] == '4'
    assert all(
        r['recognition'] == 'RECOGNIZED' and r['renderer_capability'] == 'SUPPORTED'
        for r in result['events']
    )
    assert result['source_signature'][1]['pitch'] == 'B-3'
    assert result['source_signature'][0]['voice'] is None
    assert e == before


@pytest.mark.parametrize(
    'change',
    [
        'wrong_measure',
        'missing_rest',
        'wrong_pitch',
        'ambiguous_stem',
        'extra_visual_note',
        'wrong_onset',
        'duplicate_id',
    ],
)
def test_source_inventory_fails_closed_on_identity_or_ownership_gap(change):
    s, e, g, m = source_case()
    if change == 'wrong_measure':
        e['number'] = 4
    elif change == 'missing_rest':
        e['events'].pop(0)
    elif change == 'wrong_pitch':
        e['events'][1]['pitch'] = 'C4'
    elif change == 'ambiguous_stem':
        g['relations'].append(copy.deepcopy(g['relations'][0]))
    elif change == 'extra_visual_note':
        g['symbols']['extra'] = dict(g['symbols']['h1'], id='extra')
    elif change == 'wrong_onset':
        e['events'][2]['local_offset'] = '3/2'
    elif change == 'duplicate_id':
        e['events'][2]['id'] = e['events'][1]['id']
    with pytest.raises(ValueError):
        gt.source_inventory(s, e, g, m)


@pytest.mark.parametrize('kind', ['beam', 'flag', 'slur', 'articulation', 'fermata'])
def test_unsupported_required_components_are_reported_not_silently_omitted(kind):
    n = note.Note('C4')
    s, e, g, m = source_case()
    row = e['events'][2]
    assert gt.unsupported_event(n, row, ['head', 'stem', kind], []) or gt.unsupported_event(
        n, row, ['head', 'stem'], [{'kind': kind}]
    )


def test_unverified_source_dominates_complete_render_and_good_agent_visuals():
    assert (
        gt.whole_verdict('UNVERIFIED', 'COMPLETE', 'ACCEPTABLE_FOR_EXPERIMENT', True)
        == 'COMPLETE_MEASURE_INCOMPLETE'
    )
    assert (
        gt.whole_verdict('INCOMPLETE', 'COMPLETE', 'ACCEPTABLE_FOR_EXPERIMENT', True)
        == 'COMPLETE_MEASURE_INCOMPLETE'
    )
    assert (
        gt.whole_verdict('COMPLETE', 'INCOMPLETE', 'ACCEPTABLE_FOR_EXPERIMENT', True)
        == 'COMPLETE_MEASURE_INCOMPLETE'
    )
    assert (
        gt.whole_verdict('COMPLETE', 'COMPLETE', 'UNVERIFIED', True)
        == 'COMPLETE_MEASURE_INCOMPLETE'
    )
    assert (
        gt.whole_verdict('COMPLETE', 'COMPLETE', 'ACCEPTABLE_FOR_EXPERIMENT', False)
        == 'COMPLETE_MEASURE_INCOMPLETE'
    )
    assert (
        gt.whole_verdict('COMPLETE', 'COMPLETE', 'ACCEPTABLE_FOR_EXPERIMENT', True)
        == 'COMPLETE_MEASURE_RENDERED_WITH_LIMITATIONS'
    )


def test_required_component_and_ledger_accounting_is_target_specific():
    _, e, _, _ = source_case()
    a, al = gt.required_parts(e, 'A')
    g, gl = gt.required_parts(e, 'G')
    assert len(a) == len(g) == 11
    assert sum(al.values()) == 3 and sum(gl.values()) == 4
    assert 'p1:m0:r0:rest' in a and 'p1:m0:n3:ledger' not in a


def test_exact_snapshot_masks_preserve_pixels_and_reject_incomplete_group(tmp_path):
    parts = {
        'staff': Image.new('L', (20, 20), 100),
        'bar': Image.new('L', (20, 20), 150),
        'x:head': Image.new('L', (20, 20), 255),
    }
    before = {k: m.tobytes() for k, m in parts.items()}
    manifests, music = gt.snapshot_parts(parts, set(parts), tmp_path / 'parts')
    assert np.all(music == 255) and len(manifests) == 3
    assert {k: m.tobytes() for k, m in parts.items()} == before
    assert np.array_equal(np.asarray(Image.open(tmp_path / 'parts/music-only-alpha.png')), music)
    with pytest.raises(ValueError):
        gt.snapshot_parts(parts, set(parts) | {'x:stem'}, tmp_path / 'bad')


def test_inventory_freeze_rejects_changed_or_added_records(tmp_path):
    p = tmp_path / 'inventory.json'
    p.write_text('{}')
    dump(
        tmp_path / 'source-inventory-freeze.json',
        {'files': {'inventory.json': sha(p)}, 'historical_inputs_sha256': {}},
    )
    gt.verify_inventory(tmp_path)
    p.write_text('{"changed":true}')
    with pytest.raises(ValueError):
        gt.verify_inventory(tmp_path)


def test_component_observer_cannot_change_reused_renderer_pixels(tmp_path, monkeypatch):
    # Toy rectangular font metadata and ASCII bitmaps test observation only, not notation quality.
    import fontTools.ttLib

    font = ImageFont.load_default(size=20)

    class FakeFont:
        def getBestCmap(self):
            return {ord(HEAD): 'head', ord(REST): 'rest'}

        def __getitem__(self, k):
            if k == 'head':
                return SimpleNamespace(unitsPerEm=1000)
            return {
                n: SimpleNamespace(xMin=0, xMax=400, yMin=-200, yMax=200) for n in ('head', 'rest')
            }

    monkeypatch.setattr(fontTools.ttLib, 'TTFont', lambda _: FakeFont())
    monkeypatch.setattr(ImageFont, 'truetype', lambda *args, **kwargs: font)

    def toy_glyph(size, font_, char, xy, units, scale):
        return glyph(size, font, 'A' if char == HEAD else 'R', xy, units, scale)

    inputs = tmp_path / 'input'
    inputs.mkdir()
    Image.new('RGB', (420, 500), 'white').save(inputs / 'source.png')
    _, excerpt, _, _ = source_case()
    for row in excerpt['events']:
        if row['kind'] == 'REST':
            continue
        row['frozen']['A']['head_id'] = row['symbol_id']
    spec = {
        'selected': [3],
        'source_sha256': sha(inputs / 'source.png'),
        'excerpts': [excerpt],
        'protected': [],
        'guards': {'A': {'ok': True}, 'G': {'ok': True}},
    }
    dump(inputs / 'selection.json', spec)
    (tmp_path / 'unused').write_bytes(b'Toy font metadata is mocked; not notation evidence')
    baseline = tmp_path / 'normal'
    observed = tmp_path / 'observed'
    seen = []
    render(inputs, tmp_path / 'unused', baseline, glyph_renderer=toy_glyph)

    def observer(number, target, parts):
        seen.append((number, target, set(parts)))
        for mask in parts.values():
            mask.paste(0, (0, 0, mask.width, mask.height))

    render(inputs, tmp_path / 'unused', observed, glyph_renderer=toy_glyph, parts_observer=observer)
    assert len(seen) == 2
    for name in [
        'm3-A-notation-alpha.png',
        'm3-G-notation-alpha.png',
        'predicted-a.png',
        'predicted-g.png',
    ]:
        assert (baseline / name).read_bytes() == (observed / name).read_bytes()
