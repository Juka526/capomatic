# GT-13A.2 provisional full-system rendering expansion

## Final visual refinement and freeze

**FULL_SYSTEM_INCOMPLETE.** Final research outputs are in `/private/tmp/capomatic-v4-gt13a2/gt13a2-final-output/`; earlier runs below are preserved unchanged. There are **26 recognized / 26 displayed events: 4 OWNER_VERIFIED and 22 OMR_PROVISIONAL**. This does not certify source completeness. m1/2/4 lyric strings are `OWNER_CONFIRMED_LYRIC_TRANSCRIPTION`; note/rhythm/chord/tie and exact lyric association evidence is not promoted. m3 retains the exact GT-12 rendering.

Final A/G music and lyric component PNGs, including the provisional union masks, are **byte-identical to the prior frozen GT-13A.2 run**. The only visual change is placement of diagnostic text. Every diagnostic annotation now lies outside the unchanged native 2300×410 source-coordinate viewport, in a separate 250px header or 160px footer. The final target panels are 2300×820 and the source/A/G contact sheet is 2300×2460. This panel framing does not rescale the musical content or move notes relative to source geometry.

| Final annotation measurement | A | G |
|---|---:|---:|
| Diagnostic text elements checked | 15 | 15 |
| Nonzero annotation pixels inside notation viewport | 0 | 0 |
| Actual annotation/music alpha contact pixels | 0 | 0 |
| Actual annotation/all-score alpha contact pixels | 0 | 0 |
| Minimum annotation → musical glyph pixel-center distance | 180px | 171px |
| Conservative unit-square edge-clearance lower bound | 178.586px | 169.586px |
| Minimum annotation → all-score ink pixel-center distance | 69px | 69px |

Musical ink includes actual nonzero head/rest/stem/beam/flag/ledger/local-tie alpha, using the frozen GT-11 music-only union for verified m3. It excludes diagnostic text, chords, lyrics, staff and bars. A separate stricter comparison includes all staff/chord/lyric ink. Distances use existing OpenCV `DIST_L2` / `DIST_MASK_PRECISE`, with float32 results, in pixel-index-center coordinates. The edge-gap lower bound is `max(0, d - sqrt(2))` for unit pixel squares; it is distinct from an optical spacing verdict. Tests include non-overlapping pixels only 5px apart to demonstrate that overlap-zero is not substituted for clearance. No new acceptance tolerance or alpha threshold was introduced. All diagnostics must stay outside the notation viewport and have zero actual contacts.

Outgoing tie evidence: frozen `sheet#1:4818` has one local LEFT head (`sheet#1:1852`), a serialized source cubic and `right-extension=4798`. The endpoint in the next system is outside this rendering scope. The existing local-tie renderer requires two explicit head endpoints and semantic start/stop agreement; that contract does not establish a validated one-ended stub placement. **UNSUPPORTED_OR_UNRESOLVED** is retained; no stub or invented destination is drawn. Its exact source curve/attributes are retained in the final report. The final event body is displayed, but its required outgoing tie remains incomplete.

Source verification is still UNVERIFIED for the system, rendering completeness remains INCOMPLETE, and the visual verdict is **ACCEPTABLE_FOR_PROVISIONAL_DIAGNOSTIC / NEEDS_REFINEMENT_FOR_USABLE_SCORE**. The agent inspected the actual G PNG and source/A/G comparison after prediction freeze. Diagnostic text no longer enters the music/lyric viewport; existing blue provisional and black verified notation is unchanged. Thin sampled curves and mixed-beam raster edges remain prototype quality. This is not independent optical validation and the canvas is not performance-ready or printable.

Final targeted regressions: **215 passed, 1 skipped** (existing external MuseScore dependency). Three additional tests cover distance/overlap separation, native viewport preservation and deterministic margin placement, and coordinate mismatch rejection. An initial development test import failed because SciPy was unavailable; no dependency was installed, and the implementation uses existing OpenCV instead. That failed invocation did not create a prediction directory. The final producer ran unchanged full V3 guards on both frozen GT-01 and owner-augmented GT-12 A/G streams, all passing. Historical GT-12, GT-13A, prior GT-13A.2 and GT-11 component trees were hash-checked before/after and unchanged. The original source crop PNG is identical to the previous run. Musical event counts/positions/rhythm/anchor metrics are unchanged; notehead max residual remains 0.5px.

Final artifacts: `original-bb.png`, `predicted-a.png`, `predicted-g.png`, `comparison-contact-sheet.png`, `source-event-inventory.json`, `provisional-rendering-report.json`, `unsupported-symbols.json`, `semantic-integrity.json`, `input-freeze.json`, `prediction-freeze.json`, `visual-inspection-report.json`, `validation-summary.json`, per-component PNGs, per-target annotation masks and native notation viewports. Previous outputs were not overwritten. The final prediction manifest was frozen before agent visual inspection; post-inspection reports are separate.

Remaining blockers: owner confirmation of provisional notes/rhythms/local ties and m1 chord, exact m1/2/4 lyric associations, header/repeat renderer contracts, and next-system tie evidence plus an independently tested continuation contract. No source removal or original-pixel lyric composition is authorized. Production code, masks, integrity gates and Track A ownership rules are untouched. No merge or deployment.

## Preserved pre-final expansion report

**PROVISIONAL_FULL_SYSTEM_RENDERED_WITH_LIMITATIONS.** Both A and G PNGs now depict all 26 recognized events, compared with GT-13A's 4. Exactly 4 events retain GT-12 OWNER_VERIFIED status; the other 22 are OMR_PROVISIONAL. This is an increase in actual rendered events, not in independently verified recognition accuracy.

Base: `00b7d5a0110d569c44571cbee78a6cfd4afeafda`. Branch: `experiment/v4-gt13a2-provisional-expansion`. Worktree: `/private/tmp/capomatic-v4-gt13a2`. The user created this isolated worktree after automated approval infrastructure failed; the starting commit and clean branch were verified before edits. Final SHA is reported in delivery. No branches were merged.

## Separate completion levels

| Level | Result |
|---|---|
| SOURCE_RECOGNITION_COMPLETENESS | UNVERIFIED for the whole system. Owner verification remains m3 only; m1/2/4 strings are owner-confirmed but their notes, rhythms, chords, ties and exact syllable associations remain provisional. Independent reference labels: 0. |
| RENDERING_COMPLETENESS | INCOMPLETE. 26/26 event bodies represented (4 verified + 22 provisional), but one event has an unresolved required outgoing tie and header/chord/lyric context remains incomplete. |
| VISUAL_QUALITY | ACCEPTABLE_FOR_PROVISIONAL_DIAGNOSTIC; NEEDS_REFINEMENT for a usable full-system score. Actual final PNGs were inspected by the agent, not an independent optical/human reviewer. |

Count interpretation: **0 entirely unrendered events; 1 rendered event with an unresolved required attachment; 25 events with their scoped note/rest components represented.** Unsupported-event count is not added to 26 because it overlaps the rendered set. Header, missing chord candidate and lyric associations are separate contextual blockers. A complete performance score is not claimed.

## Source and preservation

Fixed source: original Bb PDF page 2, first system, printed measures 1–4. Source raster SHA-256: `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`. No OCR/Audiveris rerun and no A/G reference page access. Targets use the frozen GT-01 A/G MusicXML, not newly repaired recognition. The GT-13A inventory, staff scaffold and GT-12 component masks are read-only inputs.

Both historical output trees are hashed before and after, with their frozen prediction hashes checked separately. GT-12 m3 combined-alpha is reused exactly, including music, E/D chord and six newly typeset Korean syllables. No provisional alpha enters its printed-measure region. New target pixels come from white canvases and rendering masks; original source pixels appear only in the untouched source comparison panel.

`source-event-inventory.json` retains the inherited GT-13A audit, including its historical `renderer_unsupported` and source-candidate fields, so earlier limitations are not silently rewritten. New `render_action`, `render_evidence` and `lyric_strings_status` fields record this run. The current capability/count results are in `provisional-rendering-report.json` and `unsupported-symbols.json`; historical unsupported fields are not current capability claims.

## Predeclared rendering contract

[Protocol](V4_GT13A2_PROTOCOL.json) was written before predictions. Existing GT-05 canonical raster placement, GT-07 upward single flag attachment and GT-12 text registration are imported unchanged. FreeSerif and AppleGothic identities are hash-bound; no fonts were installed or bundled.

- All new noteheads use source bbox-center x, frozen target written pitch and the original middle staff polyline/interline for absolute target y. Physical source center, semantic target coordinate and bitmap anchor are separate fields. The original 0.5px per-axis limit remains enforced.
- Quarter and eighth rests use actual FreeSerif U+1D13D / U+1D13E glyphs at the source rest center, using the existing head-calibrated font scale. No simplified substitute shape.
- Heads/stems require unique explicit SIG head-stem links. Upward single eighth flags require explicit flag-stem plus FLAG_1 evidence and reuse the existing renderer.
- New mixed-beam scope is deliberately limited to these three-up-stem groups. SIG beam membership and MusicXML beam levels/types must agree. Primary source slope, secondary separation, thickness and hook length/direction are retained; the primary is anchored so all stems are at least 3.5 interlines. Missing group members and missing semantic levels fail closed. This extends the source-slope principle of GT-06 rather than claiming generic engraving support.
- Local ties require explicit left/right SIG heads, semantic start/stop and equal target pitch. Original cubic geometry is moved by the endpoints' semantic diatonic displacement, sampled deterministically into 64 width-2 segments. No optical shaping or professional tie engraving is claimed.
- The final m4 cross-system tie is not drawn and no destination is invented; its source relation/ID and unresolved status are retained and labeled on the canvas.

Per target: **20 heads, 6 rests (including two eighth rests), 2 single flags, 6 full beam segments + 4 hooks, 2 local ties** across cached/new content. Newly rendered stems and ledgers accompany their notes. No explicit accidental outside target key context is required by this frozen stream; an unexpected one would block. Clef/key/time/repeat glyphs remain absent and caption-only key context is explicitly declared.

## Chords and lyrics

Measure 1's Bb is an unconfirmed source-image chord candidate; it is labeled as missing, not engraved or transposed. Only cached m3 E/D is engraved. No reference chords are copied.

Measure 1 uses confirmed strings `주 / 님 / 의` and `광 / 야 / 의` with the existing GT-12 lyric font/baseline contract. Their one-to-one x association with the three provisional notes is explicitly provisional. For measures 2/4, confirmed strings are shown as separated diagnostic text below the system, not as certified syllable-to-note placement; associations are withheld because tied notes/extenders need review. M3 remains unchanged. This is newly typeset text, not original lyric-pixel preservation.

## Measured results and visual inspection

| Measurement | A | G |
|---|---:|---:|
| Owner-verified rendered events | 4 | 4 |
| Provisionally rendered events | 22 | 22 |
| Event coverage over recognized denominator | 26/26 | 26/26 |
| Max new head raster-bbox residual per axis | 0.5px | 0.5px |
| Required stem/head/flag/beam contacts checked | 39 | 39 |
| Disconnected checked contacts | 0 | 0 |
| Minimum shared contact ink | 6 pixels | 6 pixels |
| Unexpected intersections among new musical/text masks | 0 | 0 |
| Diagnostic caption ink contacts with notation/scaffold | 0 | 0 |
| Component clipping outside source viewport | 0 | 0 |

Intersections are actual nonzero alpha intersections. Same-note head/stem/ledger/flag and explicit beam-stem contacts are separately treated as intentional. Staff intersections are expected geometry, not edit authorization. The zero counts are limited to rendered components and cannot certify missing context or original text ownership. Source broad protection regions are unchanged and are not replaced by this standalone-canvas analysis.

The first visual inspection found the G diagnostic caption close to its low note; that first frozen run is preserved under `gt13a2-initial-visual-review/`. A new run moved only diagnostic captions above the staff and added actual caption-ink contact measurements. Music geometry, source content, thresholds and GT-12 masks were unchanged. Final outputs were frozen before a second agent inspection. No target-reference comparison was used to tune either run.

Agent inspection: m1/2/4 blue provisional notation is legible and visually distinct from black verified m3. Eighth rests, flags, mixed beam levels, hooks and local ties are visible. Tie strokes and beam raster edges are technical prototype quality. Missing key/clef/repeat context, omitted m1 chord and unaligned m2/4 lyrics prevent use as a performance score. Optical judgment is not inferred from geometry tests.

## Artifacts and validation

Untracked output directory: `/private/tmp/capomatic-v4-gt13a2/gt13a2-output/`:

- `original-bb.png`, `predicted-a.png`, `predicted-g.png`, `comparison-contact-sheet.png`
- `source-event-inventory.json`, `provisional-rendering-report.json`, `unsupported-symbols.json`
- `input-freeze.json`, `prediction-freeze.json`, `semantic-integrity.json`
- `visual-inspection-report.json`, `validation-summary.json`
- Exact per-component alpha PNGs and per-target provisional-alpha unions for future reproducible contact audits.

Prediction panels are 2300×540; contact sheet is 2300×1620. The source crop is the same 2300×410 original-resolution first-system crop. Images are developer-only and incomplete; no copyrighted rasters are committed.

Tests: **212 passed, 1 skipped** (existing external MuseScore dependency). Includes 7 new synthetic tests for mixed beam/hook membership, missing/remote relations, wrong hook direction, deterministic cubic displacement and real eighth-rest raster placement, plus GT-04/05/06/07/11/12/13A and frozen V3 music/gate regressions. The unchanged full V3 guards passed for frozen GT-01 and owner-augmented GT-12 A/G streams. They do not verify original recognition completeness or certify a complete canvas. `git diff --check` and historical hash checks are run before commit. No Full Acceptance.

Reproduction with preserved local evidence: `python -m scripts.research.gt13a2_provisional --out NEW-output`. Existing output directories are rejected.

Next concrete work: owner review of the 22 provisional notes/rhythms and local ties, m1 chord and m1/2/4 syllable associations; then a separately validated header/repeat and cross-system tie contract. Keep source verification and component rendering readiness independent.

No original ink removal, original lyric-pixel compositing, mask changes, Track A promotion, V1/V3 changes, production B2, API/frontend routes, merge or deployment.
