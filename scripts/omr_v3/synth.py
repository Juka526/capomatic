"""Rights-clear synthetic lead sheets for the V3 benchmark.

Every sheet is composed here from a seed (melody, chords, Korean placeholder
lyrics), so the ground truth is exact and there are no third-party rights.
The clean engraving comes from MuseScore; degraded copies stand in for the
input classes the product actually receives:

* ``clean.pdf``     – vector PDF straight from notation software (class 1)
* ``ordinary.pdf``  – 200 dpi raster PDF, slight skew, JPEG artefacts (class 2, primary target)
* ``scan.pdf``      – 150 dpi grey scan: skew, blur, noise, paper tone (class 3)
* ``phone.jpg``     – camera photo: perspective, uneven light, ~1500 px wide (class 4)
* ``score.musicxml``– MusicXML fast path (class 5)

Limitation: all engravings share MuseScore's house style, so these sheets do
not replace real-world sheets from other notation programs.

Usage: python -m scripts.omr_v3.synth --out tests/omr_v3_eval/synthetic --seeds 101 102 103
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
from fractions import Fraction
from pathlib import Path

_SCALE = [0, 2, 4, 5, 7, 9, 11]
_KEYS = {  # name: (fifths, tonic pitch class)
    'C': (0, 0), 'G': (1, 7), 'D': (2, 2), 'A': (3, 9), 'E': (4, 4),
    'F': (-1, 5), 'Bb': (-2, 10), 'Eb': (-3, 3),
}
_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
_FLAT = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
# One-beat rhythm cells in quarter lengths (worship lead sheets: 8ths and 16ths dominate).
_CELLS = [
    [1], [Fraction(1, 2)] * 2, [Fraction(1, 2)] * 2, [Fraction(3, 4), Fraction(1, 4)],
    [Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)], [Fraction(1, 2), Fraction(1, 4), Fraction(1, 4)],
    [Fraction(1, 4)] * 4, [Fraction(1, 4), Fraction(1, 2), Fraction(1, 4)],
]
_LONG = [[2], [Fraction(3, 2), Fraction(1, 2)], [3], [4]]
_SYLLABLES = list('주님사랑은혜나의모든것을드리네하늘빛소망가운데우리함께노래해기쁨평안영원히찬양')


def _name(pc: int, flats: bool) -> str:
    return (_FLAT if flats else _SHARP)[pc % 12]


def _chord_names(key: str) -> list[tuple[int, str]]:
    """(scale degree, suffix) choices typical of CCM charts."""
    return [(0, ''), (0, ''), (0, 'add2'), (3, ''), (3, 'maj7'), (4, ''), (4, 'sus4'), (4, '7'),
            (5, 'm7'), (5, 'm'), (1, 'm7'), (2, 'm7'), (0, '/3'), (3, '/5')]


def _chord_text(key: str, degree: int, suffix: str) -> str:
    fifths, tonic = _KEYS[key]
    flats = fifths < 0
    root = _name(tonic + _SCALE[degree], flats)
    if suffix.startswith('/'):
        bass_degree = (degree + {'3': 2, '5': 4}[suffix[1:]]) % 7
        return f'{root}/{_name(tonic + _SCALE[bass_degree], flats)}'
    return root + suffix


def compose(seed: int) -> dict:
    """Return a .gt-compatible description of one lead sheet."""
    rng = random.Random(seed)
    key = rng.choice(list(_KEYS))
    time = rng.choice(['4/4'] * 4 + ['3/4'])
    beats = int(time.split('/')[0])
    bars = rng.choice([16, 20, 24])
    fifths, tonic = _KEYS[key]
    flats = fifths < 0
    # Melody pitches as diatonic indices from the tonic in octave 4 (0 = tonic, 7 = octave above).
    pos = rng.choice([0, 2, 4])
    scale_pcs = {(tonic + x) % 12 for x in _SCALE}
    measures = []
    lyric_text: list[str | None] = []
    last_pitch: str | None = None   # pitch of the previous note, for tie continuations
    pending_tie = False
    for b in range(bars):
        cells: list[list[Fraction]] = []
        left = beats
        if b % 4 == 3 and rng.random() < 0.6:
            long = rng.choice([c for c in _LONG if sum(c) <= beats])
            cells.append([Fraction(x) for x in long])
            left -= sum(long)
        while left > 0:
            cell = rng.choice(_CELLS)
            cells.insert(rng.randrange(len(cells) + 1), [Fraction(x) for x in cell])
            left -= 1
        notes = []
        last_bar = b == bars - 1
        for ci, cell in enumerate(cells):
            for qi, ql in enumerate(cell):
                is_last = last_bar and ci == len(cells) - 1 and qi == len(cell) - 1
                if pending_tie:
                    pitch = last_pitch
                    lyric_text.append(None)  # no syllable on a tie continuation
                elif rng.random() < 0.07:
                    notes.append(f'r/{_len_token(ql)}')
                    continue
                else:
                    pos = max(-3, min(9, pos + rng.choice([-2, -1, -1, 0, 0, 1, 1, 2])))
                    midi = 60 + tonic + _SCALE[pos % 7] + 12 * (pos // 7)
                    if rng.random() < 0.04 and (midi + 1) % 12 not in scale_pcs:
                        midi += 1  # chromatic neighbour, engraved with an accidental
                    pitch = f'{_name(midi % 12, flats)}{midi // 12 - 1}'
                    lyric_text.append(rng.choice(_SYLLABLES))
                tie = (not is_last) and rng.random() < 0.08
                notes.append(f'{pitch}/{_len_token(ql)}{"~" if tie else ""}')
                last_pitch, pending_tie = pitch, tie
        chord_offsets = [0] if beats == 3 or rng.random() < 0.5 else [0, 2]
        chords = [f'{_chord_text(key, *rng.choice(_chord_names(key)))}@{o}' for o in chord_offsets]
        measures.append((b + 1, chords, notes))
    title = ''.join(rng.choice(_SYLLABLES) for _ in range(rng.choice([3, 4, 5])))
    return {'seed': seed, 'title': f'연습곡 {title}', 'key': key, 'fifths': fifths, 'time': time,
            'measures': measures, 'lyrics': lyric_text}


def _len_token(ql: Fraction) -> str:
    table = {Fraction(4): '1', Fraction(3): '2.', Fraction(2): '2', Fraction(3, 2): '4.', Fraction(1): '4',
             Fraction(3, 4): '8.', Fraction(1, 2): '8', Fraction(1, 4): '16'}
    return table[Fraction(ql)]


def gt_text(sheet: dict) -> str:
    lines = [f"# Synthetic lead sheet, seed {sheet['seed']} (generated by scripts/omr_v3/synth.py; no third-party rights)",
             f"title: {sheet['title']}", f"key: {sheet['fifths']}", f"time: {sheet['time']}",
             f"lyrics1: {''.join(x for x in sheet['lyrics'] if x)}"]
    for num, chords, notes in sheet['measures']:
        lines.append(f"{num} | {' '.join(chords)} | {' '.join(notes)}")
    return '\n'.join(lines) + '\n'


def write_musicxml(sheet: dict, gt_path: Path, out: Path) -> None:
    from music21 import metadata, note

    from scripts.omr_v3.reference import parse_gt, to_music21

    score = to_music21(parse_gt(gt_path.read_text(encoding='utf-8')))
    syllables = iter(sheet['lyrics'])
    for n in score.recurse().getElementsByClass(note.Note):
        n.lyric = next(syllables, None)
    score.metadata = metadata.Metadata(title=sheet['title'])
    score.metadata.composer = 'Capomatic synthetic set'
    score.write('musicxml', fp=str(out))


def render_clean_pdf(xml: Path, pdf: Path, home: Path) -> None:
    from backend.omr_v3.core import _bin, _tool_env

    home.mkdir(parents=True, exist_ok=True)
    subprocess.run([_bin('CAPOMATIC_MUSESCORE_BIN', 'mscore3', 'mscore', 'musescore'), '-o', str(pdf), str(xml)],
                   check=True, env=_tool_env(home), capture_output=True, timeout=300)


def _raster(pdf: Path, dpi: int):
    import tempfile

    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        stem = Path(tmp) / 'page'
        subprocess.run(['pdftoppm', '-r', str(dpi), '-gray', '-png', '-singlefile', '-f', '1', '-l', '1',
                        str(pdf), str(stem)], check=True, capture_output=True)
        with Image.open(stem.with_suffix('.png')) as im:
            return im.convert('L')


def _to_pdf(im, path: Path, dpi: int, quality: int) -> None:
    im.convert('RGB').save(path, 'PDF', resolution=dpi, quality=quality)


def degrade(clean_pdf: Path, out_dir: Path, seed: int) -> None:
    import numpy as np
    from PIL import Image, ImageFilter

    rng = np.random.default_rng(seed)

    # Class 2: ordinary worship-team PDF (exported/scanned once at 200 dpi).
    im = _raster(clean_pdf, 200).rotate(float(rng.uniform(-0.4, 0.4)), resample=Image.BICUBIC, fillcolor=255)
    a = np.asarray(im, dtype=np.float32) + rng.normal(0, 4, (im.height, im.width))
    _to_pdf(Image.fromarray(np.clip(a, 0, 255).astype('uint8')), out_dir / 'ordinary.pdf', 200, 80)

    # Class 3: lower-quality scan (150 dpi, grey paper, blur, noise, skew).
    im = _raster(clean_pdf, 150).rotate(float(rng.uniform(-1.2, 1.2)), resample=Image.BICUBIC, fillcolor=255)
    im = im.filter(ImageFilter.GaussianBlur(0.8))
    a = np.asarray(im, dtype=np.float32) * 0.85 + 30 + rng.normal(0, 10, (im.height, im.width))
    _to_pdf(Image.fromarray(np.clip(a, 0, 255).astype('uint8')), out_dir / 'scan.pdf', 150, 60)

    # Class 4: smartphone photo (perspective, uneven light, ~1500 px wide, JPEG).
    im = _raster(clean_pdf, 220)
    w, h = im.size
    d = 0.03
    src = [(w * rng.uniform(0, d), h * rng.uniform(0, d)), (w * (1 - rng.uniform(0, d)), h * rng.uniform(0, d)),
           (w * (1 - rng.uniform(0, d)), h * (1 - rng.uniform(0, d))), (w * rng.uniform(0, d), h * (1 - rng.uniform(0, d)))]
    coeffs = _perspective_coeffs([(0, 0), (w, 0), (w, h), (0, h)], src)
    im = im.transform((w, h), Image.PERSPECTIVE, coeffs, Image.BICUBIC, fillcolor=255)
    yy, xx = np.mgrid[0:h, 0:w]
    light = 0.78 + 0.22 * (xx / w) * (1 - 0.4 * yy / h)
    a = np.asarray(im, dtype=np.float32) * light + rng.normal(0, 6, (h, w))
    photo = Image.fromarray(np.clip(a, 0, 255).astype('uint8')).filter(ImageFilter.GaussianBlur(0.6))
    photo = photo.resize((1500, int(1500 * h / w)), Image.LANCZOS)
    photo.convert('RGB').save(out_dir / 'phone.jpg', quality=75)


def _perspective_coeffs(dst, src):
    import numpy as np

    rows = []
    for (x, y), (u, v) in zip(dst, src):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    a = np.array(rows, dtype=float)
    b = np.array([c for p in src for c in p], dtype=float)
    return np.linalg.solve(a, b).tolist()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--seeds', type=int, nargs='+', required=True)
    args = ap.parse_args()
    for seed in args.seeds:
        d = args.out / f'syn{seed}'
        d.mkdir(parents=True, exist_ok=True)
        sheet = compose(seed)
        gt = d / 'reference.gt'
        gt.write_text(gt_text(sheet), encoding='utf-8')
        xml = d / 'score.musicxml'
        write_musicxml(sheet, gt, xml)
        render_clean_pdf(xml, d / 'clean.pdf', d / '.mscore-home')
        degrade(d / 'clean.pdf', d, seed)
        (d / 'meta.json').write_text(json.dumps({'seed': seed, 'key': sheet['key'], 'time': sheet['time'],
                                                 'bars': len(sheet['measures'])}, ensure_ascii=False))
        print(f"syn{seed}: key {sheet['key']} {sheet['time']} {len(sheet['measures'])} bars")


if __name__ == '__main__':
    main()
