# GT-05A raster anchor calibration

**Decision: ANCHOR_CALIBRATION_VALIDATED under the frozen raster-bbox contract.** The 0.5 px limit is unchanged. This validates mechanical placement of the tested glyph bitmaps, not an optical center, independent musical correctness, complete engraving or production readiness.

Branch `experiment/v4-gt05-anchor-calibration`, worktree `/private/tmp/capomatic-v4-gt05-anchor`, exact base `d35b6f3d7e5258ef48131c52c1b051b2ee507385`. GT-05B is a separate branch from the same base; nothing is cherry-picked or merged between them.

## Frozen design and execution order

[Design](V4_GT05_ANCHOR_PREREGISTRATION.json) committed as `5429dc5fd3bd9cff596b397a28b6343bf62ff12f` before new measurements. Font identity remains GT-04 FreeSerif, SHA-256 **`c1dd2270ff624d66a7f1cd23075b5ce05a662f560be06a70a9599065ce008355`**. No font/model download or alternative font comparison. Glyphs are U+1D158 black notehead and U+1D13D quarter rest.

Calibration: sizes 48/72/94/120, two fixed origins, full x/y phases {0,.25,.5,.75}: **256 cases**. Held-out synthetic regression: sizes 53/87/107, different fixed origins and full phases {.125,.375,.625,.875}: **192 cases**. Both lists and controls were fixed before outcomes; no score positions or reference notation choose cases. The correction was committed as `9a21f5af2af0033887b2bc2edbd32cb00c6644e3` before evaluating held-out cases. The separately guarded rerun tool was committed as `31ed9148b3046ddff822e50cd9b3064daa52ddd7` before the new score render.

“Independent” here means a disjoint, frozen synthetic regression set not used to choose the algorithm. It does **not** mean an outside human/perceptual reference. Actual independent human musical labels remain **0**. The cases test a coordinate contract; they cannot certify that this font's bbox midpoint is the aesthetically correct musical anchor.

## Coordinate definitions and placement-error cause

Pixel-index centers are integers, first center (0,0); that pixel's edges are −.5 to +.5. Pillow bboxes use half-open index limits. Distinguish:

| Quantity | Definition | Role |
| --- | --- | --- |
| DESIGN_OUTLINE_CENTER | Midpoint of font-unit bounds, transformed at explicit baseline | Geometric design point, not asserted raster center |
| RASTER_BBOX_CENTER | `(min_index + max_exclusive − 1)/2` of nonzero alpha pixels | Frozen target/residual criterion |
| RASTER_COVERAGE_CENTROID | Alpha-weighted pixel-index mean | Measured diagnostic, never substituted as the pass metric |
| OPTICAL_CENTER | Perceptual/engraving judgment | **UNDEFINED**, not inferred from these tests |

**Primary classification E: combination of B (fractional placement/quantization) and D (missing raster registration in the research helper).** The old measurement formula already used the correct pixel-index convention; this is not a repair to musical pitch or a discovered FreeType defect. The implementation assumed that placing a continuous design-outline midpoint on the staff coordinate would also place a raster bbox midpoint there. That assumption fails after baseline-phase quantization and raster bearings.

The installed Pillow 12.3.0 `ImageDraw.text` source splits the baseline into integer coordinates and fractional `getmask2(start=...)` input, then paints the returned raster at integer pixel coordinates. Font outline units and this integer raster support are different coordinate objects. Local source-file hashes are retained with results. The four fixed phase examples below are from the original calibration family, not newly selected pass/fail cases:

| Requested x, y | Outline-derived baseline | Actual nonzero bbox | Index center | Residual |
| --- | --- | --- | --- | --- |
| 96,128 | 81.43,136.554 | [84,119,107,138) | 95,128 | **−1,0** |
| 96.25,128 | 81.68,136.554 | [85,119,108,138) | 96,128 | −.25,0 |
| 96.5,128 | 81.93,136.554 | [85,119,108,138) | 96,128 | −.5,0 |
| 96.75,128 | 82.18,136.554 | [85,119,108,138) | 96,128 | −.75,0 |

These reproduce a 1 px error without measures 3/32. At size 94, the head outline bounds are [35,−10,275,192] in 1000 units/em, midpoint [155,91]. The diagnostic traces retain integer baseline, fractional start, `getmask2` offset and measured support separately; the full returned mask also contains bearing/advance whitespace and is not the ink bbox.

Every legacy calibration case of a given glyph/size has the **same cropped alpha hash**, despite differing requested fractional phases. Old and corrected outputs have identical cropped alpha and dimensions in **256/256 calibration pairs**. Thus this observed error is placement/registration, not a changing glyph silhouette, antialias threshold or asymmetric-shape adjustment. Asymmetry still makes coverage centroids differ from bbox centers; that does not justify calling either an optical center.

GT-04 rounded the nominal font size to 94 and consistently used that size for rasterization and design scaling. No font size changed in the correction. Font-size rounding changes raster geometry across sizes, but is not an inconsistent-size bug explaining the 1 px score residual. Each tested size is registered independently.

## Minimal correction

Research-only `gt05_raster_anchor.glyph`:

1. Rasterize the unchanged glyph/font/size at a fixed **integer** baseline with the same L-mode antialiasing.
2. Crop only empty bearing/advance margins. Preserve every nonzero alpha value; do not resize, threshold, dilate or reshape the glyph.
3. For cropped width/height W/H, use its explicit index anchor `a=((W−1)/2,(H−1)/2)`.
4. For requested coordinate t, choose destination `d=floor(t−a+.5)` independently per axis. This is nearest-grid placement, ties toward positive infinity. The resulting center is `d+a`, so each residual is bounded by .5 px mathematically.
5. Reject missing, nonfinite or clipped placements. Report requested staff point, actual font-outline point, integer baseline, raster anchor, actual bounds and residual separately.

The glyph itself supplies the bearing/registration information. There is **no constant offset chosen for jayu or measures 3/32**, and no change to pitch-to-y calculation. This intentionally replaces unconstrained fractional-baseline placement with a fixed raster phase; it is a documented research rendering policy, not an assertion that outline and raster centers are interchangeable.

`gt04_visual.render` gains an optional research glyph function. Its default remains the historical GT-04 glyph routine. The GT-05 caller explicitly supplies the calibrated function; original GT-04 worktree/code/images remain unchanged. Only placement reporting is adjusted to keep requested semantic x distinct from actual outline/raster coordinates. No production renderer is modified.

## Synthetic results and controls

| Family | Legacy passes | Legacy maximum x/y | Corrected passes | Corrected maximum x/y |
| --- | --- | --- | --- | --- |
| Calibration | 84/256 | 1.25 / 1.5 px | **256/256** | **.5 / .5 px** |
| Held-out regression | 36/192 | 1.375 / 1.375 px | **192/192** | **.375 / .375 px** |

Actual mask pixels, not helper-reported residuals, are scored. Repeated mask bytes are deterministic. Corrected cropped alpha hashes are translation-invariant for every held-out glyph/size; calibration size deltas from the old method are **0 width / 0 height**. This invariance does not claim invariance under changing font size.

All declared topology/negative controls pass: known integer-center rectangle; explicit edge/index half-pixel distinction; intentional +1px error detected; wrong-font hash, NaN and clipping rejected; fixed staff crossing; nonempty stem/head contact; required ledger contact; no unintended cross-group ink collision. The synthetic topology uses distinct positions, with 46 pixels of head/staff contact and 46 pixels of ledger/head contact recorded as intended, not disposable source ink.

Maximum corrected held-out **coverage-centroid** residuals are about .941 x / .825 y px, which can exceed .5. They are reported, not relabeled as bbox success or optical correctness. The unchanged .5 criterion applies to raster bbox centers only. External physical/perceptual annotation remains necessary for broader anchor claims.

## Gated new visual run

Only after the held-out gate passed, **GT05A-score-rerun-01** rendered the same frozen Bb source semantics, source selection and original geometry: printed **3 and 32**, A −1 and G −3. Same font and size 94; no reference page access is used to correct glyphs or pitch. The original full V3 guard is rerun against frozen A/G MusicXML and remains PASS. No missing chords are fabricated.

| Scope | GT-04 max bbox residual | GT-05A max bbox residual | Unexpected ink collisions | Protected source-ink contacts | Clipping |
| --- | ---: | ---: | ---: | ---: | ---: |
| m3 A | 1.0 px | **.5 px** | 0 | 0 | 0 |
| m3 G | 1.0 px | **.5 px** | 0 | 0 | 0 |
| m32 A | 1.0 px | **.5 px** | 0 | 0 | 0 |
| m32 G | 1.0 px | **.5 px** | 0 | 0 | 0 |

Logical note x and semantic pitch-y deviations remain 0; page/staff polylines, system identity and original measure boundaries are unchanged. All selected events are represented without duplicates. Stems and ledger contact are reevaluated naturally from the newly placed bitmap. Runtime was **2.611 s**, excluding preparation; peak memory not measured. Rendered-prototype subdecision: **VISUAL_POC_RENDERED_WITH_LIMITATIONS**, not production-ready.

New, untracked paths under `/private/tmp/capomatic-v4-gt05-anchor/gt05-anchor-output/revised-visual-prototype/`:

- `original-bb.png`
- `predicted-a.png`
- `predicted-g.png`
- `comparison-contact-sheet.png`
- `rendering-metrics.json`, `rendering-limitations.json`, `prototype-freeze.json`, technical alpha masks.

`score-run-binding.json` binds the independent gate hash, glyph algorithm hash, unchanged source-selection hash and historical GT-04 freeze. New outputs are frozen in their own directory. Original GT-04 files are verified unchanged, never overwritten. No new PDF, target lyric composite or reference-driven rerender was made.

## Remaining limits, reproduction and next step

This still supports only the tested quarter-note/rest, detached-stem, ledger/staff/simple-barline scope. Beams, flags, ties/slurs, explicit accidentals, standalone clef/key/time signatures, repeats/endings, moving attachments, full chords and protected lyric composition remain unsupported or unverified. Original lyric pixels remain in the untouched source panels. Source chord coverage is still incomplete; no PARTIAL ink is promoted to OwnedInk. No full-score rendering, API/frontend route, production V1/V3 change, merge or deployment.

Reproduction uses the retained existing font and NEW output roots. Run `gt05_anchor_study` for frozen calibration cases, then `gt05_anchor_gate synthetic` for the disjoint regression/control family. `gt05_anchor_gate score` refuses a failed/changed algorithm gate, changed historical images, a changed source selection, failed full integrity, existing run binding, or an output inside GT-04 evidence. A repeated score run needs a separate run identity; do not overwrite the one reported here.

Local `calibration-report.json`, `synthetic-controls/`, `independent-tests/` and score binding retain exact results, source/backend hashes and control evidence. The worktree's targeted tests and final `git diff --check` are recorded in `validation-summary.json`; no Audiveris/model execution is needed by unit tests and no Full Acceptance is run.

The independent scorer ran before two additional historical-output/run-identity write guards were added to its nonexecuted score branch. Its exact execution-time source is retained as `scorer-at-independent-execution.py`, matching the SHA in `independent-tests/gate.json`; the synthetic scorer/controls were not retuned or rerun. The algorithm remained frozen throughout. Final targeted GT-01–05A/V4/V3 music/gate tests: **354 passed, 1 skipped**; the skip is the existing external MuseScore dependency.

Next recommended anchor experiment is independently referenced optical/musical validation and a separately preregistered broader notation group. Keep the .5 px bbox contract while separately judging glyph/stem/beam/curve engraving. Passing a center metric does not establish complete score quality, recognition truth or an architecture winner. Keep prototypes and coordinator reports away from the unchanged independent annotation packet/pilot.
