"""Full original-side source packet. Candidate readings never confer ownership."""

import copy
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

from music21 import harmony, note, stream
from scripts.research.gt11_complete_measure import events_of, read, require
from scripts.research.gt12_render_context import ink_bbox
from scripts.research.gt14c_continuation_audit import save_native
from scripts.research.gt16_fourth_system import measure_inventory
from scripts.research.gt17_fifth_system import CANDIDATES as FIFTH, SOURCE_DIR, GT02
from scripts.research.paired_ground_truth_01 import dump, sha
from backend.omr_v3.chords import chord_symbol_from_text

RANGES = [(1, 4), (5, 8), (9, 12), (13, 16), (17, 19), (20, 24), (25, 29), (30, 33), (34, 37)]
# Transcribed only from the original Bb source. All new rows/associations remain candidates.
ROWS = {
    20: ([1, 2, 3], '나 의 맘', '나 의 삶'),
    21: ([1.5, 1.75, 2, 2.5, 2.75, 3.25, 3.75], '주 의 성 전 이 되 어', '주 의 말 씀 을 따 라'),
    22: ([1, 2, 3], '영 원 한', '이 루 실'),
    23: ([1.5, 1.75, 2, 2.5, 2.75, 3.25, 3.75], '주 의 말 씀 을 향 해', '주 의 나 라 를 향 해'),
    25: ([1.5, 1.75, 2, 2.5, 2.75, 3.25, 3.75], '주 의 마 음 있 는 곳', '주 의 시 선 있 는 곳'),
    26: ([3, 3.5], '으 로', ''),
    30: ([1, 2, 3], '주 님 의', ''),
    31: ([0, 1, 1.5, 2.5, 3.5], '마 음 있 는 곳', ''),
    32: ([1, 2, 3], '주 님 의', ''),
    33: ([0, 1, 1.5, 2.5, 3.5], '시 선 있 는 곳', ''),
    35: ([1.5, 1.75, 2, 2.5, 2.75, 3.5, 3.75], '내 가 있 기 원 하 네', ''),
}
CHORDS = {
    20: ('Bb', [340, 2121, 380, 2155]),
    22: ('F', [1255, 2120, 1295, 2155]),
    24: ('Gm7', [2214, 2120, 2305, 2160]),
    25: ('Bb/D', [277, 2471, 357, 2509]),
    26: ('Eb', [1076, 2471, 1115, 2501]),
    27: ('F', [1435, 2470, 1470, 2505]),
    28: ('Eb', [1878, 2471, 1916, 2501]),
    30: ('Bb', [339, 2821, 377, 2851]),
    32: ('F', [1375, 2820, 1410, 2855]),
    34: ('Gm', [275, 3170, 340, 3207]),
    35: ('Bb/D', [718, 3172, 798, 3209]),
    36: ('Eb', [1654, 3172, 1693, 3201]),
}
MARKS = [
    (21, 3, 1, '이'),
    (21, 3, 2, '을'),
    (22, 0, 1, '어'),
    (22, 0, 2, '라'),
    (23, 3, 1, '을'),
    (23, 3, 2, '를'),
    (24, 0, 1, '해'),
    (24, 0, 2, '해'),
    (25, 3, 1, '있'),
    (25, 3, 2, '있'),
    (26, 0, 1, '곳'),
    (26, 0, 2, '곳'),
    (27, 0, 1, '로'),
    (28, 0, 1, '곳'),
    (31, 2, 1, '있'),
    (31, 3, 1, '는'),
    (33, 2, 1, '있'),
    (33, 3, 1, '는'),
    (34, 0, 1, '곳'),
    (35, 3, 1, '원'),
]
# Missing semantic relationships are not repaired or silently rendered as verified ties.
MISSING_TIES = [
    {'measure': 21, 'onset': '15/4', 'to_measure': 22, 'to_onset': '0'},
    {'measure': 31, 'onset': '5/2', 'to_measure': 31, 'to_onset': '3'},
    {'measure': 33, 'onset': '5/2', 'to_measure': 33, 'to_onset': '3'},
    {'measure': 35, 'onset': '11/4', 'to_measure': 35, 'to_onset': '3'},
]


def full_inventory(score, graph, original):
    rows = read(GT02 / 'note-correspondence-diagnostic.json')['events']['Bb']
    systems = []
    all_events = []
    lyrics = []
    marks = []
    chords = []
    for index, (start, end) in enumerate(RANGES, 1):
        staff = next(s for s in graph['staves'] if s['id'] == f'sheet#1:{index}')
        cy = staff['lines'][2][0][1]
        view = [
            130,
            min(int(cy - 170), {6: 2040, 8: 2745}.get(index, int(cy - 170))),
            2430,
            min(3430, int(cy + 220)),
        ]
        candidates = {n: dict(FIFTH[n]) if index == 5 else {} for n in range(start, end + 1)}
        records = measure_inventory(score, graph, rows, staff, range(start, end + 1), candidates)
        for m in records:
            m['classification'] = 'OWNER_VERIFIED_SOURCE' if index <= 5 else 'OMR_PROVISIONAL'
            for e in m['events']:
                e['source_verification'] = 'OWNER_VERIFIED_SOURCE' if index <= 5 else 'UNVERIFIED'
                e['render_evidence'] = 'OWNER_VERIFIED_SOURCE' if index <= 5 else 'OMR_PROVISIONAL'
                e['part'] = 1
                e['full_measure_rest'] = bool(e['kind'] == 'REST' and e['duration'] == '4')
                all_events.append(e)
        objects = [s for s in graph['symbols'].values() if s['system'] == staff['system']]
        object_ids = {s['id'] for s in objects}
        systems.append(
            {
                'omr_objects': objects,
                'omr_relations': [
                    r
                    for r in graph['relations']
                    if object_ids.intersection((r['source'], r['target']))
                ],
                'section_candidates': (
                    [
                        {
                            'text': 'Chorus',
                            'word_id': 'sheet#1:5216',
                            'frame_ids': ['sheet#1:5190', 'sheet#1:5191'],
                            'classification': 'AGENT_VISUAL_CANDIDATE_SECTION_FRAME_NOT_MUSICAL_ENDING',
                            'owner_answer': None,
                        }
                    ]
                    if index == 6
                    else (
                        [
                            {
                                'text': 'Tag',
                                'word_id': 'sheet#1:5222',
                                'classification': 'AGENT_VISUAL_CANDIDATE',
                                'owner_answer': None,
                            }
                        ]
                        if index == 8
                        else []
                    )
                ),
                'system': index,
                'staff': staff,
                'printed_measures': list(range(start, end + 1)),
                'view': view,
                'measures': records,
                'classification': 'OWNER_VERIFIED_SOURCE' if index <= 5 else 'OMR_PROVISIONAL',
            }
        )
        if index <= 5:
            continue
        events = {(m['printed_measure'], e['onset']): e for m in records for e in m['events']}
        for n in range(start, end + 1):
            if n in ROWS:
                onsets, upper, lower = ROWS[n]
                for row, text in enumerate([upper, lower], 1):
                    for onset, syllable in zip(onsets, text.split()):
                        off = str(Fraction(onset))
                        e = events[(n, off)]
                        x = e['physical_source_center'][0]
                        top = cy + 73.5 + (row - 1) * 45
                        window = [round(x - 25), round(top - 5), round(x + 25), round(top + 45)]
                        lyrics.append(
                            {
                                'id': f'm{n}-r{row}-o{off}',
                                'measure': n,
                                'row': row,
                                'onset': off,
                                'text': syllable,
                                'event_id': e['id'],
                                'source_window': window,
                                'source_dark_bbox': ink_bbox(original, window),
                                'classification': 'AGENT_VISUAL_CANDIDATE',
                                'owner_answer': None,
                                'original_omr_lyrics': e['omr_lyrics'],
                            }
                        )
            if n in CHORDS:
                text, window = CHORDS[n]
                objects = [
                    s['id']
                    for s in graph['symbols'].values()
                    if s['system'] == staff['system']
                    and s['kind'] in ('word', 'chord-name')
                    and overlaps(s['geometry']['bbox'], window)
                ]
                chords.append(
                    {
                        'id': f'm{n}-chord',
                        'measure': n,
                        'text': text,
                        'source_window': window,
                        'source_dark_bbox': ink_bbox(original, window),
                        'source_objects': objects,
                        'classification': 'AGENT_VISUAL_CANDIDATE',
                        'owner_answer': None,
                    }
                )
        for n, onset, row, syllable in MARKS:
            if start <= n <= end:
                off = str(Fraction(onset))
                e = events[(n, off)]
                x = e['physical_source_center'][0]
                yy = cy + 89 + (row - 1) * 45
                window = [round(x - 28), round(yy - 9), round(x + 28), round(yy + 10)]
                marks.append(
                    {
                        'id': f'm{n}-r{row}-stroke-{off}',
                        'measure': n,
                        'onset': off,
                        'row': row,
                        'held_syllable_candidate': syllable,
                        'source_window': window,
                        'source_dark_bbox': ink_bbox(original, window),
                        'event_id': e['id'],
                        'classification': 'AGENT_VISUAL_CANDIDATE',
                        'owner_answer': None,
                        'association_caveat': (
                            'm28 second ending: held syllable lineage needs repeat interpretation'
                            if n == 28
                            else None
                        ),
                    }
                )
    unresolved = []
    for s in graph['symbols'].values():
        if s['kind'] in ('articulation', 'fermata') and s['source_id'] not in (
            '5686',
            '5699',
            '5747',
            '5762',
            '5999',
            '6001',
        ):
            unresolved.append(
                {
                    'id': s['id'],
                    'original_observation': s,
                    'relations': [
                        r for r in graph['relations'] if s['id'] in (r['source'], r['target'])
                    ],
                    'classification': 'UNRESOLVED',
                    'owner_answer': None,
                    'rendered': False,
                }
            )
    for s in graph['symbols'].values():
        if (
            s['kind'] == 'slur'
            and s['system'] in [f'sheet#1:system:{i}' for i in range(6, 10)]
            and ET.fromstring(s['source_xml']).get('tie') != 'true'
        ):
            unresolved.append(
                {
                    'id': s['id'],
                    'original_observation': s,
                    'classification': 'UNRESOLVED',
                    'owner_answer': None,
                    'rendered': False,
                }
            )
    for t in MISSING_TIES:
        unresolved.append(
            {
                'id': f'missing-tie-m{t["measure"]}-{t["onset"]}',
                **t,
                'classification': 'AGENT_VISUAL_CANDIDATE',
                'original_omr_relation': None,
                'rendered': False,
                'owner_answer': None,
            }
        )
    for u in unresolved:
        if 'to_measure' in u:
            a = next(
                e
                for e in all_events
                if e['printed_measure'] == u['measure'] and e['onset'] == u['onset']
            )
            b = next(
                e
                for e in all_events
                if e['printed_measure'] == u['to_measure'] and e['onset'] == u['to_onset']
            )
            u['source_window'] = [
                int(a['source_bbox'][0]) - 5,
                int(min(a['source_bbox'][1], b['source_bbox'][1])) - 35,
                int(b['source_bbox'][2]) + 5,
                int(max(a['source_bbox'][3], b['source_bbox'][3])) + 8,
            ]
            u['endpoint_source_ids'] = [a['symbol_id'], b['symbol_id']]
            u['recognized_endpoint_pitches'] = [a['pitch'], b['pitch']]
            u['candidate_kind'] = 'POSSIBLE_TIE_OR_SLUR_NOT_OWNER_VERIFIED'
            u['semantic_gap'] = (
                'No original serialized tie relationship; do not repair from visual candidate'
            )
    return {
        'systems': systems,
        'events': all_events,
        'lyrics': lyrics,
        'continuations': marks,
        'chords': chords,
        'unresolved_objects': unresolved,
        'independent_ground_truth': False,
        'new_owner_answers': 0,
        'source_completeness': 'UNVERIFIED',
        'repeat_playback': 'UNRESOLVED_NO_JUMPS_INFERRED',
    }


def overlaps(a, b):
    return bool(a and b and max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3]))


def owner_augmented(source):
    result = copy.deepcopy(source)
    m = list(result.parts[0].getElementsByClass(stream.Measure))[16]
    require(not list(m.getElementsByClass(harmony.ChordSymbol)), 'Unexpected m17 harmony')
    m.insert(0, chord_symbol_from_text('Bb/D'))
    for n in events_of(m):
        n.lyrics = []
    for onset, text in zip(['3/2', '2', '5/2', '7/2'], ['이', '루', '시', '네']):
        ns = [n for n in events_of(m) if Fraction(n.getOffsetInHierarchy(m)) == Fraction(onset)]
        require(len(ns) == 1 and ns[0].isNote, 'Approved association mismatch')
        ns[0].lyrics.append(note.Lyric(text=text, number=1))
    return result


def review_packet(out, inventory, graph, source):
    packet = out / 'owner-review'
    packet.mkdir()
    import shutil

    shutil.copyfile(SOURCE_DIR / 'source.png', packet / 'full-original-bb-page.png')
    mappings = []
    for sys in inventory['systems'][5:]:
        mappings.append(
            save_native(source, sys['view'], packet / f'source-system-{sys["system"]}.png')
        )
        for m in sys['measures']:
            b = m['omr_bounds']
            box = [
                max(130, int(b[0]) - 8),
                sys['view'][1],
                min(2430, int(b[2]) + 8),
                sys['view'][3],
            ]
            mappings.append(
                save_native(source, box, packet / f'source-m{m["printed_measure"]}.png')
            )
    for u in inventory['unresolved_objects']:
        if (
            'original_observation' in u
            and int((u['original_observation'].get('system') or 'sheet#1:system:0').split(':')[-1])
            >= 6
        ):
            b = u['original_observation']['geometry']['bbox']
            mappings.append(
                save_native(
                    source,
                    [int(b[0]) - 15, int(b[1]) - 15, int(b[2]) + 15, int(b[3]) + 15],
                    packet / (u['id'].replace(':', '_') + '.png'),
                )
            )
    for u in inventory['unresolved_objects']:
        if 'source_window' in u:
            mappings.append(
                save_native(
                    source,
                    u['source_window'],
                    packet / (u['id'].replace(':', '_').replace('/', '_') + '.png'),
                )
            )
    for c in inventory['continuations'] + inventory['chords']:
        mappings.append(
            save_native(source, c['source_window'], packet / (c['id'].replace('/', '_') + '.png'))
        )
    dump(packet / 'crop-map.json', mappings)
    checklist = {
        'classification': 'OWNER_REVIEW_PENDING_NOT_INDEPENDENT_GROUND_TRUTH',
        'source_sha256': sha(SOURCE_DIR / 'source.png'),
        'systems': [
            dict(
                s,
                owner_answer=None,
                measures=[
                    dict(
                        m,
                        owner_answer=None,
                        events=[dict(e, owner_answer=None) for e in m['events']],
                        chord_absence_answer=None,
                        lower_row_absence_answer=None,
                    )
                    for m in s['measures']
                ],
            )
            for s in inventory['systems'][5:]
        ],
        'chords': inventory['chords'],
        'lyrics': inventory['lyrics'],
        'continuations': inventory['continuations'],
        'unresolved': inventory['unresolved_objects'],
        'repeat_playback_answer': None,
        'instructions': 'Reply by measure/onset or object ID: CONFIRM / CORRECT with correction / UNCERTAIN. Do not infer absent content from blanks. No target predictions are part of this packet.',
    }
    dump(out / 'full-source-owner-review-checklist.json', checklist)
    dump(packet / 'owner-review-checklist.json', checklist)
    dump(
        packet / 'packet-freeze.json',
        {
            'files': {p.name: sha(p) for p in sorted(packet.iterdir()) if p.is_file()},
            'source_sha256': sha(SOURCE_DIR / 'source.png'),
        },
    )
