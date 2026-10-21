"""Evidence-status-only owner approvals; never rewrite XML, images or raw observations."""

import argparse
import copy
from fractions import Fraction
from pathlib import Path

from music21 import converter, stream

from backend.omr_v3.music_guard import validate
from scripts.research.gt11_complete_measure import read, require, events_of
from scripts.research.gt17b_owner_integration import (
    SOURCE_DIR,
    at,
    verify_manifest,
    relationship_signature,
)
from scripts.research.gt17c_accuracy_audit import OWNER
from scripts.research.gt17d_owner_correction import AUDIT, BASE, relationship_inventory
from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes

ROOT = Path(__file__).resolve().parents[2]
PRIOR = Path('/private/tmp/capomatic-v4-gt17d/gt17d-delivery-output')
START = '55b72a2fb2162ee4ba913b99310932fbb26fcfab'
GROUP_COUNTS = {'SYS6_EVENT': 30, 'SYS7_EVENT': 17, 'SYS8_EVENT': 22, 'SYS9_EVENT': 14}
CORE_FIELDS = ['kind', 'pitch', 'onset', 'duration', 'voice', 'part']
EVENT_APPROVAL = '''Integrate the owner's explicit approval of the 83 provisional note/rest event cores across printed systems 6–9, measures 20–37.

Approved groups:

- SYS6_EVENT: 30 events
- SYS7_EVENT: 17 events
- SYS8_EVENT: 22 events
- SYS9_EVENT: 14 events

Bind the owner's exact approval to the GT-17D review summary, event IDs, printed measures, source crops and frozen evidence hashes.

Promote only the approved event-core fields supported by those reviewed candidate records.

Expected total:
169 owner-confirmed event cores.

Do not interpret this as independent ground truth or full source completeness.'''
LYRIC_QUESTION = '83개 음악 이벤트 승인은 현재 지시문으로 반영할 수 있습니다. SYS6 가사 대응은 별도 승인 원문이나 승인한 case ID가 현재 기록에 없습니다. SYS6_LYRIC_ONSET 40개 전체를 원본과 대조해 승인하신 것인지, 일부인지 알려주세요. 명시적인 범위가 확인되기 전에는 이 40개를 승격하지 않고 별도 보류 기록으로 남기겠습니다.'
LYRIC_ANSWER = 'SYS6_LYRIC_ONSET 40개 전체 승인'


def unique_by(records, key):
    result = {}
    for record in records:
        require(record[key] not in result, f'Duplicate {key}: {record[key]}')
        result[record[key]] = record
    return result


def semantic_event(score, measure, onset):
    measures = list(score.parts[0].getElementsByClass(stream.Measure))
    require(1 <= measure <= len(measures), 'Missing semantic measure')
    m = measures[measure - 1]
    events = [n for n in events_of(m) if Fraction(n.getOffsetInHierarchy(m)) == Fraction(onset)]
    require(len(events) == 1, 'Ambiguous note/rest semantic address')
    return events[0]


def approved_scope(plan, inventory):
    """Resolve explicit group IDs against exact reviewed source candidates, fail closed."""
    groups = unique_by(plan['groups'], 'group_id')
    unique_by([i for g in plan['groups'] for i in g['items']], 'id')
    events = unique_by(inventory['events'], 'symbol_id')
    unique_by(inventory['events'], 'id')
    approved = []
    for group_id, count in GROUP_COUNTS.items():
        require(group_id in groups, 'Missing approved group: ' + group_id)
        group = groups[group_id]
        require(len(group['items']) == count, 'Approved group count mismatch')
        system = int(group_id[3])
        systems = [s for s in inventory['systems'] if s['system'] == system]
        require(len(systems) == 1, 'Ambiguous source system')
        for item in group['items']:
            sid = item['source_object_id']
            require(
                item['kind'] == 'event' and item['id'] == 'event-' + sid, 'Case identity mismatch'
            )
            require(sid in events, 'Missing source event')
            event = events[sid]
            c = item['candidate']
            require(
                item['measure'] == event['printed_measure']
                and item['measure'] in systems[0]['printed_measures']
                and 20 <= item['measure'] <= 37,
                'Printed measure/system scope mismatch',
            )
            require(
                c['music_event_kind'] == event['kind']
                and c['written_pitch'] == event['pitch']
                and c['onset'] == event['onset']
                and c['duration'] == event['duration']
                and c['voice'] == event['voice']
                and event['part'] == 1
                and item['source_window'] == event['source_bbox'],
                'Reviewed core or bbox mismatch',
            )
            require(
                event['source_verification'] == 'UNVERIFIED', 'Already approved event in new scope'
            )
            approved.append((group_id, item, event))
    require(len({e['id'] for _, _, e in approved}) == 83, 'Missing/duplicate approved event IDs')
    require(
        {e['id'] for _, _, e in approved}
        == {e['id'] for e in inventory['events'] if e['source_verification'] == 'UNVERIFIED'},
        'Provisional inventory scope differs',
    )
    return approved


def lyric_scope(plan, inventory):
    groups = unique_by(plan['groups'], 'group_id')
    require('SYS6_LYRIC_ONSET' in groups, 'Missing lyric approval group')
    items = groups['SYS6_LYRIC_ONSET']['items']
    require(len(items) == 40, 'Lyric group count mismatch')
    unique_by(items, 'id')
    lyrics = unique_by(inventory['lyrics'], 'id')
    events = unique_by(inventory['events'], 'id')
    approved = []
    for item in items:
        key = item['id'].removeprefix('lyric-')
        require(key in lyrics and item['kind'] == 'lyric_onset', 'Unknown lyric case')
        lyric = lyrics[key]
        require(item['id'] == 'lyric-' + lyric['id'], 'Lyric case namespace mismatch')
        require(
            item['candidate'] == {k: lyric[k] for k in ['onset', 'row', 'text']}
            and item['measure'] == lyric['measure']
            and 20 <= item['measure'] <= 24,
            'Lyric field scope mismatch',
        )
        require(lyric['event_id'] in events, 'Missing lyric event')
        e = events[lyric['event_id']]
        require(
            e['kind'] == 'NOTE'
            and e['printed_measure'] == lyric['measure']
            and e['onset'] == lyric['onset']
            and item['source_object_id'] == e['symbol_id'],
            'Ambiguous lyric/event identity',
        )
        approved.append((item, lyric))
    return approved


def run(out):
    require(not out.exists(), 'Fresh output required')
    # Understood as: approve only reviewed event cores and separately approved SYS6 onsets.
    frozen_dirs = [PRIOR, OWNER, AUDIT, BASE]
    snapshots = {str(p): file_hashes(p) for p in frozen_dirs}
    verify_manifest(PRIOR, 'output-freeze.json')
    for folder, manifest in [
        (OWNER, 'prediction-freeze.json'),
        (BASE, 'prediction-freeze.json'),
        (AUDIT, 'audit-freeze.json'),
    ]:
        verify_manifest(folder, manifest)
    previous_validation = read(ROOT / 'docs/V4_GT17D_VALIDATION.json')
    for name, digest in previous_validation['artifact_sha256'].items():
        require(sha(PRIOR / name) == digest, 'GT17D artifact mismatch')
    source_hashes = read(PRIOR / 'preservation-verification.json')['source_hashes']
    for name, field in [
        ('source.png', 'source_sha256'),
        ('recognized.omr', 'omr_sha256'),
        ('visual-graph.json', 'graph_sha256'),
    ]:
        require(sha(SOURCE_DIR / name) == source_hashes[field], 'Original provenance mismatch')
    # GT17D already bound these histories; verify those exact recorded files again.
    for folder in read(PRIOR / 'preservation-verification.json')['historical_directories']:
        p = Path(folder)
        if p not in frozen_dirs:
            snapshots[str(p)] = file_hashes(p)
            if (p / 'prediction-freeze.json').exists():
                verify_manifest(p, 'prediction-freeze.json')
    plan = read(PRIOR / 'remaining-review-plan.json')
    inventory = read(OWNER / 'source-event-inventory.json')
    graph = read(SOURCE_DIR / 'visual-graph.json')
    approved = approved_scope(plan, inventory)
    lyrics = lyric_scope(plan, inventory)
    source = converter.parse(str(PRIOR / 'corrected-source.musicxml'))
    for _, item, event in approved:
        raw = graph['symbols'][event['symbol_id']]
        require(
            raw == event['source_symbol'] and raw['geometry']['bbox'] == event['source_bbox'],
            'Raw source mapping mismatch',
        )
        note = semantic_event(source, event['printed_measure'], event['onset'])
        require(
            ('REST' if note.isRest else 'NOTE') == event['kind']
            and (None if note.isRest else note.pitch.nameWithOctave) == event['pitch']
            and Fraction(note.duration.quarterLength) == Fraction(event['duration']),
            'Corrected XML event mismatch',
        )
        require(
            sha(Path(item['source_crop']['path'])) == item['source_crop']['sha256'],
            'Review crop changed',
        )
    for item, lyric in lyrics:
        require(
            sha(Path(item['source_crop']['path'])) == item['source_crop']['sha256'],
            'Lyric review crop changed',
        )
        note = at(source, lyric['measure'], lyric['onset'])
        require(
            [(l.number, l.text) for l in note.lyrics].count((lyric['row'], lyric['text'])) == 1,
            'XML lyric association mismatch',
        )
    out.mkdir(parents=True)
    bindings = {
        n: {'path': str(PRIOR / n), 'sha256': sha(PRIOR / n)}
        for n in [
            'owner-review-summary.md',
            'remaining-review-plan.json',
            'output-freeze.json',
            'owner-approved-4867-correction.json',
        ]
    }
    approval = {
        'starting_sha': START,
        'classification': 'OWNER_VERIFIED_SOURCE',
        'independent_ground_truth': 0,
        'event_approval_verbatim_excerpt': EVENT_APPROVAL,
        'approval_origin': 'Actual GT17E user instruction; excerpt preserved verbatim, no signature or timestamp invented.',
        'event_groups': GROUP_COUNTS,
        'approved_event_core_fields': CORE_FIELDS,
        'excluded_fields': [
            'new attachment or SIG classifications',
            'source completeness',
            'other lyric onsets',
            'continuations',
            'm28 ancestry',
            'repeat playback',
        ],
        'separate_sys6_lyric_approval': {
            'question_verbatim': LYRIC_QUESTION,
            'answer_verbatim': LYRIC_ANSWER,
            'group_id': 'SYS6_LYRIC_ONSET',
            'count': 40,
            'approved_fields': ['event_id', 'onset', 'row association'],
        },
        'review_bindings': bindings,
        'source_hashes': source_hashes,
        'event_records': [
            {
                'group_id': g,
                'case': i,
                'source_event_id': e['id'],
                'approved_core': {k: e[k] for k in CORE_FIELDS},
            }
            for g, i, e in approved
        ],
        'lyric_records': [{'case': i, 'source_lyric_record': l} for i, l in lyrics],
    }
    dump(out / 'owner-approval-record.json', approval)
    layer = {
        'classification': 'FIELD_SCOPED_OWNER_VERIFICATION',
        'independent_ground_truth': 0,
        'prior_layers': {
            'owner': sha(OWNER / 'owner-interpretation-layer.json'),
            '4867': sha(PRIOR / 'owner-approved-4867-correction.json'),
        },
        'approval_record_sha256': sha(out / 'owner-approval-record.json'),
        'event_core_overrides': [
            {
                'event_id': e['id'],
                'source_object_id': e['symbol_id'],
                'printed_measure': e['printed_measure'],
                'classification': 'OWNER_VERIFIED_SOURCE',
                'fields': {k: e[k] for k in CORE_FIELDS},
            }
            for _, _, e in approved
        ],
        'lyric_onset_overrides': [
            {
                'id': l['id'],
                'event_id': l['event_id'],
                'onset': l['onset'],
                'row': l['row'],
                'classification': 'OWNER_VERIFIED_SOURCE',
            }
            for _, l in lyrics
        ],
        'M28_CONTINUATION_LINEAGE': 'UNRESOLVED',
        'FULL_REPEAT_PLAYBACK': 'UNRESOLVED',
    }
    dump(out / 'owner-interpretation-layer.json', layer)
    approved_ids = {e['id'] for _, _, e in approved}
    lyric_ids = {l['id'] for _, l in lyrics}
    totals = {
        'recognized_event_cores': 169,
        'owner_confirmed_event_cores': 169,
        'provisional_event_cores': 0,
        'approved_chords': 24,
        'approved_lyric_wording_rows': 167,
        'verified_lyric_onsets': 128,
        'provisional_lyric_onsets': 39,
        'verified_continuations': 30,
        'provisional_continuations': 20,
        'unresolved_raw_sig_cases': 27,
        'independent_ground_truth': 0,
    }
    matrix = {
        'totals': totals,
        'source_completeness': 'UNVERIFIED',
        'rendering_completeness': 'INCOMPLETE',
        'event_cores': [
            {
                'event_id': e['id'],
                'source_object_id': e['symbol_id'],
                'measure': e['printed_measure'],
                'classification': 'OWNER_VERIFIED_SOURCE',
                'verification_origin': (
                    'GT17E' if e['id'] in approved_ids else 'PRIOR_OWNER_APPROVAL'
                ),
                'fields': {k: e[k] for k in CORE_FIELDS},
            }
            for e in inventory['events']
        ],
        'new_scope_lyric_associations': [
            {
                'id': l['id'],
                'event_id': l['event_id'],
                'classification': (
                    'OWNER_VERIFIED_SOURCE' if l['id'] in lyric_ids else 'OMR_PROVISIONAL'
                ),
            }
            for l in inventory['lyrics']
        ],
        'prior_verified_lyric_onsets': 88,
        'all_other_fields_inherit_prior_status': True,
    }
    require(
        len(matrix['event_cores']) == 169 and len(approved_ids) == 83 and len(lyric_ids) == 40,
        'Coverage mismatch',
    )
    dump(out / 'field-coverage-matrix.json', matrix)
    remaining = copy.deepcopy(plan)
    remaining['groups'] = [
        g for g in remaining['groups'] if g['group_id'] not in {*GROUP_COUNTS, 'SYS6_LYRIC_ONSET'}
    ]
    remaining['counts'] = {
        'provisional_events': 0,
        'lyric_onsets': 39,
        'visually_supported_continuations': 19,
        'm28_unresolved': 1,
        'raw_sig_cases': 27,
        'playback_decisions': 1,
        'field_items': 87,
        'coherent_groups': len(remaining['groups']),
    }
    require(sum(len(g['items']) for g in remaining['groups']) == 87, 'Remaining questions lost')
    remaining['new_owner_answers'] = 0
    dump(out / 'remaining-review-plan.json', remaining)
    text = [
        '# GT-17E 이후 남은 소유자 검토',
        '',
        '음악 이벤트 핵심 169개와 SYS6 가사 대응 40개는 승인 완료입니다. 원본 완전성이나 독립 정답 승인은 아닙니다.',
        '',
        '새 승인 대상: 나머지 가사 대응 39개, 연장선 19개와 m28 계보 1개, raw SIG 27개, 전체 재생 경로 1개. 기존 코드·가사 문구·음악 이벤트는 재확인하지 않습니다.',
        '',
        f'[기존 원본·후보 상세 안내]({PRIOR / "owner-review-summary.md"})',
        '아래 그룹 ID만 검토하세요. 답변은 CONFIRM / CORRECT(사례 ID·필드) / UNCERTAIN으로 할 수 있으며 현재 모두 미응답입니다.',
        '',
    ]
    for g in remaining['groups']:
        text.extend(
            [
                f'## {g["group_id"]} — 인쇄 {g["printed_measures"]}',
                ', '.join(i['id'] for i in g['items']),
                '답변: ______',
                '',
            ]
        )
    (out / 'remaining-owner-review-summary.md').write_text('\n'.join(text) + '\n')
    guards = {}
    curves = read(OWNER / 'owner-interpretation-layer.json')['curve_interpretations']
    for name, shift in [('A', -1), ('G', -3)]:
        target = converter.parse(str(PRIOR / f'{name}-corrected.musicxml'))
        guards[name] = validate(source, target, shift, 'key').to_dict()
        require(guards[name]['ok'], 'Unchanged V3 guard failed')
        relationship_signature(target, curves)
    rel = relationship_inventory(source)
    require(
        len(rel['slurs']) == 1
        and all(s[0] != ((0, 21, '3'), (0, 21, '13/4')) for s in rel['slurs']),
        '4867 correction lost',
    )
    relationship_signature(source, curves)
    dump(
        out / 'semantic-validation.json',
        {
            'unchanged_v3_guards': guards,
            'approved_curves_preserved': True,
            '4867_correction_preserved': True,
            'event_semantics_changed': False,
            'xml_regenerated': False,
            'png_regenerated': False,
            'source_completeness': 'UNVERIFIED',
            'independent_ground_truth': 0,
        },
    )
    for name, field in [
        ('source.png', 'source_sha256'),
        ('recognized.omr', 'omr_sha256'),
        ('visual-graph.json', 'graph_sha256'),
    ]:
        require(sha(SOURCE_DIR / name) == source_hashes[field], 'Original changed during run')
    require(
        all(file_hashes(Path(p)) == h for p, h in snapshots.items()), 'Historical evidence changed'
    )
    dump(
        out / 'preservation-verification.json',
        {
            'historical_files_unchanged': True,
            'historical_directory_file_hashes': snapshots,
            'source_hashes': source_hashes,
            'xml_and_png_status': 'NOT_WRITTEN_OR_REGENERATED',
            'production_changes': False,
        },
    )
    dump(
        out / 'output-freeze.json',
        {'files': file_hashes(out), 'producer_sha256': sha(Path(__file__)), 'starting_sha': START},
    )
    print(totals)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
