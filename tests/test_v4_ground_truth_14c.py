"""Synthetic source-only packet controls, no Audiveris or target rendering."""

import copy

import numpy as np
import pytest
from PIL import Image
from music21 import note, stream, tie

from scripts.research import gt14c_continuation_audit as gt


def source_fixture():
    image = Image.new('RGB', (200, 200), 'white')
    for x in range(30, 66):
        image.putpixel((x, 52), (0, 0, 0))
    image.putpixel((29, 52), (200, 200, 200))
    score = stream.Score()
    p = stream.Part()
    score.append(p)
    for n in range(1, 9):
        p.append(stream.Measure(number=n))
    m = list(p.getElementsByClass(stream.Measure))[5]
    start = note.Note('C4', quarterLength=0.25)
    start.tie = tie.Tie('start')
    start.addLyric('운', lyricNumber=2)
    stop = note.Note('C4', quarterLength=0.25)
    stop.tie = tie.Tie('stop')
    m.insert(2.75, start)
    m.insert(3, stop)
    return image, score


def spec():
    return {
        'id': 'new',
        'measure': 6,
        'row': 2,
        'window': [20, 40, 80, 70],
        'review_crop': [10, 10, 100, 100],
        'onset': '3',
        'associated_syllable_candidate': '운',
        'syllable_measure': 6,
        'syllable_onset': '11/4',
        'tie_id': 'tie',
    }


def test_measurement_does_not_claim_antialias_ownership_or_mutate_source():
    image, _ = source_fixture()
    before = image.tobytes()
    assert gt.dark_support_bbox(image, [20, 40, 80, 70]) == [30, 52, 66, 53]
    assert image.getpixel((29, 52)) == (200, 200, 200) and image.tobytes() == before


@pytest.mark.parametrize(
    'window', [[0, 0, 5, 5], [-1, 0, 20, 20], [0, 0, 201, 20], [0.5, 0, 20, 20]]
)
def test_invalid_or_blank_windows_fail_closed(window):
    with pytest.raises(ValueError):
        gt.dark_support_bbox(source_fixture()[0], window)


def test_candidate_context_remains_pending_even_with_confirmed_lyrics_and_ties():
    image, score = source_fixture()
    graph = {'symbols': {'tie': {'geometry': {'bbox': [25, 30, 70, 38]}}}, 'relations': []}
    before = copy.deepcopy(graph)
    record = gt.candidate_record(spec(), image, graph, score)
    assert record['classification'] == 'AGENT_VISUAL_CANDIDATE'
    assert record['owner_response'] is None and record['new_rendering_authorized'] is False
    assert record['note_context']['syllable_text'] == '운'
    assert graph == before
    record['review_image'] = 'native.png'
    packet = gt.checklist([record])
    assert packet['cases'][0]['owner_response'] is None
    assert packet['cases'][0]['association_confirmed'] is None
    record['classification'] = 'OWNER_VERIFIED_SOURCE'
    with pytest.raises(ValueError, match='promotion'):
        gt.checklist([record])


def test_missing_lineage_or_changed_held_syllable_rejected():
    image, score = source_fixture()
    with pytest.raises(ValueError, match='tie missing'):
        gt.candidate_record(spec(), image, {'symbols': {}, 'relations': []}, score)
    gt.event(score, 6, '11/4').lyrics[0].text = 'X'
    with pytest.raises(ValueError, match='syllable'):
        gt.candidate_record(spec(), image, {'symbols': {}, 'relations': []}, score)


def test_native_review_crop_preserves_exact_mode_size_pixels_and_mapping(tmp_path):
    image, _ = source_fixture()
    record = gt.save_native(image, [20, 40, 80, 70], tmp_path / 'crop.png')
    loaded = Image.open(tmp_path / 'crop.png')
    assert loaded.mode == 'RGB' and loaded.size == (60, 30)
    assert loaded.tobytes() == image.crop((20, 40, 80, 70)).tobytes()
    assert loaded.getpixel((10, 12)) == image.getpixel((30, 52))
    assert record['scale'] == 1 and record['source_pixel_equality']


def test_two_row_census_has_all_eight_regions_without_inferred_complement():
    records = [{'id': 'confirmed', 'measure': 5, 'row': 2}]
    census = gt.row_census(records)
    assert len(census) == 8 and sum(len(r['record_ids']) for r in census) == 1
    assert census[0]['record_ids'] == []
    assert all(r['source_completeness'] == 'NOT_INDEPENDENTLY_VERIFIED' for r in census)
    with pytest.raises(ValueError, match='Duplicate'):
        gt.row_census(records + records)


def test_candidate_serialization_is_deterministic_and_source_positions_are_distinct(tmp_path):
    image, score = source_fixture()
    graph = {'symbols': {'tie': {'geometry': {'bbox': [25, 30, 70, 38]}}}, 'relations': []}
    a = gt.candidate_record(spec(), image, graph, score)
    b = gt.candidate_record(spec(), image, graph, score)
    gt.dump(tmp_path / 'a.json', a)
    gt.dump(tmp_path / 'b.json', b)
    assert (tmp_path / 'a.json').read_bytes() == (tmp_path / 'b.json').read_bytes()
    p = gt.read(gt.PROTOCOL)
    assert [(r['measure'], r['row']) for r in p['new_candidates']] == [(5, 1), (6, 2), (7, 2)]
    assert len({tuple(r['window']) for r in p['new_candidates']}) == 3
