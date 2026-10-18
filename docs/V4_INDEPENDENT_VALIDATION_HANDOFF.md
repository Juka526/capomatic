# Independent validation: diagnostic handoff

No architecture winner is selected. These commits design reference experiments and explain bounded representation/coordinate causes; they do not change acceptance, ownership or editing rules.

| Work | Starting revision | Focused result |
|---|---|---|
| Track A annotation design | `817c43af19cc91a6b145f244e191ed8ee695ea05` | Source-first sampling independent of guard outcomes; physical content, processed support and ownership remain separate |
| Track B anchor study | `1a332faaf6e30b6f7645ad0bf3d9f41e915f8ac9` | All five old-plan discrepancies decomposed; source-only reference packet, no inferred physical pivots |
| Shared integrity study | `974acba9ca4cd7eeb797a6522afbbedba13b07ac` | Bars 4/20 kind alias normalization; bar 32 equivalent XML constructions plus identified music21 realization mismatch; full guard still FAIL |

## Immutable references

- A: branch `feature/v4-independent-ink-validation`, commit `144a4e21cb76d75f25b233a4caada64a4aaf7fbf`. [Report](https://github.com/Juka526/capomatic/blob/144a4e21cb76d75f25b233a4caada64a4aaf7fbf/docs/V4_INDEPENDENT_INK_VALIDATION.md), frozen protocol SHA `2a04b99dd6b9fc2fae38d43efebfb56355e76376872f7a7ad581c2c7c3c597b6`.
- B: branch `feature/v4-independent-anchor-validation`, commit `0b27842a14cf5db364653bd41d212d40665ddf6a`. [Report](https://github.com/Juka526/capomatic/blob/0b27842a14cf5db364653bd41d212d40665ddf6a/docs/V4_ANCHOR_REFERENCE_VALIDATION.md). Frozen protocol SHA `25057996c46ceec83720fe95bc447015002b9bf826e83924e16b8f359181d085`.
- Shared: branch `feature/v4-chord-integrity-diagnostics`; [root-cause report](V4_SHARED_CHORD_INTEGRITY.md), [frozen replay/reference protocol](V4_CHORD_REFERENCE_PROTOCOL.json) SHA `0714eafa5b99db11343425825ddf9d24c81a1351d07e8314eae1bf46d6d3614d`. The commit containing this handoff identifies the shared revision without a circular self-hash.

A sampling is **not executed**: the protocol fixes 96 spatial pixel anchors and up to 32 separately reported source-only diagnostic nominations. Two independent humans and a third adjudicator are required; mixed/unknown labels never become safe suppression evidence. The next implementation recommendation is an offline packet/immutable label workflow, not a guard change.

B has ten source-only crop cases, mixed five historical repairs plus five deterministic nonrepair controls, with empty independent A/B reference forms. Expected coordinates, repair identities and semantic results remain custodian-only. Source references must distinguish detected box center, pixel-index support centroid, observed physical body-center intervals, semantic staff coordinates and the undefined future placement anchor. The 7.4 px case is `10.65 semantic correction − 3.25 raw anchor residual`; other staves account for the slightly different values. **Zero independent annotations exist**. Next: collect blinded reference intervals before reviewing any planner change; do not tune a y offset to these notes.

The shared study uses the same 28 hash-bound artifacts plus the separately bound existing raw Audiveris MXL. Root, degree identity and slash-bass checks agree for the three XML event pairs under the MusicXML reference. This is a separate specification-based diagnostic, not human validation or a universal equivalence engine. Unchanged full guard results remain memory FAIL (bars 4/20/32), persisted XML FAIL (bar 32), fresh round-trip FAIL (bar 32). Future canonical import/export boundary and dependency investigation require separate review, genuine-semantic-change controls and unsupported-case rejection; no weakening is authorized.

## Pending independent evidence and risks

Human rosters, source-only observations, signed freezes, independent adjudication and later untouched multi-score evidence are still required. An annotator must not see this handoff, root-cause reports, full coordinator protocols or candidate results before primary labels freeze. Give only the allowlisted source packet and instructions. A model's answer, helper-generated coordinates or music21's `.pitches` are not independent physical references. Arithmetic decomposition does not resolve occluded heads, glyph placement, staff ownership, masks, beam/curve layout or rendered collisions.

No acceptance pass or future implementation is implied. A causal claim about the source contrast guard remains provisional; B's physical anchor remains unvalidated; the shared harmony finding is bounded to checked root/degree/bass fields rather than recognition or printed output. Recommended next work remains independent annotation and a separately reviewed boundary/anchor design, without choosing A or B.

## Validation and safety

- A: 293 passed, 1 existing MuseScore-unavailable skip; frozen JSON/population/input checks pass.
- B: 309 passed, 1 same existing skip.
- Shared: 295 passed, 1 same existing skip; current V3 guard source hash explicitly checked and unchanged.
- `git diff --check` passes for each focused worktree; no Full Acceptance or recognition rerun.

Untracked diagnostics stay in new `validation-a-output/`, `validation-b-output/`, `validation-integrity-final/` directories under their respective new validation worktrees. Original worktrees/branches and input source artifacts remain unchanged. No source raster editing, renderer/B2, V1/V3 production modification, feature flag, API/frontend change, merge or deployment occurred.
