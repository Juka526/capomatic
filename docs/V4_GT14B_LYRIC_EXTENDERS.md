# GT-14B — Owner-confirmed lyric extenders

Source: original Bb PDF page 2, second system, printed measures 5–8. Targets: A major (−1 semitone) and G major (−3 semitones). The 13 events are the note/rest stream, separate from 3 chord symbols and 14 lyric syllables.

GT-14B adds three explicitly classified lyric continuation strokes to the frozen GT-14A standalone second-system canvases. It links the fourth object to the already rendered Korean syllable 하. No TENUTO or FERMATA symbol is added.

Understood as: preserve the original OMR observations and all existing rendering; add an owner-confirmed interpretation layer and only the three requested extender marks. This is not source-ink ownership or composition authorization.

Base: `e90499333b53846d039f34b6774536b9554f0a3e`. Branch: `experiment/v4-gt14b-lyric-extenders`. Worktree: `/private/tmp/capomatic-v4-gt14b`. The final revision is the commit containing this report, obtainable with `git rev-parse HEAD` on this branch.

## Evidence and provenance

The actual user approval is retained verbatim as UTF-8 with a terminal newline in [GT14B_OWNER_APPROVAL.txt](evidence/GT14B_OWNER_APPROVAL.txt). [GT14B_OWNER_BINDING.json](evidence/GT14B_OWNER_BINDING.json) binds it to the original source PNG, OMR, visual graph, GT-14A review sheet, four native crops, private case map, ambiguous-object records, inventory, metrics and prediction freeze. No reviewer identity, signature or timestamp was invented. Classification is **OWNER_VERIFIED_SOURCE / NOT_INDEPENDENT_GROUND_TRUTH**. Independent labels collected: **0**.

Source PNG SHA-256: `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`. Original OMR SHA-256: `857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638`. No reference A/G page was used.

All bboxes below use original page integer pixel edges, right/bottom exclusive. Row assignment is a source-only visual/geometric interpretation corroborated by the already confirmed syllable and tie context; it is not an independently annotated pixel extent.

| Object | Original persisted observation | Source bbox | Owner interpretation and context |
|---|---|---|---|
| sheet#1:5686 | TENUTO, glyph 5235; chord-articulation 4653→5686 | [298,987,335,993] | Lower row extender at m5 held Bb3, continuing m4 lower 는 across confirmed 4818/4798 tie |
| sheet#1:5699 | TENUTO, glyph 5407; chord-articulation 4650→5699 | [1330,942,1368,948] | Upper row extender at m6 onset 3 tied C4 STOP, holding 원 from onset 2.75; tie 4784 |
| sheet#1:5747 | FERMATA_BELOW, glyph 5746; fermata-chord 5747→4651 | [1410,931,1435,957] | Upper 하 at m6 onset 3.25; existing lyric component `lyric-1-13_4` already represents it; no new glyph |
| sheet#1:5762 | TENUTO, glyph 5472; chord-articulation 4654→5762 | [1620,942,1658,948] | Upper row extender at m7 held Bb3, continuing 네 from m6 onset 3.75; tie 4772 |

The current owner interpretation supersedes the earlier pending status only for these four objects in GT-14B; historical GT-14A records intentionally retain their then-current unresolved status. Original classifications, XML, grades and relation records remain intact in historical artifacts. The new `owner-interpretation-layer.json` retains those records alongside the new interpretation. Musical attachment relations in raw OMR remain observations, not evidence that the owner-classified text marks are musical articulations.

## Rendering contract

The [protocol](V4_GT14B_PROTOCOL.json) was saved before target rendering. Existing GT-14A combined alpha and 14 individual syllable masks are reused without rasterizing them again. Note, stem, beam, ledger, rest, header, chord, tie and syllable pixels are not repositioned.

Each new extender is a newly drawn 2px horizontal stroke with the original object's x interval and width. Its pixel-center y is the source bbox's pixel-center midpoint plus the **already frozen** paired-row displacement: A 0px, G 8px. Odd-height boxes would use the documented floor rule; the three actual source boxes are even-height. These lines approximate typeset continuation marks; their shape is not a claim of original glyph-raster fidelity. No source ink is copied, removed or restored.

The three source widths are 37, 38 and 38px. Their new A bounds are `[298,989,335,991]`, `[1330,944,1368,946]`, `[1620,944,1658,946]`. G bounds are the same plus 8px vertically. Source bbox midpoint residual is 0px for these cases. These are lyric continuation markers at tied-stop note positions, not lines required to touch the previous syllable physically. Semantic attachment checks require the confirmed held syllable, same-pitch START/STOP endpoints and persisted tie identity.

Only these three marks are added. Other visible continuation strokes on the complementary rows are **not inferred or generated in this run**. A complete two-row continuation inventory remains necessary before any full-score readiness claim. No MusicXML extender encoding is added; the diagnostic interpretation/placement JSON carries the new continuation evidence. Existing MusicXML lyrics and semantic events remain unchanged.

## Measured results

Final run: `/private/tmp/capomatic-v4-gt14b/gt14b-final-output/`. The earlier `gt14b-output/` is retained as a separate first development run, not overwritten.

| Measurement | A | G |
|---|---:|---:|
| Confirmed events / actually displayed | 13 / 13 | 13 / 13 |
| Confirmed chords | 3 | 3 |
| Korean syllables retained | 14 | 14 |
| New extenders / extra 하 glyphs | 3 / 0 | 3 / 0 |
| Total added alpha pixels per entire target canvas | 226 | 226 |
| Extender/music contacts | 0 | 0 |
| Extender/syllable contacts | 0 | 0 |
| Lyric/lyric and extender pair contacts | 0 | 0 |
| Existing lyric/music contacts | 0 | 0 |
| Minimum new-extender to existing ink-center distance | 18.6815px | 17.7200px |
| Clipped new elements | 0 | 0 |
| Inherited maximum notehead anchor residual | 0.5px | 0.5px |

Contacts count every nonzero alpha pixel, including faint antialiasing. Distances are Euclidean pixel-center distances, not optical quality scores. No collision tolerance or 0.5px notehead criterion was changed. Existing base pixels are identical outside new strokes, and added strokes do not overlap the old ink. No duplicate syllables or inferred extra marks were created.

## Visual outputs and review

Actual notation PNGs:

- `gt14b-final-output/original-bb.png`
- `gt14b-final-output/predicted-a.png`
- `gt14b-final-output/predicted-g.png`
- `gt14b-final-output/comparison-contact-sheet.png`

The prediction freeze precedes agent inspection. Visual criteria were intended row placement, no duplicated 하, legible retained notation, no visible new clipping, and visible incomplete warnings; they do not grade professional optical spacing. The actual A/G PNGs show the three marks in their intended rows, a single 하, retained chords, beams, ties and first ending/repeat. Agent visual verdict: **ACCEPTABLE_FOR_EXPERIMENT_WITH_LIMITATIONS**. This is not independent optical validation or a claim of professional engraving. G's low-register ledger/tie region remains visually dense, and the complementary-row continuation scope remains incomplete.

Separate outcomes:

- SOURCE_VERIFICATION: the four classifications and listed 13 events/3 chords/14 syllables are owner-confirmed; whole-source independent recognition completeness is **UNVERIFIED**.
- RENDERING_COMPLETENESS: **COMPLETE_FOR_THE_THREE_REQUESTED_EXTENDERS_AND_EXISTING_SCOPED_CONTENT**, not a complete full-score reconstruction.
- VISUAL_QUALITY: **ACCEPTABLE_FOR_EXPERIMENT_WITH_LIMITATIONS**, agent review only.
- Overall readiness: **INCOMPLETE_STANDALONE_RESEARCH_PROTOTYPE**.

## Validation and preservation

`python -m pytest tests/test_v4_ground_truth_*.py tests/test_v4_paired_ground_truth_01.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py tests/test_omr_v4_integrity.py -q`: **404 passed, 1 skipped**. The skip is the existing external MuseScore integration dependency. Thirteen new synthetic tests cover coordinate phase/width, deterministic bounded strokes, faint alpha contacts, clipping rejection, held-syllable context, no duplicated 하, raw SIG preservation and approval hash/classification rejection.

Unchanged full V3 guards pass for source roundtrip and both A/G in-memory transposition and frozen serialized MusicXML. Lyric signatures, event ordering, pitches, durations, voices and ties match the frozen representations. The rendered base is reused, so those checks do not establish independently correct recognition. GT-12's prediction freeze, GT-14A's full artifact directory, original source and bound review files are hash-checked unchanged. `prediction-freeze.json`, `semantic-integrity.json`, `rendering-validation.json` and the postfreeze visual/preservation report carry machine-readable results. `git diff --check` passes.

No original PDF/raster, protection mask, ownership rule, V1/V3 production module or API/frontend was changed. No original ink removal, original lyric-pixel composition, merge or deployment occurred. Large/copyrighted raster artifacts remain untracked.

Next task: source-confirm the complementary-row continuation inventory, then separately review the two-system notation and lyric continuation visually. Any source-pixel replacement requires its separate unchanged ownership gates.

Validation-design audit: the same research implementation generates and measures the new alpha strokes, so its geometry checks are engineering self-consistency, not external optical truth (verifier/designer overlap). The owner prompt also names the candidate classifications, so this is a source confirmation, not a blinded labeling experiment. The independent remedy is separate source-only visual annotation and output review; neither was invented or claimed here. A fresh-context cold read checked the report’s evidence/readiness wording only. Historical pending records and the current interpretation were checked for consistency without rewriting the historical records.
