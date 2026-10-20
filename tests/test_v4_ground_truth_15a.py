"""Synthetic review candidates; no real owner labels, rendering or Audiveris."""

import copy

import pytest

from scripts.research.gt15a_owner_review import build_checklist, compact_markdown


def candidates():
    inv = {
        'source_sha256': 'synthetic',
        'staff': {'system': 'system3'},
        'measures': [],
        'continuation_candidates': [],
        'ambiguous_SIG_objects': [],
        'explicit_negative_observation': {'observation': 'synthetic'},
        'repeat_context': {},
    }
    graph = {'symbols': {}, 'relations': []}
    for m in range(9, 13):
        onsets = ['0', '2', '5/2', '3', '7/2'] if m in (9, 11) else ['0', '1/2', '1', '3/2', '2']
        es = []
        for n, onset in enumerate(onsets):
            sid = f'm{m}e{n}'
            rest = m in (9, 11) and n < 2
            e = {
                'symbol_id': sid,
                'printed_measure': m,
                'onset': onset,
                'duration': '1/2',
                'pitch': None if rest else 'F4',
                'tie': None,
                'kind': 'REST' if rest else 'NOTE',
                'stem_ids': [],
                'stem_direction': None if rest else 'up',
                'beams': [],
                'source_bbox': [m * 10 + n, 20, m * 10 + n + 1, 21],
                'render_evidence': 'OMR_PROVISIONAL',
                'source_verification': 'UNVERIFIED',
            }
            es.append(e)
            graph['symbols'][sid] = {
                'id': sid,
                'kind': 'rest' if rest else 'head',
                'system': 'system3',
                'geometry': {'bbox': e['source_bbox']},
            }
        c = {
            'chord': None if m in (9, 11) else 'C',
            'upper': ['가', '나', '다'] if m in (9, 11) else ['라', '마'],
            'lower': ['바', '사', '아'] if m in (9, 11) else ['자', '차'],
            'onsets': onsets[2:] if m in (9, 11) else ['1/2', '3/2'],
        }
        inv['measures'].append(
            {'printed_measure': m, 'events': es, 'agent_candidates': c, 'recognized_harmonies': []}
        )
    for n, (am, an, bm, bn) in enumerate(
        [
            (9, 4, 10, 0),
            (10, 1, 10, 2),
            (10, 3, 10, 4),
            (11, 4, 12, 0),
            (12, 1, 12, 2),
            (12, 3, 12, 4),
        ]
    ):
        a = inv['measures'][am - 9]['events'][an]
        b = inv['measures'][bm - 9]['events'][bn]
        a['tie'], b['tie'] = 'start', 'stop'
        sid = f'tie{n}'
        graph['symbols'][sid] = {
            'id': sid,
            'kind': 'slur',
            'system': 'system3',
            'source_xml': '<slur tie="true"/>',
            'geometry': {'bbox': [0, 0, 1, 1]},
        }
        for k, e in enumerate([b, a]):  # Deliberately reverse persisted order.
            graph['relations'].append(
                {'id': f'r{n}-{k}', 'kind': 'slur-head', 'source': sid, 'target': e['symbol_id']}
            )
    for m in (10, 12):
        for row in (1, 2):
            for onset in ('0', '1', '2'):
                if (m, row, onset) == (10, 1, '1'):
                    continue
                inv['continuation_candidates'].append(
                    {
                        'measure': m,
                        'row': row,
                        'onset_candidate': onset,
                        'source_window': [0, 0, 2, 2],
                        'source_bbox_dark_support': [0, 0, 1, 1],
                        'owner_response': None,
                    }
                )
    for sid in ['5833', '5841', '5902', '5903', '5896']:
        inv['ambiguous_SIG_objects'].append(
            {
                'symbol': {
                    'id': f'sheet#1:{sid}',
                    'shape': 'TENUTO',
                    'geometry': {'bbox': [0, 0, 1, 1]},
                },
                'relations': [],
            }
        )
    return inv, graph


def test_fixed_scope_all_answers_empty_and_inputs_unchanged():
    inv, graph = candidates()
    before = copy.deepcopy((inv, graph))
    result = build_checklist(inv, graph)
    assert len(result['items']) == 72
    assert result['scope'] == {
        'events': 20,
        'ties': 6,
        'chord_or_absence_items': 4,
        'syllable_associations': 20,
        'continuation_strokes': 11,
        'ambiguous_SIG_objects': 5,
    }
    assert not result['owner_verified_source'] and not result['independent_ground_truth']
    assert all(
        i[k] is None
        for i in result['items']
        for k in ('owner_response', 'owner_correction', 'owner_uncertainty')
    )
    assert (inv, graph) == before
    assert build_checklist(inv, graph) == result
    assert compact_markdown(result) == compact_markdown(build_checklist(inv, graph))


def test_ties_chronological_not_persisted_relation_order():
    result = build_checklist(*candidates())
    ties = [i['candidate'] for i in result['items'] if i['kind'] == 'TIE']
    assert ties[0]['endpoints'][0]['symbol_id'] == 'm9e4'
    assert ties[0]['endpoints'][1]['symbol_id'] == 'm10e0'
    assert ties[0]['source_relations'][0]['target'] == 'm10e0'


def test_ambiguous_overlap_is_cross_reference_not_new_ownership():
    result = build_checklist(*candidates())
    items = [i for i in result['items'] if i['kind'] == 'AMBIGUOUS_SIG_OBJECT']
    assert len(items[0]['candidate']['overlapping_continuation_candidates']) == 11
    assert items[0]['candidate_status'] == 'AGENT_VISUAL_CANDIDATE'


@pytest.mark.parametrize('mutation', ['pitch', 'promoted', 'lyric', 'continuation', 'missing_tie'])
def test_fail_closed_on_inconsistent_or_promoted_candidates(mutation):
    inv, graph = candidates()
    if mutation == 'pitch':
        inv['measures'][1]['events'][0]['pitch'] = 'G4'
    elif mutation == 'promoted':
        inv['measures'][0]['events'][0]['source_verification'] = 'OWNER_VERIFIED_SOURCE'
    elif mutation == 'lyric':
        inv['measures'][0]['agent_candidates']['onsets'][0] = '99'
    elif mutation == 'continuation':
        inv['continuation_candidates'][0]['onset_candidate'] = '99'
    else:
        graph['relations'].pop()
    with pytest.raises(ValueError):
        build_checklist(inv, graph)


def test_tampered_frozen_input_fails_before_creating_packet(tmp_path, monkeypatch):
    from scripts.research import gt15a_owner_review as packet
    from scripts.research.paired_ground_truth_01 import dump, sha

    prior = tmp_path / 'prior'
    prior.mkdir()
    frozen = prior / 'input.json'
    frozen.write_text('original')
    dump(
        tmp_path / 'docs/V4_GT15_VALIDATION.json',
        {
            'base_sha': '13b2313cf79bee39508a5f12994be6b5a8c378f3',
            'artifact_sha256': {'input.json': sha(frozen)},
        },
    )
    frozen.write_text('tampered')
    monkeypatch.setattr(packet, 'ROOT', tmp_path)
    monkeypatch.setattr(packet, 'PRIOR', prior)
    output = tmp_path / 'packet'
    with pytest.raises(ValueError, match='GT15 artifact mismatch'):
        packet.run(output)
    assert not output.exists()
