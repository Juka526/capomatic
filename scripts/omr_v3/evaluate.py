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


def _paddle_detector():
    from backend.ocr.hybrid_detect import detect_chords_hybrid

    def detect(path: str):
        return detect_chords_hybrid(path, use_ai_fallback=False)

    return detect


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--chords', choices=('paddle', 'none'), default='paddle')
    ap.add_argument('--only', nargs='*')
    args = ap.parse_args()

    from music21 import converter

    from backend.omr_v3.core import process
    from scripts.omr_v3.compare import compare, transposed_reference
    from scripts.omr_v3.reference import parse_gt, to_music21

    manifest = json.loads((EVAL / 'manifest.json').read_text(encoding='utf-8'))
    detector = _paddle_detector() if args.chords == 'paddle' else None
    args.out.mkdir(parents=True, exist_ok=True)
    summary = {'chords': args.chords, 'python': sys.version.split()[0], 'runs': []}
    first = True
    for entry in manifest['scores']:
        if args.only and entry['name'] not in args.only:
            continue
        name = entry['name']
        src = EVAL / entry['source']
        ref_path = EVAL / entry['reference']
        if not ref_path.exists():
            print(f'skip {name}: no reference', flush=True)
            continue
        d = args.out / name
        d.mkdir(exist_ok=True)
        shutil.copy(src, d / ('original' + src.suffix.lower()))
        gt = parse_gt(ref_path.read_text(encoding='utf-8'))
        to_music21(gt).write('musicxml', fp=str(d / 'reference.musicxml'))
        original_png = _source_png(src, d / 'original.png')
        for mode, semis in (('key', entry['key_shift']), ('capo', -entry['capo'])):
            tag = f'{mode}{semis:+d}'
            t0 = time.monotonic()
            try:
                result = process(src.read_bytes(), src.suffix.lower(), semis, mode, chord_detector=detector)
            except Exception as exc:  # record failures as evidence, do not hide them
                summary['runs'].append({'score': name, 'role': entry['role'], 'condition': tag, 'error': repr(exc)})
                print(f'{name} {tag}: FAILED {exc!r}', flush=True)
                first = False
                continue
            wall = round(time.monotonic() - t0, 2)
            (d / f'transposed_{tag}.pdf').write_bytes(result.pdf)
            (d / f'transposed_{tag}.musicxml').write_bytes(result.musicxml)
            (d / 'recognized.musicxml').write_bytes(result.recognized_musicxml)
            (d / f'conversion-report_{tag}.json').write_text(
                json.dumps({'stages_ms': result.stages_ms, **result.report}, ensure_ascii=False, indent=1))

            recognized_cmp = compare(to_music21(gt), converter.parse(str(d / 'recognized.musicxml')))
            ref_t = transposed_reference(to_music21(gt), gt, semis, mode)
            ref_t.write('musicxml', fp=str(d / f'reference_{tag}.musicxml'))
            transposed_cmp = compare(copy.deepcopy(ref_t), converter.parse(str(d / f'transposed_{tag}.musicxml')))
            rt = _musescore_roundtrip(d / f'transposed_{tag}.musicxml', d / f'musescore_roundtrip_{tag}.mxl')
            fidelity = compare(converter.parse(str(d / f'transposed_{tag}.musicxml')), converter.parse(str(rt)))
            (d / f'compare_{tag}.json').write_text(json.dumps(
                {'recognized_vs_reference': recognized_cmp, 'transposed_vs_reference': transposed_cmp,
                 'musescore_roundtrip_vs_transposed': fidelity}, ensure_ascii=False, indent=1))

            pages = _pdf_to_pngs(d / f'transposed_{tag}.pdf', d / f'transposed_{tag}')
            _side_by_side(original_png, pages, d / f'side_by_side_{tag}.png',
                          (f'Original: {entry["title"]}', f'Capomatic V3 {tag}'))

            def brief(c: dict) -> dict:
                return {k: c[k] for k in ('measures', 'events', 'note_exact', 'pitch_acc', 'rhythm_acc',
                                          'pitched_notes', 'ser', 'chords', 'key_signature_acc', 'time_signature_acc')}

            run = {'score': name, 'role': entry['role'], 'condition': tag, 'cold': first,
                   'wall_s': wall, 'stages_ms': result.stages_ms, **_rss_mb(),
                   'recognized': brief(recognized_cmp), 'transposed': brief(transposed_cmp),
                   'musescore_fidelity': brief(fidelity),
                   'warnings': len(result.report.get('warnings', [])),
                   'repairs': result.report.get('repairs'),
                   'chord_source': result.report.get('chord_source'),
                   'chords_from_audiveris': result.report.get('chords_from_audiveris')}
            summary['runs'].append(run)
            first = False
            print(f"{name} {tag}: {wall}s notes={transposed_cmp['note_exact']} chords R={transposed_cmp['chords']['recall']} "
                  f"P={transposed_cmp['chords']['precision']} fidelity={fidelity['note_exact']}", flush=True)
    (args.out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    os.environ.setdefault('PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK', 'True')
    main()
