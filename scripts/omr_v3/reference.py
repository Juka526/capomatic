"""Build reference MusicXML from the hand transcriptions in tests/omr_v3_eval/reference/*.gt.

The .gt format is deliberately tiny so a reviewer can check it bar by bar against the
printed score:

    title: <text>
    key: <fifths>            (may also appear as "key: <fifths>" inside a line "@key=<fifths>")
    time: 4/4
    <measure> | <Chord@offset ...> | <note ...>

Note tokens: ``<pitch>/<len>`` with pitch like ``A4``, ``Bb4``, ``F#4`` or ``r`` for a rest;
len 1/2/4/8/16/32 plus optional ``.`` (dotted); a trailing ``~`` ties into the next note.
Measure options in the chord field: ``key=<fifths>``, ``time=2/4``.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

_NOTE_RE = re.compile(r'^(r|[A-G](?:#|b|bb|##)?\d)/(\d+)(\.{0,2})(~?)$')


@dataclass
class RefMeasure:
    number: int
    chords: list[tuple[str, Fraction]]
    notes: list[tuple[str | None, Fraction, bool]]  # pitch (None = rest), quarterLength, tie-start
    key: int | None = None
    time: str | None = None
    barline: str | None = None


@dataclass
class RefScore:
    title: str
    key: int
    time: str
    measures: list[RefMeasure] = field(default_factory=list)


def _length(den: str, dots: str) -> Fraction:
    base = Fraction(4, int(den))
    total, add = base, base
    for _ in dots:
        add /= 2
        total += add
    return total


def parse_gt(text: str) -> RefScore:
    header: dict[str, str] = {}
    measures: list[RefMeasure] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if '|' not in line:
            k, _, v = line.partition(':')
            header[k.strip()] = v.strip()
            continue
        num, chord_field, note_field = (part.strip() for part in line.split('|', 2))
        m = RefMeasure(int(num), [], [])
        for tok in chord_field.split():
            if tok.startswith('key='):
                m.key = int(tok[4:])
            elif tok.startswith('time='):
                m.time = tok[5:]
            elif tok.startswith('bar='):
                m.barline = tok[4:]
            else:
                name, _, off = tok.rpartition('@')
                m.chords.append((name, Fraction(off)))
        for tok in note_field.split():
            mt = _NOTE_RE.match(tok)
            if not mt:
                raise ValueError(f'measure {num}: bad note token {tok!r}')
            pitch = None if mt.group(1) == 'r' else mt.group(1)
            m.notes.append((pitch, _length(mt.group(2), mt.group(3)), bool(mt.group(4))))
        measures.append(m)
    return RefScore(header.get('title', ''), int(header.get('key', 0)), header.get('time', '4/4'), measures)


def check(ref: RefScore) -> list[str]:
    """Return bar-length problems (pickup and final bars may be short)."""
    problems = []
    time = ref.time
    for i, m in enumerate(ref.measures):
        time = m.time or time
        num, den = (int(x) for x in time.split('/'))
        expected = Fraction(num * 4, den)
        total = sum((n[1] for n in m.notes), Fraction(0))
        if total != expected and not (i == 0 or i == len(ref.measures) - 1 or m.barline == 'partial'):
            problems.append(f'measure {m.number}: {total} quarters, expected {expected}')
        for (name, off) in m.chords:
            if off >= max(total, expected):
                problems.append(f'measure {m.number}: chord {name} offset {off} outside bar')
    return problems


def to_music21(ref: RefScore):
    from music21 import bar, harmony, key, metadata, meter, note, stream, tie

    from backend.omr_v3.chords import chord_symbol_from_text

    part = stream.Part()
    pending_tie = False
    time = ref.time
    for i, m in enumerate(ref.measures):
        meas = stream.Measure(number=m.number)
        if i == 0:
            meas.insert(0, key.KeySignature(ref.key))
            meas.insert(0, meter.TimeSignature(ref.time))
        if m.key is not None:
            meas.insert(0, key.KeySignature(m.key))
        if m.time is not None:
            meas.insert(0, meter.TimeSignature(m.time))
            time = m.time
        offset = Fraction(0)
        for pitch, ql, tie_start in m.notes:
            el = note.Rest(quarterLength=ql) if pitch is None else note.Note(pitch[0] + pitch[1:].replace('b', '-'), quarterLength=ql)
            if pitch is not None:
                if pending_tie and tie_start:
                    el.tie = tie.Tie('continue')
                elif pending_tie:
                    el.tie = tie.Tie('stop')
                elif tie_start:
                    el.tie = tie.Tie('start')
                pending_tie = tie_start
            meas.insert(offset, el)
            offset += ql
        for name, off in m.chords:
            meas.insert(off, chord_symbol_from_text(name))
        if m.barline:
            meas.rightBarline = bar.Barline(m.barline)
        part.append(meas)
    if ref.measures and ref.measures[0].notes:
        first = part.getElementsByClass(stream.Measure).first()
        num, den = (int(x) for x in ref.time.split('/'))
        if first.duration.quarterLength < num * 4 / den:
            first.paddingLeft = num * 4 / den - first.duration.quarterLength
    score = stream.Score()
    score.metadata = metadata.Metadata(title=ref.title)
    score.insert(0, part)
    return score


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('gt', type=Path, nargs='+')
    ap.add_argument('--out', type=Path, help='directory for <name>.musicxml')
    args = ap.parse_args()
    bad = False
    for path in args.gt:
        ref = parse_gt(path.read_text(encoding='utf-8'))
        problems = check(ref)
        notes = sum(1 for m in ref.measures for n in m.notes if n[0])
        chords = sum(len(m.chords) for m in ref.measures)
        print(f'{path.stem}: {len(ref.measures)} measures, {notes} notes, {chords} chords, problems={len(problems)}')
        for p in problems:
            print('  ', p)
        bad |= bool(problems)
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
            to_music21(ref).write('musicxml', fp=str(args.out / f'{path.stem}.musicxml'))
    raise SystemExit(1 if bad else 0)


if __name__ == '__main__':
    main()
