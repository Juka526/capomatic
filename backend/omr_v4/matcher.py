"""Conservative semantic-to-SIG matching; uncertainty is an output, not a guess."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import re
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .provenance import RepairProvenance

from .visual_graph import GraphError, MAX_XML_BYTES, VisualScoreGraph, safe_xml


@dataclass(frozen=True)
class SemanticNote:
    id: str
    part: str
    source_part_id: str
    measure: str
    measure_index: int
    staff: int
    voice: str | None
    offset: Fraction
    duration: Fraction
    pitch: str
    diatonic_number: int
    staff_pitch: int | None
    chord: str
    chord_size: int
    member: int
    grace: bool

    @property
    def identity(self) -> tuple:
        return (
            self.part,
            self.measure,
            self.measure_index,
            self.staff,
            self.voice,
            self.offset,
            self.duration,
            self.chord,
            self.chord_size,
            self.member,
            self.grace,
        )


@dataclass(frozen=True)
class SemanticKey:
    part: str
    measure: str
    measure_index: int
    staff: int
    offset: Fraction
    fifths: int
    name: str
    explicit: bool


@dataclass(frozen=True)
class SemanticScore:
    notes: tuple[SemanticNote, ...]
    keys: tuple[SemanticKey, ...]


@dataclass(frozen=True)
class NoteMatch:
    note: SemanticNote
    status: Literal['MATCHED', 'AMBIGUOUS', 'UNMATCHED']
    head_id: str | None
    candidate_ids: tuple[str, ...]
    confidence: float
    reasons: tuple[str, ...]
    ownership_basis: Literal['DIRECT', 'REPAIRED_PROVENANCE'] | None = None
    provenance: RepairProvenance | None = None


@dataclass(frozen=True)
class MatchResult:
    notes: tuple[NoteMatch, ...]
    unmatched_visual_ids: tuple[str, ...]

    def summary(self) -> dict:
        """Count every pitched note and every unused visual head."""
        counts = Counter(m.status for m in self.notes)
        return {
            'semantic_pitched_note_count': len(self.notes),
            'visual_head_count': counts['MATCHED'] + len(self.unmatched_visual_ids),
            'matched_count': counts['MATCHED'],
            'direct_matches': sum(
                m.status == 'MATCHED' and m.ownership_basis == 'DIRECT' for m in self.notes
            ),
            'provenance_matches': sum(
                m.status == 'MATCHED' and m.ownership_basis == 'REPAIRED_PROVENANCE'
                for m in self.notes
            ),
            'ambiguous_count': counts['AMBIGUOUS'],
            'unmatched_semantic_count': counts['UNMATCHED'],
            'unmatched_visual_count': len(self.unmatched_visual_ids),
            'match_rate': counts['MATCHED'] / len(self.notes) if self.notes else None,
        }


def read_semantics(path: Path) -> SemanticScore:
    """Extract written MusicXML events with exact rational timing and staff IDs.

    Clefs, voices, backup/forward, chords and per-staff key changes are read from
    the exported XML, avoiding music21 PartStaff flattening and generated IDs.
    Pitch names/diatonic numbers come from music21, never a V4 spelling policy.
    """
    from music21 import key, pitch
    from dataclasses import replace

    if path.stat().st_size > MAX_XML_BYTES:
        raise GraphError('MusicXML too large')
    root = safe_xml(path.read_bytes(), musicxml=True)
    if root.tag != 'score-partwise':
        raise GraphError('Only score-partwise MusicXML is supported')
    notes, keys = [], []
    parts = root.findall('part')
    if len({p.get('id') for p in parts}) != len(parts):
        raise GraphError('Duplicate MusicXML part ID')
    for part_index, part in enumerate(parts, 1):
        logical = re.fullmatch(r'P([1-9][0-9]*)', part.get('id', ''))
        part_id = (
            logical.group(1) if logical else '1' if len(parts) == 1 else f'unresolved:{part_index}'
        )
        divisions = Fraction(1)
        clefs, key_state = {}, {1: 0}
        staff_count = 1
        for mi, measure in enumerate(part.findall('measure')):
            number = measure.get('number', '')
            cursor, previous_onset, chord_id = Fraction(0), Fraction(0), None
            explicit_keys = set()
            initial_keys = dict(key_state)
            measure_notes = []
            for element in measure:
                if element.tag == 'attributes':
                    if element.find('divisions') is not None:
                        divisions = Fraction(element.findtext('divisions'))
                        if divisions <= 0:
                            raise GraphError('Invalid MusicXML divisions')
                    staff_count = int(element.findtext('staves', str(staff_count)))
                    for clef in element.findall('clef'):
                        staff = int(clef.get('number', '1'))
                        sign, line = clef.findtext('sign'), int(clef.findtext('line', '0'))
                        octave = int(clef.findtext('clef-octave-change', '0'))
                        ref = {'G': 33, 'F': 25, 'C': 29}.get(sign)
                        clefs[staff] = (
                            ref + 2 * (3 - line) + 7 * octave
                            if ref is not None and 1 <= line <= 5
                            else None
                        )
                    for ks in element.findall('key'):
                        fifths_text = ks.findtext('fifths')
                        if fifths_text is None:
                            raise GraphError('Nontraditional key signature is unsupported')
                        fifths = int(fifths_text)
                        if not -7 <= fifths <= 7:
                            raise GraphError('Unsupported key fifths')
                        targets = (
                            [int(ks.get('number'))]
                            if ks.get('number')
                            else range(1, staff_count + 1)
                        )
                        for staff in targets:
                            key_state[staff] = fifths
                            explicit_keys.add((staff, cursor))
                            keys.append(
                                SemanticKey(
                                    part_id,
                                    number,
                                    mi,
                                    staff,
                                    cursor,
                                    fifths,
                                    key.KeySignature(fifths).asKey('major').tonic.name,
                                    True,
                                )
                            )
                elif element.tag in {'backup', 'forward'}:
                    delta = Fraction(element.findtext('duration', '0')) / divisions
                    if delta < 0:
                        raise GraphError('Negative MusicXML duration')
                    cursor += delta if element.tag == 'forward' else -delta
                    if cursor < 0:
                        raise GraphError('MusicXML backup before measure start')
                    chord_id = None
                elif element.tag == 'note':
                    duration = Fraction(element.findtext('duration', '0')) / divisions
                    if duration < 0:
                        raise GraphError('Negative note duration')
                    is_chord = element.find('chord') is not None
                    onset = previous_onset if is_chord else cursor
                    if not is_chord:
                        previous_onset = cursor
                        chord_id = f'p{part_index}:m{mi}:e{len(measure_notes)}'
                        cursor += duration
                    elif chord_id is None:
                        raise GraphError('Chord member without leading event')
                    p = element.find('pitch')
                    if p is None:
                        continue
                    staff = int(element.findtext('staff', '1'))
                    voice = element.findtext('voice')
                    step, octave = p.findtext('step'), int(p.findtext('octave'))
                    alter = Fraction(p.findtext('alter', '0'))
                    if (
                        step not in {'C', 'D', 'E', 'F', 'G', 'A', 'B'}
                        or not -1 <= octave <= 10
                        or alter.denominator != 1
                        or abs(alter) > 2
                    ):
                        raise GraphError('Unsupported written pitch')
                    pp = pitch.Pitch(step + str(octave))
                    pp.accidental = int(alter)
                    dnn = pp.diatonicNoteNum
                    mid = clefs.get(staff)
                    measure_notes.append(
                        SemanticNote(
                            f'p{part_index}:m{mi}:n{len(measure_notes)}',
                            part_id,
                            part.get('id', ''),
                            number,
                            mi,
                            staff,
                            voice,
                            onset,
                            duration,
                            pp.nameWithOctave,
                            dnn,
                            mid - dnn if mid is not None else None,
                            chord_id,
                            1,
                            0,
                            element.find('grace') is not None,
                        )
                    )
            counts = Counter(n.chord for n in measure_notes)
            members = Counter()
            for n in measure_notes:
                notes.append(replace(n, chord_size=counts[n.chord], member=members[n.chord]))
                members[n.chord] += 1
            for staff in range(1, staff_count + 1):
                if (staff, Fraction(0)) not in explicit_keys:
                    fifths = initial_keys.get(staff, 0)
                    keys.append(
                        SemanticKey(
                            part_id,
                            number,
                            mi,
                            staff,
                            Fraction(0),
                            fifths,
                            key.KeySignature(fifths).asKey('major').tonic.name,
                            False,
                        )
                    )
    return SemanticScore(
        tuple(notes),
        tuple(sorted(keys, key=lambda k: (k.part, k.measure_index, k.staff, k.offset))),
    )


def match_notes(semantic: SemanticScore, graph: VisualScoreGraph) -> MatchResult:
    """Match unique measure/staff/slot/chord/pitch evidence, then enforce bijection.

    X ordering and OCR grades describe candidates; neither breaks a tie between
    equivalent musical candidates. Voice IDs remain advisory until their export
    correspondence is proven. No nearest-point fallback exists.
    """
    heads = {k: s for k, s in graph.symbols.items() if s.kind == 'head'}
    staff_by_id = {s.id: s for s in graph.staves}
    children = {}
    for relation in graph.relations:
        if relation.kind == 'contains':
            children.setdefault(relation.source, set()).add(relation.target)
    chord_heads = {
        k: sorted(v & heads.keys())
        for k, v in children.items()
        if k in graph.symbols and graph.symbols[k].kind in {'head-chord', 'small-chord'}
    }
    memberships = {h: [c for c, members in chord_heads.items() if h in members] for h in heads}
    semantic_chords = {}
    for note in semantic.notes:
        semantic_chords.setdefault(note.chord, []).append(note)
    results = []
    for note in semantic.notes:
        candidates, verified, reasons = set(), set(), set()
        measures = [m for m in graph.measures if m.part == note.part and m.number == note.measure]
        if note.grace:
            reasons.add('grace timing unsupported')
        if note.staff_pitch is None:
            reasons.add('missing/unsupported clef')
        if note.part.startswith('unresolved:'):
            reasons.add('multi-part ID correspondence not established; ordinal matching disabled')
        if not measures:
            reasons.add('no measure/stack ID correspondence')
        # Repeated page-local bar numbers or split stacks require explicit mapping.
        measure_unique = len(measures) == 1
        if not measure_unique and measures:
            reasons.add('multiple visual measures share semantic number')
        for measure in measures:
            if measure.bounds is None:
                reasons.add('invalid/missing measure geometry')
                continue
            slots = {s.id: s for s in measure.slots}
            for chord_id in measure.symbol_ids:
                if chord_id not in chord_heads:
                    continue
                members = chord_heads[chord_id]
                onsets = [o for o in measure.onsets if o[0] == chord_id]
                onset_slots = [slots[o[1]] for o in onsets if o[1] in slots]
                known = len(onsets) == len(onset_slots) == 1
                slot = onset_slots[0] if known else None
                if slot is not None and slot.offset is not None and slot.offset != note.offset:
                    continue
                expected = sorted((n.staff, n.staff_pitch) for n in semantic_chords[note.chord])
                observed = []
                for head_id in members:
                    head = heads[head_id]
                    staff = staff_by_id.get(head.staff)
                    if staff:
                        observed.append((staff.number, head.pitch_position))
                chord_agrees = len(observed) == len(members) == len(children[chord_id]) and sorted(
                    observed, key=repr
                ) == sorted(expected, key=repr)
                for head_id in members:
                    head = heads[head_id]
                    staff = staff_by_id.get(head.staff)
                    if staff is None or staff.part != note.part or staff.number != note.staff:
                        continue
                    if not staff.valid or not head.geometry.valid or head.geometry.center is None:
                        reasons.add('invalid/missing head or staff geometry')
                        continue
                    if note.staff_pitch is not None and head.pitch_position != note.staff_pitch:
                        continue
                    candidates.add(head_id)
                    if (
                        known
                        and slot.offset is not None
                        and slot.x is not None
                        and not slot.suspicious
                        and chord_agrees
                        and len(memberships[head_id]) == 1
                        and measure_unique
                        and note.staff_pitch is not None
                        and not note.grace
                    ):
                        verified.add(head_id)
                    else:
                        reasons.add(
                            'incomplete/conflicting slot, chord, pitch or membership evidence'
                        )
        ordered = tuple(sorted(candidates, key=lambda h: (heads[h].geometry.center[0], h)))
        # Even one strong candidate cannot hide a second plausible incomplete one.
        accepted = len(candidates) == len(verified) == 1
        head_id = next(iter(verified)) if accepted else None
        status = 'MATCHED' if accepted else 'AMBIGUOUS' if candidates else 'UNMATCHED'
        if accepted:
            reasons = {
                'unique measure + staff + BEGIN slot + complete chord pitch membership',
                'x ordering recorded; confidence is Audiveris grade, not calibrated probability',
                'voice IDs advisory; chromatic spelling comes from recognized MusicXML',
            }
        elif not reasons:
            reasons.add('no head satisfies measure/staff/slot/source staff pitch')
        results.append(
            NoteMatch(
                note,
                status,
                head_id,
                ordered,
                heads[head_id].confidence if head_id else 0.0,
                tuple(sorted(reasons)),
                'DIRECT' if accepted else None,
            )
        )
    claims = Counter(h for r in results for h in r.candidate_ids)
    final = []
    for result in results:
        if result.head_id and claims[result.head_id] > 1:
            result = NoteMatch(
                result.note,
                'AMBIGUOUS',
                None,
                result.candidate_ids,
                0.0,
                ('visual head claimed by multiple semantic notes; no greedy assignment',),
            )
        final.append(result)
    used = {r.head_id for r in final if r.status == 'MATCHED'}
    return MatchResult(tuple(final), tuple(sorted(heads.keys() - used)))
