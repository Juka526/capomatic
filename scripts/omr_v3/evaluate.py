"""End-to-end evaluation of the V3 score pipeline on the evaluation sheets.

For every sheet in tests/omr_v3_eval/manifest.json this runs the real pipeline
(Audiveris + chord OCR + music21 + MuseScore) twice — once as a key change and
once as a capo conversion — and records:

* wall-clock time per stage, cold (first run in the process) and warm;
* peak RSS of the Python process and of the external tools;
* accuracy of the recognised MusicXML against the hand-made reference, and of
  the transposed MusicXML against the independently transposed reference;
* MuseScore fidelity: the PDF renderer re-exports the MusicXML it was given
  and that export is compared with the input;
* side-by-side PNGs (original page | rendered result) for visual review.

Usage (needs the external tools; see Dockerfile):
    python -m scripts.omr_v3.evaluate --out omr-v3-evidence [--chords paddle|none] [--only jusim]
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / 'tests' / 'omr_v3_eval'


def _rss_mb() -> dict:
    return {'python_peak_mb': round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
            'tools_peak_mb': round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 1)}


def _pdf_to_pngs(pdf: Path, stem: Path, dpi: int = 110) -> list[Path]:
    subprocess.run(['pdftoppm', '-r', str(dpi), '-png', str(pdf), str(stem)], check=True)
    return sorted(stem.parent.glob(stem.name + '-*.png'))


def _source_png(src: Path, out: Path, dpi: int = 110) -> Path:
    from PIL import Image

    if src.suffix.lower() == '.pdf':
        subprocess.run(['pdftoppm', '-r', str(dpi), '-png', '-singlefile', str(src), str(out.with_suffix(''))], check=True)
        return out
    with Image.open(src) as im:
        im.convert('RGB').save(out)
    return out


def _side_by_side(original: Path, rendered: list[Path], out: Path, labels: tuple[str, str]) -> None:
    from PIL import Image, ImageDraw, ImageFont

    left = Image.open(original).convert('RGB')
    pages = [Image.open(p).convert('RGB') for p in rendered]
    h = 1400
    left = left.resize((int(left.width * h / left.height), h))
    pages = [p.resize((int(p.width * h / p.height), h)) for p in pages]
    width = left.width + sum(p.width for p in pages) + 20 * (len(pages) + 1)
    canvas = Image.new('RGB', (width, h + 60), 'white')
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 26)
    except OSError:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(canvas)
    canvas.paste(left, (10, 50))
    draw.text((10, 10), labels[0], fill='black', font=font)
    x = left.width + 30
    for i, p in enumerate(pages):
        canvas.paste(p, (x, 50))
        draw.text((x, 10), labels[1] + (f' (page {i + 1})' if len(pages) > 1 else ''), fill='black', font=font)
        x += p.width + 20
    canvas.save(out, optimize=True)


def _musescore_roundtrip(xml: Path, out: Path) -> Path:
    from backend.omr_v3.core import _bin, _tool_env

    home = out.parent / 'mscore-home'
    home.mkdir(exist_ok=True)
    subprocess.run([_bin('CAPOMATIC_MUSESCORE_BIN', 'mscore3', 'mscore', 'musescore'), '-o', str(out), str(xml)],
                   check=True, env=_tool_env(home), capture_output=True, timeout=300)
    return out


def _chord_only_renderer():
    """V1's renderer from the API module (import pulls in the app, not the Paddle models)."""
    from backend.api.main import _omr_chord_only

    return _omr_chord_only


def _inputs(manifest: dict, sets: list[str]) -> list[dict]:
    """Real sheets (key + capo) and synthetic seeds x input classes (key only)."""
    out = []
    if 'real' in sets:
        for e in manifest['scores']:
            out.append({**e, 'id': e['name'], 'source': EVAL / e['source'], 'reference': EVAL / e['reference'],
                        'conditions': [('key', e['key_shift']), ('capo', -e['capo'])]})
    syn = manifest.get('synthetic', {})
    for role in ('dev', 'holdout'):
        if f'synthetic-{role}' not in sets:
            continue
        for i, seed in enumerate(syn.get(role, [])):
            base = EVAL / 'synthetic' / role / f'syn{seed}'
            shift = (2, -2, 3, -3)[i % 4]
            for cls_name, file in syn['classes'].items():
                out.append({'id': f'syn{seed}-{cls_name}', 'name': f'syn{seed}', 'title': f'synthetic {seed}',
                            'role': f'synthetic-{role}', 'class': cls_name, 'source': base / file,
                            'reference': base / 'reference.gt', 'conditions': [('key', shift)]})
    return out


def _paddle_detector():
    from backend.ocr.hybrid_detect import detect_chords_hybrid

    def detect(path: str):
        return detect_chords_hybrid(path, use_ai_fallback=False)

    return detect


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--chords', choices=('paddle', 'none'), default='paddle')
    ap.add_argument('--sets', nargs='+', default=['real', 'synthetic-dev', 'synthetic-holdout'],
                    choices=('real', 'synthetic-dev', 'synthetic-holdout'))
    ap.add_argument('--only', nargs='*', help='input ids (e.g. jusim, syn201-scan)')
    args = ap.parse_args()

    import logging

    from music21 import converter

    from backend.omr_v3.core import process
    from scripts.omr_v3.compare import compare, lyric_accuracy, transposed_reference
    from scripts.omr_v3.reference import parse_gt, to_music21

    args.out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=str(args.out / 'pipeline.log'), level=logging.WARNING,
                        format='%(asctime)s %(name)s %(levelname)s %(message)s')
    manifest = json.loads((EVAL / 'manifest.json').read_text(encoding='utf-8'))
    detector = _paddle_detector() if args.chords == 'paddle' else None
    renderer = _chord_only_renderer()
    summary = {'chords': args.chords, 'python': sys.version.split()[0], 'sets': args.sets, 'runs': []}
    first = True

    def brief(c: dict) -> dict:
        return {k: c[k] for k in ('measures', 'events', 'note_exact', 'pitch_acc', 'rhythm_acc', 'pitched_notes',
                                  'ser', 'ops', 'chords', 'chord_error_classes', 'key_signature_acc',
                                  'time_signature_acc')}

    for entry in _inputs(manifest, args.sets):
        if args.only and entry['id'] not in args.only:
            continue
        src: Path = entry['source']
        d = args.out / entry['id']
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, d / ('original' + src.suffix.lower()))
        gt = parse_gt(entry['reference'].read_text(encoding='utf-8'))
        to_music21(gt).write('musicxml', fp=str(d / 'reference.musicxml'))
        original_png = _source_png(src, d / 'original.png') if src.suffix.lower() != '.musicxml' else None
        for mode, semis in entry['conditions']:
            tag = f'{mode}{semis:+d}'
            run = {'id': entry['id'], 'score': entry['name'], 'role': entry['role'],
                   'class': entry.get('class', entry.get('input_class')), 'condition': tag, 'cold': first}
            first = False
            # 1) What the API returns (gate enforced).
            t0 = time.monotonic()
            try:
                gated = process(src.read_bytes(), src.suffix.lower(), semis, mode,
                                chord_detector=detector, chord_only_renderer=renderer)
                run.update(mode=gated.mode, decision=gated.report.get('decision'),
                           wall_s=round(time.monotonic() - t0, 2), stages_ms=gated.stages_ms,
                           preflight=gated.report.get('preflight'), post_omr=gated.report.get('post_omr'),
                           integrity=gated.report.get('integrity'))
            except Exception as exc:  # record failures as evidence, do not hide them
                run.update(mode='error', error=repr(exc), wall_s=round(time.monotonic() - t0, 2))
                gated = None
            (d / f'gated_report_{tag}.json').write_text(json.dumps(
                {'stages_ms': gated.stages_ms, **gated.report} if gated else {'error': run['error']},
                ensure_ascii=False, indent=1))
            if gated is not None and gated.mode == 'chord_only':
                (d / f'chord_only_{tag}.pdf').write_bytes(gated.pdf)
                (d / f'chord_only_{tag}.png').write_bytes(gated.png)
                _side_by_side(original_png, [d / f'chord_only_{tag}.png'], d / f'side_by_side_{tag}.png',
                              (f'Original: {entry["title"]}', f'Capomatic V3 {tag} (chord-only fallback)'))
            # 2) The full-score path (gate off when it fell back) to measure what it would have produced.
            full = gated if gated is not None and gated.mode == 'full_score' else None
            if full is None:
                t1 = time.monotonic()
                try:
                    full = process(src.read_bytes(), src.suffix.lower(), semis, mode,
                                   chord_detector=detector, chord_only_renderer=renderer, gate=False)
                    run['ungated_wall_s'] = round(time.monotonic() - t1, 2)
                except Exception as exc:
                    run['ungated_error'] = repr(exc)
            run.update(_rss_mb())
            if full is not None:
                stem = 'transposed' if full is gated else 'ungated_transposed'
                (d / f'{stem}_{tag}.pdf').write_bytes(full.pdf)
                (d / f'{stem}_{tag}.musicxml').write_bytes(full.musicxml)
                (d / 'recognized.musicxml').write_bytes(full.recognized_musicxml)
                (d / f'{stem}_report_{tag}.json').write_text(
                    json.dumps({'stages_ms': full.stages_ms, **full.report}, ensure_ascii=False, indent=1))
                recognized_cmp = compare(to_music21(gt), converter.parse(str(d / 'recognized.musicxml')))
                ref_t = transposed_reference(to_music21(gt), gt, semis, mode)
                ref_t.write('musicxml', fp=str(d / f'reference_{tag}.musicxml'))
                transposed_cmp = compare(copy.deepcopy(ref_t), converter.parse(str(d / f'{stem}_{tag}.musicxml')))
                rt = _musescore_roundtrip(d / f'{stem}_{tag}.musicxml', d / f'musescore_roundtrip_{tag}.mxl')
                fidelity = compare(converter.parse(str(d / f'{stem}_{tag}.musicxml')), converter.parse(str(rt)))
                (d / f'compare_{tag}.json').write_text(json.dumps(
                    {'recognized_vs_reference': recognized_cmp, 'transposed_vs_reference': transposed_cmp,
                     'musescore_roundtrip_vs_transposed': fidelity}, ensure_ascii=False, indent=1))
                if original_png is not None:
                    pages = _pdf_to_pngs(d / f'{stem}_{tag}.pdf', d / f'{stem}_{tag}')
                    if full is gated:
                        _side_by_side(original_png, pages, d / f'side_by_side_{tag}.png',
                                      (f'Original: {entry["title"]}', f'Capomatic V3 {tag} (full score)'))
                    else:  # what the gate withheld, for reviewers
                        _side_by_side(original_png, pages, d / f'side_by_side_ungated_{tag}.png',
                                      (f'Original: {entry["title"]}', f'{tag} full score WITHHELD by the gate'))
                rec_err = sum(recognized_cmp['ops'].values())
                tr_err = sum(transposed_cmp['ops'].values())
                run.update(
                    full_score_metrics_from='gated' if full is gated else 'ungated',
                    recognized=brief(recognized_cmp), transposed=brief(transposed_cmp),
                    musescore_fidelity=brief(fidelity),
                    error_classes={
                        'recognition_note_errors': rec_err,
                        'transposition_note_errors': max(0, tr_err - rec_err),
                        'rendering_note_errors': sum(fidelity['ops'].values()),
                        'chord_recognition_errors': recognized_cmp['chord_error_classes']['recognition'],
                        'chord_mapping_errors': recognized_cmp['chord_error_classes']['mapping'],
                        'chord_transposition_errors': max(0, transposed_cmp['chords']['reference']
                                                          - transposed_cmp['chords']['hits']
                                                          - (recognized_cmp['chords']['reference']
                                                             - recognized_cmp['chords']['hits'])),
                        'integrity_ok': (full.report.get('integrity') or {}).get('ok'),
                    },
                    lyrics_verse1=lyric_accuracy(gt.lyrics1, converter.parse(str(d / 'recognized.musicxml'))),
                    repairs=full.report.get('repairs'), chord_source=full.report.get('chord_source'),
                    post_omr=run.get('post_omr') or full.report.get('post_omr'),
                    preflight=run.get('preflight') or full.report.get('preflight'),
                    decision=run.get('decision') or full.report.get('decision'))
            summary['runs'].append(run)
            t = run.get('transposed') or {}
            print(f"{entry['id']} {tag}: mode={run.get('mode')} reason={(run.get('decision') or {}).get('reason')} "
                  f"{run.get('wall_s')}s notes={(t.get('pitched_notes') or {}).get('exact')} "
                  f"chordsR={(t.get('chords') or {}).get('recall')} bad_bars={(run.get('post_omr') or {}).get('bad_bars')}",
                  flush=True)
            (args.out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    os.environ.setdefault('PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK', 'True')
    main()
