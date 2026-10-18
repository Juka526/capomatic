"""Native source-only review packet. No OMR, predictions, or coordinator answers."""

from __future__ import annotations

import argparse
from datetime import datetime
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import shutil

from PIL import Image
from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes
from scripts.research.ground_truth_02 import verify_inputs

VERSION = 'gt02-reference-collection/1'
CASE_FIELDS = (
    'case_id',
    'status',
    'printed_measure_identity',
    'observed_system_identity',
    'boundary_or_crop_issue',
    'notes_and_rests',
    'chord_symbols',
    'ties_slurs',
    'repeat_ending_context',
    'lyric_observations',
    'uncertainty',
)
EVENT_FIELDS = {
    'event_id',
    'kind',
    'voice',
    'onset_ql',
    'duration_ql',
    'written_pitch',
    'accidental',
    'uncertainty',
}
CHORD_FIELDS = {
    'onset_ql',
    'literal_text',
    'root',
    'quality',
    'alterations',
    'slash_bass',
    'uncertainty',
}
CURVE_FIELDS = {'type', 'touching_event_ids', 'continues_outside_crop', 'uncertainty'}
INDEPENDENCE_FIELDS = {
    'worked_on_GT01_GT02_or_architecture',
    'seen_predictions_omr_or_coordinator_answers',
    'seen_other_reader_submission',
    'expertise',
    'training_page_sha256_exclusions',
    'independent_source_reading_attested',
}
INSTRUCTIONS = {
    'version': VERSION,
    'task': 'Independently transcribe visible original ink in each focus region. Use full system and full page for clef, key, bar number, ties and endings. Correct uncertain crop/measure boundaries in the form. Do not infer answers by transposing another version.',
    'answers': 'No reference answers or expected matches are supplied. Do not consult predictions, OMR, coordinator diagnostic reports, or another reader. Record UNKNOWN rather than guess.',
    'coordinates': 'Native unchanged image pixels, x right/y down, first pixel center (0,0), half-open crop bounds. Page position = local pixel-index-center + crop origin; declare viewer uncertainty in boundary_or_crop_issue. No implicit resizing for coordinate observations.',
    'observations': 'Record the printed measure identity and observed system yourself. Notes/rests use exact quarterLength fractions as strings, voice and written pitch including octave/accidental spelling. Separate chord literal names, qualities, alterations and slash bass. Preserve ties/slurs and first/second endings, including continuation outside crop.',
    'unknown': 'Set observation status UNKNOWN, PARTIAL or UNREADABLE with a nonempty uncertainty reason when needed. Null means UNKNOWN, [] means explicitly observed none; never use [] for missing work.',
    'fields': {
        'notes_and_rests': sorted(EVENT_FIELDS),
        'chord_symbols': sorted(CHORD_FIELDS),
        'ties_slurs': sorted(CURVE_FIELDS),
    },
    'statuses': ['OBSERVED', 'PARTIAL', 'UNKNOWN', 'UNREADABLE'],
    'eligibility': 'Two music-literate readers not involved in GT01/GT02, recognition, architecture/planning or coordinator analysis. Coordinator verifies identities/exclusions externally. Freeze training page hashes before viewing evaluation cases; exclude all evaluation pages.',
    'custody': 'A and B use separate sessions/drafts. Neither can see the other export. Custodian stores signed exports outside the packet, hashes and freezes each separately with independently retained receipts. No comparison until BOTH freezes. Never overwrite a frozen primary.',
    'adjudication': 'A third eligible independent reader reviews source plus both frozen submissions only, after both freezes. Retain both primaries, unknowns and disagreement; store separate adjudication tied to their hashes. No accepted ground truth before independent A/B review and adjudication of disagreements.',
    'limits': 'Files cannot authenticate humans or enforce access separation. Custodian must record eligibility, exposure/access and blinding breaches; stop collection on a breach. Validation here checks schema, not musical truth or acceptance.',
}


def opaque(text):
    return hashlib.sha256(text.encode()).hexdigest()[:24]


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def prepare(images, registration, out, private_index):
    require(
        not out.exists() and not private_index.exists(), 'New packet and private index required'
    )
    require(
        out.resolve() != private_index.resolve()
        and out.resolve() not in private_index.resolve().parents,
        'Private index must stay outside packet',
    )
    for source in images.values():
        require(
            out.resolve() != source.parent.resolve()
            and source.parent.resolve() not in out.resolve().parents,
            'Output inside immutable source evidence',
        )
    evidence = Path(os.path.commonpath([str(p.resolve().parent) for p in images.values()]))
    for path in (out, private_index):
        require(
            not any(p.is_symlink() for p in (path, *path.parents)), 'Output symlink path forbidden'
        )
        require(
            path.resolve() != evidence and evidence not in path.resolve().parents,
            'Output inside immutable evidence',
        )
    out.mkdir(parents=True)
    cases = []
    links = []
    for label, page in registration['pages'].items():
        source = images[label]
        require(sha(source) == page['source_sha256'], 'Source/raster binding mismatch')
        native = Image.open(source)
        pid = opaque(sha(source))
        pagefile = f'page-{pid}.png'
        shutil.copyfile(source, out / pagefile)
        for system in page['systems']:
            sy = system['system']
            ys = system['staff_lines_y']
            bounds = [
                0,
                max(0, math.floor(ys[0] - 140)),
                native.width,
                min(native.height, math.ceil(ys[-1] + 170)),
            ]
            systemfile = f'system-{opaque(pid+str(bounds))}.png'
            native.crop(bounds).save(out / systemfile)
            for m in [m for m in page['measures'] if m['system'] == sy]:
                crop = [
                    max(0, math.floor(m['left']['x'] - 24)),
                    bounds[1],
                    min(native.width, math.ceil(m['right']['x'] + 24)),
                    bounds[3],
                ]
                ident = 'case-' + opaque(pid + str(crop))
                focus = f'{ident}.png'
                native.crop(crop).save(out / focus)
                cases.append(
                    {
                        'case_id': ident,
                        'focus_image': focus,
                        'focus_bounds_half_open': crop,
                        'system_image': systemfile,
                        'system_bounds_half_open': bounds,
                        'page_image': pagefile,
                        'source_sha256': sha(source),
                        'focus_sha256': sha(out / focus),
                    }
                )
                links.append(
                    {
                        'case_id': ident,
                        'coordinator_page_label': label,
                        'pdf_page': page['pdf_page'],
                        'printed_measure_candidate': m['printed_measure'],
                    }
                )
        require(sha(source) == page['source_sha256'], 'Source changed during packet preparation')
    cases.sort(key=lambda r: r['case_id'])
    require(len({r['case_id'] for r in cases}) == len(cases), 'Duplicate source crop cases')
    dump(out / 'cases.json', {'version': VERSION, 'cases': cases})
    dump(out / 'instructions.json', INSTRUCTIONS)
    for role in ['A', 'B']:
        form = {
            'version': VERSION,
            'packet_cases_sha256': sha(out / 'cases.json'),
            'role': role,
            'status': 'PENDING',
            'person_id': None,
            'signed_at': None,
            'independence': dict.fromkeys(sorted(INDEPENDENCE_FIELDS)),
            'cases': [
                {
                    'case_id': r['case_id'],
                    'status': 'PENDING',
                    **dict.fromkeys(k for k in CASE_FIELDS if k not in {'case_id', 'status'}),
                }
                for r in cases
            ],
        }
        dump(out / f'blank-{role}.json', form)
    dump(
        private_index,
        {
            'version': VERSION,
            'case_linkage': links,
            'packet_file_hashes': file_hashes(out),
            'distribution': 'COORDINATOR ONLY. Never distribute this file or parent output directory to readers.',
        },
    )
    for p in out.iterdir():
        p.chmod(0o444)
    return {
        'packet_status': 'PREPARED_FOR_INDEPENDENT_REVIEW_NOT_ACCEPTED_GROUND_TRUTH',
        'cases': len(cases),
        'page_images': len(images),
        'system_images': sum(len(p['systems']) for p in registration['pages'].values()),
        'actual_independent_submissions': 0,
        'packet_hash_binding': sha(private_index),
        'external_eligibility_and_separate_sessions': 'REQUIRED_BEFORE_COLLECTION',
    }


def verify_packet(packet, private_index):
    require(not packet.is_symlink(), 'Symlink packet forbidden')
    expected = json.loads(private_index.read_text())['packet_file_hashes']
    require(
        file_hashes(packet) == expected, 'Packet missing/changed/unexpected file; do not distribute'
    )
    require(
        all(p.is_file() and not p.is_symlink() for p in packet.iterdir()),
        'Unexpected packet directory/symlink',
    )
    return expected


def exact(value, keys):
    require(isinstance(value, dict) and set(value) == set(keys), 'Unexpected/missing fields')


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def rational(value, positive=False):
    if value is None:
        return
    require(isinstance(value, str), 'Exact quarterLength fraction string or null required')
    try:
        q = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError('Invalid rational timing') from exc
    require(q > 0 if positive else q >= 0, 'Invalid musical time')


def validate_submission(data, packet, role):
    exact(
        data,
        {
            'version',
            'packet_cases_sha256',
            'role',
            'status',
            'person_id',
            'signed_at',
            'independence',
            'cases',
        },
    )
    require(
        data['packet_cases_sha256'] == sha(packet / 'cases.json'),
        'Packet submission binding changed',
    )
    require(
        data['version'] == VERSION and data['role'] == role and role in ['A', 'B'],
        'Version/role mismatch',
    )
    require(
        data['status'] == 'SIGNED_INDEPENDENT_OBSERVATION' and nonempty(data['person_id']),
        'Signed independent observation required',
    )
    require(nonempty(data['signed_at']), 'Signature time required')
    when = datetime.fromisoformat(data['signed_at'].replace('Z', '+00:00'))
    require(when.tzinfo is not None, 'Timezone required')
    independence = data['independence']
    exact(independence, INDEPENDENCE_FIELDS)
    for field in [
        'worked_on_GT01_GT02_or_architecture',
        'seen_predictions_omr_or_coordinator_answers',
        'seen_other_reader_submission',
    ]:
        require(independence[field] is False, 'Reviewer independence/exclusion failure')
    require(
        independence['independent_source_reading_attested'] is True
        and nonempty(independence['expertise']),
        'Expertise and independent source-reading attestation required',
    )
    exclusions = independence['training_page_sha256_exclusions']
    require(
        isinstance(exclusions, list) and exclusions, 'Frozen separate training page hashes required'
    )
    cases = json.loads((packet / 'cases.json').read_text())['cases']
    source_hashes = {c['source_sha256'] for c in cases}
    require(
        all(
            isinstance(h, str)
            and len(h) == 64
            and set(h) <= set('0123456789abcdef')
            and h not in source_hashes
            for h in exclusions
        ),
        'Evaluation page cannot be a training page',
    )
    require(
        [r['case_id'] for r in data['cases']] == [r['case_id'] for r in cases],
        'All cases in fixed packet order required',
    )
    for row in data['cases']:
        exact(row, CASE_FIELDS)
        require(
            row['status'] in INSTRUCTIONS['statuses'], 'Every case needs observed/unknown status'
        )
        require(
            nonempty(row['uncertainty']), 'Visibility/uncertainty reason required even if observed'
        )
        for field, fields in [
            ('notes_and_rests', EVENT_FIELDS),
            ('chord_symbols', CHORD_FIELDS),
            ('ties_slurs', CURVE_FIELDS),
        ]:
            values = row[field]
            if values is None:
                continue
            require(isinstance(values, list), 'Observations must be list or null')
            for value in values:
                exact(value, fields)
                require(
                    nonempty(value['uncertainty']),
                    'Every musical observation needs uncertainty context',
                )
                if field == 'notes_and_rests':
                    require(
                        value['kind'] in ['NOTE', 'REST'] and nonempty(value['event_id']),
                        'Note/rest identity required',
                    )
                    rational(value['onset_ql'])
                    rational(value['duration_ql'], True)
                elif field == 'chord_symbols':
                    rational(value['onset_ql'])
                else:
                    require(value['type'] in ['TIE', 'SLUR', 'UNKNOWN'], 'Unknown curve kind')
    return {
        'status': 'SCHEMA_VALID_NOT_ACCEPTED_GROUND_TRUTH',
        'role': role,
        'cases': len(cases),
        'external_identity_independence_and_freeze_checks_still_required': True,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--gt01', type=Path, required=True)
    p.add_argument('--registration', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--private-index', type=Path, required=True)
    a = p.parse_args()
    root = a.gt01
    verify_inputs(root)
    reg = json.loads(a.registration.read_text())
    images = {
        'Bb': root / 'source-only/source.png',
        'A': root / 'reference-input/A.png',
        'G': root / 'reference-input/G.png',
    }
    print(json.dumps(prepare(images, reg, a.out, a.private_index), indent=2))


if __name__ == '__main__':
    main()
