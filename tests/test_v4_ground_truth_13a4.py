"""Synthetic header and review-only evidence contracts. No Audiveris execution."""

import copy
import numpy as np
from PIL import Image, ImageDraw
import pytest

from scripts.research.gt11_complete_measure import FONT
from scripts.research.gt13a4_header import header
from scripts.research.gt13a4_system_notation import proposed_lyrics, panel
from scripts.research.gt13a3_owner_verification import EXPECTED, QUARTERS
from fractions import Fraction


def staff(inter, phase=0):
    return {
        'interline': inter,
        'lines': [
            [[0, 200 + i * inter + phase], [1000, 200 + i * inter + phase + 0.5]] for i in range(5)
        ],
    }


@pytest.mark.parametrize('inter', [14, 18, 24])
@pytest.mark.parametrize('phase', [0, 0.25])
def test_actual_header_symbols_and_semantic_anchors(inter, phase):
    if not FONT.exists():
        pytest.skip('Pinned research font unavailable')
    st = staff(inter, phase)
    before = copy.deepcopy(st)
    for target, expected in [('A', ['F5', 'C5', 'G5']), ('G', ['F5'])]:
        parts, report = header((1000, 650), st, target, FONT, x_shift=phase)
        assert [s['pitch'] for s in report['key']['sharps']] == expected
        assert len([p for n, p in parts.items() if n.startswith('sharp')]) == len(expected)
        assert max(map(abs, report['clef']['semantic_anchor_residual'])) <= 0.5
        assert report['time']['ratio'] == '4/4' and len(report['time']['digits']) == 2
        assert report['forward_repeat']['direction'] == 'start'
        dots = report['forward_repeat']['dots']
        assert len(dots) == 2 and all(
            d['center'][0] > report['forward_repeat']['thin_left'] for d in dots
        )
        assert dots[1]['center'][1] > dots[0]['center'][1]
        assert report['actual_header_component_intersections'] == []
        assert all(p.getbbox() is not None for p in parts.values())
        again, other = header((1000, 650), st, target, FONT, x_shift=phase)
        assert report == other and all(parts[n].tobytes() == again[n].tobytes() for n in parts)
    assert st == before


def test_header_rejects_wrong_key_nonfinite_and_clipping():
    with pytest.raises(ValueError, match='key'):
        header((1000, 650), staff(18), 'Bb', FONT)
    with pytest.raises(ValueError, match='Invalid'):
        header((1000, 650), staff(float('nan')), 'A', FONT)
    with pytest.raises(ValueError, match='Clipped'):
        header((220, 260), staff(18), 'A', FONT)


def inventory():
    return {
        'measures': [
            {
                'printed_measure': n,
                'events': [
                    {
                        'event_id': f'm{n}:{i}',
                        'pitch': p,
                        'onset': o,
                        'duration': d,
                        'tie': t,
                        'kind': 'NOTE' if p else 'REST',
                        'source_bbox': [10, 20, 30, 40],
                    }
                    for i, (p, o, d, t) in enumerate(QUARTERS if n == 3 else EXPECTED[n])
                ],
            }
            for n in (1, 2, 3, 4)
        ]
    }


def test_lyric_associations_never_promoted_and_tie_stop_consumes_no_new_token():
    old = inventory()
    before = copy.deepcopy(old)
    audit = proposed_lyrics(old)
    assert old == before and [a['printed_measure'] for a in audit] == [1, 2, 4]
    for a in audit:
        assert a['transcription_status'] == 'OWNER_CONFIRMED_LYRIC_TRANSCRIPTION'
        assert a['transcription_reconfirmation_requested'] is False
        assert all(e['association_status'] == 'OWNER_REVIEW_PENDING' for e in a['events'])
        if a['printed_measure'] in (2, 4):
            rows = a['events']
            assert rows[5]['extender_candidate']
            assert rows[6]['candidate_relation'] == 'TIED_CONTINUATION_NO_NEW_SYLLABLE'
            assert rows[5]['upper_candidate'] == rows[6]['upper_candidate'] == '있'
            assert rows[6]['new_syllable_candidate'] is False
            assert sum(e['new_syllable_candidate'] for e in rows) == 6
    assert audit[-1]['outgoing_extender'] == 'PENDING_DESTINATION_REVIEW'


def test_changed_candidate_rhythm_does_not_invent_syllables():
    inv = inventory()
    inv['measures'][1]['events'][6]['tie'] = None
    with pytest.raises(ValueError, match='lyric'):
        proposed_lyrics(inv)


def test_annotation_panel_preserves_native_pixels_with_header_ink():
    canvas = Image.new('RGB', (2300, 410), 'white')
    music = Image.new('L', canvas.size)
    ImageDraw.Draw(music).rectangle((20, 100, 70, 220), fill=255)
    canvas.paste('black', (0, 0, *canvas.size), music)
    out, metrics = panel(canvas, 'synthetic', target='G', music=music, all_ink=music)
    assert out.crop((0, 250, 2300, 660)).tobytes() == canvas.tobytes()
    assert all(a['notation_region_pixels'] == a['ink_contacts'] == 0 for a in metrics)
    assert min(a['min_pixel_center_distance_px'] for a in metrics) > 0


def tie_fixture(destination='B-3'):
    from music21 import note, stream, tie

    s = stream.Score()
    p = stream.Part()
    for i in range(5):
        m = stream.Measure(number=i + 1)
        if i == 3:
            n = note.Note('B-3', quarterLength=0.25)
            n.tie = tie.Tie('start')
            m.insert(3.75, n)
        if i == 4:
            n = note.Note(destination, quarterLength=4)
            n.tie = tie.Tie('stop')
            m.insert(0, n)
        p.append(m)
    s.append(p)
    graph = {
        'symbols': {
            'sheet#1:4818': {'id': 'sheet#1:4818', 'attributes': [['right-extension', '4798']]},
            'sheet#1:4798': {'id': 'sheet#1:4798', 'attributes': [['left-extension', '4818']]},
            'head-start': {'pitch_position': 7, 'staff': 'staff1'},
            'head-stop': {'pitch_position': 7, 'staff': 'staff2'},
        },
        'relations': [
            {
                'source': 'sheet#1:4818',
                'target': 'head-start',
                'kind': 'slur-head',
                'attributes': [['side', 'LEFT']],
            },
            {
                'source': 'sheet#1:4798',
                'target': 'head-stop',
                'kind': 'slur-head',
                'attributes': [['side', 'RIGHT']],
            },
        ],
    }
    events = [
        {'symbol_id': 'head-start', 'omr_measure_index': 3, 'local_offset': '15/4'},
        {'symbol_id': 'head-stop', 'omr_measure_index': 4, 'local_offset': '0'},
    ]
    return graph, events, s


def test_cross_system_omr_candidate_is_not_owner_confirmation_or_render_permission():
    from scripts.research.gt13a4_system_notation import tie_evidence

    r = tie_evidence(*tie_fixture())
    assert r['classification'] == 'OMR_SUPPORTED_CANDIDATE_PENDING_OWNER'
    assert r['destination_status'] == 'UNVERIFIED' and not r['owner_confirmed_destination']
    assert not r['complete_tie_rendered']
    disagreement = tie_evidence(*tie_fixture('C4'))
    assert disagreement['classification'] == 'EVIDENCE_DISAGREEMENT'
    assert not disagreement['complete_tie_rendered']


def test_missing_extension_or_duplicate_semantic_candidate_is_fatal():
    from scripts.research.gt13a4_system_notation import tie_evidence

    g, e, s = tie_fixture()
    g['symbols']['sheet#1:4798']['attributes'] = []
    with pytest.raises(ValueError, match='Nonreciprocal'):
        tie_evidence(g, e, s)
    g, e, s = tie_fixture()
    e.append(e[-1].copy())
    with pytest.raises(ValueError, match='Ambiguous semantic'):
        tie_evidence(g, e, s)


def reply():
    return {
        'classification': 'OWNER_VERIFIED_LYRIC_ASSOCIATION',
        'independent_ground_truth': False,
        'messages': [
            {'answer': '원본 대조 후 대응 후보 전체 확인'},
            {'answer': '아직 미확인 — 목적지는 보류'},
        ],
        'tie_destination_owner_verified': False,
    }


def test_actual_owner_association_reply_does_not_confirm_tie_destination():
    from scripts.research.gt13a4_confirmed_lyrics import approved_associations

    audit = {'measures': proposed_lyrics(inventory())}
    before = copy.deepcopy(audit)
    result = approved_associations(audit, reply())
    assert audit == before and result['status'] == 'OWNER_VERIFIED_LYRIC_ASSOCIATION'
    assert all(
        e['association_status'] == 'OWNER_VERIFIED_LYRIC_ASSOCIATION'
        for m in result['measures']
        for e in m['events']
    )
    assert reply()['tie_destination_owner_verified'] is False
    bad = reply()
    bad['messages'][0]['answer'] = '아직 미확인'
    with pytest.raises(ValueError, match='approval'):
        approved_associations(audit, bad)
    bad = reply()
    bad['independent_ground_truth'] = True
    with pytest.raises(ValueError, match='Actual owner'):
        approved_associations(audit, bad)


def test_confirmed_tied_stop_gets_no_new_lyric_token_and_m3_is_untouched():
    from music21 import note, stream, tie
    from scripts.research.gt13a4_confirmed_lyrics import apply_lyrics
    from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature

    s = stream.Score()
    p = stream.Part()
    inv = inventory()
    for row in inv['measures']:
        m = stream.Measure(number=row['printed_measure'])
        for e in row['events']:
            n = (
                note.Note(e['pitch'], quarterLength=float(Fraction(e['duration'])))
                if e['pitch']
                else note.Rest(quarterLength=float(Fraction(e['duration'])))
            )
            if e['tie']:
                n.tie = tie.Tie(e['tie'])
            if row['printed_measure'] == 3 and e['pitch']:
                n.addLyric('unchanged')
            m.insert(float(Fraction(e['onset'])), n)
        p.append(m)
    s.append(p)
    before = full_lyric_signature(s)
    result = apply_lyrics(s, {'measures': proposed_lyrics(inv)})
    assert full_lyric_signature(s) == before
    assert full_lyric_signature(result)[0][2] == full_lyric_signature(s)[0][2]
    m = result.parts[0].measure(2)
    assert [(l.number, l.text) for l in m.notesAndRests[5].lyrics] == [(1, '있'), (2, '우')]
    assert m.notesAndRests[6].lyrics == []


def test_alpha_lyric_collision_is_recorded_and_not_waived():
    from scripts.research.gt13a4_confirmed_lyrics import lyric_contacts

    music = Image.new('L', (20, 20))
    text = Image.new('L', (20, 20))
    music.putpixel((5, 5), 1)
    text.putpixel((5, 5), 1)
    contacts, mask = lyric_contacts({'confirmed-text': text}, music)
    assert contacts == [{'component': 'confirmed-text', 'pixels': 1}]
    assert mask.getpixel((5, 5)) == 255
    text = Image.new('L', (20, 20))
    text.putpixel((6, 5), 255)
    assert lyric_contacts({'text': text}, music)[0] == []


def test_full_lyric_signature_detects_changes_outside_gt12_m3_scope():
    from music21 import note, stream
    from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature

    s = stream.Score()
    p = stream.Part()
    for i in (1, 2, 3, 4):
        m = stream.Measure(number=i)
        m.append(note.Note('C4'))
        p.append(m)
    s.append(p)
    before = full_lyric_signature(s)
    s.parts[0].measure(4).notes[0].addLyric('changed')
    after = full_lyric_signature(s)
    assert before != after and before[0][2] == after[0][2]
