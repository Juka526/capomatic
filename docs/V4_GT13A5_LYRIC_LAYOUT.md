# GT-13A.5 collision-safe Korean lyric layout

**FULL_SYSTEM_INCOMPLETE.** The frozen G-major 105 lyric/music contact pixels are reproduced, then eliminated by lossless integer translation of lyric masks only. A remains unchanged. Both local and whole-system alternatives pass the declared spacing predicate; the final A/G predictions use the preregistered local strategy. This resolves the specified layout collision, not the outgoing tie or full-score readiness.

Base: `2be100658f716f766270cde676d65fa80e38f176`.
Branch: `experiment/v4-gt13a5-lyric-layout`.
Worktree: `/private/tmp/capomatic-v4-gt13a5`.
Final commit SHA is provided in delivery. No branch was merged.

## Frozen baseline and declared rule

The complete GT-13A.4 prediction-freeze manifests are checked before analysis. Frozen event alpha, header alpha, staff/bar scaffold, both chord masks, 34 new lyric masks and six GT-12 m3 lyric masks reconstruct the **entire frozen notation alpha byte-for-byte**. Source PNG SHA-256 remains `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de` (original Bb PDF page 2).

Before any new layout, exact nonzero-alpha support reproduces:

| Target | M2 D3 / upper 마 | M4 D3 / upper 시 | Unique total |
|---|---:|---:|---:|
| A | 0 | 0 | 0 |
| G | 60 | 45 | 105 |

These are actual rendered ink contacts, not broad protection envelopes. An initial exploratory filename glob also included the stored collision-summary mask; the corrected component-only selection excludes it. The reproducible helper requires the 40 actual lyric components and the 60/45 split. No evidence or policy changed.

[Protocol](V4_GT13A5_PROTOCOL.json) was written before the new predictions. All alpha values greater than zero count as ink. Only integer `dy >= 0` is permitted; `dx = 0`. Both rows and continuation marks in each group receive the identical displacement. No font, glyph, alpha value, syllable or association is regenerated.

Let L be lyric pixel support and F all fixed score ink, including musical events, staff, barlines, header and chords. Let D(F) be its one-pixel 8-neighbor dilation. A displacement d is forbidden when `(L + (0,d)) ∩ D(F)` is nonempty, or when it contacts baseline neighboring lyric support. This dilation is only a clearance obstacle, never emitted ink or source ownership. It guarantees minimum pixel-center distance of at least 2px; the conservative distance between occupied unit pixel squares is at least `2 - sqrt(2) = 0.585786px`.

The finite domain is every integer from zero through `720 - group_bottom`, inside original page-coordinate viewport `[130,310,2430,720)`. The helper evaluates the **entire** domain, records all forbidden/feasible offsets, and selects the minimum. It does not increase offsets in response to visual results or change thresholds. The local strategy tests baseline neighbors, then rejects any final inter-group collision; it does not search alternate shifts after failure. Both row spacing and horizontal anchors are invariant. M3 cannot move locally.

Synthetic controls passed before the score run: minimum-offset proof, an overlap-free but too-close negative control, initially clear geometry, row/marker invariance, global m3 disclosure, deterministic output, invalid/noninteger displacement, clipping, impossible domain, immutable m3, neighboring lyrics, and preservation of alpha values 1 and 254.

## Measured layout results

All displacements below are downward in original source-page pixels.

| Candidate | M1 | M2 | M3 | M4 | Actual lyric/music contacts | Lyric/lyric contacts | Minimum ink-center distance |
|---|---:|---:|---:|---:|---:|---:|---:|
| A local (final) | 0 | 0 | 0 | 0 | 0 | 0 | 2px |
| A whole-system | 0 | 0 | 0 | 0 | 0 | 0 | 2px |
| G local (final) | 0 | **8** | 0 | **9** | **0** | 0 | **2px** |
| G whole-system alternative | 9 | 9 | **9** | 9 | **0** | 0 | **2px** |

For G local m2, all offsets 0–7 are forbidden; m4 offsets 0–8 are forbidden. For G global, offsets 0–8 are forbidden. Thus these are measured minima within the declared downward integer translation contract, not claims of a global engraving optimum. Unchanged horizontal anchors mean neighboring measures do not introduce a cheaper hidden placement. Both rows move together: their baseline separation is unchanged.

There is no clipping, lost alpha or changed Korean glyph bitmap in any candidate. All 36 syllables, four continuation marks and their associations are retained. The **local m3 entire native region** `[1374,310,1783,720)` matches the frozen baseline exactly. The global G alternative deliberately moves m3 lyrics +9px on its new canvas; it does not replace or modify GT-12/13A.4 historical output. A local/global score alpha is identical.

The fixed 26 owner-verified musical events, rhythms, voices, pitches, local ties, stems, beams, rests, ledgers, original x coordinates, staff geometry, both chords and header masks are reused unchanged. The frozen notehead maximum residual **0.5px** is inherited by byte-identical music masks, not presented as a new optical measurement. No musical geometry or pitch calculation is recalibrated.

## Visual inspection and separate completeness levels

After prediction hashes were frozen, the assistant inspected the actual comparison sheet and global G PNG. A is unchanged in the notation viewport. G's previously contacting first low notes are separated from 마/시. Both rows and continuation marks are legible. The local result has small visible baseline steps (+8/+9px at affected measures); global G is more vertically continuous across measures but changes m3. The predeclared final choice remains local to preserve m3.

**VISUAL_QUALITY: ACCEPTABLE_FOR_EXPERIMENT for this scoped spacing change.** A 2px ink-center gap remains visually narrow. Font proportions, thin local ties, beam raster edges and overall engraving quality still require musician review. This is agent visual inspection, not independent human optical validation or professional engraving certification.

**SOURCE_VERIFICATION:** The listed 26 events, two printed chords, strings and syllable associations retain OWNER_VERIFIED classifications. No new independent labels were collected; absence of all possible unlisted symbols is not certified. **RENDERING_COMPLETENESS: INCOMPLETE.** The outgoing cross-system tie destination remains explicitly deferred by the owner, and no destination, completed curve or stub was invented. The rendering remains **FULL_SYSTEM_INCOMPLETE**, not printable or performance-ready.

## Validation and preservation

- **253 passed, 1 skipped**: new synthetic layout tests plus existing GT-04/05/06/07/11/12/13A/13A.2/13A.3/13A.4 and V3 music/gate regressions. The existing skip concerns external MuseScore availability. No Full Acceptance.
- Unchanged full V3 guard reexecuted on frozen source/target MusicXML and on freshly transposed source copies: A −1 and G −3 pass in memory and after serialization. Full lyric signatures remain equal. These checks do not establish independent recognition completeness.
- Source and frozen prediction hashes match. Before/after file manifests check GT-12, GT-13A, GT-13A.3, initial/final GT-13A.4. GT-13A.2 preservation is also checked through the prior GT-13A.4 input manifest in the final preservation audit. Earlier historical worktrees are never written.
- All 40 final component alpha tiles are independently rechecked against original tiles. Saved notation unions match recomputation, local m3 native pixels match, and no duplicate lyric contacts are hidden.
- `git diff --check` and formatting checks pass. Only new research code, tests, protocol and this report are committed. All score rasters, MusicXML and diagnostic masks remain untracked.

## Artifacts and reproduction

Developer outputs: `/private/tmp/capomatic-v4-gt13a5/gt13a5-output/`:

- `original-bb.png`, `baseline-g-collision.png`
- `candidate-local-g.png`, `candidate-global-g.png`
- `predicted-a.png`, `predicted-g.png`, `comparison-contact-sheet.png`
- `lyric-layout-metrics.json`, `collision-before-after.json`, `layout-differences.json`
- `visual-inspection-report.json`, `validation-summary.json`, `preservation-verification.json`
- Input/prediction freezes, exact local/global alpha unions and unchanged V3 guard reports.

All predictions carry developer-only/incomplete/not-for-performance warnings. Original source is shown only as an untouched comparison crop; new notation is rendered on white standalone canvases. Caption pixels remain in a separate panel band.

Run from this worktree, with the retained historical local evidence and existing environment:

```bash
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt13a5_lyric_layout --out gt13a5-new-run
```

The helper rejects an existing output directory. Reproduction requires the prior untracked evidence directories; the code alone does not contain copyrighted score inputs. Post-freeze visual review and preservation notes describe this inspected run and are not fabricated automatically for a future run.

Next work is to review the local baseline steps versus the disclosed whole-system alternative, then separately verify the outgoing-tie destination and develop its cross-system contract. No repeat lyric confirmation is required. No original ink removal, original lyric-pixel compositing, protection-mask change, ownership promotion, V1/V3 change, API/frontend work, merge or deployment occurred.
