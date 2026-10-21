# GT-17B owner approval integration

The full nine-system, 37-measure A/G experimental preview now carries all 24 owner-approved chord interpretations and 167 owner-approved Korean syllable wordings/row assignments. Three source-visible missing ties and the unequal-pitch m31 slur have been added to a separate augmented MusicXML source and standalone notation layers. **Only 86 of 169 event cores remain owner-verified; 83 event cores, 79 existing provisional syllable-onset associations and 20 continuation candidates remain provisional.** Source completeness and performance readiness remain UNVERIFIED / INCOMPLETE.

## Revision and approval boundary

Base: `1c532c4a6cfa332a50e889740088aed064511996`. Branch: `experiment/v4-gt17b-owner-integration`. Worktree: `/Users/juahnkim/transchord/.gt17b-owner`, already present at the exact base and clean when resumed. The containing commit is the implementation revision; its exact SHA is supplied at delivery.

[The actual current owner instruction](V4_GT17B_OWNER_APPROVAL.txt) is preserved verbatim. It is an attributable user approval of the preceding GT-17B review scope, not an invented separate submission, signature, timestamp or independent label. The new `owner-interpretation-layer.json` binds that text to the frozen original review checklist, full source page, candidate inventory, unresolved-object records and packet freeze. It embeds the prior m17–19 approval separately and retains all stable source IDs and raw observations.

Approval covers the twelve new printed chords/locations, Korean wording and row distinctions, Chorus/Tag labels, visible repeat/ending locations, three tie interpretations and one slur interpretation. It does not approve all new music events, all lyric onsets, all continuation marks, a complete repeat playback route, original-ink removal or source-pixel composition. Independent ground truth remains **0**.

## Frozen source and history

Read-only baseline output: `/private/tmp/capomatic-v4-gt17b/gt17b-final-output/`. All 842 prediction-manifest entries, the separate post-freeze semantic-audit manifest and all other baseline-directory files passed before/after preservation checks. GT-16B, GT-16C and GT-17 document bindings and complete artifact snapshots also passed.

| Original-side input | SHA-256 |
|---|---|
| source.png | `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de` |
| recognized.omr | `857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638` |
| visual-graph.json | `f8725c39beaaecc877ccf48b803b79a419c2d6e60aa73bc9428a39de11596508` |

No A/G reference page, OCR, recognition rerun, model download or new dependency was used. Original protection geometry remains in the unchanged source graph; this standalone-layer operation neither loads nor edits production protection masks. No source/prediction file is overwritten. The failed first development run, successful development output and first final freeze are retained separately. The delivered `final-v2` changes warning text to express the approval limits accurately; its music curves and all earlier music/text geometry equal the first final run.

## Exact source curve investigation

Each candidate is bound to two unique original head Inter IDs, printed measure/onset, written pitch, voice, original bbox and staff pitch-position. The two events must be adjacent in the frozen event sequence, have no conflicting tie role, lie in the same expected source system, and match the reviewed native source window. A tie additionally requires equal written pitches. The m31 slur deliberately retains unequal pitches and no tie role.

Onsets below are quarterLength units, reset per printed measure. Source coordinates are page pixels, x-right/y-down, with right/bottom-exclusive bboxes.

| Relationship | Source head IDs | Source addresses | Recognized pitches | New semantic record |
|---|---|---|---|---|
| m21→22 | 2147→2149 | m21 15/4→m22 0 | C5→C5 | Tie START/STOP |
| m31 | 2403→2423 | 5/2→3 | C5→Bb4 | Slur, **not tie** |
| m33 | 2411→2413 | 5/2→3 | C5→C5 | Tie START/STOP |
| m35 | 2465→2467 | 11/4→3 | C5→C5 | Tie START/STOP |

All IDs have the `sheet#1:` prefix. No persisted curve Inter or original slur-head relationship exists for these four windows. Consequently no fabricated SIG ID or raw OMR edge is introduced. New records explicitly say `original_persisted_curve_id: null`, preserve the entire original candidate, and identify the augmentation as a separate source-backed interpretation.

Agent source-only inspection finds the four visible upper arcs over those adjacent heads. Cubic centerlines are manually measured diagnostic approximations from those source crops, with each endpoint inside its corresponding head's x extent and locally above it. This geometric check is **not independent optical validation or exact source-pixel ownership**. Original head/staff pitch positions agree with the semantic endpoint pitches; this does not owner-certify the remaining event inventory. The source cubic, source window, head IDs, target translation and measured endpoint gaps are retained per curve.

A major maps C5→B4 and Bb4→A4; G major maps C5→A4 and Bb4→G4. The three ties therefore have equal target pitches, while the slur remains B4→A4 or A4→G4. Their semantic identity, order and tie roles survive target transposition and MusicXML roundtrip. The pre-existing source slur is retained, giving two source slur spanners in total.

## Source correction and coverage

| Quantity | Historical frozen prediction | Revised interpretation/render |
|---|---:|---:|
| Printed systems / measures | 9 / 37 | 9 / 37 |
| Recognized/displayed event cores | 169 | 169 |
| Owner-verified event cores | 86 | 86 |
| Provisional event cores | 83 | 83 |
| MusicXML harmonies | 16 | 24 |
| Displayed chord strings | 24 | 24, all owner-approved |
| Owner-approved lyric wording/row syllables | 88 | 167 |
| Owner-verified exact syllable onsets | 88 | 88 |
| Provisional syllable onsets | 79 | 79 |
| Displayed continuation marks | 50 | 50 |
| Owner-verified / provisional marks | 30 / 20 | 30 / 20 |
| Newly added reviewed ties / slurs | 0 / 0 | 3 / 1 |

Four of the twelve new approved chords already existed in the inherited source; eight are added. Approved source chords preserve qualities, seventh extensions, slash basses and source locations: Bb→A/G, F→E/D, Gm7→F#m7/Em7, Bb/D→A/C#/G/B, Eb→D/C, Gm→F#m/Em. Both serialized targets are checked against these expectations individually. No additional chord absence or playback inference is made.

The 79 candidate syllables are inserted into the new semantic source at their existing provisional associations so that image and XML proposals can be compared. Their wording/rows are now approved; insertion does not certify those onset assignments. `source-event-inventory.json` preserves each raw tie field and adds separate interpreted tie/slur fields. Event-core verification is unchanged. `source-coverage-matrix.json` retains per-measure provisional status and adds field-specific approval, rather than replacing an entire measure with OWNER_VERIFIED_SOURCE.

## Rendering and numerical safety

The frozen GT-17B standalone full-alpha/component masks are reused; only four new curve layers are added. No notehead, stem, beam, rest, chord, lyric, extender, staff, key, ending or old tie geometry is recomputed. Existing nonzero alpha bytes remain unchanged. Target curve y follows the existing source-relative endpoint-offset/interpolated-translation contract, independently of physical-head center versus semantic target pitch. The 0.5px notehead criterion is unchanged and met by the inherited event geometry.

Each new curve is checked against every frozen component in its system using exact nonzero-alpha masks. Staff intersections are intentional; a barline intersection is permitted only for an equal-pitch adjacent-measure tie crossing its own source boundary. A slur, same-measure tie, unrelated object or wrong boundary does not receive that exemption. Curves must remain inside the canvas, avoid one another and have positive endpoint-to-head ink-center gaps no greater than 1.5 local staff spaces. They are conventionally detached arcs, not stems requiring head contact.

| New curve metric | A | G |
|---|---:|---:|
| Unexpected component / lyric contacts | 0 | 0 |
| Newly clipped curves | 0 | 0 |
| Intentional staff contacts, summed over four curves | 64 | 201 |
| Intentional m21 own-barline contacts | 8 | 8 |
| Unique new curve/existing-ink contact coordinates | 72 | 205 |
| Endpoint-to-head center-distance range | 6–15.13px | 5–15.13px |
| Inherited maximum notehead anchor residual per axis | 0.5px | 0.5px |

The G union count is lower than the sum because four coordinates belong to both staff and barline components; these are not missing/duplicated collision pixels. Earlier 37 intentional tie/barline pixels remain unchanged and separate from the additional eight. Existing zero unexpected notation/text contacts, no clipping, old stem/beam/tie connectivity and original source registration are preserved by exact layer reuse and hash checks. This does not turn all actual alpha intersections into zero.

PNG dimensions remain 2520×3704, including the 140px developer-warning header. PDFs are one lossless RGB-image page each, at 300 export dpi, 604.8×888.96pt. Extracted PDF RGB hashes equal their PNG RGB bytes. Both PDFs were rendered through Poppler and inspected. The export uses the existing system pypdf child without modifying the calibrated font runtime.

## Actual visual review

Predictions were frozen before visual inspection. The delivered `final-v2/prediction-freeze.json` SHA-256 is `446b450bf5b2ab8e8db9f47254658d73a1de3cde09cab5e1b36d3f2aa7e23575`. Agent inspection covered both full-page PDF rasterizations and the source/frozen-G/revised-G curve detail comparison. The three ties and unequal-pitch slur are visible over the intended heads; no new lyric intersection or clipping is apparent. The close source-relative slur endpoint spacing and thin stair-stepped cubic edges remain research-quality limitations. The inherited 2px lyric clearances, heavy beam ends, omitted source metadata and large blank header region remain.

**Agent visual-quality verdict: NEEDS_REFINEMENT.** Semantic consistency passes; source recognition completeness remains UNVERIFIED; rendering is INCOMPLETE. The owner approval is real but scope-limited. It is not independent musician/optical validation, which remains zero. No preview is performance-ready.

## Validation and remaining review

Targeted V4 regressions and unchanged V3 music/gate/integrity checks: **592 passed, 1 skipped**. All 22 new synthetic controls pass. The only skip is the pre-existing MuseScore-not-installed integration test; no new skip or acceptance waiver. Full Acceptance was not run. The unchanged full V3 guard passes source roundtrip and both in-memory/serialized A/G transpositions at 37 measures / 169 events / 24 harmonies. Separate checks verify the four relationships because the V3 guard alone is not a full tie/slur classifier. Source/historical hashes and `git diff --check` pass.

There remain 28 unresolved source-object cases: 27 raw articulation observations and unclassified curve 4867. The ten previously withheld SIG objects are a subset of the 27 raw articulation observations and remain untouched. The object, event, syllable-onset and continuation review lists overlap and must not be added into one workload total. The full repeat playback route, 83 event cores, 79 exact lyric-onset associations and 20 continuation candidates still need their respective reviews. MusicXML lyric-extender serialization remains INCOMPLETE; visual dashes do not solve the existing export gap. No independent source-completeness denominator is asserted.

Next owner action: review those unresolved event/association/stroke cases with explicit corrections/exclusions. Chord wording/placements and approved lyric strings/row distinctions need no duplicate confirmation. Curve classification is approved and the specific endpoints are source-checked, but the new diagnostic stroke geometry still needs optical refinement and eventual musician review.

## Files and reproduction

Delivered artifact directory: `/private/tmp/capomatic-v4-gt17b-owner-output/final-v2/`.

- `A-full-score.png`, `G-full-score.png`, `A-full-score-experimental.pdf`, `G-full-score-experimental.pdf`.
- `Bb-A-G-full-score-comparison.png`, `curve-before-after-comparison.png`.
- `owner-interpretation-layer.json`, `source-correction-and-uncertainty.json`, `before-after-musical-correction-comparison.json`.
- `source-event-inventory.json`, `source-coverage-matrix.json`, `remaining-unresolved-items.json`.
- `owner-augmented-source.musicxml`, `A-transposed.musicxml`, `G-transposed.musicxml`.
- `semantic-integrity.json`, `rendering-validation.json`, `preservation-verification.json`, `visual-inspection-report.json`, `validation-summary.json`, `prediction-freeze.json`.

```bash
cd /Users/juahnkim/transchord/.gt17b-owner
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt17b_owner_integration --output /private/tmp/FRESH-GT17B-OWNER-OUTPUT
/private/tmp/capomatic-v4-venv/bin/python -m pytest tests/test_v4_ground_truth_*.py tests/test_v4_paired_ground_truth_01.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py tests/test_omr_v4_integrity.py -q -ra
git diff --check
```

The output directory must not exist. The source directory is `/private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output/predictions/baseline-exec/source/`; historical directories are `/private/tmp/capomatic-v4-gt16b/gt16b-final-output`, `/private/tmp/capomatic-v4-gt16c/gt16c-final-output`, `/private/tmp/capomatic-v4-gt17/gt17-final-output` and the GT-17B baseline above. The script checks every required binding before semantic changes or target generation. PDF export requires `/opt/anaconda3/bin/python` with its existing pypdf and calibrated music rendering requires the venv in the command. Frozen external source/history directories and installed font/PDF runtimes are required; this is not a portable standalone archive. Copyrighted pages, PNGs, PDFs, MusicXML and generated diagnostic JSON stay untracked outside the worktree. Only research code, tests, approval text and documentation are committed. No original source editing, ink removal, lyric-pixel composition, protection change, production/runtime/API/frontend modification, merge or deployment occurred.
