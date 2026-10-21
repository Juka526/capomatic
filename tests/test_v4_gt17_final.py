"""Synthetic extension semantics and optical contracts, not musical ground truth."""

import xml.etree.ElementTree as ET

import numpy as np
import pytest
from music21 import note, stream, tie, spanner
from PIL import Image, ImageDraw

from scripts.research.gt17_final_semantics import (
    add_extensions,
    extension_signature,
    strip_extensions,
    lineage,
)
from scripts.research.gt17_final_render import smooth_curve, place_lyrics


def xml_base(count=3):
    r = ET.Element('score-partwise')
    p = ET.SubElement(r, 'part', id='P1')
    for i in range(count):
        m = ET.SubElement(p, 'measure', number=str(i + 1))
        n = ET.SubElement(m, 'note')
        ET.SubElement(n, 'pitch')
        ET.SubElement(n, 'duration').text = '1'
        if i == 0:
            for row, text in [(1, '주'), (2, '광')]:
                l = ET.SubElement(n, 'lyric', number=str(row))
                ET.SubElement(l, 'text').text = text
    return r


def spans():
    return [
        {
            'row': row,
            'text': text,
            'path': [{'measure': i + 1, 'index': 0, 'onset': '0'} for i in range(3)],
        }
        for row, text in [(1, '주'), (2, '광')]
    ]


def test_two_rows_cross_measure_start_continue_stop_and_lossless_strip():
    base = xml_base()
    result = add_extensions(base, spans())
    sig = extension_signature(result)
    assert len(sig) == 2
    assert all([role for _, role in s['roles']] == ['start', 'continue', 'stop'] for s in sig)
    assert ET.tostring(strip_extensions(result)) == ET.tostring(base)
    assert not base.findall('.//extend')
    assert extension_signature(ET.fromstring(ET.tostring(result))) == sig


def test_legacy_extend_is_a_start_with_explicit_verified_stop():
    r = add_extensions(xml_base(), spans())
    for e in r.findall('.//extend'):
        if e.get('type') == 'start':
            del e.attrib['type']
    assert extension_signature(r) == extension_signature(add_extensions(xml_base(), spans()))


@pytest.mark.parametrize(
    'damage', ['orphan_stop', 'orphan_continue', 'unclosed', 'invalid', 'duplicate', 'new_syllable']
)
def test_extension_state_machine_rejects_semantic_damage(damage):
    r = add_extensions(xml_base(), spans())
    els = r.findall('.//extend')
    if damage == 'orphan_stop':
        els[0].set('type', 'stop')
    elif damage == 'orphan_continue':
        els[0].set('type', 'continue')
    elif damage == 'unclosed':
        els[-1].set('type', 'continue')
    elif damage == 'invalid':
        els[1].set('type', 'guess')
    elif damage == 'duplicate':
        ET.SubElement(r.find('.//lyric'), 'extend', type='start')
    else:
        ET.SubElement(r.findall('.//lyric')[2], 'text').text = '새'
    with pytest.raises(ValueError):
        extension_signature(r)


@pytest.mark.parametrize('damage', ['overlap', 'wrong_text', 'existing_syllable'])
def test_writer_rejects_ambiguous_or_overwriting_extensions(damage):
    r = xml_base()
    s = spans()
    if damage == 'overlap':
        s.append(s[0])
    elif damage == 'wrong_text':
        s[0]['text'] = '다'
    else:
        l = ET.SubElement(r.findall('.//note')[1], 'lyric', number='1')
        ET.SubElement(l, 'text').text = '새'
    with pytest.raises(ValueError):
        add_extensions(r, s)


def semantic_fixture(kind='tie'):
    s, p = stream.Score(), stream.Part()
    for i in range(2):
        m = stream.Measure(number=i + 1)
        n = note.Note('C4' if kind == 'tie' or i == 0 else 'D4', quarterLength=4)
        if i == 0:
            n.addLyric('주')
        if kind == 'tie':
            n.tie = tie.Tie('start' if i == 0 else 'stop')
        m.append(n)
        p.append(m)
    s.append(p)
    if kind == 'slur':
        s.insert(0, spanner.Slur(*list(s.recurse().notes)))
    return s, [
        {'id': 'stroke', 'measure': 2, 'onset': '0', 'row': 1, 'held_syllable_candidate': '주'}
    ]


@pytest.mark.parametrize('kind', ['tie', 'slur'])
def test_explicit_tie_or_approved_slur_lineage(kind):
    score, marks = semantic_fixture(kind)
    s, e = lineage(score, marks)
    assert len(s) == 1 and not e and len(s[0]['path']) == 2


def test_repeated_pitch_without_tie_does_not_prove_a_held_syllable():
    score, marks = semantic_fixture()
    list(score.recurse().notes)[0].tie = None
    s, e = lineage(score, marks)
    assert not s and e[0]['reason'] == 'NO_EXPLICIT_TIE_OR_APPROVED_SLUR_PATH'


def test_m28_always_stays_unresolved_without_playback_lineage():
    score, marks = semantic_fixture()
    marks[0]['measure'] = 28
    s, e = lineage(score, marks)
    assert not s and e[0]['reason'].startswith('M28_')


def test_curve_sampling_is_deterministic_and_single_component():
    import cv2

    points = [[20, 60], [40, 20], [80, 20], [100, 60]]
    a = smooth_curve((140, 100), points)
    b = smooth_curve((140, 100), points)
    assert a.tobytes() == b.tobytes()
    assert cv2.connectedComponents((np.asarray(a) > 0).astype('uint8'))[0] == 2
    assert np.any((np.asarray(a) > 0) & (np.asarray(a) < 255))
    assert a.getpixel((20, 60)) > 0 and a.getpixel((100, 60)) > 0


def test_minimal_vertical_lyric_translation_keeps_all_pixels():
    size = (100, 100)
    fixed = Image.new('L', size)
    ImageDraw.Draw(fixed).line((10, 30, 80, 30), fill=255, width=2)
    text = Image.new('L', size)
    ImageDraw.Draw(text).rectangle((20, 29, 30, 39), fill=255)
    moved, metrics = place_lyrics({'text': text}, [{'id': 'text', 'measure': 1}], fixed)
    assert metrics[0]['dy'] == 8 and metrics[0]['minimum_ink_center_after_px'] == 6
    assert np.count_nonzero(np.asarray(moved['text'])) == np.count_nonzero(np.asarray(text))
    assert moved['text'].getbbox()[::2] == text.getbbox()[::2]


def test_infeasible_clearance_blocks_instead_of_lowering_threshold():
    fixed = Image.new('L', (50, 50), 255)
    text = Image.new('L', (50, 50))
    ImageDraw.Draw(text).rectangle((10, 10, 20, 20), fill=255)
    with pytest.raises(ValueError):
        place_lyrics({'t': text}, [{'id': 't', 'measure': 1}], fixed)


def test_research_adapter_preserves_extenders_that_raw_music21_drops(tmp_path):
    from music21 import converter

    score = stream.Score()
    part = stream.Part()
    for i in range(3):
        m = stream.Measure(number=i + 1)
        n = note.Note('C4', quarterLength=4)
        n.tie = tie.Tie(['start', 'continue', 'stop'][i])
        if i == 0:
            n.addLyric('주', lyricNumber=1)
            n.addLyric('광', lyricNumber=2)
        m.append(n)
        part.append(m)
    score.append(part)
    path = tmp_path / 'source.musicxml'
    score.write('musicxml', fp=str(path))
    original = ET.fromstring(path.read_bytes())
    extended = add_extensions(original, spans())
    path.write_bytes(ET.tostring(extended))
    parsed = converter.parse(str(path))
    parsed.write('musicxml', fp=str(tmp_path / 'raw.musicxml'))
    raw = ET.fromstring((tmp_path / 'raw.musicxml').read_bytes())
    assert not raw.findall('.//lyric/extend')
    for n in parsed.recurse().notesAndRests:
        n.lyrics = [l for l in n.lyrics if l.text]
    parsed.write('musicxml', fp=str(tmp_path / 'clean.musicxml'))
    restored = add_extensions(ET.fromstring((tmp_path / 'clean.musicxml').read_bytes()), spans())
    assert extension_signature(restored) == extension_signature(extended)


@pytest.mark.parametrize('damage', ['modified', 'missing', 'unexpected_addition'])
def test_frozen_history_content_is_never_waived(monkeypatch, damage):
    from scripts.research import gt17_final as final

    original = {'score.png': 'bound'}
    actual = {'score.png': 'bound'}
    if damage == 'modified':
        actual['score.png'] = 'changed'
    elif damage == 'missing':
        actual = {}
    else:
        actual['another-score.png'] = 'unbound'
    monkeypatch.setattr(final, 'file_hashes', lambda p: actual)
    with pytest.raises(ValueError):
        final.check_history({'/synthetic': original})


def test_non_evidence_addition_is_reported_not_used_or_deleted(monkeypatch):
    from scripts.research import gt17_final as final

    folder = '/private/tmp/capomatic-v4-gt17c/gt17c-frozen-output'
    actual = {'score.png': 'bound', '.Rhistory': 'extra'}
    monkeypatch.setattr(final, 'file_hashes', lambda p: actual)
    checked, extra = final.check_history({folder: {'score.png': 'bound'}})
    assert checked[folder] == actual and extra[0]['path'].endswith('.Rhistory')
    assert extra[0]['status'] == 'UNBOUND_NON_EVIDENCE_DIRECTORY_ADDITION_NOT_USED_AS_INPUT'


def test_uniform_system_layout_keeps_rows_and_measures_level_and_prior_clearance():
    fixed = Image.new('L', (120, 120))
    ImageDraw.Draw(fixed).line((10, 30, 100, 30), fill=255, width=2)
    a = Image.new('L', fixed.size)
    ImageDraw.Draw(a).rectangle((20, 29, 30, 39), fill=255)
    b = Image.new('L', fixed.size)
    ImageDraw.Draw(b).rectangle((70, 45, 80, 55), fill=255)
    moved, metrics = place_lyrics(
        {'a': a, 'b': b},
        [{'id': 'a', 'measure': 1}, {'id': 'b', 'measure': 2}],
        fixed,
        prior_goals={1: 10},
    )
    assert {m['dy'] for m in metrics} == {12}
    assert metrics[0]['minimum_ink_center_after_px'] == 10
    assert moved['a'].getbbox()[1] - a.getbbox()[1] == moved['b'].getbbox()[1] - b.getbbox()[1]


def test_generated_xml_is_visibly_experimental_and_retains_unverified_title(tmp_path):
    from scripts.research.gt17_final import save_xml

    r = xml_base()
    title = ET.Element('movement-title')
    title.text = 'UNVERIFIED OCR TITLE'
    r.insert(0, title)
    path = tmp_path / 'experimental.musicxml'
    save_xml(r, path)
    parsed = ET.fromstring(path.read_bytes())
    assert parsed.findtext('movement-title').startswith('DEVELOPER-ONLY')
    assert 'NOT FOR PERFORMANCE OR PRINTING' in parsed.findtext('work/work-title')
    assert (
        parsed.findtext('./identification/miscellaneous/miscellaneous-field')
        == 'UNVERIFIED OCR TITLE'
    )
    assert len(parsed.findall('./part/measure')) == 3


@pytest.mark.parametrize('damage', [None, 'missing', 'duplicate', 'wrong_row'])
def test_legacy_consumer_requires_exact_origin_lineage(damage):
    from scripts.research.gt17_final_consumer import validate_legacy_origins

    r = add_extensions(xml_base(), spans())
    for n in r.findall('.//note'):
        for l in list(n.findall('lyric')):
            for e in list(l.findall('extend')):
                if e.get('type') != 'start':
                    l.remove(e)
                else:
                    del e.attrib['type']
            if len(l) == 0:
                n.remove(l)
    if damage == 'missing':
        r.find('.//lyric').remove(r.find('.//extend'))
    elif damage == 'duplicate':
        ET.SubElement(r.find('.//lyric'), 'extend')
    elif damage == 'wrong_row':
        r.find('.//lyric').set('number', '3')
    if damage:
        with pytest.raises(ValueError):
            validate_legacy_origins(r, spans())
    else:
        assert validate_legacy_origins(r, spans()) == 2
