# V3 whole-score conversion (experimental)

Status: **opt-in, off by default**. `/detect`, `/render`, `/overlay` and the V1 chord
overlay are unchanged. Accuracy and latency below are measured, not guaranteed; 99 %
and 30 s per page are targets, not runtime limits.

## What it does

```
upload (1-page PDF / PNG / JPEG / MusicXML)        MusicXML skips straight to transposition
  -> one grayscale raster (PDF at 300 dpi; small images upscaled toward 2400 px wide)
  -> GATE 1 preflight (quality.py): staff spacing at the source's native resolution,
     sharpness, contrast  -- fail => chord-only (Audiveris is not even started)
  -> Audiveris 5.11 (pinned commit)          notes, rhythm, key/time, lyrics, measure geometry (.omr)
     || PaddleOCR chord detection (V1 model, same Paddle thread as /detect)
  -> repairs: drop watermark-only voices, strip phantom dynamics/accents, missed ledger lines,
     chord names exported as plain text, footer/garbage lyrics
  -> chord placement: OCR chord boxes -> measure + beat via the .omr stacks/slots
     (left-aligned or centred engraving detected per sheet); Audiveris chords fill empty beats
  -> GATE 2 post-OMR (reliability.py): share of bars that do not add up to the time
     signature, note-head confidence, time signature present  -- fail => chord-only
  -> transposition (music21; chord text only through backend.chords via transpose_chord_text)
       key  : notes + key signatures + chords move; each key-signature region spelled
              toward V1's standard key names (D -1 -> Db, not C#)
       capo : notes untouched, chords written N semitones lower (V1 convention, semitones = -N)
  -> MusicXML (chord suffixes written as MusicXML degrees so MuseScore prints add/sus/(11))
  -> INTEGRITY CHECK (music_guard.py) on the two files handed out: same bars, same notes and
     durations, every pitch moved by exactly the shift (0 for capo), chords kept and moved,
     key signatures = targets  -- fail => HTTP 500, no result
  -> MuseScore 3 -> PDF

chord-only fallback = V1's own /detect + /render "replace" output for the page (main._omr_chord_only):
  only chord symbols are transposed, the notes stay as printed, and the response says so.
  Chords V1 does not recognise stay printed in the original key (the warning says so; on
  low-resolution phone photos and 150 dpi scans recall was 21-90 %, see REPORT.md).
  No chord recognised at all => HTTP 422, never an untouched page labelled as a result.
```

Result modes: `full_score` (MusicXML + PDF) or `chord_only` (page image + PDF of V1's chord
overlay). Responses carry `X-Capomatic-Mode` and, for chord-only, a fixed reason code in
`X-Capomatic-Fallback-Reason` (e.g. `preflight:staff_spacing_too_small`,
`omr:too_many_inconsistent_bars`). A plausible-looking full score is never returned when either
gate fails; time is never a gate (30 s/page is a target).

API: `POST /api/v3/score/transpose.pdf` and `POST /api/v3/score/transpose.zip`
(form fields `file`, `semitones`, `mode=key|capo`). For a full score the ZIP holds
`transposed.pdf`, `transposed.musicxml`, `recognized.musicxml` (before transposition) and
`conversion-report.json` (stage timings, preflight metrics, post-OMR signals, decision,
integrity check, repairs, review warnings); for chord-only it holds `chord-only.pdf`,
`chord-only.png` and the report. Every response is
marked `X-OMR-Accuracy: unverified`.

Frontend: `/score-v3`, shown only when `NEXT_PUBLIC_ENABLE_SCORE_V3=1`, login required
when Auth0 is configured. It is not linked from the main page.

## Configuration

Backend (Hugging Face Space variables):

| Variable | Default | Meaning |
| --- | --- | --- |
| `CAPOMATIC_ENABLE_OMR_V3` | `0` (image) | `1` turns the routes on; otherwise 404 |
| `CAPOMATIC_OMR_REQUIRE_AUTH` | `1` | Auth0 bearer token required (needs `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`) |
| `CAPOMATIC_OMR_RATE_LIMIT` | `6/3600` | conversions per caller per window (seconds); caller = token subject |
| `CAPOMATIC_OMR_TOOL_TIMEOUT_SECONDS` | `300` | hard kill for one external tool (safety net, not a latency target) |
| `CAPOMATIC_OMR_JAVA_OPTS` | `-Xmx1536m -Djava.awt.headless=true` | Audiveris JVM options |
| `CAPOMATIC_OMR_CHORD_MERGE` | `1` | add Audiveris chords on beats PaddleOCR left empty |
| `CAPOMATIC_OMR_KEEP_MARKS` | unset | `1` keeps dynamics, articulations and fermatas (default strips them; all were false positives on the test sheets) |
| `CAPOMATIC_OMR_OCR_LANGUAGES` | `eng+kor` | Tesseract languages for Audiveris text |
| `CAPOMATIC_OMR_MIN_INTERLINE_PX` | see `quality.py` | gate 1: minimum staff spacing at native resolution |
| `CAPOMATIC_OMR_MAX_BAD_BAR_RATIO` | see `reliability.py` | gate 2: maximum share of bars that do not add up |
| `CAPOMATIC_OMR_MIN_CONFIDENCE` | see `reliability.py` | gate 2: minimum combined post-OMR confidence |
| `CORS_ORIGINS` | existing | must include the frontend origin (already true for V1) |

Frontend (Vercel): `NEXT_PUBLIC_ENABLE_SCORE_V3=1` to show the page;
`NEXT_PUBLIC_OMR_API_URL` only if OMR runs on a different origin than `NEXT_PUBLIC_API_URL`.

Concurrency: one conversion at a time per process (second request -> 429). Chord OCR
for V3 is queued on the same single Paddle thread as `/detect`, so a running V3 job can
delay a V1 detection by the ~2-5 s chord pass, but never runs Paddle concurrently.

## Deployment (integrated container, as decided by the owner)

The production `Dockerfile` now also contains Java 25 (Temurin JRE), Audiveris built
from commit `7a36078` (Implementation-Version 5.11.0), Tesseract 4.1.0 `eng/kor/osd`
data (SHA-256 pinned), MuseScore 3, poppler-utils and Nanum fonts. The routes stay off
until `CAPOMATIC_ENABLE_OMR_V3=1` is set, so deploying the image does not change
production behaviour by itself. Measured footprint is in the PR evidence
(`api-container-stats.txt`): Audiveris peaks around 0.8-0.9 GB RSS per page.

Not done here (owner decision): enabling the flag on the live Space, Vercel env vars,
and any production deployment.

Rollback: set `CAPOMATIC_ENABLE_OMR_V3=0` (instant) and `NEXT_PUBLIC_ENABLE_SCORE_V3`
unset. Full removal: revert this PR (router registration is three lines in
`backend/api/main.py`; everything else lives in `backend/omr_v3/`, `scripts/omr_v3/`,
`frontend/pages/score-v3.tsx`, `frontend/lib/score-v3.*` and the Dockerfile stages).

## Security notes

- Login + per-subject rate limit + single slot bound the CPU cost; anonymous use is
  only possible by explicitly setting `CAPOMATIC_OMR_REQUIRE_AUTH=0`.
- Uploads: 10 MiB, magic-byte checks, Pillow decompression-bomb limit, PDF page count
  via `pdfinfo` (exactly one page), MusicXML with `<!ENTITY>` rejected, MXL archives
  limited to 50 members / 30 MiB uncompressed.
- External tools run with a scrubbed environment (no Auth0/Sentry/API keys), a private
  `HOME` inside the per-job temp dir, their own process group and a hard timeout that
  kills the whole group. Tool output is logged server-side only; API errors are fixed
  strings. All job files are deleted with the temp dir.
- Responses are `Cache-Control: no-store`. Nothing is persisted.

## Licensing (needs owner / counsel review before enabling publicly)

| Component | License | Use |
| --- | --- | --- |
| Audiveris | AGPL-3.0 | separate process (CLI). Hosting a network service that runs it, with our one-line build change (jai-core dependency removed), means offering the corresponding Audiveris source to users. |
| MuseScore 3 | GPL-2.0 (+font exceptions) | separate process (CLI) |
| Tesseract data | Apache-2.0 | data files |
| music21 | BSD-3-Clause | Python library |
| Eclipse Temurin | GPL-2.0 + Classpath Exception | runtime |

## Evaluation

`python -m scripts.omr_v3.evaluate --out <dir>` (inside the image) runs the real
pipeline on `tests/omr_v3_eval/` and writes per-sheet PDFs, MusicXML, side-by-side
images, `compare_*.json` discrepancy lists and `summary.json`. References are hand
transcriptions in a bar-by-bar text format (`tests/omr_v3_eval/reference/*.gt`) that
`scripts/omr_v3/reference.py` turns into MusicXML and checks bar lengths for.
The `OMR V3 evaluation` workflow runs this on every PR touching the pipeline and
uploads the evidence as an artifact.
