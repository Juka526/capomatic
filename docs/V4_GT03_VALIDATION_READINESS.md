# GT-03: validation workflow and source chord readiness

**Decision: BLOCKED_BY_RECOGNITION_DEPENDENCY.** The hash-bound existing OCR models were available, but the single preregistered source-only attempt terminated in native SIGSEGV before returning OCR items. This is an execution blocker, not evidence of chord accuracy or an architecture winner. Independent human labels collected: **0**. The human workflow pilot is prepared, not executed; it can proceed separately from OCR recovery.

GT-03 starts at **`85ce5cf39a85cc1fab48f940d47c6e5cc9bc2c6b`** on `experiment/v4-ground-truth-03` in `/private/tmp/capomatic-v4-ground-truth-03`. GT-01 and GT-02 remain immutable inputs. This is post-reference-access development, not a new blinded accuracy experiment.

## Input preservation and review pilot

The GT-01 baseline signature, final signature, all bound prediction/reference artifacts and original PDF were verified using the unchanged GT-02 verifier. Source identities remain Bb = PDF page 2, A = page 1, G = page 3. Source PNG SHA-256 is `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`; PDF SHA-256 is `1cc64756c0ce47b1db0ea6ac21eefe4685097a04cd4589f954afc712afb605fd`.

The **existing** GT-02 packet's 145-file hash inventory was verified, not regenerated. All 111 native measure cases, 27 system contexts, 3 native page copies and original blank A/B forms remain unchanged. The pilot helper creates only a neutral case-ID schedule and a separate custodian-only linkage record, with no images or musical labels. It preserves the existing case order and full 111-case forms.

Coordinator-only pilot coverage (do not disclose this rationale to readers):

| Version | Printed measures | Workflow coverage |
| --- | --- | --- |
| A | 5; 25–26; 35–36 | Five requested measure cases and full system/page context |
| G | 26–27 | Two requested cases and context |
| Bb | 1, 3 | Opening chord omission regions |
| Bb | 8, 9, 15, 16, 17 | Repeat/first-second-ending context and ambiguous transition |

Total **14 priority cases**, not a new statistical sample. No case selection has been changed to favor recognition outcomes. All 111 remain available. Case-to-page/measure linkage stays private; only opaque IDs go into the reader schedule. The selection itself may prime attention, so the protocol prohibits disclosing hypotheses and does not interpret pilot behavior as prevalence or accuracy.

[Reader/custodian workflow](V4_GT03_READER_WORKFLOW.md) specifies independent A/B sessions, separately verified exclusions including GT-03 involvement, UNKNOWN/uncertainty, byte-preserved raw exports, separate hash-bound freezes before any comparison, and a third independent adjudicator. Original observations cannot be overwritten by adjudication. Pilot forms retain PENDING cases and are explicitly ineligible for the unchanged full 111-case validator. Custody/access and human identity require external controls; this helper does not claim to enforce them. No readers were recruited or contacted by tools; no submissions or adjudications exist.

## Existing source chord inventory: AUDIVERIS_ONLY

The authoritative diagnostic inventory remains [GT-02](V4_GROUND_TRUTH_02_MEASURE_ALIGNMENT.md#4-full-bb-harmony-coverage-audiveris_only), with its original untracked `source-chord-coverage.json` hash-bound in GT-03 preparation. These are coordinator readings, not independent human truth. No source chords were repaired using A/G.

| Printed measure | Bb coordinator candidate | Audiveris exported harmony |
| ---: | --- | --- |
| 1 | Bb | Missing |
| 3 | F | Missing |
| 5 | Gm | Missing |
| 6 | Bb/D | Present |
| 7 | Eb | Missing |
| 10 | Eb | Missing |
| 12 | F | Missing |
| 14 | Gm7 | Present |
| 15 | Bb/D | Missing |
| 16 | Eb | Missing |
| 17 | Bb/D | Missing |
| 18 | Eb | Present |
| 20 | Bb | Missing |
| 22 | F | Missing |
| 24 | Gm7 | Missing |
| 25 | Bb/D | Present |
| 26 | Eb | Missing |
| 27 | F | Missing |
| 28 | Eb | Missing |
| 30 | Bb | Present |
| 32 | F | Missing |
| 34 | Gm | Missing |
| 35 | Bb/D | Present |
| 36 | Eb | Present |

Summary: **24 candidates, 7 exported harmonies, 17 missing**. GT-02 documents text/ending-role losses, including one chord-name retained as EndingText, and numbered words not converted by existing cleanup. This study changes none of those behaviors. Independent literal spelling, chord quality and slash-bass verification is still pending.

## Model availability, provenance and single attempt

The existing local image is exactly `sha256:fb3c1ff7f6428a499b18aae5dc0b71a5c8b03ee709b10ab82e3ab1f28e332b1e`: paddlepaddle 3.2.2, paddleocr 3.7.0, paddlex 3.7.2. A read-only/no-network metadata check confirmed the image-internal caches remain absent. Unlike GT-02's checked image cache, a broader host check located existing PaddleX official-model directories; this does not rewrite the earlier scoped finding.

Existing detector approval is recorded in `docs/V1_RELEASE_PLAN.md` (v6-medium). `backend/ocr/paddle_ocr.py::_get_ocr` selects `PP-OCRv6_medium_det`; because a detector name is explicit and no recognizer override is passed, the installed PaddleOCR/PaddleX `OCR.yaml` default is `PP-OCRv6_medium_rec`. Existing title helpers use v5 mobile detection and Korean v5 mobile recognition. The exact installed constructor/configuration was read without initializing models before preregistration.

| Required cached model | Local HF download metadata revision |
| --- | --- |
| PP-OCRv6_medium_det | `8e0f56fb2ef86b461d99cfc7ac5c137738985f61` |
| PP-OCRv6_medium_rec | `e5a92bcbc5cc1b494628e458d267778f0704fd7c` |
| PP-OCRv5_mobile_det | `0d63e78e2b680928f6b1747d76a08db6e645efb7` |
| korean_PP-OCRv5_mobile_rec | `c02ecaf1f22bfd1c618cce154fd19185b47e663a` |

For each, local `inference.pdiparams`, `inference.json` and `inference.yml` content was checked against its retained HF metadata ETag (SHA-256 for LFS or Git-blob SHA-1), then SHA-256-bound in [preregistration](V4_GT03_CHORD_PATH_PREREGISTRATION.json). This proves local content/cache consistency, not independent publisher attestation or equivalence to currently deployed weights. Copies, not original caches, were used; originals and copies' model files were verified unchanged afterward. No downloads, installs, model substitutions or global cache edits occurred.

Preregistration commit **`062ac7a892a4205a68406f6a8ba1ea2129b752cd`** preceded recognition. The runner binds only Bb source PNG, original Audiveris MXL and OMR; no A/G rasters, reference transcriptions, coordinator candidate inventory or reports were mounted. Backend code and runner were mounted read-only. Network was disabled, memory capped at 4 GiB, CPUs at 2, time at 180 s. The host supervisor would stop only this container at 195 s. This was an isolated source-only development attempt, not a recreation of production deployment conditions.

Planned unchanged path: one `detect_chords_hybrid(..., use_ai_fallback=False)` → original V3 cleanup and alignment/ledger logic → default merge/replace → existing transposition −1/−3 → unchanged full in-memory and write/read integrity guards. No rendering or Audiveris rerun. The AI path was explicitly excluded; this is the existing Paddle-only branch, not a claim to evaluate hybrid external-AI coverage.

**Measured result:** process exit **139 / SIGSEGV**, no host timeout, elapsed **6.370515 s**. Logs show all four existing cached models being created/loaded, followed by a Paddle native segmentation fault with no useful C++ stack. No OCR items or metadata were returned, so cleanup/merge/transposition never executed. The precise native cause is **UNKNOWN**; neither missing weights nor a particular version/CPU/backend incompatibility is proved by this log. No retry or parameter/version change was made.

The raw runner report remains `STARTED`, with its initial `ocr_calls: 0`, because SIGSEGV bypassed Python's `finally`. That is retained forensic evidence, not the final process outcome. `ocr-process-result.json` and `ocr-attempt-summary.json` record the single attempted top-level OCR call, zero returned OCR products and authoritative process failure. Do not interpret the stale initial report as zero attempts or a successful run.

| Mode | Coverage / integrity outcome |
| --- | --- |
| Frozen AUDIVERIS_ONLY | 7 harmonies versus 24 coordinator candidates; original A/G full-guard PASS remains historical evidence |
| EXISTING_V3_CHORD_PATH | One attempted call, native failure, no returned OCR items or assisted MusicXML |
| Improvement / false positives / spelling / quality / slash-bass differences | **UNKNOWN / NOT MEASURED**, not zero or improved |
| New full musical integrity | **NOT_RUN_NO_OCR_PRODUCT**; no PASS, bypass or waiver |

All 24 printed candidate regions remain unresolved for OCR-assisted comparison, including the 17 previous omissions. The failure is not an output eligible for use. The logs, exact command, source/model bindings and process result are local diagnostics under `ground-truth-03-output/`; model/score binaries are untracked.

## Geometry-locked demonstration prerequisites

GT-02's raster/coordinator registration stays fixed: 9 systems and 37 physical regions each; original staff polylines, page dimensions, measure boundaries, system breaks and source note x positions are unchanged. No target coordinates or prediction artifacts were recomputed. A's three merged OMR spans and G's one merged span, the missing A whole note and three tie/bar-junction candidates remain explicit recognition/registration issues.

Before a separate isolated B2 demonstration can be proposed:

1. Independent A/B observations and adjudication must confirm pilot physical measure boundaries, musical identities, repeat context and uncertain source/reference events. Broader claims require all 111 cases, not this curated pilot.
2. Preserve four distinct coordinates: observed physical head center with uncertainty, source semantic staff position, target semantic staff position, and separately calibrated renderer-specific placement anchor. A semantic staff coordinate or small detector residual is not a glyph anchor. Renderer anchors remain **UNDEFINED**; the earlier ledger-repair discrepancy still needs independent physical references and a documented anchor contract.
3. Validate coordinate origin, pixel-center conventions, staff local slope/interline and original dimensions without rescaling; retain original system breaks, measure regions and note x. Legitimate reference spacing differences are not automatically errors. GT-02 residuals are algorithmic diagnostics, never independently verified accuracy.
4. Resolve ownership and source removal/completeness separately. PARTIAL remains noneditable; GT-01 Track A remains 0/133 note and 0/32 beam approvals. A future isolated canvas does not authorize original-pixel erasure.
5. Define and test complete stems/beams/flags, accidentals, ledger lines, attached curves and chord-width geometry. Prove protected lyric/title/footer preservation, target collisions, page/system bounds, no lost/doubled notation, and fail-closed unresolved attachments. No such replacement rendering or B2 is implemented here.
6. Retain unchanged full semantic integrity for any future OCR-assisted baseline before it can be called usable; do not turn a native OCR failure into an Audiveris-only success or waive a chord failure.

These dependencies concern recognition, human reference and rendering geometry at different layers; they do not rank Track A versus Track B.

## Validation, local artifacts and next action

New tools: `scripts/research/gt03_pilot.py` prepares only the schedule; `gt03_chord_run.py` is the frozen single-attempt source-only runner. Synthetic tests cover preserving 111 IDs and blank forms, deterministic 14-case priority, absence of answer fields, changed packet/linkage rejection, forbidden input/output writes, and exact Bb-only OCR input binding. The full targeted run (new GT-03, GT-02, GT-01, V4 and frozen V3 music/gate tests) returned **330 passed, 1 skipped in 8.90 s**; the skip is the existing external MuseScore dependency. Formatting and `git diff --check` passed. Final hash checks are recorded in local `validation-summary.json`. No Full Acceptance. These tests validate software boundaries, not musical correctness or native OCR health.

Local `ground-truth-03-output/` retains pilot reader schedule/private linkage, source/model provenance, source-only input copies, isolated model cache, process command/log/raw report and failure summary. Only diagnostic code, tests, protocols and this coordinator report are committed. **Never distribute that parent output or coordinator report to readers**; give only unchanged native packet, neutral schedule and [reader workflow](V4_GT03_READER_WORKFLOW.md).

Exact custodian handoff: the unchanged packet is `/private/tmp/capomatic-v4-ground-truth-02/ground-truth-02-output/independent-reference-packet/`. Neutral schedule and workflow copies are in `/private/tmp/capomatic-v4-ground-truth-03/ground-truth-03-output/reader-instructions/`; privately retain `pilot/custodian-only.json`, GT-02's `packet-private-index.json` and `custody-pending.json`. Copy the safe materials into separately controlled reader sessions, with a writable copy of only that reader's existing blank form. No distribution or access separation has actually been exercised. Keep the private linkage and all parent directories inaccessible to readers.

Independence review identifies three continuing limitations: coordinator-selected diagnostic cases cannot certify their own answers; agreement among recognition outputs is not independent truth; and disclosing selection reasons would prime readers. The frozen full packet, neutral schedule, separate full transcripts and adjudication address collection design, but no actual human evidence exists yet. A fresh-context document review found no central evidence contradiction and requested explicit test totals and distribution paths; those details are supplied here.

Next action is two independent tracks of preparation: externally recruit eligible A/B readers and separate adjudicator, then freeze pilot observations; separately design a new preregistered native-runtime diagnostic using non-score controls to explain SIGSEGV. This run does not authorize a second score OCR attempt, version change, download or production fix. No whole-score denominator or architecture superiority follows from the prepared pilot.

A subsequent score OCR experiment requires a separate user-authorized task and a new preregistration stating the native-runtime evidence and exact environment. This report neither grants that authorization nor changes existing acceptance rules.

Original source rasters, GT-01/GT-02 artifacts, production V1/V3 behavior, ownership/admission/integrity gates, flags and API/frontend remain unchanged. No source editing, PARTIAL promotion, renderer/B2, merge or deployment.
