# GT-14 owner-confirmed context continuation (GT14A)

**13/13 listed owner-confirmed events, three chords, fourteen lyric syllables, whole rest, ending1 and backward repeat are now actually rendered in A/G PNGs.** Existing notes and ties are reused without geometry changes. The result remains **INCOMPLETE_UNRESOLVED_SYMBOLS** because four excluded TENUTO/FERMATA objects are still unclassified. This is a standalone experiment, not a performance-ready score or original-ink composition.

Base: `37a90281ce2bc8da81cfb9b605226f64c300e536`.
Branch: `experiment/v4-gt14a-confirmed-context`.
Worktree: `/private/tmp/capomatic-v4-gt14a`.
Final commit SHA is returned with delivery. No historical branch was merged or rewritten.

## Actual owner evidence and exclusions

The actual approval message is preserved in [GT14_OWNER_SOURCE_APPROVAL.txt](evidence/GT14_OWNER_SOURCE_APPROVAL.txt); the preceding user candidate/context is preserved in [GT14_SOURCE_REVIEW_CANDIDATE.txt](evidence/GT14_SOURCE_REVIEW_CANDIDATE.txt). [GT14_OWNER_BINDING.json](evidence/GT14_OWNER_BINDING.json) binds their bytes to the frozen GT14 source review sheet, checklist, inventory, source PNG and prediction freeze. The user explicitly authorized this separate rendering continuation. No timestamp, reviewer identity, signature or independent annotation was invented. Classification is OWNER_VERIFIED_SOURCE / NOT_INDEPENDENT_GROUND_TRUTH.

The original pending GT14 checklist and all historical artifacts remain untouched. The new derived inventory records the prior classifications and updates only the newly approved scope. M5's incoming whole-note stop and the m4→m5 connection retain their earlier confirmation; m6/m7 events and m8 whole-measure rest now have explicit owner approval. The listed-event total is13, not a whole-page accuracy denominator.

The following objects remain **AMBIGUOUS_UNVERIFIED_NOT_RENDERED_NOT_DISCARDED**, with exact original source XML, bbox, attributes and all incoming/outgoing relations preserved in `ambiguous-objects.json`:

| ID | Original OMR class | Original bbox, exclusive right/bottom |
|---|---|---|
| sheet#1:5686 | TENUTO | [298,987,335,993) |
| sheet#1:5699 | TENUTO | [1330,942,1368,948) |
| sheet#1:5747 | FERMATA_BELOW | [1410,931,1435,957) |
| sheet#1:5762 | TENUTO | [1620,942,1658,948) |

The typed fermata-chord relation to4651 is retained; it is not promoted to proof of a genuine musical fermata. Missing articulation relations are not repaired by proximity. Confirmed lyric “하” can be newly typeset from the owner's text/association evidence without declaring the original FERMATA object to be a lyric stroke. These are separate claims.

No dash/extender glyph is inferred at excluded-object sites. Onset3 remains a tied continuation with **no new lyric token**; ambiguous physical marks at m5/m6/m7 are withheld. Earlier first-system continuation marks remain untouched. This conservative omission is explicit and prevents a complete-source-reconstruction claim.

## Source and semantics

Original: Bb PDF page2, printed measures5–8. Source PNG SHA remains `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`. No OCR/Audiveris rerun, reference A/G access, or source recognition algorithm change occurred.

Raw historical recognition remains **13 events, one harmony, zero lyric tokens** for this system. Owner-supported diagnostic augmentation adds the previously omitted Gm/Eb harmonies and fourteen lyric tokens; it does not improve or rewrite historical OCR evidence. Existing Bb/D remains unchanged. No new m8 chord is inserted.

| Measure | Source chord | A −1 | G −3 |
|---|---|---|---|
| 5 | Gm | F#m | Em |
| 6 | Bb/D | A/C# | G/B |
| 7 | Eb | D | C |
| 8 | No newly printed chord | None | None |

Root, quality and slash bass are checked through unchanged V3 chord transposition and serialized MusicXML chord recovery. Chords retain source-based horizontal placement near the beginning of their measures, rather than being attached automatically to the first pitched note. Actual ink widths are A74/88/28px, G55/64/25px; all fit their original measure regions and have no music contacts.

M6 lyric starts are exactly onsets **1.5,1.75,2,2.5,2.75,3.25,3.75**:
upper **내/가/있/길/원/하/네**, lower **주/의/놀/라/운/손/길**.
The tied stop at onset3 receives no new syllable. All original event pitches, durations, order, voices, ties, expressions and articulations remain equal to frozen signatures; the ambiguous SIG objects remain outside any inferred semantic cleanup.

## Reused geometry and newly supported notation

[Protocol](V4_GT14A_PROTOCOL.json) was declared before target generation. All existing GT14 event, stem, beam/hook, ledger and tie alpha masks are reused, now displayed black following source approval. GT13A6's m5 whole-note endpoint, incoming/outgoing segments and first-system context remain exact cached geometry. No first-system lyric layout is changed.

New whole rest: FreeSerif U+1D13B, same note font-size rule as GT13A2. The glyph contains an upper bar and descending block. Its declared font-specific upper-bar center `(191,560)` is placed on original staff line index1 at source x2160.5 using the GT05A canonical raster translation. No rescaling or threshold selection. Synthetic controls across interlines14/18/24 and integer/fractional origins check staff contact, downward hanging ink, determinism and <=0.5px semantic-anchor residual. Actual residual is `[0.454,0.228418]px`. This is a font-design attachment anchor, distinct from optical center or a new notehead measurement. Existing notehead residuals remain <=0.5px by unchanged raster masks.

Ending1: raw ending5201 supplies left/right legs and original top-line geometry. A width2 joined polyline uses the original top y722 and leg endpoints; numeral “1.” is newly typeset with the existing FreeSerif40 text contract at its measured source location. MusicXML's existing RepeatBracket1 over m8 is checked.

Backward repeat: source thin24/heavy26 bboxes and repeat dots5765/5767 are reconstructed as separate standalone components, with both dots left of the thin bar and thin left of heavy. MusicXML's existing m8 end-repeat is required. Synthetic tests check connected bracket geometry, the number, direction, dot order, missing geometry, clipping and deterministic output. Structural contacts with original staff scaffold are intentional, not permission to modify source structural ink.

## Collision-safe Korean layout

GT12 AppleGothic44 and `text_mask` are reused. The same source-only display alignment measurement method determines the initial two baselines; it grants **no source pixel ownership**. Each syllable retains its associated original head x. Both rows translate together vertically, preserving their separation and all glyph alpha tiles.

The unchanged GT13A5 exhaustive finite displacement-domain rule uses actual nonzero alpha and a one-pixel Chebyshev spacing obstacle around all fixed notation/chords. Only downward integer shifts fitting original viewport bottom1030 are admissible; no horizontal move or font shrinking. The minimal feasible offset is selected, with all smaller forbidden offsets recorded.

| Measurement | A | G |
|---|---:|---:|
| Listed owner-confirmed / rendered musical events | 13 / 13 | 13 / 13 |
| Confirmed chords / lyric syllables rendered | 3 / 14 | 3 / 14 |
| New inferred dash/extender glyphs | 0 | 0 |
| Paired lyric-row displacement | 0px | **8px** |
| Actual lyric/fixed-music contact pixels | **0** | **0** |
| Actual lyric/lyric contacts | 0 | 0 |
| Minimum lyric→fixed-ink center distance | **3px** | **2px** |
| Chord→music contact pixels | 0 | 0 |
| Structure/chord contact pairs | 0 | 0 |
| Clipped components | 0 | 0 |

For G, every offset0–7 is forbidden. This is a measured minimum under the declared integer-downward model, not a professional engraving optimum. A requires no movement. First-system pixels are identical to GT13A6 in the preserved region. New whole rest has zero contact with old event ink; its staff-line contact is the intended hanging attachment. Text safety here concerns newly typeset standalone pixels, not original Korean text or safe erasure.

## Actual visual review and separate verdicts

Prediction hashes were frozen and verified before assistant inspection of the actual comparison PNG. Chords, both Korean rows, hanging whole rest, ending numeral/bracket and backward-repeat dots/bars are visible and legible for this experiment. G's rows clear the unchanged local tie after +8px. No new obvious clipping or symbol contact was seen. Thin ties, beam raster edges and text/font aesthetics still need musician review. The missing dash-like marks are disclosed, not silently normalized away.

- **SOURCE_VERIFICATION:** listed content OWNER_VERIFIED_SOURCE, four original objects excluded and still ambiguous. Raw OMR chord/lyric recognition remains incomplete.
- **RENDERING_COMPLETENESS:** all confirmed supported content rendered, but **INCOMPLETE_UNRESOLVED_SYMBOLS** for reconstruction of the original system.
- **VISUAL_QUALITY:** ACCEPTABLE_FOR_EXPERIMENT_WITH_UNRESOLVED_SYMBOLS, based on assistant PNG inspection only.
- **INDEPENDENT_GROUND_TRUTH:** no new independent labels; no independent human optical certification, performance or print approval.

## Validation and preservation

**391 passed, 1 skipped**: targeted ground-truth/rendering, paired-ground-truth, V3 music/gate and V4 integrity tests. Existing skip is external MuseScore availability. No Full Acceptance.

Unchanged V3 full guards pass for the owner-augmented source roundtrip, A/G in-memory transposition and serialized target files. Full lyric signatures survive serialization, and event signatures remain identical to historical targets. Chord root/quality/bass text is separately checked. New negative controls cover conflicting chord content, missing repeat, invalid direction/dots/bracket geometry, ambiguity exclusion promotion and exact tied-lyric associations.

An initial preflight used a helper constant that pointed to the GT13A5 baseline rather than the actual GT13A6 Phase2 artifacts. It failed before output-directory creation; the reference was corrected before any target rendering. No geometry or tolerance was tuned after seeing results.

Original GT14 evidence, GT13A6/GT13A4 inputs, source PNG and approval-context hashes remain unchanged. Exact cached music masks, first-system pixels and every excluded object's complete record/relations are checked. Actual approval text and context are hash-bound without invented timestamps/signatures. Formatting and `git diff --check` pass. Only research helpers/tests/protocol/docs and approval text/context are committed; all score images/MusicXML/large artifacts remain untracked.

## Outputs and next step

Untracked directory: `/private/tmp/capomatic-v4-gt14a/gt14a-output/`.

- `predicted-a-second-system.png`, `predicted-g-second-system.png`, `comparison-contact-sheet.png`, `original-second-system.png`
- `A-first-plus-second-context.png`, `G-first-plus-second-context.png`
- Actual owner approval/binding, derived verified inventory, ambiguity records, owner-augmented source/target MusicXML, rendering/guard reports, input/prediction freezes
- Post-freeze visual/preservation/final validation reports
- **`ambiguous-source-review.png`** and four native source crops, with an exact case map, for later object-specific review only. No predictions or suggested classification are painted on those source crops; owner answers remain null.

Reproduce with retained local frozen evidence and fonts, choosing a fresh output directory:

```bash
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt14a_confirmed_context --out gt14a-new-run
```

Next source decision concerns **only** objects5686/5699/5747/5762 individually. Their interpretation remains pending; no duplicate confirmation of the now-approved notes/chords/lyric strings is needed. Until resolved, retain incomplete status. No original source ink removal, original lyric-pixel compositing, protection-mask/ownership relaxation, V1/V3 production change, API/frontend route, merge or deployment occurred.
