"""Exact ownership lineage across the unchanged V3 ledger-repair boundary."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, fields, replace

from .matcher import MatchResult, NoteMatch, SemanticNote, SemanticScore, match_notes
from .visual_graph import VisualScoreGraph

LEDGER_REPAIR = 'V3_LEDGER_REPAIR'
_PITCH_FIELDS = {'pitch', 'diatonic_number', 'staff_pitch'}


@dataclass(frozen=True)
class RepairProvenance:
    raw_event: SemanticNote
    repaired_event: SemanticNote
    repair_kind: str
    changed_fields: tuple[str, ...]
    source_head_id: str | None
    raw_match_status: str
    reason: str = 'Captured around unchanged V3 cleanup.fix_missed_ledgers'


def _changes(raw: SemanticNote, repaired: SemanticNote) -> tuple[str, ...]:
    return tuple(f.name for f in fields(raw) if getattr(raw, f.name) != getattr(repaired, f.name))


def capture_ledger_repairs(
    raw: SemanticScore, repaired: SemanticScore, raw_matches: MatchResult, repair_count: int
) -> tuple[RepairProvenance, ...]:
    """Record only an identity-preserving, count-consistent observed repair batch.

    Call immediately around the actual V3 function, never on arbitrary historical
    scores. Unsupported transformations yield no authorization records. The raw
    match was established before the repair; no pitch correction is reimplemented.
    """
    if (
        len(raw.notes) != len(repaired.notes)
        or tuple(m.note for m in raw_matches.notes) != raw.notes
        or len({n.id for n in raw.notes}) != len(raw.notes)
        or len({n.id for n in repaired.notes}) != len(repaired.notes)
    ):
        return ()
    records = []
    for a, b, match in zip(raw.notes, repaired.notes, raw_matches.notes):
        changed = _changes(a, b)
        if not changed:
            continue
        if (
            a.id != b.id
            or a.identity != b.identity
            or not set(changed) <= _PITCH_FIELDS
            or 'pitch' not in changed
        ):
            return ()
        records.append(RepairProvenance(a, b, LEDGER_REPAIR, changed, match.head_id, match.status))
    return tuple(records) if len(records) == repair_count else ()


def match_with_provenance(
    raw: SemanticScore,
    repaired: SemanticScore,
    graph: VisualScoreGraph,
    raw_matches: MatchResult,
    provenance: tuple[RepairProvenance, ...],
) -> MatchResult:
    """Transfer a preexisting unique ownership, without relaxing direct matching.

    All raw/corrected event and record identities are checked, then ALL candidate
    head claims are reconciled, including collisions with direct/ambiguous matches.
    A changed event without a valid explicit record cannot fall back to a new head.
    """
    direct = match_notes(repaired, graph)
    raw_notes = {n.id: n for n in raw.notes}
    evidence = {m.note.id: m for m in raw_matches.notes}
    raw_counts = Counter(n.id for n in raw.notes)
    repaired_counts = Counter(n.id for n in repaired.notes)
    raw_claims = Counter(h for m in raw_matches.notes for h in m.candidate_ids)
    record_sources = Counter(p.raw_event.id for p in provenance)
    record_targets = Counter(p.repaired_event.id for p in provenance)
    record_heads = Counter(p.source_head_id for p in provenance if p.source_head_id)
    input_valid = tuple(
        m.note for m in raw_matches.notes
    ) == raw.notes and raw_matches == match_notes(raw, graph)
    results = []
    for result in direct.notes:
        note = result.note
        original = raw_notes.get(note.id)
        records = [p for p in provenance if p.repaired_event.id == note.id]
        if original == note and not records:
            results.append(result)
            continue
        previous = evidence.get(original.id) if original else None
        record = records[0] if len(records) == 1 else None
        valid = (
            input_valid
            and original is not None
            and previous is not None
            and record is not None
            and raw_counts[original.id] == repaired_counts[note.id] == 1
            and record_sources[original.id] == record_targets[note.id] == 1
            and record.raw_event == original
            and record.repaired_event == note
            and original.id == note.id
            and original.identity == note.identity
            and record.repair_kind == LEDGER_REPAIR
            and record.changed_fields == _changes(original, note)
            and bool(record.changed_fields)
            and set(record.changed_fields) <= _PITCH_FIELDS
            and 'pitch' in record.changed_fields
            and previous.status == record.raw_match_status == 'MATCHED'
            and previous.head_id == record.source_head_id
            and previous.head_id is not None
            and previous.candidate_ids == (previous.head_id,)
            and raw_claims[previous.head_id] == record_heads[previous.head_id] == 1
            and previous.head_id in graph.symbols
            and graph.symbols[previous.head_id].kind == 'head'
        )
        if valid:
            results.append(
                NoteMatch(
                    note,
                    'MATCHED',
                    previous.head_id,
                    previous.candidate_ids,
                    previous.confidence,
                    ('Unique raw ownership inherited through captured V3 ledger repair',),
                    'REPAIRED_PROVENANCE',
                    record,
                )
            )
        else:
            candidates = tuple(
                sorted(set(result.candidate_ids) | set(previous.candidate_ids if previous else ()))
            )
            ambiguous = bool(previous and previous.status == 'AMBIGUOUS') or len(records) > 1
            results.append(
                NoteMatch(
                    note,
                    'AMBIGUOUS' if ambiguous else 'UNMATCHED',
                    None,
                    candidates,
                    0.0,
                    (
                        'Ownership transfer rejected: missing, ambiguous or incompatible repair provenance',
                    ),
                )
            )
    claims = Counter(h for m in results for h in m.candidate_ids)
    final = []
    for result in results:
        if result.head_id and claims[result.head_id] != 1:
            result = replace(
                result,
                status='AMBIGUOUS',
                head_id=None,
                confidence=0.0,
                ownership_basis=None,
                provenance=None,
                reasons=('Head ownership collision after direct/provenance reconciliation',),
            )
        final.append(result)
    used = {m.head_id for m in final if m.status == 'MATCHED'}
    heads = {s.id for s in graph.symbols.values() if s.kind == 'head'}
    return MatchResult(tuple(final), tuple(sorted(heads - used)))
