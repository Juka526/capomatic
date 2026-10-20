# GT-16B — owner-confirmed fourth-system standalone rendering

Base: `83863d4366290bd3e804a90483721dba09b556ce`. Branch: `experiment/v4-gt16b-confirmed-fourth-system`. Worktree: `/private/tmp/capomatic-v4-gt16b`.

Understood as: promote only the owner's explicitly approved GT-16 source candidates in a new interpretation layer, then add their chords, newly typeset Korean lyrics and continuation marks over immutable historical music masks. This grants no original-ink removal, composition or production authorization.

## Separate results

| Dimension | Result |
|---|---|
| Source verification | OWNER_VERIFIED_SOURCE for the approved 18 events, five ties, four chord/absence decisions, 14 lyric associations, seven marks and first ending over m15–16 |
| Source recognition completeness | Still unresolved: five new and five earlier SIG objects remain withheld; no independent whole-measure absence/completeness attestation |
| Semantic consistency | Unchanged full V3 source roundtrip, A/G in-memory and serialized guards PASS |
| Rendering completeness | All approved fourth-system content displayed; no withheld articulation glyphs; not a completed full score |
| Visual quality | NEEDS_REFINEMENT, based on agent inspection of actual PNGs; not independent optical validation |
| Overall | DEVELOPER-ONLY / INCOMPLETE / NOT FOR PERFORMANCE OR PRINTING |

The integrated scope now displays **77 confirmed note/rest events, 10 chords, 84 Korean syllables and 28 continuation marks**. This is 59/7/70/21 preserved from GT-15B plus 18/3/14/7 in the fourth system. The full semantic artifact still has 37 measures and 169 events, with 15 harmonies after adding two owner-confirmed source chords. Those whole-score counts are not the displayed or independently verified denominator.

## Approval and immutable source

The exact current owner instruction is retained in [GT16B_OWNER_APPROVAL.txt](evidence/GT16B_OWNER_APPROVAL.txt), together with the preceding assistant review message in [GT16B_PRECEDING_REVIEW_MESSAGE.txt](evidence/GT16B_PRECEDING_REVIEW_MESSAGE.txt). [GT16B_OWNER_BINDING.json](evidence/GT16B_OWNER_BINDING.json) binds both to the frozen GT-16 checklist, source inventory, review sheet, packet freeze and preceding technical report. No signature, reviewer identity or approval timestamp was invented.

The owner approved the preceding source candidates explicitly. The separate `owner-interpretation-layer.json` retains raw candidate observations and adds scoped interpretation statuses. Historical candidate answers remain blank and unchanged. All files listed by the GT-16 source-only packet freeze and historical prediction freezes are hash-checked before use and preserved after execution.

Source: original Bb PDF page 2, raster 2520×3564 RGB. Original raster SHA-256 `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`; OMR `857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638`; graph `f8725c39beaaecc877ccf48b803b79a419c2d6e60aa73bc9428a39de11596508`. No PDF rerasterization, Audiveris rerun, OCR, target-reference page access or model download occurred.

## Confirmed fourth-system content

The GT-16 source inventory retains the 18 event IDs, pitches, onsets, durations, voices, notehead coordinates, typed relations and raw SIG objects. All five source ties are approved and reused without curve changes. Three beam groups, two flags and the half/whole-note and rest glyphs remain unchanged.

| Measure | Confirmed source chord | A / G chord | Upper lyric syllables @ onset | Lower lyric syllables @ onset |
|---|---|---|---|---|
| 13 | No new chord | None | 주@2.5 / 의@3 / 말@3.5 | 주@2.5 / 님@3 / 의@3.5 |
| 14 | Gm7 | F#m7 / Em7 | 씀@0.5 / 은@1.5 | 말@0.5 / 씀@1.5 |
| 15 | Bb/D | A/C# / G/B | 영@1.5 / 원@2 / 하@2.5 / 네@3.5 | No new syllable |
| 16 | Eb | D / C | No new syllable | No new syllable |

The three A-target chords are `F#m7`, `A/C#`, `D`; the three G-target chords are `Em7`, `G/B`, `C`. The slash inside `A/C#` or `G/B` denotes the confirmed inversion, not a separator between chords.

Seven individually approved source continuation strokes are added, once each:

- m14 upper onset 0 holds m13 말; onset 1 holds 씀; onset 2 holds 은.
- m14 lower onset 0 holds m13 의; onset 2 holds 씀. No lower onset-1 mark is invented.
- m15 upper onset 3 holds 하.
- m16 upper onset 0 holds m15 네.

Each continuation records its original source window, diagnostic dark-support bbox, lyric row, held syllable, note context and final placement. Each has a tied-stop context; no extra syllable token is added. The continuation bboxes are display-placement evidence, not pixel-ownership masks.

First-ending geometry/numeral over m15–16 is preserved. The overall repeat playback route is explicitly withheld. The old ending-sentence linkage discrepancy remains documented in the raw inventory; this experiment does not repair that graph or add a repeat jump/backward-repeat glyph at m16.

New SIG IDs **5927, 5948, 5949, 5975, 5984** and earlier IDs **5833, 5841, 5896, 5902, 5903** remain unclassified. They are neither rendered as articulations nor silently reclassified as lyric strokes.

## Reused rendering and fixed layout rules

[The preregistered protocol](V4_GT16B_PROTOCOL.json) precedes target generation. The research helper loads all GT-16 head/stem/rest/ledger/beam/flag/tie component PNGs plus scaffold, clef/key and ending masks; it does not rerender their geometry. The reconstructed union plus frozen m14 chord must equal the historical fourth alpha byte-for-byte. The existing m14 chord bitmap is also reproduced exactly by the existing GT-12 text contract. Only the two missing confirmed chords, 14 new lyric glyphs and seven new continuation strokes add ink.

Fonts remain the GT-15B hash-bound FreeSerif size40 for chords and AppleGothic size44 for Korean. Chord text preserves the source symbol left/top, root/quality/seventh and slash-bass semantics. No chord is attached geometrically to the first pitched note. New source MusicXML uses the existing research convention of chord measure-onset0 and adds only m15 Bb/D and m16 Eb; existing m14 Gm7 remains intact.

Lyrics reuse GT-12 `text_mask`, GT-14B 2px extenders and GT-15B `layout_text`. Their horizontal anchors are the approved original source-head centers. Both lyric rows and all seven marks translate together by the minimum feasible nonnegative integer dy in the exhaustive GT-13A5 domain, with one-pixel Chebyshev exclusion and minimum ink-center distance 2px. No x shift, font shrink, row-spacing change, altered musical pitch or collision-threshold change is allowed.

The native canvas remains 2520×1800. The fourth display crop extends to y1800, 60px below the earlier GT-16 preview crop, to declare the full finite layout domain before rendering; the next source staff begins at y1845.5. Existing staff/measure/note geometry stays in the same page coordinates. The original comparison includes adjacent m17 header context at the bottom; no m17 target notes are inferred or displayed.

## Measured validation

All contacts use actual **nonzero-alpha** pixel intersections, not bounding-box overlap.

| Measurement | A major | G major |
|---|---:|---:|
| Newly displayed approved note/rest events | 18/18 | 18/18 |
| Reused ties / beams / flags | 5 / 3 / 2 | 5 / 3 / 2 |
| New syllables / continuation marks | 14 / 7 | 14 / 7 |
| Minimum feasible lyric dy | 4px | 13px |
| Upper/lower baseline, before → after | 1673/1718 → 1677/1722 | 1673/1718 → 1686/1731 |
| New lyric/fixed-ink contact pixels | 0 | 0 |
| Lyric/lyric and lyric/extender contact pairs | 0 | 0 |
| Minimum lyric/fixed-ink center distance | 2px | 2px |
| Unit-square edge-distance conservative lower bound | 0.586px | 0.586px |
| New chord/notation contacts; chord/chord pairs | 0; 0 | 0; 0 |
| Minimum chord/notation ink-center distance | 10px | 10px |
| Old/new-system contact pixels | 0 | 0 |
| Clipped new components / lost translated glyph pixels | 0 / 0 | 0 / 0 |
| Maximum actual head raster-bbox anchor residual per axis | 0.5px | 0.5px |
| Preserved attachment checks / missing connections | 25 / 0 | 25 / 0 |

Anchor residuals compare actual pixel-center bbox coordinates `(left+right−1)/2,(top+bottom−1)/2` with requested source-head x and transposed semantic staff y on the original staff polyline. Physical source centers, semantic staff coordinates and actual glyph anchors remain distinct. The 25 music-attachment checks are 13 head/stem, 10 beam/stem and two flag/stem connections; they do not count lyric associations. The 14 lyric associations are checked by exact approved event onset, and all seven marks separately require a tied-stop source event and a preceding approved syllable in the same row. Staff, measure and all existing notation masks are reused, not shifted. The old first-three-system alpha and common RGB body equal GT-15B byte-for-byte.

## Semantic and regression checks

Executed unchanged V3 source-roundtrip and target in-memory/serialized guards: all PASS, 37 measures / 169 events / 15 harmonies in both compared semantic representations. Full event/pitch/rhythm/voice/tie signatures match GT-16 frozen targets, and explicit repeat bars/ending spans match across source, memory, serialization and old targets. Previously confirmed source lyrics and chord lists for m1–12 remain identical.

The newly augmented source replaces only m13–16 sparse/merged OMR lyric observations with the 14 approved associations. Source and target lyric signatures match. MusicXML contains all 14 new `<lyric>` elements but **zero `<extend>` elements** in this scope: seven visual continuation masks are separately represented in JSON/PNG. The production exporter is unchanged; this serialization gap remains a blocker to claiming complete MusicXML lyric continuation support.

Targeted command:

```sh
/private/tmp/capomatic-v4-venv/bin/python -m pytest tests/test_v4_ground_truth_*.py tests/test_v4_paired_ground_truth_01.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py tests/test_omr_v4_integrity.py -q
```

**501 passed, 1 skipped**. The existing external MuseScore integration test is skipped. Full Acceptance was not run, as the research authorization excludes it; the existing targeted guards and regression checks do not substitute for production acceptance. Nine new tests cover separate interpretation, unchanged candidates, withholding, unexpected scope changes, event/lyric/harmony preservation, no lyric insertion on blank rows, duplicate harmony rejection, exact-onset association and changed approval provenance. An initial test incorrectly included harmony objects via music21 `.notes`; it now uses the existing `events_of` helper, without changing any guard. An early output writer rejected `/` in a rational-onset filename; filenames now use a safe hyphen. Those development outputs are retained separately and are not the final freeze.

## Actual visual inspection and limits

Final predictions were hash-frozen before inspection. The agent opened A/G fourth-system crops, both four-system images and the original/A/G comparison. All approved text is visible, and no withheld object is added. Nevertheless, the G low D3 and upper 주 remain optically cramped despite the 2px numerical clearance; the analogous A region is also tight. Inherited diagonal beam stair-steps, thin ties and earlier-system lyric crowding remain. These observations yield **NEEDS_REFINEMENT**, not professional engraving approval. No post-inspection geometric retuning occurred.

Owner confirmation is not independent ground truth. The renderer and geometry checker share the same intended coordinates, so their agreement proves implementation consistency, not independent pitch-reading or optical correctness. Agent inspection does not supply an independent musical denominator. Independently collected human musical/optical labels remain zero. The next experiment should separately preregister optical-clearance and beam-quality refinement, preserving this freeze, while maintaining the five new and five earlier SIG exclusions and withheld playback route.

## Artifacts and preservation

Untracked actual images and JSON live in `/private/tmp/capomatic-v4-gt16b/gt16b-final-output/`:

- `A-four-systems.png`, `G-four-systems.png`, `Bb-A-G-comparison.png`
- `A-fourth-system.png`, `G-fourth-system.png`, `original-bb.png`
- `owner-interpretation-layer.json`, `pre-render-freeze.json`, `prediction-freeze.json`
- `rendering-validation.json`, `semantic-integrity.json`, `preservation-verification.json`
- `visual-inspection-report.json`, `validation-summary.json`

[Validation metadata](V4_GT16B_VALIDATION.json) binds the artifact hashes. Reproduction requires the preserved absolute-path evidence directories and installed pinned fonts; this is not a self-contained portable package:

```sh
cd /private/tmp/capomatic-v4-gt16b
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt16b_confirmed_fourth_system --out /private/tmp/capomatic-v4-gt16b/NEW-UNUSED-OUTPUT
```

All GT-16 and GT-15B input-directory hashes are unchanged. No original PDF/raster edit, old ink removal, lyric-pixel compositing, protection-mask change, Track A ownership promotion, V1/V3 production modification, API/frontend route, merge or deployment occurred. Copyrighted raster/MusicXML and large diagnostic outputs remain untracked.
