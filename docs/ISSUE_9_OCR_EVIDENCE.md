# Issue #9: OCR regressions and canonical corpus evidence

Scope: finish the generic OCR recovery rules, prove that parenthesis style survives the whole
pipeline, and run the complete canonical corpus locally with Docker-equivalent runtime settings.
The gate definitions are in [`V1_RELEASE_PLAN.md`](V1_RELEASE_PLAN.md). This file records one
local execution and does not change any threshold.

**Result: the corpus gate is not passed.** Coverage and precision now clear their thresholds and
no fixture regressed. `fixture_quality` still fails on one sheet, `children_of_light`, and no
frozen production baseline was available for comparison. Details are below.

## Environment

| Item | Value |
| --- | --- |
| Date | 2026-09-23 |
| Host | Darwin arm64 (macOS 26.5.1), no container runtime |
| Base commit | `6354f33` (issue #10). After the rebase onto `main` this is `220fd18`, with an identical tree, so the results below still apply. |
| Python | 3.12.2 in a venv installed from the pinned `requirements.txt` (`paddleocr 3.7.0`, `paddlepaddle 3.2.2`, `paddlex 3.7.2`, `numpy 1.26.4`) |
| Runtime settings | Copied from the `Dockerfile` `ENV`: `CHORDTAYLOR_OCR_DET_MODEL=mobile`, `PADDLE_MAX_STITCHED_PIXELS=900000`, `PADDLE_STITCH_MAX_SAFE_PIXELS=900000`, `PADDLE_MIN_STITCH_RESIZE_SCALE=0.85`, `RENDER_USE_INPAINT=0`, `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True` |
| Corpus | All 16 labels in `fixtures/labels` (git tree `b57cdd63`) and their images (git tree `28a40520`). This is the full corpus, not a subset (`corpus_complete: true`). |
| Command | `python scripts/eval_ocr.py --engine paddle --report-json <file>` |

Both trees were run one after the other, from clean exports of tracked files only: `git archive
6354f33` for the baseline, and the tracked files of this branch for the candidate. This is the same
host and runtime settings, but not the Docker image, and not the HF `cpu-basic` canary the release
gate requires.

## Corpus results

| Metric | Gate | Baseline `6354f33` | Candidate |
| --- | --- | --- | --- |
| Mean unique coverage (15 quality fixtures) | ≥ 98.06% | 98.07% | **99.10%** |
| Mean unique precision (15 quality fixtures) | ≥ 88.90% | 89.82% | **90.11%** |
| `fixture_quality` | all pass | FAIL (2 sheets) | **FAIL (1 sheet)** |
| `no_quality_regression` | true | n/a | true against `6354f33` (see baseline note below) |
| Local mean / stddev `/detect` time | local screen only | 11.60 s / 5.42 s | 15.12 s / 6.70 s |

Per-fixture changes between baseline and candidate:

| Fixture | Coverage | Precision | Occurrences | Fixture pass |
| --- | --- | --- | --- | --- |
| `because_i_love` | 76.9% → 92.3% | 58.8% → 63.2% | 44 → 47 (range 45–60) | FAIL → **PASS** |
| `children_of_light` (`strict_unseen`) | 94.1% → 94.1% | 100% → 100% | 32 → 32 (needs exactly 37) | FAIL → FAIL |
| The other 14 fixtures | unchanged | unchanged | identical detected sequences | PASS → PASS |

The candidate lost no baseline occurrences and added no extra chords on any fixture. In
`because_i_love`, the new sharp repair recovered `C#m` and `F#m` from OCR reads `Clm`, `CHm`, and
`Flm`.

Timing: the candidate ran slower on this workstation. The filter changes add only regex work per
OCR token, so the difference is most likely host variance between sequential runs. It was not
investigated further, and local timing is not the release timing gate.

Report files for this workstation session (not tracked):
`cand.json` sha256 `4e0f831d…a7ad72`, `head.json` sha256 `33e5434b…3f71ee`.

### Remaining failure: `children_of_light`

This sheet is a `strict_unseen` label, so it needs exact occurrence count and order. OCR finds 32
of 37 occurrences, with occurrence precision 100%. The five missing occurrences are all `C`. The
raw OCR output for those positions contains no `C` text of any confidence, so the chord is lost at
the detection level before filtering. No generic text-recovery rule can restore it. Fixing it would
need detector or cropping work. It would also make this sheet consumed development data, which is
already true in practice, since it has informed tuning.

One experiment used `PADDLE_DET_DB_THRESH=0.2` and `PADDLE_DET_DB_BOX_THRESH=0.3`, run on this
sheet only. It recovered 1 of the 5 `C` occurrences (33/37). The run also misses the first `Gm7`
on the chorus line. A global detector-threshold change affects every sheet and was not adopted
without a full-corpus and canary timing comparison.

### Baseline availability

The plan's gate compares against the production API or a frozen production report. **Neither was
available.** No production report exists in this worktree, the workstation report path cited in
the release plan no longer exists, and external services were out of scope. The comparison above
is only against the local `6354f33` run under identical settings. It shows that this change does
not regress. It does not satisfy the frozen-baseline requirement.

## Code changes

- `backend/ocr/filter.py`: the OCR confusion repairs are now one validated step. It rewrites a
  candidate and keeps it only if the result is valid chord syntax.
  - Flat five read as `s`: `(bs)`/`(bS)` is repaired after any chord body, and bare `bs`/`bS`
    only after a digit, so `Absus` and `Gbs` are left alone. Slash basses and trailing alterations
    are preserved (`Bm7(bs)/F` → `Bm7b5/F`, `C7bs(b9)` → `C7b5b9`).
  - Sharp read as a stroke (`l`, `I`, `H`, `|`): repaired only for roots A, C, D, F, G, and only
    when chord syntax follows (`Clm` → `C#m`). `Elm`, `Cl`, `Al`, and `Dim` are rejected.
  - A fully parenthesized single chord, including one with its own inner parentheses
    (`(F#m7(b5))`, `(Am7bs)`), is kept as one occurrence with `parenthesis: "both"`.
    Concatenated wrapped rows (`(Am7G)`, `(Am)(G)`) stay rejected.
- `backend/chords/normalize.py` and `transpose.py`: fixed a wrong transposition. `G(b5)` was
  normalized to `Gb5` and parsed as a G-flat root, so +2 gave `G#5`. The parentheses are now kept
  when an accidental extension follows a bare root, and the output stays wrapped: +2 gives
  `A(b5)`.
- `backend/api/main.py`: `/detect` now returns each chord's `style`. `chords_override` accepts an
  optional `style.parenthesis` of `open`, `close`, or `both` and returns 422 for any other value.
  Other style keys are dropped, so the client cannot set renderer-internal styling.
- `frontend/pages/index.tsx`: keeps `style` in the chord state. Before this change, every
  correction sent to `/render` silently discarded the parentheses.

No rule references a song, coordinate, chord sequence, or fixture hash.

## Checks run

| Check | Result |
| --- | --- |
| `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True python -m pytest -q` | PASS: `482 passed, 11 skipped` (baseline was 409 passed, 11 skipped) |
| New filter variants (`tests/test_paddle_ocr_filter.py`) | Positive and negative cases for `bs`/`bS`, slash basses, already-correct `b5`, invalid repairs, sharp strokes, wrapped single chords vs. concatenated chords |
| Parenthesis round trip (`tests/test_api.py::TestParenthesisStyleRoundTrip`) | Real filter → `/detect` style → `/render` in Replace and Above, with and without UI-style `chords_override`. Drawn labels are `(Bm7b5)`, `D`, `(Bm7`, `A)` |
| Frontend `tsc --noEmit` and `node --test test/*.test.mjs` | PASS: clean typecheck, 8/8. Run offline on a tracked-files copy using issue #10's `node_modules` with an identical `package-lock.json`. `next build` was not run. |
| Full canonical corpus, baseline and candidate | Ran to completion. Gate FAIL on `fixture_quality` (see above). |

## Development data

`IMG＿7710.png` is not in this worktree and was not used. As recorded in the release plan, it is
consumed development data and not independent release evidence. The canonical corpus also informed
this tuning, so it is a regression guard only. An independent unseen sheet is still required.

## Blockers

| Gate | Blocker |
| --- | --- |
| Corpus `fixture_quality` | `children_of_light` detects 32/37: five `C` occurrences are missing at detection level |
| Frozen baseline comparison | No production report or production API access. Comparison is local-only |
| Docker / HF canary run | No container runtime, and no canary deployment. Settings were replicated through environment variables only |
| Independent unseen sheet | Still required; `IMG＿7710.png` is consumed |
