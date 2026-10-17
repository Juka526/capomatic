"""Layered processed support and original-raster ownership. No score editing.

Phase 1.9's decoder is reused; its fixed-threshold/component admission is not.
A partial source core is evidence only, never an edit authorization.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
from PIL import Image, ImageDraw

from .ink import KINDS, _supporting, glyphs_from_omr, pixels_from_runs, rle
from .masks import OwnedInk, raster_digest
from .visual_graph import safe_xml

PINNED_BUILD = '7a36078e7ba0c006052c1f661b949cf9b729f505'

COMPLETE = 'VERIFIED_COMPLETE'
PARTIAL = 'VERIFIED_PARTIAL'
REJECTED = 'REJECTED'
POLICY = {
    'version': '1.9c',
    'fringe_radius': 1,
    'inspection_radius': 2,
    'background_annulus_bbox_radii': [3, 5],
    'background_min': 224,
    'fringe_background_contrast': 8,
    'core_background_contrast': 8,
    'recursive_growth': False,
    'logical_staff_half_width': 'serialized thickness/2 + 0.5 pixel',
    'fallback_staff_thickness': 'unknown: blocks completeness',
    'source_dark_threshold': None,
}


@dataclass(frozen=True)
class ProcessedInkSupport:
    symbol_id: str
    glyph_id: str | None
    kind: str
    construction_basis: str
    coordinate_system: str
    binary_digest: str
    omr_digest: str
    runs: tuple[tuple[int, int, int], ...]
    inter_geometry: tuple | None
    support_geometry: tuple | None
    relation_ids: tuple[str, ...]
    valid: bool
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class SourceInkOwnership:
    symbol_id: str
    atomic_group_id: str
    kind: str
    source_digest: str
    source_core: tuple[tuple[int, int, int], ...]
    fringe: tuple[tuple[int, int, int], ...]
    staff_attributed: tuple[tuple[int, int, int], ...]
    unknown_crossing: tuple[tuple[int, int, int], ...]
    staff_pixel_classes: tuple[tuple[str, tuple], ...]
    source_value_histogram: tuple[tuple[tuple[int, ...], int], ...]
    local_crossing_clear: bool
    status: str
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class AtomicInkGroup:
    id: str
    members: tuple[str, ...]
    source_union: tuple[tuple[int, int, int], ...]
    core_union: tuple[tuple[int, int, int], ...]
    fringe_union: tuple[tuple[int, int, int], ...]
    shared_intra_group: tuple[tuple[int, int, int], ...]
    unknown_crossing: tuple[tuple[int, int, int], ...]
    unrelated_collision_count: int
    status: str
    blockers: tuple[str, ...]
    phase18_compatible: bool
    edit_eligible: bool


@dataclass(frozen=True)
class SourceInkEvidence:
    source_digest: str
    processed: tuple[ProcessedInkSupport, ...]
    ownership: tuple[SourceInkOwnership, ...]
    groups: tuple[AtomicInkGroup, ...]

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

    def owned(self, source):
        """Phase 1.8 compatibility projections of complete atomic unions only.

        Shared coordinates in symbol views refer to one group authority, not
        separate disjoint ownership claims. No clipping to Inter bounds occurs.
        """
        if raster_digest(source) != self.source_digest:
            raise ValueError('Source digest mismatch')
        records = {r.symbol_id: r for r in self.ownership}
        return tuple(
            OwnedInk(
                i,
                self.source_digest,
                rle(pixels_from_runs(records[i].source_core) | pixels_from_runs(records[i].fringe)),
                'COMPLETE_ATOMIC_UNION_PROJECTION:' + g.id,
            )
            for g in self.groups
            if g.status == COMPLETE and g.phase18_compatible
            for i in g.members
        )


def _bounds(points):
    return (
        (
            min(x for x, y in points),
            min(y for x, y in points),
            max(x for x, y in points),
            max(y for x, y in points),
        )
        if points
        else None
    )


def _neighbors(points, radius, width, height):
    return {
        (x + dx, y + dy)
        for x, y in points
        for dx in range(-radius, radius + 1)
        for dy in range(-radius, radius + 1)
        if 0 <= x + dx < width and 0 <= y + dy < height
    } - points


def _protection(graph, size):
    mask = Image.new('L', size)
    structural = Image.new('L', size)
    unresolved = graph.invalid_geometry_count > 0
    for region in graph.text_protected_regions:
        if region.bbox is None:
            unresolved = True
        else:
            ImageDraw.Draw(mask).rectangle(region.bbox, fill=255)
    for symbol in graph.symbols.values():
        if symbol.kind in {'barline', 'staff-barline'}:
            if symbol.geometry.region is None:
                unresolved = True
            else:
                ImageDraw.Draw(structural).rectangle(symbol.geometry.region, fill=255)
    return np.asarray(mask) != 0, np.asarray(structural) != 0, unresolved


def read_processed_bundle(path: Path, graph):
    """Load actual saved BINARY, glyph groups and staff assignments, bounded by parser."""
    if len(graph.pages) != 1:
        raise ValueError('Single-page processed bundle required')
    glyphs = glyphs_from_omr(path)
    metadata, staff_points = {}, set()
    with zipfile.ZipFile(path) as archive:
        book = safe_xml(archive.read('book.xml'))
        if book.get('software-build') != PINNED_BUILD:
            raise ValueError('Unverified Audiveris construction revision')
        # The graph parser and glyph decoder already enforce bounded archive/XML.
        for page in graph.pages:
            root = safe_xml(archive.read(f'{page.id}/{page.id}.xml'))
            for glyph in root.findall('glyph-index/glyph'):
                metadata[page.id + ':' + str(glyph.get('id'))] = tuple(sorted(glyph.attrib.items()))
        payload = archive.read(f'{graph.pages[0].id}/BINARY.png')
        with Image.open(io.BytesIO(payload)) as image:
            if image.size != (graph.pages[0].width, graph.pages[0].height):
                raise ValueError('BINARY dimensions differ from graph')
            binary = image.convert('L')
    for staff in graph.staves:
        root = safe_xml(staff.source_xml.encode())
        for line in root.findall('lines/line'):
            if line.get('glyph'):
                staff_points.update(glyphs.get(staff.page + ':' + line.get('glyph')) or ())
    return (
        glyphs,
        metadata,
        binary,
        frozenset(staff_points),
        hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def _atomic_groups(graph, ids):
    """Only supported typed musical edges; containment resolves chord endpoints."""
    members = {i: {i} for i in ids}
    for symbol in graph.symbols.values():
        if symbol.kind == 'head-chord':
            members[symbol.id] = {
                r.target
                for r in graph.relations
                if r.kind == 'contains'
                and r.source == symbol.id
                and r.target in ids
                and graph.symbols[r.target].kind == 'head'
            }
    adjacency = {i: set() for i in ids}
    for relation in graph.relations:
        if relation.kind not in {
            'head-stem',
            'beam-stem',
            'flag-stem',
            'augmentation',
            'alter-head',
        }:
            continue
        source, target = graph.symbols.get(relation.source), graph.symbols.get(relation.target)
        if source is None or target is None:
            continue
        supported = any(
            s.kind in KINDS and relation.id in _supporting(graph, s) for s in (source, target)
        )
        if not supported:
            continue
        for a in members.get(source.id, ()):
            for b in members.get(target.id, ()):
                adjacency[a].add(b)
                adjacency[b].add(a)
    groups, lookup = [], {}
    for ident in sorted(ids):
        if ident in lookup:
            continue
        pending, group = [ident], set()
        while pending:
            i = pending.pop()
            if i not in group:
                group.add(i)
                pending.extend(adjacency[i] - group)
        group = tuple(sorted(group))
        gid = 'ink:' + group[0]
        groups.append((gid, group))
        lookup.update({i: gid for i in group})
    return groups, lookup, members


def _staff_context(graph, size):
    """Exact distance to original polyline segments: uncertainty, not ownership."""
    mask = np.zeros((size[1], size[0]), bool)
    unresolved = False
    for staff in graph.staves:
        root = safe_xml(staff.source_xml.encode()) if staff.source_xml else None
        raw_lines = root.findall('lines/line') if root is not None else []
        for index, line in enumerate(staff.lines):
            raw = raw_lines[index] if index < len(raw_lines) else None
            try:
                thickness = float(raw.get('thickness'))
                if not np.isfinite(thickness) or not 0 < thickness <= staff.interline:
                    raise ValueError('invalid staff thickness')
            except (AttributeError, TypeError, ValueError):
                unresolved = True
                thickness = staff.interline
            radius = thickness / 2 + 0.5
            if len(line) < 2:
                unresolved = True
            for a, b in zip(line, line[1:]):
                if not all(np.isfinite(v) for v in (*a, *b)):
                    unresolved = True
                    continue
                x0 = max(0, int(np.floor(min(a[0], b[0]) - radius)))
                x1 = min(size[0], int(np.ceil(max(a[0], b[0]) + radius)) + 1)
                y0 = max(0, int(np.floor(min(a[1], b[1]) - radius)))
                y1 = min(size[1], int(np.ceil(max(a[1], b[1]) + radius)) + 1)
                if x0 >= x1 or y0 >= y1:
                    continue
                yy, xx = np.mgrid[y0:y1, x0:x1]
                dx, dy = b[0] - a[0], b[1] - a[1]
                norm = dx * dx + dy * dy
                t = np.clip(((xx - a[0]) * dx + (yy - a[1]) * dy) / norm, 0, 1) if norm else 0
                mask[y0:y1, x0:x1] |= (xx - a[0] - t * dx) ** 2 + (
                    yy - a[1] - t * dy
                ) ** 2 <= radius * radius
    return mask, unresolved


def isolate_source_ink(
    source, graph, glyphs, metadata, binary, staff_points=frozenset(), omr_digest='synthetic'
):
    digest = raster_digest(source)
    if (
        len(graph.pages) != 1
        or source.size != (graph.pages[0].width, graph.pages[0].height)
        or source.size != binary.size
    ):
        raise ValueError('Exact single-page dimensions required')
    binary_array = np.asarray(binary)
    if binary.mode != 'L' or not np.all((binary_array == 0) | (binary_array == 255)):
        raise ValueError('Explicit binary L provenance required')
    binary_digest = raster_digest(binary)
    staff_points = set(staff_points)
    gray = np.asarray(source.convert('L'))
    native = np.asarray(source)
    protection, structural, unresolved_protection = _protection(graph, source.size)
    crossing, unresolved_staff = _staff_context(graph, source.size)
    ids = {s.id for s in graph.symbols.values() if s.kind in KINDS}
    atomic, group_of, endpoints = _atomic_groups(graph, ids)
    supports, points, fatal = {}, {}, defaultdict(set)
    for ident in sorted(ids):
        symbol = graph.symbols[ident]
        ref = dict(symbol.attributes).get('glyph')
        gid = symbol.page + ':' + ref if ref else None
        raw = set(glyphs.get(gid) or ())
        valid = {
            (x, y)
            for x, y in raw
            if type(x) is int
            and type(y) is int
            and 0 <= x < source.width
            and 0 <= y < source.height
        }
        basis = {
            'head': 'BINARY_TEMPLATE_SELECTED',
            'stem': 'SEED_FILAMENT_OR_COMPOUND',
            'beam': 'NO_STAFF_DERIVED',
            'beam-hook': 'NO_STAFF_DERIVED',
        }.get(symbol.kind)
        if basis is None:
            if 'SYMBOL' in dict(metadata.get(gid, ())).get('groups', '').split():
                basis = 'SYMBOL_STAGE_ATTRIBUTED_OR_REUSED'
            else:
                basis = 'UNKNOWN_PROCESSED_PROVENANCE'
        blockers = set()
        if not raw:
            blockers.add('MISSING_GLYPH_SUPPORT')
        if valid != raw:
            blockers.add('PAGE_BOUND_ESCAPE')
        if any(binary_array[y, x] != 0 for x, y in valid):
            blockers.add('BINARY_SUPPORT_DISAGREEMENT')
        if basis == 'UNKNOWN_PROCESSED_PROVENANCE':
            blockers.add(basis)
        relations = _supporting(graph, symbol)
        if not relations:
            blockers.add('RELATION_MISSING')
        if any(
            any(
                graph.symbols.get(endpoint) is not None
                and graph.symbols[endpoint].kind == 'head-chord'
                and not endpoints.get(endpoint)
                for endpoint in (r.source, r.target)
            )
            for r in graph.relations
            if r.id in relations
        ):
            blockers.add('UNRESOLVED_RELATION_ENDPOINT')
        if unresolved_protection:
            blockers.add('UNBOUNDED_PROTECTION')
        supports[ident] = ProcessedInkSupport(
            ident,
            gid,
            symbol.kind,
            basis,
            'ORIGINAL_AUDIVERIS_PAGE_PIXELS',
            binary_digest,
            omr_digest,
            rle(valid),
            symbol.geometry.region,
            _bounds(valid),
            relations,
            not blockers,
            tuple(sorted(blockers)),
        )
        points[ident] = valid
        fatal[group_of[ident]].update(blockers)
    group_points = {gid: set().union(*(points[i] for i in members)) for gid, members in atomic}
    processed_owners = defaultdict(set)
    for gid, union in group_points.items():
        for pixel in union:
            processed_owners[pixel].add(gid)
    foreign_support = set()
    for symbol in graph.symbols.values():
        if symbol.kind not in KINDS and symbol.kind not in {'head-chord', 'beam-group'}:
            ref = dict(symbol.attributes).get('glyph')
            if ref:
                foreign_support.update(glyphs.get(symbol.page + ':' + ref) or ())
    local = {}
    backgrounds = {}
    group_fringe = {}
    partial = defaultdict(set)
    for gid, members in atomic:
        union = group_points[gid]
        if not union:
            group_fringe[gid] = set()
            continue
        for x, y in union:
            if protection[y, x]:
                fatal[gid].add('TEXT_COLLISION')
            if structural[y, x]:
                fatal[gid].add('STRUCTURAL_COLLISION')
            if len(processed_owners[x, y]) > 1:
                fatal[gid].add('UNRELATED_GROUP_COLLISION')
        if source.mode == 'RGBA' and any(native[y, x, 3] != 255 for x, y in union):
            fatal[gid].add('TRANSPARENT_SOURCE_AMBIGUITY')
        if unresolved_staff:
            partial[gid].add('UNBOUNDED_STAFF_GEOMETRY')
        if union & foreign_support:
            partial[gid].add('UNSUPPORTED_SUPPORT_OVERLAP')
        box = _bounds(union)
        x0, y0, x1, y1 = box
        ring = [
            int(gray[y, x])
            for y in range(max(0, y0 - 5), min(source.height, y1 + 6))
            for x in range(max(0, x0 - 5), min(source.width, x1 + 6))
            if 3 <= max(x0 - x, x - x1, y0 - y, y - y1) <= 5
        ]
        background = float(np.median(ring)) if ring else None
        backgrounds[gid] = background
        if background is None or any(background - float(gray[y, x]) < 8 for x, y in union):
            partial[gid].add('CORE_CONTRAST_UNCERTAIN')
        fringe = set()
        # One nonrecursive expansion. No pixels beyond this radius are claimed.
        for pixel in _neighbors(union, 1, source.width, source.height):
            x, y = pixel
            visible = (
                background is not None and background >= 224 and background - float(gray[y, x]) >= 8
            )
            if not visible:
                if background is not None and 0 < background - float(gray[y, x]) < 8:
                    partial[gid].add('UNCERTAIN_ANTIALIAS_BOUNDARY')
                continue
            if processed_owners.get(pixel, set()) - {gid}:
                fatal[gid].add('UNRELATED_GROUP_COLLISION')
                continue
            if protection[y, x]:
                fatal[gid].add('TEXT_COLLISION')
                continue
            if structural[y, x]:
                fatal[gid].add('STRUCTURAL_COLLISION')
                continue
            if pixel in foreign_support:
                partial[gid].add('UNSUPPORTED_SUPPORT_OVERLAP')
                continue
            if crossing[y, x] or pixel in staff_points:
                partial[gid].add('UNKNOWN_CROSSING')
                continue
            fringe.add(pixel)
        # Missing local fringe/background evidence never turns into completeness.
        if background is None or background < 224:
            partial[gid].add('LOCAL_BACKGROUND_UNCERTAIN')
        if any(gray[y, x] == 255 for x, y in union):
            partial[gid].add('NO_VISIBLE_SOURCE_CONTRAST')
        owned = union | fringe
        boundary = (
            _neighbors(owned, 1, source.width, source.height)
            - _neighbors(union, 1, source.width, source.height)
            - union
        )
        if background is not None and any(
            background - float(gray[y, x]) > 0 and not crossing[y, x] and (x, y) not in staff_points
            for x, y in boundary
        ):
            partial[gid].add('UNACCOUNTED_LOCAL_CONTINUATION')
        if any(crossing[y, x] or (x, y) in staff_points for x, y in union):
            partial[gid].add('UNKNOWN_CROSSING')
        # A chord's structural stem reference is not an ownership edge. If
        # supported head-stem evidence did not establish this member, stop.
        for chord, heads in endpoints.items():
            if (
                chord in graph.symbols
                and graph.symbols[chord].kind == 'head-chord'
                and set(heads) & set(members)
            ):
                if any(
                    r.kind == 'chord-stem'
                    and chord in (r.source, r.target)
                    and (r.target if r.source == chord else r.source) not in members
                    for r in graph.relations
                ):
                    partial[gid].add('INCOMPLETE_REQUIRED_GROUP')
        # Moving attachments beyond this producer's classes cannot be complete.
        attached = {i for i, heads in endpoints.items() if set(heads) & set(members)} | set(members)
        for r in graph.relations:
            if r.source in attached or r.target in attached:
                other = r.target if r.source in attached else r.source
                if other in graph.symbols and graph.symbols[other].kind in {
                    'slur',
                    'ledger',
                    'articulation',
                    'fermata',
                }:
                    partial[gid].add('UNOWNED_MOVING_ATTACHMENT')
        # Nearby unsupported geometry cannot be swallowed by fringe/core.
        for s in graph.symbols.values():
            if (
                s.kind not in KINDS
                and s.kind not in {'head-chord', 'beam-group', 'barline', 'staff-barline'}
                and s.geometry.region
            ):
                b = s.geometry.region
                if any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for x, y in owned):
                    partial[gid].add('UNRESOLVED_OTHER_SYMBOL_CONTACT')
        if source.mode == 'RGBA' and any(native[y, x, 3] != 255 for x, y in fringe):
            fatal[gid].add('TRANSPARENT_SOURCE_AMBIGUITY')
        group_fringe[gid] = fringe
        for ident in members:
            core = {
                (x, y)
                for x, y in points[ident]
                if not crossing[y, x]
                and (x, y) not in staff_points
                and background is not None
                and background >= 224
                and background - float(gray[y, x]) >= 8
                and (x, y) not in foreign_support
            }
            unknown = {(x, y) for x, y in points[ident] if crossing[y, x] or (x, y) in staff_points}
            symbol_fringe = fringe & _neighbors(points[ident], 1, source.width, source.height)
            histogram = Counter(
                tuple(map(int, np.atleast_1d(native[y, x])))
                for x, y in points[ident] | symbol_fringe
            )
            local[ident] = (core, symbol_fringe, unknown, histogram)
    # Global source/fringe reconciliation occurs after all proposals exist.
    claims = defaultdict(set)
    for gid, union in group_points.items():
        for pixel in union | group_fringe.get(gid, set()):
            claims[pixel].add(gid)
    for owners in claims.values():
        if len(owners) > 1:
            for gid in owners:
                fatal[gid].add('UNRELATED_GROUP_COLLISION')
    groups, ownership = [], []
    for gid, members in atomic:
        union = group_points[gid]
        fringe = group_fringe.get(gid, set())
        unknown = {(x, y) for x, y in union if crossing[y, x] or (x, y) in staff_points}
        background = backgrounds.get(gid)
        core = {
            (x, y)
            for x, y in union - unknown
            if background is not None
            and background >= 224
            and background - float(gray[y, x]) >= 8
            and (x, y) not in foreign_support
        }
        status = REJECTED if fatal[gid] else PARTIAL if partial[gid] else COMPLETE
        blockers = tuple(sorted(fatal[gid] | partial[gid]))
        shared = {
            p for p, count in Counter(p for i in members for p in points[i]).items() if count > 1
        }
        phase18 = bool(union) and all(
            supports[i].inter_geometry is not None
            and all(
                supports[i].inter_geometry[0] <= x <= supports[i].inter_geometry[2]
                and supports[i].inter_geometry[1] <= y <= supports[i].inter_geometry[3]
                for x, y in points[i] | local.get(i, (set(), set(), set(), {}))[1]
            )
            for i in members
        )
        groups.append(
            AtomicInkGroup(
                gid,
                members,
                rle(core | fringe) if status != REJECTED else (),
                rle(core) if status != REJECTED else (),
                rle(fringe) if status != REJECTED else (),
                rle(shared),
                rle(unknown),
                sum(len(claims[p]) > 1 for p in union | fringe),
                status,
                blockers,
                phase18,
                status == COMPLETE and phase18,
            )
        )
        for ident in members:
            c, f, u, h = local.get(ident, (set(), set(), set(), {}))
            local_crossing_clear = not u and status != REJECTED
            ownership.append(
                SourceInkOwnership(
                    ident,
                    gid,
                    graph.symbols[ident].kind,
                    digest,
                    rle(c) if status != REJECTED else (),
                    rle(f) if status != REJECTED else (),
                    rle(points[ident] & staff_points),
                    rle(u),
                    (
                        ('SYMBOL_CORE', rle(c) if status != REJECTED else ()),
                        (
                            'STAFF_ATTRIBUTED',
                            rle(
                                (
                                    staff_points
                                    & _neighbors(points[ident], 1, source.width, source.height)
                                )
                                - union
                            ),
                        ),
                        ('SHARED_OR_INSEPARABLE', rle(points[ident] & staff_points)),
                        ('UNKNOWN', rle(u - staff_points)),
                    ),
                    tuple(sorted(h.items())),
                    local_crossing_clear,
                    status,
                    blockers,
                )
            )
    return SourceInkEvidence(
        digest,
        tuple(supports[i] for i in sorted(ids)),
        tuple(sorted(ownership, key=lambda r: r.symbol_id)),
        tuple(groups),
    )


def coverage(evidence):
    by_kind = {}
    for kind in sorted(KINDS):
        rows = [r for r in evidence.ownership if r.kind == kind]
        by_kind[kind] = {
            'candidate': len(rows),
            **{
                status: sum(r.status == status for r in rows)
                for status in (COMPLETE, PARTIAL, REJECTED)
            },
        }
    return {
        'by_kind': by_kind,
        'groups': {
            status: sum(g.status == status for g in evidence.groups)
            for status in (COMPLETE, PARTIAL, REJECTED)
        },
        'processed_support_unique_pixels': len(
            set().union(*(pixels_from_runs(r.runs) for r in evidence.processed))
        ),
        'processed_support_pixels': sum(len(pixels_from_runs(r.runs)) for r in evidence.processed),
        'source_core_pixels': sum(len(pixels_from_runs(g.core_union)) for g in evidence.groups),
        'fringe_pixels': sum(len(pixels_from_runs(g.fringe_union)) for g in evidence.groups),
        'intra_group_shared_pixels': sum(
            len(pixels_from_runs(g.shared_intra_group)) for g in evidence.groups
        ),
        'unrelated_group_collision_references': sum(
            g.unrelated_collision_count for g in evidence.groups
        ),
        'staff_crossing_unknown_pixels': sum(
            len(pixels_from_runs(g.unknown_crossing)) for g in evidence.groups
        ),
        'blocker_groups': dict(
            sorted(Counter(b for g in evidence.groups for b in g.blockers).items())
        ),
        'phase18_compatible_complete_groups': sum(g.edit_eligible for g in evidence.groups),
    }
