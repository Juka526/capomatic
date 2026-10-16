"""The hand-made reference transcriptions and the comparator used for V3 accuracy reports."""
import copy
import json
from pathlib import Path

import pytest

from scripts.omr_v3.compare import compare, transposed_reference
from scripts.omr_v3.reference import check, parse_gt, to_music21

EVAL = Path(__file__).parent / 'omr_v3_eval'
MANIFEST = json.loads((EVAL / 'manifest.json').read_text(encoding='utf-8'))
NAMES = [s['name'] for s in MANIFEST['scores']]


def _gt(name):
    return parse_gt((EVAL / 'reference' / f'{name}.gt').read_text(encoding='utf-8'))


@pytest.mark.parametrize('name', NAMES)
def test_reference_bars_add_up(name):
    assert check(_gt(name)) == []


@pytest.mark.parametrize('name', NAMES)
def test_sources_exist(name):
    entry = next(s for s in MANIFEST['scores'] if s['name'] == name)
    assert (EVAL / entry['source']).stat().st_size > 0


@pytest.mark.parametrize('name', NAMES)
def test_reference_compares_perfectly_with_itself(name):
    score = to_music21(_gt(name))
    result = compare(score, copy.deepcopy(score))
    assert result['note_exact'] == 1.0 and result['chords']['recall'] == 1.0 and result['ser'] == 0


def test_comparator_counts_errors():
    gt = _gt('jusim')
    ref = to_music21(gt)
    cand = copy.deepcopy(ref)
    from music21 import harmony, note

    first = next(n for n in cand.recurse().getElementsByClass(note.Note))
    first.pitch.step = 'B'
    cs = next(iter(cand.recurse().getElementsByClass(harmony.ChordSymbol)))
    cs.activeSite.remove(cs)
    result = compare(ref, cand)
    assert result['ops']['substitutions'] == 1
    assert result['chords']['hits'] == result['chords']['reference'] - 1


def test_transposed_reference_is_independent_of_the_pipeline():
    gt = _gt('naui')
    ref = transposed_reference(to_music21(gt), gt, -2, 'key')
    from music21 import key, note

    keys = [ks.sharps for ks in ref.recurse().getElementsByClass(key.KeySignature)]
    assert keys == [0, -3, 0]  # D -> C, F -> Eb, D -> C
    first = next(n for n in ref.recurse().getElementsByClass(note.Note))
    assert first.pitch.nameWithOctave == 'G3'  # A3 down a major second


def test_review_bundle_excludes_binary_corpus_and_limits_images(tmp_path):
    from scripts.omr_v3.review_bundle import build
    source, destination = tmp_path / 'full', tmp_path / 'review'
    source.mkdir()
    (source / 'summary.json').write_text('{"runs": []}')
    (source / 'large.pdf').write_bytes(b'x' * 100)
    for i in range(10):
        d = source / str(i)
        d.mkdir()
        (d / 'side_by_side.png').write_bytes(b'png')
    build(source, destination)
    assert (destination / 'summary.json').is_file()
    assert not list(destination.rglob('*.pdf'))
    assert len(list(destination.glob('*.png'))) <= 4
