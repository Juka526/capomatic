"""Integrate only the final 39 expressly approved lyric-onset associations."""

import argparse
import copy
from pathlib import Path

from music21 import converter

from backend.omr_v3.music_guard import validate
from scripts.research.gt11_complete_measure import read, require
from scripts.research.gt17b_owner_integration import (
    SOURCE_DIR,
    verify_manifest,
    relationship_signature,
)
from scripts.research.gt17c_accuracy_audit import OWNER
from scripts.research.gt17d_owner_correction import relationship_inventory
from scripts.research.gt17e_owner_confirmation import (
    PRIOR as SEMANTIC,
    lyric_scope,
    unique_by,
    semantic_event,
)
from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes

ROOT = Path(__file__).resolve().parents[2]
PRIOR = Path('/private/tmp/capomatic-v4-gt17e/gt17e-delivery-output')
START = 'ad0a249e3621d4755b70ee82dbd20e79f48a1c7a'
GROUPS = {
    'SYS7_LYRIC_ONSET': (16, range(25, 30)),
    'SYS8_LYRIC_ONSET': (16, range(30, 34)),
    'SYS9_LYRIC_ONSET': (7, range(34, 38)),
}
APPROVAL = '''The owner supplied the following exact decisions:

- `SYS7_LYRIC_ONSET: CONFIRM` — 16 associations
- `SYS8_LYRIC_ONSET: CONFIRM` — 16 associations
- `SYS9_LYRIC_ONSET: CONFIRM` — 7 associations

The approval explicitly applies only to the exact syllable-to-note onset mappings in these three GT-17E review groups.

All other unresolved categories remain unchanged.'''


def resolve_scope(plan, inventory, coverage):
    """Match the explicit approval groups to every and only pending association."""
    unique_by([i for g in plan['groups'] for i in g['items']], 'id')
    unique_by(inventory['events'], 'symbol_id')
    associations = unique_by(coverage['new_scope_lyric_associations'], 'id')
    require(len(associations) == 79, 'Prior lyric coverage size mismatch')
    require(coverage['prior_verified_lyric_onsets'] == 88, 'Prior inherited approvals mismatch')
    selected = []
    for group_id, (count, measures) in GROUPS.items():
        for item, lyric in lyric_scope(plan, inventory, group_id, count, measures):
            require(lyric['id'] in associations, 'Missing coverage case')
            prior = associations[lyric['id']]
            require(prior['classification'] == 'OMR_PROVISIONAL', 'Case is not pending')
            require(prior['event_id'] == lyric['event_id'], 'Prior event identity mismatch')
            selected.append((group_id, item, lyric))
    require(
        len(selected) == len({l['id'] for _, _, l in selected}) == 39, 'Duplicate approved case'
    )
    require(
        {l['id'] for _, _, l in selected}
        == {a['id'] for a in associations.values() if a['classification'] == 'OMR_PROVISIONAL'},
        'Approval does not exactly cover pending associations',
    )
    require(
        sum(a['classification'] == 'OWNER_VERIFIED_SOURCE' for a in associations.values()) == 40,
        'Prior SYS6 approvals mismatch',
    )
    return selected


def integrate(prior_layer, prior_coverage, selected):
    """New layer only: retain all prior overrides and alter association statuses only."""
    layer, coverage = copy.deepcopy(prior_layer), copy.deepcopy(prior_coverage)
    ids = {l['id'] for _, _, l in selected}
    require(
        not ids.intersection(o['id'] for o in layer['lyric_onset_overrides']),
        'Already overridden lyric',
    )
    for _, _, lyric in selected:
        layer['lyric_onset_overrides'].append(
            {
                'id': lyric['id'],
                'event_id': lyric['event_id'],
                'onset': lyric['onset'],
                'row': lyric['row'],
                'classification': 'OWNER_VERIFIED_SOURCE',
            }
        )
    for association in coverage['new_scope_lyric_associations']:
        if association['id'] in ids:
            association['classification'] = 'OWNER_VERIFIED_SOURCE'
    coverage['totals']['verified_lyric_onsets'] += len(selected)
    coverage['totals']['provisional_lyric_onsets'] -= len(selected)
    require(
        coverage['totals']['verified_lyric_onsets'] == 167
        and coverage['totals']['provisional_lyric_onsets'] == 0,
        'Final coverage mismatch',
    )
    require(
        layer['event_core_overrides'] == prior_layer['event_core_overrides'],
        'Event approval changed',
    )
    require(coverage['event_cores'] == prior_coverage['event_cores'], 'Event core coverage changed')
    return layer, coverage


def run(out):
    require(not out.exists(), 'Fresh output directory required')
    # Understood as: status-only approval of three exact lyric-onset groups, not extenders.
    meta = read(ROOT / 'docs/V4_GT17E_VALIDATION.json')
    verify_manifest(PRIOR, 'output-freeze.json')
    require(
        sha(PRIOR / 'output-freeze.json') == meta['output_freeze_sha256'],
        'GT17E freeze identity mismatch',
    )
    for name, digest in meta['artifact_sha256'].items():
        require(sha(PRIOR / name) == digest, 'GT17E artifact mismatch: ' + name)
    preservation = read(PRIOR / 'preservation-verification.json')
    snapshots = preservation['historical_directory_file_hashes']
    for folder, files in snapshots.items():
        require(file_hashes(Path(folder)) == files, 'Historical input changed: ' + folder)
    snapshots = {**snapshots, str(PRIOR): file_hashes(PRIOR)}
    source_hashes = preservation['source_hashes']
    for name, field in [
        ('source.png', 'source_sha256'),
        ('recognized.omr', 'omr_sha256'),
        ('visual-graph.json', 'graph_sha256'),
    ]:
        require(sha(SOURCE_DIR / name) == source_hashes[field], 'Source hash mismatch')
    plan = read(PRIOR / 'remaining-review-plan.json')
    inventory = read(OWNER / 'source-event-inventory.json')
    prior_layer = read(PRIOR / 'owner-interpretation-layer.json')
    prior_coverage = read(PRIOR / 'field-coverage-matrix.json')
    require(
        prior_coverage['totals']['owner_confirmed_event_cores'] == 169
        and prior_coverage['totals']['verified_lyric_onsets'] == 128,
        'Prior approved totals mismatch',
    )
    selected = resolve_scope(plan, inventory, prior_coverage)
    source = converter.parse(str(SEMANTIC / 'corrected-source.musicxml'))
    graph = read(SOURCE_DIR / 'visual-graph.json')
    events = unique_by(inventory['events'], 'id')
    for _, item, lyric in selected:
        event = events[lyric['event_id']]
        require(
            graph['symbols'][event['symbol_id']] == event['source_symbol'],
            'Raw source event identity mismatch',
        )
        require(
            sha(Path(item['source_crop']['path'])) == item['source_crop']['sha256'],
            'Source crop hash mismatch: ' + item['id'],
        )
        note = semantic_event(source, lyric['measure'], lyric['onset'])
        require(
            note.isNote and note.pitch.nameWithOctave == event['pitch'],
            'Associated semantic pitch mismatch',
        )
        require(
            [(l.number, l.text) for l in note.lyrics].count((lyric['row'], lyric['text'])) == 1,
            'Source XML lyric mismatch: ' + item['id'],
        )
    curves = read(OWNER / 'owner-interpretation-layer.json')['curve_interpretations']
    curve_checks = {'source': relationship_signature(source, curves)}
    rel = relationship_inventory(source)
    require(
        len(rel['slurs']) == 1
        and all(s[0] != ((0, 21, '3'), (0, 21, '13/4')) for s in rel['slurs']),
        '4867 correction lost',
    )
    guards = {}
    for name, shift in [('A', -1), ('G', -3)]:
        target = converter.parse(str(SEMANTIC / f'{name}-corrected.musicxml'))
        guards[name] = validate(source, target, shift, 'key').to_dict()
        require(guards[name]['ok'], 'Unchanged V3 guard failed: ' + name)
        curve_checks[name] = relationship_signature(target, curves)
        for _, _, lyric in selected:
            note = semantic_event(target, lyric['measure'], lyric['onset'])
            require(
                [(l.number, l.text) for l in note.lyrics].count((lyric['row'], lyric['text'])) == 1,
                'Target XML lyric mismatch',
            )
    layer, coverage = integrate(prior_layer, prior_coverage, selected)
    remaining = copy.deepcopy(plan)
    remaining['groups'] = [g for g in remaining['groups'] if g['group_id'] not in GROUPS]
    require(
        sum(len(g['items']) for g in remaining['groups']) == 48,
        'Remaining unresolved scope mismatch',
    )
    require(
        all(
            g['owner_answer'] is None and all(i['owner_answer'] is None for i in g['items'])
            for g in remaining['groups']
        ),
        'Unapproved answer propagation',
    )
    remaining['counts'].update(
        {'lyric_onsets': 0, 'field_items': 48, 'coherent_groups': len(remaining['groups'])}
    )
    # All candidate and semantic checks precede writing any new interpretation artifact.
    out.mkdir(parents=True)
    dump(
        out / 'owner-approval-record.json',
        {
            'classification': 'OWNER_VERIFIED_SOURCE_LYRIC_ONSET_ASSOCIATION_ONLY',
            'independent_ground_truth': 0,
            'starting_sha': START,
            'approval_context_verbatim': APPROVAL,
            'owner_decisions_verbatim': [f'{group_id}: CONFIRM' for group_id in GROUPS],
            'approval_origin': 'Exact owner decisions quoted in current GT17F user instruction; no separate submission, signature, timestamp or reviewer invented.',
            'approved_fields': ['syllable-to-event identity', 'exact onset association'],
            'review_bindings': {
                n: {'path': str(PRIOR / n), 'sha256': sha(PRIOR / n)}
                for n in [
                    'remaining-owner-review-summary.md',
                    'remaining-review-plan.json',
                    'owner-interpretation-layer.json',
                    'field-coverage-matrix.json',
                    'owner-approval-record.json',
                    'output-freeze.json',
                ]
            },
            'source_hashes': source_hashes,
            'approved_records': [
                {'group_id': g, 'review_case': i, 'original_source_lyric': l}
                for g, i, l in selected
            ],
            'no_other_fields_approved': True,
        },
    )
    layer['prior_layers']['GT17E'] = {
        'path': str(PRIOR / 'owner-interpretation-layer.json'),
        'sha256': sha(PRIOR / 'owner-interpretation-layer.json'),
    }
    layer['prior_approval_record_sha256'] = sha(PRIOR / 'owner-approval-record.json')
    layer['approval_record_sha256'] = sha(out / 'owner-approval-record.json')
    dump(out / 'owner-interpretation-layer.json', layer)
    dump(out / 'field-coverage-matrix.json', coverage)
    dump(out / 'remaining-review-plan.json', remaining)
    lines = [
        '# GT-17F 이후 남은 소유자 검토',
        '',
        '음악 핵심 169개, 코드 24개, 가사 문구·행 167개, 정확한 가사 대응 167개가 소유자 승인 상태입니다. 독립 정답은 0이며 원본 완전성은 UNVERIFIED입니다.',
        '',
        '남은 필드 질문: 연장선 20개(m28 계보 포함) + raw SIG 27개 + 전체 반복 재생 1개 = 48개. 이 수는 독립적인 오류 개수가 아닙니다.',
        '',
        '이전 EVENT 및 모든 LYRIC_ONSET 그룹은 재확인하지 마세요. MusicXML 가사 연장선 직렬화는 여전히 별도 미해결입니다.',
        f'[기존 원본·후보 상세 안내]({SEMANTIC / "owner-review-summary.md"})',
        '아래 남은 그룹만 CONFIRM / CORRECT(사례 ID·필드) / UNCERTAIN으로 답할 수 있습니다. 모든 답변은 비어 있습니다.',
        '',
    ]
    for group in remaining['groups']:
        lines.extend(
            [
                f'## {group["group_id"]} — 인쇄 {group["printed_measures"]}',
                ', '.join(i['id'] for i in group['items']),
                '답변: ______',
                '',
            ]
        )
    (out / 'remaining-owner-review-summary.md').write_text('\n'.join(lines) + '\n')
    dump(
        out / 'approval-validation.json',
        {
            'exact_scope_count': len(selected),
            'groups': {g: n for g, (n, _) in GROUPS.items()},
            'prior_128_approvals_preserved': True,
            'only_39_association_statuses_changed': True,
            'coverage': coverage['totals'],
            'unchanged_v3_guards': guards,
            'approved_curves': curve_checks,
            '4867_correction_preserved': True,
            'unresolved_group_ids': [g['group_id'] for g in remaining['groups']],
            'M28_CONTINUATION_LINEAGE': 'UNRESOLVED',
            'FULL_REPEAT_PLAYBACK': 'UNRESOLVED',
            'source_completeness': 'UNVERIFIED',
            'rendering_completeness': 'INCOMPLETE',
            'musicxml_lyric_extenders': 'UNCHANGED_UNRESOLVED',
            'independent_ground_truth': 0,
        },
    )
    require(
        all(file_hashes(Path(folder)) == files for folder, files in snapshots.items()),
        'Historical input changed during run',
    )
    for name, field in [
        ('source.png', 'source_sha256'),
        ('recognized.omr', 'omr_sha256'),
        ('visual-graph.json', 'graph_sha256'),
    ]:
        require(sha(SOURCE_DIR / name) == source_hashes[field], 'Original changed during run')
    dump(
        out / 'preservation-verification.json',
        {
            'historical_files_unchanged': True,
            'historical_directory_file_hashes': snapshots,
            'source_hashes': source_hashes,
            'xml_png_pdf_regenerated': False,
            'production_changes': False,
        },
    )
    dump(
        out / 'output-freeze.json',
        {
            'files': file_hashes(out),
            'producer_sha256': sha(Path(__file__)),
            'lyric_resolver_sha256': sha(ROOT / 'scripts/research/gt17e_owner_confirmation.py'),
            'starting_sha': START,
        },
    )
    print(coverage['totals'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
