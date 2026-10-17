# V4 Phase 1.9d: refinement handoff contract

Ownership evidence, admission to analysis and permission to edit are separate contracts. This phase does not change Phase 1.9c's historical result, core/fringe pixels, completeness labels or `SourceInkEvidence.owned()`. A `VERIFIED_PARTIAL` group may become `REFINEMENT_ELIGIBLE_PARTIAL`, but the frozen handoff has no OwnedInk-producing method and always reports `edit_authorized=false`. COMPLETE evidence remains COMPLETE; the existing Phase 1.8 contract remains authoritative outside this analysis tool.

Starting revision: `3a4e5f961c61f0eef2c964095e5abb6579739a91`. Existing jayu recognition and the saved `source-ink-1.9c/ink-evidence.json` are inputs, never rewritten or re-isolated. No Audiveris execution is needed.

## Fixed bounds and safeguards

For each group, the known core/fringe are copied exactly from evidence. The analysis-only unknown stencil consists of remaining processed pixels plus their Chebyshev radius-2 neighborhood, excluding known core/fringe. This includes background context; its pixels are not ownership claims. Explicitly identified moving-attachment regions may be added only with compatible SIG lineage, gap at most one interline, height at most two interlines and width no greater than the group support width plus two interlines. Cross-system or multi-owner curves, ambiguous nearby attachments and missing geometry block admission.

Unknown regions store canonical RLE, bbox, exact maximum Chebyshev distance to processed support, staff/polyline witnesses, attachment references and neighboring/protected/structural intersections. Distance is measured for reporting, never used to assign an event or pixel to its nearest symbol. Staff-attributed pixels remain staff evidence, not disposable ink.

Core must be nonempty. Every member's existing processed provenance and supporting relation IDs must remain valid in the exact graph. Missing lineage, unknown necessary provenance, any unresolved nonlocal/contrast blocker or invalid/unbounded page protection blocks admission. Whitelisted unresolved reasons are staff crossings, antialias boundary, local continuation requiring partition and explicitly known moving attachments. Merely whitelisting a label is insufficient: all geometric, lineage, protection and bilateral-witness checks still apply.

Analysis regions, core and fringe must avoid all text/structural bounds and another atomic group's support plus a one-pixel proximity guard. Preserved unrelated SIG geometry is an additional exclusion. No protection is weakened or normalized away.

## Continuation and antialias context

Visible local continuation uses the same measured group-background annulus as 1.9c, without changing its ownership rules. Pixel evidence is classified as `STAFF_CONNECTED`, `ATTACHED_MUSICAL_SYMBOL`, `ANTIALIAS_EDGE`, `SAME_ATOMIC_GROUP_CONTINUATION`, `NEIGHBORING_GROUP`, `PROTECTED_CONTENT`, `STRUCTURAL_CONTENT` or `UNKNOWN_LOCAL`. Labels are diagnostic evidence, not assignments of ownership. Attachment stencils and their lineage are recorded separately from visible radius-2 continuation.

A radius-4 guard looks for non-background, non-staff pixels immediately continuing from the visible local unknown region into the outer guard. Such unexplained outward continuation is `UNKNOWN_REMOTE_CONTINUATION` and blocks admission. The tool does not follow whole page-wide source connected components or absorb their pixels. A finite, isolated radius-2 boundary with no collision/remote continuation is `ANTIALIAS_BOUNDARY_REFINABLE`; otherwise it is blocking. No gray threshold, fringe radius or 1.9c rule is tuned.

## Staff analysis admission

Crossing intervals follow the original staff polyline and serialized stroke width. Each interval must be at most four interlines wide. Both sides must provide at least three distinct witness columns from fixed offsets 2–6 pixels beyond the unknown interval. A witness must belong to the serialized staff glyph, be visibly darker than local background by the existing contrast guard, be outside musical processed support and avoid protected/structural pixels. Actual polyline geometry, width, witness coordinates and rejection reason are retained.

This only produces `STAFF_REFINEMENT_ELIGIBLE` or `STAFF_REFINEMENT_BLOCKED`. It does not certify restoration or claim that missing staff attribution proves absence of physical staff ink. Missing a side, invalid width/geometry, excessive extent or a collision blocks analysis.

## Moving attachments

Compatible explicit slur-head, chord-articulation, fermata-chord or head-ledger lineage identifies attachment ownership candidates; head-chord containment resolves endpoints. A local attachment belonging only to this group is `ATTACHMENT_IDENTIFIED_NEEDS_REFINEMENT`. Explicitly other-group attachments remain `ATTACHMENT_UNRELATED_PRESERVE`; ambiguous, nonlocal or cross-group lineage becomes `ATTACHMENT_AMBIGUOUS_BLOCK`. No attachment is isolated, moved or rendered in this phase.

## Outputs and gate

```sh
python -m scripts.omr_v4.inspect_handoff v4-jayu-provenance-diagnostic \
  --out v4-jayu-provenance-diagnostic/refinement-handoff
```

The developer CLI checks prior input hashes and processed OMR binding, writes `handoff.json`, `handoff-summary.json`, context masks and `handoff-overlay.png`, and verifies original evidence hashes again. It never calls the 1.9c isolator or Phase 1.8 OwnedInk adapter; stored Phase 1.8 approval metrics remain unchanged. The handoff and all generated artifacts are local/untracked.

`READY_FOR_MASK_REFINEMENT_ANALYSIS` requires at least one safely eligible real PARTIAL group. It authorizes analysis only. `NEEDS_HANDOFF_FIXES` stops before Phase 1.10. Phase 1.10, if admitted, must independently resolve residual ink, crossing restoration, attachment ownership, target safety and outside-mask integrity before any `MASK_READY` result. Neither status authorizes a renderer or production exposure.

## Validation boundaries

Synthetic tests cover analysis-only PARTIAL evidence, bilateral staff witnesses, unbounded/missing staff geometry, bounded antialias and continuation, remote continuation, text/barline and neighboring-owner exclusion, explicit/ambiguous moving attachment, missing lineage, deterministic serialization, source binding and unchanged COMPLETE behavior. No Audiveris is needed. A passing handoff does not validate source ownership accuracy or replace the earlier pixel-integrity tests.

Before the real handoff: targeted V4 plus frozen V3 music/gate regressions passed **277 tests with 1 existing environment-dependent skip**. Policy, classifier/CLI/test hashes were recorded in `v4-jayu-provenance-diagnostic/handoff-predeclared.json` before the one-pass jayu invocation. Any study of the single development sheet remains analysis evidence, not independent ground truth for original-pixel ownership.

## One-pass jayu handoff result

**NEEDS_HANDOFF_FIXES. Phase 1.10 did not execute.** The analysis/authorization dependency is separated in code and passes synthetic positive cases, but this real-sheet run does not prove any PARTIAL group suitable for the stricter handoff. No rule or 1.9c evidence was changed after the result.

| Handoff metric | Result |
| --- | ---: |
| Existing PARTIAL ink groups | 99 |
| REFINEMENT_ELIGIBLE_PARTIAL | 0 |
| REFINEMENT_BLOCKED_PARTIAL | 99 |
| Eligible notes / beam groups | 0 / 0 |
| Eligible simple / isolated simple symbols | 0 / 0 |
| Unknown stencil pixel references in eligible groups | 0 |
| Unknown stencil pixel references in blocked PARTIAL groups | 208,286 |
| Source ownership / edit authorizations created | 0 / 0 |
| PARTIAL records sent to Phase 1.8 | 0 |

The original six REJECTED groups remain rejected analysis inputs. They are not added to the 99 blocked PARTIAL count. All unknown stencils are finite and explicitly recorded; a finite candidate stencil does not itself prove that all connected unresolved ink is contained within it. Group pixel-reference counts may overlap between analysis stencils and are not pixel ownership claims.

### Blocker breakdown

Counts overlap by PARTIAL group; do not sum them.

| Blocker family | Groups |
| --- | ---: |
| Staff | 23 |
| Antialias boundary | 99 |
| Continuation | 99 |
| Moving attachment | 87 |
| Protected text | 1 |
| Structural | 0 |
| Unrelated ownership/proximity | 0 |
| Missing lineage | 0 |
| Other preserved-object or inherited uncertainty | 15 |

All 99 groups have outward non-background continuation that the current local guard cannot explain as staff geometry/attribution or an explicitly bounded attachment. Their antialias boundary classification is therefore also blocking; these are correlated outcomes, not independent evidence of 198 failures. The guard identified 8,764 distinct unexplained pixels across the page. This does **not** establish that those pixels truly belong to remote/unrelated notation: staff antialias tails or incomplete attribution may still explain some. It establishes that this classifier has not proved the needed partition. No unsupported correction, staff removal or ownership expansion was applied to make them pass.

The visible local continuation evidence, counted by group pixel references, is: STAFF_CONNECTED 86,296; SAME_ATOMIC_GROUP_CONTINUATION 17,537; ANTIALIAS_EDGE 14,432; UNKNOWN_LOCAL 18,881; PROTECTED_CONTENT 6; ATTACHED_MUSICAL_SYMBOL 0 in the radius-2 visible-continuation subset; NEIGHBORING_GROUP and STRUCTURAL_CONTENT 0. Explicit attachment stencils are tracked separately, so zero in that subset does not mean there are no attachments.

### Staff and attachment subresults

There are 886 crossing-interval references individually marked `STAFF_REFINEMENT_ELIGIBLE`, and 32 marked `STAFF_REFINEMENT_BLOCKED`, across the PARTIAL groups. These are bilateral-evidence admission checks, **not RESTORABLE certificates**. Every group must also satisfy the remaining guards; individually eligible crossings do not override a blocked group.

Attachment references are: 2 `ATTACHMENT_IDENTIFIED_NEEDS_REFINEMENT`, 2 `ATTACHMENT_UNRELATED_PRESERVE` and 178 `ATTACHMENT_AMBIGUOUS_BLOCK`. The same physical curve/attachment can appear in multiple group handoffs; these are references, not 182 unique physical symbols. Ambiguous includes cross-group, nonlocal or absent supported lineage. Identified attachment regions are explicitly bounded; the maximum observed distance of an unknown stencil pixel to processed support is 58 pixels, from an added attachment context. Radius-2 core-boundary stencils and separately bounded attachment stencils are not conflated.

No attachment ownership, mask refinement or staff restoration was attempted. The next required work is to explain/partition the remaining outward continuation and ambiguous attachment boundaries under a principled local model, rather than tuning 1.9c or promoting PARTIAL ownership.

### Evidence preservation and validation

Generated local/untracked outputs are under `v4-jayu-provenance-diagnostic/refinement-handoff/`: `handoff.json`, `handoff-summary.json`, known-core/fringe, bounded-unknown, protected, unrelated, structural, eligible and blocked context masks, and `handoff-overlay.png`. Per-group JSON records bounds, exact distance, classes, remote guard pixels, original polylines, both-side witnesses and attachment lineage. These diagnostic masks are never approved edit masks.

The classifier/CLI/tests match their predeclared SHA-256 values after the run. Source PNG remains `e53c52dd7c31f0196b7c5a99231afd4f77bc522f8a02483277179a79c84dc0cb`; the existing 1.9c evidence remains `a5a060a0f2bf92462283519785cbbb751f4151b4124ed4028c6334a02e4c3d98`. The CLI verified every recorded input hash after writing. The original 1.9c core/fringe and all ownership status fields remain byte-for-byte unchanged.

Existing Phase 1.8 approval remains **0/249 notes and 0/66 beam groups, 0%**, with COMPLETE-only injection rules unchanged. The handoff never invokes the adapter or changes that planner. Targeted V4 and V3 music/gate validation passed **277 tests, 1 existing environment-dependent skip**; `git diff --check` passed. No Full Acceptance, fresh data, recognition rerun or CI watch was performed.

Original source pixels were not overwritten, erased or reconstructed. No finished score, renderer, API/frontend/runtime route, V1/V3 runtime change, merge or deployment was introduced.
