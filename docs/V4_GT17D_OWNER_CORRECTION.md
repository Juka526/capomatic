# GT-17D — scoped owner correction of SIG 4867

**The erroneous 4867 slur is removed from a new semantic source and A/G MusicXML candidates.** Exactly one relationship changes. All 169 note/rest cores, 24 chord meanings, 167 Korean syllable wordings/rows and every other tie/slur remain unchanged. Standalone PNG copies are byte-for-byte and pixel-for-pixel identical to the frozen GT-17B owner-integration previews: no new glyph or visual correction was necessary within that frozen standalone representation; no claim is made about other MusicXML renderers.

Source recognition completeness remains UNVERIFIED; standalone rendering remains INCOMPLETE and its optical quality remains GT-17B NEEDS_REFINEMENT. This is one OWNER_VERIFIED_INTERPRETATION, not independent ground truth or general approval of the provisional source inventory.

Original source: Bb major, PDF page2. Targets: A major (−1 semitone) and G major (−3 semitones).

## Revision and owner provenance

Base: `477b418d982c95c430531ba46d999cd40448e2e2`. Branch: `experiment/v4-gt17d-owner-correction`. Worktree: `/private/tmp/capomatic-v4-gt17d`. The containing commit is the implementation revision, with its exact SHA supplied at delivery.

`owner-approved-4867-correction.json` preserves the exact owner response **“동의합니다”**, explicitly quoted by the current GT-17D user instruction, together with its narrowly approved review context. It embeds the preceding GT-17C case verbatim and binds the prior report, source crop, delta sheet, object/event inventory, checklist and audit freeze by SHA-256. It does not invent a separate submission, signature, identity or timestamp. The classification is `OWNER_VERIFIED_INTERPRETATION`; independent ground truth remains0.

The approved interpretation is a stroke of the existing upper-row Korean syllable ‘되’, not a musical slur. The response authorizes removing that false semantic relationship only. No additional note, lyric association, continuation, repeat route or raw SIG classification is approved. Raw OMR/SIG records remain unchanged.

## Exact mapping and fail-closed removal

| Original-side identity | Verified value |
|---|---|
| Raw object | `sheet#1:4867`, original `SLUR_BELOW` observation |
| Original bbox | `[1132,2306,1158,2311]`, page pixels, right/bottom excluded |
| LEFT relation | `c5b9a509d9f3992b90e6` → `sheet#1:2143` |
| RIGHT relation | `0bed003219cae5ea4049` → `sheet#1:2191` |
| Printed measure |21 |
| Source event | `p1:m20:n5`, onset3, C5 |
| Destination event | `p1:m20:n6`, onset13/4, Bb4 |
| Existing XML | Part `V4Part1`, measure21, zero-based XML note indices7/8, slur number1 START/STOP |

The event IDs retain the historical zero-based OMR indexing; printed measure21 is authoritative. Onset13/4 means3.25 quarter notes. The raw relation sides, head identities/bboxes, written pitches, unique semantic spanner, adjacent XML event indices and exactly one matching START/STOP pair are checked before writing corrected MusicXML. Missing or ambiguous mapping raises BLOCKED; no nearest or arbitrary slur is deleted.

The new source removes those **two `<notations><slur>` elements**, preserving the other content elements/attributes, note/rest events and original XML comment/header context. Normalized XML-tree comparison against an independently formed two-node removal expectation passes. The upper lyric row already contains exactly one ‘되’ on the destination event; it is retained without adding another text/glyph. The source has2 slur spans before and1 after: only the unequal-pitch m31 span remains. The corrected source retains its original number2; A/G serialization may renumber this sole remaining span to1. Endpoint identity, not the exporter-local number, proves preservation.

Both targets retain all previous note/rest signatures, lyrics/rows, repeat/ending signatures and other curve inventories. m21→22, m33 and m35 remain equal-pitch ties; m31 remains an unequal-pitch slur. Sound `<tie>`, notational `<tied>` and `<slur>` records are audited separately. Sound/notation tie roles agree, and the four specifically approved relationships pass source/A/G endpoint checks. No additional curve removal or creation occurs.

## Preserved source scope and unresolved semantics

| Scope | Count |
|---|---:|
| Printed systems / measures |9 /37 |
| Recognized note/rest cores |169 |
| Owner-confirmed / provisional event cores |86 /83 |
| Owner-approved chord symbols |24 |
| Approved syllable wording/row assignments |167 |
| Verified / provisional exact lyric onsets |88 /79 |
| Verified / provisional continuation marks |30 /20 |

These are scoped evidence/display counts, not an independent accuracy denominator. The approved 4867 classification does not confirm the two associated note cores. Therefore all83 provisional cores persist:81 prior nonconflicting candidates plus2 attachment-corrected, still-unverified cores. No historical PASS_CANDIDATE is promoted to owner source verification.

`M28_CONTINUATION_LINEAGE = UNRESOLVED` and `FULL_REPEAT_PLAYBACK = UNRESOLVED` remain explicit. Visible approved endings and repeats are unchanged. No held-syllable ancestry, repeat jump, traversal sequence or additional XML extension is generated. Source and both corrected targets still contain0 lyric `<extend>` records; the previously identified serialization gap is not solved by this correction.

## Rendering preservation

The frozen renderer already excludes4867 from the music component map. Its original withheld-object record, existing source-derived component-map hash and the removal-only XML difference are retained as evidence. No note, stem, beam, tie, staff, chord, lyric or optical-layout geometry changes.

`A-full-score-unchanged.png` and `G-full-score-unchanged.png` are **explicit copies**, not independent rerenders. Each has the same file SHA-256, image mode,2520×3704 dimensions and decoded pixel bytes as its frozen counterpart. Copy equality alone is not a fresh rendering test; the component audit explains why this standalone representation needs no altered pixels. A different MusicXML renderer is not tested. No new PDF is produced.

A second isolated execution reproduces the corrected source byte-for-byte and the same target musical/content XML. Regenerated A/G files differ only in music21’s automatically generated score/MIDI instrument identifier values; their content trees are equal after normalizing those linked IDs. Exact target byte determinism is not claimed. All delivered files have their actual SHA-256 recorded. XML note voice fields are separately compared with the prior source/targets and remain unchanged.

Original source inputs remain hash-bound:

| File | SHA-256 |
|---|---|
| Original supplied PDF | `1cc64756c0ce47b1db0ea6ac21eefe4685097a04cd4589f954afc712afb605fd` |
| source.png | `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de` |
| recognized.omr | `857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638` |
| visual-graph.json | `f8725c39beaaecc877ccf48b803b79a419c2d6e60aa73bc9428a39de11596508` |

All GT-16B/16C/17/17B/17C source/output/interpretation snapshots and required frozen manifests pass before/after checks. Original protection geometry remains in the unchanged graph; no protection mask is loaded for mutation. Copied previews retain DEVELOPER-ONLY /INCOMPLETE /NOT FOR PERFORMANCE OR PRINTING warnings and the earlier visual limitations. No new independent optical or musician validation is claimed.

## Efficient remaining owner review

`remaining-review-plan.json` and Korean `owner-review-summary.md` organize **210 overlapping field items into21 coherent response groups**. The owner can reply by group ID with CONFIRM, CORRECT naming case IDs/fields, or UNCERTAIN; omitted fields remain pending. No manual editing of hundreds of JSON entries is required. Groups are organized by system and review field (music, lyric onset, continuation or raw SIG), with separate M28_LINEAGE and FULL_PLAYBACK groups. For example, `SYS6_EVENT: CORRECT — [case ID and corrected fields]` is a response format, not a prefilled answer. The summary provides per-measure onset/pitch/duration or row/onset/syllable associations, candidate raw-object descriptions and clickable existing source-review references.

The plan covers83 event cores (81 prior candidates plus2 carry-forwards),79 onset associations,19 visually supported continuation candidates, the unresolved m28 mark,27 other raw SIG cases and one full-playback decision. Nine one-to-one source-region overlap links connect raw stroke questions with continuation questions so the same printed stroke can be reviewed together. They do not infer ownership, propagate answers or turn overlapping questions into separate musical errors. Ambiguous overlaps would remain unmerged. All group and item answer fields are blank.

The existing GT-17C source-only delta sheet and native crops are referenced by path/hash; no new source packet is generated. The4867 question is excluded from reconfirmation. Already approved chords, Korean wording/rows,86 confirmed events and approved curve classes are not reopened. No new owner decisions are collected during plan preparation.

## Validation and outputs

Unchanged V3 guards pass source-versus-corrected-source, source→A/G in memory and serialized, and previous-target versus corrected-target at zero shift. These establish transposition/representation consistency at37 measures,169 events and24 chords; they do not establish source recognition completeness. Dedicated checks additionally preserve all tie/slur relationships except4867, lyric signatures, repeat notation, XML extension states and source content elements.

Targeted validation: **624 passed,1 skipped**, including12 new synthetic controls. The existing skip is MuseScore not installed (`test_omr_v3_gate.py:190`); no new skips or integrity waiver. Full Acceptance is not run. Synthetic negatives reject wrong part/measure, missing/incorrect roles, mismatched numbers and multiple candidate spans before mutation. Source-region linking controls reject nearby glyphs and ambiguous matches. Formatting and `git diff --check` pass. [Validation metadata](V4_GT17D_VALIDATION.json) binds the actual outputs and run results.

Final artifacts: `/private/tmp/capomatic-v4-gt17d/gt17d-delivery-output/`:

- `owner-approved-4867-correction.json`.
- `corrected-source.musicxml`, `A-corrected.musicxml`, `G-corrected.musicxml`.
- `before-after-semantic-diff.json`, `semantic-validation.json`, `preservation-verification.json`.
- `remaining-review-plan.json`, `owner-review-summary.md`.
- `A-full-score-unchanged.png`, `G-full-score-unchanged.png`, `output-freeze.json`.

```bash
cd /private/tmp/capomatic-v4-gt17d
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt17d_owner_correction --output /private/tmp/FRESH-GT17D-OUTPUT
/private/tmp/capomatic-v4-venv/bin/python -m pytest tests/test_v4_ground_truth_*.py tests/test_v4_paired_ground_truth_01.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py tests/test_omr_v4_integrity.py -q -ra
git diff --check
```

The destination must be fresh. Existing GT-17B owner output `/private/tmp/capomatic-v4-gt17b-owner-output/final-v2`, GT-17C `/private/tmp/capomatic-v4-gt17c/gt17c-frozen-output`, original source `/private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output/predictions/baseline-exec/source/`, `/private/tmp/capomatic-v4-gt16b/gt16b-final-output`, `/private/tmp/capomatic-v4-gt16c/gt16c-final-output`, `/private/tmp/capomatic-v4-gt17/gt17-final-output` and `/private/tmp/capomatic-v4-gt17b/gt17b-final-output` are required; this is local evidence-linked tooling, not a portable archive. No original or historical file is rewritten. Copyrighted PNGs/MusicXML/generated evidence stay untracked. Only research source, tests and reports are committed.

The 4867 mapping is uniquely resolved; no correction is blocked. Remaining source classifications, onset/continuation associations, playback, XML extenders and optical quality remain separate open work. No original PDF/raster changes, ink removal, lyric-pixel composition, protection-mask changes, production/API/frontend changes, merge or deployment occurred. Stop after this scoped correction and owner-review plan.
