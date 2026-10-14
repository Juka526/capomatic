# training/chords — chord-OCR data preparation (V2-1 S0/S1)

Plan: `docs/plans/V2_1_OCR_ENGINE.md`. No training, no serving code, no Paddle imports here.

## Resolved goals (owner approval "모든 작업 승인", 2026-10-14)
- Speed: detect elapsed time **halved** (warm p50 `/detect` <= 0.50 x baseline, same input/CPU).
- Accuracy: exact chord-occurrence **precision AND recall >= 99%** on the independent real-recapture holdout.
- Title: the feasibility candidate uses an **unknown/manual title** field (no Paddle title pass).
- Status: real holdout and two independent human readers do not exist yet -> **HOLD / NOT RUN**.

## Files
- `manifest.json` — rights/provenance + sha256 for every page and font. Only item today: the CI fixture.
- `gen_ci_fixture.py` — regenerates `fixtures/images/ci-selfmade.png` (`--check` compares to the manifest hash;
  bytes depend on the Pillow/FreeType build, so a mismatch on another build is a hint, not proof of tampering).
- `fonts/` — DejaVu Sans 2.35 (the copy bundled with matplotlib 3.9.2) + license. The plan pinned 2.37; not used.
- `dataset_check.py` — fail-closed validator: `python training/chords/dataset_check.py [manifest]`
  (exit 0 ready, 1 invalid, 2 HOLD), `--selftest` runs a known-positive plus negative oracle.

## Rules enforced
Explicit allowed license and `user_upload=false`/`legacy_fixture=false` per page; sha256 of every file; GIFTED/친구야/
hey_buddy/upload paths rejected; a family lives in one split; a composer in the holdout may not appear in train/dev;
holdout pages must be `real_recapture` with `independent_composition=true`, no `generator_id`, and a verified truth
file. Synthetic pages are `train`/`dev`/`ci_diagnostic` only and never count toward the gate. Primary gate:
>= 60 pages, >= 3000 chord occurrences, >= 200 staff systems, counted from the truth files.

## Human-label (truth) format, one JSON per page, referenced by `items[].truth`
```json
{"image_sha256": "<page sha256>",
 "readers": ["reader-a", "reader-b"],
 "staff_systems": [{"y0": 120, "y1": 190}],
 "chords": [{"text": "D/F#", "bbox": [x1, y1, x2, y2], "system": 0}]}
```
Original-image pixels; `system` indexes `staff_systems`; `text` is the full symbol (root, accidental, quality,
extension, slash bass) transcribed by two readers who did not author the generator or model, before any OCR.
Truth must not be produced by the production parser/transposer or any OCR. The acceptance scorer is tester-owned.
