"""Preregistered offline continuation audit. Does not modify handoff or ownership."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.omr_v4.ink import glyphs_from_omr, pixels_from_runs
from backend.omr_v4.source_ink import _bounds, _neighbors, _staff_context
from backend.omr_v4.visual_graph import load_visual_graph

PROTOCOL_SHA = '6bd86b215a3ecb71835323ed719b9c5a1114b5b7a2151d577a22417a80a4bbdb'


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')


def verify_inputs(binding):
    root = Path(binding['input_root'])
    hashes = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in binding['files']
    }
    if hashes != binding['files']:
        raise ValueError('Input hash mismatch')
    return hashes


def translate(points, dx, dy):
    return {(x + dx, y + dy) for x, y in points}


def stencil(support, core, fringe, size):
    w, h = size
    shell = _neighbors(support, 2, w, h)
    return ((support | shell) - core - fringe, _neighbors(support, 4, w, h) - support - shell)


def guard(gray, support, unknown, outer, excluded, attachments=()):
    """Exact existing rectangular-ring/background and finite guard predicate."""
    h, w = gray.shape
    x0, y0, x1, y1 = _bounds(support)
    ring = [
        int(gray[y, x])
        for y in range(max(0, y0 - 5), min(h, y1 + 6))
        for x in range(max(0, x0 - 5), min(w, x1 + 6))
        if 3 <= max(x0 - x, x - x1, y0 - y, y - y1) <= 5
    ]
    background = float(np.median(ring))
    visible = {p for p in unknown if gray[p[1], p[0]] < background}
    eligible = outer - set(attachments)
    remote = {
        p
        for p in eligible
        if gray[p[1], p[0]] < background
        and not excluded[p[1], p[0]]
        and any((p[0] + dx, p[1] + dy) in visible for dx in (-1, 0, 1) for dy in (-1, 0, 1))
    }
    return background, remote, len(eligible)


def measure(points, gray, binary, by_kind, background):
    hist = Counter(int(gray[y, x]) for x, y in points)

    def contrast(p):
        bg = background[p] if isinstance(background, dict) else background
        return bg - int(gray[p[1], p[0]])

    categories = Counter()
    support = {kind: len(points & ps) for kind, ps in by_kind.items() if points & ps}
    all_glyph = set().union(*by_kind.values())
    for x, y in points:
        if (x, y) in all_glyph:
            key = 'PERSISTED_SYMBOL_SUPPORT'
        elif binary[y, x] == 0:
            key = 'UNSUPPORTED_BINARY_INK_CANDIDATE'
        elif 0 < contrast((x, y)) < 8:
            key = 'LOW_CONTRAST_BACKGROUND_CANDIDATE'
        else:
            key = 'SOURCE_ONLY_UNRESOLVED'
        categories[key] += 1
    return {
        'pixels': len(points),
        'source_gray_histogram': dict(sorted(hist.items())),
        'contrast_histogram': dict(sorted(Counter(contrast(p) for p in points).items())),
        'binary_ink': sum(binary[y, x] == 0 for x, y in points).item() if points else 0,
        'persisted_symbol_support': support,
        'categories': dict(sorted(categories.items())),
    }


def control_origins(excluded, bbox, stride=16):
    """All eligible origins, selected without looking at source or BINARY."""
    x0, y0, x1, y1 = bbox
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    h, w = excluded.shape
    integral = cv2.integral(excluded.astype(np.uint8), sdepth=cv2.CV_32S)
    result = []
    for y in range(8, h - bh - 4, stride):
        for x in range(8, w - bw - 4, stride):
            left, top, right, bottom = x - 5, y - 5, x + bw + 5, y + bh + 5
            hits = (
                integral[bottom, right]
                - integral[top, right]
                - integral[bottom, left]
                + integral[top, left]
            )
            if hits == 0:
                result.append((x, y))
    return result


def choose_controls(origins, bbox):
    x0, y0, _, _ = bbox
    nearest = sorted(origins, key=lambda p: ((p[0] - x0) ** 2 + (p[1] - y0) ** 2, p[1], p[0]))[:3]
    page = [p for p in origins if p not in nearest][:3]
    return [('nearest_unaffected', p) for p in nearest] + [
        ('page_blank_candidate', p) for p in page
    ]


def cc_measure(remote, support, staff, labels):
    support_ids = {int(labels[y, x]) for x, y in support} - {0}
    staff_ids = {int(labels[y, x]) for x, y in staff} - {0}
    counts = Counter()
    ids = set()
    for x, y in remote:
        ident = int(labels[y, x])
        if ident:
            ids.add(ident)
            counts['surviving_remote'] += 1
            counts['connected_to_group_support'] += ident in support_ids
            counts['connected_to_staff'] += ident in staff_ids
            counts['connected_to_both'] += ident in support_ids and ident in staff_ids
    return {
        'distinct_components': len(ids),
        **{
            k: int(counts[k])
            for k in (
                'surviving_remote',
                'connected_to_group_support',
                'connected_to_staff',
                'connected_to_both',
            )
        },
    }


def run(root, output, protocol):
    if hashlib.sha256(protocol.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('Preregistered protocol changed')
    graph = load_visual_graph(root / 'recognized.omr')
    gray = np.asarray(Image.open(root / 'source.png').convert('L'))
    binary = np.asarray(Image.open(root / 'v3-evidence/binary.png').convert('L'))
    h, w = gray.shape
    handoff = json.loads((root / 'refinement-handoff/handoff.json').read_text())
    ink = json.loads((root / 'source-ink-1.9c/ink-evidence.json').read_text())
    prior = json.loads((root / 'v3-evidence/blocker-attribution.json').read_text())
    prior_by_id = {g['group_id']: g for g in prior['groups']}
    glyphs = glyphs_from_omr(root / 'recognized.omr')
    staff = set().union(
        *(
            pixels_from_runs(r['attributed_runs'])
            for r in json.loads((root / 'v3-evidence/staff-evidence.json').read_text())
        )
    )
    staff_context, _ = _staff_context(graph, (w, h))
    excluded_staff = staff_context.copy()
    for x, y in staff:
        excluded_staff[y, x] = True
    by_kind = {}
    for symbol in graph.symbols.values():
        glyph = dict(symbol.attributes).get('glyph')
        if glyph:
            by_kind.setdefault(symbol.kind, set()).update(
                glyphs.get(symbol.page + ':' + glyph) or ()
            )
    processed = {p['symbol_id']: pixels_from_runs(p['runs']) for p in ink['processed']}
    exclusion = excluded_staff.copy()
    for points in processed.values():
        for x, y in points:
            exclusion[y, x] = True
    for symbol in graph.symbols.values():
        region = symbol.geometry.region
        if region:
            x0, y0, x1, y1 = region
            exclusion[
                max(0, int(np.floor(y0)) - 6) : min(h, int(np.ceil(y1)) + 7),
                max(0, int(np.floor(x0)) - 6) : min(w, int(np.ceil(x1)) + 7),
            ] = True
    rows, controls = [], []
    all_remote = set()
    remote_backgrounds = {}
    # Background-specific component maps are shared; staff-removal topology is diagnostic only.
    component_cache = {}
    for group in handoff['groups']:
        if group['ownership_evidence_status'] != 'VERIFIED_PARTIAL':
            continue
        support = set().union(*(processed[i] for i in group['members']))
        core, fringe = (pixels_from_runs(group[k]) for k in ('known_core', 'known_fringe'))
        unknown, outer = stencil(support, core, fringe, (w, h))
        attachment_region = set().union(
            *(pixels_from_runs(a['analysis_runs']) for a in group['attachments'])
        )
        related = set().union(
            *(
                set(
                    glyphs.get(
                        graph.symbols[a['symbol_id']].page
                        + ':'
                        + dict(graph.symbols[a['symbol_id']].attributes).get('glyph', '')
                    )
                    or ()
                )
                for a in group['attachments']
                if a['disposition'] == 'ATTACHMENT_IDENTIFIED_NEEDS_REFINEMENT'
            )
        )
        excluded = excluded_staff.copy()
        for x, y in related:
            excluded[y, x] = True
        background, remote, denominator = guard(
            gray, support, unknown, outer, excluded, attachment_region
        )
        assert background == group['local_background']
        assert remote == pixels_from_runs(group['remote_continuation']), group['group_id']
        if background not in component_cache:
            mask = (gray < background).astype(np.uint8)
            _, labels = cv2.connectedComponents(mask, connectivity=8)
            mask[excluded_staff] = 0
            _, cut_labels = cv2.connectedComponents(mask, connectivity=8)
            component_cache[background] = labels, cut_labels
        labels, cut_labels = component_cache[background]
        origins = control_origins(exclusion, _bounds(support))
        row = {
            'group_id': group['group_id'],
            'background': background,
            'guard_positions': denominator,
            **measure(remote, gray, binary, by_kind, background),
            'source_components': cc_measure(remote, support, staff, labels),
            'source_components_staff_removed': cc_measure(remote, support, staff, cut_labels),
            'prior_attribution': prior_by_id[group['group_id']],
            'control_population': len(origins),
        }
        rows.append(row)
        all_remote.update(remote)
        for p in remote:
            remote_backgrounds.setdefault(p, set()).add(background)
        x0, y0, _, _ = _bounds(support)
        for stratum, (x, y) in choose_controls(origins, _bounds(support)):
            dx, dy = x - x0, y - y0
            shifted_support, shifted_unknown, shifted_outer = (
                translate(ps, dx, dy) for ps in (support, unknown, outer)
            )
            shifted_excluded = excluded_staff.copy()
            for px, py in translate(related, dx, dy):
                if 0 <= px < w and 0 <= py < h:
                    shifted_excluded[py, px] = True
            bg, points, denom = guard(
                gray,
                shifted_support,
                shifted_unknown,
                shifted_outer,
                shifted_excluded,
                translate(attachment_region, dx, dy),
            )
            controls.append(
                {
                    'group_id': group['group_id'],
                    'stratum': stratum,
                    'origin': [x, y],
                    'support_bbox': list(_bounds(shifted_support)),
                    'background': bg,
                    'guard_positions': denom,
                    'stencil_binary_ink': int(
                        sum(
                            binary[py, px] == 0
                            for px, py in shifted_support | shifted_unknown | shifted_outer
                        )
                    ),
                    'stencil_gray_below_background': int(
                        sum(
                            gray[py, px] < bg
                            for px, py in shifted_support | shifted_unknown | shifted_outer
                        )
                    ),
                    'stencil_symbol_support': {
                        kind: len((shifted_support | shifted_unknown | shifted_outer) & ps)
                        for kind, ps in by_kind.items()
                        if (shifted_support | shifted_unknown | shifted_outer) & ps
                    },
                    **measure(points, gray, binary, by_kind, bg),
                }
            )
    # Keep overlapping groups' different background estimates explicit.
    backgrounds = sorted({r['background'] for r in rows})
    minimum_background = {p: min(values) for p, values in remote_backgrounds.items()}
    excluded_groups = []
    all_status_remote = set(all_remote)
    for group in handoff['groups']:
        if group['ownership_evidence_status'] == 'VERIFIED_PARTIAL':
            continue
        points = pixels_from_runs(group['remote_continuation'])
        all_status_remote.update(points)
        excluded_groups.append(
            {
                'group_id': group['group_id'],
                'status': group['ownership_evidence_status'],
                'background': group['local_background'],
                'excluded_from_partial_analysis': True,
                **measure(points, gray, binary, by_kind, group['local_background']),
            }
        )
    control_summary = {}
    for stratum in sorted({c['stratum'] for c in controls}):
        selected = [c for c in controls if c['stratum'] == stratum]
        control_summary[stratum] = {
            'template_placements': len(selected),
            'unique_origins': len({tuple(c['origin']) for c in selected}),
            'unique_support_bbox_windows': len({tuple(c['support_bbox']) for c in selected}),
            'triggered': sum(c['pixels'] > 0 for c in selected),
            'guard_positions_references': sum(c['guard_positions'] for c in selected),
            'remote_pixel_references': sum(c['pixels'] for c in selected),
            'binary_ink_references': sum(c['binary_ink'] for c in selected),
            'stencil_binary_ink_references': sum(c['stencil_binary_ink'] for c in selected),
            'stencils_with_binary_ink': sum(c['stencil_binary_ink'] > 0 for c in selected),
            'stencil_symbol_support_references': sum(
                sum(c['stencil_symbol_support'].values()) for c in selected
            ),
            'categories': dict(sum((Counter(c['categories']) for c in selected), Counter())),
            'source_gray_histogram': dict(
                sum((Counter(c['source_gray_histogram']) for c in selected), Counter())
            ),
            'independence': 'placements reuse origins and overlap; not independent observations or ground-truth blank labels',
        }
    result = {
        'protocol_sha256': PROTOCOL_SHA,
        'diagnostic_only': True,
        'edit_authorized': False,
        'decision': 'NEEDS_MORE_CONTINUATION_EVIDENCE',
        'backgrounds': backgrounds,
        'groups': rows,
        'controls': controls,
        'control_summary': control_summary,
        'excluded_groups': excluded_groups,
        'all_status_remote_pixels': len(all_status_remote),
        'all_status_gray254': sum(int(gray[y, x]) == 254 for x, y in all_status_remote),
        'distinct_remote': measure(all_remote, gray, binary, by_kind, minimum_background),
        'distinct_contrast_basis': 'minimum observed group background at each point',
        'remote_pixels_with_multiple_backgrounds': sum(
            len(v) > 1 for v in remote_backgrounds.values()
        ),
        'prior_distinct_explained': prior['distinct_explained_remote_pixels'],
        'component_map_count': len(component_cache),
        'source_size': [w, h],
    }
    write_json(output / 'audit.json', result)
    return result


def validate_output(output, root):
    allowed = Path(__file__).resolve().parents[1] / 'dual-track-a-output'
    if output == root or root in output.parents:
        raise ValueError('Output must not be inside evidence root')
    if output != allowed and allowed not in output.parents:
        raise ValueError('Output must be inside this worktree dual-track-a-output')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bindings', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    binding = json.loads(args.bindings.read_text())
    root = Path(binding['input_root']).resolve()
    output = args.output.resolve()
    validate_output(output, root)
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    before = verify_inputs(binding)
    result = run(
        root,
        output,
        Path(__file__).resolve().parents[1] / 'docs/V4_CONTINUATION_GUARD_PROTOCOL.json',
    )
    after = verify_inputs(binding)
    protocol = Path(__file__).resolve().parents[1] / 'docs/V4_CONTINUATION_GUARD_PROTOCOL.json'
    assert hashlib.sha256(protocol.read_bytes()).hexdigest() == PROTOCOL_SHA
    assert before == after
    write_json(output / 'input-verification-after.json', after)
    write_json(
        output / 'instrumentation.json',
        {
            'wall_seconds': time.perf_counter() - started,
            'peak_rss_native_units': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'rss_units': 'bytes on macOS; KiB on Linux',
            'python': sys.version,
            'platform': sys.platform,
            'estimated_metrics': [],
        },
    )
    print(
        json.dumps(
            {
                'groups': len(result['groups']),
                'controls': len(result['controls']),
                'distinct_remote': result['distinct_remote']['pixels'],
                'decision': result['decision'],
            }
        )
    )


if __name__ == '__main__':
    main()
