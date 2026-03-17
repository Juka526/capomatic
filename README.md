# transchord

Upload a church worship sheet image → detect chord symbols → transpose → overlay.

---

## Install (macOS, Python 3.12)

```bash
pip install -r requirements.txt
```

If `paddlepaddle` fails from PyPI (common on Apple Silicon), install from the
official PaddlePaddle CPU index instead:

```bash
pip install paddlepaddle -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
pip install paddleocr opencv-python-headless Pillow
```

---

## Running

**Eval with stub (no dependencies needed):**
```bash
python scripts/eval_ocr.py
```

**Eval with real PaddleOCR:**
```bash
python scripts/eval_ocr.py --engine paddle
```

**Debug a single image:**
```bash
python scripts/ocr_debug.py "fixtures/images/<filename>"
```
Writes `tmp/debug_regions.png` — the original image with each OCR band
highlighted so you can verify the crop geometry visually.

**Start the API server:**
```bash
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True uvicorn backend.api.main:app --port 8000
```

**Kill the API server:**
```bash
lsof -ti :8000 | xargs kill
```

**Overlay (detect → transpose → render):**
```bash
curl -X POST http://localhost:8000/overlay \
  -F "image=@fixtures/images/친구야.jpeg" \
  -F "semitones=2" \
  -F "mode=replace" \
  -o tmp/overlay_output.png
```

| Parameter    | Description                                              |
|--------------|----------------------------------------------------------|
| `image`      | JPEG or PNG sheet music image                            |
| `semitones`  | Semitone shift, `-11` to `11`                            |
| `target_key` | Optional key name (e.g. `Bb`, `F#`) for spelling         |
| `mode`       | `replace` (white box + new chord) or `above` (orange above original) |

**Detect only (JSON response):**
```bash
curl -X POST http://localhost:8000/detect \
  -F "image=@fixtures/images/친구야.jpeg" \
  -F "semitones=2"
```

**Unit tests:**
```bash
python -m pytest
```

---

## Staff-aware chord-band cropping (Section 3.1)

The paddle engine uses **staff-aware band cropping** by default instead of a
global top-40% crop:

1. Detect each staff system using morphological analysis (horizontal-line
   emphasis + connected-components).
2. For each system, compute a narrow chord band directly above the top staff
   line (≈ staff-height pixels tall, with a small margin).
3. Merge overlapping bands and run OCR only on those strips — reducing the
   OCR area and eliminating lyric / footer noise.

**Fallback:** If staff detection finds no systems (blank page, heavy skew,
very low resolution), the pipeline falls back automatically to the old
top-40% global crop.  MVP assumes minimal skew (no deskew required).

---

## Troubleshooting

- **NumPy 2.x `ImportError` (`numpy.core.multiarray failed to import`).**
  PaddleOCR's dependency chain (paddlex → matplotlib) was compiled against
  NumPy 1.x and crashes with NumPy ≥ 2.0. Fix:
  ```bash
  pip install "numpy<2"
  ```
  `requirements.txt` already pins `numpy<2`; this only bites if you installed
  NumPy separately before installing the requirements file.

- **Use PaddleOCR ≥ 3.0.1.** Older versions (2.x) may hang on macOS on first
  model download or produce no output with the `lang="en"` option.

- **First run downloads models** (~80 MB) to `~/.paddleocr/`. Subsequent runs
  use the local cache and are significantly faster.

- **Apple Silicon (M1/M2/M3):** If you get an `Illegal instruction` error, make
  sure you installed the ARM-native PaddlePaddle wheel from the official index
  URL above rather than the PyPI x86 wheel.

- **`show_log=False`** suppresses PaddlePaddle startup noise. Remove it
  temporarily if you need to diagnose model-loading failures.

- **Confidence threshold:** The filter in `backend/ocr/filter.py` is regex-only.
  Low-confidence detections are *not* automatically dropped here; gate scoring
  (Section 4) handles that at the job level.

---

## Project structure

```
transchord/
├── backend/
│   ├── api/            FastAPI server (detect + overlay endpoints)
│   ├── chords/         chord parser + transpose engine
│   ├── ocr/            OCR runners (stub + PaddleOCR) + filter
│   └── overlay/        render transposed chords onto sheet image
├── fixtures/
│   ├── images/         test images (drop .jpg/.png here)
│   └── labels/         ground-truth JSON labels
├── scripts/
│   ├── eval_ocr.py     fixture evaluation loop
│   └── ocr_debug.py    single-image OCR debug output
├── tests/              pytest unit tests
└── requirements.txt
```
