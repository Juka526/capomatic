# Independent reference collection preparation

This handoff prepares human collection and a separate harmony-boundary experiment. It chooses no architecture and introduces no new acceptance rule. Historical validation reports and frozen protocols remain unchanged. Coordinator reports and diagnostic answers must never be distributed with source-only annotator packets.

| Track | Starting commit | Current collection state | Actual independent labels |
| --- | --- | --- | --- |
| A ink | `144a4e21cb76d75f25b233a4caada64a4aaf7fbf` | Screening kit ready; official packet NOT_READY until prerequisite freezes | 0 |
| B anchors | `0b27842a14cf5db364653bd41d212d40665ddf6a` | TECHNICALLY_READY, fixed 10-case source-only packet; external roster pending | 0 |
| Shared harmony | `b0caca0c22bc49a5a327e0b8368ff5936c1901c8` | Diagnostic normal form BLOCKED_FOR_RUNTIME_UNVALIDATED_REALIZATION | 0 |

## A: ink collection

Track A commit `d43c616d2040beb8693eabe695f8ef620d46fe77` on `feature/v4-independent-ink-validation` contains `docs/V4_INK_COLLECTION_PREPARATION.md`, its helper and tests. Local preparation is `reference-prep-a-output/`, including 2,145 native source-only screening tile PNGs. The exact frozen sampling remains 96 SHA-ranked spatial anchors plus up to 32 independently screened motif nominations. No official anchors have been selected: eligible human roster, frozen training exclusions and completed independent source screening are absent. Exhaustive source-only screening tiles are preparation material, not sampled evaluation cases. UNKNOWN/ABSTAIN are retained; MIXED is represented by multiple valid physical-content labels. Observed physical content never automatically establishes ownership.

The offline helper validates separate signed A/B submissions and freezes before disagreement or adjudication. Synthetic labels exist only in tests. File hashes and read-only receipts do not establish identity, enforce private sessions or prove independence; human custody and eligibility checks are required.

## B: physical anchor collection

Track B commit `4a0d725db25d55e6a3aa5753b44f8b588f24091a` on `feature/v4-independent-anchor-validation` contains `docs/V4_ANCHOR_COLLECTION_PREPARATION.md`, its helper and tests. The ten previous source crops and case selection are byte-preserved. Local preparation is `reference-prep-b-output/`; distribute only its blind packet and the recipient's draft, never the coordinator outputs or opposite session.

Intervals retain uncertainty and unknown observations. Page pixel-index-center coordinates, viewer conversion and physical head-body centers remain distinct from semantic pitch and unimplemented replacement glyph anchors. No offset tuning occurred. Collect and separately freeze both real human observations before comparison.

## Shared: harmony boundary

See [the boundary report](V4_HARMONY_BOUNDARY_DIAGNOSTIC.md). Three known events, six source/target objects and twelve declared synthetic controls were studied. Written root/bass/degree records survive self-round-trip 6/6; this is mechanical consistency, not independent semantic truth. Target spelling agrees with the existing V1/V3 implementation for 3/3 events. Canonical music21 realization matches the specification-based pitch-class record 0/6. Unsupported and ambiguous encodings reject. The unchanged full V3 guard still fails at bar 32 @ 3/4; this issue is not fixed or waived.

Local diagnostic output `harmony-boundary-complete/boundary-report.json` is coordinator-only. Independent MusicXML review and dependency reproduction must precede any runtime boundary proposal. Printed equivalence, voicing, playback and rendering require separate evidence.

## Provenance, validation and next collection

All 28 shared evidence hashes and all three frozen protocol hashes were verified unchanged. Source manifest SHA-256: `f9e4b3e951e15609051b03530839326d99d7320865f45a82ade7501d0fdc2948`. Each preparation binds its own protocol, packet and source artifacts. Real outputs remain untracked; no answer key is included in a distributed packet.

Targeted V4 plus V3 music/gate tests: B **329 passed, 1 skipped**; shared **325 passed, 1 skipped**. The skipped existing test requires external MuseScore. A **355 passed, 1 skipped**. Staged and working-tree `git diff --check` passed in all three worktrees. No Full Acceptance or Audiveris rerun occurred.

Recommended next step: recruit eligible independent humans, freeze A's roster/training/screening in protocol order, then collect separate A/B labels for both tracks. In parallel arrange blinded MusicXML interpretation review. No architecture decision is supported until independent evidence exists. Preserve unknowns and report disagreement rather than forcing agreement.

No source raster was edited, no finished score or renderer/B2 was produced, no V1/V3 production behavior or V4 acceptance rules changed, and no API/frontend route, merge or deployment occurred.
