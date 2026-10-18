# GT-07B isolated flag rendering

**FLAG_VISUAL_POC_NEEDS_REFINEMENT.** Actual A/G PNGs render one upward eighth-note flag with calibrated notehead, stem and required ledger lines. Geometry and attachment checks pass, but protected-envelope contacts and a G-target source text-support contact prevent a safety PASS. No mask is relaxed and no alternate example replaces this outcome.

Branch `experiment/v4-gt07-flag-rendering`; worktree `/private/tmp/capomatic-v4-gt07-flags`. Exact starting SHA **`cdb50339d89db475f016c922f4a8f6d40e7383fd`**. [Selection/geometry protocol](V4_GT07_FLAG_PREREGISTRATION.json) first committed as `c0ee880`; renderer as `8ccec87`; source-free gate and execution revision **`fe9356bb5b655e2112083b463a68632b45239184`**, all before score rendering. The final report SHA is in the final handoff and local validation manifest; the document commit can be identified using `git log -1 --format=%H -- docs/V4_GT07_FLAG_RENDERING.md`. GT-05B and GT-07A changes are not merged or consumed.

## Frozen source scope

Earliest eligible singleton flag in printed measure/onset order: **printed measure 2, offset 3/2**, event `p1:m1:n0` (zero-based OMR index), source F3, duration **1/2 quarterLength**. Head `sheet#1:1856`, stem `2772`, flag `5590` (`FLAG_1`). There is one explicit RIGHT head–stem edge and one flag–stem edge. MusicXML agrees on an upward, unbeamed, undotted eighth note with no tie, articulation or expression. This is consistent evidence from the same recognition pipeline, not independent human truth.

The two relations are `5227b5007b8f5b6b2c33` and `771094eff4ff97ae4c42`; raw head/flag/stem geometry and page/staff identity are preserved in `gt07-flag-inputs/selection.json`. The target spelling and rhythmic identity are checked against frozen V3 semantic artifacts before rendering: **E3 for A −1**, **D3 for G −3**. No pitch is repaired using references.

Only this complete head/stem/flag/ledger group is in scope. Eight other measure events are explicitly excluded, not simplified. Full measure and full score support are not claimed. Downward flags and sixteenth/double flags remain **unsupported**, even though the font contains other flag glyphs. Unsupported moving attachments cause rejection rather than silent omission.

## Glyph and attachment contract

The unchanged GT-05 [raster placement helper](../scripts/research/gt05_raster_anchor.py) is imported for noteheads and fixed-phase glyph generation. Its SHA-256 remains `1c8e02a08c87db86b4a956b8c989244bbd021265365116c36e0f2a902f2c81b0`. Same FreeSerif font SHA-256: `c1dd2270ff624d66a7f1cd23075b5ce05a662f560be06a70a9599065ce008355`. No new font binary, model, dependency or OCR call.

The real flag is **U+1D16E COMBINING FLAG-1**, font glyph `flag_1.cmb`, outline bounds [0,177,222,767] at 1000 units/em. It is not a hand-drawn approximate hook or an entire precomposed note. The font outline contains the explicit stem-joining strip x=0..23, y=547..767; at size 94 this is approximately 2.16 px wide, consistent with the existing 2 px stem contract. This source inspection supports the joining-edge interpretation without assuming the flag bbox midpoint is its attachment anchor.

The fixed-phase raster's first ink in its leftmost occupied column is the explicit upward-stem attachment anchor. For this font/size it is bitmap-local [0,0]. Placement translates the unchanged bitmap to the integer stem tip. Actual attachment, bbox/outline centers and notehead semantic coordinates are recorded separately. No font scaling, fractional score-tuned offset, pitch adjustment or reference-based correction is introduced.

Stem direction comes from the RIGHT relation and upward semantic stem, not inferred from note y. Length is `max(3.5*interline, corrected_semantic_source_y - persisted_source_stem_top)`: here **91.255982 px**. Stem tips are nearest-integer rounded with `floor(t+.5)`, A [976,489], G [976,498]. The source stem-top evidence is geometry, not a detector head center substituted for semantic pitch. Ledger positions are recomputed from target diatonic staff position. Original note x, staff polylines, page coordinates, system identity and measure boundaries are retained.

Four preregistered source-free controls at phases 0, .125, .5, .875 pass before score rendering. They require actual head bbox residual ≤0.5, head–stem and stem–flag ink contact, zero head–flag overlap and exact integer flag attachment. The render command rejects absent/failed/stale controls or changed font, code, protocol or calibration hashes. These are mechanical contract tests, not independent optical/musical validation.

## Measured actual-raster results

| Metric | A | G |
| --- | ---: | ---: |
| Notehead maximum residual, either axis | **0.5 px** | **0.5 px** |
| Actual flag attachment residual x/y | **0/0 px** | **0/0 px** |
| Head–stem shared ink | 12 px | 12 px |
| Stem–flag shared ink | 22 px | 22 px |
| Head–flag overlap | 0 | 0 |
| Unexpected within-layer ink collision pairs | 0 | 0 |
| Requested note x / pitch-y deviation | 0 / 0 | 0 / 0 |
| Staff / measure-boundary geometry deviation | 0 / 0 | 0 / 0 |
| Missing / duplicate scoped events | 0 / 0 | 0 / 0 |
| Page/crop clipping | 0 | 0 |
| New music/protected-envelope pixels | **24** | **233** |
| Those also dark in original at <127 | **0** | **34** |
| Independently confirmed text-contact pixels | **UNKNOWN** | **UNKNOWN** |

The notehead's actual raster residual is [+0.5,−0.255982] px for both targets. The real flag bitmap is 21×57 px at the unchanged size 94. Source and target glyph dimensions need not match different editions/fonts. Target-layer measurements use actual raster ink, not bbox overlap. Staff/new-symbol contacts are intentional on the new white canvas, not source-erasure permission.

Both full V3 semantic guards were executed unchanged: **PASS**, 37/37 measures, 169/169 events, 7/7 harmonies, no issues, for both shifts. This is not recognition completeness or independent whole-score correctness. Source original crop bytes, including Korean lyrics, are exactly preserved. No lyric compositing/retyping or original music removal occurs.

Render elapsed **0.914 s**, excluding source preparation/tests; peak memory not measured. Coordinator visual inspection confirms actual recognizable single-flag notation with target ledger changes. No professional engraving grade or external optical approval is asserted; independent human labels remain **0**.

### Post-freeze source-support contacts

A separate read-only diagnostic checks frozen music-only alpha against persisted source glyphs outside the explicit selected group. It verifies prediction freeze, selection binding and coordinate dimensions; it never changes placements. This is an additional post-freeze diagnosis, not a tuned acceptance rule.

No contact with persisted **unrelated musical**, structural or other unknown glyph support is found for either target. A has no stored text-support contact. G has **47 unique text-support candidate coordinates**, referenced by both lyric-item `4106` and word `4135` (47 each, **not 94 distinct pixels**). This is evidence for a possible genuine lyric conflict, not independently certified text ownership. The 34 original-dark contacts and 47 processed-support coordinates are different measurements; neither can be relabeled as accepted human truth.

All **47** text-support contact coordinates are inside the **233** protected-envelope contacts; none is an additional exposure outside those envelopes. Exactly 34 of those 47 are <127 in the original grayscale, accounting for all 34 measured protected/original-dark contacts. `text-contact-set-relations.json` records these set relationships. This does not change UNKNOWN confirmed-text status or authorize composition.

The 24/233 envelope contacts remain blockers even where source dark/support tests are empty. No protection is shrunk based on GT-07A or any candidate attribution. Full future-score collision safety remains **UNKNOWN**, because other groups have not been transposed/rendered together. These are neither source-ink ownership nor B2 authorization.

## Regressions and freeze

GT-05 controls: all **8 PNGs** for quarter/rest measures 3 and 32 are byte-identical to historical GT-05A. GT-06 control: all **6 PNGs** for the measure-6 two-sixteenth/double-beam group are byte-identical to GT-06, and its protection failure correctly remains `EXTENDED_VISUAL_POC_NEEDS_REFINEMENT`. No prior image is overwritten.

Actual new untracked files under `/private/tmp/capomatic-v4-gt07-flags/gt07-flag-output/`:

- `original-bb.png`, `predicted-a.png`, `predicted-g.png`, `comparison-contact-sheet.png`
- `rendering-metrics.json`, `rendering-limitations.json`, `prototype-freeze.json`
- `A/G-notation-alpha.png` and `A/G-music-only-alpha.png` technical masks.

All viewing panels say DEVELOPER-ONLY / INCOMPLETE / NOT FOR PERFORMANCE OR PRINTING. Separate validation outputs contain source-free controls, regression comparisons, post-freeze source-contact reports and reference context crops. Alpha masks are technical evidence, not a finished score. Predictions and hashes were frozen **before** the reference comparison.

## Reference diagnosis, limits and next step

After freeze verification, the unchanged GT-04 reference helper finds one algorithmic note candidate per target with matching spelling and duration. Raster center minus reference detected center: A [−16.5,0] px, G [+12,0.5] px. The preserved Bb x layout differs from reference typesetting; these differences are not used to move predictions. There is no accepted human denominator and no accuracy percentage. No reference page supplies missing chord answers or glyph anchors.

Source chord coverage remains incomplete: 7 recognized harmonies against 24 coordinator-identified candidates. No new OCR, invented chord, chord layer, width claim or complete lyric composite. Double/downward flags, curves, explicit accidentals, moving attachments and standalone clef/key/time remain unsupported. Flag extension does not imply whole-measure support.

Targeted final GT-01–07B/V4/V3 music/gate regressions: **393 passed, 1 skipped** (external MuseScore dependency), including 18 flag/gate tests and 2 source-contact tests. Formatting and `git diff --check` pass; final hashes/commands are in local `validation-summary.json`. No Full Acceptance.

Next priority is independent source-only extent review for the possible G lyric conflict and preservation of the current fail-closed decision. Any later attempt at double/downward flags needs its own selection/attachment contract; safe composition cannot be inferred from this single-glyph result. No architecture winner is selected.

Original GT-01–06 artifacts, GT-02 111-case packet and GT-03 14-case pilot are unchanged. No source PDF/raster edits, V1/V3 production behavior, integrity/ownership gate, Track A PARTIAL promotion, production B2 renderer, V4 API/frontend/runtime route, merge or deployment.
