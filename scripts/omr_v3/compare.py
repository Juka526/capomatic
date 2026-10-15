"""Compare a candidate MusicXML against a hand-made reference.

Metrics (all relative to the reference):

* notes: global edit-distance alignment of note/rest events (pitch, length).
  ``note_exact`` = reference events matched with correct pitch AND length;
  ``pitch_acc`` / ``rhythm_acc`` = correct pitch / length among aligned pairs
  counted over all reference events; ``ser`` = (S+D+I)/N symbol error rate.
* chords: (measure, beat offset, canonical text) triples; a hit needs the same
  measure, offset within 1/2 beat and identical text. Precision and recall.
* keys / time: per-bar key signature and time signature in effect.

Usage: python -m scripts.omr_v3.compare REF.gt CANDIDATE.musicxml [--semitones N --mode key|capo]
The reference is transposed independently for the comparison: notes with
music21's own ``Score.transpose`` (diatonic interval named explicitly) and
chords with V1's ``transpose_chord``.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


@dataclass(frozen=True)
class Event:
    measure: int
    offset: Fraction
    pitch: str | None   # spelled name with octave, None for rests
    midi: int | None
    length: Fraction


def _frac(x) -> Fraction:
    return Fraction(x).limit_denominator(64)


def extract(score) -> dict:
    """Events, chords, keys and time signatures per bar (first part, voice 1)."""
    from music21 import harmony, key, meter, note, stream

    from backend.omr_v3.chords import canonical, chord_text

    part = score.parts[0]
    events: list[Event] = []
    chords: list[tuple[int, Fraction, str]] = []
    keys: list[int] = []
    times: list[str] = []
    fifths, ts = None, None
    for i, m in enumerate(part.getElementsByClass(stream.Measure)):
        for ks in m.getElementsByClass(key.KeySignature):
            fifths = ks.sharps
        for t in m.getElementsByClass(meter.TimeSignature):
            ts = t.ratioString
        keys.append(fifths if fifths is not None else 0)
        times.append(ts or '?')
        voice = m.voices[0] if m.voices else m
        for n in voice.notesAndRests:
            if isinstance(n, harmony.ChordSymbol):
                continue
            if n.isRest:
                events.append(Event(i, _frac(n.offset), None, None, _frac(n.quarterLength)))
            elif isinstance(n, note.Note):
                events.append(Event(i, _frac(n.offset), n.pitch.nameWithOctave, n.pitch.midi, _frac(n.quarterLength)))
            else:  # chord of notes: OMR merged heads; score the top note
                p = max(n.pitches, key=lambda p: p.midi)
                events.append(Event(i, _frac(n.offset), p.nameWithOctave, p.midi, _frac(n.quarterLength)))
        for cs in m.recurse().getElementsByClass(harmony.ChordSymbol):
            try:
                chords.append((i, _frac(cs.getOffsetInHierarchy(m)), canonical(chord_text(cs))))
            except ValueError:
                chords.append((i, _frac(cs.getOffsetInHierarchy(m)), '?'))
    return {'events': events, 'chords': chords, 'keys': keys, 'times': times}


def _align(ref: list[Event], cand: list[Event]):
    """Levenshtein alignment; substitution cost 1 unless pitch and length both match."""
    n, m = len(ref), len(cand)
    cost = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        cost[i][0] = i
    for j in range(1, m + 1):
        cost[0][j] = j

    def sub(a: Event, b: Event) -> float:
        if a.pitch == b.pitch and a.length == b.length:
            return 0
        if a.pitch == b.pitch or a.length == b.length or (a.midi is not None and a.midi == b.midi):
            return 0.6
        return 1

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost[i][j] = min(cost[i - 1][j] + 1, cost[i][j - 1] + 1,
                             cost[i - 1][j - 1] + sub(ref[i - 1], cand[j - 1]))
    pairs, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and cost[i][j] == cost[i - 1][j - 1] + sub(ref[i - 1], cand[j - 1]):
            pairs.append((i - 1, j - 1)); i -= 1; j -= 1
        elif i > 0 and cost[i][j] == cost[i - 1][j] + 1:
            pairs.append((i - 1, None)); i -= 1
        else:
            pairs.append((None, j - 1)); j -= 1
    return pairs[::-1]


def compare(ref_score, cand_score) -> dict:
    ref, cand = extract(ref_score), extract(cand_score)
    pairs = _align(ref['events'], cand['events'])
    n = len(ref['events'])
    exact = pitch_ok = len_ok = subs = dels = ins = 0
    measure_votes: dict[int, dict[int, int]] = {}
    diffs = []
    for a, b in pairs:
        if a is not None and b is not None:
            ra, cb = ref['events'][a], cand['events'][b]
            p_ok = ra.pitch == cb.pitch
            l_ok = ra.length == cb.length
            pitch_ok += p_ok
            len_ok += l_ok
            exact += p_ok and l_ok
            if not (p_ok and l_ok):
                subs += 1
                diffs.append({'ref_measure': ra.measure, 'offset': str(ra.offset),
                              'expected': f'{ra.pitch or "rest"}/{ra.length}', 'found': f'{cb.pitch or "rest"}/{cb.length}'})
            measure_votes.setdefault(ra.measure, {}).setdefault(cb.measure, 0)
            measure_votes[ra.measure][cb.measure] += 1
        elif a is not None:
            dels += 1
            ra = ref['events'][a]
            diffs.append({'ref_measure': ra.measure, 'offset': str(ra.offset), 'expected': f'{ra.pitch or "rest"}/{ra.length}', 'found': None})
        else:
            ins += 1
            cb = cand['events'][b]
            diffs.append({'cand_measure': cb.measure, 'offset': str(cb.offset), 'expected': None, 'found': f'{cb.pitch or "rest"}/{cb.length}'})
    measure_map = {rm: max(v, key=v.get) for rm, v in measure_votes.items()}
    pitched = [e for e in ref['events'] if e.pitch]

    # Pitched-note-only view (rests excluded), the figure musicians usually quote.
    pitched_pairs = [(a, b) for a, b in pairs if a is not None and ref['events'][a].pitch]
    pn_exact = sum(1 for a, b in pitched_pairs if b is not None
                   and ref['events'][a].pitch == cand['events'][b].pitch
                   and ref['events'][a].length == cand['events'][b].length)
    pn_pitch = sum(1 for a, b in pitched_pairs if b is not None and ref['events'][a].pitch == cand['events'][b].pitch)

    cand_chords = {}
    for cm, off, text in cand['chords']:
        cand_chords.setdefault(cm, []).append((off, text))
    hits = 0
    chord_diffs = []
    for rm, off, text in ref['chords']:
        cm = measure_map.get(rm, rm)
        found = next((t for o, t in cand_chords.get(cm, []) if abs(o - off) <= Fraction(1, 2) and t == text), None)
        if found:
            hits += 1
        else:
            near = [f'{t}@{o}' for o, t in cand_chords.get(cm, [])]
            chord_diffs.append({'ref_measure': rm, 'offset': str(off), 'expected': text, 'found_in_bar': near})
    nr, nc = len(ref['chords']), len(cand['chords'])
    key_ok = sum(1 for i, k in enumerate(ref['keys']) if measure_map.get(i, i) < len(cand['keys']) and cand['keys'][measure_map.get(i, i)] == k)
    time_ok = sum(1 for i, t in enumerate(ref['times']) if measure_map.get(i, i) < len(cand['times']) and cand['times'][measure_map.get(i, i)] == t)
    return {
        'measures': {'reference': len(ref['keys']), 'candidate': len(cand['keys'])},
        'events': {'reference': n, 'candidate': len(cand['events'])},
        'note_exact': round(exact / n, 4) if n else None,
        'pitch_acc': round(pitch_ok / n, 4) if n else None,
        'rhythm_acc': round(len_ok / n, 4) if n else None,
        'pitched_notes': {'reference': len(pitched), 'exact': round(pn_exact / len(pitched), 4) if pitched else None,
                          'pitch': round(pn_pitch / len(pitched), 4) if pitched else None},
        'ser': round((subs + dels + ins) / n, 4) if n else None,
        'ops': {'substitutions': subs, 'deletions': dels, 'insertions': ins},
        'chords': {'reference': nr, 'candidate': nc, 'hits': hits,
                   'recall': round(hits / nr, 4) if nr else None,
                   'precision': round(hits / nc, 4) if nc else None},
        'key_signature_acc': round(key_ok / len(ref['keys']), 4) if ref['keys'] else None,
        'time_signature_acc': round(time_ok / len(ref['times']), 4) if ref['times'] else None,
        'note_diffs': diffs,
        'chord_diffs': chord_diffs,
    }


def _levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def lyric_accuracy(reference: str, score) -> dict | None:
    """Character accuracy of verse-1 lyrics (Hangul only, in note order)."""
    import re

    from music21 import note

    if not reference:
        return None
    sung = []
    for n in score.parts[0].recurse().getElementsByClass(note.Note):
        for ly in n.lyrics:
            if ly.number == 1 and ly.text:
                sung.append(ly.text)
    cand = re.sub(r'[^\uac00-\ud7a3]', '', ''.join(sung))
    ref = re.sub(r'[^\uac00-\ud7a3]', '', reference)
    dist = _levenshtein(ref, cand)
    return {'reference_chars': len(ref), 'candidate_chars': len(cand),
            'char_acc': round(max(0.0, 1 - dist / len(ref)), 4) if ref else None}


def transposed_reference(ref_score, ref_gt, semitones: int, mode: str):
    """Reference transposed without the pipeline's own transposition module."""
    from music21 import harmony, interval, key, stream

    from backend.chords.parser import parse_chord
    from backend.chords.transpose import compute_target_key, transpose_chord
    from backend.omr_v3.chords import chord_symbol_from_text, chord_text

    names = {-6: 'Gb', -5: 'Db', -4: 'Ab', -3: 'Eb', -2: 'Bb', -1: 'F', 0: 'C', 1: 'G', 2: 'D', 3: 'A', 4: 'E', 5: 'B', 6: 'F#'}
    out = ref_score  # transposed in place by design (caller passes a fresh copy)
    fifths = ref_gt.key
    for m in out.parts[0].getElementsByClass(stream.Measure):
        for ks in m.getElementsByClass(key.KeySignature):
            fifths = ks.sharps
        orig = names[fifths]
        target = compute_target_key(orig, semitones)
        if mode == 'key':
            # Name the interval from the two key names (letter distance + semitones).
            letters = 'CDEFGAB'
            steps = (letters.index(target[0]) - letters.index(orig[0])) % 7
            if semitones < 0 and steps:
                steps -= 7
            if semitones > 0 and steps == 0 and semitones > 6:
                steps = 7
            generic = interval.GenericInterval(steps + (1 if steps >= 0 else -1))
            ivl = interval.intervalFromGenericAndChromatic(generic, interval.ChromaticInterval(semitones))
            for ks in m.getElementsByClass(key.KeySignature):
                ks.transpose(ivl, inPlace=True)
            for n in m.recurse().notes:
                if not isinstance(n, harmony.ChordSymbol):
                    n.transpose(ivl, inPlace=True)
        else:
            target = target if mode == 'key' else orig
        for cs in list(m.recurse().getElementsByClass(harmony.ChordSymbol)):
            new = transpose_chord(parse_chord(chord_text(cs)), semitones,
                                  target_key=compute_target_key(orig, semitones), original_key=orig)
            site, off = cs.activeSite, cs.offset
            site.remove(cs)
            site.insert(off, chord_symbol_from_text(new))
    return out


def main() -> None:
    from music21 import converter

    from scripts.omr_v3.reference import parse_gt, to_music21

    ap = argparse.ArgumentParser()
    ap.add_argument('reference', type=Path)
    ap.add_argument('candidate', type=Path)
    ap.add_argument('--semitones', type=int, default=0)
    ap.add_argument('--mode', default='key', choices=('key', 'capo'))
    ap.add_argument('--json', type=Path)
    args = ap.parse_args()
    gt = parse_gt(args.reference.read_text(encoding='utf-8'))
    ref = to_music21(gt)
    if args.semitones:
        ref = transposed_reference(ref, gt, args.semitones, args.mode)
    result = compare(ref, converter.parse(str(args.candidate)))
    if args.json:
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    summary = {k: v for k, v in result.items() if k not in ('note_diffs', 'chord_diffs')}
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
