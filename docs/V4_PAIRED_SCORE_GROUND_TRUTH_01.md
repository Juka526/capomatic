# Paired score ground truth validation 01

**Architectural recommendation: INSUFFICIENT_EVIDENCE.** The musical baseline completed and passed the unchanged full V3 integrity guard for both shifts. This does not establish recognition accuracy: opening chords are missing, and independently usable whole-score reference correspondence is not yet established. Neither architecture produced a score. No acceptance rule changed.

## 1. Source and reference identities

Supplied title: **주님의 마음 있는 곳**, filename NFC `A 주님의 마음 있는 곳 (@Bb).pdf` (actual macOS filename is decomposed Unicode).

| Role | PDF page, 1-based | Declared and visually checked key | Shift from source |
| --- | --- | --- | --- |
| Original source | **2** | **Bb major**, two flats | — |
| Reference target 1 | **1** | A major, three sharps | **−1 semitone** |
| Reference target 2 | **3** | G major, one sharp | **−3 semitones** |

A→G reference interval is −2 semitones. The supplied versions are references to investigate, not assumed error-free ground truth. Professional preparation/authenticity was not independently authenticated.

## 2. PDF provenance and rasterization

Located explicitly in `/Users/juahnkim/Downloads/` by Unicode NFC comparison; no substitute/download. Original file: 3,574,780 bytes, three unencrypted pages, each MediaBox/CropBox 2520×3564 pt, rotation 0. Producer: macOS Quartz PDFContext, creation/modification 2026-10-18 11:58:03 KST. Only metadata was inspected for all pages before prediction.

| Immutable object | SHA-256 |
| --- | --- |
| Supplied three-page PDF | `1cc64756c0ce47b1db0ea6ac21eefe4685097a04cd4589f954afc712afb605fd` |
| Source page 2 raster | `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de` |
| A reference page 1 raster | `b094035763fc02685edcb1a57960833cc95b52e95034fb6cbaaba2c929e7fa67` |
| G reference page 3 raster | `2d5cae7034a78e06d62975e92dc2f9666311fb0a06659dfe49cb2fdfd8e739bc` |

Fixed before results: Poppler **26.09.0**, 72 dpi, grayscale `L`, 2520×3564 px; no subsequent scaling, rotation or correction. At this PDF's unusually large point dimensions, V3's default 300 dpi would exceed its unchanged 40M-pixel limit. The predeclared 72 dpi research input remains within that limit and has approximately 18 px staff spacing. It is not the default V3 PDF rasterization setting.

Coordinator extraction commands (the exact decomposed path and full argv are retained in local `coordinator/pdf-provenance.json` and `reference-opening.json`):

```sh
pdfinfo -f 1 -l 3 -box "$supplied_pdf"
pdftoppm -r 72 -f 2 -l 2 -gray -png -singlefile "$supplied_pdf" source-only/source
# ONLY after signed baseline freeze:
pdftoppm -r 72 -f 1 -l 1 -gray -png -singlefile "$supplied_pdf" reference-input/A
pdftoppm -r 72 -f 3 -l 3 -gray -png -singlefile "$supplied_pdf" reference-input/G
```

`$supplied_pdf` denotes the explicitly located file, not a guessed path. The PDF was read only; no page extraction overwrote it.

## 3. Code revision, isolation and baseline freeze

Worktree `/private/tmp/capomatic-v4-ground-truth-01`, branch `experiment/v4-paired-ground-truth-01`. Explicit common research base: **`04687ce6ac65eb4d9505365b92aa96c886c88530`**, verified by `git merge-base` of the existing A/B branches and ancestor checks of validation branches. Existing development worktrees/branches were not rewritten or merged.

Prediction/preregistration commit: **`9444b14e108b573f124b7ed6a14207d779aeed7c`**. [Frozen protocol](V4_PAIRED_SCORE_GROUND_TRUTH_01_PROTOCOL.json). Prediction helper SHA-256: `35da9acbcb08bf273e8880f64a6e5284b9a1143e2d28b7509078b374ae6c2dfa`.

The source-only Docker worker had **network=none**, read-only code and page-2-only PNG mounts, initially empty writable prediction output, no original PDF, no reference pages, no host home or Docker socket. Mounts were inspected before launch and saved. References were not rasterized or viewed until prediction freeze. Both reference workers later mounted predictions read-only. This is enforced **process-level source/reference separation**, not an independently blinded human study; the coordinator can access the original PDF and is not an independent annotator.

Local image: `sha256:fb3c1ff7f6428a499b18aae5dc0b71a5c8b03ee709b10ab82e3ab1f28e332b1e`. Python 3.12.15, music21 9.9.1, Pillow 12.3.0. Installed Audiveris JAR reports 5.11.0; the unchanged Dockerfile pins build source `7a36078e7ba0c006052c1f661b949cf9b729f505`. No image rebuild or download occurred; exact installed runtime is bound by image ID.

**Infrastructure exception, preserved rather than hidden:** the first native initialization failed because Docker's temporary tmpfs was `noexec`, preventing `dlopen(libjnileptonica.so)`. It failed before score recognition. Its files/logs were preserved. One pre-reference environment-only retry added `exec` to `/tmp`; all code, raster and recognition settings remained identical. This is an explicit amendment to the protocol's single source-run count: one failed startup plus one actual source-recognition run, not a result-based recognition retry.

Before reference access, 39 available prediction files—including the failed startup, source recognition, both target XML/guards/plans, A/B diagnostics and supplemental checks—were hash-bound and made read-only. Baseline manifest SHA-256 **`68f327663cf91011f62b16db770cba4e06aea1323d0b06bade1cbfe2c904ad49`**. RSA/SHA-256 detached signature was verified with OpenSSL 3.6.4 before opening references and again during evaluation. Public-key SHA-256 `b55a88e832c781eaf96e1faf8b09accb8909224e04e675330d95e4596544f0b7`. This is an automated local coordinator signature, not a human endorsement, externally authenticated identity or trusted timestamp. Baseline records production-module hashes, protocol/configuration, image, guard results and failed/unsupported steps. No frozen predictions were regenerated after reference access.

## 4. Source recognition

Existing V3 Audiveris integration and cleanup were reused, followed by V4 strict matching/provenance. **No PaddleOCR chord detection/merge** was run. This is the Audiveris diagnostic path, not an end-to-end production V3 benchmark.

- 1 part, 37 recognized measures, 133 pitched notes, 36 rests; 169 note/rest events.
- Detected signature −2 fifths (Bb); 9 systems, 9 staves.
- 133 visual heads, **133 DIRECT matches**, 0 provenance transfers, 0 ambiguous/unmatched.
- **0 ledger repairs**: this sheet does not test the earlier corrected-ledger anchor failure.
- Only **7 recognized harmony symbols**; 59 exported lyric items. Complete XML retains durations, voices, accidentals, ties/slurs, repeats and lyrics; the graph retains source geometry/relations and text regions.
- Existing cleanup removed 3 lyric items, 32 articulations, 1 dynamic and 1 fermata from semantic export. Source raster content remains intact; these removals are not layout-preservation evidence.

OMR SHA-256 `857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638`; recognized XML `d97e46d5353b8e4da2f17a38e9b0943c66b76ed41d2ecbc8ae8376e659d57f04`. Source recognition completed but is **visibly incomplete in harmony coverage**. A 133/133 semantic↔head correspondence says nothing about missing printed symbols.

## 5–7. Bb→A, Bb→G and unchanged integrity

Both shifts start from the **same single cleaned/exported source**; neither uses reference recognition to repair it. Here “cleaned” means the existing rest-only-voice, lyric, chord-word, mark and layout cleanup calls, followed by export. No ledger pitch changed, and no manual or reference-derived correction was made.

| Check | Bb→A, −1 | Bb→G, −3 |
| --- | --- | --- |
| Target signature | +3 fifths, A | +1 fifths, G |
| Measures / pitched notes / rests / harmonies | 37 / 133 / 36 / 7 | 37 / 133 / 36 / 7 |
| Unchanged full guard, in memory | PASS, no issues | PASS, no issues |
| Unchanged full guard, after XML read/write | PASS, no issues | PASS, no issues |
| Exact semantic note/voice/rhythm identity | Preserved | Preserved |
| Existing V3 interval spelling conformance | Preserved | Preserved |
| Tie/slur attachment XML event signatures | Preserved | Preserved |

The supplemental checks do not replace the full guard. Spelling conformance uses existing V3 interval logic, not independent ground truth. The guard checks recognized note/rest rhythms/pitches, keys and chord semantic/root/bass invariants; it cannot discover a chord absent from the source recognition. Voice identities and tie/slur signatures were checked separately rather than attributed to unsupported guard coverage. Accidental pitch meaning is internally checked through pitches/keys; full visual accidental placement is unverified.

Target XML SHA-256: A `a063a9f6c3201086c6be4ecf7e45bf4c1e8084f9e878c10adaea9ecdf052c919`; G `4fad6028aaa81507e82eaf0efaf41c0ca0c30f0de6fec16c89e54322145bf93b`. No recognition-accurate or usable finished score is declared.

## 8. TRACK_A_FEASIBILITY

Track A seeks to retain original pixels and eventually reconstruct only explicitly owned changing notation. COMPLETE means all required group ink is accounted for under the existing ownership contract; it is necessary, not sufficient, for edit authorization. This run uses unchanged Phase 1.9c processed support/source ownership and COMPLETE-only Phase 1.8 gate, with a witnessed exact raster→Audiveris run and page-coordinate checks. No fabricated retrospective forensic certificate, threshold change, handoff tuning or Phase 1.10.

| Candidate class | Total | COMPLETE | PARTIAL | REJECTED |
| --- | ---: | ---: | ---: | ---: |
| Heads | 133 | 0 | 128 | 5 |
| Stems | 126 | 0 | 121 | 5 |
| Beams | 45 | 0 | 41 | 4 |
| Hooks | 12 | 0 | 12 | 0 |
| Flags | 8 | 0 | 8 | 0 |
| Dots | 3 | 0 | 3 | 0 |
| Atomic ink groups | 73 | 0 | 71 | 2 |

No accidental candidates were detected; this does not certify all printed accidentals. COMPLETE reconstruction evidence: **0/327 candidate symbols**, **0/73 groups**. Ownership evidence has 126,439 unique processed-support pixels, 93,256 source-core pixels, 12,022 fringe pixels, 5,872 intra-group shared pixels and **0 unrelated-group collision references**. Unknown staff crossings: 25,535 pixels.

Overlapping group blockers: uncertain antialias boundary 73, local continuation 72, unknown crossing 70, unowned moving attachment 41, other-symbol contact 20, unsupported support overlap 20, text collision 2. Partial cores are not editable.

For **each shift**: approved notes **0/133**, approved beams **0/32**; 618 staff crossing segments require restoration analysis, never performed. Four unresolved cross-system curve segments affect 14 notes in the mask gate. Source/protected envelope intersections 40; target/protected envelope intersections **82 A / 172 G**. Unsupported attachments block 94 note plans; structural envelopes block 59. These are conservative geometric alarms, not verified ink conflicts or permissive masks. No source pixels were removed.

## 9. TRACK_B_FEASIBILITY

Track B seeks to rebuild notation at original layout coordinates while retaining protected source text. B1 is coordinate-only analysis; B2 would be an isolated replacement-notation demonstration, which did not run. B1 coordinate analysis reuses original staff polylines, interline, systems, measure widths and head x. The existing delta planner was not changed. Each of 133 notes separately records:

1. detected physical head coordinate (detector evidence, not truth);
2. corrected source semantic staff position;
3. absolute target staff coordinate `middle_line_y(x) + target_staff_pitch × interline/2`;
4. existing delta-planner coordinate and discrepancy;
5. **replacement engraving anchor = UNDEFINED_NOT_RENDERED**.

Coordinates remain in original Audiveris raster units, origin at the page top-left, x right and y down; no registration/rescaling is applied. Staff pitch 0 is the middle line; positive staff pitch is below it. Expected displacement is target semantic staff y minus source semantic staff y (equivalently `-diatonic_steps × interline/2`). It is not inferred from the detected head center. All 133 absolute positions computed. Expected downward displacement ranges **8.975–9.0125 px A**, **17.95–18.025 px G**, using each original staff's spacing. Maximum delta-planner vs absolute-staff discrepancy **0.923279 px**, with **no ledger repairs**. This is not evidence resolving the earlier 7.40 px repaired-ledger case.

Staff/head-x/measure-width deviations from the source graph are **0 by construction**, not independent accuracy measurements. Head-only target-envelope/protected pairs: **11 A / 17 G**; page-boundary blocks 0, system-envelope blocks 70 each. Unrelated head-envelope pairs 0 at this limited head-only level; complete stem/beam/flag/accidental/curve/attachment occupancy remains unknown. All 32 beam groups have uniform deltas; 27 curves linked, 4 unlinked. Chord text width is **not measured** without a font/placement model, especially with missing chords. No target glyph, beam or slur was rendered. Geometry validation is incomplete, so B2 was not attempted.

## 10. REFERENCE_AGREEMENT and cross-reference consistency

After freeze, separate bounded reference runs produced:

| OMR result, not ground truth | Bb source | A reference | G reference |
| --- | ---: | ---: | ---: |
| Measures | 37 | 34 | 36 |
| Pitched notes / rests | 133 / 36 | 134 / 36 | 134 / 36 |
| Harmony symbols / exported lyrics | 7 / 59 | 2 / 70 | 3 / 41 |
| Systems / staves | 9 / 9 | 9 / 9 | 9 / 9 |

Single-coordinator full-page visual tally sees the same printed system-start labels **1,5,9,13,17,20,25,30,34**, with bar counts **4,4,4,4,3,5,5,4,4 = 37** in each version. This exploratory structural observation is not independent adjudication. OMR regions per system: Bb `[4,4,4,4,3,5,5,4,4]`; A `[4,3,4,4,3,5,4,4,3]`; G `[4,4,4,4,3,5,4,4,4]`. Missing/merged recognized boundaries prevent treating exported bar indices as physical correspondence. A supplied-reference musical defect is **not established** by these recognition differences.

Frozen, limited opening visual check (automated coordinator reading, **not fabricated human annotation**):

| Opening observation | Bb | A | G |
| --- | --- | --- | --- |
| First three written notes | Bb3, C4, F4 | A3, B3, E4 | G3, A3, D4 |
| Durations | Three quarters after quarter rest | Same | Same |
| First two printed chords | Bb, F | A, E | G, D |

These three note and two chord correspondences agree with −1, −3 and A→G −2, including opening spelling and major quality. **Both opening chords (printed bars 1/3) are absent in the frozen source/target XML**, an observed recognition omission despite all baseline guards passing. No accuracy percentage is extrapolated from these probes. Source/reference pixel positions were never used to construct predictions.

Raw strict-identity candidate bookkeeping, deliberately **not scored as accuracy**:

| Comparison | Exact exported identity candidates | Requested interval agreements | Unpaired left / right identities |
| --- | ---: | ---: | ---: |
| Bb recognized → A recognized | 31 | 29 | 102 / 103 |
| Bb recognized → G recognized | 101 | 101 | 32 / 33 |
| A recognized → G recognized | 20 | 20 | 114 / 114 |

Identical exported indices can accidentally refer to different printed bars after segmentation drift. Thus even the two A candidate pitch disagreements are **UNKNOWN correspondence**, not proven wrong transpositions. Cross-reference full-guard diagnostics fail on measure/event/chord mismatches (37→34, 37→36, 34→36); they are not baseline transposition failures and are never waived. The guard retains its 20-issue report cap. Only one frozen G-prediction/reference harmony candidate (`G/B`) shares exact identity; its root/quality/extensions/slash/bass agree mechanically. Other chord qualities, alterations and slash-bass coverage remain unverified. Whole-score independently verified musical denominator: **0**; no independent human labels were collected.

## 11. Geometry comparison

All rasters are 2520×3564. Same-order detector graphs give 9 systems and 45 staff lines in each, with **0 px mean-y and system-top residual**. This is detector evidence; it does not prove exact physical polyline/pixel equality. Exported measure-count mismatch leaves measure-width correspondence **UNKNOWN**, not zero error.

Raw unadjudicated note candidates yield A median x residual −16 px and median y residual +0.211964 px, with extreme 1053/350 px outliers that expose correspondence drift; G median x +10.5 px and y +0.307232 px, max |x| 18 and |y| 0.948279 px. The y residual is **absolute predicted target staff y minus reference detected head y**, so expected transposition displacement is already included, not subtracted again. The x residual is source-locked target x minus reference detected head x. These are **forensic detector residuals, not accepted geometry metrics**. Legitimate engraving changes from differing key signatures and spacing are not musical errors. No reference coordinate corrected a source prediction or planner offset.

## 12. Protected text and visual outcome

Original title/composer/footer/lyrics remain original pixels because no composite or transposed score was generated. Frozen source raster and supplied PDF hashes were rechecked after evaluation. Detected lyric line/item protection counts differ (80/92/67), showing OCR segmentation uncertainty; no lyric baseline pairing was forced. Final-output lyric pixel equality is **N/A**: there is no final output. Comparing source/reference pixels would confound legitimate re-engraving and is not a preservation test.

Clipped/doubled/missing notation, full beam/stem/curve completeness, accidental placement and complete protected collisions cannot be scored from diagnostic head crosses. Original raster evidence is retained; source recognition omissions are not source pixel loss.

## 13–14. Error classification and unknowns

- **RECOGNITION FAILURE / omission:** source opening harmonies missing; reference segmentation 34/36 versus visual tally 37; 133/134 note discrepancy not yet attributed to a specific printed event. No recognition repairs were made using references.
- **Infrastructure startup failure:** native library could not map from noexec tmpfs; preserved and environment-only corrected before reference access.
- **TRANSPOSITION / SERIALIZATION / INTEGRITY FAILURE:** none observed for the two transformations of recognized source semantics. This does not establish correct recognition.
- **UNSUPPORTED CASE:** complete source ownership, moving attachments, unresolved curves, replacement glyph anchors, font metrics and full target occupancy are not established.
- **Correspondence UNKNOWN:** global note/rhythm/measure/chord equivalence until independent transcription; candidate mismatches cannot prove supplied references wrong.
- **Reporting defect preserved:** original worker status has stale top-level `track_b: NOT_RUN` although both target `track-b-geometry.json` files exist. Frozen supplemental diagnostics identify this; no baseline artifact was rewritten to hide it. Per-target artifacts establish what actually ran.

## 15–16. Architecture implications and next experiment

Separate conclusions: **MUSICAL_BASELINE** passes internal integrity but has demonstrated recognition omissions; **TRACK_A_FEASIBILITY** remains blocked COMPLETE-only; **TRACK_B_FEASIBILITY** computes semantic coordinates but cannot validate replacement placement/full notation; **REFERENCE_AGREEMENT** is limited opening evidence plus unresolved whole-score candidate correspondence.

**INSUFFICIENT_EVIDENCE.** A and B share recognition weaknesses. This run compares analysis readiness, not equal-maturity finished renderers. The next experiment should obtain independently frozen measure/note/rest/chord transcripts and physical staff/head annotations from the supplied pages, adjudicate bar segmentation and the extra-note discrepancy, and quantify recognition coverage before evaluating architecture quality. A separate preregistered source-only run may assess the existing PaddleOCR chord path; never retrofit these frozen predictions. The earlier repaired-ledger anchor cases still need independent physical references.

Before that next experiment, freeze a separate collection protocol: two music-literate annotators uninvolved in recognition/planning independently transcribe all printed measures, notes/rests and chords from source/reference pages, without predictions, guard results, coordinator answers, shared OMR exports or each other’s submissions. Freeze both, then use a third reader for adjudication; retain UNKNOWN. Correspondence must use printed measure/ending, staff, voice and onset identities, with merged/missing bars explicitly resolved. Preregister physical-anchor coverage across ledger, beam/curve and ordinary notes; declare coordinate uncertainty/tolerances and verified denominators before any new prediction. This report introduces none of those tolerances or acceptance thresholds. Architecture comparison still needs equivalent output maturity and an independent held-out score set.

Independence audit (Mandela): **Shared hallucination** would occur if common-recognizer agreement were scored as reference truth; independent, separately frozen transcripts are the remedy. **Tautology** applies if zero source-coordinate deviations by construction are called accuracy; external physical coordinate intervals are needed. **Verifier = designer** applies to the coordinator's own visual probes; two independent readers and adjudication are needed. These risks remain explicit limitations, not validation passes. This audit and its cold read do not themselves provide musical ground truth.

## Validation, artifacts and reproduction

Targeted research + V4 + frozen V3 music/gate tests: **298 passed, 1 skipped**; the existing skipped test requires external MuseScore. Tests cover geometry domain rejection, preserved skew, corrected semantic vs detected anchor separation, tamper/addition/missing-file rejection, signature gating, reference/prediction output separation, deterministic rational serialization, and refusing fuzzy cross-score correspondence. `git diff --check` passed. No Full Acceptance.

Source computation 33.261 s (container lifetime 34.250 s); reference A 19.233 s, G 16.894 s. Python source-worker peak RSS **498,012 KiB**; this excludes Java child peak and is not whole-pipeline memory. Each worker had a 4 GiB limit, no OOM; aggregate peak memory was not measured. Raw container states/times are recorded. These single-score times are not service benchmarks.

Local, **untracked** `ground-truth-01-output/` contains source/reference PNGs; source/raw/pre-ledger/recognized/target XML, OMR and inventories; A ink RLE/mask evidence; B geometry maps; signed baseline; mount/provenance/log files; `reference-evaluation/candidate-comparison.json`, initial candidate witness, measure-segmentation audit, coordinator visual observations, opening crops and A/G diagnostic overlays. Overlays show annotation boxes/crosses only, never replacement notation. No copyrighted pages or large artifacts are committed. Private signing key stays local and undistributed.

The exact Docker command/mount records and coordinator extraction argv are saved locally. Off-machine reproduction requires this untracked diagnostic bundle, access to the same supplied PDF, and the bound local container image (or an explicitly distinguished rebuild); the Git commit alone is not a portable reproduction bundle. Public verification uses the public key/signature, never the private signing key. No evidence bundle or score was uploaded. The linked protocol is committed beside this report. Core invocation inside the source-only container:

```sh
PYTHONPATH=/code python /code/scripts/research/paired_ground_truth_01.py predict \
  --source /input/source.png --out /output/baseline-exec
# After signature verification and freeze, in separate read-only-prediction containers:
PYTHONPATH=/code python /code/scripts/research/paired_ground_truth_01.py reference \
  --source /input/A.png --out /evaluation/A \
  --freeze /frozen/manifest.json --predictions /predictions
# G uses /input/G.png and /evaluation/G, sequentially.
python -m scripts.research.evaluate_paired_ground_truth_01 --root ground-truth-01-output
```

Reproduction requires fresh output directories and a new baseline identity; do not regenerate this baseline after viewing references. The signed manifest binds the prediction revision; the final report commit adds post-freeze diagnostic evaluation only.

**No production V1/V3 code/behavior, V4 ownership/acceptance/integrity gate, flag, API/frontend route or runtime renderer changed. No source was overwritten, no finished score rendered, no Phase 1.10/B2, no merge and no deployment.**
