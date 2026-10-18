"""Post-reference owner-region collision audit; no rendering or edit permission."""

import argparse
from collections import Counter
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from backend.omr_v4.ink import glyphs_from_omr, rle
from scripts.research.gt07_text import MUSICAL
from scripts.research.gt08_prepare import verify_evidence, freeze_files, SOURCE_SHA
from scripts.research.gt08_review import read_json, verify_packet
from scripts.research.gt09_owner_review import (
    COORDINATES,
    DEFAULT_PACKET,
    EXPECTED_PACKET,
    LABELS,
    VERSION,
    encoded,
    require,
    sha,
    validate_case,
)

OWNER_SHA = '0960de861dc8f74e84c05a0419287e28a01c2818e84fa4bc4af4ba5cc41bb68f'
ROOT = Path('/private/tmp')
OWNER_ROOT = ROOT / 'capomatic-v4-gt09-owner/gt09-output/owner-review-exports'
GT01 = ROOT / 'capomatic-v4-ground-truth-01/ground-truth-01-output'
GT06 = ROOT / 'capomatic-v4-gt06-extended'
GT07A = ROOT / 'capomatic-v4-gt07-text'
GT07B = ROOT / 'capomatic-v4-gt07-flags'
BUCKETS = (
    'UNMAPPED',
    'OWNER_TEXT_REGION',
    'OWNER_NON_TEXT_REGION',
    'OWNER_MIXED',
    'OWNER_UNKNOWN',
    'OWNER_CONFLICT',
)
LOOKUP = np.array([0, 1, 2, 5, 3, 5, 5, 5, 4, 5, 5, 5, 5, 5, 5, 5], dtype='uint8')
TEXT_KINDS = {'word', 'sentence', 'lyric-line', 'lyric-item', 'chord-name'}
EXPECTED = {'GT06': {'A': 1982, 'G': 2026}, 'GT07B': {'A': 24, 'G': 233}}
CONTEXT = (900, 460, 1330, 1051)


def find_export(root, expected):
    candidates = sorted(Path(root).glob('*.json'))
    matches = [p for p in candidates if sha(p.read_bytes()) == expected]
    require(
        len(matches) == 1,
        'Need exactly one export matching the user-bound SHA; never select newest',
    )
    return matches[0], {str(p): sha(p.read_bytes()) for p in candidates}


def validate_owner(path, packet=DEFAULT_PACKET):
    raw = Path(path).read_bytes()
    data = read_json(path)
    require(
        set(data)
        == {
            'version',
            'review_type',
            'evidence_status',
            'packet_sha256',
            'coordinate_system',
            'cases',
            'coverage',
            'composition_authorized',
            'protection_masks_modified',
        },
        'Unexpected export fields',
    )
    require(
        data['version'] == VERSION
        and data['review_type'] == 'OWNER_REVIEW'
        and data['evidence_status'] == 'NOT_INDEPENDENT_GROUND_TRUTH',
        'Wrong evidence status',
    )
    require(
        data['coordinate_system'] == COORDINATES
        and data['packet_sha256'] == sha((packet / 'packet.json').read_bytes()) == EXPECTED_PACKET,
        'Packet binding mismatch',
    )
    require(
        data['composition_authorized'] is False and data['protection_masks_modified'] is False,
        'No edit permission',
    )
    cases = verify_packet(packet)
    require(
        isinstance(data['cases'], list) and [r['case_id'] for r in data['cases']] == list(cases),
        'Missing/duplicate/reordered case',
    )
    coverage = {
        r['case_id']: validate_case(r, cases[r['case_id']], complete=True) for r in data['cases']
    }
    require(
        coverage == data['coverage'] and encoded(data) == raw,
        'Coverage or deterministic export mismatch',
    )
    return data, coverage


def map_owner(rows, mapping, size):
    """Bitset union retains all answers. A disagreement never becomes one chosen label."""
    width, height = size
    bits = np.zeros((height, width), dtype='uint8')
    require(len(mapping) == len(rows), 'Case mapping count mismatch')
    boxes = {r['case_id']: r['page_bbox'] for r in mapping}
    require(
        len(boxes) == len(rows) and set(boxes) == {r['case_id'] for r in rows},
        'Mapping identity mismatch',
    )
    for row in rows:
        x0, y0, x1, y1 = boxes[row['case_id']]
        require(all(type(v) is int for v in (x0, y0, x1, y1)), 'Integer mapping required')
        require(
            0 <= x0 < x1 <= width
            and 0 <= y0 < y1 <= height
            and (x1 - x0, y1 - y0) == (row['width'], row['height']),
            'Mapping dimension/alignment mismatch',
        )
        for y, left, right, label in row['runs']:
            bits[y0 + y, x0 + left : x0 + right] |= 1 << LABELS.index(label)
    return bits, LOOKUP[bits]


def protected_union(size, regions):
    mask = np.zeros((size[1], size[0]), dtype=bool)
    for region in regions:
        bounds = region['bbox']
        require(
            len(bounds) == 4 and all(math.isfinite(v) for v in bounds),
            'Invalid protection geometry',
        )
        x0, y0, x1, y1 = bounds
        require(x0 <= x1 and y0 <= y1, 'Reversed protection geometry')
        mask[
            max(0, math.floor(y0)) : min(size[1], math.ceil(y1)),
            max(0, math.floor(x0)) : min(size[0], math.ceil(x1)),
        ] = True
    return mask


def read_mask(path, size):
    with Image.open(path) as im:
        require(im.size == size and im.mode == 'L', 'No rescaling or mask-mode conversion allowed')
        return np.asarray(im).copy() > 0


def mask_rle(mask):
    return [list(r) for r in rle((int(x), int(y)) for y, x in np.argwhere(mask))]


def summarize(mask, owner, gray, text, music):
    require(all(a.shape == mask.shape for a in (owner, gray, text, music)), 'Coordinate mismatch')
    counts = {name: int(np.count_nonzero(mask & (owner == i))) for i, name in enumerate(BUCKETS)}
    require(sum(counts.values()) == int(mask.sum()), 'Missing/duplicated collision coordinates')
    dark = mask & (gray < 127)
    return {
        'unique_pixels': int(mask.sum()),
        'owner_categories': counts,
        'original_dark_support_gray_lt127': int(dark.sum()),
        'original_dark_within_owner_text_region': int(np.count_nonzero(dark & (owner == 1))),
        'owner_text_region_without_dark_support': int(
            np.count_nonzero(mask & (owner == 1) & ~(gray < 127))
        ),
        'omr_text_support_candidates': int(np.count_nonzero(mask & text)),
        'omr_music_support_candidates': int(np.count_nonzero(mask & music)),
        'omr_shared_text_music_support': int(np.count_nonzero(mask & text & music)),
        'coordinate_runs': mask_rle(mask),
    }


def subset_bounds(total, superset_counts):
    n = sum(superset_counts.values())
    require(0 <= total <= n, 'Historical contacts cannot exceed frozen superset')
    return {k: [max(0, total - (n - v)), min(total, v)] for k, v in superset_counts.items()}


def gt06_partial_result(target, expected, metric, summary, prior):
    """Exact aggregates may follow from homogeneous supersets; coordinates stay unknown."""
    require(
        prior['target'] == target and prior['all_protections_union_intersections'] == expected,
        'Prior GT06 cohort mismatch',
    )
    require(
        prior['original_dark_in_union'] == metric['protected_source_dark_contact_pixels'],
        'Prior grayscale mismatch',
    )
    regions = [r for r in prior['regions'] if r.get('id') == 'sheet#1:4134']
    require(len(regions) == 1, 'Missing/duplicate audited Direction identity')
    region = regions[0]
    require(
        region['broad_envelope_pixels'] == expected, 'Prior region does not cover full contact set'
    )
    bounds = subset_bounds(expected, summary['owner_categories'])
    return {
        'target': target,
        'status': 'PARTIAL_EXACT_MOVING_MASK_NOT_PERSISTED',
        'historical_moving_envelope_contacts': expected,
        'historical_original_dark_support': prior['original_dark_in_union'],
        'exact_owner_counts_from_reconstructed_contact_coordinates': None,
        'owner_category_bounds_for_historical_moving_subset': bounds,
        'logically_determined_owner_counts': {
            k: low if low == high else None for k, (low, high) in bounds.items()
        },
        'historical_direction_text_support_candidates': region['text_support_only_candidates']
        + region['shared_or_ambiguous'],
        'historical_omr_music_support_candidates': region['music_support_only_candidates']
        + region['shared_or_ambiguous'],
        'historical_support_provenance': 'Read-only hash-bound GT07A target_intersections; not recomputed from unavailable moving mask. Parent/child counts not added.',
        'frozen_combined_notation_superset': summary,
        'scope_warning': 'Combined alpha includes staff/bar scaffolding. Superset coordinates are not the historical moving-symbol contact set. No mask replay/subtraction/rendering performed.',
    }


def component_candidates(x, y, metric, spec):
    """Recorded bounds exclude impossible components; never claim bbox == ink ownership."""

    def inside(box):
        return box[0] <= x < box[2] and box[1] <= y < box[3]

    candidates = []
    event = metric['events'][0]
    if inside(event['rendered_bounds']):
        candidates.append('head')
    if inside(metric['flag']['rendered_bounds']):
        candidates.append('flag')
    tipx, tipy = metric['stem_tip']
    if tipx - 2 <= x <= tipx + 2 and tipy <= y < event['rendered_bounds'][3]:
        candidates.append('stem')
    # Full measure-wide row bands are conservative context only, not reconstructed ink.
    if y >= event['rendered_bounds'][1] - 2:
        if abs(x - event['requested_anchor'][0]) <= spec['staff']['interline']:
            candidates.append('ledger_possible_without_component_mask')
    return {
        'candidates_by_recorded_geometry': candidates,
        'exact_component': 'UNRESOLVED_COMPONENT_MASK_NOT_PERSISTED',
        'basis': 'Frozen union proves notation occupancy; per-component bounds are not exact component masks',
    }


def detail_rows(hit, bits, owner, gray, text_ids, music_ids, rows, mapping, metric, spec):
    boxes = {r['case_id']: r['page_bbox'] for r in mapping}
    results = []
    for y, x in np.argwhere(hit):
        x, y = int(x), int(y)
        observations = []
        for row in rows:
            x0, y0, x1, y1 = boxes[row['case_id']]
            if x0 <= x < x1 and y0 <= y < y1:
                local_x, local_y = x - x0, y - y0
                matches = [
                    label for yy, l, r, label in row['runs'] if yy == local_y and l <= local_x < r
                ]
                require(len(matches) == 1, 'Lost crop correspondence')
                observations.append(
                    {
                        'case_id': row['case_id'],
                        'crop_x': local_x,
                        'crop_y': local_y,
                        'label': matches[0],
                    }
                )
        results.append(
            {
                'x': x,
                'y': y,
                'owner_category': BUCKETS[int(owner[y, x])],
                'retained_labels': [
                    label for i, label in enumerate(LABELS) if int(bits[y, x]) & (1 << i)
                ],
                'case_observations': observations,
                'overlapping_case_disagreement': len({o['label'] for o in observations}) > 1,
                'original_gray': int(gray[y, x]),
                'original_dark_gray_lt127': bool(gray[y, x] < 127),
                'omr_text_support_membership': sorted(text_ids.get((x, y), [])),
                'omr_music_support_membership': sorted(music_ids.get((x, y), [])),
                'predicted_notation_component': component_candidates(x, y, metric, spec),
            }
        )
    return results


def audit(out):
    out = Path(out)
    require(not out.exists(), 'New output directory required; never overwrite audit evidence')
    require(
        not any(p.is_symlink() for p in [out, *out.absolute().parents]), 'Symlink output forbidden'
    )
    for historical in [GT01, GT06, GT07A, GT07B, OWNER_ROOT.parent, DEFAULT_PACKET.parent]:
        require(
            historical.resolve() not in [out.resolve(), *out.resolve().parents],
            'Output inside historical evidence forbidden',
        )
    owner_path, available_exports = find_export(OWNER_ROOT, OWNER_SHA)
    data, coverage = validate_owner(owner_path)
    binding, _ = verify_evidence(GT01, GT07A, GT07B, GT06)
    recorded_binding = read_json(
        Path(__file__).resolve().parents[2] / 'docs/V4_GT08_EVIDENCE_BINDING.json'
    )
    require(
        all(
            sha(Path(p).read_bytes()) == v
            for p, v in recorded_binding['historical_artifacts'].items()
        ),
        'Committed GT08 evidence binding changed',
    )
    original = GT01 / 'predictions/baseline-exec/source'
    source_path = original / 'source.png'
    graph_path = original / 'visual-graph.json'
    omr_path = original / 'recognized.omr'
    lineage = read_json(GT07A / 'gt07-text-output/text-provenance-report.json')
    require(
        sha(source_path.read_bytes()) == SOURCE_SHA
        and sha(graph_path.read_bytes()) == lineage['graph_sha256']
        and sha(omr_path.read_bytes()) == lineage['omr_sha256'],
        'Source/graph/OMR mismatch',
    )
    source = Image.open(source_path)
    source.load()
    size = source.size
    gray = np.asarray(source.convert('L'))
    mapping_path = GT07A / 'gt07-text-output/custodian-only.json'
    mapping = read_json(mapping_path)
    # Reprove page/crop pixel alignment, without rendering any prediction.
    for row in mapping:
        case = next(c for c in data['cases'] if c['case_id'] == row['case_id'])
        im = Image.open(DEFAULT_PACKET / (case['case_id'] + '.png'))
        cropped = source.crop(tuple(row['page_bbox']))
        require(
            im.mode == cropped.mode
            and im.tobytes() == cropped.tobytes()
            and im.size == cropped.size,
            'Crop/source pixel alignment mismatch',
        )
    bits, owner = map_owner(data['cases'], mapping, size)
    graph = read_json(graph_path)
    glyphs = glyphs_from_omr(omr_path)
    text = np.zeros(gray.shape, bool)
    music = np.zeros(gray.shape, bool)
    text_ids = {}
    music_ids = {}
    for ident, s in graph['symbols'].items():
        if s['kind'] not in TEXT_KINDS | MUSICAL:
            continue
        pixels = glyphs.get(s['page'] + ':' + str(dict(s['attributes']).get('glyph'))) or ()
        target, ids = (text, text_ids) if s['kind'] in TEXT_KINDS else (music, music_ids)
        for x, y in pixels:
            require(0 <= x < size[0] and 0 <= y < size[1], 'Support escapes page')
            target[y, x] = True
            ids.setdefault((x, y), []).append(ident)
    paths = dict(binding['files'])
    renderer_path = GT06 / 'scripts/research/gt06_extended.py'
    renderer_sha = sha(renderer_path.read_bytes())
    require(
        renderer_sha == read_json(GT06 / 'gt06-output/prototype-freeze.json')['code_sha256'],
        'Frozen combined-mask subset contract source mismatch',
    )
    paths[str(renderer_path)] = renderer_sha
    for p in [owner_path, graph_path, omr_path, mapping_path, *DEFAULT_PACKET.iterdir()]:
        paths[str(p)] = sha(p.read_bytes())
    outputs = {}
    visuals = []
    details = []
    for study, root, inputs in [
        ('GT06', GT06 / 'gt06-output', GT06 / 'gt06-inputs'),
        ('GT07B', GT07B / 'gt07-flag-output', GT07B / 'gt07-flag-inputs'),
    ]:
        freeze_files(root)
        spec = read_json(inputs / 'selection.json')
        metrics = read_json(root / 'rendering-metrics.json')
        protection = protected_union(size, spec['protected'])
        require(spec['protected'] == graph['text_protected_regions'], 'Protection changed')
        report = []
        for metric in metrics['metrics']:
            target = metric['target']
            expected = EXPECTED[study][target]
            require(
                metric['protected_envelope_contact_pixels'] == expected, 'Wrong historical cohort'
            )
            if study == 'GT06':
                combined = read_mask(root / (target + '-notation-alpha.png'), size)
                hit = combined & protection
                summary = summarize(hit, owner, gray, text, music)
                prior = next(r for r in lineage['target_intersections'] if r['target'] == target)
                row = gt06_partial_result(target, expected, metric, summary, prior)
                row['exact_moving_mask_not_persisted'] = str(
                    root / (target + '-music-only-alpha.png')
                )
            else:
                moving = read_mask(root / (target + '-music-only-alpha.png'), size)
                combined = read_mask(root / (target + '-notation-alpha.png'), size)
                require(not np.any(moving & ~combined), 'Music not contained in frozen notation')
                hit = moving & protection
                summary = summarize(hit, owner, gray, text, music)
                require(
                    summary['unique_pixels'] == expected
                    and summary['original_dark_support_gray_lt127']
                    == metric['protected_source_dark_contact_pixels'],
                    'Frozen exact contact mismatch',
                )
                row = {
                    'target': target,
                    'status': 'EXACT_FROZEN_MOVING_CONTACT_SET',
                    'contacts': summary,
                }
                if target == 'G':
                    all_text_hit = moving & text
                    require(
                        np.count_nonzero(all_text_hit) == 47 and np.all(protection[all_text_hit]),
                        '47-set identity mismatch',
                    )
                    require(
                        int(np.count_nonzero(all_text_hit & (gray < 127))) == 34,
                        'Frozen 47-set grayscale mismatch',
                    )
                    details = detail_rows(
                        all_text_hit,
                        bits,
                        owner,
                        gray,
                        text_ids,
                        music_ids,
                        data['cases'],
                        mapping,
                        metric,
                        spec,
                    )
                    require(
                        len(details) == len({(r['x'], r['y']) for r in details}) == 47,
                        'Lost/duplicated detail coordinates',
                    )
                    row['text_support_contact_47_owner_categories'] = summarize(
                        all_text_hit, owner, gray, text, music
                    )['owner_categories']
            report.append(row)
            visuals.append((study, target, combined, hit, study == 'GT07B'))
        outputs[study] = report
    combinations = Counter()
    for b, n in Counter(bits[owner == 5].tolist()).items():
        combinations['/'.join(label for i, label in enumerate(LABELS) if b & (1 << i))] += n
    owner_report = {
        'owner_sha256': OWNER_SHA,
        'selected_export': str(owner_path),
        'available_exports': available_exports,
        'review_type': 'OWNER_REVIEW',
        'evidence_status': 'NOT_INDEPENDENT_GROUND_TRUTH',
        'case_coverage': coverage,
        'unique_source_coordinates_mapped': int(np.count_nonzero(bits)),
        'conflicting_source_coordinates': int(np.count_nonzero(owner == 5)),
        'conflict_combinations': dict(combinations),
        'conflict_resolution': 'NONE',
        'independent_human_ground_truth': False,
    }
    report = {
        'decision': 'OWNER_COLLISION_AUDIT_PARTIALLY_RESOLVED',
        'owner': owner_report,
        'gray_measurement': 'Pillow L <127; historical descriptive support only, never text segmentation/ownership',
        'GT06': outputs['GT06'],
        'GT07B': outputs['GT07B'],
        'safety': {
            'A_collision_characterization': 'GT07B exact; GT06 combined-alpha superset/bounds only',
            'B_source_music_removal': 'NOT_AUTHORIZED',
            'C_lyric_preserving_composition': 'NOT_AUTHORIZED',
            'protection_masks_changed': False,
            'track_A_partial_promoted': False,
            'independent_text_ink': 'UNKNOWN',
        },
        'input_sha256': paths,
    }
    out.mkdir(parents=True)
    for name, value in [
        ('owner-rle-validation', owner_report),
        ('gt06-contact-analysis', outputs['GT06']),
        ('gt07b-contact-analysis', outputs['GT07B']),
        (
            'gt07b-g-47-contact-details',
            {
                'coordinates': details,
                'coordinate_system': 'original page integer pixel-index centers; x right, y down',
                'scope': 'coordinator-only owner review, not independent text ink',
            },
        ),
        ('collision-report', report),
    ]:
        (out / (name + '.json')).write_bytes(encoded(value))
    diagnostics(source, owner, visuals, details, out)
    require(
        all(sha(Path(p).read_bytes()) == value for p, value in paths.items()),
        'Historical input changed during audit',
    )
    require(owner_path.read_bytes() == encoded(data), 'Owner submission changed')
    summary = {
        'decision': report['decision'],
        'verified_input_files': len(paths),
        'source_and_old_freezes_unchanged': True,
        'owner_submission_unchanged': True,
        'historical_predictions_rerendered': False,
        'automatic_category_substitution': False,
        'protection_masks_changed': False,
        'source_music_removal_authorized': False,
        'composition_authorized': False,
        'independent_labels': 0,
        'outputs_sha256': {p.name: sha(p.read_bytes()) for p in sorted(out.iterdir())},
    }
    (out / 'validation-summary.json').write_bytes(encoded(summary))
    for p in out.iterdir():
        p.chmod(0o444)
    return report


def painted(source, box, layers):
    """Annotations on a copied diagnostic crop, never a source/score output."""
    image = np.asarray(source.convert('RGB').crop(box)).copy()
    x0, y0, x1, y1 = box
    for mask, color, alpha in layers:
        local = mask[y0:y1, x0:x1]
        image[local] = np.rint(image[local] * (1 - alpha) + np.array(color) * alpha).astype('uint8')
    return Image.fromarray(image)


def panel(image, title, subtitle):
    result = Image.new('RGB', (image.width, image.height + 72), 'white')
    d = ImageDraw.Draw(result)
    for i, text in enumerate(
        [
            'DEVELOPER-ONLY / OWNER REVIEW',
            'NOT INDEPENDENT GROUND TRUTH / NOT A SCORE',
            title,
            subtitle,
        ]
    ):
        d.text((7, 4 + i * 16), text, fill='black')
    result.paste(image, (0, 72))
    return result


def diagnostics(source, owner, visuals, details, out):
    palette = [
        (140, 140, 140),
        (240, 65, 65),
        (45, 135, 240),
        (150, 65, 200),
        (240, 180, 20),
        (255, 0, 200),
    ]
    owner_layers = [(owner == i, palette[i], 0.40) for i in range(6)]
    uncertain_layers = [(owner == i, palette[i], 0.65) for i in (0, 3, 4, 5)]
    rows = []
    for study, target, notation, hit, exact in visuals:
        scope = 'EXACT MUSIC CONTACTS' if exact else 'COMBINED MASK SUPERSET ONLY'
        group = f'{study} {target}: {scope}'
        images = [
            panel(source.crop(CONTEXT), 'A: ORIGINAL SOURCE', group),
            panel(painted(source, CONTEXT, owner_layers), 'B: OWNER REGIONS (not text ink)', group),
            panel(
                painted(source, CONTEXT, [(notation, (0, 165, 160), 0.85)]),
                'C: FROZEN NOTATION POSITIONS',
                'Includes frozen staff/bar; no regenerated ink',
            ),
            panel(
                painted(source, CONTEXT, [(hit, (230, 20, 20) if exact else (220, 155, 0), 0.90)]),
                'D: ' + scope,
                group,
            ),
            panel(
                painted(source, CONTEXT, uncertain_layers),
                'E: CONFLICT / UNKNOWN / UNMAPPED',
                'Magenta=conflict, yellow=unknown, gray=unmapped',
            ),
        ]
        row = Image.new(
            'RGB', (sum(i.width for i in images), max(i.height for i in images)), 'white'
        )
        x = 0
        for im in images:
            row.paste(im, (x, 0))
            x += im.width
        row.save(out / f'{study.lower()}-{target.lower()}-diagnostic.png')
        rows.append(row)
    sheet = Image.new('RGB', (max(i.width for i in rows), sum(i.height for i in rows)), 'white')
    y = 0
    for row in rows:
        sheet.paste(row, (0, y))
        y += row.height
    sheet.save(out / 'comparison-contact-sheet.png')
    xs = [r['x'] for r in details]
    ys = [r['y'] for r in details]
    box = (
        max(0, min(xs) - 6),
        max(0, min(ys) - 6),
        min(source.width, max(xs) + 7),
        min(source.height, max(ys) + 7),
    )
    zoom = 16
    base = source.crop(box).resize(
        ((box[2] - box[0]) * zoom, (box[3] - box[1]) * zoom), Image.Resampling.NEAREST
    )
    owner_view = painted(source, box, owner_layers).resize(base.size, Image.Resampling.NEAREST)
    marked = base.copy()
    d = ImageDraw.Draw(marked)
    for r in details:
        x, y = (r['x'] - box[0]) * zoom, (r['y'] - box[1]) * zoom
        d.rectangle((x, y, x + zoom - 1, y + zoom - 1), outline=(0, 190, 255), width=2)
        if r['overlapping_case_disagreement']:
            d.line((x, y, x + zoom - 1, y + zoom - 1), fill=(255, 0, 200), width=2)
    label = f'GT07B G: 47 unique coords / crop {box} / 16x nearest'
    panels = [
        panel(base, 'ORIGINAL SOURCE', label),
        panel(owner_view, 'OWNER LABELS (not text ink)', label),
        panel(marked, 'CYAN=47 CONTACTS; MAGENTA=CONFLICT', label),
    ]
    enlarged = Image.new('RGB', (sum(p.width for p in panels), panels[0].height), 'white')
    x = 0
    for im in panels:
        enlarged.paste(im, (x, 0))
        x += im.width
    enlarged.save(out / 'enlarged-contact-review.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.out)
    except FileNotFoundError as exc:
        parser.exit(2, f'OWNER_COLLISION_AUDIT_BLOCKED_MISSING_INPUT: {exc}\n')
    print(result['decision'])
