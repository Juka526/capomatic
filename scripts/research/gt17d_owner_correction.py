"""Remove only owner-classified glyph 4867's erroneous XML slur, research-only."""

import argparse
import copy
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

from music21 import converter, spanner, stream
from PIL import Image

from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt11_complete_measure import read, require, events_of
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.gt16_fourth_system import repeat_signature
from scripts.research.gt17b_owner_integration import (
    BASE,
    SOURCE_DIR,
    at,
    core_signature,
    relationship_signature,
    verify_manifest,
)
from scripts.research.gt17b_full_score import binding
from scripts.research.gt17c_accuracy_audit import OWNER, xml_curve_audit, xml_lyric_extension_audit
from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes

ROOT = Path(__file__).resolve().parents[2]
AUDIT = Path('/private/tmp/capomatic-v4-gt17c/gt17c-frozen-output')
START = '477b418d982c95c430531ba46d999cd40448e2e2'
APPROVAL = '동의합니다'
APPROVAL_CONTEXT = '''The owner reviewed the previous GT-17C source analysis and explicitly responded:

"동의합니다"

The approved interpretation is:

- `sheet#1:4867` belongs to the Korean lyric glyph '되'.
- It is NOT a musical slur.
- The inherited MusicXML slur associated with this raw object must be removed from a new, separately augmented semantic source.
- The underlying note/rest events must remain unchanged.
- The original Korean lyric must remain unchanged.

This approval is limited to the specific source classification and erroneous slur interpretation.'''
ENDPOINTS = [('sheet#1:2143', '3', 'C5'), ('sheet#1:2191', '13/4', 'B-4')]


def tree_fingerprint(element):
    return (
        element.tag,
        tuple(sorted(element.attrib.items())),
        (element.text or '').strip(),
        tuple(tree_fingerprint(c) for c in element if isinstance(c.tag, str)),
    )


def relationship_inventory(score):
    addresses = {}
    ties = []
    for p, part in enumerate(score.parts):
        for m, measure in enumerate(part.getElementsByClass(stream.Measure), 1):
            for n in events_of(measure):
                address = (p, m, str(Fraction(n.getOffsetInHierarchy(measure))))
                addresses[id(n)] = address
                if n.tie:
                    ties.append((address, n.tie.type, n.tie.placement))
    slurs = sorted(
        (tuple(addresses[id(n)] for n in s.getSpannedElements()), s.placement)
        for s in score.recurse().getElementsByClass(spanner.Slur)
    )
    return {'ties': ties, 'slurs': slurs}


def exact_mapping(source, inventory, graph, root):
    raw = graph['symbols']['sheet#1:4867']
    require(
        raw['kind'] == 'slur' and raw['shape'] == 'SLUR_BELOW', 'Original 4867 observation mismatch'
    )
    relations = [
        r for r in graph['relations'] if r['source'] == raw['id'] and r['kind'] == 'slur-head'
    ]
    byside = {dict(r['attributes']).get('side'): r['target'] for r in relations}
    require(
        len(relations) == 2 and byside == {'LEFT': ENDPOINTS[0][0], 'RIGHT': ENDPOINTS[1][0]},
        'Ambiguous raw 4867 endpoints',
    )
    notes = []
    event_ids = []
    for sid, onset, pitch in ENDPOINTS:
        es = [e for e in inventory['events'] if e['symbol_id'] == sid]
        require(len(es) == 1, 'Nonunique source event identity')
        e = es[0]
        n = at(source, 21, onset)
        require(
            e['printed_measure'] == 21
            and e['onset'] == onset
            and e['pitch'] == pitch == n.pitch.nameWithOctave,
            '4867 address/pitch mismatch',
        )
        require(
            e['source_bbox'] == graph['symbols'][sid]['geometry']['bbox'],
            'Original head bbox mismatch',
        )
        notes.append(n)
        event_ids.append(e['id'])
    spans = [
        s
        for s in source.recurse().getElementsByClass(spanner.Slur)
        if list(s.getSpannedElements()) == notes
    ]
    require(len(spans) == 1, 'BLOCKED: 4867 MusicXML span not unique')
    part = root.findall('part')
    require(len(part) == 1, 'Unexpected multipart source')
    measures = part[0].findall('measure')
    require(len(measures) == 37, 'Printed-measure registration changed')
    m = measures[20]
    xmlnotes = m.findall('note')
    sem = list(source.parts[0].getElementsByClass(stream.Measure))[20]
    ns = events_of(sem)
    require(
        len(xmlnotes) == len(ns) and not m.findall('backup') and not m.findall('forward'),
        'Ambiguous XML note/event ordering',
    )
    indices = [next(j for j, n in enumerate(ns) if n is end) for end in notes]
    require(indices[1] == indices[0] + 1, 'Intervening event at 4867 span')
    require(
        [(l.number, l.text) for l in notes[1].lyrics].count((1, '되')) == 1,
        'Original upper 되 lyric not unique',
    )
    return {
        'raw_object': raw,
        'raw_relations': relations,
        'part_id': part[0].get('id'),
        'measure_xml_number': m.get('number'),
        'printed_measure': 21,
        'note_indices': indices,
        'source_event_ids': event_ids,
        'endpoint_source_ids': [x[0] for x in ENDPOINTS],
        'source_pitches': [n.pitch.nameWithOctave for n in notes],
    }


def remove_exact_slur(root, mapping):
    """Validate both exact references before mutation; never delete by nearby position."""
    result = copy.deepcopy(root)
    parts = [p for p in result.findall('part') if p.get('id') == mapping['part_id']]
    require(len(parts) == 1, 'Nonunique XML part')
    measures = [
        m for m in parts[0].findall('measure') if m.get('number') == mapping['measure_xml_number']
    ]
    require(len(measures) == 1, 'Nonunique XML measure')
    notes = measures[0].findall('note')
    left, right = [notes[j] for j in mapping['note_indices']]
    starts = [s for s in left.findall('./notations/slur') if s.get('type') == 'start']
    stops = [s for s in right.findall('./notations/slur') if s.get('type') == 'stop']
    pairs = [(a, b) for a in starts for b in stops if a.get('number', '1') == b.get('number', '1')]
    require(len(pairs) == 1, 'BLOCKED: exact XML slur references not unique')
    start, stop = pairs[0]
    refs = {
        'slur_number': start.get('number', '1'),
        'removed_xml': [ET.tostring(n, encoding='unicode') for n in [start, stop]],
        'removed_relationships': 1,
        'removed_notation_nodes': 2,
    }
    for parent, child in [(left.find('notations'), start), (right.find('notations'), stop)]:
        parent.remove(child)
    return result, refs


def stroke_overlap_links(sig_cases, marks):
    """Link reviewed regions, never infer ownership or propagate an owner answer."""
    possible = []
    for raw in sig_cases:
        if raw['proposed_interpretation'] != 'LYRIC_CONTINUATION_STROKE_CANDIDATE':
            continue
        a = raw['source_bbox']
        for mark in marks:
            b = mark.get('source_dark_bbox')
            if not b:
                continue
            area = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(
                0, min(a[3], b[3]) - max(a[1], b[1])
            )
            small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
            if small > 0 and area / small >= 0.8:
                possible.append({'raw_sig_case': raw['id'], 'continuation_case': mark['id']})
    unique = [
        p
        for p in possible
        if sum(q['raw_sig_case'] == p['raw_sig_case'] for q in possible) == 1
        and sum(q['continuation_case'] == p['continuation_case'] for q in possible) == 1
    ]
    return {
        'unambiguous_region_links': unique,
        'ambiguous_region_links': [p for p in possible if p not in unique],
        'classification_or_answers_propagated': False,
    }


def review_plan(out, inventory):
    prior = read(AUDIT / 'owner-approval-checklist.json')
    groups = defaultdict(list)
    items = [
        i
        for m in prior['grouped_by_printed_measure']
        for i in m['items']
        if i['id'] != 'sig-sheet#1:4867'
    ]
    for item in items:
        item = copy.deepcopy(item)
        number = next(
            m['measure']
            for m in prior['grouped_by_printed_measure']
            if any(i['id'] == item['id'] for i in m['items'])
        )
        system = next(s['system'] for s in inventory['systems'] if number in s['printed_measures'])
        item['measure'] = number
        item['owner_answer'] = None
        item['source_crop'] = next(
            m['source_measure_crop']
            for m in prior['grouped_by_printed_measure']
            if m['measure'] == number
        )
        if item['kind'] == 'event' and item['source_object_id'] in [x[0] for x in ENDPOINTS]:
            item['status'] = 'ATTACHMENT_CORRECTED_CORE_STILL_PROVISIONAL'
            item['review_reason'] = (
                '4867 classification/slur removal resolved; note core not approved by this decision.'
            )
        key = (
            'M28_LINEAGE'
            if item['kind'] == 'continuation' and number == 28
            else (
                'FULL_PLAYBACK'
                if item['kind'] == 'playback'
                else f'SYS{system}_{item["kind"].upper()}'
            )
        )
        groups[key].append(item)
    require(
        len(items) == 210 and sum(i['kind'] == 'event' for i in items) == 83,
        'Future scope lost/duplicated',
    )
    require(len({i['id'] for i in items}) == len(items), 'Duplicate review item')
    summary = [
        '# GT-17D 이후 소유자 검토',
        '',
        '4867의 ‘되’ 획 분류와 잘못된 이음줄 제거는 승인 완료입니다. 아래 항목만 검토하며 기존 코드·가사 문자열·승인된 곡선 분류는 다시 묻지 않습니다.',
        '',
        '각 그룹은 CONFIRM / CORRECT(사례 ID와 수정 필드) / UNCERTAIN으로 답할 수 있습니다. 일부만 답하면 나머지는 미확인으로 남습니다. 실제 답변은 모두 비어 있습니다.',
        '',
        '음표 핵심 미확인 83개 = 기존 비충돌 후보 81개 + 연결 문제만 해결된 2개입니다. 2개를 승인 또는 삭제한 것으로 계산하지 않습니다.',
        '',
        '원본 영상은 기존 GT-17C source-review-delta-sheet.png 및 원본 crop 참조를 사용합니다. target 악보를 원본 정답으로 사용하지 마세요.',
        f'[원본 차이 검토 영상]({AUDIT / "source-review-delta-sheet.png"})',
        f'[기존 마디·사례별 상세 안내]({AUDIT / "owner-review-guide.md"})',
        '',
    ]
    records = []
    for key, questions in sorted(groups.items()):
        record = {
            'group_id': key,
            'printed_measures': sorted({q['measure'] for q in questions}),
            'items': questions,
            'owner_answer': None,
            'approval_classification_if_confirmed': 'SCOPED_OWNER_REVIEW_NOT_INDEPENDENT',
        }
        records.append(record)
        summary.extend(
            [
                f'## {key}: 인쇄 {record["printed_measures"]} / {len(questions)}개 미확인 필드',
                f'검토 ID: {", ".join(q["id"] for q in questions)}',
                '답변: ______',
                '',
            ]
        )
        for measure in record['printed_measures']:
            same = [q for q in questions if q['measure'] == measure]
            if same[0]['kind'] == 'event':
                detail = '; '.join(
                    f'{q["source_object_id"]}: {q["candidate"]["onset"]} '
                    f'{q["candidate"].get("written_pitch") or "REST"}'
                    f'({q["candidate"]["duration"]})'
                    for q in same
                )
            elif same[0]['kind'] == 'lyric_onset':
                detail = '; '.join(
                    f'row{q["candidate"]["row"]} '
                    f'{q["candidate"]["onset"]}:{q["candidate"]["text"]}'
                    for q in same
                )
            elif same[0]['kind'] == 'continuation':
                detail = '; '.join(
                    f'row{q["candidate"]["row"]} '
                    f'{q["candidate"]["onset"]}: held {q["candidate"]["held_syllable_candidate"]}'
                    for q in same
                )
            elif same[0]['kind'] == 'raw_sig':
                detail = '; '.join(
                    f'{q["source_object_id"]}: ' f'{q["candidate"]["proposed_interpretation"]}'
                    for q in same
                )
            else:
                detail = same[0]['candidate']['question']
            summary.extend([f'- 인쇄 {measure}: {detail}', ''])
    summary.extend(
        [
            '## 우선순위',
            '',
            '1. M28_LINEAGE와 FULL_PLAYBACK은 근거가 없으면 UNCERTAIN 또는 DEFER로 보류합니다. 재생 경로를 추측하지 않습니다.',
            '2. SYS6–9의 event 그룹을 원본과 대조합니다. pitch/rest, onset, duration, voice와 아직 승인되지 않은 연결만 검토합니다.',
            '3. lyric_onset은 이미 승인한 문자열이 아니라 정확한 음표 대응만 검토합니다. continuation과 raw_sig는 동일 원본 영역을 가리킬 수 있으며 별도 음악 사건으로 더하지 않습니다.',
            '',
            '현재 독립 인간 정답은 0건입니다. PASS_CANDIDATE는 소유자 승인이나 연주 가능한 완성 악보 판정이 아닙니다.',
        ]
    )
    overlaps = stroke_overlap_links(
        [
            s
            for s in read(AUDIT / 'unresolved-sig-review.json')
            if s['source_object_id'] != 'sheet#1:4867'
        ],
        read(AUDIT / 'continuation-review.json'),
    )
    summary.extend(
        [
            '',
            '## 중복 원본 영역을 함께 검토',
            '',
            '아래 연결은 같은 획 영역의 후보입니다. 한 묶음으로 답하되 raw 분류와 음절/음표 연결 필드를 명시하세요. 답변이나 소유권을 자동 전파하지 않습니다.',
        ]
    )
    summary.extend(
        f'- {p["raw_sig_case"]} ↔ {p["continuation_case"]}'
        for p in overlaps['unambiguous_region_links']
    )
    plan = {
        'groups': records,
        'counts': {
            'nonconflicting_event_candidates': 81,
            'attachment_corrected_but_core_unverified': 2,
            'all_provisional_event_cores': 83,
            'lyric_onsets': 79,
            'visually_supported_continuations': 19,
            'm28_unresolved': 1,
            'raw_sig_cases': 27,
            'playback_decisions': 1,
            'field_items': 210,
            'coherent_groups': len(records),
        },
        'approved_4867_reconfirmation_requested': False,
        'overlapping_source_region_questions': overlaps,
        'new_owner_answers': 0,
        'independent_ground_truth': 0,
        'scope_note': 'Review fields overlap; counts are not independent musical errors or an accuracy denominator.',
        'prior_delta_sheet': {
            'path': str(AUDIT / 'source-review-delta-sheet.png'),
            'sha256': sha(AUDIT / 'source-review-delta-sheet.png'),
        },
    }
    dump(out / 'remaining-review-plan.json', plan)
    (out / 'owner-review-summary.md').write_text('\n'.join(summary) + '\n')
    return plan['counts']


def run(out):
    require(not out.exists(), 'Fresh output required')
    out.mkdir(parents=True)
    snapshots = {str(p): file_hashes(p) for p in [BASE, OWNER, AUDIT]}
    verify_manifest(BASE, 'prediction-freeze.json')
    verify_manifest(OWNER, 'prediction-freeze.json')
    verify_manifest(AUDIT, 'audit-freeze.json')
    for n, h in read(ROOT / 'docs/V4_GT17C_VALIDATION.json')['artifact_sha256'].items():
        require(sha(AUDIT / n) == h, 'GT17C mismatch ' + n)
    history, src = binding(out)
    (out / 'owner-interpretation-layer.json').unlink()
    inventory = read(OWNER / 'source-event-inventory.json')
    graph = read(SOURCE_DIR / 'visual-graph.json')
    text = (OWNER / 'owner-augmented-source.musicxml').read_text()
    root = ET.fromstring(text, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    source = converter.parse(str(OWNER / 'owner-augmented-source.musicxml'))
    mapping = exact_mapping(source, inventory, graph, root)
    corrected, refs = remove_exact_slur(root, mapping)
    # Compare to a separately computed removal expectation, leaving every other XML node intact.
    expected = copy.deepcopy(root)
    measure = expected.findall('part')[0].findall('measure')[20]
    for j, role in zip(mapping['note_indices'], ['start', 'stop']):
        parent = measure.findall('note')[j].find('notations')
        victim = [
            s
            for s in parent.findall('slur')
            if s.get('type') == role and s.get('number', '1') == refs['slur_number']
        ]
        require(len(victim) == 1, 'Nonunique expected removal')
        parent.remove(victim[0])
    require(tree_fingerprint(corrected) == tree_fingerprint(expected), 'Other XML changed')
    prefix = text[: text.index('<score-partwise')]
    (out / 'corrected-source.musicxml').write_text(
        prefix + ET.tostring(corrected, encoding='unicode') + '\n'
    )
    revised = converter.parse(str(out / 'corrected-source.musicxml'))
    before = relationship_inventory(source)
    after = relationship_inventory(revised)
    removed = (((0, 21, '3'), (0, 21, '13/4')), 'below')
    require(before['slurs'].count(removed) == 1, 'Semantic removal identity not unique')
    require(
        after['slurs'] == [s for s in before['slurs'] if s != removed]
        and before['ties'] == after['ties'],
        'Other curve changed',
    )
    require(core_signature(source) == core_signature(revised), 'Event core changed')
    require(full_lyric_signature(source) == full_lyric_signature(revised), 'Lyrics changed')
    require(repeat_signature(source) == repeat_signature(revised), 'Repeat changed')
    layer = {
        'classification': 'OWNER_VERIFIED_INTERPRETATION',
        'independent_ground_truth': 0,
        'owner_response_verbatim': APPROVAL,
        'review_context_verbatim': APPROVAL_CONTEXT,
        'approval_origin': 'Actual owner response explicitly quoted in current GT17D user instruction; no signature/timestamp fabricated.',
        'starting_sha': START,
        'interpretation': 'KOREAN_LYRIC_GLYPH_STROKE',
        'associated_existing_lyric': '되',
        'original_observation_and_exact_mapping': mapping,
        'specific_xml_removal': refs,
        'source_hashes': src,
        'review_binding': {
            n: sha(AUDIT / n)
            for n in [
                'audit-freeze.json',
                'source-review-delta-sheet.png',
                'unresolved-sig-review.json',
                'provisional-event-review.json',
                'owner-approval-checklist.json',
            ]
        },
        'prior_owner_interpretation_sha256': sha(OWNER / 'owner-interpretation-layer.json'),
        'preceding_gt17c_case_verbatim': next(
            c
            for c in read(AUDIT / 'unresolved-sig-review.json')
            if c['source_object_id'] == 'sheet#1:4867'
        ),
        'preceding_report_sha256': sha(ROOT / 'docs/V4_GT17C_ACCURACY_AUDIT.md'),
        'note_event_approvals_added': 0,
        'lyric_approvals_added': 0,
        'other_sig_approvals_added': 0,
        'M28_CONTINUATION_LINEAGE': 'UNRESOLVED',
        'FULL_REPEAT_PLAYBACK': 'UNRESOLVED',
    }
    dump(out / 'owner-approved-4867-correction.json', layer)
    evidence = read(OWNER / 'owner-interpretation-layer.json')['curve_interpretations']
    guards = {'source_roundtrip': validate(source, revised, 0, 'key').to_dict()}
    relationships = {'source': relationship_signature(revised, evidence)}
    xmlchecks = {'source': xml_curve_audit((out / 'corrected-source.musicxml').read_text())}
    extendchecks = {
        'source': xml_lyric_extension_audit((out / 'corrected-source.musicxml').read_text())
    }
    target_diffs = {}
    pixels = []
    for name, shift in [('A', -1), ('G', -3)]:
        target = copy.deepcopy(revised)
        summary = transpose_score(target, shift, 'key')
        target.write('musicxml', fp=str(out / f'{name}-corrected.musicxml'))
        parsed = converter.parse(str(out / f'{name}-corrected.musicxml'))
        previous = converter.parse(str(OWNER / f'{name}-transposed.musicxml'))
        guards[name] = {
            'in_memory': validate(revised, target, shift, 'key', summary).to_dict(),
            'serialized': validate(revised, parsed, shift, 'key', summary).to_dict(),
            'previous_target_core_chords': validate(previous, parsed, 0, 'key').to_dict(),
        }
        require(
            core_signature(previous) == core_signature(parsed)
            and full_lyric_signature(previous) == full_lyric_signature(parsed),
            'Target note/lyric changed',
        )
        require(repeat_signature(previous) == repeat_signature(parsed), 'Target repeat changed')
        prevrel, newrel = relationship_inventory(previous), relationship_inventory(parsed)
        require(
            prevrel['ties'] == newrel['ties'] and len(prevrel['slurs']) == len(newrel['slurs']) + 1,
            'Target curve count/ties changed',
        )
        require(
            newrel['slurs'] == [s for s in prevrel['slurs'] if s[0] != removed[0]],
            'Other target slur changed',
        )
        target_diffs[name] = {'before': prevrel, 'after': newrel, 'only_removed_span': removed[0]}
        relationships[name] = relationship_signature(parsed, evidence)
        xmlchecks[name] = xml_curve_audit((out / f'{name}-corrected.musicxml').read_text())
        extendchecks[name] = xml_lyric_extension_audit(
            (out / f'{name}-corrected.musicxml').read_text()
        )
        # A copied frozen layer is explicitly not a newly run MusicXML renderer.
        maps = read(BASE / f'{name}-system-6-components/component-map.json')
        require('sheet#1:4867' not in {m['id'] for m in maps}, '4867 unexpectedly rendered')
        oldpng = OWNER / f'{name}-full-score.png'
        newpng = out / f'{name}-full-score-unchanged.png'
        shutil.copyfile(oldpng, newpng)
        a, b = Image.open(oldpng), Image.open(newpng)
        require(
            sha(oldpng) == sha(newpng)
            and a.mode == b.mode
            and a.size == b.size
            and a.tobytes() == b.tobytes(),
            'Rendered pixels changed',
        )
        pixels.append(
            {
                'target': name,
                'frozen_png_sha256': sha(oldpng),
                'new_copy_sha256': sha(newpng),
                'exact_file_and_pixels_equal': True,
                'frozen_component_map_sha256': sha(
                    BASE / f'{name}-system-6-components/component-map.json'
                ),
                '4867_music_component_exists': False,
                'method': 'Byte-exact standalone PNG copy; not an independent rerender or optical validation.',
            }
        )
    require(
        guards['source_roundtrip']['ok']
        and all(g['ok'] for n in ['A', 'G'] for g in guards[n].values()),
        'V3 guard failed',
    )
    require(
        all(not r['tie_sound_notation_disagreements'] for r in xmlchecks.values()),
        'Sound/notation tie mismatch',
    )
    require(
        all(r['count'] == 0 for r in extendchecks.values()),
        'Unapproved extender serialization introduced',
    )
    dump(
        out / 'before-after-semantic-diff.json',
        {
            'source_before': before,
            'source_after': after,
            'target_diffs': target_diffs,
            'removed_relationship_count': 1,
            'removed_source_notation_nodes': 2,
            'other_source_xml_tree_unchanged': True,
            'events_unchanged': 169,
            'chords_unchanged': 24,
            'lyric_wording_rows_unchanged': 167,
            'no_new_lyric_glyph': True,
        },
    )
    workload = review_plan(out, inventory)
    dump(
        out / 'semantic-validation.json',
        {
            'guards': guards,
            'approved_curves': relationships,
            'raw_xml_tie_slur_checks': xmlchecks,
            'lyric_extension_checks': extendchecks,
            'M28_CONTINUATION_LINEAGE': 'UNRESOLVED',
            'FULL_REPEAT_PLAYBACK': 'UNRESOLVED',
            'source_completeness': 'UNVERIFIED',
            'rendering_completeness': 'INCOMPLETE',
            'visual_quality': 'UNCHANGED_GT17B_NEEDS_REFINEMENT',
            'independent_ground_truth': 0,
            'preserved_scope': {
                'measures': 37,
                'systems': 9,
                'events': 169,
                'owner_events': 86,
                'provisional_events': 83,
                'owner_chords': 24,
                'owner_lyric_wording_rows': 167,
                'verified_lyric_onsets': 88,
                'provisional_lyric_onsets': 79,
                'verified_marks': 30,
                'provisional_marks': 20,
            },
        },
    )
    require(
        all(file_hashes(Path(k)) == v for k, v in {**snapshots, **history}.items()),
        'Historical input changed',
    )
    for n, k in [
        ('source.png', 'source_sha256'),
        ('recognized.omr', 'omr_sha256'),
        ('visual-graph.json', 'graph_sha256'),
    ]:
        require(sha(SOURCE_DIR / n) == src[k], 'Original changed')
    dump(
        out / 'preservation-verification.json',
        {
            'source_hashes': src,
            'historical_directories': list(snapshots) + list(history),
            'all_historical_files_unchanged': True,
            'original_omr_sig_masks_unmodified': True,
            'standalone_png_pixel_checks': pixels,
            'new_pngs_are_explicit_frozen_copies_not_rerenders': True,
            'no_production_changes': True,
        },
    )
    dump(
        out / 'output-freeze.json',
        {'files': file_hashes(out), 'producer_sha256': sha(Path(__file__)), 'starting_sha': START},
    )
    print('Scoped correction PASS; future review:', workload)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        run(args.output)
    except ValueError as exc:
        if args.output.exists():
            dump(
                args.output / 'blocked.json',
                {
                    'status': 'BLOCKED',
                    'reason': str(exc),
                    'no_fallback_slur_deletion_authorized': True,
                },
            )
        raise
