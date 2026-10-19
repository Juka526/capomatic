"""Synthetic context renderer checks; these are not independent source annotations."""

import copy

import numpy as np
from PIL import Image, ImageFont
import pytest
from music21 import harmony, key, note, stream

from backend.omr_v3.chords import chord_text
from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research import gt12_render_context as gt


def record():
    return {
        'source_chord': 'F',
        'upper_lyrics': ['주', '님', '의'],
        'lower_lyrics': ['사', '막', '의'],
    }


def score():
    s = stream.Score()
    p = stream.Part()
    for i in range(1, 4):
        m = stream.Measure(number=i)
        if i == 1:
            m.insert(0, key.KeySignature(-2))
        if i == 3:
            for n in [
                note.Rest(quarterLength=1),
                note.Note('B-3'),
                note.Note('C4'),
                note.Note('F4'),
            ]:
                m.append(n)
        p.append(m)
    s.append(p)
    return s


def test_missing_or_candidate_confirmation_is_fatal(tmp_path):
    with pytest.raises(ValueError, match='Explicit owner'):
        gt.confirmation({'classification': 'ASSISTANT_VISUAL_REVIEW'}, tmp_path)
    with pytest.raises(ValueError, match='Explicit owner'):
        gt.confirmation({'classification': 'OWNER_REVIEW_CANDIDATE'}, tmp_path)


def test_independent_claim_is_not_accepted(tmp_path):
    with pytest.raises(ValueError, match='independent ground truth'):
        gt.confirmation(
            {'classification': 'OWNER_VERIFIED_SOURCE', 'independent_ground_truth': True}, tmp_path
        )


@pytest.mark.parametrize('target,shift,expected', [('A', -1, 'E'), ('G', -3, 'D')])
def test_augmented_semantics_chord_at_onset_zero_and_two_lyric_rows(target, shift, expected):
    original = gt.augment_source(score(), record())
    sig = gt.lyric_signature(original)
    assert sig == [[], [(1, '주'), (2, '사')], [(1, '님'), (2, '막')], [(1, '의'), (2, '의')]]
    result = copy.deepcopy(original)
    summary = transpose_score(result, shift, 'key')
    assert validate(original, result, shift, 'key', summary).ok
    assert gt.lyric_signature(result) == sig
    m = list(result.parts[0].getElementsByClass(stream.Measure))[2]
    cs = list(m.getElementsByClass(harmony.ChordSymbol))
    assert len(cs) == 1 and cs[0].offset == 0
    assert chord_text(cs[0]) == expected
    assert next(n for n in gt.events_of(m) if n.isNote).offset == 1


def test_source_content_change_cannot_silently_render():
    s = score()
    s.parts[0].measure(3).notes[-1].pitch.nameWithOctave = 'G4'
    with pytest.raises(ValueError, match='Source events changed'):
        gt.augment_source(s, record())


def test_text_position_uses_ink_left_top_not_first_note():
    font = ImageFont.load_default(size=24)
    mask, info = gt.text_mask((300, 200), font, 'E', left_top=(30, 40))
    assert mask.getbbox()[:2] == (30, 40)
    assert info['measured_ink_width_px'] == mask.getbbox()[2] - 30


def test_lyric_baseline_and_x_are_deterministic():
    font = ImageFont.load_default(size=24)
    a, info = gt.text_mask((300, 200), font, 'A', center_x=100.5, baseline=120)
    b, same = gt.text_mask((300, 200), font, 'A', center_x=100.5, baseline=120)
    assert a.tobytes() == b.tobytes() and info == same
    assert info['baseline'][1] == 120
    assert abs(info['raster_placement_anchor'][0] - 100.5) <= 0.5


def test_real_alpha_collisions_not_only_bbox():
    a, b = Image.new('L', (20, 20)), Image.new('L', (20, 20))
    a.putpixel((10, 10), 10)
    b.putpixel((11, 10), 255)
    assert gt.collisions({'music': a, 'text': b}) == []
    b.putpixel((10, 10), 1)
    assert gt.collisions({'music': a, 'text': b})[0]['pixels'] == 1


def test_source_display_bbox_does_not_modify_source_or_claim_ownership():
    source = Image.new('RGB', (40, 40), 'white')
    source.putpixel((15, 25), (100, 100, 100))
    before = source.tobytes()
    assert gt.ink_bbox(source, (10, 20, 30, 35)) == [15, 25, 16, 26]
    assert source.tobytes() == before
    with pytest.raises(ValueError, match='lacks observable support'):
        gt.ink_bbox(source, (0, 0, 5, 5))


def test_original_panel_source_region_remains_equal():
    crop = Image.new('RGB', (560, 390), (100, 120, 140))
    p = gt.panel(crop, 'Synthetic source')
    assert p.crop((0, 100, 560, 490)).tobytes() == crop.tobytes()
