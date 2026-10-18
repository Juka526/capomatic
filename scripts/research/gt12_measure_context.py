"""Prepare source-only GT-12 owner review; never infer human verification or render it."""

import argparse
from pathlib import Path
import shutil

from PIL import Image, ImageDraw

from scripts.research.gt11_complete_measure import read, require, verify_inventory
from scripts.research.paired_ground_truth_01 import dump, file_hashes, sha

BASE = '9d83c868b350b4435a8d775be655e0b23fc6cedd'
GT11 = Path('/private/tmp/capomatic-v4-gt11')
# Includes complete visible lyric rows, previous/next notation, and white margin below.
# Selection is source-only; this is a review crop, not a text-ownership mask.
CROP = (1300, 330, 1860, 720)


def checklist(inventory, image_sha):
    require(inventory['printed_measure'] == 3, 'Only fixed printed measure 3 is authorized')
    return {
        'study': 'GT12_SOURCE_ONLY_MEASURE_CONTEXT',
        'base': BASE,
        'understood_as': 'Prepare a full-context source checklist; only actual owner confirmation may supply missing chord/lyrics for a future standalone canvas.',
        'source_page': 2,
        'source_key': 'Bb major',
        'printed_measure': 3,
        'image_sha256': image_sha,
        'crop_page_bbox_right_bottom_exclusive': list(CROP),
        'pixel_coordinates': 'Native source pixels; page=(crop_x+1300,crop_y+330), no rescaling',
        'omr_observations': [
            {
                'event_id': e['source_event_id'],
                'kind': e['kind'],
                'written_pitch': e['written_pitch'],
                'onset_quarter_length': e['onset'],
                'duration_quarter_length': e['duration'],
                'voice': e['voice'],
                'physical_detected_center': e['physical_detected_center'],
                'source_completeness': 'UNVERIFIED',
            }
            for e in inventory['events']
        ],
        'agent_source_image_observations_NOT_HUMAN_CONFIRMED': {
            'chord_candidate': 'F',
            'lyric_rows_candidates': [['주', '님', '의'], ['사', '막', '의']],
            'candidate_note_associations': ['p1:m2:n0', 'p1:m2:n1', 'p1:m2:n2'],
            'additional_symbols': 'No additional attachment identified by agent/OMR; owner must check',
            'limitations': 'These readings must not be used as verified source text or chord input.',
        },
        'owner_review': {
            'status': 'WAITING_FOR_OWNER_SOURCE_CONFIRMATION',
            'actual_submission': None,
            'events': None,
            'onsets_and_durations': None,
            'additional_symbols_or_none': None,
            'chord_with_quality_bass_alterations': None,
            'exact_lyric_rows': None,
            'lyric_to_note_associations': None,
        },
        'provenance_boundary': {
            'owner_verification_label': 'OWNER_VERIFIED_SOURCE',
            'independent_ground_truth': False,
            'independent_labels_collected': 0,
            'no_automatic_completion_from_omr_agreement': True,
        },
    }


def review_gate(record):
    """Pending or incomplete human fields cannot authorize even a standalone composite."""
    owner = record['owner_review']
    fields = [
        'actual_submission',
        'events',
        'onsets_and_durations',
        'additional_symbols_or_none',
        'chord_with_quality_bass_alterations',
        'exact_lyric_rows',
        'lyric_to_note_associations',
    ]
    missing = [f for f in fields if owner.get(f) is None]
    return {
        'combined_rendering': 'BLOCKED',
        'owner_confirmed_events': [],
        'source_recognition_completeness': 'UNVERIFIED',
        'unverified_owner_fields': missing,
        'reason': 'This preparation tool retains candidate replies but does not authenticate source confirmation or authorize rendering. Actual visual confirmation and its validated render integration require a separate step.',
    }


def review_images(source, out, bbox=CROP):
    with Image.open(source) as im:
        require(im.mode == 'RGB', 'Explicit RGB source expected; no implicit mode conversion')
        require(
            0 <= bbox[0] < bbox[2] <= im.width and 0 <= bbox[1] < bbox[3] <= im.height,
            'Invalid crop',
        )
        crop = im.crop(bbox)
    crop.save(out / 'original-bb.png')
    header = 82
    sheet = Image.new('RGB', (crop.width, crop.height + header), 'white')
    sheet.paste(crop, (0, header))
    draw = ImageDraw.Draw(sheet)
    for y, text in enumerate(
        [
            'DEVELOPER-ONLY SOURCE REVIEW / GT-12 printed measure 3',
            'Bb source PDF page 2. Owner review; NOT independent ground truth.',
            f'Native crop: page bbox {tuple(bbox)}; no scaling.',
            'Confirm notes, durations, F candidate, BOTH lyric rows and attachments.',
        ]
    ):
        draw.text((6, 5 + 18 * y), text, fill='black')
    sheet.save(out / 'source-review-sheet.png')
    with Image.open(out / 'original-bb.png') as raw, Image.open(
        out / 'source-review-sheet.png'
    ) as labeled:
        require(raw.tobytes() == crop.tobytes(), 'Raw crop pixels changed')
        require(
            labeled.crop((0, header, crop.width, header + crop.height)).tobytes() == crop.tobytes(),
            'Review sheet source pixels changed',
        )


def retain_candidate(record, candidate, out):
    """Retain bytes, not an attestation: this path never confirms source content."""
    digest = sha(candidate)
    destination = out / 'owner-review-candidate.txt'
    shutil.copyfile(candidate, destination)
    require(sha(candidate) == sha(destination) == digest, 'Candidate submission changed')
    record['owner_review']['status'] = 'OWNER_REVIEW_CANDIDATE_PENDING_VISUAL_CONFIRMATION'
    record['owner_review']['actual_submission'] = {
        'file': destination.name,
        'sha256': digest,
        'review_type': 'OWNER_REVIEW_CANDIDATE',
        'source_verified': False,
        'independent_ground_truth': False,
    }
    return record


def prepare(out, owner_candidate=None):
    require(not out.exists(), 'Use a fresh output directory; never overwrite review evidence')
    verify_inventory(GT11 / 'gt11-input')
    historical = file_hashes(GT11 / 'gt11-output')
    frozen = read(GT11 / 'gt11-output/prediction-freeze.json')
    require(
        all(sha(GT11 / 'gt11-output' / p) == h for p, h in frozen['files'].items()),
        'GT11 freeze changed',
    )
    source = GT11 / 'gt11-input/source.png'
    source_sha = sha(source)
    out.mkdir(parents=True)
    review_images(source, out)
    inv = read(GT11 / 'gt11-output/source-event-inventory.json')
    record = checklist(inv, sha(out / 'original-bb.png'))
    if owner_candidate is not None:
        retain_candidate(record, owner_candidate, out)
    dump(out / 'source-checklist.json', record)
    dump(
        out / 'chord-audit.json',
        {
            'omr_harmony_count_in_measure': 0,
            'agent_source_candidate': 'F',
            'owner_confirmed_chord': None,
            'rendering': 'BLOCKED_PENDING_HUMAN_CONFIRMATION',
            'conditional_transpositions_not_predictions': {'F_if_confirmed': {'A': 'E', 'G': 'D'}},
            'target_reference_pages_used': False,
        },
    )
    dump(
        out / 'lyric-audit.json',
        {
            'recognized_musicxml_lyric_items': 0,
            'agent_candidates': record['agent_source_image_observations_NOT_HUMAN_CONFIRMED'][
                'lyric_rows_candidates'
            ],
            'owner_confirmed_rows': None,
            'owner_confirmed_associations': None,
            'rendering': 'BLOCKED_PENDING_HUMAN_CONFIRMATION',
            'future_method': 'Newly typeset human-confirmed text on standalone canvas; not original-pixel preservation',
        },
    )
    report = review_gate(record)
    report.update(
        {
            'recognized_events': 4,
            'missing_omr_content': ['F chord candidate', 'Korean lyric rows'],
            'unsupported_or_unvalidated_rendering': [
                'Korean typesetting and row baseline contract',
                'Chord placement and measured width',
                'Any additional owner-identified symbols',
            ],
            'owner_candidate_submissions_received': int(owner_candidate is not None),
            'visually_confirmed_source_submissions': 0,
            'independent_ground_truth_labels': 0,
        }
    )
    dump(out / 'completeness-report.json', report)
    require(file_hashes(GT11 / 'gt11-output') == historical, 'Historical GT11 files changed')
    require(sha(source) == source_sha, 'Original source changed')
    dump(
        out / 'validation-summary.json',
        {
            'base': BASE,
            'combined_rendering': 'BLOCKED',
            'reason': 'WAITING_FOR_OWNER_SOURCE_CONFIRMATION',
            'predicted_images_generated': [],
            'source_sha256': source_sha,
            'gt11_files_sha256': historical,
            'source_crop_pixel_equality': True,
            'gt11_freeze_unchanged': True,
            'outputs_sha256': file_hashes(out),
            'reference_pages_used': False,
            'source_removal_or_composition_authorized': False,
        },
    )
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('gt12-output'))
    parser.add_argument(
        '--owner-candidate',
        type=Path,
        help='Retain a real candidate reply; never grants verification',
    )
    args = parser.parse_args()
    print(prepare(args.out, args.owner_candidate)['combined_rendering'])
