# GT-14 second-system standalone expansion

**SECOND_SYSTEM_INCOMPLETE.** A/G PNGs display **12 of 13 recognized events**: one existing owner-confirmed m5 endpoint and eleven new **OMR_PROVISIONAL** events. Actual mixed beams/hooks, the two-sixteenth pair, and two new local ties are rendered. Whole rest m8, ending1/final repeat, disputed OMR attachments, all new chord candidates and both lyric rows remain explicit omissions. This is not a usable full score.

Base: `4b3aabda905f2f56f3e2c181f724f80a94db1b7f`.
Branch: `experiment/v4-gt14-second-system`.
Worktree: `/private/tmp/capomatic-v4-gt14`.
Final SHA is supplied with delivery. No merge or production changes.

## Four separate verdicts

| Dimension | Result |
|---|---|
| SOURCE_RECOGNITION_COMPLETENESS | UNVERIFIED_WITH_AGENT_OBSERVED_OMR_OMISSIONS; source-image chord/lyric candidates exceed exported content |
| OWNER_VERIFICATION_COVERAGE | 1/13 recognized events, the previously confirmed m5 whole-note tie stop; no new owner answers |
| RENDERING_COMPLETENESS | INCOMPLETE: 12 events displayed, 1 unsupported/unrendered; unresolved required context and attachments |
| VISUAL_QUALITY | ACCEPTABLE_FOR_EXPERIMENT_PARTIAL_MUSIC_LAYER after assistant PNG inspection; not independent human optical validation |

No recognition-accuracy percentage or independently verified denominator is established. Displayed events are not equivalent to complete atomic notation groups. The first system remains its historical confirmed standalone layer, not newly recognized or relabeled content.

## Source audit and evidence isolation

Original Bb PDF page2, printed second system m5–8. No A/G reference pixels/content, OCR or Audiveris rerun. Source PNG SHA remains `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`. Original PDF SHA remains `1cc64756c0ce47b1db0ea6ac21eefe4685097a04cd4589f954afc712afb605fd`; OMR SHA remains `857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638`.

The source audit joins GT02's Bb-only physical registration, frozen corrected source MusicXML, persisted staff2 polylines and unique head/rest bounding boxes. It checks measure lineage, onset, duration and pitch, without treating agreement as human ground truth. Measures have one persisted OMR voice1; MusicXML/diagnostic default voice may be omitted, and that provenance is explicit. No unstable object IDs are used.

Source-native review window `[130,700,2430,1030)` includes chord band, both lyric baselines and ending/repeat context. A complete review sheet and four original-resolution per-measure crops contain unchanged source pixels. Coordinator candidate answers are stored separately in the checklist, not painted into the source crops. This is owner source review, not an independent blinded packet.

### Recognized source stream

All durations/onsets below are quarterLength. Only the first row is already OWNER_VERIFIED_SOURCE; the remaining rows are OMR_RECOGNIZED/UNVERIFIED and, if displayed, OMR_PROVISIONAL.

| Measure | Recognized events |
|---|---|
| 5 | Bb3 whole note, onset0/duration4, tie STOP from m4 |
| 6 | Quarter rest0/1; eighth rest1/0.5; Bb3 1.5/0.25; C4 1.75/0.25; D4 2/0.5; C4 2.5/0.25; C4 2.75/0.25 START; C4 3/0.25 STOP; Bb3 3.25/0.5; Bb3 3.75/0.25 START |
| 7 | Bb3 whole note0/4 STOP from m6 |
| 8 | Whole-measure rest0/4; recognized but not rendered |

Each measure totals four quarters internally. Source bbox, written pitch/accidental, onset/duration, voice provenance, grade/ctx-grade, beams, tie role, articulations, expressions and raw lyric tokens are in `source-event-inventory.json`. This internal four-beat consistency does not certify source completeness.

Source context is treble/two flats; target clef/key context reuses the frozen GT13A6 target masks. No extra printed accidental is identified in the supported stream; all target pitches are checked against A/G key context before rendering. There are no required flags in this system's recognized stream; earlier flag support is unchanged.

### Chords, lyrics and ambiguous symbols

Agent visual candidates, **not owner confirmation**:

- m5 `Gm`; m6 `Bb/D`; m7 `Eb`; no new m8 chord identified.
- OMR exports only m6 `B-/D` as harmony; the other two candidates are absent from the exported harmony stream. Rendered new chords:0, owner-confirmed new chords:0.
- Upper m6: 내 / 가 / 있 / 길 / 원 / hold / 하 / 네.
- Lower m6: 주 / 의 / 놀 / 라 / 운 / hold / 손 / 길.
- Proposed onsets:1.5,1.75,2,2.5,2.75,3(hold),3.25,3.75. The tied stop at3 is not a new syllable candidate. M5 and m7 visible row dashes/extenders and their exact associations still need review.

MusicXML exports **zero lyric tokens** for this system. No strings, extender assignments or chord answers are borrowed from target pages or inherited merely because a phrase/pitch resembles previously confirmed material. All new chord/lyric pixels are withheld, so collision-aware text positioning is deliberately **not executed**. Future owner-confirmed text can use GT12/GT13A5 contracts; unverified content is not silently filled.

OMR has TENUTO objects5686/5699/5762, a FERMATA_BELOW5747 with an explicit fermata-chord link to4651, ending5201 and repeat dots5765/5767. Source visual inspection suggests some may represent lyric strokes rather than musical attachments; that is only AGENT_VISUAL_CANDIDATE interpretation. Their identities/bboxes/relations remain in the inventory and unsupported list. They are not automatically dismissed, rendered, or used as source ownership.

## Actual rendering expansion

[Protocol](V4_GT14_PROTOCOL.json) fixes the scope before target predictions. Existing components are reused:

- GT05A fixed-phase FreeSerif glyph placement and original 0.5px per-axis criterion.
- GT06 `beam_geometry` for m6's explicit two-sixteenth group; semantic duration, direction and both beam/stem relations are required.
- GT13A2 `mixed_layout` for the two three-stem mixed groups and partial hooks. All group memberships and semantic levels must agree; no nearest-neighbor construction.
- GT13A2 cubic rasterization/translation for local ties4784 (C4→C4 inside m6) and4772 (Bb3 m6→m7). Explicit LEFT/RIGHT heads, matching target pitch, START/STOP and actual bbox-bottom attachment displacement are checked. These ties remain OMR_PROVISIONAL.
- GT13A6 whole-note glyph for provisional m7, with independently checked raster registration and transparent head interior.
- **Exact saved** GT13A6 m5 whole-head/ledger and incoming tie masks; no rerendering of historical predictions. The first-plus-second preview imports the frozen first-system layer and outgoing cross-system segment as well.

The staff2 polylines, slope and measure boundaries639/1598/1961/2397 remain source-derived. The last thin line is diagnostic boundary scaffold, **not** a rendered backward-repeat substitute. No final-repeat dots/heavy bar or ending bracket is claimed. M8's whole rest lacks a validated hanging-line glyph contract in the reused component set, so its event is visibly absent and explicitly listed as unsupported.

Black denotes the confirmed endpoint and source geometry context; amber denotes new provisional music. The separate preview also retains the previous first system's confirmed black music/lyrics. Coloring does not confer ownership or performance readiness.

## Measured results

| Metric | A | G |
|---|---:|---:|
| Recognized events | 13 | 13 |
| Owner-confirmed displayed | 1 | 1 |
| New provisional displayed | 11 | 11 |
| Unsupported/unrendered event | 1 | 1 |
| Rendered beams/hooks | 7 | 7 |
| New local ties / reused confirmed incoming tie | 2 / 1 | 2 / 1 |
| Max notehead anchor residual | 0.5px | 0.5px |
| Unexpected musical component intersections | 0 | 0 |
| Missing stem/head/beam connections | 0 | 0 |
| Clipped components | 0 | 0 |
| New provisional ink→frozen confirmed context contacts | 0 | 0 |
| Minimum tested nearby distinct-component center distance | 3.162278px | 3.162278px |
| Rendered new chord/lyric components | 0 / 0 | 0 / 0 |

Clearance is measured among nearby distinct components, excluding same-event head/stem/ledger and intentional contact pairs; it can include a tie's own connected head. It is **not** a claim that all unrelated original-source ink is clear. Deliberate staff crossings and explicit head/stem/ledger or beam/stem contacts are distinguished from unexpected collisions.

Four broad original text-protection regions intersect the rendered music union: **A5878/G6026 unique pixels**. These are envelope diagnostics, not verified text ink contacts or permission to shrink protection. Actual source-text ownership/collision remains UNKNOWN. With new lyrics withheld, lyric/music contacts and minimum lyric clearance are NOT_EVALUABLE, not zero. No source composition is authorized.

## Visual review and frozen runs

Actual comparison and G first-plus-second preview were inspected. Provisional noteheads/stems and double/mixed beams/hooks are visible, and both new ties connect the intended geometric neighborhoods without obvious clipping or missing stem joins. The preserved m5 endpoint remains black. The large empty m8 and absent chord/lyric/ending/repeat layers are explicit limitations. Thin ties and stepped beam raster edges remain experimental. This is assistant visual review, not independent optical or musician validation.

Initial development outputs remain under `gt14-output/`, including their producer snapshot/hash binding. Final outputs are separately frozen under **`gt14-final-output/`**. The follow-up clarifies the black geometry legend and renames the clearance metric to avoid calling connected tie/head pairs unrelated. Font/owner-record checks were also made explicit. All **84 component/union alpha PNGs are byte-identical** across these runs: no musical geometry, threshold or collision rule was tuned to improve results. Final hashes were verified and visual inspection repeated after generation/freeze completion. No target reference page was accessed.

## Validation and preservation

**371 passed, 1 skipped**: all ground-truth/rendering research tests, paired-ground-truth tests, V3 music/gate and V4 integrity regressions. Existing skip is external MuseScore availability. No Full Acceptance. New synthetic tests cover source/mapping identity, noninheritance of m5 confirmation to same-pitch m7, voice provenance, source tie/duration changes, local tie lineage/pitch/anchor failure and avoiding accidental exclusion of distinct beam contacts.

Unchanged V3 full guards pass for A/G fresh in-memory transposition and frozen serialized targets; complete lyric signatures remain equal. These are semantic-preservation checks, not independent source accuracy. Source and target raw counts do not replace the missing human denominator.

Original PDF/PNG/OMR, actual confirmation record, GT13A6 target freezes, linked Phase1/GT13A4 evidence and source review packet remain hash-identical. GT14 audit and prediction freezes also match. Historical directories are read-only inputs; tests and outputs are isolated in this worktree. Formatting and `git diff --check` pass. Only research code/tests/protocol/report are committed; copyrighted images and large artifacts remain untracked.

## Actual outputs and next owner review

Directory: `/private/tmp/capomatic-v4-gt14/gt14-final-output/`.

- `original-second-system.png`, `predicted-a-second-system.png`, `predicted-g-second-system.png`, `second-system-comparison.png`
- `source-second-system-review-sheet.png`, native `source-measure-5.png` through `source-measure-8.png`
- `source-event-inventory.json`, `source-review-checklist.json`, `unsupported-elements.json`, `rendering-validation.json`
- `A-first-plus-second-provisional-preview.png`, `G-first-plus-second-provisional-preview.png`
- Exact component masks, guards, freezes, visual/preservation/final validation reports.

**Next owner review:** inspect the raw review sheet and confirm/correct (1) m6 sequence and ties, m7 whole note, m8 whole rest; (2) Gm/Bb/D/Eb chord candidates; (3) both lyric strings, tied holds and note associations; (4) ending1/final repeat and whether the disputed TENUTO/FERMATA objects are musical symbols or lyric content. No repeat confirmation of the m4→m5 tie/whole note is requested. All new answers remain pending; none were fabricated.

Next engineering capability is validated whole-rest hanging-line placement and ending/backward-repeat engraving, independently of source-content confirmation. Text rendering awaits verified source content. No original ink removal, source PDF/raster change, original lyric-pixel compositing, protection/ownership relaxation, V1/V3 changes, production API/frontend, merge or deployment occurred.
