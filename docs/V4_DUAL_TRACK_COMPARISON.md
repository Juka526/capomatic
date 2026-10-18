# V4 dual-track architecture evaluation

## Comparison protocol frozen before track results

Common base: `04687ce6ac65eb4d9505365b92aa96c886c88530`.
Inputs: [V4_DUAL_TRACK_INPUTS.json](V4_DUAL_TRACK_INPUTS.json), 28 existing files verified before execution. The original worktree and evidence are read-only. Track A and B have separate branches, worktrees and writable outputs. The coordination branch contains documentation only; no experimental changes are merged or cherry-picked.

The comparison evaluates architecture feasibility, not a winner on this one development score. Track A is an audit of a prerequisite to selective reconstruction. Track B begins with geometry feasibility and may make a limited visual demonstration only after its preregistered gates pass. Audit artifacts are not equivalent to a rendered crop.

We will compare:

- Layout fidelity: measured coordinates, page/system/measure constraints and any raster evidence; distinguish imposed zero-deviation constraints from independently verified visible notation.
- Semantic fidelity: unchanged V3 guard results, scope of those checks, and unresolved chord/note/rhythm/key failures. Diagnostic warnings are never production acceptance.
- Protected-region preservation: input-file integrity, annotation behavior and actual composition tests reported separately. An untouched source is not proof that a future renderer preserves text.
- Completeness: implemented analysis versus unimplemented masks, reconstruction, curves, attachments and visual composition.
- Operational cost: observed wall time and process peak memory with methodology/environment, not a performance ranking between unequal workloads. Measurements from concurrent development runs are not benchmarks.
- Generalization: tests and controls can falsify narrow hypotheses; neither track may claim real-score accuracy or safe editing from jayu alone.

No numeric pass-rate target will be invented after seeing results. A favorable recommendation cannot authorize rendering, production integration, merge or deployment. The next experiment must address the most consequential remaining uncertainty and eventually use independently selected evidence with comparable output maturity.

## Results

Selective reconstruction retains original raster content and eventually changes only proven owned music ink. Geometry-locked re-engraving would rebuild notation at original staff/measure/x coordinates while preserving protected source content. Both tracks stop at unresolved prerequisite evidence; no architecture winner is established. The intended semantic transform in both is the existing key transposition by −2 semitones.

| | Track A: selective reconstruction prerequisite | Track B: geometry-locked feasibility |
|---|---|---|
| Branch | `feature/v4-continuation-audit` | `feature/v4-geometry-locked` |
| Commit | `817c43af19cc91a6b145f244e191ed8ee695ea05` | `1a332faaf6e30b6f7645ad0bf3d9f41e915f8ac9` |
| Decision | **NEEDS_MORE_CONTINUATION_EVIDENCE** | **GEOMETRY_LOCKED_POC_NEEDS_WORK** |
| Implemented | Frozen continuation predicate replay, support attribution, topology and controls; no rule change | Frozen measures 1/2/3, 30 absolute target coordinates, geometry/collision reports and annotated crops |
| Actual output maturity | Audit JSON and documentation, not edit masks or score output | B1 maps/annotations only; B2 replacement-notation PoC skipped |
| Layout fidelity | No layout modification; future selective masks remain unresolved | Page/staff/system/measure/x deviations zero by coordinate construction; no visible engraving validation |
| Semantic fidelity | Identical source/target artifacts, no semantic mutation | Unchanged full V3 guard fails bar 32 chord semantics; cannot waive it with note-only pass |
| Protection | No OwnedInk promotion; Phase 1.8 unchanged at 0/249 notes, 0/66 beams | No source edit; annotation borders change lyric pixels as reported; replacement lyric equality not applicable |
| Completeness | 99 groups remain blocked; original-pixel ownership unresolved | Complete notation/beam/curve/chord layout unvalidated, actual ink collisions unknown |
| Observed workload | 99 groups, page components, 594 translated controls | 30 heads in three measures, semantic checks and three annotated crops |
| Tests | 293 passed, 1 skipped | 299 passed, 1 skipped |

Immutable track reports: [Track A audit](https://github.com/Juka526/capomatic/blob/817c43af19cc91a6b145f244e191ed8ee695ea05/docs/V4_CONTINUATION_GUARD_AUDIT.md), [Track B feasibility](https://github.com/Juka526/capomatic/blob/1a332faaf6e30b6f7645ad0bf3d9f41e915f8ac9/docs/V4_GEOMETRY_LOCKED_FEASIBILITY.md).

## Comparable evidence and frozen populations

The shared [input manifest](V4_DUAL_TRACK_INPUTS.json) records all 28 hashes. Both helpers verified them before and after execution. Primary bindings:

| Artifact | SHA-256 |
|---|---|
| source.png | `e53c52dd7c31f0196b7c5a99231afd4f77bc522f8a02483277179a79c84dc0cb` |
| recognized.omr | `e5076145d9b682f77d3bcf333996d9dd33c3c0b5cb6a597caf7b330c6981e29b` |
| recognized.musicxml | `dacf6f94af18e92fabebbc59926a5bb34e42366deb453232dde5e0c18ea92d14` |
| transposed.musicxml | `7b79a8f79de2d453b5f08a934712ad6f472a1e7d18ec9cb37576032201cf0557` |
| plan.json | `30f52e0cbadf42af37be585f3b5a7b5c4f13b1ce9de03dab918ea0ccd5729f45` |

Current artifact hashes are not independent original-recognition authentication; OMR lacks an embedded original-input digest. Both use the same semantic evidence and repaired ownership, including the five historical ledger repairs. No experimental changes crossed branches.

Track A protocol SHA: `6bd86b215a3ecb71835323ed719b9c5a1114b5b7a2151d577a22417a80a4bbdb`. Track B excerpt registration SHA: `71d3e2012c86e83880b768498d6ac3b6b8a2a0d33f05be262cded7067b0abbfb`. Both were recorded before outcome measurements and are committed as small protocol fixtures. These are development examples selected by declared structure/geometry, not blind independent holdouts.

## Track A findings and limits

The earlier claim of 8,764 remote pixels including 4,282 gray-254 pixels mixed populations. The **99 PARTIAL groups contain 8,764 pixels and 4,263 gray-254 pixels**. Six REJECTED groups add 21 pixels, including 19 gray-254 pixels, making 8,785/4,282 across all 105 groups. The original evidence was not changed. Here “remote” means the saved radius-four guard pixels, not an established remote musical component; “gray-254” is original grayscale intensity 254, and BINARY is Audiveris adaptive foreground support. Counts in the population/partition statements are distinct source coordinates. Component and control totals are group/template references; per-group remote sets happen not to overlap in this run.

A preregistered diagnostic classification partitions the 8,764 PARTIAL pixels into 5,207 low-contrast background **candidates**, 163 persisted musical-symbol support intersections, 229 otherwise unassigned BINARY-ink candidates and 3,165 source-only unresolved pixels. These are evidence classes, not physical ground-truth ownership. Direct slur/ledger attribution still does not certify an edit mask.

There are 594 geometry-selected controls at 292 distinct origins. Row-major blank candidates trigger 0/297; nearby graph-empty candidates trigger 124/297 and contain 20,700 guard-pixel references, including 5,273 BINARY hits. The latter are contaminated or physically unknown controls, not proven blanks. Reused/overlapping locations are not independent observations; no false-positive rate or confidence interval is claimed. The controlled synthetic one-level-gray tail demonstrates that `gray < local_background` can trigger without musical ink support, but does not label real pixels automatically.

At each group's unchanged background, 8,390 remote references share source components with staff and group support. Removing logical staff context plus serialized attribution leaves 8,003 connected to group support. This temporary-mask intervention demonstrates broad topology dependence, not permission to partition source components. Visible watermark/background structure and missing support attribution still require independent labels. There was no guard threshold, ownership admission, Phase 1.8 authorization or eligibility change; Phase 1.10 did not run.

## Track B findings and limits

B preserves original geometry in coordinate data, then independently anchors target y to corrected semantic staff pitch and the original middle-line polyline/interline. This avoids merely checking the old relative movement equation against itself.

For repaired heads `sheet#1:2334` and `sheet#1:2335` in frozen measure 1, the old target y is 568.65 but the absolute semantic model gives 576.05: a **7.40 px anchor discrepancy**. Raw detected centers are not guaranteed correct glyph pivots after recognition/ledger repair. This is a geometric modeling issue to resolve, not proof of exact replacement ink positions or a change to existing modules.

The 30 absolute target displacements, measured as target y minus original detected head-center y in page raster coordinates, range from +10.10 to +18.05 px. Target head rectangles have zero pair/protected-envelope overlaps in these excerpts, while 146 existing-plan swept component/group/curve envelope pairs overlap. Expected attachment/group containment contributes to the latter. Neither count is a rendered ink-collision count. Actual complete-notation collisions, chord width conflicts and replacement lyric equality remain unknown. Two chord strings gain one character, but characters are not measured glyph widths.

The unchanged full guard on persisted XML fails at bar 32, outside the chosen excerpts; the whole-artifact gate remains enforced. A separate in-memory transposition check also flags bars 4 and 20; this compares a different representation stage and does not establish new V3 bugs without round-trip analysis. B2 was skipped rather than relaxing that gate. The three PNGs retain source notation with explicit diagnostic annotations; they are not transposed-score output. Annotation differences are measured, not reported as protected-pixel equality.

## Complexity, cost and generalization

Both add only offline helpers, tests and evidence documentation. No new runtime dependency, font binary, API or production renderer was introduced. Track A's future cost is proving source ownership, boundaries, attachments and atomic masks before local replacement. Track B's future cost is constructing an engraving model for all notation while locking horizontal space, curves and protected source composition. Neither implementation measures those future costs.

Observed runs on the same macOS host:

| Measurement | A | B |
|---|---:|---:|
| Wall time | 58.40 s | 0.83 s |
| Process peak RSS | 517,013,504 bytes | 232,144,896 bytes |

These are actual diagnostic-process measurements, not estimates or renderer performance. A analyzes a page and hundreds of controls; B analyzes 30 targets with no reconstruction. Development ran concurrently and repeated verification/reporting steps occurred. The numbers cannot fairly rank architecture speed or memory; no production cost is inferred. Timing is stored separately from deterministic scientific JSON.

Single-sheet risks include shared recognition errors, incomplete text/attachment coverage, geometric model assumptions, missing grayscale ownership and chord serialization behavior. Structural coordinate invariants and designer-defined candidate classes are not independent raster or semantic ground truth. Synthetic tests check mechanics and negative cases; they do not establish general score accuracy.

## Recommendation and next experiment

**NEEDS_INDEPENDENT_VALIDATION.** Neither outcome justifies choosing an architecture or starting a production renderer. In particular, Track A's audit is not comparable to a completed B visual renderer, and no such B renderer exists here.

The next experiment should preregister a small independently annotated source-evidence set: genuine blank/background/watermark patches, symbol edges, staff-connected notation, moving attachments and corrected-pitch head anchors. Annotators should label without the guard's candidate classes or knowing which architecture a sample favors. Freeze those labels before scoring. For A, ask which guard classes are actual notation versus preserved non-musical content; any suppression proposal must retain independently labeled musical/unknown pixels as blockers. For B, independently annotate corrected-pitch pivots with uncertainty bounds before checking absolute targets; copied coordinate invariants alone cannot pass visible-layout checks. Keep these two prerequisite questions separate. Evaluate unchanged A evidence categories and B absolute target geometry against that evidence, while separately investigating the shared chord guard/serialization blocker without weakening production gates. No new scores, labels or recognition runs were generated in this evaluation.

Only after those prerequisites pass should a later comparison bring both tracks to equivalent isolated output maturity. Both approaches must represent the same complete atomic group, including its beams/curve/chord context and protected lyric composition. The comparison must then verify musical semantics, full notation collisions and protected-pixel composition on independently selected real-score excerpts. This recommendation authorizes no implementation, rendering, new data collection or production change by itself.

## Artifacts, safety and stopping state

- A: `/private/tmp/capomatic-v4-audit/dual-track-a-output/` (untracked audit, controls, preregistration and resource JSON).
- B: `/private/tmp/capomatic-v4-geometry/dual-track-b-output/` (untracked maps/reports, frozen-registration evidence and three annotated PNGs).
- Original: `/private/tmp/capomatic-v4`, still at the common base with the same pre-existing untracked evidence directories.
- Coordination: `/private/tmp/capomatic-v4-comparison`, branch `docs/v4-dual-track-comparison`, documentation only.

Both experimental branches are separate descendants of the exact common base. No cherry-pick or merge joined them. Final input hashes match; original source evidence, V1/V3 runtime and production flags are unchanged. No finished transposed score, production renderer, V4 API/frontend route, Full Acceptance, Audiveris/Docker run, branch/worktree deletion, merge or deployment occurred. Targeted tests and diff checks passed independently; the comparison changes are documentation only.

Both tracks ran `python -m pytest tests/test_omr_v4_*.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py -q` in their own worktrees. Each skipped test is the existing MuseScore-not-installed fast-path test, not B2. B2 is an explicitly blocked experiment, not a skipped unit test. Runtime measurements are the latest recorded complete helper runs, not cumulative development cost. Reproduction commands, protocol details and per-metric evidence are in the immutable track reports linked above.
