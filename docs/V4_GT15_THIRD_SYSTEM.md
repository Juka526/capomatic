# GT-15: third-system source audit and provisional expansion

The new preview displays 20/20 frozen OMR note/rest event cores in printed measures 9–12. It adds no owner-confirmed source information. Together with the unchanged GT-14E first two systems, the diagnostic canvases display 59 event cores: 39 previously owner-confirmed and 20 `OMR_PROVISIONAL`. This is an incomplete music-layer prototype, not a finished score.

Base: `13b2313cf79bee39508a5f12994be6b5a8c378f3`.
Branch: `experiment/v4-gt15-third-system`.
Worktree: `/private/tmp/capomatic-v4-gt15`.
The commit containing this report identifies the final research code revision; `docs/V4_GT15_VALIDATION.json` binds the local output hashes.

## Source and registration

Only the original Bb page-2 raster and its persisted OMR/source evidence informed the new content. No A/G reference raster or reference recognition was opened. Legacy GT-02 registration metadata includes cross-page coordinate fields; they were ignored. This is post-reference-access development research, not a blinded experiment.

| Input | SHA-256 |
|---|---|
| Original 2520×3564 RGB source PNG | `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de` |
| Recognized OMR | `857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638` |
| Visual graph | `f8725c39beaaecc877ccf48b803b79a419c2d6e60aa73bc9428a39de11596508` |

The third staff is `sheet#1:3`, system `sheet#1:system:3`, with 18px spacing. Its five original polylines run from x159 to x2399 at y1145.5, 1163.5, 1181.5, 1199.5 and 1217.5. The visible printed 9 and four bar regions support measures 9–12. The source graph boundaries are x159/807/1338/1869/2400; widths are 648/531/531/531px. Earlier raster registration candidates differ by at most 1px and remain an uncertainty, not independent boundary truth. The outer barline `sheet#1:58` has bbox [2398,1144,2402,1219]; this explicit geometry supports x2400 beyond the polyline endpoint. No source raster is rescaled or altered.

## Frozen source inventory

Full IDs, geometry, relations, physical head centers, semantic coordinates and raw OMR lyric observations are in the untracked `source-event-inventory.json`. Each measure contains five recognized events totaling four quarter lengths in the persisted single voice.

| Measure | OMR notes/rests, as onset:pitch-or-rest/duration in quarter lengths |
|---|---|
| 9 | 0:rest/2; 2:rest/½; 2½:F3/½; 3:F4/½; 3½:F4/½ |
| 10 | 0:F4/½; ½:F4/½; 1:F4/½; 1½:F4/½; 2:F4/2 |
| 11 | 0:rest/2; 2:rest/½; 2½:F3/½; 3:F4/½; 3½:F4/½ |
| 12 | 0:F4/½; ½:F4/½; 1:F4/½; 1½:G4/½; 2:G4/2 |

There are 16 notes and four rests. Four single-level beams (1250/1252/1254/1248), two flags (5775/5849), and six local or adjacent-measure ties (4768/4780/4782/4770/4786/4804) have explicit persisted support. None is newly owner-verified. Target pitches are F3→E3/D3, F4→E4/D4, G4→F#4/E4 for A/G respectively. Target key context supplies F# in A; no explicit accidental is silently added or omitted from this recognized stream.

The source second-ending object 5193 spans m9 with an open right side. Sentence 4186 and child words support the numeral 2. The existing m8 first ending/backward repeat and m1 forward repeat remain unchanged. A first-pass return followed by skipping m8 toward m9 on the second pass is an OMR/source-supported structural interpretation only; playback expansion and complete repeat semantics are not newly owner-confirmed. No m8→m9 tie is invented.

## Missing and uncertain context

Two visible source chord candidates, m10 `Eb` and m12 `F`, are absent from recognized harmonies. They are not rendered. No newly printed chord was observed in m9/m11; carried harmony is not invented.

| Measure | Upper lyric candidates | Lower lyric candidates |
|---|---|---|
| 9 | 풀 / 은 / 마 | 전 / 능 / 하 |
| 10 | 르 / 고 | 신 / 주 |
| 11 | 꽃 / 을 / 시 | 거 / 룩 / 하 |
| 12 | 드 / 나 | 신 / 왕 |

These 20 syllables span both lyric rows (10 upper and 10 lower); the 11 continuation strokes are additional marks, not syllables. The syllables, their associations and individually inspected continuation strokes are `AGENT_VISUAL_CANDIDATE`. No new text or continuation stroke is rendered. The upper m10 onset-1 region has no observed dash; a lower-row mark was not copied upward. Sparse OMR lyric observations are retained verbatim, including merged `드신` and `나왕`, rather than silently repaired.

Five raw SIG objects remain unresolved: TENUTO 5833/5841/5902/5903 and ACCENT 5896. Their original IDs, bboxes and source context remain available. They are neither rendered as musical articulations nor discarded as lyric strokes. The native review packet requests their interpretation separately.

The source-only `owner-review/` packet contains native crops, crop-coordinate mappings, inventory and null-response checklists. It includes the m8/m9 ending transition and individual disputed-object crops. It contains no target prediction images; its checklist deliberately contains labeled OMR observations and agent transcription candidates for an owner review, not a blinded independent-reader task. All answer fields remain null. Actual new owner confirmations and independent human labels: **0**. Agent reading and OMR agreement do not establish source completeness.

## Rendering and validation

The preregistered `V4_GT15_PROTOCOL.json` precedes prediction generation. New helpers reuse GT-05 fixed-phase FreeSerif placement, GT-07 flag attachment, GT-14 tie curves and existing scaffolding/header components. The only new primitives are hollow half-note heads, half rests and explicitly supported 2/4-stem single eighth beams. Font identity remains hash-bound to the historical font. Transparent head centers remain transparent after stem attachment. Beam slope/thickness use source evidence; stems are re-anchored to target pitches.

A first attempt stopped before predictions on a renderer call-signature error; a second stopped before predictions because the scaffold required the persisted outer-barline geometry. Both were corrected before any preview. The failed output directories are retained separately. Neither caused threshold changes or score-specific optical offsets.

| Measurement, per target | A | G |
|---|---:|---:|
| Recognized/displayed event cores | 20/20 | 20/20 |
| New owner-verified events | 0 | 0 |
| Beams / flags / ties displayed | 4 / 2 / 6 | 4 / 2 / 6 |
| Attachment checks / missing connections | 30 / 0 | 30 / 0 |
| Maximum head anchor residual per axis | 0.5px | 0.5px |
| Unexpected core-symbol alpha contacts | 0 | 0 |
| Header/ending actual alpha contacts | 0 | 0 |
| Clipping / new-old system ink overlap | 0 / 0 | 0 / 0 |
| New lyric/music collision validation | NOT EVALUABLE | NOT EVALUABLE |

The 30 attachment checks comprise 16 head/stem contacts, 12 beam/stem contacts and two flag/stem contacts; no connection is missing among those specified checks. The six ties are six note-to-note curve components, with source endpoint identities and geometric endpoint residuals checked separately. They are not included in the 30 contact checks.

All nonzero-alpha pixels count. Intended staff crossings and explicit head/stem/ledger, beam/stem and stem/flag connections are accounted for separately. These results do not prove safe composition with omitted lyrics. Source musical ink ownership/removal remains unauthorized.

Tests: **462 passed, 1 skipped**, including 25 new synthetic/renderer tests, GT-01–14 regressions and relevant V3/V4 guards. The skip is the existing external MuseScore-dependent test. Command:

```sh
/private/tmp/capomatic-v4-venv/bin/python -m pytest \
  tests/test_v4_ground_truth_*.py tests/test_v4_paired_ground_truth_01.py \
  tests/test_omr_v3_music.py tests/test_omr_v3_gate.py tests/test_omr_v4_integrity.py -q
```

Unchanged full V3 guards pass for the source roundtrip, both in-memory transpositions, both serialized new targets and frozen A/G targets. Each checks 37 measures, 169 events and 11 total harmonies in the current input, which includes prior owner-confirmed additions. This report does not claim all 11 were recognized in the original OMR. This whole-artifact count is not a third-system recognition denominator. Event/tie/lyric signatures also remain preserved. Full Acceptance was not run.

Historical source/OMR/graph, GT-12 evidence, GT-14A–E bindings and frozen outputs passed hash-preservation checks. Both first-two-system RGB body viewports are byte-identical to GT-14E, including 39 events, five chords, 50 syllables, ten continuation marks and the m4→m5 tie. No existing lyric baseline or music geometry was changed.

## Actual visual review and independent verdicts

The agent inspected both third-system PNGs, the original/A/G contact sheet and both three-system previews. Hollow heads, flags, beams and six ties are visibly present. A's third sharp is optically close to the second-ending numeral despite zero actual alpha contact. Sloped beams retain visible pixel stair-steps; G's low notes require a separate lyric-layout analysis once text is confirmed. Existing first-two-system optical crowding remains unchanged. No retuning followed this inspection.

- **SOURCE_RECOGNITION_COMPLETENESS:** UNVERIFIED for the new system.
- **RENDERING_COMPLETENESS:** 20/20 recognized event cores displayed; incomplete source context, text and disputed attachments withheld.
- **VISUAL_QUALITY:** readable provisional music-only preview with limitations, based on agent inspection only, not independent optical validation or professional engraving approval.

The overall result remains **THIRD_SYSTEM_PROVISIONAL_MUSIC_PREVIEW_WITH_SOURCE_REVIEW_PENDING**. It is not full-score completion and does not choose an architecture winner.

## Artifacts and next step

All large/copyrighted artifacts remain untracked under `/private/tmp/capomatic-v4-gt15/gt15-final-output/`:

- `source-third-system-review-sheet.png`, `source-third-system-native.png`, `source-ending-transition-review.png`
- `predicted-a-third-system.png`, `predicted-g-third-system.png`, `third-system-comparison.png`
- `A-three-systems.png`, `G-three-systems.png`
- `owner-review/owner-packet-freeze.json`, source-only review crops/checklists
- `source-event-inventory.json`, `rendering-validation.json`, `semantic-integrity.json`, `prediction-freeze.json`, `preservation-verification.json`, `visual-inspection-report.json`, `final-validation.json`

To reproduce in a **new empty directory**, from this worktree:

```sh
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt15_third_system --out /private/tmp/gt15-new-run
```

The helper deliberately requires preserved local historical inputs; it does not rerun OCR/Audiveris. Prediction freeze precedes agent inspection; post-inspection metadata is additional, not a rewritten prediction. The next required owner review is the fixed m9–12 event inventory, two chord candidates, both lyric rows and associations, 11 continuation marks, second-ending interpretation and five disputed objects. Subsequent rendering belongs to a separately authorized run.

No source PDF/raster editing, source-ink removal, original lyric-pixel compositing, protection-mask changes, ownership promotion, V1/V3 production changes, API/frontend routes, merge or deployment occurred.
