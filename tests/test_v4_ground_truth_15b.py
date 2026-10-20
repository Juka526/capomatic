"""Owner-layer and collision-layout tests; no score recognition or fabricated labels."""

import copy
from fractions import Fraction

import pytest
from music21 import harmony, note, stream, tie
from PIL import Image, ImageDraw

from scripts.research.gt15a_owner_review import build_checklist
from scripts.research.gt15b_confirmed_third_system import (
    WITHHELD,
    augment,
    interpretation,
    layout_text,
    verify_owner,
    chord_text,
)
from scripts.research.paired_ground_truth_01 import dump, sha
from test_v4_ground_truth_15a import candidates


def owner_layer():
    inv, graph = candidates()
    # Replace synthetic strings with fixed candidate content; still no human labels.
    texts = {
        9: (['풀', '은', '마'], ['전', '능', '하']),
        10: (['르', '고'], ['신', '주']),
        11: (['꽃', '을', '시'], ['거', '룩', '하']),
        12: (['드', '나'], ['신', '왕']),
    }
    for m in inv['measures']:
        c = m['agent_candidates']
        c['upper'], c['lower'] = texts[m['printed_measure']]
        c['chord'] = {10: 'Eb', 12: 'F'}.get(m['printed_measure'])
    checklist = build_checklist(inv, graph)
    b = {
        'withheld_ids': sorted(WITHHELD),
        'approval_sha256': 'synthetic-test-binding',
        'correction': {'id': 'm11-row1-syllable-3', 'old': '을', 'new': '은', 'onset': '3'},
        'approved_kinds': [
            'MUSIC_EVENT',
            'TIE',
            'CHORD_OR_ABSENCE',
            'LYRIC_ASSOCIATION',
            'CONTINUATION_STROKE',
            'REPEAT_ENDING',
            'NEGATIVE_OBSERVATION',
        ],
    }
    return checklist, b


def test_owner_correction_is_separate_and_five_objects_remain_withheld():
    original, binding = owner_layer()
    snapshot = copy.deepcopy(original)
    layer = interpretation(original, binding)
    assert original == snapshot
    assert sum(i['interpretation_status'] == 'OWNER_VERIFIED_SOURCE' for i in layer['items']) == 63
    withheld = [i for i in layer['items'] if i['id'] in WITHHELD]
    assert len(withheld) == 5
    assert all(
        i['interpretation_status'] == 'UNRESOLVED_CLASSIFICATION_EXPLICITLY_WITHHELD'
        for i in withheld
    )
    corrected = next(i for i in layer['items'] if i['id'] == 'm11-row1-syllable-3')
    assert corrected['historical_candidate']['syllable'] == '을'
    assert corrected['candidate']['syllable'] == '은' and corrected['candidate']['onset'] == '3'
    assert all(i['owner_response'] is None for i in original['items'])
    assert layer['independent_ground_truth'] is False


@pytest.mark.parametrize('bad', ['withheld', 'correction', 'prior_answer'])
def test_changed_scope_or_historical_answer_rejected(bad):
    checklist, b = owner_layer()
    if bad == 'withheld':
        b['withheld_ids'] = []
    elif bad == 'correction':
        b['correction']['onset'] = '1'
    else:
        checklist['items'][0]['owner_response'] = 'GENERATED'
    with pytest.raises(ValueError):
        interpretation(checklist, b)


def synthetic_score():
    score = stream.Score()
    part = stream.Part()
    score.append(part)
    source, _ = candidates()
    for m in source['measures']:
        measure = stream.Measure(number=m['printed_measure'])
        for e in m['events']:
            n = note.Rest() if e['kind'] == 'REST' else note.Note(e['pitch'])
            n.quarterLength = Fraction(e['duration'])
            if e['tie']:
                n.tie = tie.Tie(e['tie'])
            measure.insert(Fraction(e['onset']), n)
        part.append(measure)
    # Augment indexes original measures, so prepend eight inert measures.
    measures = list(part.getElementsByClass(stream.Measure))
    part.clear()
    for i in range(1, 9):
        m = stream.Measure(number=i)
        m.append(note.Rest(quarterLength=4))
        part.append(m)
    for m in measures:
        part.append(m)
    return score


def test_augment_two_chords_twenty_syllables_no_new_tied_tokens():
    c, b = owner_layer()
    layer = interpretation(c, b)
    source = synthetic_score()
    result = augment(source, layer)
    measures = list(result.parts[0].getElementsByClass(stream.Measure))
    assert sum(len(n.lyrics) for m in measures[8:12] for n in m.notesAndRests) == 20
    assert [
        chord_text(list(m.getElementsByClass(harmony.ChordSymbol))[0])
        for m in (measures[9], measures[11])
    ] == ['Eb', 'F']
    assert not list(measures[8].getElementsByClass(harmony.ChordSymbol))
    assert all(
        not n.lyrics
        for m in measures[8:12]
        for n in m.notesAndRests
        if n.tie and n.tie.type == 'stop'
    )
    assert not any(
        n.lyrics
        for m in source.parts[0].getElementsByClass(stream.Measure)
        for n in m.notesAndRests
    )


def mask(box, size=(40, 40)):
    m = Image.new('L', size)
    ImageDraw.Draw(m).rectangle(box, fill=255)
    return m


def test_minimal_shared_translation_preserves_x_row_spacing_and_pixels():
    fixed = mask((10, 10, 14, 12))
    parts = {
        'upper': mask((11, 12, 13, 14)),
        'lower': mask((11, 20, 13, 22)),
        'mark': mask((18, 14, 21, 15)),
    }
    moved, r = layout_text(parts, fixed, (0, 0, 40, 40))
    assert r['dy'] == 2 and r['lyric_music_contacts'] == 0
    assert r['minimum_ink_center_distance_px'] >= 2
    for k, p in parts.items():
        old, new = p.getbbox(), moved[k].getbbox()
        assert new == tuple(v + 2 if j in (1, 3) else v for j, v in enumerate(old))
        assert p.crop(old).tobytes() == moved[k].crop(new).tobytes()
    assert layout_text(parts, fixed, (0, 0, 40, 40))[1] == r


def test_no_clearance_domain_fails_without_shrinking_or_clipping():
    with pytest.raises(ValueError, match='No collision-safe'):
        layout_text({'word': mask((1, 1, 4, 4))}, mask((0, 0, 39, 39)), (0, 0, 40, 40))


def test_owner_binding_fails_if_actual_message_changed(tmp_path):
    packet = tmp_path / 'packet'
    packet.mkdir()
    dump(packet / 'packet-freeze.json', {'files': {}})
    approval = tmp_path / 'approval.txt'
    approval.write_text('synthetic message')
    binding = {
        'classification': 'OWNER_VERIFIED_SOURCE',
        'independent_ground_truth': False,
        'source_ink_replacement_authorized': False,
        'approval_file': 'approval.txt',
        'approval_sha256': sha(approval),
        'packet_directory': str(packet),
        'packet_freeze_sha256': sha(packet / 'packet-freeze.json'),
    }
    dump(tmp_path / 'binding.json', binding)
    approval.write_text('changed')
    with pytest.raises(ValueError, match='Approval bytes changed'):
        verify_owner(tmp_path / 'binding.json')


@pytest.mark.parametrize('text', ['F', 'D', 'Bb/D', 'Pre-Chorus', 'WWWWWWWWWWWW'])
def test_section_plain_text_uses_measured_width_and_lossless_phase(text):
    from PIL import ImageFont
    from scripts.research.gt15b_confirmed_third_system import section_label, FONT
    from scripts.research.gt12_render_context import text_mask

    f = ImageFont.truetype(str(FONT), 33)
    mask, info = section_label((700, 200), f, text, (20, 30))
    b = mask.getbbox()
    assert b[:2] == (20, 30) and b[2] - b[0] == info['measured_ink_width_px']
    assert section_label((700, 200), f, text, (20, 30))[0].tobytes() == mask.tobytes()
    if len(text) < 5:
        old, _ = text_mask((700, 200), f, text, left_top=(20, 30))
        assert old.tobytes() == mask.tobytes()


def test_section_plain_text_rejects_clipping_without_font_shrink():
    from PIL import ImageFont
    from scripts.research.gt15b_confirmed_third_system import section_label, FONT

    f = ImageFont.truetype(str(FONT), 33)
    with pytest.raises(ValueError, match='Clipped section placement'):
        section_label((60, 60), f, 'Pre-Chorus', (20, 30))
