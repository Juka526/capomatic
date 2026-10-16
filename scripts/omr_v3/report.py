"""Turn an evaluate.py output directory into a Markdown accuracy/discrepancy report.

Usage: python -m scripts.omr_v3.report EVIDENCE_DIR [--compare-dir OTHER_EVIDENCE_DIR] > REPORT.md

Every run has an API outcome (``mode``: full_score / chord_only / error) and,
when the full-score path could run (gated, or ungated after a fallback), the
accuracy of that full score against the reference. The gate is judged by
whether it withheld exactly the full scores that would have been unusable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# A full score is "usable" for the gate confusion table at this pitched-note exact rate.
USABLE_NOTE_EXACT = 0.95
SET_ORDER = ('dev', 'synthetic-dev', 'synthetic-holdout', 'held-out')


def _pct(x) -> str:
    return '–' if x is None else f'{x * 100:.1f}%'


def _runs(directory: Path) -> list[dict]:
    return json.loads((directory / 'summary.json').read_text(encoding='utf-8'))['runs']


def _notes(r: dict) -> float | None:
    return ((r.get('transposed') or {}).get('pitched_notes') or {}).get('exact')


def _micro(runs: list[dict], section: str) -> dict:
    """Pooled (micro-averaged) rates over all reference notes / chords."""
    pn = pe = pp = cr = ch = cc = 0
    for r in runs:
        s = r[section]
        p = s['pitched_notes']
        pn += p['reference']
        pe += round(p['exact'] * p['reference'])
        pp += round(p['pitch'] * p['reference'])
        cr += s['chords']['reference']
        ch += s['chords']['hits']
        cc += s['chords']['candidate']
    return {'pitched_exact': pe / pn if pn else None, 'pitched_pitch': pp / pn if pn else None,
            'chord_recall': ch / cr if cr else None, 'chord_precision': ch / cc if cc else None,
            'notes_n': pn, 'chords_n': cr}


def _outcome(r: dict) -> str:
    if r.get('mode') == 'error':
        reason = (r.get('decision') or {}).get('reason')
        return f"error ({reason})" if reason else 'error'
    return r.get('mode', '?')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('evidence', type=Path)
    ap.add_argument('--compare-dir', type=Path, help='same evaluation with Audiveris-only chords')
    args = ap.parse_args()
    runs = _runs(args.evidence)
    sets = sorted({r['role'] for r in runs}, key=lambda s: SET_ORDER.index(s) if s in SET_ORDER else 99)
    out: list[str] = []
    w = out.append

    w('### API outcome per input (gate enforced) and full-score accuracy')
    w('')
    w('"Notes exact" etc. are measured on the full score the API returned, or — marked *(withheld)* — on the '
      'full score the gate refused to return (ungated run), so the gate decision can be checked.')
    w('')
    w('| Input | Set | Class | Condition | API outcome | Gate reason | Staff px | Bad bars | Notes exact | Rhythm | '
      'Chords R / P | Key sig | Integrity | Time (s) | Peak RSS py / tools |')
    w('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for r in runs:
        t = r.get('transposed')
        po = r.get('post_omr') or {}
        pf = ((r.get('preflight') or {}).get('metrics') or {})
        withheld = ' *(withheld)*' if r.get('full_score_metrics_from') == 'ungated' else ''
        integ = (r.get('error_classes') or {}).get('integrity_ok')
        acc = (f"{_pct(_notes(r))}{withheld} | {_pct(t['rhythm_acc'])} | "
               f"{_pct(t['chords']['recall'])} / {_pct(t['chords']['precision'])} | {_pct(t['key_signature_acc'])}"
               if t else f"– | – | – | – ({r.get('ungated_error', r.get('error', ''))[:80]})")
        bad = f"{po['bad_bars']}/{po['bars']}" if po.get('bars') is not None else '–'
        ungated = f" (+{r['ungated_wall_s']:.0f} ungated)" if r.get('ungated_wall_s') else ''
        w(f"| {r['id']} | {r['role']} | {r.get('class')} | {r['condition']}{' (cold)' if r.get('cold') else ''} | "
          f"**{_outcome(r)}** | {(r.get('decision') or {}).get('reason', '–')} | "
          f"{pf.get('effective_interline_px', '–')} | {bad} | {acc} | "
          f"{'ok' if integ else ('FAIL' if integ is False else '–')} | {r['wall_s']:.1f}{ungated} | "
          f"{r.get('python_peak_mb', 0):.0f} / {r.get('tools_peak_mb', 0):.0f} MB |")
    w('')

    w(f'### Gate decisions vs. usefulness (full score usable = pitched notes exact >= {USABLE_NOTE_EXACT:.0%})')
    w('')
    w('| Set | Full score returned, usable | Full score returned, NOT usable (unsafe) | '
      'Withheld, would have been unusable (correct fallback) | Withheld, would have been usable (unnecessary) | Errors |')
    w('|---|---|---|---|---|---|')
    for role in sets:
        cells = {k: [] for k in ('tp', 'unsafe', 'good_fb', 'extra_fb', 'err')}
        for r in (x for x in runs if x['role'] == role):
            n = _notes(r)
            label = f"{r['id']} {r['condition']}"
            withheld = r.get('decision', {}) and (r.get('decision') or {}).get('mode') == 'chord_only'
            if r.get('mode') == 'full_score':
                cells['err' if n is None else ('tp' if n >= USABLE_NOTE_EXACT else 'unsafe')].append(label)
            elif withheld and n is not None:
                cells['extra_fb' if n >= USABLE_NOTE_EXACT else 'good_fb'].append(label)
            if r.get('mode') == 'error':
                cells['err'].append(label)
        w(f"| {role} | " + ' | '.join(f"{len(v)}" + (f"<br><sub>{', '.join(v)}</sub>" if v and k != 'tp' else '')
                                      for k, v in cells.items()) + ' |')
    w('')
    w('An "error" with a gate reason means the gate fell back to chord-only but chord recognition was not '
      'available in that run (PaddleOCR missing), so the API would answer 422 rather than a fabricated score.')
    w('')

    w('### Pooled accuracy of full scores the API actually returned (key-change runs)')
    w('')
    for role in sets:
        sel = [r for r in runs if r['role'] == role and r.get('mode') == 'full_score'
               and r['condition'].startswith('key') and r.get('transposed')]
        withheld = [r for r in runs if r['role'] == role and r.get('full_score_metrics_from') == 'ungated'
                    and r['condition'].startswith('key') and r.get('transposed')]
        for label, group in (('returned', sel), ('withheld by the gate', withheld)):
            if not group:
                continue
            m = _micro(group, 'transposed')
            w(f"- **{role}, {label}** ({len(group)} runs): notes exact {_pct(m['pitched_exact'])} of {m['notes_n']} "
              f"notes (pitch only {_pct(m['pitched_pitch'])}); chords recall {_pct(m['chord_recall'])}, "
              f"precision {_pct(m['chord_precision'])} of {m['chords_n']} chords.")
    w('')

    w(f"Chord-only accepted: {sum(r.get('mode') == 'chord_only' for r in runs)}; rejected for insufficient confidence: {sum((r.get('chord_only_confidence') or {}).get('accepted') is False for r in runs)}.")
    w('')
    co = [r for r in runs if r.get('chord_only_chords')]
    if co:
        w('### Chord-only fallback: transposed chord labels vs the transposed reference')
        w('')
        w('Position-free multiset comparison (the fallback draws labels on the page, it has no measure structure). '
          'Recall = reference chords found; precision = drawn chords that are correct. '
          'A run with no chord at all is now an explicit 422 error, not a result.')
        w('')
        w('| Input | Set | Condition | Reference chords | Drawn | Recall | Precision | Recall incl. enharmonic |')
        w('|---|---|---|---|---|---|---|---|')
        tot = {}
        for r in co:
            c = r['chord_only_chords']
            for k in ('reference', 'candidate'):
                tot[k] = tot.get(k, 0) + c[k]
            tot['hits'] = tot.get('hits', 0) + c['exact']['hits']
            w(f"| {r['id']} | {r['role']} | {r['condition']} | {c['reference']} | {c['candidate']} | "
              f"{_pct(c['exact']['recall'])} | {_pct(c['exact']['precision'])} | {_pct(c['sounding']['recall'])} |")
        w(f"| **pooled** | | | {tot['reference']} | {tot['candidate']} | {_pct(tot['hits'] / tot['reference'])} | "
          f"{_pct(tot['hits'] / tot['candidate'] if tot['candidate'] else None)} | |")
        w('')

    rejected = [r for r in runs if r.get('rejected_chord_only_chords')]
    if rejected:
        w('### Rejected chord-only candidates (offline, never returned)')
        w('')
        w('| Input | Recall | Precision |')
        w('|---|---|---|')
        for r in rejected:
            metrics = r['rejected_chord_only_chords']['exact']
            w(f"| {r['id']} | {_pct(metrics['recall'])} | {_pct(metrics['precision'])} |")
        w('')
    w('### Error classes (all runs with a full-score path)')
    w('')
    w('| Input | Condition | Recognition (notes) | Transposition (notes) | Rendering (MuseScore, notes) | '
      'Chord recognition | Chord mapping | Chord transposition | Lyrics v1 chars |')
    w('|---|---|---|---|---|---|---|---|---|')
    totals = {}
    for r in runs:
        e = r.get('error_classes')
        if not e:
            continue
        for k, v in e.items():
            if isinstance(v, int) and not isinstance(v, bool):
                totals[k] = totals.get(k, 0) + v
        ly = (r.get('lyrics_verse1') or {}).get('char_acc')
        w(f"| {r['id']} | {r['condition']} | {e['recognition_note_errors']} | {e['transposition_note_errors']} | "
          f"{e['rendering_note_errors']} | {e['chord_recognition_errors']} | {e['chord_mapping_errors']} | "
          f"{e['chord_transposition_errors']} | {_pct(ly)} |")
    if totals:
        w(f"| **total** | | {totals.get('recognition_note_errors', 0)} | {totals.get('transposition_note_errors', 0)} | "
          f"{totals.get('rendering_note_errors', 0)} | {totals.get('chord_recognition_errors', 0)} | "
          f"{totals.get('chord_mapping_errors', 0)} | {totals.get('chord_transposition_errors', 0)} | |")
    w('')

    if args.compare_dir and (args.compare_dir / 'summary.json').exists():
        base = {(r['id'], r['condition']): r for r in _runs(args.compare_dir) if r.get('transposed')}
        w('### Chord source comparison (key-change runs)')
        w('')
        w('| Input | Audiveris chords R / P | PaddleOCR + Audiveris R / P |')
        w('|---|---|---|')
        for r in runs:
            b = base.get((r['id'], r['condition']))
            if b and r.get('transposed') and r['condition'].startswith('key'):
                w(f"| {r['id']} | {_pct(b['transposed']['chords']['recall'])} / {_pct(b['transposed']['chords']['precision'])} | "
                  f"{_pct(r['transposed']['chords']['recall'])} / {_pct(r['transposed']['chords']['precision'])} |")
        w('')

    w('### Discrepancies (recognised score vs reference, before transposition)')
    w('')
    for r in runs:
        cmp_path = args.evidence / r['id'] / f"compare_{r['condition']}.json"
        if not r['condition'].startswith('key') or not cmp_path.exists():
            continue
        data = json.loads(cmp_path.read_text(encoding='utf-8'))['recognized_vs_reference']
        w(f"<details><summary><b>{r['id']}</b> ({_outcome(r)}): {len(data['note_diffs'])} note/rest differences, "
          f"{len(data['chord_diffs'])} missed or wrong chords</summary>")
        w('')
        if data['note_diffs']:
            w('| Bar (ref) | Beat | Expected | Found |')
            w('|---|---|---|---|')
            for d in data['note_diffs']:
                bar = d.get('ref_measure', d.get('cand_measure'))
                w(f"| {bar if bar is None else bar + 1} | {d['offset']} | {d['expected'] or '(extra)'} | {d['found'] or '(missing)'} |")
            w('')
        if data['chord_diffs']:
            w('| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |')
            w('|---|---|---|---|---|')
            for d in data['chord_diffs']:
                w(f"| {d['ref_measure'] + 1} | {d['offset']} | {d['expected']} | {d.get('class', '–')} | "
                  f"{', '.join(d['found_in_bar']) or '–'} |")
            w('')
        w('</details>')
        w('')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
