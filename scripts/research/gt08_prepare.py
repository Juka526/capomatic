"""Verify historical evidence; copy only unchanged source cases into neutral handoff."""

import argparse
from pathlib import Path
import subprocess

from PIL import Image

from scripts.research.ground_truth_02 import verify_inputs
from scripts.research.paired_ground_truth_01 import sha, file_hashes
from scripts.research.gt02_reference_packet import require
from scripts.research.gt08_review import (
    VERSION,
    COORDINATES,
    read_json,
    template,
    write_json,
    exclusive,
)

A_SHA = 'feeb33bec47b73d5e32f042bc9a5561944ed6314'
B_SHA = 'f3b808d3fb072d521f516ef9e8f50ef54bd59756'
SOURCE_SHA = 'eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de'
INSTRUCTIONS = '''Independent source-pixel extent review. Inspect ONLY these original-resolution images and neutral instructions. Do not consult recognition/OCR, predictions, coordinator reports, automated classifications or another reader's observations. Do not use an AI system to label or infer observations.

Coordinates: first pixel center (0,0), x right, y down, original crop size. Display zoom is allowed only if observations are exported in the original coordinate system. Never rescale or change supplied images. Annotation software may encode your own observations but must not classify pixels automatically.

Use CONFIRMED_TEXT for pixels confidently observed as printed text ink, including antialias ink when confident; CONFIRMED_NON_TEXT for confidently non-text pixels (including music or background). Neither category authorizes editing. MIXED means inseparable/shared content; UNKNOWN means not confidently classified, unreadable, unworked or uncertain boundary/fringe. Do not guess. Do not infer text from a rectangular envelope.

Export explicit run-length pixels [row,left,right_exclusive] grouped by category, ordered by row/left. Every crop pixel must have exactly one explicit category. Record uncertain pixels as MIXED/UNKNOWN rather than using unmarked gaps; no default labels. State uncertainty_status PRESENT if any MIXED/UNKNOWN exists, otherwise explicitly NONE_OBSERVED; explain uncertainty even if none was observed. These are extent observations, not a lyric transcription or score accuracy task. Overlapping cases may be ambiguous; preserve your observations and uncertainty rather than consulting other answers.

Readers A and B work in separate sessions and keep drafts/exports private. Fill the separate GT08 template, not the historical GT07 form. Declare eligibility, expertise, prior exposure, and HUMAN_SOURCE_REVIEW origin truthfully. Use a pseudonymous person_id; identifying records remain with the human custodian. Do not submit blank forms as observations. Freeze the complete original export without reformatting; retain original drafts separately.

A separate eligible human adjudicator starts ONLY after BOTH independent primary submissions and external custody checks have frozen. They receive original source pixels plus both frozen primaries and uncertainty, never predictions or coordinator classifications. Their separate export must reference both primary freeze hashes. Preserve both original reader exports; do not overwrite or silently complete them. Human-origin/independence attestation is checked separately from file/schema validity. These targeted overlapping crops do not establish whole-score accuracy.
'''


def freeze_files(root):
    f = read_json(root / 'prototype-freeze.json')
    actual = file_hashes(root)
    actual.pop('prototype-freeze.json')
    require(actual == f['files'], 'Historical prediction missing/changed')
    return f


def verify_evidence(gt01, a, b, gt06):
    verify_inputs(gt01)
    for worktree, expected in [(a, A_SHA), (b, B_SHA)]:
        require(
            subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=worktree, text=True).strip()
            == expected,
            'Wrong verified historical branch HEAD',
        )
    source = gt01 / 'predictions/baseline-exec/source/source.png'
    require(sha(source) == SOURCE_SHA, 'Wrong Bb raster')
    ar = a / 'gt07-text-output'
    br = b / 'gt07-flag-validation-output'
    report = read_json(ar / 'text-provenance-report.json')
    require(
        report['source_sha256'] == SOURCE_SHA
        and sha(gt01 / 'predictions/baseline-exec/source/recognized.omr') == report['omr_sha256'],
        'Text evidence source/OMR mismatch',
    )
    require(
        file_hashes(ar / 'independent-review-packet') == report['packet_files'],
        'Historical five-case packet changed',
    )
    native = Image.open(source)
    links = read_json(ar / 'custodian-only.json')
    blank = read_json(ar / 'independent-review-packet/blank-A.json')
    require(
        len(links) == len(blank['cases']) == 5
        and {r['case_id'] for r in links} == {r['case_id'] for r in blank['cases']},
        'Original five cases missing',
    )
    for row in links:
        old = ar / 'independent-review-packet' / f'{row["case_id"]}.png'
        crop = Image.open(old)
        expected = native.crop(tuple(row['page_bbox']))
        require(
            crop.mode == expected.mode
            and crop.size == expected.size
            and crop.tobytes() == expected.tobytes(),
            'Packet is not exact original source pixels',
        )
    graph = read_json(gt01 / 'predictions/baseline-exec/source/visual-graph.json')
    targets = []
    for prefix, output, inputs, expected in [
        ('GT06', gt06 / 'gt06-output', gt06 / 'gt06-inputs', {'A': 1982, 'G': 2026}),
        ('GT07B', b / 'gt07-flag-output', b / 'gt07-flag-inputs', {'A': 24, 'G': 233}),
    ]:
        f = freeze_files(output)
        require(
            sha(inputs / 'selection.json') == f['selection_sha256'],
            'Frozen source selection changed',
        )
        spec = read_json(inputs / 'selection.json')
        m = read_json(output / 'rendering-metrics.json')
        require(
            m['source_sha256'] == spec['source_sha256'] == SOURCE_SHA,
            'Source mismatch across experiments',
        )
        require(
            spec['protected'] == graph['text_protected_regions'],
            'Historical protection definitions changed',
        )
        require(
            all(v['ok'] for v in m['full_integrity'].values()),
            'Historical integrity result mismatch',
        )
        for row in m['metrics']:
            require(
                row['protected_envelope_contact_pixels'] == expected[row['target']],
                'Historical contact count changed',
            )
            targets.append(
                {
                    'experiment': prefix,
                    'target': row['target'],
                    'protected_envelope_pixels': row['protected_envelope_contact_pixels'],
                    'confirmed_text_contacts': 'UNKNOWN',
                    'confirmed_non_text_contacts': 'UNKNOWN',
                    'ambiguous_contacts': 'UNKNOWN',
                    'unresolved_protected_envelope_pixels': row[
                        'protected_envelope_contact_pixels'
                    ],
                }
            )
    contacts = read_json(br / 'source-contact-report-validated.json')
    sets = read_json(br / 'text-contact-set-relations.json')
    require(
        contacts['prototype_freeze_sha256'] == sha(b / 'gt07-flag-output/prototype-freeze.json'),
        'Text support record is not bound to frozen flags',
    )
    require(
        contacts['targets']['G']['unique_pixels']['TEXT_SUPPORT_CANDIDATE'] == 47
        and sets['text_support_contact_unique_pixels'] == 47
        and sets['inside_protected_envelopes'] == 47
        and sets['total_protected_contact_pixels'] == 233,
        'GT07B text-support diagnostic identity mismatch',
    )
    # Hash existing files only: no predictions, case images or labels are generated here.
    paths = [
        source,
        ar / 'text-provenance-report.json',
        ar / 'custodian-only.json',
        ar / 'related-text-support.json',
        ar / 'source-category-summary.json',
        br / 'source-contact-report-validated.json',
        br / 'text-contact-set-relations.json',
    ]
    for root in [
        ar / 'independent-review-packet',
        gt06 / 'gt06-output',
        gt06 / 'gt06-inputs',
        b / 'gt07-flag-output',
        b / 'gt07-flag-inputs',
    ]:
        paths.extend(p for p in root.rglob('*') if p.is_file())
    bindings = {str(p): sha(p) for p in sorted(set(paths))}
    return {
        'source_sha256': SOURCE_SHA,
        'gt07a_head': A_SHA,
        'gt07b_read_only_head': B_SHA,
        'files': bindings,
        'targets': targets,
        'gt07b_g_processed_text_support_candidate_coordinates': 47,
    }, links


def prepare(gt01, a, b, gt06, out):
    out = Path(out)
    require(
        not out.exists() and not any(p.is_symlink() for p in [out, *out.absolute().parents]),
        'New non-symlink GT08 output required',
    )
    require(
        not any(
            r.resolve() == out.resolve() or r.resolve() in out.resolve().parents
            for r in [gt01, a, b, gt06]
        ),
        'Output inside historical evidence forbidden',
    )
    binding, links = verify_evidence(gt01, a, b, gt06)
    packet = out / 'reviewer-handoff/source-only-packet'
    packet.mkdir(parents=True)
    cases = []
    for link in links:
        ident = link['case_id']
        original = a / 'gt07-text-output/independent-review-packet' / f'{ident}.png'
        image = Image.open(original)
        exclusive(packet / original.name, original.read_bytes())
        cases.append(
            {
                'case_id': ident,
                'image': original.name,
                'sha256': sha(original),
                'width': image.width,
                'height': image.height,
            }
        )
    exclusive(packet / 'instructions.txt', INSTRUCTIONS.encode())
    write_json(
        packet / 'packet.json',
        {
            'version': VERSION,
            'coordinate_system': COORDINATES,
            'cases': cases,
            'instructions_sha256': sha(packet / 'instructions.txt'),
        },
    )
    for role in ['A', 'B', 'ADJUDICATOR']:
        folder = out / 'reviewer-handoff' / role
        write_json(folder / 'submission-template.json', template(packet, role))
        exclusive(
            folder / 'HANDOFF.txt',
            (
                'Distribute ONLY the source-only-packet and this role folder. Never distribute other roles drafts or the surrounding research directory. '
                + (
                    'Do not start: both primary reviews must first be independently completed and frozen.'
                    if role == 'ADJUDICATOR'
                    else 'Inspect independently; do not view the other reader or any coordinator material.'
                )
                + '\n'
            ).encode(),
        )
    exclusive(
        out / 'custodian-case-map.json', (a / 'gt07-text-output/custodian-only.json').read_bytes()
    )
    write_json(
        out / 'collection-policy.json',
        {
            'version': VERSION,
            'packet_sha256': sha(packet / 'packet.json'),
            'case_map_sha256': sha(out / 'custodian-case-map.json'),
            'trusted_custodian_key_sha256': None,
            'trust_registration': 'Human task owner must verify/pin external custodian public key. Agent must not create keys, attestations or human observations.',
        },
    )
    exclusive(
        out / 'CUSTODIAN.txt',
        b'No eligible reviewers are currently assigned. WAITING_FOR_HUMAN_REVIEW. Do not fill, sign or freeze synthetic/agent labels. Register trusted human custodian key externally before collection. Separate A/B sessions; verify human identities, independence, exclusions and no automated labeling. Sign custody receipts bound to exact raw submission and packet hashes; preserve all originals. A third independent human adjudicates only after both primary freezes; reviewer-facing distribution excludes every diagnostic and custodian-only file. File hashes/signatures prove custody only, not human personhood or correct observations. No source removal or composition is authorized.\n',
    )
    for name in ['submitted-labels', 'adjudication', 'collision-audit']:
        (out / name).mkdir()
    write_json(
        out / 'collision-audit/pending.json',
        {
            'decision': 'WAITING_FOR_HUMAN_REVIEW',
            'audit_executed': False,
            'independently_verified_human_submissions': 0,
            'adjudications': 0,
            'targets': binding['targets'],
            'gt07b_g_processed_text_support_candidate_coordinates': 47,
            'candidate_coordinates_are_not_confirmed_text': True,
            'requirements': {
                'original_text_preservation': 'UNPROVEN_PENDING_HUMAN_EXTENTS',
                'old_music_removal': 'NOT_AUTHORIZED_REQUIRES_COMPLETE_OWNERSHIP',
            },
            'composition_authorized': False,
        },
    )
    write_json(out / 'evidence-binding.json', binding)
    write_json(
        out / 'validation-summary.json',
        {
            'decision': 'WAITING_FOR_HUMAN_REVIEW',
            'user_confirmed_no_assigned_reviewers': True,
            'actual_human_submissions_collected': 0,
            'actual_adjudications': 0,
            'case_count': 5,
            'case_images_byte_identical': True,
            'historical_predictions_regenerated': False,
            'source_sha256': SOURCE_SHA,
            'composition_authorized': False,
        },
    )
    require(
        all(sha(Path(p)) == value for p, value in binding['files'].items()),
        'Historical evidence changed during handoff',
    )
    return binding


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    prepare(
        Path('/private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output'),
        Path('/private/tmp/capomatic-v4-gt07-text'),
        Path('/private/tmp/capomatic-v4-gt07-flags'),
        Path('/private/tmp/capomatic-v4-gt06-extended'),
        args.out,
    )
    print('WAITING_FOR_HUMAN_REVIEW')
