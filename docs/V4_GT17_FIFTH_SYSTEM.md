# GT-17 — fifth-system source audit and provisional rendering

The original Bb fifth system is **printed measures 17–19**, not 17–20. Both experimental targets display all **9 recognized note/rest cores** (6 notes, 3 rests). None is newly owner-verified. Combined previews contain the frozen **77 confirmed + 9 provisional** event cores. This is an incomplete research expansion, not a complete score or an accuracy measurement.

## Revision and evidence boundary

Base: `4da717a8e8675db84ea6a6b941bec3d4dacc86a5`, branch `experiment/v4-gt17-fifth-system`, worktree `/private/tmp/capomatic-v4-gt17`. The commit containing this report is the GT-17 implementation revision. [Protocol](V4_GT17_PROTOCOL.json) records the user's approval context verbatim as **OWNER_APPROVED_EXPERIMENTAL_LAYOUT** only. It does not approve fifth-system content, production use, automatic layout adaptation or independent musician validation.

Original source artifacts are read-only under `/private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output/predictions/baseline-exec/source/`:

| Artifact | SHA-256 |
|---|---|
| source.png, RGB 2520×3564 | `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de` |
| recognized.omr | `857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638` |
| visual-graph.json | `f8725c39beaaecc877ccf48b803b79a419c2d6e60aa73bc9428a39de11596508` |

GT-16B's owner-augmented source MusicXML supplies existing semantics; no new recognition, OCR or Audiveris execution occurred. No A/G reference pages were read for this experiment. The 169 whole-score semantic events are an internal guard denominator, **not** independently verified musical accuracy.

## Source registration and inventory

Staff `sheet#1:5`, system `sheet#1:system:5`, interline18px. Original staff polylines are retained; line ordinates are 1845.5, 1863.5, 1881.5, 1899.5 and 1917.5. Logical boundaries are x159/1361/1851/2400, widths1202/490/549px. Persisted right barline objects88/90/92 and staffbarlines4598/4599/4600 support those boundaries. Source measure/rest geometry and semantic duration are retained separately; m19's duration comes from its explicit MusicXML whole-measure rest in 4/4, not an invented missing OMR stack duration.

| Printed measure | Onsets and written source events (quarterLength durations) |
|---|---|
| 17 | 0 quarter rest(1); 1 eighth rest(1/2); 3/2 D4(1/2); 2 D4(1/2); 5/2 F4(1/2); 3 F4(1/2); 7/2 G4(1/2) |
| 18 | 0 G4 whole note(4), tie STOP |
| 19 | 0 whole-measure rest(4) |

Full stable IDs, original bboxes, voice, source centers, stem IDs, beam records, raw XML and relations are in `source-fifth-system-inventory.json`. Observations retain their OMR origin; render evidence is OMR_PROVISIONAL, source verification UNVERIFIED. Voice1 is the matched exported stream, not an independent absence-of-other-voices assertion.

New source text candidates, withheld from lyric rendering:

- m17 `Bb/D`, persisted as ordinary word4270 in sentence4268 with numeral `2.`/word4269; it is **absent from exported harmony semantics**. Do not insert it into source MusicXML or silently render it.
- m18 `Eb`, chord-name4267, is exported and is rendered provisionally as A-target `D`, G-target `C`. There is no owner approval of this chord yet.
- m19: no newly printed chord candidate observed; owner confirmation remains pending.
- Upper row m17: **이 / 루 / 시 / 네** at candidate onsets3/2,2,5/2,7/2. Only 이4274 and 시4275 are recognized lyric-items. 루4272 is ordinary TEXT; 네 lacks an exported lyric-item. Those losses are not repaired.
- Two visible upper-row continuation candidates: object5999 near x1069–1107/y1968–1974, associated with tied 시 at m17 onset3; object6001 near x1383–1420/y1968–1974, associated with 네 at m18 onset0. Their historical OMR shape remains TENUTO. Both source identity and stroke interpretation are retained; neither is rendered or promoted to verified.
- No lower lyric row was observed in this fifth-system crop. No syllables or strokes are mirrored from the upper row. The Chorus label below belongs to system6 and is outside the fifth-system rendering scope.

The owner packet includes original-resolution system/measure/stroke crops, a first/second-ending transition crop, individual event/text/association/beam/flag/tie/ending response fields and uncertain/missing-symbol fields. **All owner answers are empty.** It includes source observations, never the generated A/G images. It is owner review preparation, not an independent blinded protocol. The packet is `gt17-final-output/owner-review-checklist.json` with its native review sheet in the same directory. The owner may answer in chat by printed measure/onset or object ID with CONFIRM, CORRECT (including the correction), or UNCERTAIN; editing JSON is unnecessary. Preserve the eventual actual reply against this packet hash in a separately authorized continuation. Do not populate answers or run GT-17B now.

## Beam, flag, ties and second ending

Single beam1281 links four up-stems (3234/3236/3237/3235); isolated FLAG_1 object5997 links stem3238. No mixed or double beam is newly introduced. The old single-beam algorithm is reused; GT-16C supersampling is retained only inside its frozen earlier-system layer.

Tie4759 connects heads2088→2090 (F4→F4); tie4762 connects2086→2109 (G4→G4), across the m17/m18 barline in the same system. Both persisted curves have `tie="true"` and explicit LEFT/RIGHT slur-head relations. A targets are E4→E4 and F#4→F#4; G targets D4→D4 and E4→E4. These remain OMR-supported candidates. Curve attachment residuals are at most0.5px per axis; no endpoint is invented.

Ending5195 is an open-right bracket, left x276.4, right x1358, near y1760, spanning m17. Word4269 supplies the visible `2.`. OMR ending-bar links reach4597/4598 but there is no ending-sentence link. The neighboring `Bb/D` ordinary word must not be mistaken for an ending label. Existing MusicXML has first ending15–16 and second ending17. Source-visible notation and serialized spans agree on this local association; the full repeat playback route remains **UNRESOLVED**, with no jump inferred or added. Thin right barlines in17–19 do not introduce a backward repeat.

## Rendering and preservation contract

The standalone page canvas is explicitly2520×2110. Fifth viewport `[130,1740,2430,2050]`; integrated viewport `[130,310,2430,2050]`. PNG warnings occupy an extra130px outside page coordinates. Source review crops remain unscaled original RGB pixels; their private map records hashes and page translation.

GT-16C's frozen A/G refined alpha layers (2520×1800) are pasted unchanged into the larger generated canvas. Existing **77 events,10 chords,84 syllables,28 continuation marks**, including cross-system ties, are retained without rerendering. All previous nonzero ink values remain exact; new fifth ink is disjoint. New bracket/chord context enters a previously blank part of the former four-system viewport, so the integrated image is not asserted byte-identical over that old blank footer. Frozen historical PNGs and masks themselves are unchanged.

Reusable research changes are narrowly scoped:

- Extract GT-16's existing physical/semantic event registration into `measure_inventory`; its historical default inventory is unchanged.
- Expose the existing calibrated whole-note glyph independently of the old A3/G3 cross-system endpoint wrapper. The wrapper still rejects other endpoint pitches. The new scope needs F#4/E4 whole glyphs with the same font, scale, raster convention, transparent-center check and0.5px criterion.
- Reuse GT-14A's whole-rest component only when the source shape is WHOLE_REST and MusicXML explicitly identifies a full-measure rest. Its staff-hanging semantic anchor is distinguished from a notehead bbox center.
- Reject event-count mismatch before any paired iteration; no silent zip truncation.

No pitch calculation, sounding octave, original note x, staff registration, admission rule or production module changes. No automatic fifth-system lyric redistribution is applied.

## Measured results and actual visual inspection

| Result | A | G |
|---|---:|---:|
| New recognized/displayed event cores | 9/9 | 9/9 |
| Newly owner-confirmed events | 0 | 0 |
| Maximum notehead raster residual per axis | 0.5px | 0.5px |
| Unexpected component alpha contacts | 0 | 0 |
| Missing stem/head/beam/flag contacts | 0 | 0 |
| Music/context contacts | 0 | 0 |
| Old/new layer contacts | 0 | 0 |
| Minimum old/new ink-center distance | 31px | 22px |
| Viewport/canvas clipping | 0 | 0 |
| New lyrics/extenders rendered | 0/0 | 0/0 |
| New lyric/music safety | NOT EVALUABLE | NOT EVALUABLE |

Expected head/stem, stem/flag and stem/beam intersections are explicitly classified; staff intersections are intentional scaffold content, not erased source ownership. Zero unexpected contacts is not a claim of no staff/music overlap.

The67-file prediction manifest was hash-verified **before** agent inspection. Actual A/G fifth-system comparison and both integrated PNGs were opened after freezing. Music cores, whole-note holes, hanging whole rest, single flag, connected beam and separate local ties are legible at the displayed scale. The sparse blue fifth system clearly distinguishes provisional content. The ties remain thinner and more visibly raster-stepped than professional engraving; whole-note/font optical balance remains inherited research quality. There is deliberate blank lyric space and a missing m17 chord, so this is visibly and semantically incomplete. No new target tuning followed this inspection. This is **agent visual review**, not independent optical or musician validation.

Separate verdicts:

| Axis | Verdict |
|---|---|
| Source recognition completeness | UNVERIFIED; missing semantic lyric/chord assignments and ambiguous objects |
| Rendering completeness | 9/9 recognized event cores; INCOMPLETE required text/uncertain attachments withheld |
| Semantic consistency | Unchanged full V3 source roundtrip, in-memory and serialized A/G guards PASS |
| Visual quality | ACCEPTABLE_FOR_PROVISIONAL_DIAGNOSIS; thin curves and incomplete text remain limitations |
| Independent validation | 0 genuine independent labels/reviews |

## Files and validation

Actual untracked output directory: `/private/tmp/capomatic-v4-gt17/gt17-final-output/`.

- `A-fifth-system-provisional.png`, `G-fifth-system-provisional.png`
- `A-five-systems.png`, `G-five-systems.png`
- `Bb-A-G-fifth-system-comparison.png`
- `source-fifth-system-review-sheet.png`, `source-m17.png` through `source-m19.png`, `source-ending-transition.png`, individual stroke crops
- `source-fifth-system-inventory.json`, `owner-review-checklist.json`, `source-crop-map.json`
- `source-inventory-freeze.json`, `prediction-freeze.json`, `rendering-validation.json`, `semantic-integrity.json`, `preservation-verification.json`, `visual-inspection-report.json`, `validation-summary.json`

The frozen `validation-summary.json` intentionally retains its pre-inspection PENDING state; `post-inspection-validation.json` and `visual-inspection-report.json` are the later agent verdict, bound to the unchanged prediction freeze. [Validation metadata](V4_GT17_VALIDATION.json) records environment versions, artifact hashes and the test result.

Run from this worktree with the preserved external artifact paths:

```bash
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt17_fifth_system --output /private/tmp/capomatic-v4-gt17/NEW-EMPTY-GT17-OUTPUT
/private/tmp/capomatic-v4-venv/bin/python -m pytest tests/test_v4_ground_truth_*.py tests/test_v4_paired_ground_truth_01.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py tests/test_omr_v4_integrity.py -q
git diff --check
```

Targeted regressions: **545 passed,1 skipped** (the existing external MuseScore dependency). Includes22 new synthetic tests: integer/fractional whole-note placement, holes, deterministic raster bytes, unchanged restricted wrapper, whole-rest lineage rejection, missing events, viewport clipping, open-ending identity and no mirrored lyrics. Full unchanged V3 guards report37 measures/169 events/15 harmonies preserved for each target; these are semantic-consistency checks only. GT-16B and GT-16C document bindings, complete freeze manifests and before/after directory hashes pass. Source hashes pass before and after. Full Acceptance was not run.

## Next authorized boundary

Owner review is needed for all9 events,2 ties,flag/beam identity,`Bb/D`/`Eb` and m19 absence,4 syllables and exact associations,2 stroke/TENUTO interpretations,lower-row absence and local second-ending context. Ten earlier SIG objects5833/5841/5896/5902/5903/5927/5948/5949/5975/5984 remain withheld without reclassification. Full repeat playback and MusicXML lyric-extender serialization remain unresolved. GT-17B is not authorized.

No original PDF/raster edits, ink removal, source-pixel composition, mask changes, ownership promotion, V1/V3 production/API/frontend changes, merge or deployment occurred. Copyrighted score images remain untracked. The available outputs depend on preserved local external inputs/fonts; this report does not assert a self-contained archival package.
