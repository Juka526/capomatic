# V4 Phase 1.8: diagnostic mask safety gate

**Decision: NEEDS_MASK_SAFETY_FIXES.** No replacement renderer, erasure, inpainting,
font binary, API/frontend/runtime V4 route, merge, deployment or production
activation was implemented. This is a mask admission/diagnostic layer only.

Analyzed starting commit: `52704f499d7a537a11bf95854fbcfeaa4f9fb379`, branch
`feature/score-v4-layout-preserve`. Existing jayu evidence was consumed from
`v4-jayu-provenance-diagnostic/`. **Audiveris was not run.** The planner was applied
to that evidence exactly once, after unit tests; the algorithm was not changed
after observing its result. All original evidence remains untracked.

## Model and admission boundary

`backend/omr_v4/masks.py` adds frozen `OwnedInk`, `Crossing`, `NoteMask`,
`AtomicGroup`, `SymbolPolicy` and `MaskSafetyPlan` records. Diagnostic masks are
native-resolution binary `L` images, values exactly 0/255. Source raster size,
mode, pixel digest and coordinate space are explicit. No implicit rescaling is
allowed. Invalid/nonfinite movement or geometry fails closed.

Every note has one primary state and the complete list of applicable blockers:

- `APPROVED_EDIT_MASK`
- `BLOCKED_PROTECTED_COLLISION`
- `BLOCKED_UNKNOWN_OWNERSHIP`
- `BLOCKED_INCOMPLETE_GROUP`
- `BLOCKED_UNSUPPORTED_ATTACHMENT`
- `BLOCKED_STRUCTURAL_COLLISION`
- `BLOCKED_TARGET_COLLISION`

When multiple blockers apply, the primary state is chosen deterministically by
state name; it is not a severity ranking or an exclusive root-cause count. The
full blocker/reason list is authoritative. One blocker is sufficient to withhold
approval; none is silently waived.

**A bounding box is not symbol ink ownership.** Approved pixels are made only from
complete, independently verified symbol-level run evidence, bound to the exact
source pixels/mode/dimensions and symbol ID. The gate checks run bounds and rejects
duplicate, unknown or misbound evidence. It does not manufacture ownership from a
bbox, connected component or darkness threshold.

`OwnedInk` is a trusted upstream evidence contract, **not an ownership extractor or
an independently authenticated certificate**. Completeness and symbol attribution
must be established before supplying it. The current real-score pipeline has no
such producer, and the CLI deliberately supplies none. Synthetic tests construct
known glyph pixels, including ellipse corners that remain unapproved, to exercise
the conditional approval path. This does not prove real glyph segmentation safe.

Consequently **no jayu source pixel is approved**. Its blocked-mask rectangles are
only conservative diagnostic envelopes, not masks a renderer may use for erasing.
`approved-mask.png` is entirely zero. The decision has no arbitrary pass threshold.

## Source ownership and noneditable pixels

The note layer starts with existing DIRECT or REPAIRED_PROVENANCE ownership. Both
bases face the same mask rules; provenance does not certify ink isolation or
correct a visual pivot. Physical candidates are collected through explicit
head/chord containment, head-stem/chord-stem, beam-stem, flag-stem, alter-head,
augmentation/double-dot and slur-head relations. Head-chords/beam-groups remain
containers, not independent rectangles to erase.

Ledger x-overlap candidates remain explicitly unproven. The gate does not turn
x proximity into ledger ownership. Changed accidental requirements and target
ledger occupancy remain unknown without independently bounded geometry. No V1
chord spelling or V3 repair/transposition policy is reimplemented.

Lyrics and all existing non-chord text protections stay active. Dynamics, pedal,
rests and chord-name text are not implicitly collected as note-owned pixels.
Clefs, key signatures/key alters, time signatures, barlines and staff-barlines are
preserved structural content for this note-mask gate. Unknown objects are neither
silently erased nor included in an approved mask. Source/target overlap with
unrelated heads/curves or preserved/unknown objects also blocks.

Malformed geometry is fatal; missing physical/protected/structural geometry stays
unknown. No final key-signature or chord-text editing mask is implemented here.

## Source versus target

`SOURCE_EDIT_MASK` is the verified original symbol-ink union only when admission
succeeds. Until then, `source_envelope` is diagnostic context and stays blocked.
`TARGET_OCCUPANCY_ENVELOPE` is a separate conservative destination envelope. It is
not a swept source-to-target rectangle and grants no source editing permission.

The layer checks source envelopes against active protected objects, and separately
checks target occupancy against text, structural content and unrelated notation.
A target leaving the page blocks. Uniform translation is only envelope context;
mixed beam displacement or nonuniform curve endpoint deltas remain incomplete.
Changed accidental shape/placement and newly required ledgers remain unknown.
No reconstructed target symbol is drawn.

Bounding collision checks are intentionally conservative. They may block a mask
whose future exact ink would fit. They cannot prove a genuine collision between
music ink and text when that ink has not been isolated. The gate reports that
uncertainty rather than calling all envelope alarms harmless or genuine.

## Atomicity and cross-system ties

Connected note/chord/stem ownership, beam groups and slurred/tied structures form
atomic components. A blocker on any member propagates to the complete component;
one head inside a beam group cannot receive partial approval. Beam/curve reports
return `APPROVABLE_AS_GROUP` or `BLOCKED` with complete reasons. Unknown endpoints,
beam/rest ownership and required mixed geometry remain incomplete.

Cross-system extensions are used **only to propagate blockers along explicit
relations**, never to invent or approve curve ownership. The four existing tie
segments block **two larger connected components containing ten notes total**,
not only the four immediate endpoint notes:

| Atomic component | Heads | Curve-segment blockers |
|---|---|---|
| `atomic:sheet#1:2626` | 2626, 2656, 2693, 2711, 2816 | 7253, 7273 |
| `atomic:sheet#1:2782` | 2782, 2794, 2818, 2824, 2903 | 7241, 7275 |

The larger scope follows the original beam/slur connections. No extension pairing,
curve reconstruction or new head matching was introduced.

## Staff ink is RESTORE_REQUIRED

Each candidate records which original staff polyline, line number and exact float
crossing segment intersects its source geometry. Clipping uses the piecewise line
segments, not a staff's mean y. Crossings are tagged `RESTORE_REQUIRED`.

With verified symbol runs, clipping is against the source ink runs; otherwise it
is explicitly tagged `SOURCE_CANDIDATE_ENVELOPE`. The diagnostic staff mask is a
conservative corridor around these centerline segments, using half the local
interline as corridor width. It is **not extracted staff ink**, an erasure mask,
or a restoration result. The width is diagnostic geometry, not a calibrated ink
thickness estimate used to approve edits.

The single jayu result has **1,290 distinct clipped candidate segments**, covering
**238,865 corridor pixels**. Overlapping segments can belong to the same staff
line or group; these are segment/corridor counts, not 1,290 unique staff lines or
1,290 approved restoration operations. Since every note mask is blocked, none
currently authorizes restoration.

A future renderer must restore interrupted staff pixels inside an approved mask;
anything outside that mask must remain unchanged. Staff crossing is not permission
to delete a line permanently. Measuring actual staff ink/restoration feasibility
and enforcing the restoration obligation remain separate work before rendering.

## Pixel integrity contract

`validate_pixel_integrity(original, hypothetical_output, approved_mask)` requires:

- equal image and mask dimensions;
- exactly equal source/output modes (`L`, `RGB` or `RGBA`), with no conversions;
- an aligned binary `L` mask;
- every changed pixel, considering every color/alpha channel, inside that mask.

Any outside-mask change raises `ValueError`. NaN geometry and unsupported image
modes cannot be converted implicitly into valid coordinates. Tests accept an
inside-only synthetic change, reject outside changes, wrong dimensions, wrong
modes and nonbinary masks.

This validator proves **containment of changes**, not that an approved mask was
semantically correct, that restoration happened inside it, or that the rendered
music is correct. Those obligations cannot be replaced by this necessary check.
No real edited candidate score was generated: the real-run identity check compares
the original with its identical copy (0 changed pixels), and separately verifies
input file hashes. That is a preservation check, not a rendering accuracy claim.

## Single jayu gate result

Input ownership remains **249 notes / 249 heads, 244 DIRECT + 5
REPAIRED_PROVENANCE**, no ambiguous or unowned events. The previously recorded
chord-integrity warning remains present in `mask-summary.json`; note/rhythm/key
integrity still passes. No integrity failure is downgraded by mask planning.

| Metric | Result |
|---|---:|
| Matched notes eligible for mask planning | 249 |
| Atomic connected components eligible for planning | 41 |
| Approved / blocked note masks | **0 / 249** |
| Percentage of notes covered by approved masks | **0%** |
| Approved / blocked beam groups | **0 / 66** |
| Source/text envelope pairs | 11 |
| Target/text envelope pairs | 29 |
| Staff crossing segments requiring future restoration review | 1,290 |
| Notes blocked by unresolved attachment/group structure | 10 |
| Cross-system tie segments / blocked components / affected notes | 4 / 2 / 10 |
| Unsupported attached instances | 40 |
| Notes blocked by unsupported attachments after atomic propagation | 151 |
| Notes blocked by structural collision alarms after propagation | 104 |
| Notes blocked by target collision alarms after propagation | 224 |
| Invalid geometry | 0 |

All 249 records include **complete independently verified symbol ink unavailable**.
The other blocker counts overlap and must not be summed. For example, a note may
have both target collision and unsupported-attachment blockers inherited from a
connected member. Complete head ownership and uniform beams did not override the
missing ink evidence.

Primary states, for completeness: target collision 105, structural collision 87,
unknown ownership 15, protected collision 32, incomplete group 10. There are no
approvals. These deterministic labels do not imply only 15 notes lack verified
ink: **all 249 do**.

## Protection findings and accounting

The existing layout report remains **30 intersection pairs / four connected
physical envelope-overlap areas**, including **12 lyric-line/lyric-item nested
duplicate pairs**. The new report preserves original pair numbers, every nested
relationship and the four original intersection-component bboxes. Both nested
protections remain logically active; normalization is reporting only.

The new **11 source** and **29 target** counts are different audit units: per-note
explicit-object source envelopes and destination envelopes against text. The old
30 also included broader swept group/curve regions and duplicated owners. These
numbers are not a reduction or relaxation of protection and should not be compared
as a pass-rate improvement. Key/barline and unrelated-notation checks are reported
separately as structural/target blockers.

All **four** original physical overlap areas remain unresolved at the ink-ownership
level. **Genuine source-edit ink conflicts are unknown (`null`), not certified
zero.** Candidate source ink is not yet isolated, and no approved source mask
exists. Target counts are conservative potential conflicts, not claims that
reconstructed glyphs would actually strike lyrics. Earlier line-envelope and
nested accounting explanations remain useful but do not approve these pixels.

## Unsupported instances

| Encountered kind | Count | Policy | Result |
|---|---:|---|---|
| articulation | 38 | ATTACHED_MAY_MOVE | explicit chord attachment retained; moving local reconstruction is unsupported and blocks the atomic component |
| fermata | 2 | ATTACHED_MAY_MOVE | owning head-chords are known; reconstruction/ink isolation remains unsupported |
| dynamics | 1 | PRESERVE_IN_PLACE | source pixels protected; excluded from note-owned edits |
| pedal | 1 | PRESERVE_IN_PLACE | source pixels protected; excluded from note-owned edits |
| barline | 45 | STRUCTURAL_PROTECTED | original geometry protected |
| staff-barline | 41 | STRUCTURAL_PROTECTED | original geometry protected |

No encountered articulation/fermata lacks its graph attachment in this evidence
(unresolved attachment-instance count 0). That does not certify glyph correctness:
false-positive recognition and overlapping text/watermark ownership remain possible.
The synthetic test also covers an unattached fermata, which becomes UNRESOLVED
and blocks overlapping edits. No unsupported mark was erased or moved.

## Outputs and reproduction

Run on an empty/new output directory, using existing artifacts only:

```bash
python -m scripts.omr_v4.inspect_masks \
  v4-jayu-provenance-diagnostic \
  --out v4-jayu-provenance-diagnostic/mask-safety
```

The completed single run generated:

- `mask-summary.json`: all per-note objects, atomic/group blockers, exact crossing
  segments, preservation policies, metrics and input hashes;
- `approved-mask.png`: all zero; **no edit authorization**;
- `blocked-mask.png`: conservative blocked source envelopes;
- `protected-mask.png`: all logical text protection plus structural/preserved
  object regions; nested items are not removed;
- `staff-restore-mask.png`: diagnostic restoration corridors only;
- `target-envelope.png`: conservative destination occupancy only;
- `mask-overlay.png`: source copy beneath annotation tints and an external legend
  distinguishing approved, blocked, protected, restore-required, target and unknown.

All five masks are binary and exactly the source raster dimensions. The overlay
adds a legend outside the source page; it is not a changed score output. No
real-source pixels were erased, inpainted or replaced. Original source/graph/plan/
summary/semantic files are hash-checked unchanged. Generated artifacts stay local
and untracked alongside the previous execution evidence.

## Verification and next boundary

Targeted tests: **213 passed, 1 skipped** (24 mask tests, existing V4 tests and the
relevant V3 music/gate regressions). The existing host test requiring MuseScore
was skipped. Tests need no Audiveris. `git diff --check` passed. V1/V3 runtime,
matcher/provenance behavior and production integrity checks are unchanged.

Before a prototype can be considered, produce independently verified source-symbol
ink ownership, resolve source/target text and structural envelope alarms, prove
new accidental/ledger occupancy bounds, define staff restoration obligations, and
handle or explicitly withhold attached articulations/fermatas and cross-system
curves atomically. Do not relax these blockers to increase coverage.

**NEEDS_MASK_SAFETY_FIXES**. Phase 2 rendering, API exposure and production release
remain unauthorized. No merge or deployment occurred.
