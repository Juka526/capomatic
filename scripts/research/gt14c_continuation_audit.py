"""Source-only lyric continuation census; no target rendering or ownership changes."""

import argparse
import copy
from fractions import Fraction
from pathlib import Path

import numpy as np
from music21 import converter, harmony, stream
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.chords import chord_text
from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt11_complete_measure import events_of, event_signature, read, require
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.gt13a5_lyric_layout import verify_freeze
from scripts.research.gt14b_lyric_extenders import (
    SOURCE,
    SOURCE_DIR,
    PRIOR as GT14A,
    verify_binding,
    context,
    event,
)
from scripts.research.paired_ground_truth_01 import dump, file_hashes, sha

ROOT = Path(__file__).resolve().parents[2]
GT14B = Path('/private/tmp/capomatic-v4-gt14b/gt14b-final-output')
PROTOCOL = ROOT / 'docs/V4_GT14C_PROTOCOL.json'


def dark_support_bbox(source, window):
    """Measurement only: keep original pixels and unknown antialias extent separate."""
    require(source.mode == 'RGB', 'Unexpected original source mode')
    require(len(window) == 4 and all(type(v) is int for v in window), 'Integer window required')
    x0, y0, x1, y1 = window
    require(0 <= x0 < x1 <= source.width and 0 <= y0 < y1 <= source.height, 'Invalid source window')
    yy, xx = np.nonzero(np.asarray(source.crop(window).convert('L')) < 127)
    require(len(xx) > 0, 'No observed dark support in candidate window')
    return [int(x0 + xx.min()), int(y0 + yy.min()), int(x0 + xx.max() + 1), int(y0 + yy.max() + 1)]


def intersect(a, b):
    return a and b and max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def candidate_record(spec, source, graph, score):
    n = event(score, spec['measure'], spec['onset'])
    previous = event(score, spec['syllable_measure'], spec['syllable_onset'])
    require(
        n.tie and n.tie.type == 'stop' and previous.tie and previous.tie.type == 'start',
        'Tie roles mismatch',
    )
    require(n.pitch == previous.pitch, 'Different held pitches')
    require(
        [l.text for l in previous.lyrics if int(l.number) == spec['row']]
        == [spec['associated_syllable_candidate']],
        'Confirmed syllable context mismatch',
    )
    require(spec['tie_id'] in graph['symbols'], 'Persisted tie missing')
    b = dark_support_bbox(source, spec['window'])
    objects = [s for s in graph['symbols'].values() if intersect(s['geometry']['bbox'], b)]
    return {
        **spec,
        'classification': 'AGENT_VISUAL_CANDIDATE',
        'source_bbox': b,
        'bbox_basis': 'L_LT_127_DARK_SUPPORT_NOT_COMPLETE_INK_OWNERSHIP',
        'antialias_extent': 'UNVERIFIED_WITHIN_NATIVE_REVIEW_WINDOW',
        'identification_basis': 'INDIVIDUAL_SOURCE_ONLY_VISUAL_INSPECTION_NOT_COPIED_FROM_OTHER_ROW',
        'note_context': {
            'written_pitch': n.pitch.nameWithOctave,
            'onset': str(Fraction(n.offset)),
            'duration': str(Fraction(n.quarterLength)),
            'tie_role': n.tie.type,
            'syllable_source_measure': spec['syllable_measure'],
            'syllable_source_onset': spec['syllable_onset'],
            'syllable_text': spec['associated_syllable_candidate'],
            'semantic_context_evidence': 'EXISTING_OWNER_VERIFIED_NOTES_SYLLABLES_AND_TIES',
            'new_stroke_association_evidence': 'AGENT_VISUAL_CANDIDATE',
        },
        'tie_source_record': graph['symbols'][spec['tie_id']],
        'tie_relations': [
            r for r in graph['relations'] if spec['tie_id'] in (r['source'], r['target'])
        ],
        'intersecting_omr_objects': objects,
        'omr_overlap_interpretation': 'SPATIAL_CONTEXT_ONLY_NOT_STROKE_RECOGNITION_OR_OWNERSHIP',
        'owner_response': None,
        'new_rendering_authorized': False,
        'independent_ground_truth': False,
    }


def row_census(records):
    require(
        len({r.get('id', r.get('symbol_id')) for r in records}) == len(records),
        'Duplicate inventory ID',
    )
    return [
        {
            'measure': m,
            'row': row,
            'record_ids': [
                r.get('id', r.get('symbol_id'))
                for r in records
                if r['measure'] == m and r['row'] == row
            ],
            'inspection_status': 'AGENT_VISUAL_REVIEW_ENTIRE_MEASURE_ROW',
            'absence_status': 'NO_ADDITIONAL_STROKE_OBSERVED_NOT_INDEPENDENT_PROOF',
            'source_completeness': 'NOT_INDEPENDENTLY_VERIFIED',
        }
        for m in range(5, 9)
        for row in (1, 2)
    ]


def save_native(source, bbox, path):
    crop = source.crop(bbox)
    crop.save(path)
    reopened = Image.open(path)
    require(
        reopened.mode == source.mode
        and reopened.size == (bbox[2] - bbox[0], bbox[3] - bbox[1])
        and reopened.tobytes() == crop.tobytes(),
        'Native crop changed source pixels',
    )
    return {
        'file': path.name,
        'page_bbox': bbox,
        'size': list(crop.size),
        'mode': crop.mode,
        'sha256': sha(path),
        'source_pixel_equality': True,
        'scale': 1,
    }


def checklist(candidates):
    require(
        all(
            r['classification'] == 'AGENT_VISUAL_CANDIDATE' and r['owner_response'] is None
            for r in candidates
        ),
        'Candidate promotion forbidden',
    )
    return {
        'review_type': 'OWNER_REVIEW_PENDING_NOT_INDEPENDENT_GROUND_TRUTH',
        'instructions_ko': '원본 두 줄을 보며 아래 새 후보 3개만 확인해 주세요. 기존 3개 연장선과 하 분류는 재확인하지 않습니다. 획의 존재, 가사 줄, 이어지는 음절을 각각 확인·수정할 수 있습니다. 불확실하면 OWNER_UNCERTAIN을 선택해 주세요.',
        'allowed_responses': ['OWNER_CONFIRMED', 'OWNER_REJECTED', 'OWNER_UNCERTAIN'],
        'cases': [
            {
                'id': r['id'],
                'measure': r['measure'],
                'row': r['row'],
                'source_bbox': r['source_bbox'],
                'crop': r['review_image'],
                'question_ko': f"{r['measure']}마디 {'위' if r['row']==1 else '아래'} 줄의 표시된 위치에 연장선이 있고, 앞 음절 ‘{r['associated_syllable_candidate']}’을 이어가는 것이 맞나요?",
                'stroke_present': None,
                'row_confirmed': None,
                'association_confirmed': None,
                'owner_response': None,
                'correction': None,
                'uncertainty': None,
            }
            for r in candidates
        ],
        'rendering_blocked_until_explicit_approval': True,
    }


def run(out):
    require(not (out / 'lyric-continuation-inventory.json').exists(), 'Audit output already frozen')
    protocol = read(PROTOCOL)
    verify_binding()
    verify_freeze(GT14A)
    verify_freeze(GT14B)
    prior_hashes = {str(p): file_hashes(p) for p in (GT14A, GT14B)}
    require(sha(SOURCE) == protocol['source_sha256'], 'Wrong source')
    graph = read(SOURCE_DIR / 'visual-graph.json')
    source = Image.open(SOURCE)
    score = converter.parse(str(GT14A / 'owner-augmented-source.musicxml'))
    old = read(ROOT / 'docs/V4_GT14B_PROTOCOL.json')['interpretations']
    preserved = [context(r, graph, score) for r in old]
    require(
        read(GT14B / 'owner-interpretation-layer.json') == preserved,
        'Confirmed interpretation changed',
    )
    candidates = [candidate_record(r, source, graph, score) for r in protocol['new_candidates']]
    all_marks = [r for r in preserved if r['interpretation'] == 'LYRIC_EXTENDER'] + candidates
    require(len(all_marks) == 6 and len(preserved) == 4 and len(candidates) == 3, 'Scope changed')
    require(
        not any(
            intersect(a['source_bbox'], b['source_bbox'])
            for i, a in enumerate(all_marks)
            for b in all_marks[i + 1 :]
        ),
        'Duplicated source mark',
    )
    measures = list(score.parts[0].getElementsByClass(stream.Measure))
    require(sum(len(events_of(m)) for m in measures[4:8]) == 13, '13 confirmed events required')
    require(
        [chord_text(c) for m in measures[4:8] for c in m.getElementsByClass(harmony.ChordSymbol)]
        == ['Gm', 'Bb/D', 'Eb'],
        'Confirmed chords changed',
    )
    require(
        sum(len(n.lyrics) for m in measures[4:8] for n in events_of(m)) == 14,
        'Confirmed syllables changed',
    )
    out.mkdir(exist_ok=True)
    native_records = []
    full_box = [130, 700, 2430, 1030]
    native_records.append(save_native(source, full_box, out / 'source-second-system-native.png'))
    strips = []
    for row, bbox in enumerate(protocol['row_inspection_strips'], 1):
        name = f'source-row-{row}-native.png'
        native_records.append(save_native(source, bbox, out / name))
        strips.append(Image.open(out / name))
    for r in candidates:
        r['review_image'] = f"{r['id']}-native.png"
        native_records.append(save_native(source, r['review_crop'], out / r['review_image']))
        r['review_crop_sha256'] = sha(out / r['review_image'])
    # Native tiles only; labels stay outside source pixels. No target music or answers are pasted.
    sheet = Image.new('RGB', (2300, 840), 'white')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20)
    draw.text(
        (10, 8),
        'SOURCE-ONLY / OWNER REVIEW PENDING / native pixels, no target predictions',
        font=font,
        fill='black',
    )
    sheet.paste(source.crop(full_box), (0, 40))
    for row, tile in enumerate(strips):
        y = 410 + row * 90
        draw.text(
            (10, y - 26),
            f'Entire source lyric row {row+1}; page x=159..2396',
            font=font,
            fill='black',
        )
        sheet.paste(tile, (29, y))
    for i, r in enumerate(candidates):
        x = 30 + 700 * i
        draw.text((x, 575), f"{r['id']} / NEW CANDIDATE", font=font, fill='black')
        sheet.paste(source.crop(r['review_crop']), (x, 610))
    sheet.save(out / 'source-two-row-extender-review.png')
    guards = {
        'source_roundtrip': validate(
            score, converter.parse(str(GT14A / 'owner-augmented-source.musicxml')), 0, 'key'
        ).to_dict()
    }
    for target, shift in [('A', -1), ('G', -3)]:
        predicted = copy.deepcopy(score)
        summary = transpose_score(predicted, shift, 'key')
        frozen = converter.parse(str(GT14A / f'{target}-transposed.musicxml'))
        guards[target] = {
            'in_memory': validate(score, predicted, shift, 'key', summary).to_dict(),
            'frozen_serialized': validate(score, frozen, shift, 'key', summary).to_dict(),
        }
        require(all(r['ok'] for r in guards[target].values()), 'Full V3 guard failure')
        require(
            full_lyric_signature(score) == full_lyric_signature(frozen), 'Lyric signature changed'
        )
        require(
            [event_signature(m) for m in predicted.parts[0].getElementsByClass(stream.Measure)]
            == [event_signature(m) for m in frozen.parts[0].getElementsByClass(stream.Measure)],
            'Frozen music changed',
        )
    require(guards['source_roundtrip']['ok'], 'Source roundtrip guard failure')
    inventory = {
        'source_sha256': sha(SOURCE),
        'protocol_sha256': sha(PROTOCOL),
        'coordinate_convention': protocol['coordinate_convention'],
        'confirmed_records': preserved,
        'new_candidates': candidates,
        'measure_row_census': row_census(all_marks),
        'visible_continuation_count': 6,
        'owner_confirmed_continuations': 3,
        'pending_continuations': 3,
        'excluded_non_extender': 'sheet#1:5747 already rendered as part of 하',
        'inventory_coverage': 'AGENT_CENSUS_OF_8_MEASURE_ROW_REGIONS_NOT_INDEPENDENT_COMPLETENESS',
        'renderer_completeness': 'UNCHANGED_GT14B_3_OF_6_OBSERVED_MARKS_RENDERED',
        'new_candidates_rendered': 0,
        'native_crop_bindings': native_records,
    }
    dump(out / 'lyric-continuation-inventory.json', inventory)
    dump(out / 'owner-review-checklist.json', checklist(candidates))
    dump(out / 'semantic-integrity.json', guards)
    require(
        all(file_hashes(Path(p)) == h for p, h in prior_hashes.items()),
        'Historical artifact mutation',
    )
    require(sha(SOURCE) == protocol['source_sha256'], 'Source mutation')
    dump(
        out / 'input-preservation.json',
        {
            'historical_files': prior_hashes,
            'source_sha256': sha(SOURCE),
            'producer_sha256': sha(Path(__file__)),
            'protocol_sha256': sha(PROTOCOL),
            'unchanged': True,
        },
    )
    dump(
        out / 'validation-summary.json',
        {
            'status': 'SOURCE_AUDIT_AND_OWNER_PACKET_READY',
            'recognized_confirmed_events': 13,
            'confirmed_chords': 3,
            'confirmed_syllables': 14,
            'owner_confirmed_extenders_preserved': 3,
            'ha_classification_preserved': True,
            'new_agent_candidates': 3,
            'new_owner_confirmations': 0,
            'independent_labels': 0,
            'measure_row_regions_inspected': 8,
            'source_completeness': 'NOT_INDEPENDENTLY_VERIFIED',
            'renderer_completeness': 'UNCHANGED_SCOPED_GT14B_NOT_FULL_SYSTEM',
            'new_candidates_rendered': 0,
            'full_V3_guards': 'PASS',
            'history_unchanged': True,
            'source_ink_or_composition_authorized': False,
        },
    )
    dump(
        out / 'audit-freeze.json',
        {'files': file_hashes(out), 'phase': 'SOURCE_AUDIT_ONLY_NO_TARGET_RENDERING'},
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    run(parser.parse_args().out)
