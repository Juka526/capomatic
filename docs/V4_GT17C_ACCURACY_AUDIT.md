# GT-17C — consolidated accuracy and evidence audit

**The audit is complete; source accuracy closure is waiting for owner decisions.** No new source approval, score correction or rendering was performed. The 37-measure coverage matrix preserves the confirmed scope and focuses the review on 83 provisional event cores, 79 lyric-onset associations, 20 continuation candidates, 28 raw SIG cases and one full-playback decision. These are overlapping review fields, not an accuracy denominator.

The concrete new finding is **raw curve 4867**: the original source image looks like part of the Korean syllable ‘되’, the renderer withholds it, but inherited MusicXML still serializes it as an m21 onset 3→13/4 slur. Classification/removal is not authorized by this audit. Two event reviews and the corresponding SIG case report the same disagreement, not three unrelated errors.

## Revision, inputs and confirmed boundary

Start: `ff4dd9dbb12a21807ba3b3672eac5b519ebbc5f3`. Branch: `experiment/v4-gt17c-accuracy-audit`. Worktree: `/private/tmp/capomatic-v4-gt17c`. The containing commit is the implementation revision; delivery supplies its SHA.

Understood as: audit remaining source evidence and prepare a focused delta review, without changing predictions or treating algorithm agreement as owner approval.

The audit reads the original Bb page2 raster and persisted original-side OMR graph. No A/G reference pages, OCR, Audiveris or production runtime were invoked. Historical target MusicXML/masks are comparison objects, never source truth.

| Original input | SHA-256 |
|---|---|
| source.png | `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de` |
| recognized.omr | `857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638` |
| visual-graph.json | `f8725c39beaaecc877ccf48b803b79a419c2d6e60aa73bc9428a39de11596508` |

GT-17B original output is `/private/tmp/capomatic-v4-gt17b/gt17b-final-output`; owner-integration output is `/private/tmp/capomatic-v4-gt17b-owner-output/final-v2`. Their full file snapshots, prediction manifests, owner validation hashes and original packet freeze are checked. Every reused packet crop is compared byte-for-byte against its original raster rectangle. GT-16B/16C/17 bindings and file snapshots are preserved. The source graph, all masks and owner interpretation records stay unchanged.

No duplicate approval is requested for the existing 86 event cores, 24 chords, 167 syllable wordings/row assignments, 88 exact lyric onsets, 30 marks, three corrected ties or the m31 slur. GT-16C remains an approved experimental layout only. Independent human/musician ground truth and new GT-17C submissions both remain **0**.

## Audit results

| Remaining scope | PASS_CANDIDATE | DISAGREEMENT | UNRESOLVED |
|---|---:|---:|---:|
| 83 music events including attachments | 81 | 2 | 0 |
| 79 exact lyric-onset candidates | 79 | 0 | 0 |
| 20 continuation candidates | 19 | 0 | 1 |
| 28 raw SIG cases | 0 | 1 | 27 |
| Complete playback traversal | 0 | 0 | 1 |

PASS_CANDIDATE means an agent source review and specified consistency checks found no conflict. It is not OWNER_VERIFIED_SOURCE. DISAGREEMENT identifies a recorded inconsistency needing review; it is not an independently proven musical error. UNRESOLVED retains insufficient or interpretation-dependent evidence. None of these states changes the owner's approved inventory.

### Event audit

Original source systems6–9 cover m20–24 /25–29 /30–33 /34–37, with30 /17 /22 /14 recognized events. Agent inspection of their native source images observes those candidate note/rest counts. All83 pitch/duration cores agree with the persisted staff positions, treble/Bb key context, raw notehead/rest shapes and typed stem/beam/flag/augmentation lineage. Onsets are checked against cumulative durations in the raw glyph sequence, with4 quarterLength units per measure and the preserved single voice. A/G MusicXML is checked for the same onsets/durations and the requested −1/−3-semitone pitches.

Each review retains the exact original Inter ID/bbox, raw event record, written pitch, accidental context, original relations, typed duration support, source window hash and target semantics. The inventory's original event IDs can contain zero-based OMR measure indices; **printed `measure` is the review address**. Onset0 starts each printed measure; duration/onset units are quarter notes, so13/4=3.25. Coordinates are original x-right/y-down pixels with right/bottom-exclusive bboxes.

The two attachment disagreements are m21 C5 onset3 (`sheet#1:2143`) and Bb4 onset13/4 (`sheet#1:2191`). Their note/rest cores still pass. Raw curve `sheet#1:4867`, below the staff inside the ‘되’ region, links those heads and persists as an XML slur. Its renderer withholding and source glyph-stroke candidate contradict treating the serialized attachment as settled. No pitch change or automatic slur deletion is proposed as an approved correction. The owner is asked to classify that exact object; previously approved m31's slur is not asked again.

Recognized-glyph agreement does not prove all printed events were recognized. All37 matrix rows retain an unexcluded missing-source possibility and no independent denominator. No specific missing note is invented from an empty region or target image.

### Lyrics and continuations

All79 onset candidates were compared with the entire original source rows, in printed order, preserving the approved wording/row distinctions. Each record includes source window, source head/event ID, candidate onset and horizontal relation. The original50px windows were centered on proposed notes; **their horizontal bounds are tautological and not independent evidence of the association**. The pass is a review candidate, not a geometry-derived claim of lyrical truth. No words are copied from target previews or between rows.

Nineteen continuation candidates visually match a same-row held-syllable candidate. m28 upper ‘곳’ remains unresolved: printed-order m27 contains ‘로’, but the second ending may bypass that passage. The audit neither replaces ‘곳’ with ‘로’ nor assigns playback lineage by nearest preceding text. All20 source stroke/onset/row records remain unapproved. Approved30 earlier marks are not reopened.

### Raw SIG classification proposals

Agent source-only inspection proposes:

- 19 lyric-continuation stroke candidates;
- 7 Korean glyph-stroke candidates:5660 ‘곳’,5896 ‘시’,5948 ‘씀’,6127 ‘한’,6150 ‘씀’,6189 ‘으’,4867 ‘되’;
- 2 ending-number punctuation candidates:6184 ‘1.’ and6198 ‘2.’.

The table's one SIG DISAGREEMENT is4867's existing XML/rendering inconsistency; its actual source classification still requires approval. All28 original object records, source bboxes and relations remain intact. None is automatically discarded or promoted to an articulation/lyric classification. The ten previously withheld SIG objects are included in these28; do not add them as a separate workload. A raw-object question asks how that object relates to existing approved content, not duplicate confirmation of an already approved syllable or extender.

## Repeats and MusicXML

Original-side XML and visual evidence preserve forward repeats at1/20/30, backward repeats at8/27/37, first endings8,15–16,26–27 and second endings9,17,28. Visible locations already approved by the owner are not reopened. The first-ending15–16 /second-ending17 relationship lacks an explicit backward repeat at16 in the source image and barline records. The complete performance traversal, counts/exits and m28 held-syllable ancestry are not certified. `repeat-playback-review.json` requests a full traversal or explicit deferral and leaves `expanded_playback_sequence: null`; no repeat expander is run.

The sound `<tie>` and visual `<tied>` records are compared directly, separately from music21's reconstructed objects. They agree in source and both targets. Three approved new ties and m31's unequal-pitch slur retain precise endpoint lineage after serialization. Agreement does not validate source correctness; the original4867 slur remains a separate known issue. MusicXML distinguishes sound ties from notational ties. [W3C tie reference](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/tie/)

**Source/A/G files each contain0 lyric `<extend>` records.** Visual50 continuation marks therefore do not establish XML continuation completeness. A research-only extractor tests explicit start/continue/stop, legacy omitted-type handling and rejection of invalid states. It does not generate or change XML. A future serializer needs approved row, syllable, start/stop event and repeat-dependent lineage, plus independent roundtrip tests; it cannot turn each drawn dash into an extension event. [W3C extend reference](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/extend/)

Repeat notation and playback remain separate; MusicXML's repeat attributes cannot supply absent source/owner decisions. [W3C repeat reference](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/repeat/)

## Focused review materials

Output: `/private/tmp/capomatic-v4-gt17c/gt17c-frozen-output/`.

Start with `owner-review-guide.md`, `owner-approval-checklist.json` and `source-review-delta-sheet.png`. There are **211 field-review entries grouped into26 printed measures**. They overlap: two event entries and4867 refer to the same attachment problem; raw marks can overlap already approved visual content.211 is not the number of independent musical errors.

The source-only sheet reuses the18 original GT-17B measure crops and source-derived context only for earlier unresolved objects/playback. New native object crops are created only where the old packet lacks them. Brown event boxes/Inter labels and magenta raw-object boxes are annotations on a diagnostic copy, not changes to native source crops or ink ownership. The frozen original image/crop references remain available without overlays. No new full-page source packet or target score preview is copied into the owner materials.

The checklist provides CONFIRM /CORRECT with exact correction /UNCERTAIN, source IDs and coordinates. Every owner answer is blank. Corrections to a candidate attachment must not be interpreted as edits to an already approved lyric string. Each event checklist explicitly requests note/rest identity and written pitch, onset, duration, voice and unapproved stem/beam/flag/attachment fields; already approved curve classes are excluded. The only new owner decisions requested are remaining event fields, exact79 onset associations,20 continuation lineages,28 raw-object interpretations and full playback/deferral. Approved chords, text wording, existing approved ties and visible repeat locations are excluded from reconfirmation. Prioritize4867, then m28/playback, then the other per-measure fields. A partial reply may name case IDs and confirmed/corrected fields; every omitted field stays pending. For playback, reply `DEFER` or an explicit sequence of printed measure ranges with pass numbers; no example traversal is prefilled.

Required outputs are `accuracy-audit-matrix.json`, `provisional-event-review.json`, `lyric-onset-review.json`, `continuation-review.json`, `unresolved-sig-review.json`, `repeat-playback-review.json`, `source-review-delta-sheet.png` and `owner-approval-checklist.json`. Companions include `musicxml-semantic-audit.json`, `frozen-render-validation.json`, `preservation-verification.json`, `validation-summary.json`, the source-object detail directory and `audit-freeze.json`.

## Validation and limits

Unchanged V3 guards pass for source→A/G at37 measures,169 events and24 harmonies. Target tests cover all relevant historical rendering regressions, V3 music/gate guards and V4 integrity, plus20 new synthetic controls. **612 passed,1 skipped**, including all20 new controls, are recorded in [validation metadata](V4_GT17C_VALIDATION.json). No new skip is accepted; the existing MuseScore-not-installed test is reported separately. Full Acceptance is not run.

Fresh analysis recomputes67 notehead bbox anchors per target from frozen component tiles, maximum0.5px per axis; lyric/music and lyric/lyric contacts are0; stem/beam/flag connection failures and viewport clipping are0 in the four audited systems. The four corrected curves are recomputed as temporary analysis masks and equal the frozen masks exactly, with no unexpected contacts. Intended staff/barline contacts are retained. First-five-system safety is preserved by unchanged hashes and prior reports, not claimed as a newly independent recognition or complete rerun of every earlier collision test.

Agent visual inspection confirms readable native source context and concrete boxed delta regions; the long sheet requires scrolling/native zoom. This is owner-review readiness, not independent optical validation or a new score-quality pass. GT-17B's NEEDS_REFINEMENT visual verdict remains unchanged.

Reproduction:

```bash
cd /private/tmp/capomatic-v4-gt17c
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt17c_accuracy_audit --output /private/tmp/FRESH-GT17C-AUDIT
/private/tmp/capomatic-v4-venv/bin/python -m pytest tests/test_v4_ground_truth_*.py tests/test_v4_paired_ground_truth_01.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py tests/test_omr_v4_integrity.py -q -ra
git diff --check
```

The output directory must not exist. Original source inputs live under `/private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output/predictions/baseline-exec/source/`; the existing `/private/tmp/capomatic-v4-gt16b/gt16b-final-output`, `/private/tmp/capomatic-v4-gt16c/gt16c-final-output`, `/private/tmp/capomatic-v4-gt17/gt17-final-output` and GT-17B directories above are required. The script fails closed on mismatched hashes/crop bytes. This is a local evidence-linked audit, not a self-contained portable archive.

Only research code, tests and reports are committed. Copyrighted crops, source images and diagnostic JSON remain untracked. No original PDF/raster editing, ink removal, protection-mask change, owner-label promotion, production/API/frontend modification, merge or deployment occurred. Stop at the owner approval boundary; do not automatically apply the suggested classifications or generate corrected scores.
