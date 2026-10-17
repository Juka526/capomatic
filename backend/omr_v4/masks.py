"""Diagnostic source-mask admission. Never erases, restores or renders score ink."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from enum import StrEnum

import numpy as np
from PIL import Image, ImageDraw

from .visual_graph import Box, VisualScoreGraph, union


class MaskState(StrEnum):
    APPROVED = 'APPROVED_EDIT_MASK'
    PROTECTED = 'BLOCKED_PROTECTED_COLLISION'
    UNKNOWN = 'BLOCKED_UNKNOWN_OWNERSHIP'
    INCOMPLETE = 'BLOCKED_INCOMPLETE_GROUP'
    ATTACHMENT = 'BLOCKED_UNSUPPORTED_ATTACHMENT'
    STRUCTURAL = 'BLOCKED_STRUCTURAL_COLLISION'
    TARGET = 'BLOCKED_TARGET_COLLISION'


@dataclass(frozen=True)
class OwnedInk:
    """Trusted upstream evidence, not inferred by this module from a rectangle.

    Runs are (y, x_start, x_stop_exclusive) in the exact original raster. The
    caller must independently verify symbol ownership and complete ink isolation.
    No real-score evidence producer is implemented in Phase 1.8; unit fixtures
    supply known ownership. A digest binds evidence to pixels AND image mode.
    """

    symbol_id: str
    source_digest: str
    runs: tuple[tuple[int, int, int], ...]
    evidence: str


@dataclass(frozen=True)
class Crossing:
    staff_id: str
    line_number: int
    start: tuple[float, float]
    end: tuple[float, float]
    status: str = 'RESTORE_REQUIRED'
    basis: str = 'SOURCE_CANDIDATE_ENVELOPE'


@dataclass(frozen=True)
class NoteMask:
    head_id: str
    atomic_group: str
    ownership_basis: str
    source_object_ids: tuple[str, ...]
    ledger_candidates: tuple[str, ...]
    source_envelope: Box | None
    target_envelope: Box | None
    state: MaskState
    reasons: tuple[str, ...]
    blockers: tuple[MaskState, ...]
    source_protected_ids: tuple[str, ...]
    target_protected_ids: tuple[str, ...]
    structural_collision_ids: tuple[str, ...]
    staff_crossings: tuple[Crossing, ...]


@dataclass(frozen=True)
class AtomicGroup:
    id: str
    head_ids: tuple[str, ...]
    disposition: str
    blockers: tuple[MaskState, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class SymbolPolicy:
    id: str
    kind: str
    policy: str
    attached_heads: tuple[str, ...]


@dataclass(frozen=True)
class MaskSafetyPlan:
    width: int
    height: int
    mode: str
    source_digest: str
    notes: tuple[NoteMask, ...]
    groups: tuple[AtomicGroup, ...]
    beam_groups: tuple[AtomicGroup, ...]
    curve_groups: tuple[AtomicGroup, ...]
    symbol_policies: tuple[SymbolPolicy, ...]
    protected_regions: tuple[tuple[str, Box | None], ...]
    nested_protection: tuple[tuple[str, str], ...]
    metrics: tuple[tuple[str, int | float], ...]
    decision: str

    def to_json(self) -> str:
        data = asdict(self)
        data['metrics'] = dict(self.metrics)
        data['diagnostic_only'] = True
        data['approved_masks_are_conditional_on_verified_ink_evidence'] = True
        return json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + '\n'


@dataclass
class MaskArtifacts:
    """Binary images are diagnostics; only approved is an edit authorization union."""

    approved: Image.Image
    blocked: Image.Image
    protected: Image.Image
    staff_restore: Image.Image
    target: Image.Image
    unknown: Image.Image


def raster_digest(image: Image.Image) -> str:
    """Bind exact native pixels, dimensions and mode without conversions."""
    if image.mode not in {'L', 'RGB', 'RGBA'}:
        raise ValueError('Explicit L, RGB or RGBA raster required')
    header = f'{image.width}:{image.height}:{image.mode}:'.encode()
    return hashlib.sha256(header + image.tobytes()).hexdigest()


def validate_pixel_integrity(
    original: Image.Image, candidate: Image.Image, approved_mask: Image.Image
) -> dict:
    """Fail on any pixel change outside a binary mask, without implicit rescaling."""
    if original.size != candidate.size or original.size != approved_mask.size:
        raise ValueError('Raster/mask dimensions differ')
    if original.mode != candidate.mode:
        raise ValueError('Raster modes differ; implicit conversion is forbidden')
    raster_digest(original)
    if approved_mask.mode != 'L':
        raise ValueError('Approved mask must be native-coordinate binary L')
    mask = np.asarray(approved_mask)
    if not np.all((mask == 0) | (mask == 255)):
        raise ValueError('Mask is not binary')
    changed = np.asarray(original) != np.asarray(candidate)
    if changed.ndim == 3:
        changed = changed.any(axis=2)
    outside = int(np.count_nonzero(changed & (mask == 0)))
    if outside:
        raise ValueError(f'{outside} changed pixels outside approved mask')
    return {
        'ok': True,
        'changed_pixels': int(np.count_nonzero(changed)),
        'outside_mask_changed_pixels': 0,
        'mode': original.mode,
        'coordinate_alignment': 'exact_original_raster',
    }


def _box(value, width, height) -> Box | None:
    if value is None:
        return None
    if len(value) != 4 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in value):
        raise ValueError('Nonfinite/invalid geometry')
    a, b, c, d = map(float, value)
    if c < a or d < b or a < 0 or b < 0 or c > width or d > height:
        raise ValueError('Geometry outside original raster or inverted')
    return a, b, c, d


def _intersects(a, b):
    return (
        a is not None
        and b is not None
        and max(a[0], b[0]) <= min(a[2], b[2])
        and max(a[1], b[1]) <= min(a[3], b[3])
    )


def _rectangle(mask, box):
    if box:
        ImageDraw.Draw(mask).rectangle(
            (
                math.floor(box[0]),
                math.floor(box[1]),
                min(mask.width - 1, math.ceil(box[2])),
                min(mask.height - 1, math.ceil(box[3])),
            ),
            fill=255,
        )


def _clip_segment(a, b, box):
    """Liang–Barsky clipping preserves original float endpoints (no mean-y lines)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    lo, hi = 0.0, 1.0
    for p, q in (
        (-dx, a[0] - box[0]),
        (dx, box[2] - a[0]),
        (-dy, a[1] - box[1]),
        (dy, box[3] - a[1]),
    ):
        if p == 0:
            if q < 0:
                return None
        elif p < 0:
            lo = max(lo, q / p)
        else:
            hi = min(hi, q / p)
        if lo > hi:
            return None
    return ((a[0] + lo * dx, a[1] + lo * dy), (a[0] + hi * dx, a[1] + hi * dy))


def _crossings(graph, staff_ids, boxes, basis='SOURCE_CANDIDATE_ENVELOPE'):
    result = set()
    for staff in graph.staves:
        if staff.id not in staff_ids:
            continue
        for number, line in enumerate(staff.lines, 1):
            for a, b in zip(line, line[1:]):
                for box in boxes:
                    segment = _clip_segment(a, b, box) if box else None
                    if segment:
                        result.add(Crossing(staff.id, number, *segment, basis=basis))
    return tuple(sorted(result, key=lambda c: (c.staff_id, c.line_number, c.start, c.end)))


def _ink_image(evidence, symbol, digest, width, height):
    if evidence is None:
        return None
    if (
        evidence.symbol_id != symbol.id
        or evidence.source_digest != digest
        or not evidence.evidence
        or not evidence.runs
    ):
        raise ValueError('Unbound or incomplete ink evidence')
    for y, start, stop in evidence.runs:
        if (
            not all(type(v) is int for v in (y, start, stop))
            or not 0 <= y < height
            or not 0 <= start < stop <= width
        ):
            raise ValueError('Invalid ink run')
        box = symbol.geometry.region
        if box is None or not (box[0] <= start and stop - 1 <= box[2] and box[1] <= y <= box[3]):
            raise ValueError('Ink evidence escapes symbol geometry')
    return evidence.runs


def _components(heads, links):
    parent = {h: h for h in heads}

    def find(h):
        while parent[h] != h:
            h = parent[h]
        return h

    for linked in links:
        values = sorted(set(linked) & parent.keys())
        for h in values[1:]:
            a, b = find(values[0]), find(h)
            parent[max(a, b)] = min(a, b)
    groups = {}
    for h in sorted(heads):
        groups.setdefault(find(h), []).append(h)
    return tuple(tuple(v) for _, v in sorted(groups.items()))


def plan_masks(
    source: Image.Image, graph: VisualScoreGraph, layout: dict, owned_ink: tuple[OwnedInk, ...] = ()
) -> tuple[MaskSafetyPlan, MaskArtifacts]:
    """Audit masks with strict atomicity. No real-score ink isolation is guessed.

    Unknown isolation, ledgers, curve extensions and unsupported moving symbols
    remain blockers even if bounding geometry looks plausible. Supplied OwnedInk
    is a trusted upstream contract, not an ownership certificate manufactured here.
    """
    if len(graph.pages) != 1:
        raise ValueError('Mask gate accepts one explicitly aligned raster page')
    page = graph.pages[0]
    width, height = source.size
    if source.size != (page.width, page.height):
        raise ValueError('Graph and raster dimensions differ')
    digest = raster_digest(source)
    symbols = graph.symbols
    moves = {m['source_head_id']: m for m in layout['note_moves']}
    if len(moves) != len(layout['note_moves']):
        raise ValueError('Duplicate head ownership in layout')
    matches = {m['head_id']: m for m in layout['matches']['notes'] if m['status'] == 'MATCHED'}
    if len(matches) != sum(m['status'] == 'MATCHED' for m in layout['matches']['notes']):
        raise ValueError('Head claimed by multiple semantic events')
    if moves.keys() != matches.keys():
        raise ValueError('Move/ownership identity mismatch')
    ink = {e.symbol_id: e for e in owned_ink}
    if len(ink) != len(owned_ink) or any(i not in symbols for i in ink):
        raise ValueError('Duplicate or unknown ink evidence')
    blank = lambda: Image.new('L', source.size)
    artifacts = MaskArtifacts(*(blank() for _ in range(6)))
    protected = tuple((r.id, _box(r.bbox, width, height)) for r in graph.text_protected_regions)
    for _, box in protected:
        _rectangle(artifacts.protected, box)
    nested = tuple(
        sorted(
            (r.source, r.target)
            for r in graph.relations
            if r.kind == 'contains' and r.source in dict(protected) and r.target in dict(protected)
        )
    )
    member_heads = {
        s.id: {
            r.target
            for r in graph.relations
            if r.kind == 'contains'
            and r.source == s.id
            and r.target in symbols
            and symbols[r.target].kind == 'head'
        }
        for s in symbols.values()
        if s.kind in {'head-chord', 'small-chord'}
    }
    policies = []
    structural, preserved, unknown = {}, {}, {}
    for s in symbols.values():
        if s.kind in {'articulation', 'fermata', 'dynamics', 'pedal', 'barline', 'staff-barline'}:
            attached = set()
            for r in graph.relations:
                if s.id not in (r.source, r.target):
                    continue
                other = r.target if r.source == s.id else r.source
                if r.kind in {
                    'chord-articulation',
                    'fermata-chord',
                    'chord-dynamics',
                    'chord-pedal',
                }:
                    attached |= member_heads.get(other, set())
            policy = (
                ('ATTACHED_MAY_MOVE' if attached else 'UNRESOLVED')
                if s.kind in {'articulation', 'fermata'}
                else (
                    'STRUCTURAL_PROTECTED'
                    if s.kind in {'barline', 'staff-barline'}
                    else 'PRESERVE_IN_PLACE'
                )
            )
            policies.append(SymbolPolicy(s.id, s.kind, policy, tuple(sorted(attached))))
            if policy == 'STRUCTURAL_PROTECTED':
                structural[s.id] = _box(s.geometry.region, width, height)
            elif policy == 'PRESERVE_IN_PLACE':
                preserved[s.id] = _box(s.geometry.region, width, height)
            else:
                unknown[s.id] = _box(s.geometry.region, width, height)
        elif s.kind in {
            'clef',
            'key',
            'key-alter',
            'time-pair',
            'time-whole',
            'time-number',
            'time-top-bottom',
        }:
            structural[s.id] = _box(s.geometry.region, width, height)
        elif s.kind not in {
            'head',
            'head-chord',
            'small-chord',
            'stem',
            'beam',
            'beam-hook',
            'small-beam',
            'beam-group',
            'flag',
            'small-flag',
            'augmentation-dot',
            'alter',
            'ledger',
            'slur',
            'lyric-item',
            'lyric-line',
            'word',
            'sentence',
            'chord-name',
            'rest',
            'rest-chord',
        }:
            unknown[s.id] = _box(s.geometry.region, width, height)
    for box in list(structural.values()) + list(preserved.values()) + list(unknown.values()):
        _rectangle(artifacts.protected, box)
    # Rest and chord text pixels are never implicitly owned by note edits.
    for s in symbols.values():
        if s.kind in {'rest', 'chord-name'}:
            preserved[s.id] = _box(s.geometry.region, width, height)
            _rectangle(artifacts.protected, preserved[s.id])
    links = [b['heads'] for b in layout['beam_groups']]
    links += [[e[1] for e in c['endpoints']] for c in layout['slurs']]
    links += [list(hs) for hs in member_heads.values()]
    # Cross-system relations are used ONLY to propagate a blocker to all explicitly
    # linked notes. They never authorize curve ownership/reconstruction.
    curve_heads = {c['id']: {e[1] for e in c['endpoints']} for c in layout['slurs']}
    for r in graph.relations:
        if r.kind in {'left-extension', 'right-extension'}:
            links.append(list(curve_heads.get(r.source, set()) | curve_heads.get(r.target, set())))
    stem_heads = {}
    for r in graph.relations:
        if r.kind in {'head-stem', 'chord-stem'}:
            for stem, other in ((r.source, r.target), (r.target, r.source)):
                if stem in symbols and symbols[stem].kind == 'stem':
                    stem_heads.setdefault(stem, set()).update(
                        member_heads.get(other, {other} if other in moves else set())
                    )
    links += [list(heads) for heads in stem_heads.values()]
    components = _components(moves, links)
    component_heads = {h: set(component) for component in components for h in component}
    local = {}
    all_crossings = set()
    for head_id, move in sorted(moves.items()):
        head = symbols.get(head_id)
        if head is None or head.kind != 'head' or not head.geometry.valid:
            raise ValueError('Invalid matched head')
        for name in ('source_x', 'source_y', 'target_x', 'target_y'):
            if not math.isfinite(move[name]):
                raise ValueError('Nonfinite movement')
        if (
            head.geometry.center != (move['source_x'], move['source_y'])
            or head.staff != move['staff']
        ):
            raise ValueError('Source/head coordinate lineage mismatch')
        dy = move['target_y'] - move['source_y']
        from music21 import pitch

        source_pitch = pitch.Pitch(move['source_pitch'])
        target_pitch = pitch.Pitch(move['target_pitch'])
        source_alter = source_pitch.accidental.alter if source_pitch.accidental else 0
        target_alter = target_pitch.accidental.alter if target_pitch.accidental else 0
        if move['target_x'] != move['source_x']:
            raise ValueError('Horizontal reflow is unsupported')
        objects = {head_id}
        containers = {
            r.source
            for r in graph.relations
            if r.kind == 'contains' and r.target == head_id and r.source in member_heads
        }
        stems = set()
        for r in graph.relations:
            if r.kind in {'head-stem', 'chord-stem'} and (
                r.source in containers | {head_id} or r.target in containers | {head_id}
            ):
                stems |= {
                    i for i in (r.source, r.target) if i in symbols and symbols[i].kind == 'stem'
                }
        objects |= stems
        for r in graph.relations:
            if r.kind in {'beam-stem', 'flag-stem'} and (r.source in stems or r.target in stems):
                objects |= {
                    i
                    for i in (r.source, r.target)
                    if i in symbols
                    and symbols[i].kind in {'beam', 'beam-hook', 'small-beam', 'flag', 'small-flag'}
                }
            if r.kind in {'alter-head', 'augmentation', 'double-dot'} and head_id in (
                r.source,
                r.target,
            ):
                objects |= {
                    i
                    for i in (r.source, r.target)
                    if i in symbols and symbols[i].kind in {'alter', 'augmentation-dot'}
                }
            if r.kind == 'slur-head' and head_id in (r.source, r.target):
                objects |= {
                    i for i in (r.source, r.target) if i in symbols and symbols[i].kind == 'slur'
                }
        blockers = set()
        reasons = set()
        staff = next(s for s in graph.staves if s.id == head.staff)
        source_staff_pitch = (
            matches[head_id].get('note', {}).get('staff_pitch', head.pitch_position)
        )
        if source_alter != target_alter:
            blockers.add(MaskState.UNKNOWN)
            reasons.add('Changed accidental occupancy is not independently bounded')
        if source_staff_pitch is None or abs(source_staff_pitch + 2 * dy / staff.interline) > 4:
            blockers.add(MaskState.UNKNOWN)
            reasons.add('Target ledger occupancy requires explicit geometry/ownership')
        ledgers = tuple(
            sorted(
                s.id
                for s in symbols.values()
                if s.kind == 'ledger'
                and s.staff == head.staff
                and _intersects(
                    (
                        (s.geometry.region[0], 0, s.geometry.region[2], height)
                        if s.geometry.region
                        else None
                    ),
                    (
                        (head.geometry.bbox[0], 0, head.geometry.bbox[2], height)
                        if head.geometry.bbox
                        else None
                    ),
                )
            )
        )
        if ledgers:
            blockers.add(MaskState.UNKNOWN)
            reasons.add('Ledger/pivot ink ownership requires independent evidence')
        for policy in policies:
            if head_id in policy.attached_heads and policy.kind in {'articulation', 'fermata'}:
                objects.add(policy.id)
                if dy != 0 or move['source_pitch'] != move['target_pitch']:
                    blockers.add(MaskState.ATTACHMENT)
                    reasons.add(f'Unsupported moving attachment: {policy.id}')
        for beam in layout['beam_groups']:
            if head_id in beam['heads'] and (
                beam['status'] != 'UNIFORM_DELTA' or any(h not in moves for h in beam['heads'])
            ):
                blockers.add(MaskState.INCOMPLETE)
                reasons.add(f'Incomplete beam group: {beam["id"]}')
        for curve in layout['slurs']:
            if head_id in curve_heads[curve['id']] and (
                not curve['linked'] or len({e[4] for e in curve['endpoints']}) != 1
            ):
                blockers.add(MaskState.INCOMPLETE)
                reasons.add(f'Unresolved curve/extension: {curve["id"]}')
        if any(
            r.kind == 'beam-rest' and (r.source in objects or r.target in objects)
            for r in graph.relations
        ):
            blockers.add(MaskState.INCOMPLETE)
            reasons.add('Connected beam/rest ownership is incomplete')
        boxes = [_box(symbols[i].geometry.region, width, height) for i in sorted(objects)]
        if any(b is None for b in boxes) or any(not symbols[i].geometry.valid for i in objects):
            blockers.add(MaskState.UNKNOWN)
            reasons.add('Incomplete object geometry')
        source_box = union(boxes)
        # Target is destination only, never the source-to-target swept rectangle.
        target_box = union((b[0], b[1] + dy, b[2], b[3] + dy) for b in boxes if b)
        target_outside = bool(target_box and (target_box[1] < 0 or target_box[3] > height))
        if target_outside:
            blockers.add(MaskState.TARGET)
            reasons.add('Target envelope leaves raster')
        for box in boxes:
            _rectangle(
                artifacts.target,
                (
                    (box[0], max(0, box[1] + dy), box[2], min(height, box[3] + dy))
                    if box and not target_outside
                    else None
                ),
            )
        source_protected = tuple(
            i for i, b in protected if any(_intersects(box, b) for box in boxes)
        )
        target_protected = tuple(i for i, b in protected if _intersects(target_box, b))
        if source_protected:
            blockers.add(MaskState.PROTECTED)
            reasons.add('Source envelope intersects active text protection')
        if target_protected:
            blockers.add(MaskState.TARGET)
            reasons.add('Target envelope intersects active text protection')
        collisions = tuple(
            sorted(
                i
                for i, b in structural.items()
                if any(_intersects(box, b) for box in boxes) or _intersects(target_box, b)
            )
        )
        if collisions:
            blockers.add(MaskState.STRUCTURAL)
            reasons.add('Source/target intersects structural protection')
        if any(
            any(_intersects(box, b) for box in boxes) or _intersects(target_box, b)
            for b in list(preserved.values()) + list(unknown.values())
        ):
            blockers.add(MaskState.UNKNOWN)
            reasons.add('Collision with preserved or unknown source object')
        if graph.invalid_geometry_count or any(
            b is None
            for b in list(structural.values()) + list(preserved.values()) + list(unknown.values())
        ):
            blockers.add(MaskState.UNKNOWN)
            reasons.add('Invalid or unbounded noneditable object geometry')
        other_heads = [
            s for s in symbols.values() if s.kind == 'head' and s.id not in component_heads[head_id]
        ]
        unrelated_curves = [s for s in symbols.values() if s.kind == 'slur' and s.id not in objects]
        if any(
            any(_intersects(box, s.geometry.region) for box in boxes)
            for s in other_heads + unrelated_curves
        ):
            blockers.add(MaskState.UNKNOWN)
            reasons.add('Source overlaps unrelated note/curve envelope')
        if any(_intersects(target_box, s.geometry.region) for s in other_heads + unrelated_curves):
            blockers.add(MaskState.TARGET)
            reasons.add('Target overlaps unrelated note/curve envelope')
        if any(b is None for _, b in protected):
            blockers.add(MaskState.UNKNOWN)
            reasons.add('Unbounded protected text exists')
        # No thresholding or bbox-fill operation can produce approved symbol ink.
        exact = {i: _ink_image(ink.get(i), symbols[i], digest, width, height) for i in objects}
        if any(image is None for image in exact.values()):
            blockers.add(MaskState.UNKNOWN)
            reasons.add('Complete independently verified symbol ink is unavailable')
        crossing_boxes = boxes
        basis = 'SOURCE_CANDIDATE_ENVELOPE'
        if all(runs is not None for runs in exact.values()):
            crossing_boxes = [
                (start, y, stop - 1, y) for runs in exact.values() for y, start, stop in runs
            ]
            basis = 'VERIFIED_SOURCE_INK'
        crossings = _crossings(graph, {head.staff}, crossing_boxes, basis)
        all_crossings.update(crossings)
        for c in crossings:
            # Diagnostic corridor only: true staff ink thickness is not isolated.
            staff = next(s for s in graph.staves if s.id == c.staff_id)
            ImageDraw.Draw(artifacts.staff_restore).line(
                (*c.start, *c.end), fill=255, width=max(1, math.ceil(staff.interline / 2))
            )
        local[head_id] = {
            'objects': tuple(sorted(objects)),
            'ledgers': ledgers,
            'source': source_box,
            'target': target_box,
            'blockers': blockers,
            'reasons': reasons,
            'source_protected': source_protected,
            'target_protected': target_protected,
            'structural': collisions,
            'crossings': crossings,
            'exact': exact,
        }
    groups = []
    notes = []
    for heads in components:
        blockers = set().union(*(local[h]['blockers'] for h in heads))
        reasons = set().union(*(local[h]['reasons'] for h in heads))
        state = sorted(blockers, key=str)[0] if blockers else MaskState.APPROVED
        group_id = 'atomic:' + heads[0]
        groups.append(
            AtomicGroup(
                group_id,
                heads,
                'BLOCKED' if blockers else 'APPROVABLE_AS_GROUP',
                tuple(sorted(blockers)),
                tuple(sorted(reasons)),
            )
        )
        for h in heads:
            item = local[h]
            notes.append(
                NoteMask(
                    h,
                    group_id,
                    matches[h].get('ownership_basis', 'DIRECT'),
                    item['objects'],
                    item['ledgers'],
                    item['source'],
                    item['target'],
                    state,
                    tuple(sorted(reasons)),
                    tuple(sorted(blockers)),
                    item['source_protected'],
                    item['target_protected'],
                    item['structural'],
                    item['crossings'],
                )
            )
            if blockers:
                _rectangle(artifacts.blocked, item['source'])
                if MaskState.UNKNOWN in blockers:
                    _rectangle(artifacts.unknown, item['source'])
            else:
                draw = ImageDraw.Draw(artifacts.approved)
                for runs in item['exact'].values():
                    for y, start, stop in runs:
                        draw.line((start, y, stop - 1, y), fill=255)
    by_head = {n.head_id: n for n in notes}

    def group_report(id, heads):
        heads = tuple(sorted(heads))
        present = [by_head[h] for h in heads if h in by_head]
        blockers = set().union(*(set(n.blockers) for n in present))
        reasons = set().union(*(set(n.reasons) for n in present))
        if not heads or len(present) != len(heads):
            blockers.add(MaskState.INCOMPLETE)
            reasons.add('Group contains unowned endpoints/heads')
        return AtomicGroup(
            id,
            heads,
            'BLOCKED' if blockers else 'APPROVABLE_AS_GROUP',
            tuple(sorted(blockers)),
            tuple(sorted(reasons)),
        )

    beams = tuple(group_report(b['id'], b['heads']) for b in layout['beam_groups'])
    curves = tuple(group_report(c['id'], curve_heads[c['id']]) for c in layout['slurs'])
    approved = sum(n.state == MaskState.APPROVED for n in notes)
    cross_ids = {
        c['id']
        for c in layout['slurs']
        if any(
            k in dict(symbols[c['id']].attributes) for k in ('left-extension', 'right-extension')
        )
    }
    cross_groups = {
        g.id for g in groups if any(any(cid in reason for cid in cross_ids) for reason in g.reasons)
    }
    metrics = {
        'total_matched_notes': len(matches),
        'notes_eligible_for_mask_planning': len(notes),
        'atomic_groups_eligible_for_mask_planning': len(groups),
        'approved_note_masks': approved,
        'blocked_note_masks': len(notes) - approved,
        'approved_beam_groups': sum(b.disposition == 'APPROVABLE_AS_GROUP' for b in beams),
        'blocked_beam_groups': sum(b.disposition == 'BLOCKED' for b in beams),
        'source_protected_intersections': sum(len(n.source_protected_ids) for n in notes),
        'target_protected_intersections': sum(len(n.target_protected_ids) for n in notes),
        'staff_line_crossing_segments_restore_required': len(all_crossings),
        'unresolved_attachment_blocked_notes': sum(
            MaskState.INCOMPLETE in n.blockers for n in notes
        ),
        'cross_system_tie_segments': sum(
            any(
                k in dict(symbols[c['id']].attributes)
                for k in ('left-extension', 'right-extension')
            )
            for c in layout['slurs']
        ),
        'unsupported_attachment_blocked_notes': sum(
            MaskState.ATTACHMENT in n.blockers for n in notes
        ),
        'cross_system_tie_blocked_atomic_groups': len(cross_groups),
        'cross_system_tie_blocked_notes': sum(n.atomic_group in cross_groups for n in notes),
        'structural_collision_blocked_notes': sum(
            MaskState.STRUCTURAL in n.blockers for n in notes
        ),
        'target_collision_blocked_notes': sum(MaskState.TARGET in n.blockers for n in notes),
        'invalid_geometry': graph.invalid_geometry_count,
        'staff_restore_corridor_pixels': int(np.count_nonzero(np.asarray(artifacts.staff_restore))),
        'unsupported_attached_symbol_instances': sum(
            p.policy == 'ATTACHED_MAY_MOVE' for p in policies
        ),
        'unresolved_attachment_instances': sum(p.policy == 'UNRESOLVED' for p in policies),
        'approved_note_percentage': 100 * approved / len(notes) if notes else 0,
    }
    decision = (
        'NEEDS_MASK_SAFETY_FIXES'
        if any(n.blockers for n in notes)
        or not notes
        or layout['matches'].get('unmatched_visual_ids')
        or any(m['status'] != 'MATCHED' for m in layout['matches']['notes'])
        else 'READY_FOR_PHASE_2_PROTOTYPE'
    )
    result = MaskSafetyPlan(
        width,
        height,
        source.mode,
        digest,
        tuple(sorted(notes, key=lambda n: n.head_id)),
        tuple(groups),
        beams,
        curves,
        tuple(policies),
        protected,
        nested,
        tuple(sorted(metrics.items())),
        decision,
    )
    return result, artifacts
