# GT-14D — Confirmed lyric continuation rendering

GT-14D adds the three newly owner-approved continuation marks to the frozen GT-14B A/G standalone canvases. The second-system inventory now has **6 owner-confirmed marks rendered**. The 13 note/rest events, 3 chords, 14 Korean syllables, existing ties, lyric baselines and earlier marks remain unchanged.

Base: `3df64a6e7b3eed080fad7ebb8301f34f7b658c84`. Branch: `experiment/v4-gt14d-confirmed-extenders`. Worktree: `/private/tmp/capomatic-v4-gt14d`. Final revision is the commit containing this report, available with `git rev-parse HEAD` on this branch.

Understood as: apply the explicit owner approval in a new interpretation layer, reuse validated GT-14B stroke geometry and frozen canvases, and add exactly three marks. No source-image replacement or independent completeness claim is authorized.

## Approval and source provenance

The exact user Markdown message, retained as UTF-8 with a terminal newline, is [GT14D_OWNER_APPROVAL.txt](evidence/GT14D_OWNER_APPROVAL.txt). [GT14D_OWNER_BINDING.json](evidence/GT14D_OWNER_BINDING.json) binds its SHA-256 to every file in the frozen GT-14C final packet, including the source review sheet, native crops, inventory, unanswered checklist, audit freeze and post-audit verification. It names exactly the three approved case IDs. There is no invented signature, reviewer identity or timestamp.

Classification: **OWNER_VERIFIED_SOURCE**, **NOT_INDEPENDENT_GROUND_TRUTH**. Independent labels collected: **0**. The owner approved the source interpretations and authorized this experimental rendering; the newly generated PNGs have not been owner-accepted or independently reviewed. The original GT-14C records remain AGENT_VISUAL_CANDIDATE with null responses; they are preserved as historical observations. `owner-confirmed-interpretation-layer.json` separately records the new confirmation and its message hash.

Source: original Bb PDF page 2, second system, printed measures 5–8. Original raster is 2520×3564 RGB, SHA-256 `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`. The original OMR/graph are verified through the inherited GT-14B evidence binding. No A/G reference pixels or content enter this rendering.

| New approved ID | Measure/row | Confirmed association | Source bbox | Tie context |
|---|---|---|---|---|
| GT14C-m5-upper | m5 upper | 곳 held from m4 onset 3.75 | [298,942,335,947) | Bb3 START → Bb3 whole-note STOP, 4818/4798 |
| GT14C-m6-lower | m6 lower | 운 held from onset 2.75 | [1331,987,1367,992) | C4 at onset 3 STOP, curve 4784 |
| GT14C-m7-lower | m7 lower | 길 held from m6 onset 3.75 | [1621,987,1657,992) | Bb3 whole-note STOP, curve 4772 |

The source bboxes are the original GT-14C L<127 dark-support measurements, not claims of exact antialias extent or source-ink ownership. All row, syllable, event and tie context is rechecked against the source graph and frozen owner-augmented MusicXML before rendering.

The three earlier GT-14B extenders remain byte-identical: lower m5 는 (5686), upper m6 원 (5699), upper m7 네 (5762). Original OMR classifications and relation XML remain unchanged. Object 5747 remains interpreted as part of the existing upper 하 at m6 onset 3.25; it does not produce a new syllable, fermata or separate source-stroke copy.

## Reused placement contract

[GT14D protocol](V4_GT14D_PROTOCOL.json) was saved before the target render. The existing GT-14B `extender` helper draws a new 2px horizontal stroke with the measured source x interval and width. Top y is `floor((source_top + source_bottom - 1)/2) + frozen_row_dy`. Existing row displacement is A **0px**, G **8px**; the 45px upper/lower row separation is retained. No layout search, alternate baseline or threshold change was needed.

| Mark | A rendered bounds | G rendered bounds | Width |
|---|---|---|---:|
| m5 upper 곳 | [298,944,335,946) | [298,952,335,954) | 37px |
| m6 lower 운 | [1331,989,1367,991) | [1331,997,1367,999) | 36px |
| m7 lower 길 | [1621,989,1657,991) | [1621,997,1657,999) | 36px |

Bounds use page pixel edges, right/bottom exclusive. These odd-height source boxes yield a **+0.5px** pixel-center difference under the existing two-pixel raster convention; this is measured rather than corrected with a new offset. The new lines align with the established paired row phases. They are newly typeset straight strokes, not original-pixel glyph replicas. Notehead geometry is never rerasterized; the unchanged inherited maximum per-axis anchor residual remains **0.5px**.

Semantic attachment here means a continuation mark at the confirmed held-note position linked to its previous syllable, not a line physically touching that syllable. Three additions total **218 alpha pixels per target canvas**, with no duplicate syllable or old extender. New continuation interpretation is recorded in diagnostic JSON; MusicXML `<extend>` export was not implemented.

## Actual alpha validation

All nonzero alpha pixels count, including faint antialias coverage. Existing text consists of the 14 syllable masks and the 3 prior extender masks. Remaining frozen canvas ink is treated as fixed notation/context for collision tests. No original source mask is edited or subtracted; this set separation is diagnostic only.

| Measurement | A major (−1 semitone) | G major (−3 semitones) |
|---|---:|---:|
| Confirmed music events retained | 13 | 13 |
| Chords retained | 3 | 3 |
| Korean syllables retained | 14 | 14 |
| Previous / newly added / total extenders | 3 / 3 / 6 | 3 / 3 / 6 |
| New extender/music contacts | 0 | 0 |
| New extender/old lyric or extender contacts | 0 | 0 |
| All lyric/music contacts | 0 | 0 |
| All text-component contact pairs | 0 | 0 |
| Minimum new-extender to existing ink-center distance | 18px | 17px |
| Minimum all-lyrics to fixed ink-center distance | 3px | 2px |
| Clipping | 0 | 0 |
| Extra Korean syllables / musical articulations | 0 / 0 | 0 / 0 |

All original nonzero canvas alpha values remain exact, and every pixel outside the three added masks remains bitwise unchanged. All six extender components have intact two-pixel strokes at the recorded widths. No collision rule, baseline or music-event geometry was relaxed. These distances are Euclidean pixel-center measurements; a zero-contact result is not professional engraving certification.

## Actual visual outputs and completion levels

Untracked output directory: `/private/tmp/capomatic-v4-gt14d/gt14d-output/`.

- `predicted-a.png`
- `predicted-g.png`
- `comparison-contact-sheet.png` — unchanged original Bb crop above the new A/G standalone layers
- `A-combined-alpha.png`, `G-combined-alpha.png` and the six new target-specific component masks
- `owner-confirmed-interpretation-layer.json`, `lyric-extender-validation.json`, `semantic-integrity.json`
- `input-freeze.json`, `prediction-freeze.json`, `visual-inspection-report.json`, `preservation-verification.json`, `final-validation.json`

The prediction freeze was written before actual PNG inspection. The individual A and G images and contact sheet were opened. Inspection criteria: all six marks in their intended rows, no duplicate 하, retained readable notation and lyrics, no visible new overlap or clipping, and developer-only incomplete warnings. Both targets meet those experimental criteria. G's low-register ledger/tie area remains dense; this unchanged area warrants musician review.

Separate outcomes:

- **SOURCE_VERIFICATION:** the listed events/chords/syllables and six inventoried marks are OWNER_VERIFIED_SOURCE. Independent whole-source recognition completeness remains UNVERIFIED.
- **RENDERING_COMPLETENESS:** ALL_SIX_INVENTORIED_CONTINUATION_MARKS_RENDERED; prior content is preserved. This does not establish full-score reconstruction or MusicXML extender-export completeness.
- **VISUAL_QUALITY:** ACCEPTABLE_FOR_EXPERIMENT_WITH_LIMITATIONS, based on agent inspection only, not independent optical or musician validation.
- Overall: **SCOPED_CONTINUATION_RENDER_COMPLETE_WITH_LIMITATIONS**; all images remain labeled INCOMPLETE / NOT FOR PERFORMANCE OR PRINTING.

## Tests and preservation

```bash
/private/tmp/capomatic-v4-venv/bin/python -m pytest \
  tests/test_v4_ground_truth_*.py tests/test_v4_paired_ground_truth_01.py \
  tests/test_omr_v3_music.py tests/test_omr_v3_gate.py tests/test_omr_v4_integrity.py -q
```

Result: **427 passed, 1 skipped**, including 13 new tests. The existing skipped case requires external MuseScore. New tests cover immutable approval overlays, source-packet/message hash mismatch, duplicate/missing case rejection, rejection of independent/ink-removal scope, deterministic addition-only masks, faint alpha collision rejection and reuse of the half-pixel phase for odd-height source boxes.

Unchanged full V3 semantic guards pass for source roundtrip, A/G in-memory transposition and frozen serialized targets. Exact event, lyric and tie signatures agree with the frozen source/targets; durations, voices, order and pitches are preserved. These are pipeline consistency checks, not recognition ground truth.

The source, GT-12 prediction freeze, complete GT-14A/B/C output directories and recorded upstream artifact bindings are hash-verified unchanged. In particular, no GT-14B prediction or individual music/lyric/extender mask was regenerated. Only the new GT-14D canvases receive three added masks. `git diff --check` passes. Large raster artifacts and copyrighted score pages are not committed.

Validation-design limitation: the renderer and mask measurements share an implementation, so automated checks establish engineering self-consistency. Owner approval is disclosed candidate confirmation, not blind independent annotation. Source-only independent annotation and a separate musician/optical review are the corresponding independent checks; neither is claimed here.

Remaining work is independent visual/musical review, a separately scoped continuation export contract if MusicXML export is required, and verification of the rest of the score before full-score claims. Original-ink removal/composition remains subject to its separate unchanged ownership gates.

No original PDF/raster, protection mask, ownership/integrity rule, production V1/V3 module or API/frontend was changed. No source ink removal, original lyric-pixel composition, merge or deployment occurred.

A fresh-context report review checked evidence/readiness wording only. Its substantive recommendation was applied: rendering completeness is stated for the six continuation marks, with prior content preserved, rather than newly certifying all inherited notation. It supplied no source labels or optical validation. Historical pending GT-14C records and current approved GT-14D interpretations were checked for consistency without rewriting historical evidence.
