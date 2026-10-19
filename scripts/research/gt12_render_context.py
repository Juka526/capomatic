"""Owner-confirmed, standalone measure-context experiment; never edits source ink."""

import argparse
import copy
import math
from pathlib import Path
import shutil
import time

import numpy as np
from fontTools.ttLib import TTFont
from music21 import converter, harmony, note, stream
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.chords import chord_symbol_from_text, chord_text, transpose_chord_text
from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt05_raster_anchor import glyph
from scripts.research.gt11_complete_measure import (
    FONT,
    GT01,
    event_signature,
    events_of,
    read,
    require,
    verify_inventory,
)
from scripts.research.paired_ground_truth_01 import dump, file_hashes, sha

GT11 = Path('/private/tmp/capomatic-v4-gt11')
PROTOCOL = Path(__file__).resolve().parents[2] / 'docs/V4_GT12_RENDER_PROTOCOL.json'
KOREAN_FONT = Path('/System/Library/Fonts/Supplemental/AppleGothic.ttf')
CROP = (1300, 330, 1860, 720)


def confirmation(record, out):
    require(
        record['classification'] == 'OWNER_VERIFIED_SOURCE', 'Explicit owner confirmation required'
    )
    require(record['independent_ground_truth'] is False, 'Must not claim independent ground truth')
    require(record['all_checklist_content_explicitly_confirmed'] is True, 'Incomplete confirmation')
    require((record['source_page'], record['printed_measure']) == (2, 3), 'Wrong source identity')
    require(
        record['source_chord'] == 'F', 'This fixed research run supports confirmed F major only'
    )
    require(
        record['upper_lyrics'] == ['주', '님', '의']
        and record['lower_lyrics'] == ['사', '막', '의'],
        'Changed content needs a new declared run',
    )
    require(
        sha(Path(record['actual_confirmation_file'])) == record['actual_confirmation_sha256'],
        'Confirmation bytes changed',
    )
    require(
        sha(out / 'source-review-sheet.png') == record['review_sheet_sha256'],
        'Wrong reviewed image',
    )
    require(
        sha(out / 'owner-confirmation/normalized-source-checklist.json')
        == record['pending_normalized_checklist_sha256'],
        'Wrong confirmed checklist',
    )


def ink_bbox(source, window):
    """Display-placement measurement only; never source-ink ownership."""
    a = np.asarray(source.convert('L').crop(window))
    ys, xs = np.where(a < 127)
    require(len(xs) > 0, 'Source alignment window lacks observable support')
    return [
        int(xs.min()) + window[0],
        int(ys.min()) + window[1],
        int(xs.max()) + window[0] + 1,
        int(ys.max()) + window[1] + 1,
    ]


def canonical_box(font, char):
    tile = Image.new('L', (font.size * 6, font.size * 6))
    ImageDraw.Draw(tile).text(
        (2 * font.size, 2 * font.size), char, font=font, fill=255, anchor='ls'
    )
    box = tile.getbbox()
    require(box is not None, 'Missing text glyph')
    return box


def text_mask(size, font, char, *, center_x=None, baseline=None, left_top=None):
    box = canonical_box(font, char)
    width, height = box[2] - box[0], box[3] - box[1]
    if left_top is not None:
        anchor = (left_top[0] + (width - 1) / 2, left_top[1] + (height - 1) / 2)
    else:
        anchor = (center_x, baseline + (box[1] + box[3] - 1) / 2 - 2 * font.size)
    mask, info = glyph(size, font, char, anchor, (0, 0, 0, 0), 1)
    info.pop('font_outline_anchor')  # No text-outline/optical-center assertion.
    require(all(abs(v) <= 0.5 for v in info['anchor_residual']), 'Text raster placement failed')
    info.update(text=char, measured_advance_px=font.getlength(char), measured_ink_width_px=width)
    return mask, info


def collisions(parts):
    result = []
    names = list(parts)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            count = int(np.count_nonzero((np.asarray(parts[a]) > 0) & (np.asarray(parts[b]) > 0)))
            if count:
                result.append({'a': a, 'b': b, 'pixels': count})
    return result


def panel(crop, title):
    canvas = Image.new('RGB', (crop.width, crop.height + 100), 'white')
    canvas.paste(crop, (0, 100))
    draw = ImageDraw.Draw(canvas)
    for y, text in enumerate(
        [
            'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE',
            'NOT FOR PERFORMANCE OR PRINTING',
            title,
            'Contextual measure: G clef; key stated above, not engraved.',
            'Lyrics newly typeset; no original-pixel preservation claim.',
        ]
    ):
        draw.text((6, 4 + y * 18), text, fill='black')
    return canvas


def augment_source(score, record):
    m = list(score.parts[0].getElementsByClass(stream.Measure))[2]
    require(len(m.getElementsByClass(harmony.ChordSymbol)) == 0, 'Unexpected existing chord')
    events = events_of(m)
    require(
        [e.pitch.nameWithOctave if e.isNote else None for e in events] == [None, 'B-3', 'C4', 'F4'],
        'Source events changed',
    )
    require([e.quarterLength for e in events] == [1, 1, 1, 1], 'Source rhythm changed')
    m.insert(0, chord_symbol_from_text(record['source_chord']))
    for number, row in enumerate([record['upper_lyrics'], record['lower_lyrics']], 1):
        for n, syllable in zip([e for e in events if e.isNote], row):
            n.lyrics.append(note.Lyric(text=syllable, number=number))
    return score


def lyric_signature(score):
    m = list(score.parts[0].getElementsByClass(stream.Measure))[2]
    return [[(l.number, l.text) for l in n.lyrics] for n in events_of(m)]


def run(out, record_path):
    started = time.monotonic()
    record = read(record_path)
    confirmation(record, out)
    require(
        not (out / 'predicted-a.png').exists() and not (out / 'predicted-g.png').exists(),
        'Never overwrite predictions',
    )
    details = out / 'confirmed-context'
    require(not details.exists(), 'New run directory required')
    protocol = read(PROTOCOL)
    prior = file_hashes(out)
    archive = out.with_name(out.name + '-pre-confirmed-context')
    require(not archive.exists(), 'Prior evidence archive already exists')
    verify_inventory(GT11 / 'gt11-input')
    old = file_hashes(GT11 / 'gt11-output')
    frozen = read(GT11 / 'gt11-output/prediction-freeze.json')
    require(
        all(sha(GT11 / 'gt11-output' / p) == h for p, h in frozen['files'].items()),
        'Historical predictions changed',
    )
    # Preserve prior pending reports, review images and candidate bytes before superseding metadata.
    shutil.copytree(out, archive)
    require(file_hashes(archive) == prior, 'Prior evidence archive mismatch')
    details.mkdir()
    shutil.copyfile(record['actual_confirmation_file'], details / 'owner-visual-confirmation.txt')
    dump(details / 'confirmed-source.json', record)
    source_path = GT11 / 'gt11-input/source.png'
    source = Image.open(source_path)
    source_sha = sha(source_path)
    chord_box = ink_bbox(source, protocol['source_chord_measurement_window'])
    row_boxes = [ink_bbox(source, w) for w in protocol['source_lyric_row_measurement_windows']]
    lyric_font = ImageFont.truetype(str(KOREAN_FONT), 44)
    chord_font = ImageFont.truetype(str(FONT), 40)
    cmap = TTFont(KOREAN_FONT).getBestCmap()
    require(all(ord(c) in cmap for c in '주님의사막'), 'Korean font lacks confirmed syllables')
    baseline_offset = max(
        canonical_box(lyric_font, c)[3] - 2 * lyric_font.size for c in '주님의사막'
    )
    baselines = [b[3] - baseline_offset for b in row_boxes]
    score = converter.parse(str(GT01 / 'predictions/baseline-exec/source/recognized.musicxml'))
    augmented = augment_source(copy.deepcopy(score), record)
    augmented.write('musicxml', fp=str(details / 'owner-augmented-source.musicxml'))
    roundtrip_source = converter.parse(str(details / 'owner-augmented-source.musicxml'))
    require(
        lyric_signature(roundtrip_source) == lyric_signature(augmented),
        'Source lyrics changed in serialization',
    )
    source_guard = validate(augmented, roundtrip_source, 0, 'key').to_dict()
    require(source_guard['ok'], 'Owner-augmented source serialization failed full guard')
    gt11 = read(GT11 / 'gt11-output/rendering-metrics.json')
    target_metrics = []
    guard_reports = {'owner_augmented_source_roundtrip': source_guard}
    panels = [panel(source.crop(CROP), 'Unchanged Bb source; printed measure 3')]
    for name, shift in [('A', -1), ('G', -3)]:
        target = copy.deepcopy(augmented)
        summary = transpose_score(target, shift, 'key')
        mem = validate(augmented, target, shift, 'key', summary).to_dict()
        target.write('musicxml', fp=str(details / f'{name}-transposed.musicxml'))
        parsed = converter.parse(str(details / f'{name}-transposed.musicxml'))
        serialized = validate(augmented, parsed, shift, 'key', summary).to_dict()
        require(mem['ok'] and serialized['ok'], 'Full V3 integrity guard failed')
        require(lyric_signature(parsed) == lyric_signature(augmented), 'Target lyrics changed')
        m = list(parsed.parts[0].getElementsByClass(stream.Measure))[2]
        historical = converter.parse(str(GT11 / 'gt11-output' / f'{name}-transposed.musicxml'))
        hm = list(historical.parts[0].getElementsByClass(stream.Measure))[2]
        require(event_signature(m) == event_signature(hm), 'Music events differ from frozen GT11')
        expected_chord = transpose_chord_text('F', shift, original_key='Bb', target_key=name)
        cs = list(m.getElementsByClass(harmony.ChordSymbol))
        require(
            len(cs) == 1 and cs[0].offset == 0 and chord_text(cs[0]) == expected_chord,
            'Chord semantics/placement changed',
        )
        guard_reports[name] = {
            'in_memory': mem,
            'serialized': serialized,
            'chord': expected_chord,
            'harmony_offset': '0',
            'lyric_identity_preserved': True,
        }
        base = Image.open(GT11 / 'gt11-output/components' / name / 'notation-alpha.png').copy()
        parts = {'music': base}
        chord_mask, chord_info = text_mask(
            source.size, chord_font, expected_chord, left_top=chord_box[:2]
        )
        parts['chord'] = chord_mask
        current = next(r for r in gt11['metrics'] if r['target'] == name)
        notes = [r for r in current['events'] if r['kind'] == 'NOTE']
        lyrics = []
        for row_i, row in enumerate([record['upper_lyrics'], record['lower_lyrics']]):
            for syllable, e in zip(row, notes):
                mask, info = text_mask(
                    source.size,
                    lyric_font,
                    syllable,
                    center_x=e['requested_anchor'][0],
                    baseline=baselines[row_i],
                )
                component = f'lyric-{row_i + 1}-{e["semantic_id"]}'
                parts[component] = mask
                info.update(
                    row=row_i + 1,
                    semantic_id=e['semantic_id'],
                    source_note_x=e['requested_anchor'][0],
                )
                require(info['baseline'][1] == baselines[row_i], 'Lyric baseline changed')
                lyrics.append(info)
        intersections = collisions(parts)
        clipping = []
        for component, mask in parts.items():
            b = mask.getbbox()
            require(b is not None, 'Missing rendered component')
            if b[0] < CROP[0] or b[1] < CROP[1] or b[2] > CROP[2] or b[3] > CROP[3]:
                clipping.append(component)
            mask.save(details / (name + '-' + component.replace(':', '_') + '-alpha.png'))
        combined = Image.fromarray(np.maximum.reduce([np.asarray(p) for p in parts.values()]))
        combined.save(details / f'{name}-combined-alpha.png')
        black = Image.new('RGB', source.size, 'black')
        white = Image.new('RGB', source.size, 'white')
        # White + newly rendered alpha only. No original page pixels enter this target canvas.
        canvas = Image.composite(black, white, combined)
        prediction = panel(
            canvas.crop(CROP), f'{name} major; OWNER_VERIFIED_SOURCE; printed measure 3'
        )
        prediction.save(out / ('predicted-a.png' if name == 'A' else 'predicted-g.png'))
        panels.append(prediction)
        target_metrics.append(
            {
                'target': name,
                'events_rendered': 4,
                'chord': chord_info,
                'chord_text': expected_chord,
                'chord_anchor_basis': 'Measured source chord ink left/top; not first-note x',
                'lyric_syllables': lyrics,
                'text_music_ink_collisions': intersections,
                'clipping': clipping,
                'notehead_max_anchor_residual': current['max_notehead_raster_anchor_residual'],
                'music_alpha_sha256': sha(
                    GT11 / 'gt11-output/components' / name / 'notation-alpha.png'
                ),
                'music_alpha_unchanged': True,
                'missing_or_duplicated_music_events': 0,
                'lyric_count': len(lyrics),
                'staff_measure_geometry_deviation': 0,
            }
        )
    sheet = Image.new('RGB', (sum(p.width for p in panels), panels[0].height), 'white')
    for i, p in enumerate(panels):
        sheet.paste(p, (i * p.width, 0))
    sheet.save(out / 'comparison-contact-sheet.png')
    require(
        sha(source_path) == source_sha and file_hashes(GT11 / 'gt11-output') == old,
        'Historical source/predictions changed',
    )
    require(
        sha(out / 'original-bb.png') == prior['original-bb.png'], 'Original review crop changed'
    )
    require(
        sha(out / 'owner-review-candidate.txt') == prior['owner-review-candidate.txt'],
        'Old owner candidate changed',
    )
    dump(
        out / 'rendering-metrics.json',
        {
            'protocol_sha256': sha(PROTOCOL),
            'source_sha256': source_sha,
            'font_sha256': {'music_and_chord': sha(FONT), 'Korean': sha(KOREAN_FONT)},
            'font_sizes': {'chord': 40, 'lyric': 44},
            'source_display_alignment_bboxes': {'chord': chord_box, 'lyric_rows': row_boxes},
            'lyric_baselines': baselines,
            'metrics': target_metrics,
            'seconds': time.monotonic() - started,
            'original_pixel_fidelity_claim': False,
        },
    )
    dump(details / 'semantic-integrity.json', guard_reports)
    normalized = read(out / 'owner-confirmation/normalized-source-checklist.json')
    normalized['review_provenance'].update(
        owner_verified_source=True,
        owner_confirmation='EXPLICITLY_CONFIRMED',
        actual_confirmation_sha256=record['actual_confirmation_sha256'],
    )
    for row in normalized['events_for_confirmation']:
        row['owner_confirmed'] = True
    for k in [
        'chord_for_confirmation',
        'lyrics_for_confirmation',
        'additional_symbols_for_confirmation',
    ]:
        normalized[k]['owner_confirmed'] = True
    normalized['authorization']['combined_rendering'] = 'AUTHORIZED_STANDALONE_NEW_CANVAS_ONLY'
    dump(out / 'source-checklist.json', normalized)
    dump(
        out / 'chord-audit.json',
        {
            'source': 'F',
            'source_basis': 'OWNER_VERIFIED_SOURCE',
            'raw_omr_harmony_count': 0,
            'owner_added_harmony_count': 1,
            'targets': {'A': 'E', 'G': 'D'},
            'source_anchor': chord_box[:2],
            'first_note_attachment': False,
            'harmony_offset': '0',
            'full_integrity': 'PASS',
            'exact_source_pixel_preservation': False,
        },
    )
    dump(
        out / 'lyric-audit.json',
        {
            'source_basis': 'OWNER_VERIFIED_SOURCE',
            'upper': record['upper_lyrics'],
            'lower': record['lower_lyrics'],
            'association_note_ids': [e['semantic_id'] for e in notes],
            'initial_rest_has_lyrics': False,
            'raw_omr_lyric_count': 0,
            'owner_added_lyric_count': 6,
            'rendering': 'NEWLY_TYPESET',
            'original_pixel_preservation': False,
        },
    )
    safe = all(
        not m['text_music_ink_collisions']
        and not m['clipping']
        and m['notehead_max_anchor_residual'] <= 0.5
        for m in target_metrics
    )
    status = {
        'SOURCE_RECOGNITION_COMPLETENESS': 'INCOMPLETE_RAW_OMR_CHORD_AND_LYRICS_MISSING',
        'OWNER_VERIFIED_SOURCE_CONTENT': 'COMPLETE_WITHIN_CONFIRMED_MEASURE_SCOPE',
        'RENDERING_COMPLETENESS': 'COMPLETE' if safe else 'INCOMPLETE',
        'VISUAL_QUALITY': 'UNVERIFIED_PENDING_POST_FREEZE_INSPECTION',
        'independent_ground_truth_labels': 0,
    }
    dump(out / 'completeness-report.json', status)
    dump(
        out / 'validation-summary.json',
        {
            'combined_rendering': 'RENDERED_PENDING_VISUAL_REVIEW' if safe else 'NEEDS_REFINEMENT',
            'completion_levels': status,
            'full_v3_guard': 'PASS',
            'source_unchanged': True,
            'GT11_unchanged': True,
            'prior_GT12_archive': str(archive),
            'prior_GT12_files_sha256': prior,
            'reference_pages_accessed': False,
            'source_pixels_composited_into_targets': False,
            'limitations': [
                'Mid-system contextual measure; clef and key context supplied in caption, not engraved',
                'Newly typeset lyrics are not original lyric pixels',
                'Owner review is not independent ground truth',
                'No source music removal or full-score output',
            ],
        },
    )
    dump(
        details / 'prediction-freeze.json',
        {
            'phase': 'BEFORE_VISUAL_REVIEW',
            'protocol_sha256': sha(PROTOCOL),
            'code_sha256': sha(Path(__file__)),
            'confirmation_sha256': record['actual_confirmation_sha256'],
            'output_files_sha256': file_hashes(out),
        },
    )
    return 'RENDERED_PENDING_VISUAL_REVIEW' if safe else 'NEEDS_REFINEMENT'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('gt12-output'))
    parser.add_argument('--confirmation', type=Path, required=True)
    args = parser.parse_args()
    print(run(args.out, args.confirmation))
