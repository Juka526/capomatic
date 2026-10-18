# GT-10 owner collision audit

Starting SHA: `3a0f8fd9901e0da89a53f150f51face1378e89e3`.
Branch: `experiment/v4-gt10-owner-collision-audit`.
Worktree: `/private/tmp/capomatic-v4-gt10`.

This is a coordinator-only computational audit of OWNER_REVIEW / NOT_INDEPENDENT_GROUND_TRUTH. No additional annotations are requested or manufactured. The submitted review is bound to SHA-256 `0960de861dc8f74e84c05a0419287e28a01c2818e84fa4bc4af4ba5cc41bb68f`; export modification times are never selection evidence.

## Fixed audit rules

Declared before the real audit run: decode the exact GT09 RLE, verify all five original case-image hashes/dimensions and page-crop pixel equality, retain the union of all submitted labels at each source coordinate. A disagreement is OWNER_CONFLICT, never majority vote or preference for a child/parent case. Coordinates outside the crops are UNMAPPED. TEXT regions remain owner-painted regions, including any background; they are not verified Korean text ink.

Use only frozen alpha masks, unmodified protection rectangles and serialized OMR glyph support. A mask coordinate is occupied when frozen alpha >0, matching the historical prototype measurement. Original dark-pixel support is Pillow L <127, matching the historical descriptive measurement; it is not a segmentation or ownership rule. OMR text and musical support are separately counted and may overlap. Their counts must not be added to owner categories.

GT07B has frozen music-only alpha masks. GT06 persisted only combined notation alpha, including staff and bar scaffolding, not its music-only mask. The historical GT07A audit replayed component masks to recover the GT06 moving-symbol contact set. GT10 must not repeat that replay or rerender old predictions. GT06 exact moving-contact coordinates therefore remain unavailable from its saved masks. Report the measured combined-alpha superset, historical moving totals and mathematically conservative category bounds; never label the superset as the original 1,982/2,026 contacts. Missing per-component masks also prevent an exact head/ledger/stem partition at the 47 flag-prototype coordinates. Recorded geometry can report candidate components only, not invent component ownership.

Source-removal authorization and lyric-preserving composition remain NOT AUTHORIZED independently of any contact characterization. No protection shrinkage, Track A PARTIAL promotion, guard relaxation, original pixel editing, score rendering, API/frontend change, merge or deployment is performed.

## Result

**OWNER_COLLISION_AUDIT_PARTIALLY_RESOLVED.** The computation is finished for the available evidence; individual GT06 moving-contact coordinates and exact per-component masks were not persisted. No new human annotation is needed to reach this audit's conclusions. It neither creates independent labels nor adjudicates conflicting owner observations.

Owner export: `/private/tmp/capomatic-v4-gt09-owner/gt09-output/owner-review-exports/0960de861dc8f74e84c05a0419287e28a01c2818e84fa4bc4af4ba5cc41bb68f.json`, 60,606 original bytes. It matches the user's Downloads submission by SHA. There was one matching export; other/newer exports could not supersede its identity. Five cases are finalized; all RLE intervals, dimensions, coverage and deterministic encoding pass. All source images match the exact GT08 packet and page crops. Raw submission bytes are unchanged.

There are 442,705 crop-pixel observations but only **216,290 unique page coordinates** because the cases overlap. **10,623 unique page coordinates** retain conflicting TEXT/NON_TEXT observations. These are OWNER_CONFLICT, never silently NON_TEXT, TEXT, MIXED or UNKNOWN. The four original categories remain available separately; MIXED, UNKNOWN and unreviewed counts happen to be zero in this submission. Unreviewed page coordinates remain UNMAPPED.

## Owner-region contact counts

| Cohort | Historical moving contact total | Owner TEXT region | Owner NON_TEXT region | Owner MIXED | Owner UNKNOWN | Owner CONFLICT | UNMAPPED | Basis |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| GT06 A | 1,982 | 0 | 1,982 | 0 | 0 | 0 | 0 | Exact aggregate implication from homogeneous combined-mask superset; individual moving coordinates unavailable |
| GT06 G | 2,026 | 0 | 2,026 | 0 | 0 | 0 | 0 | Same implication; individual moving coordinates unavailable |
| GT07B A | 24 | 0 | 0 | 0 | 0 | 24 | 0 | Exact frozen music-only mask intersection |
| GT07B G | 233 | 145 | 0 | 0 | 0 | 88 | 0 | Exact frozen music-only mask intersection |

For GT06 the frozen combined-alpha/protection superset contains **5,128 A / 5,448 G** unique coordinates. Every coordinate in each superset is consistently owner NON_TEXT. The source-inspected, hash-verified GT06 renderer contract (`6f5f191515b7103b9d07e606bb8b4e9b91ecb09ab83c15e58bd44831f02fca31`) defines combined alpha as the maximum union of music, staff and bar masks. Thus moving contacts are a subset of the combined contacts. This implication relies on inspection of that exact frozen source; the helper verifies its hash rather than mechanically proving the renderer’s Python semantics. If a category has `c` of `S` superset coordinates and the historical subset has `N` coordinates, its count is bounded by `[max(0,N-(S-c)), min(N,c)]`. Here those bounds collapse to the table's exact owner aggregates. This is set containment, not recovering missing pixels from geometry or matching a desired total.

GT06 diagnostic images explicitly show the **combined-mask superset**, not a newly invented 1,982/2,026-pixel mask. Required missing resources are `gt06-output/A-music-only-alpha.png` and `G-music-only-alpha.png`, or an equivalently hash-bound exact moving-contact RLE. They are **not listed in the original freeze**; this is non-persistence, not a claim that an existing file was lost. Staff-only subtraction would destroy shared music/staff pixels, so it was not attempted.

## Region, grayscale and OMR support are distinct

| Cohort | Original L <127 support | Original dark inside consistent owner TEXT | OMR text-support candidates | OMR music-support candidates |
| --- | ---: | ---: | ---: | ---: |
| GT06 A historical moving set | 1,543 | 0 by subset implication | 0 | 1,661 |
| GT06 G historical moving set | 556 | 0 by subset implication | 0 | 652 |
| GT07B A exact set | 0 | 0 | 0 | 0 |
| GT07B G exact set | 34 | 34 | 47 | 0 |

GT06 grayscale/music-support values are **read from the hash-bound GT07A prior aggregate audit**, whose replay was verified then. They are not recomputed from an unavailable music-only mask. GT06's prior text-support scope is the audited sentence/descendant words. The present superset has zero overlap with any serialized text glyph in the broader text-kind inventory, also proving zero for its moving subset. Nested sentence/word protection counts are never added together.

For transparency, the newly measured GT06 **supersets** have dark support 3,266 / 2,545 and musical support 2,186 / 1,453 respectively. Those larger values are not substituted for the historical moving-set measurements.

GT07B G's 145 consistent owner-TEXT contacts include **111 coordinates not dark under the fixed <127 measurement**. They are not thereby certified background: this includes possible light antialias pixels and background inside broad owner-painted regions. Owner TEXT-region contact, original dark support and processed OMR text-support contact are different measurements. None is an independently verified lyric-ink ownership mask.

## The 47-coordinate set

All **47 unique GT07B G OMR text-support contacts** are inside protected envelopes and consistently owner TEXT, with **zero overlapping-case disagreement** in that set. Coordinates span x=959–976, y=591–598 (inclusive). **34** have original L <127; **13** do not. Persisted text-support memberships are the lyric-item `sheet#1:4106` and word `sheet#1:4135`, each with the same 47-coordinate set; their union is 47, not 94. No musical-support membership is present at these coordinates.

`gt07b-g-47-contact-details.json` contains each page x/y, all covering case IDs and crop-local x/y, each original owner label, conflict state, original grayscale, text/music-support object IDs and predicted-component diagnostics. Every coordinate is occupied in the frozen music-only union. All lie within the recorded target head bounds; nine also fall in the conservative stem geometry range, and ledger overlap remains a possibility. Exact head/stem/ledger ownership is **UNRESOLVED_COMPONENT_MASK_NOT_PERSISTED**. Recorded component bboxes are not exact masks. No glyphs, stems, ledgers or flags were rerendered to resolve this.

The enlarged image highlights these coordinates with cyan pixel-cell outlines at **16× nearest-neighbor diagnostic zoom**, with page crop bounds in its header. The original image remains unmodified. The contact sheet places original source, owner regions, frozen notation positions, contact coordinates and conflict/unknown/unmapped context in separate annotated panels; it is not a finished or composited score.

## Safety decisions

- **A — Collision risk more precisely characterized:** yes, with GT07B exact sets and GT06 owner aggregates proved by containment. GT06 exact moving-coordinate/support recomputation and component attribution remain limited.
- **B — Safe source music removal:** **NOT AUTHORIZED**. No COMPLETE ink evidence or source-removal gate was established or promoted.
- **C — Lyric-preserving composition:** **NOT AUTHORIZED**. Owner review is not independent ground truth, conflicts remain, and original music-removal evidence is still missing.

All existing protection envelopes remain active, including their parent/child nesting. An owner NON_TEXT observation does not clear an envelope or authorize editing. Frozen V3 full integrity results remain A/G PASS (37 measures, 169 events, 7 harmonies); this run creates no new semantic prediction and does not waive or rerun a failing guard. No architecture winner is selected.

## Reproduction and artifacts

```bash
cd /private/tmp/capomatic-v4-gt10
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt10_owner_collision --out NEW_OUTPUT_DIRECTORY
```

The script refuses existing output directories, historical evidence locations and symlink output paths. It never starts Audiveris, OCR, a renderer or a browser. All PNGs are coordinator-only diagnostic copies; every generated artifact is read-only. Fifty input files are hash-bound and verified again after analysis. The committed GT08 historical binding and original GT06/GT07B complete freezes are also checked. The initial audit artifact set is retained untracked at `gt10-output-initial/`; final `gt10-output/` adds the generic subset aggregate derivation and hash-bound prior summaries without changing collision pixels, owner categories or admission rules.

Final untracked artifacts under `/private/tmp/capomatic-v4-gt10/gt10-output/`:

- `collision-report.json`, `owner-rle-validation.json`, `gt06-contact-analysis.json`, `gt07b-contact-analysis.json`.
- `gt07b-g-47-contact-details.json`, `validation-summary.json`.
- `comparison-contact-sheet.png`, `enlarged-contact-review.png`.
- `gt06-a-diagnostic.png`, `gt06-g-diagnostic.png`, `gt07b-a-diagnostic.png`, `gt07b-g-diagnostic.png`.

No copyrighted image, owner RLE or source submission is committed. The final commit is identified by `git log -1 --format=%H -- docs/V4_GT10_OWNER_COLLISION_AUDIT.md` and the final local validation record. Remaining evidence gaps are persisted GT06 music-only/contact masks, exact component support, unresolved owner overlaps and independent text-extent evidence. None was fabricated or resolved by voting. No additional human annotations were requested before completing this computational audit.

## Final validation

Targeted GT06/GT07A/GT08/GT09/GT10 and unchanged V3 music/gate regressions: **202 passed, 1 skipped** (the existing external MuseScore-dependent test). After the final audited-region identity assertion, the **21 GT10 tests** pass again. Synthetic tests cover all four owner categories and conflicts/UNMAPPED, strict export identity/RLE, SHA rather than newest-file selection, page/crop bounds, nested-envelope union, separate region/dark/OMR measurements, sound subset bounds, missing mask/coordinate identity, non-mutating diagnostic copies, deterministic coordinate details and historical-output path rejection.

All 50 input hashes, both complete prototype freezes and the original user Downloads submission pass the final preservation check. GT07B collision RLE decodes to exactly 24/233 unique coordinates, and the detail set has exactly 47 unique coordinates. No missing/duplicated contact pixels, automatic category substitution or modified protection definitions were found in the exact audit. GT06 moving-coordinate uniqueness cannot be rechecked without its missing mask, and is not claimed. Formatting and `git diff --check` pass. No Full Acceptance, Audiveris, OCR, historical prediction rendering, production changes, merge or deployment occurred.
