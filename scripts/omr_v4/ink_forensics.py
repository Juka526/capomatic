"""Measurement-only raster/glyph provenance audit. Never supplies OwnedInk."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import zipfile

import cv2
import numpy as np
from PIL import Image, ImageDraw

from backend.omr_v4.ink import KINDS, POLICY, _supporting, glyphs_from_omr
from backend.omr_v4.masks import raster_digest
from backend.omr_v4.visual_graph import load_visual_graph, safe_xml

THRESHOLDS = (64, 96, 127, 160, 192)
SHIFTS = tuple(itertools.product(range(-3, 4), repeat=2))


def agreement(gray, pixels, dx=0, dy=0, threshold=127):
    """Denominator always includes every proposed glyph pixel, including off-page."""
    dark = sum(
        0 <= x + dx < gray.shape[1]
        and 0 <= y + dy < gray.shape[0]
        and int(gray[y + dy, x + dx]) <= threshold
        for x, y in pixels
    )
    return {
        'dark': int(dark),
        'total': len(pixels),
        'percentage': 100 * dark / len(pixels) if pixels else None,
    }


def relation_groups(graph, candidates):
    adjacency = {i: set() for i in candidates}
    for r in graph.relations:
        if (
            r.kind in {'head-stem', 'beam-stem', 'flag-stem', 'augmentation', 'alter-head'}
            and r.source in adjacency
            and r.target in adjacency
        ):
            if r.id in _supporting(graph, graph.symbols[r.source]) or r.id in _supporting(
                graph, graph.symbols[r.target]
            ):
                adjacency[r.source].add(r.target)
                adjacency[r.target].add(r.source)
    groups = {}
    for ident in sorted(adjacency):
        if ident in groups:
            continue
        pending, group = [ident], set()
        while pending:
            item = pending.pop()
            if item in group:
                continue
            group.add(item)
            pending.extend(adjacency[item] - group)
        for item in group:
            groups[item] = frozenset(group)
    return groups


def region_mask(size, boxes):
    result = Image.new('L', size)
    draw = ImageDraw.Draw(result)
    for box in boxes:
        if box:
            draw.rectangle(tuple(map(math.floor, box)), fill=255)
    return np.asarray(result) != 0


def staff_masks(source, graph):
    masks = []
    for width in (1, 5):
        image = Image.new('L', source.size)
        for staff in graph.staves:
            for line in staff.lines:
                if len(line) >= 2:
                    ImageDraw.Draw(image).line(line, fill=255, width=width)
        masks.append(np.asarray(image) != 0)
    return masks


def sharing(candidates, groups, labels):
    owners = defaultdict(set)
    glyph_users = defaultdict(list)
    for ident, (glyph_id, pixels) in candidates.items():
        if glyph_id:
            glyph_users[glyph_id].append(ident)
        for point in pixels:
            owners[point].add(ident)
    overlaps = Counter()
    for ids in owners.values():
        for a, b in itertools.combinations(sorted(ids), 2):
            overlaps[a, b] += 1
    component_users = defaultdict(set)
    for ident, (_, pixels) in candidates.items():
        for x, y in pixels:
            if 0 <= y < labels.shape[0] and 0 <= x < labels.shape[1] and labels[y, x]:
                component_users[int(labels[y, x])].add(ident)
    touching_pairs = set()
    for ids in component_users.values():
        for pair in itertools.combinations(sorted(ids), 2):
            if pair not in overlaps:
                touching_pairs.add(pair)
    direct_touch = set()
    for (x, y), ids in owners.items():
        for dx, dy in ((0, 1), (1, -1), (1, 0), (1, 1)):
            for a in ids:
                for b in owners.get((x + dx, y + dy), ()):
                    if a != b:
                        pair = tuple(sorted((a, b)))
                        if pair not in overlaps:
                            direct_touch.add(pair)
    pairs = [
        {
            'a': a,
            'b': b,
            'shared_pixels': count,
            'same_glyph': candidates[a][0] == candidates[b][0],
            'sig_connected': b in groups[a],
        }
        for (a, b), count in sorted(overlaps.items())
    ]
    return owners, {
        'scope': f'{len(candidates)} first-pass symbol candidates; pairs unordered; categories may overlap',
        'same_glyph_ids_with_multiple_symbols': sum(len(ids) > 1 for ids in glyph_users.values()),
        'same_glyph_symbol_pairs': sum(
            len(ids) * (len(ids) - 1) // 2 for ids in glyph_users.values()
        ),
        'different_glyph_overlapping_pairs': sum(not p['same_glyph'] for p in pairs),
        'sig_connected_overlapping_pairs': sum(p['sig_connected'] for p in pairs),
        'unrelated_overlapping_pairs': sum(not p['sig_connected'] for p in pairs),
        'overlapping_candidate_symbols': len({p[k] for p in pairs for k in ('a', 'b')}),
        'distinct_multi_owner_pixels': sum(len(ids) > 1 for ids in owners.values()),
        'same_source_component_without_pixel_overlap_pairs': len(touching_pairs),
        'direct_8_neighbor_contact_without_overlap_pairs': len(direct_touch),
        'direct_contact_sig_connected_pairs': sum(b in groups[a] for a, b in direct_touch),
        'direct_contact_unrelated_pairs': sum(b not in groups[a] for a, b in direct_touch),
        'touching_pair_caveat': 'Same threshold-127 source component is transitive connectivity, not necessarily direct symbol contact; staff lines can join distant symbols.',
        'pairs': pairs,
    }


def image_info(image, encoded=None):
    result = {
        'dimensions': list(image.size),
        'mode': image.mode,
        'native_raster_digest': raster_digest(image),
    }
    if encoded is not None:
        result['file_sha256'] = hashlib.sha256(encoded).hexdigest()
    return result


def supplementary_metrics(artifacts: Path, summary: dict, reproduced: Path):
    """Exact staff assignments and raster reproduction; no isolation admission."""
    source_bytes = (artifacts / 'source.png').read_bytes()
    with Image.open(io.BytesIO(source_bytes)) as im:
        source = im.copy()
    repeated_bytes = reproduced.read_bytes()
    with Image.open(io.BytesIO(repeated_bytes)) as im:
        repeated = im.copy()
    graph = load_visual_graph(artifacts / 'recognized.omr')
    glyphs = glyphs_from_omr(artifacts / 'recognized.omr')
    gray = np.asarray(source.convert('L'))
    with zipfile.ZipFile(artifacts / 'recognized.omr') as archive:
        with Image.open(io.BytesIO(archive.read('sheet#1/BINARY.png'))) as im:
            binary = np.asarray(im.convert('L')).copy()
    _, corridor = staff_masks(source, graph)
    staff_points, staff_refs = set(), []
    for staff in graph.staves:
        root = safe_xml(staff.source_xml.encode())
        for line in root.findall('lines/line'):
            ref = line.get('glyph')
            if ref:
                key = staff.page + ':' + ref
                staff_refs.append(key)
                staff_points.update(glyphs.get(key) or ())
    staff_mask = np.zeros(gray.shape, bool)
    for x, y in staff_points:
        if 0 <= x < source.width and 0 <= y < source.height:
            staff_mask[y, x] = True
    rows, all_counts = {}, Counter()
    totals = Counter()
    component_count, component_labels = cv2.connectedComponents(
        (gray <= 127).astype('uint8'), connectivity=8
    )
    component_sizes = np.bincount(component_labels.ravel(), minlength=component_count)
    candidates = {}
    for ident, symbol in sorted(graph.symbols.items()):
        if symbol.kind in KINDS:
            gid = symbol.page + ':' + dict(symbol.attributes).get('glyph', '')
            candidates[ident] = (gid, set(glyphs.get(gid) or ()))
    groups = relation_groups(graph, candidates)
    group_coverage = {}
    escape_counts = Counter()
    for ident, symbol in sorted(graph.symbols.items()):
        if symbol.kind not in KINDS:
            continue
        gid = symbol.page + ':' + dict(symbol.attributes).get('glyph', '')
        points = set(glyphs.get(gid) or ())
        ys = np.array([y for x, y in sorted(points)], dtype=int)
        xs = np.array([x for x, y in sorted(points)], dtype=int)
        group = groups[ident]
        if group not in group_coverage:
            union = set().union(*(candidates[i][1] for i in group))
            group_coverage[group] = Counter(int(component_labels[y, x]) for x, y in union)
        ids = {int(component_labels[y, x]) for x, y in points if component_labels[y, x]}
        component_escape = any(group_coverage[group][i] != int(component_sizes[i]) for i in ids)
        box = symbol.geometry.region
        geometry_escape = box is not None and any(
            not (box[0] <= x <= box[2] and box[1] <= y <= box[3]) for x, y in points
        )
        escape_counts['component_coverage_failure_symbols'] += component_escape
        escape_counts['glyph_outside_inter_region_symbols'] += geometry_escape
        escape_counts['both_failure_symbols'] += component_escape and geometry_escape
        escape_counts['union_failure_symbols'] += component_escape or geometry_escape
        dark = gray[ys, xs] <= 127
        cor = corridor[ys, xs]
        st = staff_mask[ys, xs]
        rows[ident] = {
            'glyph_pixels': len(points),
            'glyph_outside_inter_region': geometry_escape,
            'source_component_coverage_failure': component_escape,
            'binary_dark_pixels': int((binary[ys, xs] == 0).sum()),
            'staff_glyph_overlap_pixels': int(st.sum()),
            'staff_overlap_outside_corridor_pixels': int((st & ~cor).sum()),
            'corridor_not_staff_glyph_pixels': int((cor & ~st).sum()),
            'phase19_corridor_source_dark_pixels': int((cor & dark).sum()),
            'phase19_alarm_pixels_also_staff_glyph': int((cor & dark & st).sum()),
            'phase19_alarm_pixels_not_staff_glyph': int((cor & dark & ~st).sum()),
        }
        totals['glyph_pixel_references'] += len(points)
        totals['embedded_binary_dark_references'] += rows[ident]['binary_dark_pixels']
        totals['binary_exact_symbols'] += bool(points) and rows[ident]['binary_dark_pixels'] == len(
            points
        )
        if (cor & dark).any():
            all_counts['phase19_staff_alarm_symbols'] += 1
            all_counts['alarm_with_staff_glyph_overlap'] += bool((cor & dark & st).any())
            all_counts['alarm_without_staff_glyph_overlap'] += not bool((cor & dark & st).any())
        for key in (
            'phase19_alarm_pixels_also_staff_glyph',
            'phase19_alarm_pixels_not_staff_glyph',
        ):
            all_counts[key] += rows[ident][key]
    sample_staff = {}
    for sample in summary['samples']:
        sample_staff[sample['symbol_id']] = rows[sample['symbol_id']]
    return {
        'raster_reproduction': {
            'file_identical': source_bytes == repeated_bytes,
            'native_pixels_identical': source.mode == repeated.mode
            and source.size == repeated.size
            and source.tobytes() == repeated.tobytes(),
            'reproduced': image_info(repeated, repeated_bytes),
            'historical_input_digest_available': False,
            'caveat': 'Reproduction and copy2 code establish reproducibility/strong provenance, not an independent historical pre-Audiveris digest.',
        },
        'all_candidate_binary_agreement': dict(totals),
        'component_escape_counts': dict(escape_counts),
        'staff_assignment': {
            'staff_glyph_references': staff_refs,
            'unique_staff_glyph_pixels': len(staff_points),
            'alarm_counts': dict(all_counts),
            'sample_details': sample_staff,
            'caveat': 'Staff-glyph membership is Audiveris attribution, not independently proven original-pixel ownership. Missing membership does not prove a pixel is not staff. Counts of pixel references include repeated claims.',
        },
    }


def sample_panels(source, xs, ys, ident, gid):
    """Display exact-size source crops with padding so labels never overlap."""
    gray = np.asarray(source.convert('L'))
    left, top = max(0, int(xs.min()) - 16), max(0, int(ys.min()) - 16)
    right, bottom = min(source.width, int(xs.max()) + 17), min(source.height, int(ys.max()) + 17)
    box = (left, top, right, bottom)
    glyph = np.zeros((bottom - top, right - left), bool)
    glyph[ys - top, xs - left] = True
    dark = gray[top:bottom, left:right] <= 127
    width, height = right - left, bottom - top
    panel_width = max(width + 12, 180)
    canvas = Image.new('RGB', (3 * panel_width, 2 * (height + 30) + 40), 'white')
    d = ImageDraw.Draw(canvas)
    d.text((2, 2), f'{ident} / glyph {gid} / MEASUREMENT ONLY', fill='black')
    panels = [('A source', source.crop(box).convert('RGB'))]
    for label, mask in [
        ('B glyph', glyph),
        ('C source <=127', dark),
        ('D intersection', glyph & dark),
        ('E glyph only', glyph & ~dark),
        ('F source only', dark & ~glyph),
    ]:
        panels.append(
            (label, Image.fromarray(np.where(mask, 0, 255).astype('uint8')).convert('RGB'))
        )
    for i, (label, panel) in enumerate(panels):
        x, y = (i % 3) * panel_width, 25 + (i // 3) * (height + 30)
        d.text((x, y), label, fill='black')
        canvas.paste(panel, (x, y + 18))
    return canvas


def forensic(artifacts: Path, out: Path, manifest: Path):
    # A previously saved geometry-only manifest is mandatory: no sample reselection.
    selected_bytes = manifest.read_bytes()
    selected = json.loads(selected_bytes)
    if (out / 'ink-forensics-summary.json').exists():
        raise ValueError('Forensic result already exists; do not overwrite measurements')
    source_bytes = (artifacts / 'source.png').read_bytes()
    with Image.open(io.BytesIO(source_bytes)) as image:
        source = image.copy()
    gray = np.asarray(source.convert('L'))
    graph = load_visual_graph(artifacts / 'recognized.omr')
    glyphs = glyphs_from_omr(artifacts / 'recognized.omr')
    candidates = {}
    for ident, s in sorted(graph.symbols.items()):
        if s.kind in KINDS:
            ref = dict(s.attributes).get('glyph')
            gid = ident.split(':')[0] + ':' + ref if ref else None
            candidates[ident] = (gid, set(glyphs.get(gid) or ()))
    groups = relation_groups(graph, candidates)
    _, labels = cv2.connectedComponents((gray <= 127).astype('uint8'), connectivity=8)
    owners, shared = sharing(candidates, groups, labels)
    core, corridor = staff_masks(source, graph)
    text = region_mask(source.size, [r.bbox for r in graph.text_protected_regions])
    ledgers = region_mask(
        source.size, [s.geometry.region for s in graph.symbols.values() if s.kind == 'ledger']
    )
    with zipfile.ZipFile(artifacts / 'recognized.omr') as archive:
        binary_bytes = archive.read('sheet#1/BINARY.png')
        with Image.open(io.BytesIO(binary_bytes)) as image:
            binary_image = image.copy()
        book = safe_xml(archive.read('book.xml'))
    if binary_image.size != source.size:
        raise ValueError('Embedded binary coordinate mismatch')
    binary = np.asarray(binary_image.convert('L'))
    samples = []
    out.mkdir(parents=True, exist_ok=True)
    for ordinal, entry in enumerate(selected['samples'], 1):
        ident = entry['symbol_id']
        gid, points = candidates[ident]
        if not points or any(
            not (0 <= x < source.width and 0 <= y < source.height) for x, y in points
        ):
            raise ValueError('Sample glyph missing or off-page')
        xs = np.array([p[0] for p in sorted(points)])
        ys = np.array([p[1] for p in sorted(points)])
        intensities = gray[ys, xs]
        shifts = [{'dx': dx, 'dy': dy, **agreement(gray, points, dx, dy)} for dx, dy in SHIFTS]
        maximum = max(s['dark'] for s in shifts)
        component_ids = sorted({int(labels[y, x]) for x, y in points if labels[y, x]})
        component = np.isin(labels, component_ids)
        group_points = set().union(*(candidates[i][1] for i in groups[ident]))
        group_mask = np.zeros(gray.shape, bool)
        for x, y in group_points:
            if 0 <= x < source.width and 0 <= y < source.height:
                group_mask[y, x] = True
        escape = component & ~group_mask
        related_head = region_mask(
            source.size,
            [
                s.geometry.region
                for s in graph.symbols.values()
                if s.id in groups[ident] and s.kind == 'head'
            ],
        )
        related_stem = region_mask(
            source.size,
            [
                s.geometry.region
                for s in graph.symbols.values()
                if s.id in groups[ident] and s.kind == 'stem'
            ],
        )
        related_beam = region_mask(
            source.size,
            [
                s.geometry.region
                for s in graph.symbols.values()
                if s.id in groups[ident] and s.kind in {'beam', 'beam-hook'}
            ],
        )
        unrelated = region_mask(
            source.size,
            [
                s.geometry.region
                for s in graph.symbols.values()
                if s.id not in groups[ident] and s.kind in KINDS
            ],
        )
        categories = {
            'staff_centerline_dark_support': core,
            'staff_corridor_dark_support': corridor,
            'attached_head_bounds': related_head,
            'attached_stem_bounds': related_stem,
            'connected_beam_bounds': related_beam,
            'ledger_bounds': ledgers,
            'unrelated_notation_bounds': unrelated,
            'text_bounds': text,
            'gray_edge_1_to_127': (gray > 0) & (gray <= 127),
        }
        mapped = np.zeros(gray.shape, bool)
        for mask in categories.values():
            mapped |= mask
        sample = {
            **entry,
            'decoded_glyph_id': gid,
            'glyph_pixel_count': len(points),
            'glyph_bounds_inclusive': [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            'source_agreement_127': agreement(gray, points),
            'embedded_binary_agreement': agreement(binary, points),
            'source_intensity': {
                'min': int(intensities.min()),
                'max': int(intensities.max()),
                'mean': float(intensities.mean()),
                'percentiles_0_25_50_75_100': np.percentile(
                    intensities, [0, 25, 50, 75, 100]
                ).tolist(),
                'histogram': {
                    str(k): int(v) for k, v in sorted(Counter(map(int, intensities)).items())
                },
            },
            'staff_corridor_pixels': int(corridor[ys, xs].sum()),
            'staff_centerline_pixels': int(core[ys, xs].sum()),
            'staff_near_but_not_centerline_pixels': int((corridor[ys, xs] & ~core[ys, xs]).sum()),
            'corridor_pixels_white_in_embedded_binary': int(
                (corridor[ys, xs] & (binary[ys, xs] != 0)).sum()
            ),
            'shared_related_pixels': sum(
                bool((owners[p] - {ident}) & groups[ident]) for p in points
            ),
            'shared_unrelated_pixels': sum(
                bool((owners[p] - {ident}) - groups[ident]) for p in points
            ),
            'component_ids': component_ids,
            'sig_group': sorted(groups[ident]),
            'component_escape': {
                'outside_sig_group_glyph_union': int(escape.sum()),
                'category_evidence_counts': {
                    name: int((escape & mask).sum()) for name, mask in categories.items()
                },
                'other_unclassified': int((escape & ~mapped).sum()),
                'caveat': 'Categories overlap; geometric/gray evidence does not establish actual pixel ownership.',
            },
            'translations': shifts,
            'best_translations': [
                {'dx': s['dx'], 'dy': s['dy'], 'dark': s['dark']}
                for s in shifts
                if s['dark'] == maximum
            ],
            'threshold_curve': {str(t): agreement(gray, points, threshold=t) for t in THRESHOLDS},
        }
        samples.append(sample)
        sample_panels(source, xs, ys, ident, gid).save(out / f'sample-{ordinal:02d}.png')
    common = set.intersection(
        *({(s['dx'], s['dy']) for s in sample['best_translations']} for sample in samples)
    )
    global_curve = {
        str(t): {
            'dark': sum(agreement(gray, p, threshold=t)['dark'] for _, p in candidates.values()),
            'total': sum(len(p) for _, p in candidates.values()),
        }
        for t in THRESHOLDS
    }
    for stats in global_curve.values():
        stats['percentage'] = 100 * stats['dark'] / stats['total'] if stats['total'] else None
    summary = {
        'diagnostic_only': True,
        'starting_sha': 'b3df2a478eba2ed1b690e166e74f3b5716088c44',
        'manifest_sha256': hashlib.sha256(selected_bytes).hexdigest(),
        'selection': selected,
        'source': image_info(source, source_bytes),
        'embedded_binary': image_info(binary_image, binary_bytes),
        'omr_sha256': hashlib.sha256((artifacts / 'recognized.omr').read_bytes()).hexdigest(),
        'book_metadata': dict(book.attrib),
        'recorded_input_path': book.findtext('sheet/input/path'),
        'source_rgb_channels_equal': (
            bool(
                np.array_equal(np.asarray(source)[..., 0], np.asarray(source)[..., 1])
                and np.array_equal(np.asarray(source)[..., 1], np.asarray(source)[..., 2])
            )
            if source.mode == 'RGB'
            else None
        ),
        'source_threshold_127_vs_embedded_binary_disagreement_pixels': int(
            ((gray <= 127) != (binary == 0)).sum()
        ),
        'policy_unchanged': POLICY,
        'translation_common_maximizers': sorted(common),
        'global_threshold_curve_counting_shared_pixels_per_symbol': global_curve,
        'sharing': shared,
        'samples': samples,
    }
    (out / 'ink-forensics-summary.json').write_text(
        json.dumps(summary, sort_keys=True, indent=2, allow_nan=False) + '\n'
    )
    if (
        artifacts / 'source.png'
    ).read_bytes() != source_bytes or manifest.read_bytes() != selected_bytes:
        raise ValueError('Source or preregistered manifest changed')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument(
        '--supplement-existing',
        action='store_true',
        help='Only add exact staff assignments and comparison with --reproduced-raster to an existing measurement JSON',
    )
    parser.add_argument('--reproduced-raster', type=Path)
    args = parser.parse_args()
    if args.supplement_existing:
        if args.reproduced_raster is None:
            parser.error('--supplement-existing requires --reproduced-raster')
        summary_path = args.out / 'ink-forensics-summary.json'
        existing = json.loads(summary_path.read_text())
        extra = supplementary_metrics(args.artifacts, existing, args.reproduced_raster)
        existing['supplementary_measurements'] = extra
        (args.out / 'ink-forensics-supplement.json').write_text(
            json.dumps(extra, sort_keys=True, indent=2) + '\n'
        )
        summary_path.write_text(json.dumps(existing, sort_keys=True, indent=2) + '\n')
        print(json.dumps(extra, sort_keys=True, indent=2))
        raise SystemExit(0)
    result = forensic(args.artifacts, args.out, args.manifest)
    print(
        json.dumps(
            {
                'source': result['source'],
                'translation_common_maximizers': result['translation_common_maximizers'],
                'global_threshold_curve': result[
                    'global_threshold_curve_counting_shared_pixels_per_symbol'
                ],
                'sharing_counts': {k: v for k, v in result['sharing'].items() if k != 'pairs'},
                'samples': [
                    {
                        k: s[k]
                        for k in (
                            'symbol_id',
                            'source_agreement_127',
                            'embedded_binary_agreement',
                            'best_translations',
                            'staff_corridor_pixels',
                            'component_escape',
                        )
                    }
                    for s in result['samples']
                ],
            },
            indent=2,
        )
    )
