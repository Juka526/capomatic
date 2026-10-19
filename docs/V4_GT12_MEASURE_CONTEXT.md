# GT-12: owner-verified standalone measure context

**GT12_STANDALONE_CONTEXT_RENDERED_WITH_LIMITATIONS.** Actual A/G PNGs now include the owner-confirmed four music events, chord and both Korean lyric rows on separate white experimental canvases. They do not replace source ink or preserve original lyric pixels.

| Evidence / completion level | Final result |
|---|---|
| SOURCE_RECOGNITION_COMPLETENESS | INCOMPLETE for raw OMR: the F chord and six lyric items were missing |
| OWNER_VERIFIED_SOURCE_CONTENT | COMPLETE within the owner's confirmed printed-measure scope; not independent ground truth |
| RENDERING_COMPLETENESS | COMPLETE for that contextual measure scope: 4 music events, 1 chord, 6 lyric syllables per target |
| VISUAL_QUALITY | ACCEPTABLE_FOR_EXPERIMENT, from agent inspection of actual PNGs; not independent optical validation |

## Revision and source identity

Original GT-12 base: `9d83c868b350b4435a8d775be655e0b23fc6cedd` (GT-11). This continuation starts at `30a32adfed3cbe043fa4a0759a09abfb06ffd30b`. Branch: `experiment/v4-gt12-measure-context`; worktree: `/private/tmp/capomatic-v4-gt12`. The commit containing this report is delivered with its immutable SHA, rather than embedding a self-referential final hash.

The review scope is fixed to **Bb source PDF page 2, printed measure 3**. Targets remain A major (-1) and G major (-3). No target reference pages, new OCR/Audiveris recognition or source repairs were used. Original raster: 2520×3564 RGB, SHA-256 `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`.

The original-resolution source crop is [1300,330,1860,720), 560×390 pixels, containing both complete visible lyric rows and neighboring context. Page coordinates equal crop-local coordinates plus (1300,330). The source review sheet adds an 82px header outside the unchanged crop. Its SHA-256 remains `3ff4e49da99865ee93dcd1bea483d267cdfedc0377ef7bb84673ef78943e2ccf`. All frozen GT-11 artifacts remain unchanged.

## Source verification and historical stages

The first GT-12 preparation correctly returned BLOCKED. One owner candidate reply explicitly declined visual confirmation. A subsequent submitted review was classified ASSISTANT_VISUAL_REVIEW, NOT_INDEPENDENT_GROUND_TRUTH, and was also kept pending. Neither was promoted into source verification.

The owner then explicitly stated that they directly compared and confirmed the entire checklist, including notes/rhythm, F major and both lyric rows with their note associations. That actual reply is retained verbatim in untracked `confirmed-context/owner-visual-confirmation.txt`, bound by SHA in `confirmed-context/confirmed-source.json` and the prediction freeze. Its classification is **OWNER_VERIFIED_SOURCE**, not independent human ground truth. Actual independent reference labels remain 0.

Every prior GT-12 artifact was archived byte-for-byte before superseding current metadata, under `/private/tmp/capomatic-v4-gt12/gt12-output-pre-confirmed-context/`. Earlier source-only and pre-candidate packets remain in their existing directories. The old candidate reply, source crop and source review image retain their original bytes and hashes. Historical BLOCKED reports remain available in that archive; they describe the earlier state, not the final result.

| Source event | Onset / duration, quarterLength | Owner-confirmed content | Rendering |
|---|---|---|---|
| `p1:m2:r0` | 0 / 1 | Quarter rest, no syllable | Quarter-rest glyph |
| `p1:m2:n0` | 1 / 1 | Bb3; upper 주, lower 사 | A3 / G3, stems and ledgers |
| `p1:m2:n1` | 2 / 1 | C4; upper 님, lower 막 | B3 / A3, stems and ledgers |
| `p1:m2:n2` | 3 / 1 | F4; upper 의, lower 의 | E4 / D4, stems |

Absolute source pitches rely on existing source treble-clef/Bb-key context, which is outside this cropped image. Timing follows the frozen OMR and the owner's explicit confirmation; four quarterLength units are not an independent optical certification of a printed time signature.

The owner confirmed the reviewed absence of additional accidental, tie, slur, beam, flag or articulation in this measure. Neighboring notation is shown only in the original source context panel and is excluded from targets. The F chord is major with no suffix, slash bass or alteration. It belongs near the measure beginning, not at the first pitched note. The original rest has no associated syllable in either row.

## Research-only augmented semantics

Raw OMR remains unchanged: four selected-measure music events, zero harmonies and zero MusicXML lyric items. The experiment adds one owner-confirmed F harmony at onset 0 and six numbered lyric items to an in-memory research copy, then writes a separately named `owner-augmented-source.musicxml`. This is a disclosed human-supported augmentation, not improved recognition or a repair of GT-01/11 predictions.

Unchanged V3 `transpose_score` and `music_guard.validate` handle the augmented source. F→E and F→D use the existing V1/V3 chord path, preserving major quality, absence of alterations and absence of slash bass. Source/target harmony offset remains 0. Visual chord placement is separately retained from the source image; it is never inferred from the first pitched note's x position.

Full V3 guards pass for the augmented source write/read and for A/G both in memory and after serialization: 37/37 measures, 169/169 music events, 8/8 harmonies, no issues. The earlier unaugmented GT-11 had 7 harmonies; these denominators are deliberately separate. Additional checks preserve both lyric numbers/texts, their event associations, rest silence, source ordering, durations and voices. Target music-event signatures exactly match frozen GT-11.

## Frozen rendering contract

[The rendering protocol](V4_GT12_RENDER_PROTOCOL.json) was written before the actual visual run. Only confirmed source content and source-only display-alignment measurements enter it. No reference-page comparison or tuning was performed.

The renderer reuses GT-11's exact full-resolution producer alpha masks: calibrated heads/rests, stems, ledgers, staff polylines and original measure boundaries. It does not reimplement note rendering or modify pitch geometry. The original 0.5px per-axis notehead raster-bbox criterion remains unchanged. Physical detected centers, semantic source/target staff coordinates and rendered bitmap anchors remain distinct.

Text is newly typeset using existing local fonts: FreeSerif size 40 for chords and macOS AppleGothic size 44 for Korean. Font file hashes are recorded in `rendering-metrics.json`. No fonts were downloaded or bundled; the local macOS font dependency means this tool does not claim portable identical rendering across machines.

For display alignment only, fixed source windows are measured with L<127: chord [1390,350,1450,414), upper row [1480,588,1730,632), lower row [1480,635,1730,688). These are not text-ownership masks, confirmed ink extents or removal evidence. They do not change any protection mask. Measured source chord bbox is [1406,372,1426,399); its ink left/top (1406,372) is preserved for both targets. E has measured ink width 24px and advance 24px; D has ink width 28px and advance 29px. Actual font widths are measured, not inferred from character count.

The measured source row bottoms are 628 and 674. Fixed-phase GT-05 bitmap registration aligns each new syllable's ink-center x with the corresponding original note x. Common new baselines are 624 and 670. Both rows remain associated with the same three pitched events; no syllable is attached to the rest. This is retypesetting with a visibly different font, not original-pixel fidelity.

## Actual outputs and measured results

Untracked output directory: `/private/tmp/capomatic-v4-gt12/gt12-output/`.

- `original-bb.png` and `source-review-sheet.png`: unchanged source review images.
- `predicted-a.png`, `predicted-g.png`: actual standalone newly rendered music/chord/lyric canvases.
- `comparison-contact-sheet.png`: frozen original source context beside both predictions.
- `comparison-contact-sheet-clarified.png`: post-freeze diagnostic derivative clarifying only the source-panel footer; all notation and source-crop pixels unchanged.
- `source-checklist.json`, `chord-audit.json`, `lyric-audit.json`, `completeness-report.json`: current owner-confirmed content and recognized-versus-added provenance.
- `confirmed-context/`: confirmation, augmented/target MusicXML, full semantic guards and exact text/music alpha layers.
- `confirmed-context/source-clef-key-context.png`: additional unchanged source-only crop [130,330,1860,720) for subsequent musician review of the clef/key context outside the measure crop.
- `rendering-metrics.json`, `confirmed-context/prediction-freeze.json`: measured geometry and hashes frozen before image inspection.
- `visual-inspection-report.json`, `final-validation-summary.json`: separate post-freeze review and authoritative final decisions. Pre-review `validation-summary.json` remains unchanged after freeze and intentionally says pending visual review.

| Metric | A | G |
|---|---:|---:|
| Music events rendered | 4 | 4 |
| Transposed chord | E | D |
| Newly typeset lyric syllables | 6, two rows | 6, two rows |
| Maximum notehead raster residual per axis | 0.5px | 0.5px |
| Music alpha compared with GT-11 | Unchanged | Unchanged |
| Staff / measure geometry deviation | 0px | 0px |
| New text/music and inter-text alpha collision pairs | 0 | 0 |
| Clipped components | 0 | 0 |
| Missing/duplicated confirmed music events | 0 / 0 | 0 / 0 |

Measured run time was 2.18 seconds locally, excluding test execution and later visual inspection. Memory was not profiled. Music component connections inherit the saved GT-11 checks; text collision checks use actual nonzero-alpha pixels of every new syllable/chord and the exact music union. Bounding-box overlap is not substituted for ink contact.

The agent opened the actual contact sheet and both individual predictions after freeze. Chords appear near the original measure beginning, both Korean rows are readable, note/lyric order is coherent, and no music/text contact or new notation clipping is visible. **VISUAL_QUALITY=ACCEPTABLE_FOR_EXPERIMENT** is an agent judgment, not independent optical validation. Optical typography and professional engraving quality remain unvalidated.

These are contextual mid-system excerpts: treble-clef and key context are supplied by captions, not engraved glyphs. Therefore they are not self-contained performance scores. All panels carry developer-only/no-performance warnings. The frozen comparison source panel used the common footer about newly typeset lyrics; that statement applies only to predictions. A separately hashed post-freeze diagnostic derivative clarifies that footer without changing any source crop or notation pixels. The original frozen comparison remains untouched. No claim of source-pixel replacement or original lyric fidelity follows from either comparison.

## Reproduction and validation

Preparation remains available via `scripts.research.gt12_measure_context`; it never authenticates a candidate or unlocks rendering. For an explicitly confirmed new standalone run, `scripts.research.gt12_render_context` accepts the actual confirmation record, validates its source sheet/checklist hashes and refuses to overwrite predictions. It requires the preserved local GT-01/11 artifacts and fonts. Do not rerun it over this frozen directory.

Targeted regressions: **197 passed, 1 skipped**, with the existing skip requiring external MuseScore. Command:

```sh
python -m pytest tests/test_v4_ground_truth_12_context.py tests/test_v4_ground_truth_12.py tests/test_v4_ground_truth_11.py tests/test_v4_ground_truth_04.py tests/test_v4_ground_truth_05_anchor.py tests/test_v4_ground_truth_06.py tests/test_v4_ground_truth_07_flags.py tests/test_v4_ground_truth_07_flag_contacts.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py -q
```

New tests cover candidate rejection, independent-ground-truth claim rejection, source mismatch, F→E/D full semantics, onset-0 chord versus onset-1 first note, rest/lyric relationships, common baselines, fixed-phase text placement, actual-alpha collisions and source-image immutability. These synthetic tests are not source annotations. Formatting, `git diff --check`, pre-review freeze hashes, prior GT-12 archive and GT-11 historical hashes are checked before commit. No Full Acceptance.

The concrete next step is musician review of this complete owner-supported contextual measure, including chord placement, lyric alignment and typeface quality. Safe old-music removal, production composition, independent whole-score correctness and page expansion remain separate unpassed gates. No V1/V3 production, ownership or integrity rules, protection masks, source PDF/raster, API/frontend, production B2, merge or deployment were changed.
