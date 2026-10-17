"""Immutable diagnostic intent. These regions are NOT approved editing masks."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, fields, is_dataclass
from fractions import Fraction

from .matcher import MatchResult, SemanticScore
from .visual_graph import Box, Page, ProtectedRegion, VisualScoreGraph, union


@dataclass(frozen=True)
class NoteMovePlan:
    semantic_id: str
    source_head_id: str
    page: str
    source_pitch: str
    target_pitch: str
    diatonic_steps: int
    source_x: float
    source_y: float
    target_x: float
    target_y: float
    staff: str
    measure: str
    offset: Fraction
    confidence: float
    connected_symbols: tuple[tuple[str, tuple[str, ...]], ...]
    source_region: Box | None
    potential_edit_region: Box | None
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class BeamGroupPlan:
    id: str
    page: str
    heads: tuple[str, ...]
    stems: tuple[str, ...]
    beams: tuple[str, ...]
    head_target_deltas: tuple[tuple[str, float | None], ...]
    uniform_delta: bool | None
    status: str
    source_region: Box | None
    potential_edit_region: Box | None


@dataclass(frozen=True)
class SlurPlan:
    id: str
    page: str
    tie: bool
    curve: tuple[tuple[float, float], ...]
    # side, head ID, source position, target position, delta y
    endpoints: tuple[
        tuple[str, str, tuple[float, float] | None, tuple[float, float] | None, float | None], ...
    ]
    linked: bool
    source_region: Box | None
    potential_edit_region: Box | None


@dataclass(frozen=True)
class KeySignaturePlan:
    id: str
    page: str | None
    source_symbol_ids: tuple[str, ...]
    part: str
    staff: int | None
    measure: str
    offset: Fraction | None
    source_key: str | None
    target_key: str | None
    target_fifths: int | None
    region: Box | None
    status: str
    reason: str


@dataclass(frozen=True)
class Intersection:
    edit_id: str
    protected_id: str
    page: str
    region: Box


@dataclass(frozen=True)
class LayoutEditPlan:
    schema_version: int
    diagnostic_only: bool
    pages: tuple[Page, ...]
    matches: MatchResult
    note_moves: tuple[NoteMovePlan, ...]
    beam_groups: tuple[BeamGroupPlan, ...]
    slurs: tuple[SlurPlan, ...]
    key_signatures: tuple[KeySignaturePlan, ...]
    protected_regions: tuple[ProtectedRegion, ...]
    intersections: tuple[Intersection, ...]
    blockers: tuple[str, ...]
    metrics: tuple[tuple[str, int | float | None], ...]

    def to_json(self) -> str:
        """Serialize without timestamps, random IDs, NaN, or mutable payloads."""
        data = to_data(self)
        data['metrics'] = dict(self.metrics)
        return (
            json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'
        )


def to_data(value):
    """Convert frozen dataclasses and rational times to deterministic JSON data."""
    if is_dataclass(value):
        return {f.name: to_data(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, tuple):
        return [to_data(v) for v in value]
    return value


def _swept(box: Box | None, deltas) -> Box | None:
    if box is None:
        return None
    values = [d for d in deltas if d is not None]
    return (box[0], box[1] + min([0.0] + values), box[2], box[3] + max([0.0] + values))


def _intersection(a: Box | None, b: Box | None) -> Box | None:
    if a is None or b is None:
        return None
    result = (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))
    return result if result[0] <= result[2] and result[1] <= result[3] else None


def build_plan(
    graph: VisualScoreGraph, source: SemanticScore, target: SemanticScore, matches: MatchResult
) -> LayoutEditPlan:
    """Plan per-note diatonic displacement using existing V3 transposed semantics."""
    if len(source.notes) != len(target.notes) or any(
        a.identity != b.identity for a, b in zip(source.notes, target.notes)
    ):
        raise ValueError('Source/target event correspondence changed; no plan generated')
    if tuple(m.note for m in matches.notes) != source.notes:
        raise ValueError('Matcher input does not correspond to source semantics')
    target_notes = {a.id: b for a, b in zip(source.notes, target.notes)}
    staff_by_id = {s.id: s for s in graph.staves}
    page_by_id = {p.id: p for p in graph.pages}
    symbols = graph.symbols
    blockers = list(graph.issues)
    moves = []
    attachment_edges = {
        'contains',
        'head-stem',
        'chord-stem',
        'beam-stem',
        'beam-head',
        'beam-chord',
        'flag-stem',
        'alter-head',
        'augmentation',
        'double-dot',
        'slur-head',
    }
    for match in matches.notes:
        if match.status != 'MATCHED':
            continue
        head = symbols[match.head_id]
        staff = staff_by_id.get(head.staff)
        point = head.geometry.center
        if not staff or not staff.valid or point is None:
            raise ValueError('Matched note has invalid geometry')
        target_note = target_notes[match.note.id]
        steps = target_note.diatonic_number - match.note.diatonic_number
        dy = -steps * staff.interline / 2
        tx, ty = point[0], point[1] + dy
        if not all(math.isfinite(v) for v in (*point, tx, ty)):
            raise ValueError('Nonfinite note target')
        # Follow only this chord's heads and stems; do not flood through a beam
        # or slur into unrelated notes. Beam components are handled separately.
        connected = {head.id}
        chords = {
            i
            for i in graph.neighbors(head.id, {'contains'})
            if i in symbols and symbols[i].kind in {'head-chord', 'small-chord'}
        }
        connected |= chords
        for ident in chords | {head.id}:
            connected.update(graph.neighbors(ident, attachment_edges))
        stems = {i for i in connected if i in symbols and symbols[i].kind == 'stem'}
        for stem in stems:
            connected.update(graph.neighbors(stem, attachment_edges))
        # Ledger-head edges are not serialized by Audiveris. Record nearby ledger
        # candidates conservatively, with an explicit unresolved-association blocker.
        ledger_candidates = {
            s.id
            for s in symbols.values()
            if s.kind == 'ledger'
            and s.staff == head.staff
            and s.geometry.region
            and head.geometry.bbox
            and s.geometry.region[0] <= head.geometry.bbox[2]
            and s.geometry.region[2] >= head.geometry.bbox[0]
        }
        connected |= ledger_candidates
        local_blockers = []
        if ledger_candidates:
            local_blockers.append('ledger candidates need explicit association before editing')
        if any(
            i not in symbols or not symbols[i].geometry.valid or symbols[i].geometry.region is None
            for i in connected
        ):
            local_blockers.append('connected symbol geometry incomplete')
        if not 0 <= tx < page_by_id[head.page].width or not 0 <= ty < page_by_id[head.page].height:
            local_blockers.append('target outside page')
        categories = tuple(
            (kind, tuple(sorted(i for i in connected if i in symbols and symbols[i].kind == kind)))
            for kind in sorted({symbols[i].kind for i in connected if i in symbols})
        )
        region = union(symbols[i].geometry.region for i in connected if i in symbols)
        moves.append(
            NoteMovePlan(
                match.note.id,
                head.id,
                head.page,
                match.note.pitch,
                target_note.pitch,
                steps,
                *point,
                tx,
                ty,
                head.staff,
                match.note.measure,
                match.note.offset,
                match.confidence,
                categories,
                region,
                _swept(region, [dy]),
                tuple(local_blockers),
            )
        )
    move_by_head = {m.source_head_id: m for m in moves}
    beam_kinds = {'beam', 'beam-hook', 'small-beam'}
    group_kinds = beam_kinds | {'head', 'head-chord', 'small-chord', 'stem', 'beam-group'}
    group_edges = {
        'contains',
        'head-stem',
        'chord-stem',
        'beam-stem',
        'beam-head',
        'beam-chord',
        'beam-beam',
    }
    remaining = {s.id for s in symbols.values() if s.kind in beam_kinds}
    groups = []
    while remaining:
        pending, component = [min(remaining)], set()
        while pending:
            ident = pending.pop()
            if ident in component or ident not in symbols or symbols[ident].kind not in group_kinds:
                continue
            component.add(ident)
            pending.extend(graph.neighbors(ident, group_edges))
        beams = tuple(sorted(i for i in component if symbols[i].kind in beam_kinds))
        remaining.difference_update(beams)
        heads = tuple(sorted(i for i in component if symbols[i].kind == 'head'))
        stems = tuple(sorted(i for i in component if symbols[i].kind == 'stem'))
        deltas = tuple(
            (h, move_by_head[h].target_y - move_by_head[h].source_y if h in move_by_head else None)
            for h in heads
        )
        complete = (
            bool(heads)
            and all(d is not None for _, d in deltas)
            and all(symbols[i].geometry.valid for i in component)
        )
        uniform = len({round(d, 8) for _, d in deltas}) == 1 if complete else None
        status = (
            'UNRESOLVED'
            if uniform is None
            else 'UNIFORM_DELTA' if uniform else 'RECONSTRUCT_REQUIRED'
        )
        region = union(symbols[i].geometry.region for i in component)
        groups.append(
            BeamGroupPlan(
                beams[0],
                symbols[beams[0]].page,
                heads,
                stems,
                beams,
                deltas,
                uniform,
                status,
                region,
                _swept(region, [d for _, d in deltas]),
            )
        )
    slurs = []
    for symbol in symbols.values():
        if symbol.kind != 'slur':
            continue
        endpoints = []
        for r in graph.relations:
            if r.kind != 'slur-head' or symbol.id not in (r.source, r.target):
                continue
            head_id = r.target if r.source == symbol.id else r.source
            move = move_by_head.get(head_id)
            side = dict(r.attributes).get('side', 'UNKNOWN')
            endpoints.append(
                (
                    side,
                    head_id,
                    (move.source_x, move.source_y) if move else None,
                    (move.target_x, move.target_y) if move else None,
                    move.target_y - move.source_y if move else None,
                )
            )
        linked = (
            len(endpoints) == 2
            and {e[0] for e in endpoints} == {'LEFT', 'RIGHT'}
            and all(e[4] is not None for e in endpoints)
            and bool(symbol.geometry.curve)
            and not any(
                name in dict(symbol.attributes) for name in ('left-extension', 'right-extension')
            )
        )
        slurs.append(
            SlurPlan(
                symbol.id,
                symbol.page,
                dict(symbol.attributes).get('tie') == 'true',
                symbol.geometry.curve,
                tuple(sorted(endpoints)),
                linked,
                symbol.geometry.region,
                _swept(symbol.geometry.region, [e[4] for e in endpoints]),
            )
        )
    keys = _key_plans(graph, source, target)
    regions = [(m.source_head_id, m.page, m.potential_edit_region) for m in moves]
    regions += [(b.id, b.page, b.potential_edit_region) for b in groups]
    regions += [(s.id, s.page, s.potential_edit_region) for s in slurs]
    regions += [(k.id, k.page, k.region) for k in keys]
    intersections = []
    for ident, page, region in regions:
        for protected in graph.text_protected_regions:
            overlap = _intersection(region, protected.bbox) if page == protected.page else None
            if overlap:
                intersections.append(Intersection(ident, protected.id, page, overlap))
    if matches.unmatched_visual_ids or any(m.status != 'MATCHED' for m in matches.notes):
        blockers.append('semantic/visual correspondence incomplete')
    if any(p.bbox is None for p in graph.text_protected_regions):
        blockers.append('protected text without usable bounds')
    if any(b.status == 'UNRESOLVED' for b in groups):
        blockers.append('beam group membership or geometry unresolved')
    if any(not s.linked for s in slurs):
        blockers.append('slur/tie endpoints or cross-system extensions unresolved')
    if any(k.status != 'MAPPED' for k in keys):
        blockers.append('key-signature regions unresolved')
    if graph.unsupported_constructs:
        blockers.append('unsupported Audiveris constructs retained for review')
    if intersections:
        blockers.append('potential music edits intersect protected text')
    if any(m.blockers for m in moves):
        blockers.append('note-connected geometry/association requires review')
    blockers.append('Phase 1 diagnostic regions are not approved masks; pixel editing is disabled')
    metrics = matches.summary()
    metrics.update(
        protected_region_intersection_count=len(intersections),
        number_of_beam_groups=len(groups),
        uniform_delta_beam_groups=sum(b.uniform_delta is True for b in groups),
        mixed_delta_beam_groups=sum(b.uniform_delta is False for b in groups),
        unresolved_beam_groups=sum(b.uniform_delta is None for b in groups),
        slurs_ties_linked=sum(s.linked for s in slurs),
        slurs_ties_unlinked=sum(not s.linked for s in slurs),
        key_regions_mapped=sum(k.status == 'MAPPED' for k in keys),
        key_regions_unmapped=sum(k.status != 'MAPPED' for k in keys),
        nonfinite_invalid_geometry_count=graph.invalid_geometry_count,
    )
    return LayoutEditPlan(
        1,
        True,
        graph.pages,
        matches,
        tuple(moves),
        tuple(groups),
        tuple(slurs),
        tuple(keys),
        graph.text_protected_regions,
        tuple(sorted(intersections, key=lambda i: (i.edit_id, i.protected_id))),
        tuple(sorted(set(blockers))),
        tuple(sorted(metrics.items())),
    )


def _key_plans(graph, source, target):
    staves = {s.id: s for s in graph.staves}
    keys, covered = [], set()
    for symbol in graph.symbols.values():
        if symbol.kind != 'key':
            continue
        staff = staves.get(symbol.staff)
        measures = [
            m
            for m in graph.measures
            if symbol.id in m.symbol_ids and staff and m.part == staff.part
        ]
        candidates = [
            k
            for k in source.keys
            if len(measures) == 1
            and staff
            and k.part == staff.part
            and k.staff == staff.number
            and k.measure == measures[0].number
        ]
        source_key = candidates[0] if len(candidates) == 1 else None
        targets = [
            k
            for k in target.keys
            if source_key
            and (k.part, k.staff, k.measure_index, k.offset)
            == (source_key.part, source_key.staff, source_key.measure_index, source_key.offset)
        ]
        target_key = targets[0] if len(targets) == 1 else None
        fifths = dict(symbol.attributes).get('fifths')
        mapped = (
            source_key is not None
            and target_key is not None
            and fifths == str(source_key.fifths)
            and symbol.geometry.region is not None
        )
        members = tuple(
            sorted(
                {symbol.id}
                | {
                    r.target
                    for r in graph.relations
                    if r.kind == 'contains' and r.source == symbol.id
                }
            )
        )
        keys.append(
            KeySignaturePlan(
                symbol.id,
                symbol.page,
                members,
                staff.part if staff else '',
                staff.number if staff else None,
                measures[0].number if len(measures) == 1 else '',
                source_key.offset if source_key else None,
                source_key.name if source_key else None,
                target_key.name if target_key else None,
                target_key.fifths if target_key else None,
                symbol.geometry.region,
                'MAPPED' if mapped else 'UNMAPPED',
                (
                    'measure/staff/fifths agree'
                    if mapped
                    else 'missing/ambiguous region, bounds or fifths'
                ),
            )
        )
        if mapped:
            covered.add(
                (source_key.part, source_key.staff, source_key.measure_index, source_key.offset)
            )
    for k in source.keys:
        ident = (k.part, k.staff, k.measure_index, k.offset)
        if (k.explicit or k.measure_index == 0) and ident not in covered:
            targets = [
                t for t in target.keys if (t.part, t.staff, t.measure_index, t.offset) == ident
            ]
            t = targets[0] if len(targets) == 1 else None
            keys.append(
                KeySignaturePlan(
                    f'semantic-key:{ident}',
                    None,
                    (),
                    k.part,
                    k.staff,
                    k.measure,
                    k.offset,
                    k.name,
                    t.name if t else None,
                    t.fifths if t else None,
                    None,
                    'UNMAPPED',
                    'semantic key region has no confirmed visual object (including empty C-major signatures)',
                )
            )
    return keys
