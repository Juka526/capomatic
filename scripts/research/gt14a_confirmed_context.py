"""Owner-confirmed standalone text/notation addition; ambiguous SIG objects stay unresolved."""

import argparse
import copy
from fractions import Fraction
from pathlib import Path

import numpy as np
from music21 import converter, harmony, spanner, stream
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.chords import chord_symbol_from_text, chord_text, transpose_chord_text
from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt11_complete_measure import events_of, event_signature, read, require, FONT
from scripts.research.gt12_render_context import KOREAN_FONT, text_mask, canonical_box, ink_bbox
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.gt13a5_lyric_layout import (
    union,
    displacement_domain,
    translate,
    contacts,
    verify_freeze,
)
from scripts.research.gt13a2_provisional import ink_distance
from scripts.research.gt13a6_tie_review import SOURCE, SOURCE_DIR
from scripts.research.gt13a6_tie_rendering import OLD, SIZE
from scripts.research.gt14_second_system import PRIOR as GT13A6
from scripts.research.gt13a_full_system import scaffold
from scripts.research.gt14a_notation import whole_rest, ending_repeat
from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes

ROOT = Path(__file__).resolve().parents[2]
PRIOR = Path('/private/tmp/capomatic-v4-gt14/gt14-final-output')
BINDING = ROOT / 'docs/evidence/GT14_OWNER_BINDING.json'
PROTOCOL = ROOT / 'docs/V4_GT14A_PROTOCOL.json'
EXCLUDED = ['sheet#1:5686', 'sheet#1:5699', 'sheet#1:5747', 'sheet#1:5762']
ONSETS = ['3/2', '7/4', '2', '5/2', '11/4', '13/4', '15/4']
LYRICS = [['내', '가', '있', '길', '원', '하', '네'], ['주', '의', '놀', '라', '운', '손', '길']]
CHORDS = {5: 'Gm', 6: 'Bb/D', 7: 'Eb'}
VIEW = (130, 700, 2430, 1030)


def owner_binding(binding_path, prior):
    r = read(binding_path)
    require(
        r['classification'] == 'OWNER_VERIFIED_SOURCE' and r['independent_ground_truth'] is False,
        'Owner source classification required',
    )
    require(r['excluded_objects'] == EXCLUDED, 'Ambiguity exclusions must remain unchanged')
    for field, hashfield in [
        ('approval_file', 'approval_sha256'),
        ('review_context_file', 'review_context_sha256'),
    ]:
        require(sha(binding_path.parent / r[field]) == r[hashfield], 'Actual message bytes changed')
    for field, name in [
        ('review_sheet_sha256', 'source-second-system-review-sheet.png'),
        ('review_checklist_sha256', 'source-review-checklist.json'),
        ('source_inventory_sha256', 'source-event-inventory.json'),
        ('prediction_freeze_sha256', 'prediction-freeze.json'),
    ]:
        require(sha(prior / name) == r[field], 'Approval/source context mismatch')
    verify_freeze(prior)
    require(sha(SOURCE) == r['source_sha256'], 'Wrong original source')
    return r


def augment(score):
    result = copy.deepcopy(score)
    measures = list(result.parts[0].getElementsByClass(stream.Measure))
    for number, chord in CHORDS.items():
        m = measures[number - 1]
        found = list(m.getElementsByClass(harmony.ChordSymbol))
        if found:
            require(
                len(found) == 1 and chord_text(found[0]) == chord,
                'Existing harmony differs from owner source',
            )
        else:
            m.insert(0, chord_symbol_from_text(chord))
    require(
        not list(measures[7].getElementsByClass(harmony.ChordSymbol)), 'No new m8 chord authorized'
    )
    notes = events_of(measures[5])
    by_onset = {str(Fraction(n.getOffsetInHierarchy(measures[5]))): n for n in notes}
    for n in notes:
        n.lyrics = []
    for i, onset in enumerate(ONSETS):
        n = by_onset[onset]
        require(n.isNote, 'Confirmed lyric cannot attach to rest')
        for row, syllables in enumerate(LYRICS, 1):
            n.addLyric(syllables[i], lyricNumber=row)
    require(
        not by_onset['3'].lyrics and by_onset['3'].tie.type == 'stop',
        'Held onset must not receive new lyric',
    )
    require(measures[7].rightBarline.direction == 'end', 'Backward repeat source semantics missing')
    brackets = [
        b
        for b in result.recurse().getElementsByClass(spanner.RepeatBracket)
        if str(b.number) == '1' and measures[7] in b.getSpannedElements()
    ]
    require(len(brackets) == 1, 'First-ending source semantics missing')
    require(
        [event_signature(m) for m in measures]
        == [event_signature(m) for m in score.parts[0].getElementsByClass(stream.Measure)],
        'Music event semantics changed',
    )
    return result


def panel(native, title):
    out = Image.new('RGB', (native.width, native.height + 150), 'white')
    d = ImageDraw.Draw(out)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20)
    for i, t in enumerate(
        [
            'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING',
            title,
            'OWNER_VERIFIED listed content; four TENUTO/FERMATA objects remain AMBIGUOUS and NOT RENDERED.',
            'Newly typeset lyrics; no original-pixel composition; ambiguous dash/extender glyphs withheld.',
        ]
    ):
        d.text((10, 8 + 30 * i), t, font=font, fill='black')
    out.paste(native, (0, 150))
    return out


def native(alpha):
    return Image.composite(Image.new('RGB', SIZE, 'black'), Image.new('RGB', SIZE, 'white'), alpha)


def run(out):
    require(not out.exists(), 'Fresh output directory required')
    owner = owner_binding(BINDING, PRIOR)
    protocol = read(PROTOCOL)
    verify_freeze(GT13A6)
    histories = {str(p): file_hashes(p) for p in (PRIOR, GT13A6, OLD)}
    expected_font = read(GT13A6 / 'input-freeze.json')['font_sha256']
    require(sha(FONT) == expected_font, 'Notation font changed')
    korean_hash = read(
        Path('/private/tmp/capomatic-v4-gt13a2/gt13a2-final-output/input-freeze.json')
    )['korean_font']
    require(sha(KOREAN_FONT) == korean_hash, 'Korean font changed')
    graph = read(SOURCE_DIR / 'visual-graph.json')
    require(
        sha(SOURCE_DIR / 'visual-graph.json') == read(PRIOR / 'input-freeze.json')['graph_sha256'],
        'Source graph changed',
    )
    inv = read(PRIOR / 'source-event-inventory.json')
    staff = inv['staff']
    source = Image.open(SOURCE)
    ambiguous = [
        {
            'classification': 'AMBIGUOUS_UNVERIFIED_NOT_RENDERED_NOT_DISCARDED',
            'symbol': graph['symbols'][i],
            'relations': [r for r in graph['relations'] if i in (r['source'], r['target'])],
        }
        for i in EXCLUDED
    ]
    derived = copy.deepcopy(inv)
    for m in derived['measures']:
        for e in m['events']:
            e['prior_source_verification'] = e['source_verification']
            e['source_verification'] = 'OWNER_VERIFIED_SOURCE'
            e['render_evidence'] = 'OWNER_VERIFIED_SOURCE'
        m['chords'] = 'OWNER_VERIFIED_SOURCE'
        m['lyrics_and_associations'] = (
            'OWNER_VERIFIED_SOURCE_SCOPED_SYLLABLES_EXCLUDING_AMBIGUOUS_OBJECTS'
        )
    derived['owner_verified_events'] = 13
    derived['source_completeness'] = 'LISTED_CONTENT_OWNER_VERIFIED_WITH_FOUR_AMBIGUOUS_OBJECTS'
    out.mkdir()
    dump(out / 'owner-verified-inventory.json', derived)
    dump(out / 'ambiguous-objects.json', ambiguous)
    (out / 'owner-approval.txt').write_bytes((BINDING.parent / owner['approval_file']).read_bytes())
    (out / 'owner-binding.json').write_bytes(BINDING.read_bytes())
    score = converter.parse(str(OLD / 'owner-associated-source.musicxml'))
    augmented = augment(score)
    augmented.write('musicxml', fp=str(out / 'owner-augmented-source.musicxml'))
    parsed_source = converter.parse(str(out / 'owner-augmented-source.musicxml'))
    guards = {'source_roundtrip': validate(augmented, parsed_source, 0, 'key').to_dict()}
    require(
        guards['source_roundtrip']['ok']
        and full_lyric_signature(augmented) == full_lyric_signature(parsed_source),
        'Source full guard or lyric serialization failed',
    )
    boxes = [ink_bbox(source, w) for w in protocol['chord_source_windows']]
    row_boxes = [ink_bbox(source, w) for w in protocol['lyric_source_windows']]
    digit_box = ink_bbox(source, protocol['ending_digit_window'])
    lyric_font = ImageFont.truetype(str(KOREAN_FONT), 44)
    chord_font = ImageFont.truetype(str(FONT), 40)
    descent = max(canonical_box(lyric_font, c)[3] - 2 * lyric_font.size for c in '주님의사막')
    baselines = [b[3] - descent for b in row_boxes]
    lyric_parts = {}
    lyric_rows = []
    source_events = {e['onset']: e for e in inv['measures'][1]['events']}
    for i, onset in enumerate(ONSETS):
        e = source_events[onset]
        x = (e['source_bbox'][0] + e['source_bbox'][2]) / 2
        for row, syllables in enumerate(LYRICS):
            name = f'lyric-{row+1}-{onset.replace("/","_")}'
            mask, info = text_mask(
                SIZE, lyric_font, syllables[i], center_x=x, baseline=baselines[row]
            )
            lyric_parts[name] = mask
            lyric_rows.append(
                {
                    'component': name,
                    'event_id': e['id'],
                    'onset': onset,
                    'row': row + 1,
                    'text': syllables[i],
                    **info,
                }
            )
    rest, rest_info = whole_rest(SIZE, staff, 2160.5)
    structures, structure_info = ending_repeat(
        SIZE,
        graph['symbols']['sheet#1:5201'],
        [graph['symbols'][k] for k in ['sheet#1:24', 'sheet#1:26']],
        [graph['symbols'][k] for k in ['sheet#1:5765', 'sheet#1:5767']],
        digit_box[:2],
    )
    scaffold_mask = scaffold(
        SIZE,
        staff,
        [639, 1598, 1961, 2397],
        {2397: graph['symbols']['sheet#1:26']['geometry']['bbox']},
    )
    frozen_source_parts = {n: sha(p) for n, p in ((p.name, p) for p in PRIOR.glob('*alpha.png'))}
    dump(
        out / 'pre-render-freeze.json',
        {
            'approval_sha256': owner['approval_sha256'],
            'protocol_sha256': sha(PROTOCOL),
            'source_review_sheet_sha256': owner['review_sheet_sha256'],
            'cached_gt14_alpha_hashes': frozen_source_parts,
            'source_text_measurement_boxes': boxes,
            'lyric_windows_bbox': row_boxes,
            'lyric_baselines': baselines,
            'semantic_lyric_tokens': 14,
            'new_extender_glyphs': 0,
            'ambiguous_objects': EXCLUDED,
        },
    )
    reports = []
    images = []
    original = panel(source.crop(VIEW), 'Unchanged original Bb source comparison')
    original.save(out / 'original-second-system.png')
    for target, shift in [('A', -1), ('G', -3)]:
        target_score = copy.deepcopy(augmented)
        summary = transpose_score(target_score, shift, 'key')
        mem = validate(augmented, target_score, shift, 'key', summary).to_dict()
        target_score.write('musicxml', fp=str(out / f'{target}-transposed.musicxml'))
        parsed = converter.parse(str(out / f'{target}-transposed.musicxml'))
        disk = validate(augmented, parsed, shift, 'key', summary).to_dict()
        require(
            mem['ok']
            and disk['ok']
            and full_lyric_signature(augmented) == full_lyric_signature(parsed),
            'Unchanged full V3 target guard failed',
        )
        frozen = converter.parse(str(OLD / f'{target}-transposed.musicxml'))
        require(
            [event_signature(m) for m in parsed.parts[0].getElementsByClass(stream.Measure)]
            == [event_signature(m) for m in frozen.parts[0].getElementsByClass(stream.Measure)],
            'Cached music semantics changed',
        )
        guards[target] = {'in_memory': mem, 'serialized': disk}
        cached = Image.open(PRIOR / f'{target}-provisional-music-alpha.png').copy()
        prior_canvas = Image.open(GT13A6 / f'{target}-two-system-alpha.png').copy()
        fixed_music = union([prior_canvas, scaffold_mask, cached, rest, *structures.values()])
        chords = {}
        chord_report = []
        for (number, source_text), box in zip(CHORDS.items(), boxes):
            text = transpose_chord_text(source_text, shift, original_key='Bb', target_key=target)
            measure = list(parsed.parts[0].getElementsByClass(stream.Measure))[number - 1]
            cs = list(measure.getElementsByClass(harmony.ChordSymbol))
            require(
                len(cs) == 1 and chord_text(cs[0]) == text,
                'Chord root/quality/bass serialization mismatch',
            )
            mask, info = text_mask(SIZE, chord_font, text, left_top=box[:2])
            chords[f'chord-m{number}'] = mask
            bounds = mask.getbbox()
            omr = inv['measures'][number - 5]['omr_bounds']
            chord_report.append(
                {
                    'measure': number,
                    'source_chord': source_text,
                    'target_chord': text,
                    'source_box': box,
                    'measure_width_conflict': bounds[0] < omr[0] or bounds[2] > omr[2],
                    **info,
                }
            )
        fixed = union([fixed_music, *chords.values()])
        domain = displacement_domain(
            union(list(lyric_parts.values())), fixed, Image.new('L', SIZE), VIEW
        )
        feasible = domain['selected_dy'] is not None
        dy = domain['selected_dy'] if feasible else 0
        moved = {n: translate(p, dy, VIEW) for n, p in lyric_parts.items()}
        text_union = union(list(moved.values()))
        hits = (np.asarray(text_union) > 0) & (np.asarray(fixed) > 0)
        pair_hits = contacts(moved)
        distances = ink_distance(fixed)
        clearance = float(distances[np.asarray(text_union) > 0].min())
        chord_hits = {
            n: int(np.count_nonzero((np.asarray(p) > 0) & (np.asarray(fixed_music) > 0)))
            for n, p in chords.items()
        }
        other_pairs = contacts({**structures, **chords})
        clipped = [
            n
            for n, p in {**structures, **chords, **moved, 'rest': rest}.items()
            if p.getbbox()[0] < VIEW[0]
            or p.getbbox()[1] < VIEW[1]
            or p.getbbox()[2] > VIEW[2]
            or p.getbbox()[3] > VIEW[3]
        ]
        alpha = union([fixed, text_union])
        image = panel(
            native(alpha).crop(VIEW),
            f'{target} major: 13 owner-confirmed events, 3 chords, 14 lyric syllables; ambiguity exclusions remain',
        )
        image.save(out / f'predicted-{target.lower()}-second-system.png')
        images.append(image)
        preview = panel(
            native(alpha).crop((130, 310, 2430, 1030)),
            f'{target} first+second context / unresolved TENUTO-FERMATA objects excluded',
        )
        preview.save(out / f'{target}-first-plus-second-context.png')
        alpha.save(out / f'{target}-combined-alpha.png')
        cached.save(out / f'{target}-reused-music-alpha.png')
        rest.save(out / f'{target}-whole-rest-alpha.png')
        for n, p in {**structures, **chords, **moved}.items():
            p.save(out / f'{target}-{n}-alpha.png')
        reports.append(
            {
                'target': target,
                'owner_verified_events': 13,
                'rendered_events': 13,
                'cached_music_geometry_unchanged': True,
                'new_chords': chord_report,
                'lyric_rows': lyric_rows,
                'lyric_syllables': 14,
                'lyric_hold_at_onset3': 'NO_NEW_TOKEN',
                'ambiguous_extender_glyphs_rendered': 0,
                'lyric_baselines': baselines,
                'lyric_displacement_dy': dy,
                'displacement_domain': domain,
                'lyric_music_unique_contact_pixels': int(hits.sum()),
                'lyric_lyric_contacts': pair_hits,
                'minimum_lyric_to_fixed_ink_center_distance_px': clearance,
                'chord_to_music_contact_pixels': chord_hits,
                'structure_chord_contact_pairs': other_pairs,
                'clipping': clipped,
                'whole_rest': rest_info,
                'ending_repeat': structure_info,
                'collision_safety': (
                    'PASS'
                    if feasible
                    and not hits.any()
                    and not pair_hits
                    and not clipped
                    and not any(chord_hits.values())
                    and not other_pairs
                    and not any(c['measure_width_conflict'] for c in chord_report)
                    else 'BLOCKED_OR_NEEDS_REFINEMENT'
                ),
                'SOURCE_VERIFICATION': 'OWNER_VERIFIED_LISTED_CONTENT_WITH_EXCLUSIONS',
                'RENDERING_COMPLETENESS': 'INCOMPLETE_UNRESOLVED_SYMBOLS',
                'VISUAL_QUALITY': 'PENDING_POST_FREEZE_INSPECTION',
                'ambiguous_object_ids': EXCLUDED,
                'old_notehead_max_residual_px': read(PRIOR / 'rendering-validation.json')[0][
                    'max_head_anchor_residual'
                ],
                'new_independent_ground_truth_labels': 0,
            }
        )
    sheet = Image.new(
        'RGB', (original.width, original.height + sum(i.height for i in images)), 'white'
    )
    sheet.paste(original, (0, 0))
    y = original.height
    for image in images:
        sheet.paste(image, (0, y))
        y += image.height
    sheet.save(out / 'comparison-contact-sheet.png')
    dump(out / 'rendering-validation.json', reports)
    dump(out / 'semantic-integrity.json', guards)
    require(
        all(file_hashes(Path(p)) == h for p, h in histories.items()), 'Historical files changed'
    )
    require(sha(SOURCE) == owner['source_sha256'], 'Original source changed')
    dump(
        out / 'input-freeze.json',
        {
            'history_files': histories,
            'owner_binding_sha256': sha(BINDING),
            'protocol_sha256': sha(PROTOCOL),
            'producer_sha256': sha(Path(__file__)),
            'notation_helper_sha256': sha(ROOT / 'scripts/research/gt14a_notation.py'),
            'font_sha256': sha(FONT),
            'korean_font_sha256': sha(KOREAN_FONT),
        },
    )
    dump(
        out / 'validation-summary.json',
        {
            'status': 'INCOMPLETE_UNRESOLVED_SYMBOLS',
            'owner_verified_events': 13,
            'rendered_events': 13,
            'confirmed_chords_rendered': 3,
            'confirmed_syllables_rendered': 14,
            'ending1_backward_repeat_rendered': True,
            'ambiguous_objects_preserved_unclassified': EXCLUDED,
            'source_ink_authorization': False,
            'full_V3_guards': 'PASS',
            'visual_review': 'PENDING_POST_FREEZE',
        },
    )
    dump(
        out / 'prediction-freeze.json',
        {'files': file_hashes(out), 'phase': 'BEFORE_AGENT_VISUAL_REVIEW_NO_REFERENCE_ACCESS'},
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    run(parser.parse_args().out)
