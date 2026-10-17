# V4 Phase 1.9: symbol ink isolation

This offline gate produces exact-pixel ownership evidence, not an edited score. Starting revision: `b00874aff1ee0883b2a19bd005129aa4ab7c4582`. V1/V3 recognition, ledger repair, transposition and integrity behavior remain unchanged.

## Fixed policy

The analysis raster uses Pillow luminance `L <= 127`, original dimensions, 8-connected components and zero dilation. No rotation, scaling, morphology or staff removal occurs. Parameters were fixed before the one-pass jayu result. Native source mode, dimensions and bytes are bound by the existing raster digest.

The OMR glyph index contains explicit symbol-to-glyph references and glyph run tables. The decoder interprets alternating foreground/background lengths, including an initial zero foreground run, in horizontal or vertical orientation. Empty, malformed, oversized, duplicate or out-of-bounds glyph evidence is rejected. The graph's bounded entity-free XML parser is reused.

A bounding box never establishes ownership. A candidate's explicit glyph pixels must all be actual dark source pixels inside admissible symbol geometry. Its complete source connected component must be accounted for by disjoint glyph assignments in a group established by typed SIG edges. No unexplained component pixels, proximity ownership, component cropping, shared pixels, confidence scores or fuzzy thresholds are allowed. Even related glyphs sharing a pixel are rejected rather than allocated arbitrarily. Open-head white centers are not filled.

Heads require containment or head-stem evidence; stems require head-stem; beams/hooks require beam-stem; flags require flag-stem; dots require augmentation; accidentals require alter-head. Related targets must exist with compatible symbol types. Exact component corroboration is stronger than merely accepting Audiveris glyph attribution, but is not independent proof that Audiveris assigned every semantic label correctly.

Text bounds, structural barlines and unrelated symbol regions are conservative exclusions. This gate does not certify curves, articulations, fermatas, dynamics, pedal, key signatures, clefs, time signatures, bars or text. Those objects remain unowned. Missing text protection bounds fail closed.

## Staff uncertainty and current limit

A fixed 2-pixel-radius corridor follows the original staff polylines. It is an uncertainty exclusion, **not** an assertion that nearby dark pixels are staff ink. Candidate dark pixels inside it are recorded exactly as uncertain overlap runs, with `restore_required=true`, and rejected as `STAFF_OWNERSHIP_UNCLEAR`. This producer does not yet prove crossing topology. It therefore emits no VERIFIED staff-crossing ink. It is intentionally narrower than the eventual topology-aware producer.

Outside the exclusion, proposed glyph pixels are non-staff candidates, still subject to every other check. No staff-line ink is certified or removed. Rejecting an unresolved crossing preserves the ownership contract; it does not demonstrate staff restoration feasibility.

## Evidence and admission

`InkEvidence` and `InkRecord` are frozen. JSON traces each candidate to symbol kind/ID, glyph ID, component IDs, SIG relation IDs, exact canonical horizontal runs, uncertainty overlap runs and raster digest. VERIFIED records alone convert into the unchanged Phase 1.8 `OwnedInk` contract. Digest mismatch is fatal. Component IDs are deterministic within the recorded binary analysis and connectivity policy.

The CLI feeds these records into the existing Phase 1.8 mask planner and asserts that every approved pixel is VERIFIED. Group completeness and target/protection gates remain unchanged. A verified individual symbol does not imply an approvable note or beam group.

`READY_FOR_MASK_REFINEMENT` requires at least one real VERIFIED symbol, fail-closed ownership and the existing outside-mask integrity contract. It does not imply renderer readiness. The real-score integrity check compares the unchanged source copy; synthetic regression tests separately exercise actual inside/outside-mask changes.

## Reproduce without recognition

```sh
python -m scripts.omr_v4.inspect_ink v4-jayu-provenance-diagnostic \
  --out v4-jayu-provenance-diagnostic/ink-isolation
```

The output directory must be new/empty. Artifacts are local and untracked: `ink-evidence.json`, `ink-summary.json`, updated `mask-summary.json`, `verified-ink-mask.png`, `rejected-ink-mask.png`, `staff-overlap-mask.png`, `approved-mask.png` and `ink-ownership-overlay.png`. Rejected rectangles in the overlay are diagnostic windows, never claimed ink. All five input artifact SHA-256 values are checked again after writing.

## Validation scope

Synthetic tests cover filled/open heads, explicit relations for stems/beams/flags/dots/accidentals, staff-crossing rejection with restoration metadata, unrelated merged ink, escaping components, text/barline protection, duplicate ownership, deterministic RLE, horizontal/vertical glyph decoding, malformed runs, complete/incomplete connected beam components and digest mismatch. Existing mask tests cover atomic beam approval and pixel integrity.

The jayu sheet is development evidence, not a holdout or accuracy benchmark. Symbol labels and geometry originate from the same Audiveris graph; component agreement checks raster consistency, not independent musical truth. Future independent pixel annotations are required before making general ownership-accuracy claims. No coverage threshold is selected or tuned on this run.

## One-pass jayu result

Decision: **NEEDS_INK_ISOLATION_FIXES**. Phase 1.10 is not started. The algorithm was not adjusted after this result, and Audiveris was not rerun.

| Symbol type | Candidates | VERIFIED | Rejected |
| --- | ---: | ---: | ---: |
| head | 249 | 0 | 249 |
| stem | 249 | 0 | 249 |
| beam | 115 | 0 | 115 |
| beam-hook | 4 | 0 | 4 |
| flag | 14 | 0 | 14 |
| augmentation-dot | 11 | 0 | 11 |
| alter / accidental | 0 | 0 | 0 |
| **Total** | **642** | **0** | **642** |

Rejection counts overlap: `OTHER` (glyph/source dark-pixel disagreement) 642; `COMPONENT_ESCAPES_WINDOW` 631; `MULTI_OWNER_COMPONENT` 617; `STAFF_OWNERSHIP_UNCLEAR` 569; `AMBIGUOUS_COMPONENT` 22; `RELATION_MISSING` 6. There were zero source text/structural-collision rejection records and zero unsupported-attachment rejection records in this isolation pass; that does not remove the independent planner's conservative collisions or moving attachments. Ownership-collision count 617 is affected candidate symbols, not distinct collision pixels or groups.

No raw glyph assignment could be certified under exact threshold agreement. The source/glyph discrepancy needs separate investigation of raster provenance, Audiveris binarization and exact run-table semantics before changing any isolation rule. It is not evidence that all 642 Audiveris symbols are wrong, and no alignment correction or threshold relaxation was inferred. Shared glyph assignments and staff topology also require explicit reconciliation. Uncertain staff pixels remain unowned.

Injecting the actual VERIFIED set (empty) into the unchanged Phase 1.8 gate gives:

| Metric | Result |
| --- | ---: |
| Matched notes eligible | 249 |
| Atomic components eligible | 41 |
| VERIFIED noteheads / staff-crossing symbols | 0 / 0 |
| Fully verified atomic / beam groups | 0 / 0 |
| Approved / blocked note masks | 0 / 249 |
| Approved / blocked beam groups | 0 / 66 |
| Approved note percentage | 0% |
| Source / target text envelope intersections | 11 / 29 |
| Structural / target collision blocked notes | 104 / 224 |
| Unsupported attached instances / propagated blocked notes | 40 / 151 |
| Cross-system tie segments / blocked notes | 4 / 10 |
| Invalid graph geometry | 0 |

The 1,290 planned staff crossing segments and 238,865 corridor pixels are the existing Phase 1.8 conservative diagnostics, not VERIFIED staff ink or approved restoration pixels. The historical 30 protected-envelope pairs and four physical overlap areas remain protected; isolation does not normalize away any protection.

Source SHA-256 before and after the run: `e53c52dd7c31f0196b7c5a99231afd4f77bc522f8a02483277179a79c84dc0cb`. The native RGB integrity report records zero changed pixels and zero outside-mask changes. All five input artifacts retained their hashes. The only image compositing is a diagnostic annotation overlay; no source pixels were overwritten, erased or replaced.

Validation: `python -m pytest tests/test_omr_v4_*.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py -q` passed 228 tests with one existing environment-dependent skip. `git diff --check` passed. No full acceptance run, independent holdout, renderer, API/frontend/runtime V4 route, V1/V3 runtime change, merge or deployment occurred.

## Review boundaries

The ownership group in the component check is the transitive connected component of supported typed SIG edges. It is not the larger edit-atomic group: that group may additionally require ledgers, curves, unsupported attachments or target safety. Every proposed pixel must satisfy the fixed source-dark predicate, and the union of glyph assignments must exactly account for every touched source component. Any pixel intersection with the conservative protection or unrelated-symbol bounds rejects the candidate. A corridor overlap is any pixel intersection, not necessarily a traversal across a complete line.

A cold-read review identified this distinction between ownership components and edit-atomic groups as necessary for the handoff. The existing `masks.py` remains the canonical OwnedInk admission and pixel-integrity contract; this module supplies evidence and does not replace it. Historical Phase 1.8 statements that no producer existed describe that revision; this phase adds a producer but certifies no real jayu ink yet. The development result is raster-consistency evidence only, not independent symbol-ownership accuracy.
