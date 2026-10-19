# GT-13A.6 Phase 2: owner-confirmed cross-system tie rendering

**Actual A/G standalone PNGs now show both tie segments and the incoming whole-note endpoint.** This is completion of the scoped two-segment context, not a complete score. The entire second system, its remaining music/chords/lyrics, source-ink replacement and production composition are outside this result.

Rendering baseline: `20af28ea54d45d980da57ec3084790a2001b4d4e` (GT-13A.5).
Phase 1 worktree/branch reused: `/private/tmp/capomatic-v4-gt13a6`, `experiment/v4-gt13a6-cross-system-tie`.
Actual starting branch revision: `596c8d716301d5c5bfc927f9a9d63652b65fa38c`, the source-only side-by-side packet fix after `37120d6`. No merge, cherry-pick or alternate baseline. Final SHA is returned with delivery.

## Separate results

| Level | Verdict | Scope/limit |
|---|---|---|
| SOURCE_VERIFICATION | OWNER_VERIFIED_SOURCE | Exact m4 Bb3 START→m5 Bb3 whole-note STOP relationship; not independent ground truth |
| TIE_RENDERING_COMPLETENESS | COMPLETE_SCOPED_TWO_SEGMENT_CONTEXT | Actual separate outgoing/incoming curves and incoming target whole note; full second system absent |
| VISUAL_QUALITY | ACCEPTABLE_FOR_EXPERIMENT_SCOPED_TIE_CONTEXT | Actual PNG inspected by assistant after freeze; not independent optical or professional engraving certification |

The overall score remains **INCOMPLETE / NOT FOR PERFORMANCE OR PRINTING**. No whole-score recognition completeness or production readiness is inferred.

## Actual owner confirmation and provenance

Read-only original record:
`/Users/juahnkim/Documents/Codex/2026-10-19/referenced-chatgpt-conversation-this-is-an-2/outputs/tie-owner-confirmation.json`.

SHA-256: `bb47729dd9432b218d6e5495afa1149b6425b3d3ebca27ab6e31ed945aed5e05`.
Actual reply preserved verbatim: **`OWNER_CONFIRMED`**, including its original JSON quoting/backticks. The record states an explicit human reply after delivery of the source-only review packet. Its source curves are 4818/4798 and producer revision is `596c8d7`.

The four bound hashes match the actual packet in sibling `gt13a6-source-review/`: review sheet, owner checklist, source evidence and review freeze. Every file listed in the review freeze also matches. Review-sheet SHA-256 is `46ccebab82647829d4fb4bf8affdc9f9f6a83ca88a900713c5998d7b21aae605`, **not** the earlier superseded vertically arranged packet's hash. Source PNG SHA remains `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`.

Original PDF SHA `1cc64756c0ce47b1db0ea6ac21eefe4685097a04cd4589f954afc712afb605fd`, OMR SHA `857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638`, raw sheet XML and graph hashes are rechecked. The reciprocal extension attributes and raw head relations match the packet. No PDF rasterization, recognition or target-reference-page access occurred.

The original record's `owner_verified_source_promotion_performed:false` describes the earlier confirmation-record-only step. This newly authorized rendering study derives a separate OWNER_VERIFIED_SOURCE record without altering that original file or pending historical checklists. Its original scope did not itself authorize rendering; the current user instruction supplies that authorization. Hash binding is provenance evidence, not a cryptographic human signature or independent annotation.

## Frozen design and tested whole-note placement

[Phase 2 protocol](V4_GT13A6_PHASE2_PROTOCOL.json) was fixed before new target PNG generation. Existing GT-05A fixed-phase raster placement, GT-13A.2 curve sampling and GT-13A.4 header glyphs are reused. FreeSerif remains SHA `c1dd2270ff624d66a7f1cd23075b5ce05a662f560be06a70a9599065ce008355`.

The newly used whole-note glyph is U+1D15D. Its font size follows the existing black-head scale rule, with no resize. Pre-score synthetic controls cover interlines14/18/24, phases0/0.25/0.5/0.75 and both pitches. Independently computed nonzero-alpha bbox centers stay within 0.5px per axis (max synthetic `[0.5,0.200375]px`); the glyph's transparent interior and deterministic cropped alpha remain intact. Confirmation-binding negative controls reject altered source/revision/packet hashes, missing actual reply, wrong question, uncertain status and missing record. Synthetic test fixtures are not human submissions.

Incoming x is the original head1923 bbox center, **320.5px**. Y is computed from the target semantic pitch and actual source staff2 middle polyline/interline18.025, preserving slope. The source physical head center is `[320.5,894]`, whereas its semantic Bb3 staff coordinate is `[320.5,894.558622]`; these are explicitly separate. A3 target y is `903.571122`, G3 is `912.583622`. Actual raster centers are `[321,904]` and `[321,913]`, respectively. No raw-center-plus-semitones approximation or reference-page anchor is used.

The original staff2 geometry is clipped exactly to source m5 boundaries x159–639. Only source-backed clef and target key glyphs are reused there; no new repeat/time or extra musical event is invented. The whole note has no stem. Required ledgers use the existing pitch-position/width2 rule, extending beyond the wider whole-note head. Intentional head/ledger support contacts are counted separately (A44, G15 pixels), rather than falsely classified as unrelated collisions. The head alpha itself retains its open center; ledger crossing is a separate notation component.

## Two visible tie segments and attachment

Source outgoing curve4818 retains its original cubic x coordinates near system1's right boundary. Incoming4798 remains near system2's left boundary. No curve is drawn across the physical inter-system gap.

Each curve's uniform y displacement is the difference between the source Inter head bbox bottom and the target **actual raster bbox** bottom. The source attached-end offset relative to that head reference is retained: outgoing `[+1.4,+3.1]px`, incoming `[-6.6,+2.9]px`. Source Inter edge-center references and target raster pixel-index centers are recorded separately. This accounts for a font head's different bounds while leaving target pitch and all original x coordinates unchanged.

Actual curve-to-declared-attachment residual is `[-0.5,0]px` for each segment and target, within the fixed per-axis criterion. This is a geometric registration test, not an independent optical assertion. Existing GT-13A.5 first-system music/lyrics/header/chords are reused byte-for-byte; only the new outgoing curve is added to that generated canvas. The incoming whole note is independently registered and tested.

| Measurement | A | G |
|---|---:|---:|
| Endpoint pitches | A3→A3 | G3→G3 |
| Roles/durations | START1/4→STOP4 | START1/4→STOP4 |
| New whole-note residual x/y | 0.5 / 0.428878px | 0.5 / 0.416378px |
| Frozen outgoing-head max per-axis residual | 0.5px | 0.5px |
| Outgoing/incoming unrelated-ink contacts | 0 / 0 | 0 / 0 |
| New tie/lyric contacts | 0 | 0 |
| Minimum tie→existing ink center distance, outgoing/incoming | 4 / 3.162278px | 4 / 3.162278px |
| Minimum tie→first-system lyric center distance | 16.031219px | 16.031219px |
| Inter-system bridge ink / clipping | 0 / 0 | 0 / 0 |
| New tie pixels | 192 | 192 |
| Changes outside new tie mask on generated before-tie canvas | 0 | 0 |

Existing GT-13A.5 lyric/music contact count remains0 and its positive clearance rule is preserved. These are contacts with **newly typeset diagnostic notation**, not claims about original Korean text ownership or safe source erasure. The pixel-integrity validator is applied only between generated before/after canvases. It grants no permission to edit the original source image.

## Actual visual inspection

New predictions and hashes were frozen before assistant inspection of `tie-comparison-contact-sheet.png`. Both outgoing/incoming short below-tie curves are visible and aligned near their respective heads, with no obvious new clipping or lyric contact. The incoming open whole note and intentional ledgers are readable. Existing local lyric-baseline steps and experimental beam/header styling remain unchanged. Short uniform-width curves and font aesthetics still need musician review; a numerical 0.5px pass does not prove professional engraving.

The second context is explicitly labeled **MEASURE 5 ENDPOINT CONTEXT ONLY**. Its remaining system music/chords/lyrics are NOT RENDERED; no omitted content is presented as a complete score. No source lyric pixels are composited into predictions.

## Validation and preservation

**359 passed, 1 skipped**: all ground-truth rendering research tests, paired-ground-truth diagnostics, unchanged V3 music/gate and V4 integrity regressions. Existing skip is external MuseScore availability. No Full Acceptance.

Unchanged V3 full guard passes for A/G in-memory transposition and frozen serialized targets. Endpoint roles, ordering, onsets15/4→0 and durations1/4→4 are separately checked. Full lyric signatures remain equal. These semantic checks do not establish independent recognition completeness.

GT-13A.5, GT-13A.4, both original Phase1 packet sets, the actual owner record, original PDF/PNG and OMR remain unchanged. Full directory manifests and frozen prediction hashes match. Recomputed first-system alpha equals the saved historical layer exactly; all actual canvas changes from adding curves are confined to those curves. Source pixels are never used as an editable background. `git diff --check` and formatting checks pass.

## Actual artifacts and next work

Untracked directory `/private/tmp/capomatic-v4-gt13a6/gt13a6-phase2-output/`:

- `predicted-a-tie.png`, `predicted-g-tie.png`
- `tie-comparison-contact-sheet.png`, `original-bb-two-system-context.png`
- Exact outgoing/incoming tie alpha, whole-note/ledger masks, frozen first-system layer and generated before/after canvases
- Byte-preserved `tie-owner-confirmation.json`, derived `source-verification.json`
- `endpoint-rendering-validation.json`, `semantic-integrity.json`, input/prediction freezes
- Post-freeze `visual-inspection-report.json`, `preservation-verification.json`, `final-validation.json`

Pre-score synthetic controls are separately retained in `gt13a6-phase2-controls/`. All copyrighted images/MusicXML/large evidence stay outside commits.

Reproduce in a fresh output directory with the retained original record/packets and frozen local inputs:

```bash
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt13a6_tie_rendering --out gt13a6-phase2-new-run
```

The next task is a source-only second-system content inventory and verification before expanding its remaining events, chord/lyric content and attachments. Independent musician/optical review remains separate. No original ink removal, original lyric-pixel composition, source PDF change, protection-mask/ownership-gate change, V1/V3 modification, production renderer/API/frontend, merge or deployment occurred.
