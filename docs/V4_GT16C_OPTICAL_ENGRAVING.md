# GT-16C — adaptive optical engraving 1.0

**DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE — INCOMPLETE — NOT FOR PERFORMANCE OR PRINTING**

Base `6cc1dd558d13b7c56799c0cfda49fafbaca8ccd4`; branch `experiment/v4-gt16c-adaptive-optical-engraving`; worktree `/private/tmp/capomatic-v4-gt16c`.

Understood as: preserve the confirmed musical and textual content of printed measures 1–16, improve only generated lyric spacing and selected beam raster quality, and retain every GT-16B artifact unchanged. This study is development research, not independent blind validation.

## Separate results

| Dimension | Result |
|---|---|
| Source verification | Unchanged owner-confirmed notes/text/associations; no independent attestation that every printed symbol is accounted for |
| Semantic consistency | Full unchanged V3 source/target guards and exact event/chord/lyric/repeat signatures PASS |
| Rendering coverage | 77 events, 10 chords, 84 syllables, 28 continuation marks retained; no extra/missing components |
| Numerical layout safety | Selected 6px candidate passes actual alpha contact, glyph preservation, clipping and anchor checks |
| Agent visual review | Modest readable separation and smoother selected beams; limitations remain |
| Independent musician/optical review | 0 actual reviews; not established |
| Freeze recommendation | **Ready to freeze as an INCOMPLETE experimental baseline**, not production or performance-ready |

The full semantic files still contain 37 measures / 169 events / 15 harmonies. These differ from the displayed, owner-confirmed 16-measure scope. Neither count is an independent accuracy denominator.

## Frozen baseline and provenance

Inputs are the actual GT-16B PNGs, generated masks, `rendering-validation.json`, source/owner bindings and previous rendering layers. [V4_GT16C_VALIDATION.json](V4_GT16C_VALIDATION.json) binds final artifact hashes; `input-freeze.json` records every file in 15 historical input directories. Each historical prediction manifest is checked before use and every directory rehashed afterward. GT-12's earlier `output_files_sha256` manifest uses its parent output root, as documented by its producer; other manifests use their `files` root. No missing file or mismatch is ignored.

| Frozen GT-16B artifact | SHA-256 |
|---|---|
| A four-system PNG | `6296c7c27f1ffebdb9272963b2b598d3e31e1c5b8f9cf8f06d81fe8f64f0c273` |
| G four-system PNG | `17b24a6cd03bf0679f2003ba8ef7f95b12f380283691b9afdb8d8026c3da0c01` |
| Prediction freeze | `7b83582528dcdcd958ea175e301fa0df8e9e7dbb05399fb4674981f99abfd0a2` |
| Rendering validation | `fe15185fbfb79662ccf0c29f9c0228fd6ff9ec0f3ce336c18b090baf7ef04259` |

Original Bb source remains SHA-256 `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`, 2520×3564 RGB. OMR `857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638`; graph `f8725c39beaaecc877ccf48b803b79a419c2d6e60aa73bc9428a39de11596508`. Only the Bb graph and previously frozen source/target semantics were used. No target-reference pages, new OCR, recognition repair, font download or owner reclassification was used.

## Baseline audit and protocol revision

The priority audit covers m2, m4, m6, m9, m10, m11, m13, m14 and m15 in each key: **18 target/measure regions**, of which **12 initially had center distance below 6px**. Native baseline crops are saved as `*-m*-baseline-native.png`. `optical-baseline-audit.json` records lyric/component IDs, actual page-coordinate bboxes, nearest center/edge pixel pairs, nearest notation files and event/symbol lineage, original source records, actual head bboxes and available vertical space. Those generated masks are not original source-ink ownership.

The initial [protocol](V4_GT16C_PROTOCOL.json) fixed 6/10/14px alternatives and 2×/3×/4× beam candidates before generation. A baseline control exposed an incorrect domain: the fixed-notation strip split y1015 was also used as the second-system lyric bottom, although frozen G lyrics already extend to y1020 and A to y1012. The resulting revision-1 failures are artificial domain failures, **not evidence that the page lacks space**. No revision-1 preview was visually used for selection.

[Revision 2](V4_GT16C_PROTOCOL_REVISION_2.json), retained separately and hash-linked to revision 1, uses the existing GT-14E lyric display bottom **y1030**. Fixed-notation strip splits remain 720/1015/1408/1800; lyric bottoms are 720/1030/1408/1800. A synthetic known-valid-baseline test covers this distinction. This correction changes no collision criterion, source data or musical geometry. Development artifacts and the original protocol remain preserved.

## Deterministic layout alternatives and exact changes

All 112 existing glyph/mark bitmaps are reused. The first two systems use GT-14E `load_components`, the later two use frozen GT-15B/16B placements. Four first-system continuation masks are identified through their existing approved tied-note associations, not pixel shape or a new classification. All 84 syllables and 28 mark IDs remain unique.

For each system, move both rows and all associated marks together by the minimum nonnegative integer dy that satisfies the chosen native ink-center goal against the complete fixed notation/context. Pixel alpha, font, x positions, row ordering, row spacing, lyric text and associations remain unchanged. Exhaust the finite declared domain and verify final text/text and text/notation alpha contacts. GT-16C does not horizontally move lyrics.

The preregistered selection is **6px**, not whichever alternative looks best:

| Target | Additional lyric dy, systems 1–4 | 6px native | 10px native | 14px native |
|---|---|---|---|---|
| A | 5 / 4 / 4 / 4px | Feasible, selected | Feasible | Feasible |
| G | 6 / 5 / 4 / 4px | Feasible, selected | Infeasible in system-2 lyric allocation | Infeasible in system-2 lyric allocation |

The G 10/14px alternatives also succeed in a separately labeled **120px extra allocation per system** experiment. Its system translations are 0/120/240/360px and canvas height 2280px. This is a coarse feasibility alternative, not the minimum extra system spacing or proof that no other native layout could work. The selected 6px result needs **no system movement and no larger canvas**.

Selected working alpha canvas remains **2520×1800** in page coordinates. Applying the right/bottom-exclusive crop `[130,310,2430,1800]` produces a **2300×1490** musical body; the wrapped 90px warning header makes each final four-system display PNG **2300×1580**. This presentation crop/header does not move page-coordinate notation. Original physical source page is 2520×3564; this four-system crop is not full-page pagination. Middle staff coordinates at source x159 stay y481.4/831.5/1181.5/1531.5; all polylines, measure widths, note x/y, stems, rests, flags, ties, chord locations and ending geometries remain fixed. Only lyrics move and two simple diagonal beam groups per target change rasterization. Measure 3 lyrics also move in this new experiment; historical GT-12 and all other older outputs remain byte-identical.

## Measured before/after optical distances

Each cell is **center distance / exact pixel-square edge distance**, native pixels. Every nonzero-alpha pixel counts; no intensity cutoff or erosion is used. Pixel edges are the closed, axis-aligned unit squares centered on integer pixel coordinates. The edge minimum is computed independently over local point pairs within a proven distance bound; it is not simply `center−sqrt(2)`.

| Measure | A before | A after | G before | G after |
|---|---:|---:|---:|---:|
| 2 | 2.828 / 1.414 | 6.708 / 5.385 | 2.236 / 1.000 | 6.708 / 5.385 |
| 4 | 2.000 / 1.000 | 7.000 / 6.000 | 2.000 / 1.000 | 8.000 / 7.000 |
| 6 | 3.000 / 2.000 | 6.708 / 5.385 | 2.000 / 1.000 | 6.708 / 5.385 |
| 9 | 2.000 / 1.000 | 6.000 / 5.000 | 2.000 / 1.000 | 6.000 / 5.000 |
| 10 | 47.000 / 46.000 | 43.000 / 42.000 | 38.000 / 37.000 | 34.000 / 33.000 |
| 11 | 2.000 / 1.000 | 6.000 / 5.000 | 2.000 / 1.000 | 6.000 / 5.000 |
| 13 | 2.000 / 1.000 | 6.000 / 5.000 | 2.000 / 1.000 | 6.000 / 5.000 |
| 14 | 51.420 / 50.220 | 55.317 / 54.129 | 51.420 / 50.220 | 55.317 / 54.129 |
| 15 | 15.232 / 13.928 | 18.974 / 17.720 | 15.232 / 13.928 | 18.974 / 17.720 |

All **12/12 initially crowded target/measure regions** improve to at least 6px; none remains below the target. Across all 18 audited regions, 16 center-distance minima increase. The two m10 minima decrease 4px because the coupled rows approach lower context; they remain 43px/34px, not an unqualified improvement everywhere. Unmeasured regions are not included in this denominator. Whole-system feasibility checks include every lyric/mark component, not only these nine selected measures.

Selected layout has **0 actual text/notation contact pixels**, **0 text/text contact pairs**, **0 lost glyph alpha pixels** and **0 clipping**. The 6px goal is an experimental heuristic, not a professional standard. At 50% display it becomes only 3px nominal center distance; native safety does not prove readability at every scale.

## Beam raster comparison

Only individually recoverable, single-level diagonal groups are replaced: source IDs **sheet#1:1248** (m12) and **sheet#1:1275** (m15), each in A/G. All first/second-system mixed beams/hooks and all horizontal beams remain unchanged. Their remaining staircase appearance is explicitly not solved here.

Each 2×/3×/4× candidate samples a finite subpixel grid in the original pixel-center coordinate system and BOX-averages coverage. The source centerline endpoints, declared 10px width, beam memberships and stem locations are unchanged. Cap edges remain half a pixel beyond the endpoint centers, retaining endpoint columns. No ringing filter, post-hoc translation or alpha threshold is used. This is a new raster alternative, so bitmap byte equality is neither required nor claimed.

Before substitution, the third-system music/context is exactly reconstructed with frozen component masks and the existing scaffold/header/ending functions. The fourth-system context is already individually frozen. Nonbeam components are restored explicitly, and baseline recomposition must match byte-for-byte. Changed fixed-ink pixels must fall inside the union of old/new selected beam support. All nonmember music contacts and newly appearing context-contact pairs are rejected; existing same-staff contacts retain their intentional status.

All 2×/3×/4× candidates pass stem connectivity and unrelated-contact checks. The frozen rule chooses the highest safe scale with lower detrended coverage-centroid RMS, hence **4×** for all four target/group instances:

| Beam | Old detrended RMS | 2× | 3× | 4× |
|---|---:|---:|---:|---:|
| 1248 | 0.315934px | 0.141671 | 0.092200 | 0.067548 |
| 1275 | 0.273821px | 0.136864 | 0.088353 | 0.063334 |

A/G phase differs by integer staff steps and gives the same rounded results. Each selected beam remains one connected component, all four attached stems contact it, and there are zero unrelated component contacts or new context-contact pairs. No endpoint, stem or note position is optimized.

**Optical weight caveat:** coverage area changes from 2154→2390.204px² for beam1248 and 2350→2600.235px² for beam1275, about +11%. The old binary raster realizes less coverage than the declared strip width. New nonzero support is 2570/2804 pixels, with 360/408 intermediate-alpha pixels. Beam1248's bbox extends one pixel farther down; beam1275's bbox stays the same. These are intentional raster support changes, not preserved optical thickness. Broader stroke-weight validation is still needed; a smoother numerical profile alone does not establish a superior engraving.

## Semantic, anchor and preservation validation

Full unchanged V3 guards pass for source roundtrip, A/G in-memory and serialized targets. Full event/pitch/duration/voice/tie signatures, chord figures, lyric associations and explicit repeat/ending signatures match GT-16B. No sounding octave, 8va/8vb mark, note, chord, syllable, continuation, tie destination or repeat jump is added.

A separate post-freeze validator recomputes all **60 actual head-bbox anchors per target** using frozen head components and exact measure/onset correspondence. Maximum residual remains **0.5px per axis**, and all head-support alpha in the refined composite equals baseline. All ten chord masks per target also retain exact composite alpha. It verifies the known GT-11 cached m3 heads against their original hashes rather than silently treating them as a different source. All other fixed-ink changes are restricted to the two beam support regions; rests, headers and existing ties stay fixed.

Targeted regression command:

```sh
/private/tmp/capomatic-v4-venv/bin/python -m pytest tests/test_v4_ground_truth_*.py tests/test_v4_paired_ground_truth_01.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py tests/test_omr_v4_integrity.py -q
```

**523 passed, 1 skipped**, including 22 synthetic optical/beam controls. The skip is the existing external MuseScore integration dependency. Full Acceptance was not authorized and was not run. The separate manual-only [V3 Full Acceptance Evaluation](V3_ACCEPTANCE.md#ci-operation-after-closure) evaluates the larger real/synthetic/fresh-holdout corpus, full-score gates and fallback outcomes; this local run establishes none of those corpus-level acceptance or blind-accuracy results. Synthetic controls include integer/fractional phases, positive/negative slopes, horizontal controls, exact edge-vs-center distance, disconnected/remote attachments, unrelated contact, clipping, lossless coupled rows, deterministic masks, native infeasibility/taller fallback and the corrected allocation-boundary control. `git diff --check` passes.

All historical directories and source hashes remain unchanged. A separate producer execution returns **exit0**, takes **44.22s** and peaks at **596,246,528 bytes RSS** on this host. All **90 PNGs** and **95/97 frozen files** reproduce byte-for-byte. The two MusicXML files differ only in linked `score-instrument`/`midi-instrument` IDs; their musical signatures match. No production serializer normalization was added. An earlier `/usr/bin/time -l` measurement reported 36.54s but its own `kern.clockrate` query was denied after rendering completed; it was replaced by explicit subprocess status and Python timing/resource measurement, without bypassing permissions.

## Actual image inspection and remaining limits

Final candidate hashes were frozen before agent inspection. The agent inspected both A/G native four-system previews, both 50% displays, both original/refined comparisons, G m13 and m9 native details, the m15 beam before/after and the 2×/3×/4× mask alternatives. The G m13 주 and m9 풀 now have visibly more breathing room from the low note; A shows a similar modest separation. The selected diagonal edges look smoother at native size. At 50%, the spacing and beam differences are subtler; this is not a musician reading-speed or professional engraving result.

Remaining optical limitations include unchanged mixed beams/hooks, some horizontally crowded adjacent Korean syllables, thin ties at reduced scale and the new beam optical-weight difference. No horizontal syllable redistribution, font substitution, tie redesign or post-inspection retuning occurred. The baseline comparisons rewrap warning headers for alignment while verifying that their musical body is identical to the actual frozen GT-16B PNG body. Detail crops intentionally show partial neighboring context, not clipped full-score exports.

Practically, owner approval establishes the listed notes/text/associations, but the renderer may still omit genuine musical marks among the unclassified objects. The ten unresolved SIG objects stay withheld: 5833/5841/5896/5902/5903 and 5927/5948/5949/5975/5984. Repeat playback remains unresolved, and MusicXML lyric-extender serialization remains incomplete. The agent is also the experiment designer; shared geometry/semantic checks establish implementation consistency, not independent musical or optical truth. **Independent musician review count is 0.** The unresolved playback route means these PNGs cannot specify a verified complete performance sequence; the missing MusicXML extend instructions mean visual continuations cannot be assumed to survive another exporter/player. Owner source approval and numerical/agent visual findings remain separate.

Recommendation: freeze this labeled research baseline and request a separately scoped musician optical review before extending beam rasterization to mixed groups or treating 6px as a reusable default. A concrete next review should show the frozen A/G original/refined previews at native and 50% size plus G m13, G m9 and both selected beam details. Ask a qualified musician whether low notes/lyrics are distinguishable, beam group durations and tie directions are readable, spacing is preferable, and any new ambiguity appears. Record the reviewer’s actual answers and uncertainty. Any new ambiguity or apparent symbol loss blocks default adoption and requires a new experiment. This would be an unblinded optical comparison, not a replacement for the untouched independent source-transcription packets; no reviewer is assigned or answer fabricated here. Future extreme-register layout and explicit optional octave notation are discussed in [adaptive-engraving-design.md](adaptive-engraving-design.md); none of the octave semantics is implemented here.

## Actual artifacts and reproduction

Untracked final output directory: `/private/tmp/capomatic-v4-gt16c/gt16c-final-output/`.

- `A-original-vs-refined.png`, `G-original-vs-refined.png`
- `A-refined-four-systems.png`, `G-refined-four-systems.png`
- `G-m13-lyric-clearance-detail.png`, `diagonal-beam-before-after.png`
- `A-refined-half-display.png`, `G-refined-half-display.png`
- `optical-spacing-metrics.json`, `optical-baseline-audit.json`, `beam-quality-metrics.json`
- `adaptive-engraving-design.md`, `visual-validation.json`, `validation-summary.json`
- `all-head-anchor-preservation.json`, `semantic-integrity.json`, `determinism-and-runtime.json`
- `input-freeze.json`, `prediction-freeze.json`, `preservation-verification.json`

The research freeze gate is: passing safety/semantic checks, explicit agent visual verdict, immutable output hashes, committed/pushed code and a checked local output snapshot. A local archive and SHA-256 sidecar are retained at `/Users/juahnkim/transchord/tmp/gt16c-optical-freeze.zip` and `.sha256`, outside Git. It contains final outputs, this experiment’s code/tests/docs and a commit/environment/external-input manifest. The project owner controls local retention and backup; a local archive is not an off-site backup guarantee. Original source evidence, other historical inputs and system fonts are **external dependencies**, not bundled or claimed durably archived. Their required paths/hashes are listed, and preserving them is still required for end-to-end reproduction. No original source PDF or font binaries are added to the archive.

The canonical committed design is linked above; the output copy is a hash-bound experiment snapshot. [V4_GT16C_VALIDATION.json](V4_GT16C_VALIDATION.json) binds final outputs and metrics. Raw alpha data PNGs carry warning metadata instead of contaminating alpha support with text. Display images carry developer-only incomplete warnings.

```sh
cd /private/tmp/capomatic-v4-gt16c
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt16c_optical_engraving --out /private/tmp/capomatic-v4-gt16c/NEW-UNUSED-OUTPUT
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt16c_validate_heads --out /private/tmp/capomatic-v4-gt16c/NEW-UNUSED-OUTPUT
```

Reproduction requires preserved absolute-path historical evidence and the existing pinned font environment; it is not a portable package. Failed pre-render imports/old manifest-schema assumptions and the revision-1 domain experiment are retained as development artifacts, not used as final evidence or silently substituted. No dependencies were installed.

No original Bb PDF/raster edit, original ink removal, source-pixel composition, protection-mask change, owner-record change, SIG reclassification, V1/V3/API/frontend production modification, merge or deployment occurred. Images, alpha masks, MusicXML and large diagnostic evidence remain untracked.
