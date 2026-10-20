"""Source-only GT-15A packet; never render targets or populate owner responses."""

import argparse
import copy
import shutil
from fractions import Fraction
from pathlib import Path

from PIL import Image

from scripts.research.gt11_complete_measure import read, require
from scripts.research.paired_ground_truth_01 import dump, file_hashes, sha

BASE = '08a9af470907f7bb54733585a18f7bd7d509752e'
PRIOR = Path('/private/tmp/capomatic-v4-gt15/gt15-final-output')
GT14E = Path('/private/tmp/capomatic-v4-gt14e/gt14e-final-output')
SOURCE_DIR = Path(
    '/private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output/predictions/baseline-exec/source'
)
ROOT = Path(__file__).resolve().parents[2]


def relations(graph, sid):
    return [r for r in graph['relations'] if sid in (r['source'], r['target'])]


def build_checklist(inv, graph):
    """Keep observations immutable; put unanswered review fields in a separate layer."""
    items, events, lyric_map = [], {}, {}

    def add(ident, kind, candidate, status='AGENT_VISUAL_CANDIDATE'):
        items.append(
            {
                'id': ident,
                'kind': kind,
                'candidate_status': status,
                'candidate': copy.deepcopy(candidate),
                'owner_response': None,
                'owner_correction': None,
                'owner_uncertainty': None,
            }
        )

    for m in inv['measures']:
        number = m['printed_measure']
        for n, e in enumerate(m['events'], 1):
            require(
                e['render_evidence'] == 'OMR_PROVISIONAL'
                and e['source_verification'] == 'UNVERIFIED',
                'Unexpected promoted source event',
            )
            events[e['symbol_id']] = e
            ids = [e['symbol_id'], *e['stem_ids']]
            lineage = [
                r for r in graph['relations'] if any(s in (r['source'], r['target']) for s in ids)
            ]
            add(
                f'm{number}-event-{n}',
                'MUSIC_EVENT',
                {
                    **e,
                    'source_relations': lineage,
                    'source_components': {
                        sid: graph['symbols'][sid]
                        for sid in sorted(
                            set(ids) | {r[k] for r in lineage for k in ('source', 'target')}
                        )
                        if sid in graph['symbols']
                    },
                },
                'OMR_PROVISIONAL',
            )
        c = m['agent_candidates']
        add(
            f'm{number}-chord',
            'CHORD_OR_ABSENCE',
            {
                'printed_measure': number,
                'printed_chord_candidate': c['chord'],
                'absence_scope': 'NO_NEW_PRINTED_CHORD_CANDIDATE' if c['chord'] is None else None,
                'suffix_bass_alteration': 'NONE_VISUALLY_IDENTIFIED_UNVERIFIED',
                'source_image': f'frozen/source-measure-{number}.png',
                'recognized_harmonies': m['recognized_harmonies'],
                'question': 'Confirm/correct printed chord, suffix, bass and placement; absence means no NEW printed chord, not harmonic silence.',
            },
        )
        for row, key in [(1, 'upper'), (2, 'lower')]:
            require(len(c[key]) == len(c['onsets']), 'Incomplete lyric associations')
            for onset, syllable in zip(c['onsets'], c[key]):
                matches = [e for e in m['events'] if e['onset'] == onset and e['kind'] == 'NOTE']
                require(len(matches) == 1, 'Lyric has no unique candidate note')
                event = matches[0]
                lyric_map[(event['symbol_id'], row)] = syllable
                add(
                    f'm{number}-row{row}-syllable-{onset}',
                    'LYRIC_ASSOCIATION',
                    {
                        'printed_measure': number,
                        'row': row,
                        'syllable': syllable,
                        'onset': onset,
                        'head_id': event['symbol_id'],
                        'source_head_bbox': event['source_bbox'],
                        'source_image': f'frozen/source-measure-{number}.png',
                    },
                )
        add(
            f'm{number}-additional',
            'SOURCE_COMPLETENESS',
            {
                'printed_measure': number,
                'question': 'Are any additional notes/rests, accidentals, symbols, lyric syllables or continuation strokes missing from these candidates?',
            },
        )

    ties = []
    for s in graph['symbols'].values():
        if s['system'] != inv['staff']['system'] or s['kind'] != 'slur':
            continue
        require('tie="true"' in s['source_xml'], 'Unclassified source curve')
        rel = relations(graph, s['id'])
        head_ids = [r['target'] for r in rel if r['source'] == s['id'] and r['kind'] == 'slur-head']
        require(len(head_ids) == 2 and all(h in events for h in head_ids), 'Unbound tie endpoint')
        endpoints = sorted(
            (events[h] for h in head_ids),
            key=lambda e: (e['printed_measure'], Fraction(e['onset'])),
        )
        a, b = endpoints
        require(
            a['tie'] == 'start' and b['tie'] == 'stop' and a['pitch'] == b['pitch'],
            'Tie candidate inconsistency',
        )
        tie = {
            'source_symbol': s,
            'source_relations': rel,
            'endpoints': [
                {
                    k: e[k]
                    for k in (
                        'symbol_id',
                        'printed_measure',
                        'onset',
                        'duration',
                        'pitch',
                        'tie',
                        'source_bbox',
                    )
                }
                for e in endpoints
            ],
        }
        ties.append(tie)
        add(s['id'], 'TIE', tie, 'OMR_PROVISIONAL')

    for n, mark in enumerate(inv['continuation_candidates'], 1):
        candidates = [
            t
            for t in ties
            if t['endpoints'][1]['printed_measure'] == mark['measure']
            and t['endpoints'][1]['onset'] == mark['onset_candidate']
        ]
        require(len(candidates) == 1, 'Continuation has no unique candidate tie context')
        t = candidates[0]
        start = t['endpoints'][0]
        syllable = lyric_map.get((start['symbol_id'], mark['row']))
        require(syllable is not None, 'Continuation syllable candidate absent')
        add(
            f'continuation-{n:02}',
            'CONTINUATION_STROKE',
            {
                **mark,
                'associated_syllable_candidate': syllable,
                'tie_source_id': t['source_symbol']['id'],
                'candidate_tie_endpoints': t['endpoints'],
                'source_image': f'continuation-{n:02}.png',
                'bbox_caveat': 'dark-support bbox is frozen diagnostic support, NOT exact text ownership',
            },
        )
    for obj in inv['ambiguous_SIG_objects']:
        sid = obj['symbol']['id']
        overlapping = [
            i['id']
            for i in items
            if i['kind'] == 'CONTINUATION_STROKE'
            and _overlap(obj['symbol']['geometry']['bbox'], i['candidate']['source_window'])
        ]
        add(
            sid,
            'AMBIGUOUS_SIG_OBJECT',
            {
                **obj,
                'overlapping_continuation_candidates': overlapping,
                'source_image': f'frozen/source-ambiguous-{sid.split(":")[-1]}.png',
                'question': 'Classify from source: music articulation, lyric glyph stroke, lyric continuation, other or uncertain. Overlapping items can describe the SAME stroke; do not count twice.',
            },
        )
    add('m10-upper-onset1-no-dash', 'NEGATIVE_OBSERVATION', inv['explicit_negative_observation'])
    add('m8-m9-ending-transition', 'REPEAT_ENDING', inv['repeat_context'])
    require(len(events) == 20 and len(ties) == 6 and len(lyric_map) == 20, 'Fixed scope mismatch')
    return {
        'base_sha': BASE,
        'source_sha256': inv['source_sha256'],
        'review_type': 'OWNER_REVIEW_PENDING',
        'independent_ground_truth': False,
        'owner_verified_source': False,
        'understood_as': 'Prepare source-only candidates for explicit owner review; no approvals, target rendering or interpretation promotion.',
        'coordinate_convention': 'Original page x right/y down, integer pixel indices; bboxes right/bottom exclusive. Raw OMR float geometry preserved separately. Onsets/durations in quarterLength.',
        'allowed_answers': ['CONFIRM', 'CORRECT', 'UNCERTAIN'],
        'items': items,
        'scope': {
            'events': 20,
            'ties': 6,
            'chord_or_absence_items': 4,
            'syllable_associations': 20,
            'continuation_strokes': 11,
            'ambiguous_SIG_objects': 5,
        },
    }


def _overlap(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def compact_markdown(checklist):
    lines = [
        '# GT-15A 원본 소유자 검토',
        '',
        '원본 Bb PDF 2쪽의 인쇄 9–12마디만 검토합니다. 모든 내용은 미확인 후보입니다.',
        'OWNER_REVIEW이며 독립 정답이 아닙니다. 코드·가사·음표를 직접 대조하고 확인/수정/불확실로 답해 주세요.',
        'onset/duration 단위는 4분음표 길이입니다. 음높이는 원본의 높은음자리표·Bb 조표 문맥 후보입니다.',
        '그림은 원본 픽셀만 포함합니다. 표에는 검토용 OMR/에이전트 후보가 있어 맹검 검토가 아닙니다.',
        '각 항목 답변은 비어 있습니다. 전체 승인 없이 부분적으로 확인·수정할 수 있습니다.',
        '',
        '| ID | 유형 | 후보 | 소유자 답변·수정·불확실성 |',
        '|---|---|---|---|',
    ]
    for i in checklist['items']:
        c, k = i['candidate'], i['kind']
        if k == 'MUSIC_EVENT':
            detail = f"m{c['printed_measure']} onset {c['onset']} / {c['pitch'] or '쉼표'} / 길이 {c['duration']}; stem {c['stem_direction']}; beam {c['beams']}; tie {c['tie']}; required {c.get('required_capabilities', [])}"
        elif k == 'LYRIC_ASSOCIATION':
            detail = f"m{c['printed_measure']} {'위' if c['row']==1 else '아래'} '{c['syllable']}' → onset {c['onset']}"
        elif k == 'CONTINUATION_STROKE':
            detail = f"m{c['measure']} {'위' if c['row']==1 else '아래'} onset {c['onset_candidate']} '{c['associated_syllable_candidate']}' 연장 후보; {c['source_image']}"
        elif k == 'TIE':
            a, b = c['endpoints']
            detail = f"m{a['printed_measure']}:{a['onset']} {a['pitch']} → m{b['printed_measure']}:{b['onset']} {b['pitch']}"
        elif k == 'CHORD_OR_ABSENCE':
            detail = f"m{c['printed_measure']} 새 코드 {c['printed_chord_candidate'] or '없음 후보'}; suffix/슬래시/변화음·원래 배치 확인"
        elif k == 'AMBIGUOUS_SIG_OBJECT':
            detail = f"원 OMR {c['symbol']['shape']}; bbox {c['symbol']['geometry']['bbox']}; 겹치는 연장선 항목 {c['overlapping_continuation_candidates']}"
        elif k == 'REPEAT_ENDING':
            detail = 'm8 1번 괄호·도돌이표와 m9 열린 2번 괄호; 1회차 되돌아감/2회차 m8 건너 m9 진행 후보. 반복 경로를 확인·수정해 주세요.'
        elif k == 'NEGATIVE_OBSERVATION':
            detail = 'm10 위 onset 1: 관찰된 대시 없음 후보. 아래 행을 복사해 대시를 만들지 않았습니다. 별도 표기가 보이면 수정해 주세요.'
        else:
            detail = f"m{c['printed_measure']} 추가/누락 기호·가사·연장선 확인"
        lines.append(f"| {i['id']} | {k} | {detail} | |")
    lines += [
        '',
        '추가 자료: 원본 전체 source-only-owner-review-sheet.png, 마디/미분류 crop은 frozen/, 각 연장선 crop은 continuation-XX.png.',
        '모든 bbox/관계/음절 대응은 owner-approval-checklist.json 및 per-measure-inventory.json에 보존됩니다.',
        '승인은 OWNER_VERIFIED_SOURCE 범위만 가능하며 원본 잉크 제거·보호 마스크 변경·합성 승인이 아닙니다.',
        '',
    ]
    return '\n'.join(lines)


def run(out):
    require(not out.exists(), 'Fresh output directory required')
    expected = read(ROOT / 'docs/V4_GT15_VALIDATION.json')
    require(
        expected['base_sha'] == '13b2313cf79bee39508a5f12994be6b5a8c378f3', 'Wrong GT15 lineage'
    )
    for name, h in expected['artifact_sha256'].items():
        require(sha(PRIOR / name) == h, f'GT15 artifact mismatch: {name}')
    for name, h in read(PRIOR / 'prediction-freeze.json')['files'].items():
        require(sha(PRIOR / name) == h, f'GT15 prediction freeze mismatch: {name}')
    for name, h in read(GT14E / 'prediction-freeze.json')['files'].items():
        require(sha(GT14E / name) == h, f'GT14E freeze mismatch: {name}')
    inv = read(PRIOR / 'source-event-inventory.json')
    binding = read(PRIOR / 'input-freeze.json')
    for name, key in [
        ('source.png', 'source_sha256'),
        ('visual-graph.json', 'graph_sha256'),
        ('recognized.omr', 'omr_sha256'),
    ]:
        require(sha(SOURCE_DIR / name) == binding[key], f'Source provenance mismatch: {name}')
    require(inv['source_sha256'] == binding['source_sha256'], 'Inventory/source binding mismatch')
    graph = read(SOURCE_DIR / 'visual-graph.json')
    source = Image.open(SOURCE_DIR / 'source.png')
    history = {str(p): file_hashes(p) for p in (PRIOR, GT14E)}
    frozen = PRIOR / 'owner-review'
    for n, h in read(frozen / 'owner-packet-freeze.json')['files'].items():
        require(sha(frozen / n) == h, f'Original packet mismatch: {n}')
    checklist = build_checklist(inv, graph)
    out.mkdir(parents=True)
    shutil.copytree(frozen, out / 'frozen')
    shutil.copyfile(
        frozen / 'source-third-system-native.png', out / 'source-only-owner-review-sheet.png'
    )
    crop_map = read(frozen / 'source-review-crop-map.json')
    crop_map += [r['native_crop'] for r in read(frozen / 'ambiguous-object-review.json')]
    for c in crop_map:
        image = Image.open(out / 'frozen' / c['file'])
        tile = source.crop(c['page_bbox'])
        require(
            sha(out / 'frozen' / c['file']) == c['sha256']
            and image.size == tile.size
            and image.mode == tile.mode
            and image.tobytes() == tile.tobytes(),
            'Native crop mismatch',
        )
    new_crops = []

    def crop(name, bbox):
        require(
            all(isinstance(v, int) for v in bbox)
            and 0 <= bbox[0] < bbox[2] <= source.width
            and 0 <= bbox[1] < bbox[3] <= source.height,
            'Invalid source crop',
        )
        source.crop(bbox).save(out / name)
        tile = Image.open(out / name)
        require(
            tile.mode == source.mode and tile.tobytes() == source.crop(bbox).tobytes(),
            'Crop pixel mismatch',
        )
        new_crops.append(
            {
                'file': name,
                'page_bbox': bbox,
                'size': list(tile.size),
                'mode': tile.mode,
                'scale': 1,
                'sha256': sha(out / name),
                'source_pixel_equality': True,
            }
        )

    for i in checklist['items']:
        if i['kind'] == 'CONTINUATION_STROKE':
            crop(i['candidate']['source_image'], i['candidate']['source_window'])
    crop('first-second-ending-native.png', [130, 690, 2430, 1390])
    crop('m8-first-ending-native.png', [1920, 690, 2430, 1030])
    crop('m9-second-ending-native.png', [130, 1030, 835, 1390])
    dump(out / 'owner-approval-checklist.json', checklist)
    dump(
        out / 'per-measure-inventory.json',
        {
            'source_sha256': inv['source_sha256'],
            'classification': 'UNVERIFIED_CANDIDATES',
            'measures': inv['measures'],
            'review_items': checklist['items'],
        },
    )
    dump(out / 'crop-map.json', {'frozen_native_crops': crop_map, 'new_native_crops': new_crops})
    (out / 'OWNER_REVIEW.md').write_text(compact_markdown(checklist))
    require(
        all(
            i['owner_response'] is None
            and i['owner_correction'] is None
            and i['owner_uncertainty'] is None
            for i in checklist['items']
        ),
        'Owner answer fabrication',
    )
    require(
        all(file_hashes(Path(p)) == h for p, h in history.items()), 'Historical evidence mutated'
    )
    dump(
        out / 'evidence-verification.json',
        {
            'base_sha': BASE,
            'source_sha256': sha(SOURCE_DIR / 'source.png'),
            'source_omr_graph_hashes_verified': True,
            'input_sha256': {
                k: binding[k] for k in ('source_sha256', 'omr_sha256', 'graph_sha256')
            },
            'original_inventory_sha256': sha(PRIOR / 'source-event-inventory.json'),
            'original_owner_packet_freeze_sha256': sha(frozen / 'owner-packet-freeze.json'),
            'GT15_prediction_freeze_sha256': sha(PRIOR / 'prediction-freeze.json'),
            'GT14E_prediction_freeze_sha256': sha(GT14E / 'prediction-freeze.json'),
            'GT14E_GT15_freezes_verified': True,
            'original_packet_all_bytes_preserved': file_hashes(out / 'frozen')
            == file_hashes(frozen),
            'native_crop_pixel_equality': True,
            'owner_responses_received': 0,
            'independent_ground_truth': False,
            'new_target_predictions': False,
            'scope': checklist['scope'],
            'review_items': len(checklist['items']),
            'status': 'OWNER_REVIEW_PENDING',
        },
    )
    dump(
        out / 'packet-freeze.json',
        {
            'base_sha': BASE,
            'files': file_hashes(out),
            'status': 'OWNER_REVIEW_PENDING_NOT_INDEPENDENT_GROUND_TRUTH',
        },
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    run(parser.parse_args().out)
