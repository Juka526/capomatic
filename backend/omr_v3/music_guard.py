"""Post-transposition integrity check.

Adapted from the V3 completion package (``omr_v3_final/music_guard.py``). It
compares the two files a user actually receives — ``recognized.musicxml`` and
``transposed.musicxml`` — and proves the transposition/export stage changed
nothing it should not have:

* same measure count, and per measure the same notes/rests with the same durations;
* every sounding pitch moved by exactly the requested interval (key mode) or
  not at all (capo mode);
* chord symbols kept per measure, root and bass moved by the shift (mod 12);
* key signatures equal to the region targets in the transposition summary.

It says nothing about recognition accuracy; it isolates errors this pipeline
itself would introduce. A failure is returned to the caller as an error, never
as a normal result.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from fractions import Fraction

from backend.chords.parser import parse_chord
from .chords import chord_text
from backend.chords.transpose import compute_target_key
from .transpose import _region_key

_FIFTHS = {'Cb': -7, 'Gb': -6, 'Db': -5, 'Ab': -4, 'Eb': -3, 'Bb': -2, 'F': -1, 'C': 0,
           'G': 1, 'D': 2, 'A': 3, 'E': 4, 'B': 5, 'F#': 6, 'C#': 7}


@dataclass
class GuardReport:
    ok: bool = True
    measures: tuple[int, int] = (0, 0)
    events: tuple[int, int] = (0, 0)
    chords: tuple[int, int] = (0, 0)
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def fail(self, issue: str) -> None:
        self.ok = False
        if len(self.issues) < 20:
            self.issues.append(issue)


def _measure_content(score):
    from music21 import harmony, key, stream

    out = []
    for m in score.parts[0].getElementsByClass(stream.Measure):
        events, chords, keys = [], [], []
        for el in m.recurse():
            if isinstance(el, harmony.ChordSymbol):
                root, bass = el.root(), el.bass()
                parsed = parse_chord(chord_text(el))
                semantics = (parsed.quality, parsed.extensions,
                             tuple(sorted((d.modType, d.degree, d.interval.chromatic.semitones)
                                          for d in el.getChordStepModifications())), el.chordKind)
                slash = parsed.bass is not None
                chords.append((Fraction(el.getOffsetInHierarchy(m)).limit_denominator(64),
                               root.pitchClass if root else None, bass.pitchClass if bass else None, slash, semantics))
            elif isinstance(el, key.KeySignature):
                keys.append(el.sharps)
            elif getattr(el, 'isNote', False) or getattr(el, 'isRest', False) or getattr(el, 'isChord', False):
                if el.isRest:
                    midis: tuple[int, ...] = ()
                elif el.isChord:
                    midis = tuple(sorted(p.midi for p in el.pitches))
                else:
                    midis = (el.pitch.midi,)
                events.append((Fraction(el.getOffsetInHierarchy(m)).limit_denominator(64),
                               Fraction(el.quarterLength).limit_denominator(64), midis))
        out.append((m.measureNumberWithSuffix(), sorted(events), sorted(chords, key=lambda c: c[0]), keys))
    return out


def validate(original, transposed, semitones: int, mode: str, summary: dict | None = None) -> GuardReport:
    """Compare a recognised score with its transposed version."""
    report = GuardReport()
    try:
        a, b = _measure_content(original), _measure_content(transposed)
    except (ValueError, TypeError, AttributeError, IndexError):
        report.fail('unreadable chord or score semantics')
        return report
    report.measures = (len(a), len(b))
    report.events = (sum(len(x[1]) for x in a), sum(len(x[1]) for x in b))
    report.chords = (sum(len(x[2]) for x in a), sum(len(x[2]) for x in b))
    if len(a) != len(b):
        report.fail(f'measure count changed {len(a)} -> {len(b)}')
    pitch_shift = semitones if mode == 'key' else 0
    chord_shift = semitones % 12
    source_fifths = 0
    for index, ((num, ev_a, ch_a, ks_a), (_, ev_b, ch_b, ks_b)) in enumerate(zip(a, b)):
        if ks_a:
            source_fifths = ks_a[-1]
        original_key = _region_key(source_fifths)
        expected = compute_target_key(original_key, semitones) if mode == 'key' else original_key
        if ((index == 0 or ks_a) and not ks_b) or any(k != _FIFTHS[expected] for k in ks_b):
            report.fail(f'bar {num}: key signature missing or inconsistent with requested shift')
        if len(ev_a) != len(ev_b):
            report.fail(f'bar {num}: {len(ev_a)} -> {len(ev_b)} notes/rests')
            continue
        for (oa, la, pa), (ob, lb, pb) in zip(ev_a, ev_b):
            if oa != ob or la != lb:
                report.fail(f'bar {num}: rhythm changed at {oa}')
            elif len(pa) != len(pb) or any(y - x != pitch_shift for x, y in zip(pa, pb)):
                report.fail(f'bar {num}: pitch moved by an unexpected interval at {oa}')
        if len(ch_a) != len(ch_b):
            report.fail(f'bar {num}: {len(ch_a)} -> {len(ch_b)} chord symbols')
            continue
        for (oa, ra, ba, sa, qa), (ob, rb, bb, sb, qb) in zip(ch_a, ch_b):
            if sa != sb or qa != qb:
                report.fail(f'bar {num}: chord semantics changed at {oa}')
            if oa != ob or ra is None or rb is None or (rb - ra) % 12 != chord_shift:
                report.fail(f'bar {num}: chord root moved wrongly at {oa}')
            elif ba is not None and bb is not None and (bb - ba) % 12 != chord_shift:
                report.fail(f'bar {num}: chord bass moved wrongly at {oa}')
    if summary and summary.get('keys'):
        wanted = {r['measure']: r['target'] for r in summary['keys']}
        for num, _, _, ks in b:
            try:
                n = int(''.join(ch for ch in str(num) if ch.isdigit() or ch == '-'))
            except ValueError:
                continue
            if n in wanted:
                target = _FIFTHS.get(wanted[n])
                if target is None or not ks or any(k != target for k in ks):
                    report.fail(f'bar {num}: missing or incorrect target key signature')
            elif ks:
                prior = [m for m in wanted if m <= n]
                if not prior or any(k != _FIFTHS.get(wanted[max(prior)]) for k in ks):
                    report.fail(f'bar {num}: key signature contradicts region target')
        observed = {int(str(num)) for num, _, _, _ in b if str(num).lstrip('-').isdigit()}
        if set(wanted) - observed:
            report.fail('key region references a missing measure')
    return report
