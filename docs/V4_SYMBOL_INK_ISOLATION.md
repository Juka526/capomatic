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

## Phase 1.9c: layered source ownership (supersedes old admission)

The original Phase 1.9 implementation and the one-pass 0/642 result above are retained as historical evidence. Its fixed threshold-127, whole-source-component equality, per-symbol disjointness and Inter-bbox clipping assumptions are **superseded**, not silently rewritten. See [the pinned-source forensic findings](V4_INK_PROVENANCE_FORENSICS.md). The old decoder/CLI remain reproducible; the active offline experiment is `scripts.omr_v4.inspect_source_ink`, backed by `backend/omr_v4/source_ink.py`. No V1/V3 runtime or Phase 1.8 planner change is involved.

### Immutable evidence layers

`ProcessedInkSupport` binds symbol/glyph IDs, canonical glyph RLE, typed SIG relation IDs, Inter geometry, actual glyph geometry, page coordinates, OMR SHA-256 and saved BINARY native digest. Every proposed coordinate must be on-page and black in the actual saved binary. This certifies processed support, not original-source ownership. The bundle loader requires the pinned Java build. The CLI additionally requires the existing forensic report to bind the exact source/OMR hashes and successful raster reproduction; it never infers registration from nearest positions.

Heads record `BINARY_TEMPLATE_SELECTED`; beams/hooks `NO_STAFF_DERIVED`; stems `SEED_FILAMENT_OR_COMPOUND`. Flags/dots/accidentals with explicit glyph `SYMBOL` attribution record `SYMBOL_STAGE_ATTRIBUTED_OR_REUSED`, which deliberately does not pretend to know which optional/reused construction branch occurred. Without this attribution they record `UNKNOWN_PROCESSED_PROVENANCE` and fail closed. Exact per-instance construction history is not invented.

`SourceInkOwnership` binds original raster native digest and records core/fringe RLE, raw staff-attributed intersection, unknown crossing RLE, four staff pixel classes, actual native-channel value histograms over the proposed support/fringe, group ID, completeness and blockers. Exact per-coordinate native values are recoverable from the bound original plus RLE; the histogram alone is not claimed to encode spatial values. The original RGB/L/RGBA samples are never transformed for output. Luminance conversion is analysis only, without rescaling. Transparency ambiguity blocks ownership.

`AtomicInkGroup` uses only compatible head-stem, beam-stem, flag-stem, augmentation and alter-head edges. Explicit head-chord containment can resolve a relation endpoint to its contained heads; proximity never establishes membership. A deterministic ID uses the lexicographically first member ID. Group unions contain each pixel once. Related-symbol views may reference the same coordinate, but never assign a shared pixel arbitrarily to head or stem. Any unrelated-group processed/source claim collision rejects the affected group; unrelated fringe claims are refused. Non-candidate glyph overlap remains unresolved and cannot become owned core.

### Fixed source/core/fringe rules, declared before the retry

Let `U` be a group's processed support union. No whole original-source connected component is required or absorbed. Let `B` be the median source luminance in the rectangular annulus with Chebyshev distance 3–5 pixels outside the tight glyph-union bbox. This bbox is a background sampling/exclusion window, never a filled ownership mask. A usable local background requires `B >= 224`.

A non-crossing processed coordinate can be verified source core when its provenance and relationships pass, it avoids all protection/structural/unrelated claims, and `B - L(p) >= 8`. This is a local contrast rule, **not a source gray threshold of 127 or 192**. Gray 200 on a white background passes. Uniform gray 230 with an artificially black processed label does not. Raw channel values are recorded. A source/core contrast uncertainty keeps the group partial; white pixels are never certified merely because processed support says black.

Fringe is at most one nonrecursive 8-neighbor expansion of `U`, within its support-derived bbox expanded by one pixel. It uses the same fixed background contrast 8, must touch `U`, and must avoid protected/structural, foreign-support and unrelated-group claims. Staff-attributed or logical-crossing neighbors are withheld. Contrast 1–7 at the immediate boundary is `UNCERTAIN_ANTIALIAS_BOUNDARY`, not silently ignored as background. A second local inspection shell checks whether any non-background continuation remains beyond the admitted fringe; it is recorded as `UNACCOUNTED_LOCAL_CONTINUATION`, never grown into ownership. No source component is clipped to fabricate completeness.

The rule inspects local topology only. Unknown continuation preserves any independently verified core but blocks COMPLETE. This is intentionally conservative about low-contrast tails and imperfect background estimates. It does not claim independent ground truth for all visible ink merely from agreement with Audiveris.

### Staff crossings and completeness

The former fixed 2px proximity corridor is not an ownership rejection rule. Crossing uncertainty uses exact distance to the original polyline segments, with radius `serialized line thickness / 2 + 0.5 pixel`; it does not flatten slope/curvature. Missing/invalid width or polyline geometry blocks completeness. Explicit serialized staff-glyph pixels are retained separately. Absence from those glyphs never proves that no physical staff line contributes at a crossing.

Each candidate records disjoint contextual classes: `SYMBOL_CORE` (verified non-crossing source pixels), `STAFF_ATTRIBUTED` (nearby explicit staff assignment outside the musical support union, context only), `SHARED_OR_INSEPARABLE` (its support also attributed to staff), and `UNKNOWN` (logical-crossing support without staff attribution). `unknown_crossing` includes both shared/inseparable and unknown cases; all remain RESTORE_REQUIRED/unowned. The separate raw `staff_attributed` field records actual overlap evidence. No staff restoration is performed in 1.9c.

A group with valid non-crossing core plus crossing uncertainty is `VERIFIED_PARTIAL`. A group is `VERIFIED_COMPLETE` only when every member is valid, no uncertain local fringe/tail or unsupported moving attachment remains, no source protection/collision exists, and all proposed source ink needed for its move is locally accounted for. Slur/ledger/articulation/fermata attachments remain unowned and block completeness. The final group status propagates to candidate status: a locally isolated dot does not authorize editing its incomplete connected note group. `local_crossing_clear` is context, not a separate completeness verdict. Synthetic isolated dots in fully accounted groups can pass without any sheet-specific exception.

Rejected groups emit no source-ownership core/fringe; their processed support and blockers remain auditable. Partial groups retain evidence but never reach Phase 1.8.

### Unchanged Phase 1.8 compatibility

Only COMPLETE atomic groups may supply the existing `OwnedInk` API. Symbol views are explicitly labeled `COMPLETE_ATOMIC_UNION_PROJECTION:<group>` and refer to one deduplicated group union. The current Phase 1.8 planner also insists every per-symbol run fits its Inter region. That frozen restriction is separately reported as `phase18_compatible`: COMPLETE support extending outside an Inter bbox is **not clipped, not misclassified as bad support and not injected**. Any incompatible member withholds the entire group. Changing that contract requires a separate review; the existing planner is unchanged here.

Approval still requires the independent Phase 1.8 note/beam/curve completeness, source/target protection and ownership checks. A complete ink certificate is not a ready-to-move note. Its approved pixel union must be a subset of COMPLETE source ownership, and the existing pixel-integrity validator remains authoritative. Unit tests exercise actual inside/outside-mask changes; the real ownership pass compares the untouched source to an identical copy, not a fabricated edited score.

### Developer command and decision

```sh
python -m scripts.omr_v4.inspect_source_ink v4-jayu-provenance-diagnostic \
  --out v4-jayu-provenance-diagnostic/source-ink-1.9c
```

The command obtains the actual saved BINARY and existing glyph/staff RLE, does not invoke recognition, writes `ink-evidence.json`, `ink-summary.json`, `mask-summary.json`, binary processed/core/fringe/unknown/complete/rejected/approved masks and an annotation overlay. Input artifacts and original pixels remain unchanged; all diagnostic directories stay untracked.

`READY_FOR_MASK_REFINEMENT` requires at least one COMPLETE atomic source group and all admission/integrity invariants. Otherwise return `NEEDS_INK_ISOLATION_FIXES` and do not execute Phase 1.10. No percentage threshold is selected. These rules and tests were fixed before the single existing-jayu retry; they must not be retuned in response to its coverage.

### Phase 1.9c one-pass jayu result

**NEEDS_INK_ISOLATION_FIXES. Phase 1.10 did not execute.** Starting revision was `bdc74dd0b9675383a74fb99547b417b75310d8ce`. The original source, OMR and semantic artifacts were reused; Audiveris was not run. A predeclared policy/code hash manifest was saved before the single isolation invocation. No code or policy was retuned after observing its result.

| Kind | Candidate | COMPLETE | PARTIAL | REJECTED |
| --- | ---: | ---: | ---: | ---: |
| head | 249 | 0 | 249 | 0 |
| stem | 249 | 0 | 249 | 0 |
| beam | 115 | 0 | 115 | 0 |
| beam-hook | 4 | 0 | 4 | 0 |
| flag | 14 | 0 | 14 | 0 |
| augmentation-dot | 11 | 0 | 5 | 6 |
| alter / accidental | 0 | 0 | 0 | 0 |
| **Total** | **642** | **0** | **636** | **6** |

The six rejected dot records lack a required supported typed relation; this does not assert that their raw XML has no relation of any kind. A dot's local simple shape cannot override missing supported lineage or an incomplete connected group. No real-sheet dot was promoted by exception.

| Evidence / coverage | Result |
| --- | ---: |
| Atomic ink groups COMPLETE / PARTIAL / REJECTED | 0 / 99 / 6 |
| Processed support pixel references | 332,852 |
| Unique processed support pixels | 310,142 |
| Verified non-crossing source-core pixels, group union | 232,367 |
| Bounded source-fringe pixels, group union | 34,651 |
| Intra-group shared processed pixels, recorded once per group | 22,710 |
| Unrelated-group collision references | 0 |
| Unknown processed-support crossing pixels | 59,771 |
| COMPLETE groups compatible with Phase 1.8 | 0 |
| Symbol views injected into unchanged Phase 1.8 | 0 |
| Phase 1.8 approved / blocked notes | 0 / 249 |
| Phase 1.8 approved / blocked beam groups | 0 / 66 |
| Phase 1.8 approved percentage | 0% |

The 105 ink groups use only the listed ownership edges. They are not the same grouping as the 41 Phase 1.8 edit-atomic components, which additionally constrain chord/curve structures. Pixel counts are deduplicated within an ink group; processed reference counts intentionally count each symbol view. The 59,771 uncertainty pixels count processed-support crossings; withheld neighboring fringe crossings are blocker evidence and are not claimed as source ink or added to that processed-support count.

Blockers overlap by group:

| Blocker | Groups |
| --- | ---: |
| uncertain antialias boundary | 105 |
| unknown crossing | 99 |
| unaccounted local continuation | 99 |
| unowned moving attachment | 86 |
| unresolved other-symbol contact | 8 |
| unsupported support overlap | 8 |
| local background uncertain | 6 |
| required typed relation missing | 6 |
| core contrast uncertain | 4 |

This outcome establishes real partial source cores and reconciled group support, but does **not** establish complete editable ink. Every nonrejected group remains blocked. Uncertainty in immediate low-contrast boundary pixels, bounded continuation, staff crossing or moving attachments cannot be resolved by simply declaring a strong core sufficient. The algorithm was not changed to remove those blockers.

All text protection and structural safeguards remain active. The unchanged Phase 1.8 planner still reports 11 source/text and 29 target/text conservative envelope intersections, 104 structural-collision-blocked notes, 224 target-collision-blocked notes and 40 unsupported moving attachment instances affecting 151 notes. These are independent planner checks and overlapping units; they do not contradict zero exact proposed-ownership text/structural collision blockers in this run. Four cross-system tie segments still block two edit components / ten notes. None was inferred away by ink evidence.

Artifacts remain local/untracked under `v4-jayu-provenance-diagnostic/source-ink-1.9c/`: layered `ink-evidence.json`, metrics `ink-summary.json`, unchanged-planner `mask-summary.json`, `processed-support-mask.png`, `verified-core-mask.png`, `fringe-mask.png`, `unknown-crossing-mask.png`, `complete-ownership-mask.png`, `rejected-support-mask.png`, `approved-mask.png` and `ink-ownership-overlay.png`. The predeclared manifest is `v4-jayu-provenance-diagnostic/source-ink-1.9c-predeclared.json`. Partial core/fringe images are diagnostic evidence, never approved edit masks.

Validation before the retry: **262 passed, 1 existing environment-dependent skip** from `python -m pytest tests/test_omr_v4_*.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py -q`, including 28 new layered ownership tests. The existing pixel-integrity tests include changed-pixel cases; this real pass reports zero source or outside-mask changed pixels for the unchanged RGB raster. `git diff --check` passes. The source PNG remains SHA-256 `e53c52dd7c31f0196b7c5a99231afd4f77bc522f8a02483277179a79c84dc0cb`; all five input artifact hashes remain unchanged.

Remaining work requires an explicitly authorized investigation/design of uncertain boundary pixels and staff-crossing ownership/restoration, plus moving-attachment coverage. This pass does not enlarge the fringe, relax the contrast/background guards, infer missing relations or introduce a renderer. Source pixels were never overwritten/erased/replaced; V1/V3 runtime, API/frontend/runtime V4 routes, feature flags, merge and deployment are unchanged.
