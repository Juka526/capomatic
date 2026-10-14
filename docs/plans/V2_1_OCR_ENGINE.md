# V2-1: Dedicated chord OCR server feasibility

Status: PLAN ONLY. Recommendation: **HOLD production implementation; offer a bounded feasibility experiment for owner approval.** Issue: [#55](https://github.com/Juka526/capomatic/issues/55). Base and owner-reported production: `3929ed86a96d156377649c55714a45eb9c23d719` (`origin/main`, 2026-10-14).

Understood as: build our own Capomatic-specific OCR server, with no PaddleOCR service/model fallback in the candidate serving path, that takes at most half the current chord-detection time and reaches 99% accuracy. Investigate effectiveness first and hold the feature if it is not promising. This supersedes the original prompt's "halve OCR error rates" goal. The owner still must approve any development, including an experimental implementation.

## 1. Decision and evidence

There is a credible reason to investigate a compact chord-only recognizer: chord syntax is small and staff-aware preprocessing already uses OpenCV rather than Paddle. There is no evidence yet that it meets 99% full-page accuracy, and synthetic training may not transfer to photographs/scans. A renamed Paddle wrapper, Paddle fine-tuning or Paddle fallback would not satisfy the clarified goal and is excluded.

The independent tester recommends **GO-RESEARCH only after data/rights and owner approval**, not GO-BUILD. The existing corpus cannot support a 99% claim: most labels describe unique chord types rather than every occurrence, some notes say truth was aligned with OCR output, and rights are undocumented. More than one component can agree on the same wrong answer; neither the current model nor a language model is allowed to generate evaluation truth.

Historical [PR #27](https://github.com/Juka526/capomatic/pull/27) reports 98.78% coverage / 89.72% precision for a candidate. These are unique-type macro measures and exclude the strict-unseen sheet from the averaged denominator; they are not current production occurrence accuracy. Its 16-sheet no-regression check is useful history, not a frozen V2 holdout. Labels and production changed afterwards. Do not turn better labels into claimed model improvement.

A tester-read historical HF report on PR #21's branch had median `/detect` 14,281 ms and median inference 12,794 ms. They are separate marginal medians; subtracting them is only an illustration, not a paired overhead measurement. The current Korean title pass was added later. Current production p50/p95 and exact occurrence accuracy are **NOT RUN**. We will not use 7.1 seconds as a hard current target derived from that old report.

### Current recommendation to the owner

Hold production development now. Authorize at most S0-S1 to obtain independent rights-cleared truth and the current baseline; then authorize S2-S4 only if the budget/profiling shows a plausible 2x end-to-end improvement. No claim that 99% or 2x has already been achieved. If data rights, accurate labels, title compatibility or CPU cost make the goal uneconomic, record HOLD and stop without weakening the goal.

## 2. Exact acceptance proposal

Interpret "50% faster" as **50% less elapsed time**, not 1.5x throughput: candidate warm p50 `/detect` <=0.50 x baseline p50 on the same input/CPU/environment. This interpretation follows the owner's desired twofold speedup and is presented for approval.

Interpret "99% accuracy" as **both end-to-end chord-occurrence precision and recall >=99%**, not character accuracy, unique chord types or performance on already perfect crops. TP requires the complete normalized chord symbol (root, accidental, quality, extension, slash bass) and one correct geometric match. A wrong symbol produces one FN and one FP; duplicates are FP; missed symbols are FN. Rejections/missing pages remain in the denominator. This is not a claim that 99% of pages contain zero mistakes; report error-free-page rate separately.

| Gate | Measurement and acceptance |
| --- | --- |
| Latency | Current production-equivalent baseline and candidate on identical frozen pages, Linux x86_64, CPU quota 2, 16 GB RAM, no GPU. Warm p50 ratio <=0.50; p95 ratio <=1.00; cold-start and queue/upload/title time reported separately, no omitted work. |
| Exact occurrence | Micro precision TP/(TP+FP) >=0.99 and recall TP/(TP+FN) >=0.99 on the independent real-recapture holdout, with >=3,000 occurrences. Synthetic results are separate diagnostics and cannot satisfy this gate. Preserve every accidental, suffix and slash bass. |
| Per-sheet regression | Zero sheets worse in exact occurrence recall/precision than the paired baseline; also retain unique-type coverage/precision, lost-occurrence and new-extra diagnostics from the existing evaluator. Report all per-sheet rows. |
| Staff systems | Independently label original-image Y extents; one-to-one matching with interval IoU >=0.8, fixed before tuning. Precision and recall >=0.99, no per-sheet count regressions; report exact-system-count and chord-to-system assignment separately. No five-line geometry guarantee is implied. |
| Transposition | Existing chord grammar/spelling examples and independent hand-calculated shift cases remain exact; OCR cannot erase extensions or slash bass before transposition. |
| Service compatibility | Existing `/detect` top-level keys, chord keys/types, original-coordinate bboxes and error behavior remain compatible. No image/cache ownership change is smuggled into cm1. Title behavior must be decided before candidate acceptance. |
| Resources | Candidate total OCR weights <=50 MiB, OCR process peak RSS <=1 GiB, whole service <=10 GiB, zero OOM on the fixed stress protocol. These are budgets, NOT measurements. |

Freeze geometric matching, normalization and order rules in the scorer before the holdout. Normalize only documented equivalent notation (for example Unicode versus ASCII accidentals); do not normalize different chord meanings into a match. Emit counts, per-sheet rates and sheet-bootstrap confidence intervals alongside aggregate ratios. The target is an empirical gate; a small sample does not establish a universal 99% guarantee.

Baseline measurement: record production SHA/config/model hashes; use a separate rights-cleared development set for profiling and tuning. A tester can measure the locked baseline before tuning but keeps its outputs/labels and detailed errors sealed from the developer. After model/config/scorer lock, evaluate the candidate once. Warm up both services identically, alternate baseline/candidate order, at least three repetitions per page and >=30 requests per arm, and repeat three paired rounds. Publish timing dispersion and all page failures. If the actual HF candidate cannot be run without deployment (not authorized), mark the HF gate **NOT RUN** and report controlled-CPU feasibility separately. Do not deploy to satisfy a test.

## 3. Dataset and data rights

Start with synthetic/self-composed scores and synthetic chord crops; never harvest user uploads. No GIFTED material, including `fixtures/images/친구야.jpeg` and `fixtures/labels/hey_buddy.json`. These names still occur in tracked fixtures and the current CI smoke test. Existing files remain untouched in planning, and none is run as new evaluation data. An unknown-rights legacy image does not become permitted by removing a filename or cropping it.

Proposed primary holdout minimum: 60 independently composed, rights-cleared pages recaptured by phone/scanner, >=3,000 independently labeled chord occurrences and >=200 staff systems, separate from development material. Add pages if needed to reach all three minima. Human composers/typesetters must not reuse the training generator's chord progressions, templates or layout rules. Synthetic held-out examples remain diagnostic only; their results never enter the primary accuracy denominator. Include faint/skewed staves, dense chord spacing, lyrics, repeat/direction marks, accidentals, extensions, slash bass and hard negatives. Reserve whole layout/template/font-style/recapture families across train/dev/holdout; no augmentations of the same source page cross splits. A one-font synthetic score is not evidence of general font coverage.

Training truth may come from the known synthetic generator; evaluation images receive independent human transcription/geometry inspection by two readers before any OCR. Neither reader authors the generator or model. Evaluation construction must not call the production parser/transposer to create expected outputs. The tester independently authors the acceptance scorer under `tests/ocr_v2/`; a second reviewer checks its matching rules and known-positive/negative oracle cases before its hash is frozen. Developer-owned `scripts/eval_*` may invoke that scorer and export predictions but cannot define the acceptance oracle. Rights manifest per asset: creator/source, license/permission, allowable use, image SHA-256, labels SHA-256, font/version/hash, split and provenance. Freeze image and label manifests before any tuning. Missing sample size, rights or independent labels -> HOLD. Defects found after lock require a new preregistration and rerunning both arms, never score repair for one candidate.

The current evaluator's unique-type metrics stay as historical diagnostics. Add occurrence/geometry and staff scoring explicitly rather than relabeling old numbers. Freeze hard negatives before selecting thresholds. The tester controls held-out assets and does not disclose examples or model errors to the developer until the final one-shot decision.

## 4. Candidate architecture and ownership

Proposed independent OCR service: owned training pipeline -> compact chord detector and sequence recognizer -> exported CPU ONNX weights -> Capomatic OCR worker/server. Train from synthetic/self-owned sources without Paddle weights; use a compact CNN/CTC-style sequence model with a documented chord alphabet. A small learned detector can augment deterministic staff-band proposals when region recall is insufficient. Architecture size, quantization and confidence thresholds are chosen on development data only. Training compute is not silently placed on the production HF CPU; any GPU expense needs a separate decision.

`backend/ocr/**` owns preprocessing, the new inference/service modules and the legacy-callable adapter; `backend/chords/**` is only changed if necessary for a documented parsing issue. `scripts/eval_*` owns prediction-export/profile commands, not the acceptance scorer. New `training/chords/**` and `data/chord-ocr/**` hold synthetic recipes/manifests, never user data. Tester owns `tests/ocr_v2/**`; dev never edits tester files. Do not add cm1 tests to unowned frontend paths. The current Dockerfile copies the repository and `.dockerignore` does not exclude these two new roots. Before creating them, obtain an explicit orchestrator-assigned ownership exception for cm1-dev to add only `training/` and `data/` exclusions to `.dockerignore`; otherwise HOLD that slice. This does not authorize a Dockerfile edit or shipping training data/runtime.

Retain the existing callable `detect_chords_hybrid(image_path, use_ai_fallback=False) -> (items, meta)` as a compatibility boundary, with candidate dispatch implemented inside cm1-owned modules. In the new candidate path, do not import, initialize or call PaddleOCR/Paddle or an external vision service. The old engine may exist solely in a separately selected baseline/rollback environment, never as an automatic candidate fallback. Test import/dependency and request boundaries.

Service proposal: a dedicated internal OCR process exposes a bounded recognition endpoint, with the existing public API facade returning the same `/detect` response and handling the current cache. Local facade port 8101/web 3101 remain as assigned; if the experiment needs a second process, reserve loopback-only 8111 and include RPC time/serialization/RSS in all measurements. cm2 owns any `backend/api/main.py` wiring; no such edits belong to cm1. Before selecting a two-process deployment, compare it with embedding the same independent engine in the existing application process. Either option is Capomatic's own engine; neither may use a Paddle serving fallback. Choose one deployable architecture before the final timing gate, and never compare one path's pure kernel time to another's HTTP time.

Public response remains `{detection_id, song_title, chords, count, original_key, meta}` and chord items `{text, confidence, bbox, style}`. `meta.ocr_engine` truthfully identifies the selected engine without removing old metadata fields; unused model-specific values may be null only if existing consumers tolerate them. Coordinate schema checks with cm2.

**Korean title blocker:** current `song_title` uses a second Paddle pipeline. A chord-only model does not replace Korean text OCR. The new server must not quietly retain this Paddle pass. Present two owner choices: (recommended for feasibility) preserve the response field but explicitly use unknown/manual title entry in cm2 and report title capability as reduced; or add a separately researched non-Paddle Korean-title model, with its entire latency/rights/cost included. No silent title regression or claim of full compatibility. cm2 PDF grouping must support unknown titles and manual grouping in either case. Production development stays HOLD until the owner resolves this.

Proposed narrow cross-cutting prerequisite requiring explicit owner approval and orchestrator assignment: cm1-dev replaces the refused CI smoke input in `.github/workflows/ci.yml` with a self-made rights-cleared fixture; the tester updates any integration fixture references under `tests/`. This workflow is outside cm1's existing ownership and is not authorized by this draft. Do not expand the exception to unrelated CI edits. All three feature CI runs must wait for that safe fixture prerequisite. Requirements/package locks are orchestrator-coordinated, one feature at a time; Dockerfile still requires separate owner approval.

## 5. Dependencies, licenses and model rights

Exact proposed pins below are planning candidates, not installed or approved feature packages. Read upstream LICENSE files; registry classifiers alone are insufficient. Freeze wheel/model hashes and complete dependency licenses before a training or inference experiment.

| Component | Proposed pin | Upstream license / entry gate |
| --- | --- | --- |
| onnxruntime, CPU serving | 1.31.0 | [MIT](https://github.com/microsoft/onnxruntime/blob/main/LICENSE). Python 3.12 Linux CPU wheel and declared NumPy >=1.21.6 observed by tester; actual import/ABI/speed on NumPy 1.26.4 NOT RUN. |
| torch, training only | 2.14.1 | [upstream LICENSE](https://github.com/pytorch/pytorch/blob/main/LICENSE) has BSD-style and third-party notices. Registry license expression differs; reconcile exact distribution notices before adoption. Do not ship training runtime on HF. |
| onnx, export only | 1.23.2 | [Apache-2.0](https://github.com/onnx/onnx/blob/main/LICENSE); declared NumPy >=1.23.2, runtime compatibility NOT RUN. |
| opencv-python-headless | Existing 4.11.0.86 | Wrapper [MIT](https://github.com/opencv/opencv-python/blob/4.x/LICENSE.txt), core [Apache-2.0](https://raw.githubusercontent.com/opencv/opencv/4.11.0/LICENSE); bundled notices require inventory. |
| Pillow | Existing 12.3.0 | [MIT-CMU](https://raw.githubusercontent.com/python-pillow/Pillow/main/LICENSE). |
| NumPy | Existing 1.26.4 for first experiment | [BSD-3-Clause](https://raw.githubusercontent.com/numpy/numpy/v1.26.4/LICENSE.txt). Keep baseline environment intact; test candidate in its own environment rather than upgrading the primary one. |
| DejaVu fonts, synthetic source | 2.37 plus per-file hashes | [Bitstream Vera terms and public-domain DejaVu changes](https://github.com/dejavu-fonts/dejavu-fonts/blob/master/LICENSE). Preserve notices; do not use proprietary system-font fallbacks for training. Additional fonts require explicit pins/rights before dataset lock. |
| Baseline only: PaddleOCR / PaddlePaddle | 3.7.0 / 3.2.2 | [Apache-2.0 OCR](https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/LICENSE), [Apache-2.0 Paddle](https://raw.githubusercontent.com/PaddlePaddle/Paddle/develop/LICENSE). Not part of the new candidate serving stack. |

Custom model bytes and training-source rights are recorded separately from library licenses. No unverified pretrained weights or benchmark datasets. If dependencies cannot satisfy the CPU/ABI/license constraints, HOLD instead of adding an unapproved engine. Published general OCR benchmarks demonstrate a technique exists, not that our exact 99% / 2x goal is feasible.

## 6. Runtime cost and policy impact

Existing [HF CPU Basic](https://huggingface.co/docs/hub/spaces-overview) provides 2 vCPU and 16 GB RAM. Do not assume that a second compute Space can be created on a free account or that a second process adds CPU capacity. No hosting changes are approved. Current model size/RSS on that deployment are NOT MEASURED; record baseline and candidate totals, cold download/load times, warm p50/p95, process-tree RSS and cgroup peak. Candidate model budget <=50 MiB and OCR process <=1 GiB are stop thresholds, not achieved results. Training storage/time/compute is separately reported after an approved experiment.

Policy reference is main's current 20-section policy (`3929ed8`). Feature PRs do not edit privacy/terms.

| Policy section | Proposed change or explicit unchanged condition |
| --- | --- |
| Privacy §1 purpose; §2 items | Explain dedicated chord OCR if necessary; no new user-upload training purpose. Title behavior changes are disclosed if approved. |
| Privacy §4 retention; §5 destruction | Keep current ephemeral processing/LRU behavior unless a separately approved server design changes it; document actual new worker copies, timeouts and cleanup before activation. |
| Privacy §7 additional use | Preserve no secondary use; training uses independent permitted data, never service uploads. |
| Privacy §8 processors; §9 overseas transfer | Same host may require no recipient change; a new recipient/region requires a reviewed update before any transfer. No unapproved remote OCR vendor. |
| Privacy §10 security | Add/verify content-free telemetry, input validation and worker isolation without claiming legal compliance from these controls alone. |
| Privacy §12 cookies and similar technology; §14 rights | No new browser store in cm1; coordinate with cm2 if manual titles/settings create new locally retained data. |
| Privacy §20 changes | Publish any changed processing/retention behavior in a separately approved policy update before rollout. |
| Terms: The service; Accuracy and responsibility; What the service does and does not do | Describe actual scope/limitations. A 99% test result is not a no-error guarantee; preserve no sharing/gallery, no permanent user-score storage and no user-upload training. |

Owner reports frontend Sentry enabled, 5,000 errors/month, `sendDefaultPii=false`. Backend `main.py` also conditionally initializes Sentry when a DSN exists; its production activation is not asserted or inspected. Both pipelines must exclude sheet images, annotation content, camera frames and detected text from errors, breadcrumbs and tags. OCR examples, titles, chord strings, filenames and underlying model exception payloads can carry content; log only fixed error codes/stages, no request bodies or local variables. Defaults alone do not sanitize a parser exception or logging breadcrumb. cm1 sanitizes its own emitted errors; any shared API or telemetry integration change is coordinated through cm2 and a named ownership assignment before editing. No Sentry console/settings change is authorized. Tester locally intercepts frontend and backend envelopes, proves synthetic sentinels are captured through real exception/logging paths, then verifies their exclusion from all outbound payload fields using that same detector. Never send calibration content to production.

## 7. Bounded slices, tests and stop rules

Each slice is roughly 1-2 agent workdays. Human labeling and rights work can dominate elapsed time; do not promise a production system in this timebox. Approve slices, not automatic progression to the full product.

| Slice | Deliverable / independent test / exit |
| --- | --- |
| S0 (1-2 days) | Resolve target definitions, title choice, data/font rights and dependency distribution licenses; tester audits independent labeling and approved ownership. Missing prerequisites -> HOLD. |
| S1 (2 days plus human labeling) | Freeze train/dev/held-out manifests and independent scorer; measure current baseline, seal held-out outputs. Tester calibrates known missed/extra/wrong chord and staff cases. No tuning yet. |
| S2 (2 days) | Offline synthetic detector/CTC training prototype with no Paddle weights/fallback; only development-set learning curves, memory and profiling. Tester checks data isolation, full-string truth and import/network boundaries. |
| S3 (2 days) | Candidate CPU serving/RPC path and title strategy; tester verifies full public contract, process-tree cost, model bytes, negative samples and crash/cancel behavior. Stop if profiling cannot fit half-baseline time. |
| S4 (1 day) | Freeze a single model/configuration and run one held-out evaluation; tester publishes per-sheet baseline/candidate counts and timing, T1-T5 evidence. Any primary gate failure -> HOLD. |
| Owner gate 2 | Review measured feasibility before production implementation/integration. A passing experiment does not authorize deployment, Dockerfile edits or a production switch. |

Research work stops after the S2-S4 five-day prototype/validation budget if both >=99% and <=0.50 latency are not supported. If actual HF validation is unavailable, the result is inconclusive/HOLD for production, not failure proof or a desktop performance claim. No threshold relaxation, repeated held-out tuning or silent substitution of Paddle.

T1 checks every library/API/license claim against official sources. T2 requires regression tests to fail when the real fix is removed and pass when restored. A scoped stash of an already committed fix is a no-op; propose temporary restoration of only the pre-fix file in this isolated worktree, execute the test, then restore the fixed committed file. Use the requested stash/pop workflow only for truly uncommitted fixes and verify the stash exists. This is a requested protocol correction, not permission to alter git history.

T3: clean shell, no `.env`, dependencies installed beforehand; only documented model downloads use network. T4: PASS/FAIL/NOT RUN table with exact commands, outputs and per-sheet held-out results. T5: prove the SAME detector catches a known positive before accepting no request/no error/no match. For network tests, deliberately request a harmless local resource and show it in browser resource timing or the framework request log; for score gates, inject a synthetic omission/extra/wrong accidental and require failure. For telemetry, prove a synthetic sentinel is detectable in a locally captured event before checking its absence. No real score content is sent for calibration.

No product code changed, no training/inference/benchmarks/tests/screenshots ran for this planning PR. Existing `npm ci` completed for setup only. A future full UI gate captures 390, 820, 1024 x1366 and 1280 views; old home pixel differences must be zero.

## 8. Handoff and rollback

Worktree `/Users/juahnkim/transchord-wt/cm1`; branch `v2/ocr-engine`; Herdr `w6`; `cm1-dev` Sonnet 5.5, `cm1-test` Opus 5.5; ports 8101/3101 (proposed internal-only 8111 if needed). Primary Python `/opt/anaconda3/bin/python` 3.12.2 was observed; create an isolated worktree venv only after approving new dependencies. Frontend process variable `NEXT_PUBLIC_API_URL=http://localhost:8101`; no env files copied/printed/committed.

The plan-only commit uses `[skip ci]` because current CI explicitly OCRs the refused GIFTED fixture. Skipped checks are not PASS. Before feature code CI, obtain approval for and complete the safe fixture prerequisite. cm1's safe integration should land first, cm2 second, cm3 last, always merged by the owner. Rebase against current main before readiness only without force-pushing/replacing published history; if those requirements conflict, propose a fresh replacement branch to the owner rather than rewriting this one.

Rollback is an explicit owner-approved switch back to the previously released engine/build, never automatic Paddle fallback inside the new candidate. Stop new candidate admissions, discard transient buffers and return a clear error if inference fails. Preserve the existing release until feasibility and deployment approvals exist. Do not merge, deploy, push main, change consoles or touch the protected fretboard/favicon/home layout files.

Owner choices: (1) keep production on HOLD and approve S0-S1 feasibility preparation, or hold all cm1 work; (2) define 99% as exact occurrence precision AND recall, with detect duration halved; (3) unknown/manual titles for the chord-only experiment, or include a separate non-Paddle Korean-title research budget. The recommended starting decision is S0-S1 only, with no promise or approval of a production build.

## Planning verification (2026-10-14)

Independent reviewer: `cm1-test`, Claude Opus 5.5, through Herdr Roundtrip. Final return token: `cm1-final-plan-20261014-e`; both return markers were recovered and read by the orchestrator. The reviewer changed no repository files.

| Check | Result / limit |
| --- | --- |
| Plan publication review | PASS for planning only: previous material findings resolved; no remaining publication blockers. This is not feature acceptance. |
| Evidence/independence | Official license/source checks and evaluation-design review completed; primary truth, scorer independence and known-positive T5 calibration are specified. Asset rights and human recruitment still gate execution. |
| Product validation | NOT RUN: implementation, model accuracy, runtime/RSS, application telemetry and UI/device behavior. No before/after result or screenshot is fabricated. |
| CI | SKIPPED by plan-only `[skip ci]`; current smoke fixture is refused material. Required implementation checks remain pending. |

Recovery command: `herdr agent read cm1-test --source recent-unwrapped --lines 240`. Result: matching final return markers, no remaining publication blockers, and explicit NOT RUN limitations. Review sources and package LICENSE URLs are listed above.
