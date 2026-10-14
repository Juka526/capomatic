# V2-3: Melody recognition and transposition feasibility

Status: RESEARCH PLAN APPROVED (owner: "모든 작업 승인", 2026-10-14). Contracts/readiness preparation is implemented and tested; actual experiments remain gated on independent data/assets. No hosted adoption or product release is approved. Issue: [#57](https://github.com/Juka526/capomatic/issues/57). This worktree retains PR #51's head `bc6ecdfce595bf8ec954df3b6c34f456fc62a80b` (`plan/staff-transpose`). Current main and owner-reported production: `3929ed86a96d156377649c55714a45eb9c23d719` as of 2026-10-14. Keep this base now; rebase on current `origin/main` before any owner decision to make the PR ready, without force-pushing or rewriting already pushed history. Resolve that future history constraint with an owner-approved replacement branch if a rebase would require rewriting published commits.

Understood as: find which of two rendering methods gives musicians a usable transposed melody sheet sooner, preserve Korean text, and implement a method only after measured research and a second owner approval. The inherited [STAFF_TRANSPOSE_PLAN.md](STAFF_TRANSPOSE_PLAN.md) remains the source of detailed musical correctness gates; this document fixes the V2 comparison, ownership and approval boundaries.

## 1. Recommendation, scope and baseline

Approve at most the rights/labels and bounded comparison research first. Product implementation stays on hold. Start with printed, single-melody treble-staff lead sheets in a fixed major key/time signature. Preserve lyrics, syllable anchors, titles, credits and chord beats. Unsupported structures are rejected as an entire page. The scope does not cover grand staves, multiple voices, mid-score key/time/clef changes, handwritten notation, tuplets, ornaments or complex repeats.

The current product changes chord symbols, not melody notes; therefore successful melody transposition has no current baseline. OMR accuracy, latency, RSS, human correction time and musician ratings are **NOT RUN**. Historical chord OCR numbers cannot substitute for any melody measurement. A small passing sample does not guarantee error-free user output.

Per the owner's revised brief and [issue #55](https://github.com/Juka526/capomatic/issues/55), cm1 now targets a purpose-built non-Paddle OCR server with proposed >=99% exact-chord precision/recall and <=50% current detect time, subject to target approval and feasibility. These are goals, not measured results. cm3 consumes its interface and cannot assume it succeeds. Research can use independently annotated chord snapshots fixed before OMR. If cm1 is held, production integration is also held unless the owner explicitly approves a new dependency arrangement.

## 2. Meaning of capo and key change

Specify intent before research code is written. `intent=capo` permits `capo_fret=0..7`, shifts guitar chord shapes by `-capo_fret`, and leaves melody pitch/key signature untouched. `intent=key_change` permits `semitones=-11..11` and only this mode permits melody transposition. Contradictory fields, out-of-range input and capo-plus-transpose-notes requests return 422. The same numeric -2 must not implicitly select a mode. Reset state on intent change and invalidate stale output revisions.

No automatic octave folding. Any required note beyond three ledger lines above/below the staff is rejected in the initial scope. Recover original key signatures and measure-local accidentals before transposing. Reconcile melody key with chord inference rather than treating a relative-major guess as ground truth. Rewrite actual MusicXML `step/alter/octave`, accidentals and key signatures, not merely an instrument `<transpose>` element ([MusicXML pitch](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/pitch/), [transpose](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/transpose/)). Preserve pitch, duration, rests, ties, pickup measures, beat position and enharmonic policy together.

## 3. Measured comparison and independent truth

Arm A: run OMR, erase only a validated staff/note region, re-engrave that region, and composite it onto the original while retaining protected text pixels. This is the inherited plan's partial re-engraving approach, not moving isolated noteheads while leaving stems/beams/ties behind. Note-level geometry must match original syllable/chord anchors; resizing a whole measure is insufficient.

Arm B: the same pinned OMR output -> MusicXML -> identical musical transposition -> full re-engraving. Text and lyric links must be recovered and checked; clean notation that drops Korean lyrics or credits fails.

Both arms receive the same image, chord snapshot, shift and frozen OMR output. Report each engine/arm separately if a second engine is tested. Compare both arms on the six development snippets only; these are also the tuning data, so this comparison is explicitly in-sample. Choose one engine/arm/configuration before the locked set is opened. Run that single selection on the two held-out snippets once, preserving PR #51's Lock B rule. The development comparison is descriptive research, not held-out proof of superiority. A fair two-arm confirmatory study would need a newly preregistered external set and owner approval.

### Dataset and two locks

Use eight rights-cleared sheets, each cropped to its first three printed systems: six development, two held-out, with at least 500 sounding note events in total. Add the 32 self-made rejection examples (16 excluded structures x2) from the inherited plan and an independently typeset public-domain control with self-written test lyrics. Do not reuse an unlicensed modern arrangement or translation. Existing `친구야.jpeg` / `hey_buddy` and all GIFTED material are excluded, as are every user upload and unknown-rights fixture.

Reader A and reader B independently annotate from original images without model output. Reconcile discrepancies by reading the source; expected transpositions use independent hand calculation, never the product function. Labels include note/rest events, rational onset/duration, original pitch/accidental/octave, ties, measures, original geometry, key/time, Korean text and lyric/chord anchors. Labelers, correctors, final raters and implementation authors have disjoint roles. At least one fresh held-out reader has not seen development outputs or helped design the pipeline. The tester independently authors `tests/omr/scorer.py`; a second reviewer checks event alignment and oracle cases before its rules/hash are frozen. Developer runners export predictions only and cannot define the acceptance oracle.

Lock A before experiments: rights evidence, images/crops/labels/hashes, split, 32 rejection cases, thresholds, alignment metric, timebox, correction procedure and candidate cap of two engines. Lock B before held-out access: one selected engine, rendering arm, preprocessing, models/hashes, renderer/fonts, scorer and acceptance rules. Never pick settings on held-out output. After a failure followed by tuning, retire that holdout to development and obtain a new independently labeled holdout. Changes in labels invalidate both baseline and candidate results.

### Two separate result tracks

1. **Automatic safety track:** zero human fixes. Seal automatic accept/reject before revealing labels. Report every request, including unsupported/failed/timeout results. Only this track can satisfy automated quality and coverage gates.
2. **Human-assisted usefulness study:** processing wall time plus active human correction/verification time, through a independently judged usable sheet. Record queue/upload/cold start separately and also include them in user-perceived total time. Corrected outputs never count as raw OMR accuracy or automatic safety successes.

Use two or more musician correctors who did not make the labels; each sees a given source in only one arm, with counterbalanced arm/order across correctors. They may view the source but not frozen truth, the favored-arm hypothesis or the 20% decision rule. Freeze correction tools and allowed actions for both arms, include retyping Korean text and fixing alignment, and cap active correction at 30 minutes per snippet. Independent final raters compare to truth; the clock does not stop when the corrector merely says "done". Unusable outputs at the cap remain failures/right-censored, never excluded or assigned an invented success time. Report the remaining unblinded rendering-style limitation.

Three independent musician raters grade 1-5: notation readability at print/tablet size, lyric alignment, chord alignment, spacing/collisions, and practical page/line breaks; also answer whether they would perform from it. Anchor 1 = unusable, 3 = readable only with corrections, 5 = ready to perform. Usable means all objective content/anchor checks pass, median rating >=4 in every category, no rating below 3, and all raters answer yes. Rendering style makes blinding imperfect; report it.

Report per-item engine time, correction/verification time, time-to-usable, pass/fail, per-rater scores and rejection reason. Compare usable-within-cap fraction first, then median time among sufficiently observed successes with failures shown separately. No median is reported as estimable if at least half remain censored. Prefer an arm only if it clears all automatic gates, does not lower usable fraction/ratings, and improves paired time-to-usable by >=20% on development cases; otherwise the outcome is inconclusive/HOLD. This 20% is a decision threshold, not a statistical significance claim. No product note editor is in scope; needing one triggers a new owner decision.

## 4. Fixed quality gates

These preserve the inherited plan, including denominators. N is labeled events; unmatched predictions are FP. Pitch accuracy uses correct MIDI matches / (N + FP); rhythm includes rests and requires onset, duration and ties all correct. Geometry/order align events before pitch comparison, so alignment cannot be optimized to make pitches match.

| Gate | Requirement |
| --- | --- |
| Pitch | >=99.5% overall and >=99% for each snippet, with missing/extra/octave errors counted. |
| Rhythm | >=99% overall and >=98% per snippet; exact measure durations including pickups. |
| Key, measure structure | 100% original/transposed key signatures and cancellations, measure count/order/structure. |
| Shifts | -11, -7, -2, 0, +1, +5, +11; accepted output pitch, octave, spelling, key and chord consistency all 100%. Capo negative controls must leave melody unchanged. |
| Text and anchors | Accepted results: exact Korean lyrics/title/credits, syllable/note and chord/beat links; no collisions or erased non-note marks. A has zero changed protected pixels; B has exact independently labeled content/links. |
| Silent error | Zero wrong, missing or extra notes and zero erroneous automatically accepted snippets. A warning/confirmation checkbox cannot erase an error. |
| Useful acceptance | >=80% of 8 snippets x7 shifts (56 requests), and >=80% of the locked 2x7 subset, including ledger-line/overlap refusals in denominators. Zero accepts fails. |
| Unsupported inputs | Zero false acceptances in the 32 fixed rejection cases, with a reason per case. |
| Release, separately approved | Ten new independent full pages, >=2,000 notes across all systems, same quality gates, >=80% of 70 requests accepted, silent errors 0. Snippet results are not full-page readiness. |

Block downloads for detected wrong notes, missing/uncertain lyrics, unresolved geometry or unsupported structures. All result-serving paths enforce the block server-side, not just a disabled button. Present the original and precise coarse issue locations without claiming perfect detection of unknown errors. No automatic choice of arm B after A fails.

## 5. Architecture, ownership and costs

cm3 owns only new `backend/omr/**`, `research/melody/**` (prediction exporters and experiment runners, not the acceptance scorer) and its plan. Tester owns `tests/omr/**`, including the independently authored scorer; no tester product edits. cm1 owns `backend/ocr/**` and `scripts/eval_*`; cm3 never edits them. cm2 owns API mounting, main/home/i18n and reader camera headers. Propose a new `backend/omr/intent.py` domain contract consumed through cm2's `backend/pdf/intent_adapter.py` rather than changing existing home controls or the legacy overlay renderer. Agree the schema before implementation. Existing `backend/overlay/render.py` and `frontend/lib/transpose-control.mjs` remain unchanged in research. Any later common intent implementation gets one named owner before edits. `research/` is not excluded by the current `.dockerignore`; keep this branch local/non-deployed and require an explicit coordinated exclusion before any future product packaging. No Dockerfile edit is included.

Input boundary: upright RGB source dimensions/hash, chord items `{text, confidence, bbox, style}`, confirmed key and explicit intent. `bbox` is in original-image coordinates; null boxes are not safe for automatic alignment. Staff candidate API currently returns only sorted `(top_y, bottom_y)` pairs, not five staff lines or x extents. cm3 must derive/validate its own note geometry; do not treat a chord band as a melody crop or calculate pitch from staff-height/4 without line validation.

Research is a local CLI with machine-readable score/events/geometry and per-request acceptance records. A later product service would be isolated from chord OCR compute, with one executing job and one waiting, owner-scoped random capabilities, bounded source/result storage, revisioned output and cancellation. Neither extra endpoints nor an async queue eliminate CPU contention on a shared 2-vCPU host. A separate HF service is only a proposal: do not create/deploy it, change Dockerfile, purchase compute or alter env/console settings.

| Cost item | Budget / evidence status |
| --- | --- |
| Reference CPU | Current [HF CPU Basic](https://huggingface.co/docs/hub/spaces-overview): 2 vCPU, 16 GB RAM; verify account eligibility before proposing new compute. No new service is authorized. |
| Processing | Warm p95 <=120 s, max <=180 s; cold startup+processing <=240 s. NOT RUN. Measure >=20 warm requests with stage times and first cold start separately. |
| Memory | Process-tree/cgroup peak <=10 GiB, single worker. NOT RUN; include Java/native child memory, not just heap. |
| Model/package size | oemer published ONNX assets approximately 67.5 MB +36.7 MB, rights unresolved; Audiveris full native/JVM/language-data footprint NOT MEASURED. Log exact model and installed bytes at the research gate. Proposed total model/font/language assets <=1 GiB; exceedance returns to the owner. |
| Existing service | Paired feature-off vs notes-load runs, >=30 requests per path, three rounds; existing detect/render p50/p95 slowdown <=5%, 5xx/OOM 0. NOT RUN; isolated deployment cannot be assumed available. |
| Human effort | Prior plan estimates 14-23 person-hours for labels; additionally schedule correctors and three raters. These are estimates, not completed or booked work. |

Research timing must use rights-cleared development data; any held-out model numbers must be reported in a separate per-sheet before/after table only after Lock B. Do not substitute desktop timing for HF CPU or upload evaluation files to an unapproved service.

## 6. Dependency choices and rights

No engine or feature package is installed by this plan. Read upstream license files and resolve code, weights, training data, fonts, language packs and renderer separately. Selecting a permissive code license does not clear its model weights.

| Component | Proposed pin if approved | License source and adoption gate |
| --- | --- | --- |
| Audiveris, first research candidate | 5.11.0, commit `9e1e55cd2746037d059345881c53e6a6754bffbd` | [AGPL-3.0](https://raw.githubusercontent.com/Audiveris/audiveris/master/LICENSE). [Build properties](https://raw.githubusercontent.com/Audiveris/audiveris/5.11.0/gradle.properties) require Java 25 and tessdata 4.1.0. Owner must approve license review/research use first; production adoption remains a separate decision. |
| oemer, possible second candidate replacing homr | 0.1.8 | [MIT code](https://raw.githubusercontent.com/BreezeWhite/oemer/main/LICENSE). ONNX checkpoint license and underlying data rights unresolved. Its declared GPU runtime is not approved for the CPU experiment; a separately reviewed CPU installation path must use onnxruntime 1.31.0 and existing NumPy 1.26.4, with import/ABI verification. No automatic GPU package substitution. **Do not download/adopt weights until cleared.** |
| onnxruntime, only for a cleared CPU oemer path | 1.31.0 | [MIT](https://raw.githubusercontent.com/microsoft/onnxruntime/main/LICENSE). Compatibility and exact dependency lock remain M0 entry checks, not a claim that upstream oemer already supports this configuration. |
| Verovio, candidate renderer | 6.3.0 | [LGPL-3.0](https://raw.githubusercontent.com/rism-digital/verovio/develop/COPYING.LESSER); review distribution/relinking and bundled fonts. Korean rendering is NOT VERIFIED. |
| music21, candidate structural transform | 10.5.0 | [BSD-3-Clause code](https://raw.githubusercontent.com/cuthbertLab/music21/master/LICENSE). Exclude its separately licensed corpus; verify an installation with no corpus data before use. |
| Tesseract language data | tessdata 4.1.0 `kor` and `eng`, hashes frozen before use | [Apache-2.0](https://raw.githubusercontent.com/tesseract-ocr/tessdata/main/LICENSE); verify exact files and notices rather than assuming all assets are covered. |
| Temurin JRE, proposed Linux x86_64 HotSpot runtime | `25.0.4.1+1`, `OpenJDK25U-jre_x64_linux_hotspot_25.0.4.1_1.tar.gz` | [GPL-2.0 source license](https://raw.githubusercontent.com/adoptium/jdk25u/master/LICENSE); inspect exact distribution exceptions and bundled notices in M0 before adoption. Freeze the [published SHA-256](https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.4.1%2B1/OpenJDK25U-jre_x64_linux_hotspot_25.0.4.1_1.tar.gz.sha256.txt). No runtime installation is authorized now. |
| Noto Sans CJK Korean, candidate lyric/title font | Sans2.004, commit `523d033d6cb47f4a80c58a35753646f5c3608a78`, `Sans/OTF/Korean/NotoSansCJKkr-Regular.otf` | [SIL OFL-1.1](https://raw.githubusercontent.com/notofonts/noto-cjk/Sans2.004/LICENSE). Freeze actual file SHA-256 and check all needed glyphs before use; prohibit fallback to unrecorded system fonts. |
| Playwright Chromium, research SVG-to-PNG rasterization only | @playwright/test 1.64.0 plus its exact browser revision | [Apache-2.0 wrapper](https://raw.githubusercontent.com/microsoft/playwright/main/LICENSE); inspect Chromium bundled notices, freeze browser binary/hash and font files in M0. Render local SVG with external resources/network blocked and fixed scale/background. Include browser memory/time in measurements. This is an experimental rendering option, not an approved product dependency. |

Homr AGPL and Clarity-OMR GPL are not extra default experiments. Limit to two fully cleared candidates. If the owner rejects copyleft and the MIT candidate's weights cannot be cleared, HOLD; do not silently substitute. No Dockerfile edit or GPL/AGPL adoption is authorized merely by approving the plan document.

## 7. Policy changes and error reporting

Reference the 20-section privacy policy on production/main `3929ed8`, even though this worktree starts from PR #51's older base. Do not edit `/privacy` or `/terms`.

| Policy location | Proposed changes for a separate reviewed policy PR |
| --- | --- |
| Privacy §1 purpose; §2 items | Add opt-in melody recognition, note/lyric structure, transformation settings and output score; distinguish research datasets from user data. |
| Privacy §4 retention; §5 destruction | Define any future job TTL (proposed completion+30 minutes), cancellation/failure cleanup and model-worker temporary files, rather than inheriting current no-TTL LRU claims. |
| Privacy §8 processors; §9 overseas transfers | Identify the actual notes compute recipient, country, data and purpose before a separate service exists; do not assume unchanged routing. |
| Privacy §10 security | Add owner-scoped jobs, content-free error reporting, output gating and strict XML external-entity/network denial. |
| Privacy §11 sensitive and pseudonymized information | No face recognition or new sensitive-information purpose is proposed; review actual note/lyric processing scope without assuming a legal classification. |
| Privacy §12 cookies and similar technology | No new browser store in research. Disclose optional local result storage only if later adopted. |
| Privacy §14 user rights | Describe future result deletion/access controls if jobs or local results are added; no new collection or user store in this research phase. |
| Privacy §19 video devices | Unchanged: cm3 does not use a camera. |
| Privacy §15; §20 | Explain musical assistance and uncertainty without inventing a legal classification; publish changed scope and effective date before activation. |
| Terms: The service; Accuracy and responsibility; Copyright and what you may upload; Results are for your personal practice only; What the service does and does not do | Add melody and re-engraving scope, lyric/arrangement rights, detected-error download blocking and limitations. Preserve no distribution/gallery/sharing, no user-upload training and no permanent score storage. |

Owner reports frontend Sentry now enabled, free-plan quota 5,000 errors/month and `sendDefaultPii=false`. Backend initialization is conditional; activation is not assumed or inspected. All three features must exclude sheet images, annotation content, camera frames and detected text from error messages, breadcrumbs and tags on both paths. For cm3 this includes lyrics, titles, credits, MusicXML and chord/note sequences. Use fixed error/stage codes; strip underlying engine exception strings if they embed score data, paths or input. Test locally intercepted real application exception/logging paths with synthetic sentinels and T5 positive controls, not only fabricated envelopes. Existing Sentry disclosure belongs to privacy §§4, 8 and 9; no score-content telemetry category is proposed. Do not change Sentry console/settings or send test content to production.

## 8. Slices, verification and stop decisions

About 1-2 agent workdays per slice; estimates exclude human recruitment and rights/license approval. No slice starts before owner approval. Developer and tester work sequentially within cm3.

| Slice | Deliverable and independent verification |
| --- | --- |
| M0 (1 day) | Rights and dependency/license/pin register, intent/geometry contracts. Tester confirms every asset and rejects missing rights, including oemer weights. No engine if missing. |
| M1 (2 days + human labeling) | Lock A dataset and independent truth/scorer specification; tester audits missing events, exclusions, denominators, hash/split isolation. No tuning before lock. |
| M2 (1-2 days) | Allowed-engine CPU/geometry feasibility only; tester reports raw events/anchors, title/lyric loss, time/RSS and NOT RUN where needed. Stop if note-to-source positions cannot map within this slice. |
| M3 (2 days) | A region-compositing experiment; tester checks protected pixel identity, note/lyric/chord alignment and negative capo controls. |
| M4 (2 days) | B full re-engraving experiment from identical OMR output; tester checks all content/anchors and measured comparison protocol. |
| M5 (1 day + musicians) | Development-only human correction/rubric comparison, fixed selection rule and Lock B. Report HOLD if no usable winner. |
| M6 (1 day) | One locked evaluation of selected configuration plus frozen rejection set; per-sheet gates and costs. Any failure blocks implementation. |
| Owner gate 2 | Submit measured research and proposed chosen approach. Only explicit approval permits a new sliced MVP plan and implementation. |

T1: cite official docs and LICENSE; do not let two model opinions count as independent musical truth. T2: fail-before/pass-after each regression. The original stash command is a no-op for already committed fixes; propose a temporary file-level pre-fix restoration, then restore the committed fixed file, without history rewrite or touching tester tests. Use stash only when the scoped fix is actually uncommitted and verify it created a stash. This protocol correction is part of the approval request.

T3: clean-shell suite with no `.env`; only documented model downloads use network after dependency setup. T4: exact commands, outputs and PASS/FAIL/NOT RUN, not invented completion. T5: before trusting no network/no error/no match/no changed pixels, prove the same detector fires on a known positive. Use a deliberate harmless request caught by resource timing or the framework request log for browser network checks; synthetic wrong notes, changed protected pixels and content sentinels must trigger the corresponding gates. Never leak real score data for calibration.

Stop on missing data rights/independent musicians, unapproved licenses, inability to preserve Korean content/anchors, any silent error, <80% acceptance, an over-budget engine or no effective time-to-usable improvement. Insufficient evidence means HOLD rather than weakening gates. If a renderer requires a note editor or broader musical scope, return to the owner. Rebase against the owner-merged cm1 and then current main only under the no-force-push constraint; integration order remains cm1 -> cm2 -> cm3, owner merges.

Worktree `/Users/juahnkim/transchord-wt/cm3`, Herdr `w8`, `cm3-dev` Sonnet 5.5 / `cm3-test` Opus 5.5; ports 8301/3301, guest frontend process variable `NEXT_PUBLIC_API_URL=http://localhost:8301`. Existing `npm ci` completed; use primary Python `/opt/anaconda3/bin/python` 3.12.2 until feature dependencies require a worktree-local environment. No env files are copied. Models, tests, screenshots and research runs are NOT RUN for this plan PR.

Rollback: research is isolated and changes no product behavior. Any later product feature stays default-off; rollback stops new notes jobs, removes pending results and restores the last owner-approved code by a new commit, with no deployment by the orchestrator. Plan commits use `[skip ci]` because existing CI processes the refused GIFTED fixture; no CI pass is claimed. Keep Draft; no merge/main push/force push, deployment, settings changes, protected-file edits or home layout changes.

Owner choices: approve only M0-M1 rights/labels preparation, or also a bounded research experiment once engine rights/runtime pins are cleared; permit Audiveris license review/research use or hold copyleft candidates. Implementing either rendering arm as a product requires gate 2 regardless.

## Planning verification (2026-10-14)

Independent reviewer: `cm3-test`, Claude Opus 5.5, through Herdr Roundtrip. Final return token: `cm3-final-plan-20261014-e`; both return markers were recovered and read by the orchestrator. The reviewer changed no repository files.

| Check | Result / limit |
| --- | --- |
| Plan publication review | PASS for planning only: previous material findings resolved; no remaining publication blockers. This is not feature acceptance. |
| Evidence/independence | Official license/source checks and evaluation-design review completed; primary truth, scorer independence and known-positive T5 calibration are specified. Asset rights and human recruitment still gate execution. |
| Product validation | NOT RUN: implementation, model accuracy, runtime/RSS, application telemetry and UI/device behavior. No before/after result or screenshot is fabricated. |
| CI | SKIPPED by plan-only `[skip ci]`; current smoke fixture is refused material. Required implementation checks remain pending. |

Recovery command: `herdr agent read cm3-test --source recent-unwrapped --lines 240`. Result: matching final return markers, no remaining publication blockers, and explicit NOT RUN limitations. Review sources and package LICENSE URLs are listed above.

Approved preparation evidence: [V2_3_PREPARATION_REPORT.md](V2_3_PREPARATION_REPORT.md). Code tests pass; real assets, independent humans/scorer and the musical comparison remain NOT RUN / NOT READY.
