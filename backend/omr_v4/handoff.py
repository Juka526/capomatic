"""Admission to bounded refinement analysis. Never supplies OwnedInk."""

from __future__ import annotations
from collections import Counter
from dataclasses import asdict, dataclass
import json
import math

import cv2
import numpy as np
from PIL import Image

from .ink import pixels_from_runs, rle
from .masks import raster_digest
from .source_ink import COMPLETE, PARTIAL, _bounds, _neighbors, _protection, _staff_context
from .visual_graph import safe_xml

ELIGIBLE = 'REFINEMENT_ELIGIBLE_PARTIAL'
BLOCKED = 'REFINEMENT_BLOCKED_PARTIAL'
POLICY = {
    'local_radius': 2,
    'remote_guard_radius': 4,
    'unrelated_proximity_radius': 1,
    'attachment_max_gap_interlines': 1,
    'attachment_max_height_interlines': 2,
    'staff_witness_offsets': [2, 3, 4, 5, 6],
    'staff_min_witness_columns_per_side': 3,
    'max_crossing_width_interlines': 4,
    'edit_authorization_from_partial': False,
}
ALLOWED = {
    'UNKNOWN_CROSSING',
    'UNCERTAIN_ANTIALIAS_BOUNDARY',
    'UNACCOUNTED_LOCAL_CONTINUATION',
    'UNOWNED_MOVING_ATTACHMENT',
    'UNRESOLVED_OTHER_SYMBOL_CONTACT',
    'UNSUPPORTED_SUPPORT_OVERLAP',
}
MOVING = {'slur', 'articulation', 'fermata', 'ledger'}


@dataclass(frozen=True)
class AttachmentHandoff:
    symbol_id: str
    kind: str
    disposition: str
    relation_ids: tuple[str, ...]
    region: tuple[float, ...] | None
    analysis_runs: tuple[tuple[int, int, int], ...]
    reason: str


@dataclass(frozen=True)
class StaffHandoff:
    staff_id: str
    line_number: int
    interval: tuple[int, int]
    polyline: tuple[tuple[float, float], ...]
    thickness: float
    left_evidence: tuple[tuple[int, int], ...]
    right_evidence: tuple[tuple[int, int], ...]
    status: str
    reason: str


@dataclass(frozen=True)
class GroupHandoff:
    group_id: str
    ownership_evidence_status: str
    refinement_eligibility: str
    edit_authorized: bool
    members: tuple[str, ...]
    known_core: tuple[tuple[int, int, int], ...]
    known_fringe: tuple[tuple[int, int, int], ...]
    bounded_unknown: tuple[tuple[int, int, int], ...]
    protected: tuple[tuple[int, int, int], ...]
    unrelated: tuple[tuple[int, int, int], ...]
    structural: tuple[tuple[int, int, int], ...]
    unknown_bbox: tuple | None
    max_support_distance: int
    local_background: float | None
    continuation: tuple[tuple[str, tuple], ...]
    remote_continuation: tuple[tuple[int, int, int], ...]
    antialias_status: str
    staff: tuple[StaffHandoff, ...]
    attachments: tuple[AttachmentHandoff, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class RefinementHandoff:
    source_digest: str
    ownership_evidence_digest: str
    groups: tuple[GroupHandoff, ...]
    metrics: tuple[tuple[str, int], ...]
    decision: str

    def to_json(self):
        return (
            json.dumps(
                {
                    **asdict(self),
                    'metrics': dict(self.metrics),
                    'policy': POLICY,
                    'diagnostic_only': True,
                    'partial_is_never_edit_authorized': True,
                },
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            + '\n'
        )


def _inside(points, box, width, height):
    if box is None or not all(math.isfinite(v) for v in box):
        return set()
    x0, y0, x1, y1 = box
    return {
        (x, y)
        for x, y in points
        if 0 <= x < width and 0 <= y < height and x0 <= x <= x1 and y0 <= y <= y1
    }


def _box_pixels(box, size):
    if box is None or not all(math.isfinite(v) for v in box):
        return set()
    return {
        (x, y)
        for y in range(max(0, math.floor(box[1])), min(size[1] - 1, math.ceil(box[3])) + 1)
        for x in range(max(0, math.floor(box[0])), min(size[0] - 1, math.ceil(box[2])) + 1)
    }


def _chord_members(graph):
    return {
        s.id: {
            r.target
            for r in graph.relations
            if r.kind == 'contains'
            and r.source == s.id
            and r.target in graph.symbols
            and graph.symbols[r.target].kind == 'head'
        }
        for s in graph.symbols.values()
        if s.kind == 'head-chord'
    }


def attachment_handoffs(graph, group, groups_by_symbol, glyphs, size, interline):
    members = set(group['members'])
    chords = _chord_members(graph)
    anchors = members | {i for i, heads in chords.items() if heads & members}
    support = set().union(
        *(
            glyphs.get(s.page + ':' + dict(s.attributes).get('glyph', '')) or set()
            for i in members
            if (s := graph.symbols.get(i))
        )
    )
    bbox = _bounds(support)
    result = []
    for symbol in sorted(graph.symbols.values(), key=lambda s: s.id):
        if symbol.kind not in MOVING:
            continue
        rels = [r for r in graph.relations if symbol.id in (r.source, r.target)]
        attached = []
        for r in rels:
            other = r.target if r.source == symbol.id else r.source
            if r.kind in {'slur-head', 'chord-articulation', 'fermata-chord', 'head-ledger'}:
                attached.extend(chords.get(other, {other}))
        owners = {groups_by_symbol[i] for i in attached if i in groups_by_symbol}
        box = symbol.geometry.region
        near = bool(
            bbox
            and box
            and not (
                box[2] < bbox[0] - interline
                or box[0] > bbox[2] + interline
                or box[3] < bbox[1] - interline
                or box[1] > bbox[3] + interline
            )
        )
        own = set(attached) & members
        if not own and not near:
            continue
        disposition = 'ATTACHMENT_UNRELATED_PRESERVE'
        reason = 'Explicitly belongs to another group'
        region = set()
        if own or (near and not attached):
            disposition = 'ATTACHMENT_AMBIGUOUS_BLOCK'
            reason = 'Missing, cross-group or nonlocal lineage'
            if box and bbox and owners == {group['id']} and len(box) == 4:
                gap = max(bbox[0] - box[2], box[0] - bbox[2], bbox[1] - box[3], box[1] - bbox[3], 0)
                local = (
                    gap <= interline
                    and box[3] - box[1] <= 2 * interline
                    and box[2] - box[0] <= bbox[2] - bbox[0] + 2 * interline
                )
                cross_system = any(
                    k in dict(symbol.attributes) for k in ('left-extension', 'right-extension')
                )
                if local and not cross_system:
                    disposition = 'ATTACHMENT_IDENTIFIED_NEEDS_REFINEMENT'
                    reason = 'Explicit local lineage; pixels remain unowned'
                    region = _box_pixels(box, size)
        result.append(
            AttachmentHandoff(
                symbol.id,
                symbol.kind,
                disposition,
                tuple(sorted(r.id for r in rels)),
                box,
                rle(region),
                reason,
            )
        )
    return tuple(result)


def _line_y(line, x):
    for a, b in zip(line, line[1:]):
        if min(a[0], b[0]) <= x <= max(a[0], b[0]) and a[0] != b[0]:
            t = (x - a[0]) / (b[0] - a[0])
            return a[1] + t * (b[1] - a[1])
    return None


def staff_handoffs(
    source, graph, unknown, staff_points, all_support, protected, structural, background
):
    gray = np.asarray(source.convert('L'))
    out = []
    for staff in graph.staves:
        root = safe_xml(staff.source_xml.encode()) if staff.source_xml else None
        raw_lines = root.findall('lines/line') if root is not None else []
        for number, line in enumerate(staff.lines):
            try:
                thickness = float(raw_lines[number].get('thickness'))
                valid = (
                    staff.valid
                    and 0 < thickness <= staff.interline
                    and all(math.isfinite(v) for p in line for v in p)
                )
            except (IndexError, TypeError, ValueError):
                thickness = staff.interline
                valid = False
            if not np.isfinite(thickness) or thickness <= 0:
                thickness = staff.interline
                valid = False
            if len(line) < 2:
                valid = False
            xs = sorted(
                {
                    x
                    for x, y in unknown
                    if (ly := _line_y(line, x)) is not None and abs(y - ly) <= thickness / 2 + 0.5
                }
            )
            intervals = []
            for x in xs:
                if not intervals or x > intervals[-1][1] + 1:
                    intervals.append([x, x])
                else:
                    intervals[-1][1] = x
            for left, right in intervals:
                witnesses = []
                for anchor, sign in ((left, -1), (right, 1)):
                    side = []
                    for offset in POLICY['staff_witness_offsets']:
                        x = anchor + sign * offset
                        ly = _line_y(line, x)
                        if ly is None or not 0 <= x < source.width:
                            continue
                        candidates = [
                            (x, y)
                            for y in range(
                                max(0, math.floor(ly - thickness / 2)),
                                min(source.height - 1, math.ceil(ly + thickness / 2)) + 1,
                            )
                            if (x, y) in staff_points
                            and (x, y) not in all_support
                            and not protected[y, x]
                            and not structural[y, x]
                            and background is not None
                            and background - float(gray[y, x]) >= 8
                        ]
                        if candidates:
                            side.append(min(candidates, key=lambda p: (abs(p[1] - ly), p)))
                    witnesses.append(tuple(side))
                bounded = right - left + 1 <= 4 * staff.interline
                collision = any(
                    protected[y, x] or structural[y, x]
                    for x, y in unknown
                    if left <= x <= right
                    and (ly := _line_y(line, x)) is not None
                    and abs(y - ly) <= thickness / 2 + 0.5
                )
                ok = valid and bounded and not collision and all(len(s) >= 3 for s in witnesses)
                out.append(
                    StaffHandoff(
                        staff.id,
                        number + 1,
                        (left, right),
                        line,
                        thickness,
                        *witnesses,
                        'STAFF_REFINEMENT_ELIGIBLE' if ok else 'STAFF_REFINEMENT_BLOCKED',
                        (
                            'Both original/polyline/staff-glyph witnesses present'
                            if ok
                            else 'Missing geometry, bounded extent, collision-free region or bilateral evidence'
                        ),
                    )
                )
    return tuple(out)


def classify_handoff(source, graph, evidence: dict, glyphs, staff_points):
    digest = raster_digest(source)
    if digest != evidence['source_digest']:
        raise ValueError('Source/ownership digest mismatch')
    if len(graph.pages) != 1 or source.size != (graph.pages[0].width, graph.pages[0].height):
        raise ValueError('Invalid page geometry')
    width, height = source.size
    gray = np.asarray(source.convert('L'))
    protected, structural, invalid = _protection(graph, source.size)
    staff_context, missing_staff = _staff_context(graph, source.size)
    processed = {r['symbol_id']: r for r in evidence['processed']}
    ownership = {r['symbol_id']: r for r in evidence['ownership']}
    groups = evidence['groups']
    group_by_symbol = {i: g['id'] for g in groups for i in g['members']}
    supports = {
        g['id']: set().union(
            *(pixels_from_runs(processed.get(i, {}).get('runs', ())) for i in g['members'])
        )
        for g in groups
    }
    all_support = set().union(*supports.values())
    staff_points = set(staff_points)
    owners = {}
    for gid, points in supports.items():
        for point in points:
            owners.setdefault(point, set()).add(gid)
    rows = []
    for group in groups:
        gid = group['id']
        support = supports[gid]
        core = pixels_from_runs(group['core_union'])
        fringe = pixels_from_runs(group['fringe_union'])
        blockers = set()
        categories = {
            key: set()
            for key in (
                'STAFF_CONNECTED',
                'ATTACHED_MUSICAL_SYMBOL',
                'ANTIALIAS_EDGE',
                'SAME_ATOMIC_GROUP_CONTINUATION',
                'NEIGHBORING_GROUP',
                'PROTECTED_CONTENT',
                'STRUCTURAL_CONTENT',
                'UNKNOWN_LOCAL',
            )
        }
        if any(not (0 <= x < width and 0 <= y < height) for x, y in support | core | fringe):
            raise ValueError('Off-page evidence')
        if invalid or graph.invalid_geometry_count:
            blockers.add('OTHER:INVALID_GEOMETRY')
        if not core:
            blockers.add('OTHER:NO_VERIFIED_NONCROSSING_CORE')
        relation_ids = {r.id for r in graph.relations}
        if any(
            not processed.get(i, {}).get('valid', False)
            or not processed.get(i, {}).get('relation_ids')
            or not set(processed.get(i, {}).get('relation_ids', ())) <= relation_ids
            or processed.get(i, {}).get('construction_basis') == 'UNKNOWN_PROCESSED_PROVENANCE'
            for i in group['members']
        ):
            blockers.add('MISSING_LINEAGE:INVALID_SUPPORT_OR_IDENTITY')
        if any(
            i not in graph.symbols
            or i not in ownership
            or ownership.get(i, {}).get('atomic_group_id') != gid
            or ownership.get(i, {}).get('source_digest') != digest
            or ownership.get(i, {}).get('status') != group['status']
            for i in group['members']
        ):
            blockers.add('MISSING_LINEAGE:GROUP_IDENTITY')
        if group['unrelated_collision_count']:
            blockers.add('UNRELATED_OWNERSHIP:EXISTING_COLLISION')
        if any(b not in ALLOWED for b in group['blockers']):
            blockers.add('OTHER:UNRESOLVED_NONLOCAL_OR_CONTRAST_BLOCKER')
        shell1 = _neighbors(support, 1, width, height)
        shell = _neighbors(support, 2, width, height)
        unknown = (support | shell) - core - fringe
        bbox = _bounds(support)
        background = None
        if bbox:
            x0, y0, x1, y1 = bbox
            ring = [
                int(gray[y, x])
                for y in range(max(0, y0 - 5), min(height, y1 + 6))
                for x in range(max(0, x0 - 5), min(width, x1 + 6))
                if 3 <= max(x0 - x, x - x1, y0 - y, y - y1) <= 5
            ]
            background = float(np.median(ring)) if ring else None
        # Unknown is a local analysis stencil, not a source ink claim.
        local_visible = {
            p for p in unknown if background is not None and gray[p[1], p[0]] < background
        }
        interline = graph.pages[0].interline
        attachments = attachment_handoffs(
            graph, group, group_by_symbol, glyphs, source.size, interline
        )
        attachment_region = set().union(*(pixels_from_runs(a.analysis_runs) for a in attachments))
        if any(a.disposition == 'ATTACHMENT_AMBIGUOUS_BLOCK' for a in attachments):
            blockers.add('MOVING_ATTACHMENT:AMBIGUOUS_OR_NONLOCAL')
        unknown |= attachment_region - core - fringe
        related_attachment_support = set().union(
            *(
                set(
                    glyphs.get(
                        graph.symbols[a.symbol_id].page
                        + ':'
                        + dict(graph.symbols[a.symbol_id].attributes).get('glyph', '')
                    )
                    or ()
                )
                for a in attachments
                if a.disposition == 'ATTACHMENT_IDENTIFIED_NEEDS_REFINEMENT'
            )
        )
        near_other = {
            p
            for p in unknown | core | fringe
            if any(
                owners.get((p[0] + dx, p[1] + dy), set()) - {gid}
                for dx in (-1, 0, 1)
                for dy in (-1, 0, 1)
            )
        }
        p_hits = {(x, y) for x, y in unknown | core | fringe if protected[y, x]}
        s_hits = {(x, y) for x, y in unknown | core | fringe if structural[y, x]}
        unrelated = (unknown | core | fringe) & near_other
        own_attachment_ids = {
            a.symbol_id
            for a in attachments
            if a.disposition == 'ATTACHMENT_IDENTIFIED_NEEDS_REFINEMENT'
        }
        for symbol in graph.symbols.values():
            if (
                symbol.id not in group['members']
                and symbol.id not in own_attachment_ids
                and symbol.kind
                not in {
                    'head-chord',
                    'beam-group',
                    'head',
                    'stem',
                    'beam',
                    'beam-hook',
                    'flag',
                    'augmentation-dot',
                    'alter',
                    'accidental',
                }
            ):
                if _inside(unknown | core | fringe, symbol.geometry.region, width, height):
                    blockers.add('OTHER:UNRESOLVED_PRESERVED_OBJECT_CONTACT')
        if p_hits:
            blockers.add('PROTECTED:TEXT_COLLISION')
        if s_hits:
            blockers.add('STRUCTURAL:BARLINE_COLLISION')
        if unrelated:
            blockers.add('UNRELATED_OWNERSHIP:NEIGHBOR_PROXIMITY')
        # Remote guard is diagnostic only: never follow a page-wide source CC.
        guard = _neighbors(support, 4, width, height) - shell - support - attachment_region
        remote = {
            p
            for p in guard
            if background is not None
            and gray[p[1], p[0]] < background
            and not staff_context[p[1], p[0]]
            and p not in staff_points
            and p not in related_attachment_support
            and any(
                (p[0] + dx, p[1] + dy) in local_visible for dx in (-1, 0, 1) for dy in (-1, 0, 1)
            )
        }
        if remote:
            blockers.add('CONTINUATION:UNKNOWN_REMOTE_CONTINUATION')
        for x, y in local_visible:
            p = (x, y)
            if protected[y, x]:
                category = 'PROTECTED_CONTENT'
            elif structural[y, x]:
                category = 'STRUCTURAL_CONTENT'
            elif p in near_other:
                category = 'NEIGHBORING_GROUP'
            elif p in staff_points or staff_context[y, x]:
                category = 'STAFF_CONNECTED'
            elif p in related_attachment_support or p in attachment_region:
                category = 'ATTACHED_MUSICAL_SYMBOL'
            elif p in support:
                category = 'SAME_ATOMIC_GROUP_CONTINUATION'
            elif p in shell1:
                category = 'ANTIALIAS_EDGE'
            else:
                category = 'UNKNOWN_LOCAL'
            categories[category].add(p)
        staff = staff_handoffs(
            source,
            graph,
            pixels_from_runs(group['unknown_crossing'])
            | {p for p in local_visible if staff_context[p[1], p[0]]},
            staff_points,
            all_support,
            protected,
            structural,
            background,
        )
        if (
            missing_staff
            or (group['unknown_crossing'] and not staff)
            or any(s.status != 'STAFF_REFINEMENT_ELIGIBLE' for s in staff)
        ):
            blockers.add('STAFF:UNSUITABLE_CROSSING')
        aa_ok = bool(support) and not (p_hits or s_hits or unrelated or remote)
        if not aa_ok:
            blockers.add('ANTIALIAS:BOUNDARY_NOT_ISOLATED')
        # Attachment regions have their own proven finite local geometry. All
        # other unresolved pixels must remain in the declared radius-2 stencil.
        if unknown - support - shell - attachment_region:
            blockers.add('CONTINUATION:UNBOUNDED_UNKNOWN')
        distance = 0
        if support and unknown:
            box = _bounds(support | unknown)
            x0, y0, x1, y1 = box
            local = np.ones((y1 - y0 + 1, x1 - x0 + 1), dtype='uint8')
            for x, y in support:
                local[y - y0, x - x0] = 0
            distances = cv2.distanceTransform(local, cv2.DIST_C, 3)
            distance = int(max(distances[y - y0, x - x0] for x, y in unknown))
        status = (
            ELIGIBLE
            if group['status'] == PARTIAL and not blockers
            else (
                BLOCKED
                if group['status'] == PARTIAL
                else (
                    'COMPLETE_ANALYSIS_INPUT'
                    if group['status'] == COMPLETE
                    else 'REJECTED_ANALYSIS_INPUT'
                )
            )
        )
        rows.append(
            GroupHandoff(
                gid,
                group['status'],
                status,
                False,
                tuple(group['members']),
                rle(core),
                rle(fringe),
                rle(unknown),
                rle(p_hits),
                rle(unrelated),
                rle(s_hits),
                _bounds(unknown),
                distance,
                background,
                tuple((key, rle(points)) for key, points in sorted(categories.items())),
                rle(remote),
                'ANTIALIAS_BOUNDARY_REFINABLE' if aa_ok else 'ANTIALIAS_BOUNDARY_BLOCKING',
                staff,
                attachments,
                tuple(sorted(blockers)),
            )
        )
    eligible = [r for r in rows if r.refinement_eligibility == ELIGIBLE]
    eligible_symbols = {i for r in eligible for i in r.members}
    metrics = {
        'partial_groups': sum(r.ownership_evidence_status == PARTIAL for r in rows),
        'eligible_partial_groups': len(eligible),
        'blocked_partial_groups': sum(r.refinement_eligibility == BLOCKED for r in rows),
        'eligible_notes': sum(graph.symbols[i].kind == 'head' for i in eligible_symbols),
        'eligible_simple_symbols': sum(
            graph.symbols[i].kind in {'flag', 'augmentation-dot', 'alter', 'accidental'}
            for i in eligible_symbols
        ),
        'bounded_unknown_pixels': sum(len(pixels_from_runs(r.bounded_unknown)) for r in eligible),
        'blocked_unknown_pixels': sum(
            len(pixels_from_runs(r.bounded_unknown))
            for r in rows
            if r.refinement_eligibility == BLOCKED
        ),
    }
    for category in (
        'STAFF',
        'ANTIALIAS',
        'CONTINUATION',
        'MOVING_ATTACHMENT',
        'PROTECTED',
        'STRUCTURAL',
        'UNRELATED_OWNERSHIP',
        'MISSING_LINEAGE',
        'OTHER',
    ):
        metrics['blocked_' + category.lower()] = sum(
            any(b.startswith(category + ':') for b in r.blockers)
            for r in rows
            if r.ownership_evidence_status == PARTIAL
        )
    # No edit permission can be created by a handoff, even for COMPLETE inputs.
    return RefinementHandoff(
        digest,
        __import__('hashlib')
        .sha256(json.dumps(evidence, sort_keys=True, allow_nan=False).encode())
        .hexdigest(),
        tuple(rows),
        tuple(sorted(metrics.items())),
        'READY_FOR_MASK_REFINEMENT_ANALYSIS' if eligible else 'NEEDS_HANDOFF_FIXES',
    )
