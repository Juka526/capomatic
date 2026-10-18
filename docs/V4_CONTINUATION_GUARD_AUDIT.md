# V4 Phase 1.9f continuation guard audit (Track A)

**Decision: `NEEDS_MORE_CONTINUATION_EVIDENCE`.** The existing guard is reproduced exactly for all 99 VERIFIED_PARTIAL groups. Its positive predicate does not establish musical ink: a synthetic one-level gray tail triggers without processed foreground. Real geometry-matched controls show that the graph's empty regions can still contain unrepresented source/BINARY content. The available evidence cannot safely partition every remote pixel into musical continuation, antialias, watermark or background. No guard, admission, ownership, attachment, mask, Phase 1.8 authorization, or V1/V3 runtime rule changes here.

## Frozen protocol and inputs

[The protocol fixture](V4_CONTINUATION_GUARD_PROTOCOL.json) was recorded before the first measurements at `2026-10-18T01:49:16.705004+00:00`; SHA-256 `6bd86b215a3ecb71835323ed719b9c5a1114b5b7a2151d577a22417a80a4bbdb`. Its original bytes remain unchanged. Proof is in `dual-track-a-output/preregistration.json`. The parent requested no commits until review, so this timestamp/hash is the preregistration record. All 28 bindings in `/private/tmp/capomatic-v4-dual-inputs.json` are checked before and after the CLI run; the protocol hash is checked before and after too. Original OMR input identity remains limited as described by that binding file: the OMR does not embed an original input SHA.

The source, saved handoff, source-ink evidence and persisted V3 evidence under `/private/tmp/capomatic-v4/v4-jayu-provenance-diagnostic/` are read-only inputs. The offline [helper](../scripts/audit_continuation_guard.py) writes only inside this worktree's `dual-track-a-output/`, rejecting the input root and other destinations. All large outputs remain untracked. No Audiveris, Docker, Phase 1.10, FullAcceptance or runtime evaluation was run.

## Population reconciliation

The earlier [feasibility prose](V4_V3_EVIDENCE_FEASIBILITY.md) combined two populations in its 8,764/4,282 statement. The frozen JSON and direct original-raster lookup establish:

| Population | Groups | Distinct remote pixels | Original grayscale 254 |
|---|---:|---:|---:|
| VERIFIED_PARTIAL | 99 | 8,764 | 4,263 |
| Additional REJECTED groups | 6 | 21 | 19 |
| All handoff groups | 105 | 8,785 | 4,282 |

Thus 4,282 is real, but belongs to all 105 groups; it is not the gray-254 count within the 8,764-pixel PARTIAL population. The six rejected groups remain excluded from continuation admission analysis; `audit.json` records their separate per-group measurements. No historical score or evidence file was edited.

All 99 original remote sets and background estimates match the saved handoff exactly. Distinct remote sets do not overlap between these groups. The backgrounds are 255 for 93 groups, 212 for four, 248 for one and 214 for one. `gray < local_background` can therefore detect a one-level variation or a strong contrast; it is not a uniform contrast threshold. The summary retains every per-group histogram. Distinct contrast reporting explicitly uses each pixel's minimum observed group background; no pixel in this run has multiple group backgrounds. An initial reporting-only assumption that backgrounds were identical failed, and was corrected to retain these differences; neither the registered measurements nor the guard predicate changed.

## Attribution, without ownership inference

The 8,764 PARTIAL remote pixels include 392 BINARY foreground pixels and 8,372 outside BINARY. Exact semantic-symbol glyph support covers 163 distinct pixels: 120 ledger, 43 slur. Those intersections explain a persisted representation, not the ownership of the original gray pixels or their attachment to a moving group. Zero hits in already excluded staff/support classes cannot prove those structures are absent upstream.

The following disjoint categories use the preregistered precedence. Every row is diagnostic evidence; none authorizes editing.

| Category | Distinct pixels | Meaning |
|---|---:|---|
| PERSISTED_SYMBOL_SUPPORT | 163 | Exact slur/ledger glyph intersection |
| UNSUPPORTED_BINARY_INK_CANDIDATE | 229 | BINARY foreground with no semantic-symbol glyph intersection |
| LOW_CONTRAST_BACKGROUND_CANDIDATE | 5,207 | Outside BINARY/support, contrast 1–7; possible antialias or background variation |
| SOURCE_ONLY_UNRESOLVED | 3,165 | Remaining source-only contrast; physical cause unknown |

Contrast means local background minus source grayscale. The low-contrast category uses 1–7 inclusive; source-only unresolved is the residual after support and BINARY precedence. The 120 ledger and 43 slur supports are disjoint here. These counts sum to 8,764. All 4,263 gray-254 PARTIAL points are outside BINARY and glyph support. Full source intensity and local contrast distributions, all 99 rows of original nonexclusive attribution, and attachment records are in `audit.json`. In particular, intensity 212 occurs at 1,599 remote pixels; it cannot be dismissed by focusing on near-white values. Direct visual inspection of the source shows a broad pale-gray watermark across the middle systems. That observation supplies a plausible non-musical contributor; there is no independently labeled watermark polygon, so no exact remote-pixel watermark attribution is claimed.

**True unresolved musical ink is not independently counted by this experiment.** The 229 unsupported BINARY pixels are foreground candidates; they may include notation, preserved text or other content. Neither BINARY agreement nor contrast proves musical identity. Similarly, the 5,207 low-contrast candidates are not 5,207 proven false positives. This is an evidence gap, not an inferred ownership partition.

Persisted attachment information remains available but incomplete for ownership: the frozen attribution reports 103 unique attachments with explicit relation, geometry and support, four cross-system extensions and 11 with support but ambiguous relation. Missing use of ledger/slur support explains the 163 intersections, not all continuation or attachment blockers. No nearest-symbol ownership, extension inference or policy expansion is proposed.

## Source component connectivity through staff

For each distinct measured background, the helper measures full-page 8-connected components of original `gray < background`, then repeats after removing the union of logical staff context and exact persisted staff glyphs. This is a sensitivity experiment on topology, not a proposal to follow, erase or own a component. Real guard pixels already exclude those staff regions; all 8,764 survive the removal.

| Measured remote-pixel references | Original source CC | Staff context/glyph removed |
|---|---:|---:|
| Shares component with group processed support | 8,395 | 8,003 |
| Shares component with staff support | 8,390 | 0 by construction |
| Component count, summed per group | 249 | 702 |

Group-support connection drops for 69 groups, a total of 392 remote points. At least those paths depended on removed staff evidence under this mask; the removal also can break non-staff paths where staff context overlaps other content. The remaining 8,003 group-connected points are not proven group-owned: long components can include watermark, staff antialias and unrelated notation. Component counts are summed per group, not distinct page components. The 369 original points without a group-support component and the 761 after removal remain separate unresolved cases. Exact per-group values are exported.

## Geometry-matched negative controls

Selection was fixed before results and does not inspect gray, BINARY or trigger outcomes. For each original group, preserve and translate the exact support/core/fringe-derived unknown stencil, radius-4 outer stencil, attachment exclusions and support-bbox ring. Eligible bbox origins lie on the fixed `(8 + 16k, 8 + 16j)` grid, with a full 5px ring on-page. Reject any complete translated bbox/ring intersecting a symbol region expanded 6px, logical/exact staff or processed group support. The first three eligible origins by squared distance from the original origin form the nearest-unaffected stratum. The first three remaining row-major origins form the page-blank-candidate stratum. The unknown stencil is `(support union radius-2 neighbors) minus saved core minus saved fringe`; it is constructed before evaluating guard outcomes. Core/fringe come from earlier source-derived evidence, so the matched template is not a newly blinded ownership estimate. The outer guard is radius-4 neighbors minus support, radius-2 neighbors and attachment analysis regions. A remote pixel must have `gray < background`, avoid existing staff/related-attachment exclusions, and have an 8-neighbor in the source-visible unknown stencil. The background is the median grayscale in the rectangular bbox annulus at Chebyshev distance 3–5. This uses the original shape, not a filled rectangle.

The eligible population ranges from 3,092 to 10,793 origins per group; all 99 groups yield six samples. These are geometric blank **candidates**, not externally labeled blanks. Translated support shapes differ even at reused origins, and nearby windows overlap.

| Measured control references | Nearest unaffected | Page blank candidate |
|---|---:|---:|
| Group-template placements | 297 | 297 |
| Unique origins | 289 | 3 |
| Unique support-bbox windows | 297 | 216 |
| Triggered placements | 124 | 0 |
| Tested guard positions | 448,194 | 448,194 |
| Remote pixel references | 20,700 | 0 |
| Remote BINARY ink references | 5,273 | 0 |
| Full-stencil BINARY ink references | 38,220 | 0 |
| Stencils containing any BINARY ink | 90 | 0 |
| Full-stencil semantic-symbol support references | 0 | 0 |

These are reference counts, not distinct control pixels. `audit.json` additionally records unique bbox windows, all selected coordinates, group populations and full-stencil foreground measurements. No confidence interval or independent-sample rate is inferred. The page stratum heavily reuses three top-of-page origins and has no source-gray-below-background pixels in any stencil; its zero triggers validate this limited blank case only. The nearest stratum contains 162,526 full-stencil gray-below-background references despite graph exclusion. Of its triggered references, 1,952 are low-contrast candidates, 13,475 source-only unresolved and 5,273 unsupported BINARY candidates. Intensity 212 contributes 11,293 references. The presence of unrepresented BINARY content in 90 stencils defeats any claim that this stratum is known physical background or that its 124 triggers are a measured false-positive rate.

The separate synthetic controls establish the predicate's behavior with independent constructed truth: a uniform white blank has no trigger; a two-pixel connected tail at gray 254 on white produces one remote pixel even with no BINARY or symbol support; the same geometry with dark values also triggers. Removing the inner tail pixel breaks adjacency and suppresses the remote trigger; marking the remote pixel in the existing exclusion mask also suppresses it. This does not establish that the synthetic tail resembles real antialias or watermark pixels. These are narrow counterexamples to interpreting the predicate as musical identity, not an accuracy benchmark.

## Smallest structural proposal and next evidence

Keep the existing guard blocking. Before proposing a rule change, add an analysis-only continuation witness record that separates exact processed support, source-only contrast, local-background provenance and staff-dependent topology. Treat persisted ledger/slur support as additional named evidence, with its explicit relation and ambiguity retained. Do not merge whole source components or silently suppress low-contrast candidates. The minimum next experiment is independent pixel/polygon annotation of a fixed sample spanning these four categories, all four observed backgrounds and both control strata, explicitly separating watermark, musical ink, text and antialias/unknown. A proposed sampling unit is a distinct source pixel with page/staff context; hash-rank coordinates within category/background cells, deduplicate overlapping control pixels, and freeze a bounded sample before annotation or guard implementation. Two independent annotators should retain an unknown option and adjudicate disagreements. Its detailed sample cap and annotation contract must be preregistered separately. Musical or ambiguous pixels in any proposed suppression category require continued blocking; a later structural proposal requires independently labeled non-musical evidence plus a rule that retains musical/unknown cases. This is a future study proposal, not an experiment run here or a current ownership-safe suppression rule.

## Reproduction and validation

```sh
/private/tmp/capomatic-v4-venv/bin/python scripts/audit_continuation_guard.py \
  --bindings /private/tmp/capomatic-v4-dual-inputs.json \
  --output dual-track-a-output
/private/tmp/capomatic-v4-venv/bin/python -m pytest -q \
  tests/test_omr_v4_*.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py
```

The scientific JSON is deterministic; measured wall time and process peak RSS are kept in a separate instrumentation file. Runtime/RSS describe this offline helper on this machine, not V4 production latency, a budget estimate, or general score accuracy. The final measured helper run took **58.395 seconds**, with process peak RSS **517,013,504 bytes (493.1 MiB)** on macOS/Python 3.12.2. These include input verification, graph/glyph loading, all controls, connected components and JSON output. No metric is presented as estimated. Checks are recorded in `dual-track-a-output/validation.json` and `instrumentation.json`.

The leakage check distinguishes a reproducible mechanism test from ground truth: the guard replay and threshold buckets are implementation-derived, so they cannot validate semantic ownership. Geometry-only controls avoid selecting on the measured gray outcome, but graph omissions contaminate their physical blank status, and one score plus overlapping placements cannot support generalization. Existing documents retain their historical decisions; this audit is the canonical correction of the mixed-population count above. No duplicate historical artifact was silently reconciled. This work intentionally leaves guard fixes, annotated ground truth and general V4 accuracy unmeasured.
