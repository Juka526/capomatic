"""Turn an evaluate.py output directory into a Markdown accuracy/discrepancy report.

Usage: python -m scripts.omr_v3.report EVIDENCE_DIR [--compare-dir OTHER_EVIDENCE_DIR] > REPORT.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _pct(x) -> str:
    return '–' if x is None else f'{x * 100:.1f}%'


def _runs(directory: Path) -> list[dict]:
    return json.loads((directory / 'summary.json').read_text(encoding='utf-8'))['runs']


def _micro(runs: list[dict], section: str) -> dict:
    """Pooled (micro-averaged) rates over all reference events / chords."""
    ev = ex = pn = pe = pp = cr = ch = cc = 0
    for r in runs:
        s = r[section]
        n = s['events']['reference']
        ev += n
        ex += round(s['note_exact'] * n)
        p = s['pitched_notes']
        pn += p['reference']
        pe += round(p['exact'] * p['reference'])
        pp += round(p['pitch'] * p['reference'])
        cr += s['chords']['reference']
        ch += s['chords']['hits']
        cc += s['chords']['candidate']
    return {'events': ex / ev if ev else None, 'pitched_exact': pe / pn if pn else None,
            'pitched_pitch': pp / pn if pn else None, 'chord_recall': ch / cr if cr else None,
            'chord_precision': ch / cc if cc else None, 'notes_n': pn, 'chords_n': cr}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('evidence', type=Path)
    ap.add_argument('--compare-dir', type=Path, help='same evaluation with Audiveris-only chords')
    args = ap.parse_args()
    runs = [r for r in _runs(args.evidence) if 'error' not in r]
    errors = [r for r in _runs(args.evidence) if 'error' in r]
    out: list[str] = []
    w = out.append

    w('| Sheet | Set | Condition | Notes exact | Pitch | Rhythm | Chords R / P | Key sig | Time sig | Lyrics v1 | MuseScore fidelity | Time (s) | Tool peak RSS |')
    w('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for r in runs:
        t = r['transposed']
        ly = (r.get('lyrics_verse1') or {}).get('char_acc')
        w(f"| {r['score']} | {r['role']} | {r['condition']}{' (cold)' if r['cold'] else ''} | "
          f"{_pct(t['pitched_notes']['exact'])} | {_pct(t['pitched_notes']['pitch'])} | {_pct(t['rhythm_acc'])} | "
          f"{_pct(t['chords']['recall'])} / {_pct(t['chords']['precision'])} | {_pct(t['key_signature_acc'])} | "
          f"{_pct(t['time_signature_acc'])} | {_pct(ly)} | {_pct(r['musescore_fidelity']['note_exact'])} | "
          f"{r['wall_s']:.1f} | {r['tools_peak_mb']:.0f} MB |")
    for r in errors:
        w(f"| {r['score']} | {r['role']} | {r['condition']} | FAILED: `{r['error'][:120]}` |")
    w('')
    for role in ('dev', 'held-out'):
        sel = [r for r in runs if r['role'] == role and r['condition'].startswith('key')]
        if not sel:
            continue
        m = _micro(sel, 'transposed')
        w(f"**{role} pooled (key-change runs, transposed output vs independently transposed reference):** "
          f"notes exact {_pct(m['pitched_exact'])} of {m['notes_n']} notes, pitch {_pct(m['pitched_pitch'])}; "
          f"chords recall {_pct(m['chord_recall'])}, precision {_pct(m['chord_precision'])} of {m['chords_n']} chords.")
        w('')
    if args.compare_dir and (args.compare_dir / 'summary.json').exists():
        base = {(r['score'], r['condition']): r for r in _runs(args.compare_dir) if 'error' not in r}
        w('Chord source comparison (key-change runs):')
        w('')
        w('| Sheet | Audiveris chords R / P | PaddleOCR + Audiveris R / P |')
        w('|---|---|---|')
        for r in runs:
            b = base.get((r['score'], r['condition']))
            if b and r['condition'].startswith('key'):
                w(f"| {r['score']} | {_pct(b['transposed']['chords']['recall'])} / {_pct(b['transposed']['chords']['precision'])} | "
                  f"{_pct(r['transposed']['chords']['recall'])} / {_pct(r['transposed']['chords']['precision'])} |")
        w('')
    w('### Discrepancies (recognised score vs reference, before transposition)')
    w('')
    for r in runs:
        if not r['condition'].startswith('key'):
            continue
        cmp_path = args.evidence / r['score'] / f"compare_{r['condition']}.json"
        data = json.loads(cmp_path.read_text(encoding='utf-8'))['recognized_vs_reference']
        w(f"<details><summary><b>{r['score']}</b>: {len(data['note_diffs'])} note/rest differences, "
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
            w('| Bar (ref) | Beat | Expected chord | Chords found in that bar |')
            w('|---|---|---|---|')
            for d in data['chord_diffs']:
                w(f"| {d['ref_measure'] + 1} | {d['offset']} | {d['expected']} | {', '.join(d['found_in_bar']) or '–'} |")
            w('')
        w('</details>')
        w('')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
