# GT-16: fourth-system provisional expansion

The new A/G previews display all **18 note/rest event cores in the current provisional recognition inventory** for printed measures **13–16**, plus one provisional recognized harmony. Source-event completeness remains unverified. Across four systems, 77 cores are visible: the unchanged **59 owner-confirmed events** and **18 new OMR_PROVISIONAL events**. No new owner confirmations were collected. This is an incomplete developer-only preview, not a performance score.

Base: `3762aaaaecdbcd42433556089489c674fe57cccb`.
Branch: `experiment/v4-gt16-fourth-system`.
Worktree: `/private/tmp/capomatic-v4-gt16`.
The commit containing this report identifies the final research revision; `V4_GT16_VALIDATION.json` binds the local artifact hashes.

## Source and registration

Only the original Bb page-2 raster, persisted OMR/visual graph and source-side Bb evidence were used. No A/G reference pages or reference recognition were accessed, and no OCR, Audiveris or PDF rasterization was run.

Original source PNG: 2520×3564 RGB, SHA-256 `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`. OMR: `857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638`. Visual graph: `f8725c39beaaecc877ccf48b803b79a419c2d6e60aa73bc9428a39de11596508`. Existing hash-bound artifacts supply the input; the original PDF is not opened or changed.

Staff `sheet#1:4`, system `sheet#1:system:4`, has 18px interline spacing. Its five polylines run x159–2399 at y1495.5/1513.5/1531.5/1549.5/1567.5. The visible printed 13 and four source bar regions identify measures 13–16. Source graph centerline boundaries used are **159 / 851 / 1427 / 2093 / 2400**, giving widths **692 / 576 / 666 / 307px**. These are source-derived logical registration coordinates, not independent human certification of exact raster edges. The final barline80 has bbox [2398,1494,2402,1569], supporting x2400 beyond the staff polyline endpoint.

Each event is matched by source-side printed measure, onset, duration and pitch to the persisted graph and existing Bb diagnostic rows. No nearest-note or exported-index-only fallback is used. Native review crops preserve original source pixel values and include the complete lyric rows. All new owner-answer fields remain empty.

## New source inventory and coverage

Full IDs, physical head centers, original bounding boxes, semantic observations and SIG (Audiveris symbol-relation graph) lineage are retained in `source-event-inventory.json`.

| Measure | Recognized events, onset:pitch/rest / duration in quarter lengths |
|---|---|
| 13 | 0:rest/2; 2:rest/½; 2½:F3/½; 3:F4/½; 3½:F4/½ |
| 14 | 0:F4/½; ½:F4/½; 1:F4/½; 1½:F4/½; 2:F4/2 |
| 15 | 0:rest/1; 1:rest/½; 1½:D4/½; 2:D4/½; 2½:C4/½; 3:C4/½; 3½:Bb3/½ |
| 16 | 0:Bb3/4 |

This is 14 notes and four rests in the single persisted voice, totaling four quarter lengths per measure. Five tie objects are retained: 4764, 4774, 4778, 4776 and 4766. They connect m13→14, two internal m14 pairs, an internal m15 pair, and m15→16. Three explicit beam groups and two single upward flags are supported. There is no new inferred cross-system tie or missing endpoint invented.

| New element category | Source evidence | Displayed | Newly owner-confirmed |
|---|---|---:|---:|
| Note/rest cores | 18 frozen OMR events | 18 | 0 |
| Beams / flags / ties | 3 / 2 / 5, explicit relations | 3 / 2 / 5 | 0 |
| Harmony | m14 Gm7 recognized in MusicXML and raw chord-name4230 | 1 provisional | 0 |
| Additional chords | m15 Bb/D and m16 Eb visible/raw-text candidates, absent as harmonies | 0 | 0 |
| Korean syllables | 14 agent visual/association candidates; OMR has only three sparse/mixed serialized lyric observations | 0 | 0 |
| Lyric continuation strokes | 7 individually inspected candidates | 0 | 0 |
| Raw TENUTO hypotheses | 5 ambiguous objects | 0 as articulations | 0 |
| Ending context | First-ending candidate over m15–16 | Provisional bracket/numeral | 0 |

The recognized Gm7 is transposed using unchanged V3 chord logic to **F#m7 (A)** and **Em7 (G)**, at its original source text placement. These are provisional predictions, not newly verified chords. The displayed chord total is seven prior owner-confirmed chords plus one provisional chord. Missing Bb/D and Eb are not supplied from references or inserted into the semantic source.

Source lyric/association candidates, not confirmed transcription:

| Measure | Upper candidate / onsets | Lower candidate / onsets |
|---|---|---|
| 13 | 주 / 의 / 말 at 2½ / 3 / 3½ | 주 / 님 / 의 at 2½ / 3 / 3½ |
| 14 | 씀 / 은 at ½ / 1½ | 말 / 씀 at ½ / 1½ |
| 15 | 영 / 원 / 하 / 네 at 1½ / 2 / 2½ / 3½ | No new visible syllables observed; not filled |
| 16 | No new syllable observed; continuation candidate | No new visible syllable or stroke observed; not filled |

Seven visible stroke windows are reviewed separately: m14 upper onsets0/1/2, lower0/2, m15 upper3 and m16 upper0. The m14 lower onset1 blank was not copied from the upper row. All original sparse/merged lyric items, including 의님/말의 and the raw quote/dot objects, remain recorded rather than silently repaired. Stroke dark-support bboxes are diagnostic display measurements, not pixel ownership.

Five new raw hypotheses remain unresolved: TENUTO5927, 5948, 5949, 5975 and 5984. They are not automatically accepted as articulations, lyric strokes or extenders. The earlier withheld IDs5833/5841/5896/5902/5903 remain explicitly withheld, with unchanged GT-15B interpretation and masks.

## Repeat and section evidence

Agent source-image inspection identifies `1.` above m15–16; geometry5203 has both legs. MusicXML retains RepeatBracket1 over15/16 and RepeatBracket2 over17. The raw ending-sentence relation, however, targets4236 containing Eb, while the leading `1.` is word4234 in Direction4233. This disagreement is preserved in the inventory. The source m16 right boundary is a plain barline; no new backward-repeat glyph or playback route is invented.

Only the source-supported bracket geometry and provisional `1.` are rendered. Their existence does not resolve the larger repeat playback interpretation. The old owner-confirmed m8/m9 relationship and m4→5 cross-system tie are preserved. No new section heading was observed in system4; the prior Pre-Chorus label is retained once, and the printed measure-number13 is newly shown as provisional context.

## Rendering reuse, preservation and tests

The research GT-15 renderer now accepts explicit canvas-size/viewport keyword arguments with unchanged historical defaults. It composes the already validated GT-13A.6 whole-head/ledger contract for A3/G3 and GT-04/13A.2 quarter-rest glyph with its existing half rest, half note, beam, flag and tie components. No new raster placement algorithm, font, music-ink ownership or production capability was introduced. Unsupported whole-note pitches remain rejected.

Before rendering system4, both A/G historical GT-15 runs were recomputed in new memory and all **50 component masks per target** matched their frozen counterparts byte-for-byte. No historical files were overwritten. The actual GT-15B three-system alpha layers are reused, preserving all 59 confirmed events, seven chords, 70 syllables, 21 marks, existing lyric baselines, headers and cross-system curves. The common RGB score-body viewport in each new four-system image is **byte-identical** to GT-15B; only the new diagnostic header and appended fourth-system content differ. No new system ink enters y<1408.

| Measurement | A | G |
|---|---:|---:|
| Recognized/displayed new event cores | 18/18 | 18/18 |
| Maximum head raster-anchor residual per axis | 0.5px | 0.5px |
| Actual head/stem, beam/stem, flag/stem checks | 25 | 25 |
| Missing connections | 0 | 0 |
| Unexpected core-symbol alpha contacts | 0 | 0 |
| New header/ending/context-to-core contact pairs | 0 | 0 |
| Provisional chord contacts | 0 | 0 |
| New/old-system alpha contacts | 0 | 0 |
| Minimum new-to-old-system ink-center clearance | 35px | 26px |
| All new component clipping | 0 | 0 |
| New lyric/music safety | NOT EVALUABLE | NOT EVALUABLE |

Raster residual compares the actual head-mask bbox pixel-center `(left+right-1)/2, (top+bottom-1)/2` with the requested anchor: original source head x plus target diatonic pitch y on the original staff polyline. The 25 attachment checks comprise 13 head/stem, ten beam/stem and two flag/stem positive alpha intersections. Whole notes have no stem check; the five ties use separate linked-endpoint geometry checks.

Every nonzero-alpha pixel counts. Established intentional head/stem/ledger and explicitly connected beam/stem or flag/stem contacts are separate from unexpected collisions. Tie endpoint identity and attachment geometry use the existing source relation contract. New lyrics are withheld, so their collision safety is not reported as zero or PASS.

Full unchanged V3 guards pass for the source roundtrip, both in-memory transpositions and both serialized targets: 37 measures, 169 events and 13 existing harmonies per comparison. The 77 displayed cores refer to the four-system preview; the 169 semantic events refer to the entire 37-measure input, including previously unrendered systems. All 18 new-system events already existed in that GT-15B semantic artifact. This iteration expands rendering coverage, not recognition or semantic content. These counts are not a musical-accuracy denominator. Full event/tie/voice and lyric signatures match GT-15B targets for that reason. Explicit repeat-bar and ending-span signatures also match source, memory, serialization and frozen targets; matching does not certify new playback interpretation.

Regression suite: **492 passed, 1 skipped**, including seven new synthetic controls. They test exact reuse of whole/quarter components, size/viewport invariance, clipping reporting, rejection of unsupported whole-note evidence/pitch, and negative controls for removal of a backward repeat and changing an ending number. The skip is the existing unavailable external MuseScore dependency. Full Acceptance was not run.

```sh
/private/tmp/capomatic-v4-venv/bin/python -m pytest \
  tests/test_v4_ground_truth_*.py tests/test_v4_paired_ground_truth_01.py \
  tests/test_omr_v3_music.py tests/test_omr_v3_gate.py tests/test_omr_v4_integrity.py -q
```

Source/OMR/graph/font bindings and complete GT-15/GT-15B output hashes are checked before and after generation. The final run adds an explicit repeat-signature guard to the initial run without changing rendering inputs or geometry. Both run directories remain separate. Predictions are frozen before agent visual inspection; later review/spacing metadata supplements the freeze. `git diff --check` passes.

## Separate verdicts and next review

- **SOURCE_RECOGNITION_COMPLETENESS:** UNVERIFIED for system4. There are 18 recognized event cores, zero new owner confirmations and no independent labels. Text omissions, ambiguous objects and repeat lineage remain unresolved.
- **RENDERING_COMPLETENESS:** all 18 recognized event cores, three beams, two flags, five ties and one recognized chord are displayed provisionally. Two chord candidates, 14 syllables, seven continuation marks and five new SIG classifications remain outside the new rendered scope. Prior confirmed coverage is unchanged.
- **SEMANTIC_CONSISTENCY:** full unchanged V3 and explicit signatures pass against the frozen source. These checks do not prove recognition accuracy or source completeness. The prior MusicXML lyric-extender serialization gap remains unchanged.
- **VISUAL_QUALITY:** the agent viewed actual A/G four-system PNGs, the G system4 image and the original/A/G comparison. Music glyphs, half/whole heads, beams, flags and tie arcs are visible and readable as a provisional music layer. Sloped beam raster stair-steps and earlier optical crowding remain unchanged. Omitted new text is explicit. This is agent inspection, not independent optical validation or professional engraving approval.

Overall: **FOUR_SYSTEM_PREVIEW_INCOMPLETE_PROVISIONAL_FOURTH_SYSTEM**. No architecture winner or performance-ready/full-score claim is made. The next required owner review covers the fixed 18 events/five ties, three chord candidates or absences, both lyric rows/associations, seven individual strokes, five new objects, and ending context. Previously confirmed content does not need duplicate approval. The prior five withheld objects remain withheld.

## Actual files and reproduction

Authoritative output: `/private/tmp/capomatic-v4-gt16/gt16-final-output/`.

- `A-four-systems.png`, `G-four-systems.png`
- `fourth-system-comparison.png`, `A-fourth-system.png`, `G-fourth-system.png`
- `source-fourth-system-review-sheet.png`, `source-measure-13.png` through16
- `source-event-inventory.json`, `owner-review-checklist.json`, `source-crop-map.json`
- Individual source stroke/ambiguous-object crops
- `rendering-validation.json`, `semantic-integrity.json`, `repeat-preservation.json`
- `historical-renderer-regression.json`, `preservation-verification.json`, `prediction-freeze.json`
- `post-render-measurements.json`, `visual-inspection-report.json`
- `owner-review/`: source-only copies, a native ending-transition context crop, blank checklist and packet freeze; no prediction images

The candidate packet is an owner review aid, not a blinded independent-reader packet. Source OMR observations and agent candidates are openly labeled. No owner answers or independent identities were manufactured. Neither this candidate packet nor the agent inspection establishes independent recognition accuracy. The helper requires preserved local prior artifacts and is not a standalone portable archive.

```sh
cd /private/tmp/capomatic-v4-gt16
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt16_fourth_system \
  --out /private/tmp/gt16-new-run
```

Use a fresh output directory. This generates new diagnostic files only and never executes OCR/Audiveris. All copyrighted source crops, score PNGs, masks and MusicXML remain untracked; only research code/tests/protocol/report/hash metadata are committed. No original ink removal, source-pixel composition, PDF/raster editing, protection-mask change, V1/V3 production changes, API/frontend changes, merge or deployment occurred.
