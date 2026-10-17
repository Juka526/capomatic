"""Conservative glyph-backed raster ownership, offline diagnostics only.

No geometry crop is promoted to ink. Glyph run tables are explicit Audiveris
pixel assignments; actual source components must corroborate their completeness.
Staff-crossing topology is deliberately not certified by this first producer.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import zipfile

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .masks import OwnedInk, raster_digest
from .visual_graph import safe_xml

KINDS = frozenset(
    {'head', 'stem', 'beam', 'beam-hook', 'flag', 'augmentation-dot', 'alter', 'accidental'}
)
RELATIONS = {
    'head': {'head-stem', 'contains'},
    'stem': {'head-stem'},
    'beam': {'beam-stem'},
    'beam-hook': {'beam-stem'},
    'flag': {'flag-stem'},
    'augmentation-dot': {'augmentation'},
    'alter': {'alter-head'},
    'accidental': {'alter-head'},
}
POLICY = {
    'threshold': 127,
    'threshold_method': 'Pillow L <= 127',
    'connectivity': 8,
    'dilation_radius': 0,
    'staff_corridor_radius': 2,
    'staff_corridor_is_exclusion_not_staff_ownership': True,
    'method': 'AUDIVERIS_GLYPH_RLE_EXACT_COMPONENT_CORROBORATION',
}


def rle(pixels):
    """Canonical horizontal runs; never fills holes or inter-component gaps."""
    rows = {}
    for x, y in pixels:
        rows.setdefault(y, set()).add(x)
    out = []
    for y, xs in sorted(rows.items()):
        start = previous = None
        for x in sorted(xs):
            if previous is not None and x != previous + 1:
                out.append((y, start, previous + 1))
                start = None
            if start is None:
                start = x
            previous = x
        if start is not None:
            out.append((y, start, previous + 1))
    return tuple(out)


def pixels_from_runs(runs):
    return {(x, y) for y, left, right in runs for x in range(left, right)}


def glyphs_from_omr(path: Path):
    """Bounded, entity-free OMR decoding; invalid glyphs are absent, never repaired."""
    result = {}
    decoded_pixels = 0
    with zipfile.ZipFile(path) as archive:
        if sum(i.file_size for i in archive.infolist()) > 128 * 1024 * 1024:
            raise ValueError('OMR exceeds ink decoder size limit')
        for name in sorted(archive.namelist()):
            if not name.endswith('.xml') or not name.startswith('sheet#'):
                continue
            sheet = name.split('/')[0]
            root = safe_xml(archive.read(name))
            seen = set()
            for glyph in root.findall('./glyph-index/glyph'):
                key = sheet + ':' + str(glyph.get('id'))
                if key in seen:
                    result[key] = None
                    continue
                seen.add(key)
                try:
                    left, top = int(glyph.attrib['left']), int(glyph.attrib['top'])
                    table = glyph.find('run-table')
                    width, height = int(table.attrib['width']), int(table.attrib['height'])
                    orientation = table.attrib['orientation']
                    if orientation not in {'VERTICAL', 'HORIZONTAL'} or not (
                        0 < width <= 10000 and 0 < height <= 10000 and width * height <= 2_000_000
                    ):
                        raise ValueError('Invalid run table bounds')
                    rows = table.findall('runs')
                    if len(rows) != (width if orientation == 'VERTICAL' else height):
                        raise ValueError('Truncated run table')
                    pixels = set()
                    for index, row in enumerate(rows):
                        lengths = [int(v) for v in (row.text or '').split()]
                        pos = 0
                        for i, length in enumerate(lengths):
                            if length < 0 or (length == 0 and i != 0):
                                raise ValueError('Invalid run')
                            end = pos + length
                            if end > (height if orientation == 'VERTICAL' else width):
                                raise ValueError('Run escapes glyph')
                            if i % 2 == 0:
                                for value in range(pos, end):
                                    pixels.add(
                                        (left + index, top + value)
                                        if orientation == 'VERTICAL'
                                        else (left + value, top + index)
                                    )
                            pos = end
                    decoded_pixels += len(pixels)
                    if decoded_pixels > 16_000_000:
                        raise RuntimeError('Decoded glyph pixel budget exceeded')
                    result[key] = frozenset(pixels) if pixels else None
                except (KeyError, TypeError, AttributeError, ValueError):
                    result[key] = None
    return result


@dataclass(frozen=True)
class InkRecord:
    symbol_id: str
    kind: str
    status: str
    reasons: tuple[str, ...]
    glyph_id: str | None
    runs: tuple[tuple[int, int, int], ...]
    component_ids: tuple[int, ...]
    relation_ids: tuple[str, ...]
    staff_overlap_runs: tuple[tuple[int, int, int], ...]
    restore_required: bool


@dataclass(frozen=True)
class InkEvidence:
    source_digest: str
    records: tuple[InkRecord, ...]

    def owned(self, source):
        if raster_digest(source) != self.source_digest:
            raise ValueError('Source digest mismatch')
        return tuple(
            OwnedInk(r.symbol_id, self.source_digest, r.runs, POLICY['method'])
            for r in self.records
            if r.status == 'VERIFIED'
        )

    def to_json(self):
        return (
            json.dumps(
                {**asdict(self), 'policy': POLICY, 'diagnostic_only': True},
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            + '\n'
        )


def _box_mask(size, boxes):
    mask = Image.new('L', size)
    draw = ImageDraw.Draw(mask)
    for box in boxes:
        if box is not None and all(math.isfinite(v) for v in box):
            draw.rectangle(tuple(map(math.floor, box)), fill=255)
    return np.asarray(mask) != 0


def _supporting(graph, symbol):
    expected = {
        'head-stem': {'head', 'stem'},
        'contains': {'head', 'head-chord'},
        'beam-stem': {'beam', 'beam-hook', 'stem'},
        'flag-stem': {'flag', 'stem'},
        'alter-head': {'alter', 'accidental', 'head'},
        'augmentation': {'augmentation-dot', 'head', 'head-chord'},
    }
    return tuple(
        sorted(
            r.id
            for r in graph.relations
            if symbol.id in (r.source, r.target)
            and r.kind in RELATIONS[symbol.kind]
            and r.source in graph.symbols
            and r.target in graph.symbols
            and graph.symbols[r.source].kind != graph.symbols[r.target].kind
            and {graph.symbols[r.source].kind, graph.symbols[r.target].kind} <= expected[r.kind]
        )
    )


def isolate_ink(source, graph, glyphs):
    """Certify only exact glyph/component agreement, fail closed on every contact."""
    digest = raster_digest(source)
    if len(graph.pages) != 1 or (graph.pages[0].width, graph.pages[0].height) != source.size:
        raise ValueError('Single-page original-coordinate raster required')
    ink = np.asarray(source.convert('L')) <= POLICY['threshold']
    count, labels = cv2.connectedComponents(ink.astype('uint8'), connectivity=8)
    component_sizes = np.bincount(labels.ravel(), minlength=count)
    protected = _box_mask(source.size, (r.bbox for r in graph.text_protected_regions))
    structural = _box_mask(
        source.size,
        (
            s.geometry.region
            for s in graph.symbols.values()
            if s.kind in {'barline', 'staff-barline'}
        ),
    )
    missing_protection = any(r.bbox is None for r in graph.text_protected_regions)
    staff_image = Image.new('L', source.size)
    draw = ImageDraw.Draw(staff_image)
    for staff in graph.staves:
        for line in staff.lines:
            if len(line) >= 2:
                draw.line(line, fill=255, width=2 * POLICY['staff_corridor_radius'] + 1)
    staff_exclusion = np.asarray(staff_image) != 0
    candidates = {}
    owners = {}
    for ident, symbol in sorted(graph.symbols.items()):
        if symbol.kind not in KINDS:
            continue
        glyph_ref = dict(symbol.attributes).get('glyph')
        key = ident.split(':')[0] + ':' + glyph_ref if glyph_ref else None
        pixels = set(glyphs.get(key) or ())
        candidates[ident] = (symbol, key, pixels)
        for pixel in pixels:
            owners.setdefault(pixel, set()).add(ident)
    # Reconcile connected musical components by explicit SIG edges, never proximity.
    adjacency = {i: set() for i in candidates}
    for relation in graph.relations:
        if relation.kind in {'head-stem', 'beam-stem', 'flag-stem', 'augmentation', 'alter-head'}:
            if (
                relation.source in adjacency
                and relation.target in adjacency
                and (
                    relation.id in _supporting(graph, graph.symbols[relation.source])
                    or relation.id in _supporting(graph, graph.symbols[relation.target])
                )
            ):
                adjacency[relation.source].add(relation.target)
                adjacency[relation.target].add(relation.source)
    group_of = {}
    for ident in adjacency:
        if ident in group_of:
            continue
        pending, group = [ident], set()
        while pending:
            item = pending.pop()
            if item in group:
                continue
            group.add(item)
            pending.extend(adjacency[item] - group)
        for item in group:
            group_of[item] = frozenset(group)
    records = []
    for ident, (symbol, key, pixels) in candidates.items():
        reasons = set()
        relations = _supporting(graph, symbol)
        if not relations:
            reasons.add('RELATION_MISSING')
        box = symbol.geometry.region
        if not pixels or box is None or not symbol.geometry.valid:
            reasons.add('INCOMPLETE_GEOMETRY')
        valid = {(x, y) for x, y in pixels if 0 <= x < source.width and 0 <= y < source.height}
        if valid != pixels or (
            box and any(not (box[0] <= x <= box[2] and box[1] <= y <= box[3]) for x, y in pixels)
        ):
            reasons.add('COMPONENT_ESCAPES_WINDOW')
        if any(not ink[y, x] for x, y in valid):
            reasons.add('OTHER')  # Glyph/source disagreement, no threshold relaxation.
        if missing_protection or any(protected[y, x] for x, y in valid):
            reasons.add('TEXT_COLLISION')
        if any(structural[y, x] for x, y in valid):
            reasons.add('STRUCTURAL_COLLISION')
        overlap = {(x, y) for x, y in valid if staff_exclusion[y, x] and ink[y, x]}
        if overlap:
            reasons.add('STAFF_OWNERSHIP_UNCLEAR')
        if any(len(owners[p]) != 1 for p in pixels):
            reasons.add('MULTI_OWNER_COMPONENT')
        # Other symbols' windows are exclusion evidence only, never ownership.
        for other in graph.symbols.values():
            if (
                other.id == ident
                or other.kind in {'head-chord', 'beam-group'}
                or other.id in group_of[ident]
            ):
                continue
            b = other.geometry.region
            if b and any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for x, y in valid):
                reasons.add(
                    'UNSUPPORTED_ATTACHMENT'
                    if other.kind in {'articulation', 'fermata'}
                    else 'AMBIGUOUS_COMPONENT'
                )
        ids = tuple(sorted({int(labels[y, x]) for x, y in valid if ink[y, x]}))
        group_pixels = set().union(*(candidates[i][2] for i in group_of[ident]))
        for component in ids:
            # Every source component pixel must have exactly one explicit owner
            # within this SIG group. Shared contact pixels reject both owners.
            covered = sum(
                1
                for x, y in group_pixels
                if 0 <= x < source.width and 0 <= y < source.height and labels[y, x] == component
            )
            if covered != int(component_sizes[component]):
                reasons.add('COMPONENT_ESCAPES_WINDOW')
        if len(ids) != 1:
            reasons.add('AMBIGUOUS_COMPONENT')
        records.append(
            InkRecord(
                ident,
                symbol.kind,
                'REJECTED' if reasons else 'VERIFIED',
                tuple(sorted(reasons)),
                key,
                rle(valid) if not reasons else (),
                ids,
                relations,
                rle(overlap),
                bool(overlap),
            )
        )
    return InkEvidence(digest, tuple(records))


def coverage(evidence):
    result = {}
    for kind in sorted(KINDS):
        records = [r for r in evidence.records if r.kind == kind]
        result[kind] = {
            'candidate': len(records),
            'VERIFIED': sum(r.status == 'VERIFIED' for r in records),
            'rejected': sum(r.status != 'VERIFIED' for r in records),
        }
    return {
        'by_kind': result,
        'rejection_reasons': dict(
            sorted(Counter(reason for r in evidence.records for reason in r.reasons).items())
        ),
        'verified_symbols': sum(r.status == 'VERIFIED' for r in evidence.records),
        'verified_staff_crossing_symbols': sum(
            r.status == 'VERIFIED' and r.restore_required for r in evidence.records
        ),
    }
