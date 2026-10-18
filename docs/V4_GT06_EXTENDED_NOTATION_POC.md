# GT-06 extended notation prototype

**EXTENDED_VISUAL_POC_NEEDS_REFINEMENT.** Actual isolated A/G notation PNGs contain a complete two-note, two-beam group. Raster placement, all required connections and unchanged full V3 guards pass. Existing protected-region envelopes intersect the new notation, so safe text composition is **not established**. No excerpt replacement, protection relaxation or production gate change follows this result.

Branch `experiment/v4-gt06-extended-notation`, worktree `/private/tmp/capomatic-v4-gt06-extended`. Starting SHA **`16c43394b3b63aa19e08bd35ae333a7da148d11c`**. Selection/measurement design was committed as `af63774` before rendering; exact execution revision **`312e2b180e0a7936ad8d613775046e8137200220`** before results. The report's commit is recorded in the final handoff and local validation manifest; use `git log -1 --format=%H -- docs/V4_GT06_EXTENDED_NOTATION_POC.md` to identify it rather than relying on a movable branch name. GT-05B is neither merged nor used.

V3 is the existing production recognition/transposition/integrity pipeline; V4 here is offline research. Track A's source-pixel ownership authorization and production B2 rendering gates remain separate and unchanged. GT-01–05 are the preserved earlier research baselines; no full acceptance corpus is run here.

## Frozen scope and evidence

[Preregistration](V4_GT06_PREREGISTRATION.json) selects the first complete atomic group in printed measure/onset order with exactly two single-head sixteenth notes, two full beams, explicit head–stem and every beam–stem edge, and no unsupported moving attachments. This is a bounded group experiment, **not a whole-measure renderer**. Earlier groups in measures 2 and 4 failed the predeclared semantic/attachment/geometry restrictions; no selection used rendered outcomes or reference answers.

Selected: **printed measure 6, quarterLength offsets 3/2 through 2**. Group `sheet#1:1230`; heads `1896,1900`; stems `2847,2848`; beams `1230,1236`, all on `sheet#1`. Six explicit SIG relations support two head–stem and four beam–stem connections. Source MusicXML additionally supplies two beam levels, start/stop, for both notes, with no ties/articulations/expressions. This is consistency evidence from the same recognizer, not an independent human reference. Source identity, onset, duration and target semantic spelling are checked, rather than inferred from detected centers. Event IDs use zero-based OMR indices: `m5` maps to printed measure 6 in the frozen physical registration; this index convention is not a general cross-score alignment rule.

| Event | Source | A −1 | G −3 | Duration quarterLength |
| --- | --- | --- | --- | --- |
| `p1:m5:n0` | Bb3 | A3 | G3 | 1/4 |
| `p1:m5:n1` | C4 | B3 | A3 | 1/4 |

Eight other measure events (two rests, six notes), their mixed beams/hooks, ties and any attachments are **excluded from the declared scope**, not simplified or silently omitted. The source panel displays the original full measure; targets explicitly label the offset-only group and incomplete status. Clef/key context is supplied as text; standalone clef/key/time glyphs are absent. No claim of a complete measure or usable transposed score.

Hash-bound inputs are the unchanged GT-01 frozen Bb/A/G semantics and GT-02 Bb registration. No new recognition or OCR occurred. Bb raster SHA-256: `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`. `gt06-inputs/selection.json` retains every semantic/graph hash, selection decision, excluded event ID and full guard report. Its SHA-256 is `2b0000585af5572ef21af9bf53974842289b188d46bdd1ca658f65ff5b77f00d`.

## Placement and new beam capability

The unchanged [GT-05 raster algorithm](../scripts/research/gt05_raster_anchor.py) is imported, not duplicated or offset-tuned. Algorithm SHA-256 remains `1c8e02a08c87db86b4a956b8c989244bbd021265365116c36e0f2a902f2c81b0`; FreeSerif SHA remains `c1dd2270ff624d66a7f1cd23075b5ce05a662f560be06a70a9599065ce008355`. The original **0.5 px per axis** raster-bbox limit remains fixed. Actual nonzero-alpha bbox centers are measured separately from placement metadata.

Original note x, absolute target pitch y, page coordinates, staff polylines and measure boundaries are retained. Detected physical center, corrected source staff y, target staff y, outline anchor, raster anchor and actual ink bounds remain distinct fields. Requested x deviation is 0; grid placement gives actual raster x residual +0.5 px for these heads. No physical center is substituted for a semantic pitch anchor.

Explicit RIGHT head–stem relations establish upward stems. Stem columns come from actual head ink; stems and staff/ledgers use the existing 2 px rule. Primary beam slope is the persisted `−4.5/83 = −0.054216867...`. Both rendered beam levels are parallel to that primary slope; this is not a claim to retain the secondary source beam's slightly different fitted slope. Source median separation is 13.8 px and each persisted thickness rounds to 10 px. Both beam endpoints meet the rendered stem columns, x=938 and 1018. Vertical intercept is determined from target pitches so the shortest head-center-to-primary-median distance is at least 3.5 interlines; this is a declared research engraving rule, not reference fitting. Group notation is reconstructed on a new white canvas, never erased from source pixels.

## Measured results

| Check | A | G |
| --- | ---: | ---: |
| Max notehead raster residual, either axis | **0.5 px** | **0.5 px** |
| Logical note x / semantic pitch-y deviation | 0 / 0 | 0 / 0 |
| Staff / measure-boundary coordinate deviation | 0 / 0 | 0 / 0 |
| Head–stem contacts | 2/2 | 2/2 |
| Stem–beam contacts | 4/4 | 4/4 |
| Required beams rendered | 2/2 | 2/2 |
| Unexpected symbol-to-symbol ink collision pairs | 0 | 0 |
| Missing / duplicate events within declared scope | 0 / 0 | 0 / 0 |
| Page / crop clipping | 0 | 0 |
| New music ink inside protected envelopes, pixels | **1,982** | **2,026** |
| Same pixels also dark in original at <127 | **1,543** | **556** |

Every head–stem contact has 12 shared raster pixels. Primary and secondary beam contacts are 11 pixels at the first stem and 20 at the second. Contact counting uses actual raster ink, not bbox proximity. Only explicit same-note head/stem/ledger and declared beam/stem contacts are allowed; staff crossings are intentional new-layer contacts. No Track A source ownership is inferred.

The original full V3 guards pass for **both shifts**, each with 37/37 measures, 169/169 events, 7/7 harmonies and no reported issues. This certifies the frozen semantic transposition under the existing guard, not recognition truth or that every possible engraving feature is validated. No integrity gate is waived.

Render elapsed time: **2.008 s** for this bounded A/G run, excluding preparation/tests. Peak memory not measured. Visual inspection confirms actual double-beam notation, not coordinate overlays; raster stairs at the sloped beam edges and the limited font/stroke contract are not professionally graded. Independent optical/musical reference labels remain **0**.

### Protection outcome

The original lyric/source crop bytes equal the original raster crop exactly. No lyric OCR/retyping, source erasure, source/target composite or copied target reference content is used.

The conservative protection remains active. `Direction` regions `4134` ([945,588,1290,1011]) and `4135` ([945,588,1054,968]) span music and multiple vertical bands, while smaller lyric protections also remain present. Their origin/ownership has not been resolved here. Thus the intersection counts above are **potential protected-content contacts**, not verified counts of lyric ink: original dark pixels inside broad text envelopes can themselves be musical notation. The <127 measurement is diagnostic only, not a new ownership rule. It is neither valid to declare all 1,543 pixels Korean text nor to discard the regions because they look overbroad. The envelope collision blocks the safety check and final PASS. No masks, compositing or protection rules were changed after viewing results.

## Controls and output freeze

Measures **3 and 32** were rerendered once into `gt06-validation-output/regression-controls/` using the unchanged GT-05 method. All **8 PNG files** are byte-identical to GT-05A, including the original/predicted/contact sheets and four alpha masks. The legacy max residual remains 0.5 px; no historical output was overwritten.

Actual new untracked output root: `/private/tmp/capomatic-v4-gt06-extended/gt06-output/`:

- `original-bb.png`, `predicted-a.png`, `predicted-g.png`
- `comparison-contact-sheet.png`
- `A-notation-alpha.png`, `G-notation-alpha.png` (technical alpha evidence, not score views)
- `rendering-metrics.json`, `rendering-limitations.json`, `prototype-freeze.json`

All four viewing PNGs carry DEVELOPER-ONLY and INCOMPLETE / NOT FOR PERFORMANCE OR PRINTING labels. `prototype-freeze.json` hashes the outputs before reference comparison. No PDF or full score is generated. The frozen outputs are not regenerated after reference access.

## Post-freeze reference diagnosis

The unchanged GT-04 comparison helper checks the entire new freeze before opening A/G reference images. Its report/contact context crops are separately retained in `gt06-validation-output/reference-comparison/`. Both notes have algorithmic reference candidates in each target: spelling and duration agree for **2/2 candidates per target**. This is not an independently verified accuracy denominator or a whole-score percentage.

Raster center minus reference detected center: A x=−19/−16.5 px, y=+0.5/0 px; G x=+13.5/+12.5 px, y=0/+0.5 px. References are differently typeset; the prototype deliberately keeps Bb x and measure geometry. These x differences are not used to shift predictions. Neither reference detector centers nor candidate agreement establish an independently correct glyph anchor. Reference harmonic and lyric-composition correctness remain unverified.

## Validation, limitations and next step

Final-state targeted GT-01–06/V4/V3 music/gate regression: **373 passed, 1 skipped** (existing external MuseScore dependency). The GT-06 suite contributes **19 tests**, including actual-raster measurement, both stem directions, pitch changes, deterministic slope/spacing, invalid geometry, missing relations/heads, unsupported attachments, semantic beam-level mismatch and genuine unrelated ink collisions. No tests require Audiveris or score/model downloads. Final formatting and `git diff --check` are recorded with preservation hashes in `gt06-validation-output/validation-summary.json`; no Full Acceptance.

Source harmony coverage remains 7 recognized harmonies against 24 coordinator-identified candidates. No missing chord is invented, no reference chord copied, no chord layer or rendered-width claim made. Flags, mixed/partial beams and hooks, curves, explicit accidentals, moving attachments, full standalone context and lyric composition are **not supported by this experiment**. They remain blocked when required, even though two full beams now have a tested bounded contract.

Next priority is a separate provenance audit of the broad `Direction` protections, preserving every protection until independently justified; no rendering-offset tuning or easier-excerpt substitution. Any future proposal to refine protection needs explicit persisted sentence/word lineage, source-only text-extent observations from independent readers and adjudication, and evidence that every text-ink pixel remains protected. Uncertain extents stay protected; a plausible screenshot or these collision counts are insufficient. This is a future evidence requirement, not permission to shrink masks now. The next notation capability to preregister is stem-side/direction-correct flags, before attempting the other events in this measure or complete mixed beam/curve groups. Keep geometry/optical review separate from pixel-center success. This result does not select an architecture winner.

Original scores and GT-01–05 artifacts/annotation packets are unchanged. No V1/V3 production code, musical integrity rule, B2 gate, Track A COMPLETE-only ownership, API/frontend/runtime V4 route, production flag, merge or deployment is changed.
