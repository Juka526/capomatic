# GT-17B — full-score source audit and provisional A/G rendering

**All nine printed systems, measures 1–37, now have real standalone A/G experimental previews.** Each target displays 169 recognized note/rest cores, 24 chord strings, 167 Korean syllables and 50 continuation marks. These are display counts, not independently verified accuracy. The owner-confirmed subset is 86 events, 12 chords, 88 syllables and 30 marks through m19. The remaining 83 events and candidate text are provisional. Source completeness and full-score musical readiness remain **UNVERIFIED / INCOMPLETE**.

For consolidated owner review, start with `gt17b-final-output/full-source-owner-review-sheet.png` and `gt17b-final-output/full-source-owner-review-checklist.json` in the worktree below. These contain source-only evidence; review does not require opening target previews.

## Revision, approval and frozen inputs

Base: `36a6b153aa40f44986b30ca112e73114e8c8ec79`. Branch: `experiment/v4-gt17b-full-score-rendering`; worktree `/private/tmp/capomatic-v4-gt17b`. The commit containing this report is the implementation revision; its exact SHA is supplied at delivery. [Protocol](V4_GT17B_PROTOCOL.json) and [validation metadata](V4_GT17B_VALIDATION.json) bind code, files and results.

Source is the original Bb PDF page2, represented by its frozen source raster and persisted source-side OMR. No A/G reference pages were accessed. No OCR, Audiveris, model download or source re-recognition occurred.

| Read-only source file | SHA-256 |
|---|---|
| source.png, RGB2520×3564 | `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de` |
| recognized.omr | `857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638` |
| visual-graph.json | `f8725c39beaaecc877ccf48b803b79a419c2d6e60aa73bc9428a39de11596508` |

Source files live under `/private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output/predictions/baseline-exec/source/`. Required historical layers are GT-16B/GT-16C/GT-17 `*-final-output` directories. Their committed document bindings, complete prediction manifests and before/after file hashes passed. Historical PNGs, masks and interpretation records were never rewritten.

`owner-interpretation-layer.json` preserves the actual Phase2 approval excerpt verbatim, its origin in the current GT-17B user instruction, and GT-17 inventory/checklist/review-sheet/freeze hashes. It approves m17–19 only, including Bb/D, Eb, four syllables and two strokes. Raw SIG 5999/6001 remain TENUTO observations in the original graph; the approved lyric-stroke interpretation is a separate layer. No reviewer identity, signature or timestamp was fabricated. The GT-16C authorization remains OWNER_APPROVED_EXPERIMENTAL_LAYOUT within its original scope, not independent musician validation.

## Complete source structure and coverage

Persisted staff polylines and barline coordinates, printed-number words and source raster views establish this diagnostic registration:

| System | Printed measures | Recognized events | Verification scope |
|---|---|---:|---|
| 1 | 1–4 | 26 | Existing owner-confirmed music/text scope |
| 2 | 5–8 | 13 | Existing owner-confirmed scope |
| 3 | 9–12 | 20 | Existing owner-confirmed scope; withheld SIG retained |
| 4 | 13–16 | 18 | Existing owner-confirmed scope; playback/SIG exclusions retained |
| 5 | 17–19 | 9 | Newly approved by the actual GT-17B instruction |
| 6 | 20–24 | 30 | OMR_PROVISIONAL; source visual text candidates |
| 7 | 25–29 | 17 | OMR_PROVISIONAL; source visual text candidates |
| 8 | 30–33 | 22 | OMR_PROVISIONAL; source visual text candidates |
| 9 | 34–37 | 14 | OMR_PROVISIONAL; source visual text candidates |

Total 169 comprises133 pitched notes and 36 rests. The preserved semantic stream is one part/voice; all measures have four quarterLength units. Event registration checks source-side GT-02 physical associations against MusicXML onset/duration/pitch and raw Inter IDs. Agreement between those sources is consistency evidence, not independent completeness. No visually absent symbol is certified absent for the new systems.

`full-source-system-map.json` records exact system/measure bounds and original staff geometry. `full-source-event-inventory.json` contains every system's raw OMR objects/relations, stable IDs/bboxes, events, separate candidate lyrics/chords/marks and uncertainty classifications. `full-source-coverage-matrix.json` has 74 rows: every37 measures separately for both targets. It records recognized/displayed/owner event counts, text coverage, unclassified IDs and repeat uncertainty. A measure-level owner-confirmed label is bounded to approved events/text, never an assertion that all raw SIG interpretations are settled.

## New source text and structural candidates

Newly audited m20–37 contain 12 chord candidates:

| Measures | Candidate chords |
|---|---|
| 20, 22, 24 | Bb, F, Gm7 |
| 25, 26, 27, 28 | Bb/D, Eb, F, Eb |
| 30, 32 | Bb, F |
| 34, 35, 36 | Gm, Bb/D, Eb |

Other new measures have no newly printed chord candidate observed; their absence remains a review question. Only four of these12 appear as harmonies in the inherited owner-augmented MusicXML. Ordinary words, missing text and recognition mistakes are preserved separately. For example, source word 4314 near the printed Bb is recognized as 마; word 4380 near the Eb candidate is Eh. Their raw values are not rewritten.

The79 new Korean syllable candidates are individually tied to source windows, diagnostic dark-support bounds, note IDs and candidate onsets. Both rows in systems 6–7 were inspected separately; no lower-row marks were copied automatically. Systems8–9 show one visible lyric row, with lower-row absence explicitly pending. Representative rows include m20 나/의/맘 and 나/의/삶; m21 주/의/성/전/이/되/어 and 주/의/말/씀/을/따/라; m25 주/의/마/음/있/는/곳 and 주/의/시/선/있/는/곳. Full strings/associations are in the source-only checklist. Merged OMR strings such as 성딸, 전씀, 마시 and 선있 remain original observations, not approved transcriptions.

Twenty new continuation candidates have individual native crops, row, source bounds, event association and uncertainty. They include tied/melismatic positions and m28's second-ending context; a visible dash is not by itself proof of a repeat-dependent held-syllable lineage.

Source structure candidates include forward repeats at m20/m30, first ending 26–27 with backward repeat at 27, second ending 28, final backward repeat 37, and section labels Chorus/Tag. Exact source barline/dot/ending geometry is newly engraved on the research canvas. The English Chorus label uses title case while the raw word retains lowercase `chorus`; this is a provisional display interpretation. The OMR's5190/5191 ENDING observations around that section frame remain raw observations, not newly inferred musical endings. **No playback jump or complete repeat route is inferred.** The original title, Verse label, credits and publisher footer are not retypeset or copied into the generated score; the full source page remains available for review.

## Musical rendering and isolated fifth-system integration

The GT-16C four-system generated alpha layers are reused byte-for-byte. The frozen GT-17 fifth-system music/clef/key/ending/Eb layer is also reused, adding only approved Bb/D, four newly typeset syllables and two strokes. Fifth lyric displacement is 0px for both targets; minimum ink-center clearance is 11px A and 2px G. Integration reaches the expected confirmed totals86/12/88/30 without moving historical notes, beams, ties, rests or lyric baselines.

The remaining 83 event cores are newly rendered with validated primitives: GT-05 raster placement, GT-12 text placement, GT-14 whole rest, GT-15 half head, GT-07 flag bitmap and GT-13 cubic curves. New research-only composition supports up/down stems, explicitly serialized mixed beams/hooks, a down single flag and source-backed dotted-half notes. It does not change any production component.

- Target note y comes from semantic diatonic pitch and original staff spacing, independently of the detected physical head center. Physical source center, semantic target coordinate, raster anchor and bitmap bounds remain separate fields. Source note x is retained; residual limit stays0.5px per axis.
- Stem side must match the persisted LEFT/RIGHT head-stem relation. Beam membership, primary order, semantic levels, hook direction, source slope and secondary separation are checked. New mixed groups use existing line rasterization, not automatic GT-16C supersampling.
- The down flag is a vertical reflection of the validated single-flag bitmap. Its required stem tip is derived from actual head-bottom and flag extent: `tip_y >= head_bottom_inclusive + upward_flag_span + interline/2`. This avoids self-contact independently of a particular source measure. Fractional-phase controls verify attachment and clearance.
- Dotted halves require NOTEHEAD_VOID, a true dotted-half duration and exact augmentation lineage. Dot placement follows the target staff line/space convention. No sounding octave changes, new8va/8vb or unsupported accidental glyphs are introduced.
- Eleven persisted curve segments are rendered in the new systems. The m33→34 pair4907/4816 has reciprocal extension attributes and matching source pitch/tie roles; two separate provisional segments are drawn. No line crosses the physical inter-system gap. The confirmed m4→5 pair remains in the frozen earlier layer.

All original recognized note/rest cores are displayed. That does **not** mean every printed attachment or source event is recognized correctly.

## Layout and collision accounting

Source-registered canvas remains2520×3564, with an extra140px warning header outside source coordinates. PNGs are2520×3704. PDFs contain a lossless RGB image XObject at 300 export dpi, yielding one custom604.8×888.96pt page. This custom warning-bearing page is not asserted to equal the physical original PDF page. It introduces no MuseScore stretch or note-coordinate reflow.

New coupled lyric rows use the predeclared finite minimum-displacement search with unchanged2px ink-center safety floor, zero actual text/music and text/text contacts, no horizontal lyric shift, no lost pixels and preserved row separation. The6px GT-16C optical objective is **not** globally adopted.

| New system | A lyric dy | G lyric dy | Final minimum lyric/fixed-ink center distance |
|---|---:|---:|---:|
| 6 | 7px | 16px | 2px |
| 7 | 4px | 13px | 2px |
| 8 | 4px | 13px | 2px |
| 9 | 6px | 15px | 2px |

The three-sharp A key groups in systems 6/8 require an8px left translation to clear source repeat bars. Only that key group's x changes; sharp y, glyph bytes/order, clef, note positions and repeat geometry remain fixed. The least feasible integer translation is selected with actual-ink clearance≥2px. Other new key groups have dx0. Synthetic controls reject impossible allocations.

Measured new-region results for each target:

- 83/83 note/rest cores; maximum notehead residual0.5px per axis;0 missing stem/head/beam/flag connections.
- 0 unexpected music-component contacts;0 unexpected key/chord/structural contacts;0 lyric/music or lyric/lyric contacts;0 inter-system alpha contacts;0 clipping.
- Minimum clearance to preceding-system ink is 61px A /52px G across the new systems. No increased inter-system spacing or multipage reflow is numerically necessary under the declared safety floor. The clean-style file is a style alternative, **not** a reflowed engraving.
- **37 actual tie/barline contact pixels per target are reported separately**, across four explicitly serialized equal-pitch START/STOP ties and their own adjacent-measure boundary bars. Staff crossings and these specific barline crossings are intentional notation context; they are not zero contact or unrelated-symbol permission. Other structural collisions fail closed. Unit controls reject unequal pitch, missing tie roles, wrong measure, wrong barline and ordinary slurs.

Chords use actual font ink/advance widths, source placement and alpha collision checks. Longest new rendered width is recorded per system; character count is not used as a fit metric. No provisional syllable/mark was dropped to obtain zero contacts.

## Unresolved content and recognition gaps

`unresolved-source-objects.json` lists32 cases, not32 proven missing articulations:

- 27 unclassified raw articulation observations: the ten previously withheld IDs5833/5841/5896/5902/5903/5927/5948/5949/5975/5984, three earlier objects 5591/5649/5660, and 14 objects in systems 6–9. Some spatially coincide with already rendered lyric/mark candidates; no automatic constituent-ink classification follows from that overlap.
- Non-tie curve 4867 remains unclassified/withheld.
- Four source-visible possible tie/slur relationships missing from semantic lineage: m21 onset15/4→m22 onset0; m31 onset5/2→3; m33 onset5/2→3; m35 onset11/4→3. Their exact source windows, endpoint IDs and recognized pitches are provided. In particular, m31's recognized C5/Bb4 endpoints are unequal, so even the source pitch correspondence needs review. No guessed curve or pitch repair is rendered.

SIG 5999/6001 and the earlier approved lyric interpretations are not promoted to music articulations. Historical observations remain intact. Full repeat playback, uncertain associations and source completeness remain unresolved. Missing source metadata and these attachment gaps prevent a complete-score claim even though all 169 currently recognized event cores are visible.

## Semantic checks: distinguish the two artifact levels

Frozen original-side pre-ledger and recognized MusicXML each have 37 measures/169 events/**7** harmonies. GT-16B's owner-augmented source has 15 harmonies. The frozen GT-17B owner-source/targets have 16, adding the approved m17 Bb/D; their new-region raw merged OCR lyrics are retained. The unchanged full V3 source-roundtrip, A/G in-memory and serialized guards pass at that level. Notes/onsets/durations/voices/ties/repeat signatures remain unchanged.

The visual candidate has 24 chord strings and 167 syllables, exceeding those 16 frozen harmonies. This difference is explicitly audited, not hidden behind the guard. After the image freeze, a **separate semantic-only diagnostic** adds the eight missing provisional chord candidates and 79 candidate lyric associations to a copy, without changing any note/rest/tie or frozen output. It writes `post-freeze-semantic-audit/provisional-source.musicxml` and A/G `*-provisional-transposed.musicxml`.

The unchanged full V3 guard also passes for those 24-harmony candidates in memory and after serialization. Source-derived chord expectations are Bb→A/G, F→E/D, Gm7→F#m7/Em7, Bb/D→A/C#/G/B, Eb→D/C and Gm→F#m/Em. Those checks establish mathematical/representation consistency of the proposals, not source correctness. No owner labels beyond19 are added. The raw/recognized/owner measure comparison preserves the original pitch-repair lineage for inspection.

**MusicXML lyric-extender serialization is still incomplete.** Visual dashes are not automatically `<extend>` semantics. Neither the production exporter nor the original predictions are modified. The post-freeze semantic audit does not retroactively turn the frozen16-harmony MusicXML into24-harmony predictions; consumers must distinguish the clearly named diagnostic candidate files.

## Agent visual review and independent gates

An842-file manifest was verified before actual image inspection. Agent inspection covered the original/A/G comparison, native new-system previews, the G clean-style candidate and Poppler-rendered A/G PDFs. The new content is legible enough for consolidated source review; notes, whole-note holes, dots, flag and mixed-beam grouping are visible. Optical shortcomings remain: thin/stair-stepped curves, close lyrics under down-stem beams, visibly tight2px clearances, heavy beam ends and wide blank source-header space. Missing curves and source text uncertainty matter more than plausibility.

**Agent visual-quality verdict: NEEDS_REFINEMENT.** Numerical nonintersection is not professional engraving quality. This is not independent optical or musician validation; genuine independent labels/reviews remain0. Clean-style candidates retain prominent warnings and repeated PROVISIONAL/INCOMPLETE margin watermarks, with the same uncertainties as the color diagnostic.

| Gate | Result |
|---|---|
| Semantic consistency | PASS, unchanged V3 guards at 16-harmony frozen and 24-harmony diagnostic levels |
| Source recognition coverage |169 recognized cores mapped; true printed completeness UNVERIFIED |
| Rendering completeness |169 cores, 24 chord strings, 167 syllables, 50 marks; INCOMPLETE attachments/source metadata |
| Numerical layout safety | Declared alpha/anchor/connectivity/viewport checks PASS;37 intentional tie/barline pixels separately retained |
| Agent visual review | NEEDS_REFINEMENT, readable research preview |
| Owner verification |86 events/12 chords/88 syllables/30 marks, through 19 only |
| Independent musician validation |0, not performed |

## Review packet, files and reproduction

Output directory: `/private/tmp/capomatic-v4-gt17b/gt17b-final-output/`.

Required real artifacts:

- `A-full-score.png`, `G-full-score.png`; companion `*-full-score-clean-style.png`.
- `A-full-score-experimental.pdf`, `G-full-score-experimental.pdf`; `Bb-A-G-full-score-comparison.png`.
- `full-source-system-map.json`, `full-source-event-inventory.json`, `full-source-coverage-matrix.json`.
- `full-source-owner-review-sheet.png`, `full-source-owner-review-checklist.json`, `owner-review/` with the original page, four native system crops, 18 measure crops, individual stroke/chord/ambiguous-object/curve crops and packet freeze.
- `full-score-rendering-validation.json`, `full-score-semantic-integrity.json`, `full-score-preservation-verification.json`, `full-score-visual-review.json`, `unresolved-source-objects.json` and `prediction-freeze.json`.
- `post-freeze-semantic-audit/` and the measure-level uncertainty manifest are separate diagnostic companions; no prediction images were changed after inspection.

The owner-facing directory contains source evidence and neutral response fields, **no target predictions**. Answer by measure/onset or object ID: CONFIRM, CORRECT with correction, or UNCERTAIN. Onsets reset to0 in each printed measure and use quarterLength units (one quarter note=1;15/4=3.75); durations use the same units. Source page pixels use x-right/y-down and right/bottom-exclusive bboxes. The entire new scope may be reviewed in one consolidated reply with explicit exclusions. All answer fields remain empty. The current owner approval excerpt is only for17–19; do not mistake prepared forms for new human submissions.

```bash
cd /private/tmp/capomatic-v4-gt17b
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt17b_full_score --output /private/tmp/capomatic-v4-gt17b/FRESH-OUTPUT
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt17b_post_audit --output /private/tmp/capomatic-v4-gt17b/FRESH-OUTPUT
/private/tmp/capomatic-v4-venv/bin/python -m pytest tests/test_v4_ground_truth_*.py tests/test_v4_paired_ground_truth_01.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py tests/test_omr_v4_integrity.py -q
git diff --check
```

Validation: **570 passed, 1 skipped**, including 25 new synthetic controls. The sole skip is the existing external MuseScore integration dependency; no new skips or gate waivers. Source/freeze/file-hash preservation passes. The separate [V3 Full Acceptance evaluation](V3_ACCEPTANCE.md#ci-operation-after-closure), covering the broader real/synthetic/fresh-holdout corpus and fallback outcomes, was not run; these local targeted checks do not establish that acceptance result. The calibrated font runtime stays in the existing venv; PDF encoding uses an isolated child with already installed system pypdf 6.18.1 at `/opt/anaconda3/bin/python`. ReportLab/pypdf were absent in the font venv; nothing was installed or silently substituted there. PDF image extraction hashes equal the source PNG RGB bytes, and both pages were rendered with Poppler and inspected.

Development failures are retained in separate untracked directories: a missing nullable staff assumption, initial 4px then1px own-head/down-flag contact, section-label viewport clipping, RGB source-panel handling, and A key/repeat 50/57px contacts. The fixes use explicit geometry/type contracts and synthetic controls; no A/G reference tuning, event substitution or historical rerendering occurred. Final prediction and post-audit hashes remain separate. The artifact operation marker ran before PDF authoring. Software/font hashes and environment are in validation metadata; these local external dependencies are not a self-contained archival package.

## Next approval boundary

The next action is consolidated owner review of measures 20–37, especially the four missing curve/pitch cases, exact lyric associations, 20 strokes, 12 chords/absences, section/repeat notation and individual SIG uncertainties. Once actual corrections/approvals are received, continue **this same GT-17B project** with a separately frozen owner-confirmed interpretation and render. Do not automatically promote candidates or invent a full repeat route. Independent musician review and further optical refinement are separate later gates.

No original PDF/raster edits, source ink removal, original-pixel lyric composition, protection-mask changes, ownership promotion, V1/V3 production/API/frontend changes, merge or deployment occurred. Copyrighted pages, score images, MusicXML and large diagnostics remain untracked.
