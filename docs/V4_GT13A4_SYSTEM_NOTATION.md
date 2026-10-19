# GT-13A.4 first-system notation completion study

**FULL_SYSTEM_INCOMPLETE.** Actual A/G PNGs now contain treble clef, transposed key signatures, 4/4, opening repeat, all 26 owner-verified musical events, both confirmed chords, and the two Korean lyric rows with owner-confirmed note associations. The outgoing cross-system tie remains deliberately incomplete. **G has 105 measured lyric/music contact pixels and is BLOCKED for visual safety**; A has 0 such contacts. No spacing or tolerance was changed to hide this result.

Base: `9b44157a38964179a375dfc6a0ce6645e6e8e413`. Branch `experiment/v4-gt13a4-system-notation`, worktree `/private/tmp/capomatic-v4-gt13a4`. Final SHA is returned with delivery. This is standalone research, not original-ink replacement or production B2.

## Separate results

| Level | A | G |
|---|---|---|
| SOURCE_VERIFICATION | 26 listed events, 2 printed chords, lyric strings and m1/2/4 associations OWNER_VERIFIED; tie destination still UNVERIFIED | Same |
| RENDERING_COMPLETENESS | INCOMPLETE: actual header and aligned lyrics rendered; complete outgoing tie absent | INCOMPLETE: same plus blocked lyric/music contacts |
| VISUAL_QUALITY | ACCEPTABLE_FOR_EXPERIMENT, still needs optical/musician validation and complete tie | NEEDS_REFINEMENT / BLOCKED_COLLISION |

Independent ground-truth labels remain 0. Owner confirmation does not establish absence of every unlisted source symbol or independent optical accuracy. Existing notehead registration stays within the original 0.5px per-axis criterion; no note or rhythm coordinate was recalculated or moved.

## Immutable source and review stages

Source remains original Bb PDF page 2, first system, printed m1–4. Source raster SHA-256 `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`. No OCR/Audiveris rerun or A/G reference-page access. GT-12 and GT-13A.3 artifacts and prior GT-13A.2 evidence are hash-checked unchanged.

The initial header-only run is preserved under `gt13a4-output/`, with source-only `owner-review/` crops, proposed associations, outgoing-tie evidence, exact header masks and frozen predictions. Its original producer/header code and protocol snapshots are retained with matching hashes. Header-only output is not silently replaced by the subsequent owner-confirmed lyric run.

The owner then answered the actual review questions:

- Lyric associations: **“원본 대조 후 대응 후보 전체 확인”**.
- Tie destination: **“아직 미확인 — 목적지는 보류”**.

The question text, exact answers and question IDs are preserved in [GT13A4_OWNER_ASSOCIATION_REPLY.json](evidence/GT13A4_OWNER_ASSOCIATION_REPLY.json), hash-bound by [protocol](V4_GT13A4_PROTOCOL.json) and the final input manifest. This is OWNER_VERIFIED_LYRIC_ASSOCIATION, NOT_INDEPENDENT_GROUND_TRUTH. No invented identity, timestamp or human signature. This reply does not approve source removal or resolve the outgoing tie.

## Lyric association audit

Previously confirmed strings were reused without asking for transcription again. Source-only review crops include complete upper/lower lyric baselines and neighboring context. Initial candidates remain in the original frozen audit; the final audit records the owner's subsequent association confirmation.

| Measure | Syllable-bearing note onsets | Upper row | Lower row |
|---|---|---|---|
| 1 | 1 / 2 / 3 | 주 / 님 / 의 | 광 / 야 / 의 |
| 2 | 1.5 / 2 / 2.5 / 2.75 / 3.25 / 3.75 | 마 / 음 / 이 / 있 / 는 / 곳 | 꽃 / 을 / 피 / 우 / 시 / 고 |
| 3 | Existing GT-12 | 주 / 님 / 의 | 사 / 막 / 의 |
| 4 | 1.5 / 2 / 2.5 / 2.75 / 3.25 / 3.75 | 시 / 선 / 이 / 있 / 는 / 곳 | 강 / 물 / 을 / 내 / 시 / 는 |

Rests receive no syllables. In m2/4, C4 at onset 3 is a tied continuation of C4 at 2.75; it receives no new lyric token. A horizontal continuation marker is rendered for each row at the tied-stop note's original x. This uses the existing text renderer with U+2014, not an additional sung syllable or a claim to copy the original dash pixels. The final Bb3 in m4 carries the confirmed last syllables but no unverified continuation into the next system is engraved.

The research MusicXML stores the confirmed syllable starts. Tie continuation and marker placement are retained in the bound association audit; complete MusicXML extender encoding is not claimed.

After approval, a **new separately frozen run** under `gt13a4-final-output/` applies the unchanged GT-12 AppleGothic44 text registration, original note x and existing source-derived row baselines (not an optimized target layout). There are **36 syllables and 4 continuation marks**. M3's original confirmation and rendered native region remain byte-identical; m1 glyph positions are identical to their old masks, now rendered black following association confirmation. Newly typeset text is distinct from original lyric-pixel preservation.

## Actual header engraving

Treble and two-flat source key are persisted in MusicXML and SIG Inters 204/211. Forward repeat is persisted in MusicXML plus thick/thin bars 2/4 and repeat-dot relations 5577/5579. 4/4 is visible in the source and explicitly required by this task, but absent from raw Audiveris MusicXML; it is added only to a separate research semantic stream as source context. No recognition code changes.

Existing pinned FreeSerif is reused; no new font download/bundling. Actual glyphs are U+1D11E treble, U+266F sharp and two numeral-4 glyphs; repeat uses source-backed bar/dot geometry.

- Treble uses a declared **font-specific lower-bowl anchor (331,160) in 1000-UPM design units**, derived from the isolated outline before score rendering. It is placed on the original G4 staff polyline with the existing fixed-phase glyph registration. This is not a SMuFL anchor or independent optical validation.
- A key: F5/C5/G5 sharps, fifths +3. G key: F5 sharp, fifths +1. Y positions come from original staff polylines/interline and target diatonic positions, not reference-page pixels.
- Source key-left is retained; the repeat block shifts only enough to clear the extra sharp: **A +16px, G +0px**. 4/4 then fits before the unchanged first rest. Musical events, staff polylines and measure boundaries do not move.
- The old diagnostic DUMMY left frame at x160 is omitted from the new generated scaffold; the actual source-backed opening repeat is now engraved. This changes no original image pixels.
- Clef semantic-anchor residual is [0.086, -0.353]px in the real-sheet run, within 0.5px. Six synthetic conditions (interlines14/18/24 and integer/fractional origins) exercise both keys before score rendering. Actual glyph content, sharp counts, positions, two time digits, repeat orientation and clipping are checked.

Header-to-existing nonstaff notation contact pixels: **0 both targets**. Minimum header-to-prior-ink pixel-center distances: **A42.755px, G58.549px**. Header component-to-component contacts: 0. Staff crossings are intentional. Header font sizing/anchor choices remain experimental; mathematical registration is not proof of professional engraving quality.

## Outgoing tie evidence and explicit hold

Existing OMR has reciprocal `4818 right-extension→4798` and `4798 left-extension→4818`. The outgoing segment has LEFT head1852, staff1 pitch-position7, m4 Bb3 at onset3.75/duration0.25/tie-start. The incoming segment has RIGHT head1923, staff2 pitch-position7, m5 Bb3 at onset0/duration4/tie-stop. The next head is a persisted WHOLE_NOTE. Source curves, IDs and relations are retained in `outgoing-tie-evidence.json`; source-only crops show both ends and the next system's clef/key context.

This is **OMR_SUPPORTED_CANDIDATE_PENDING_OWNER**, not a new independently verified destination. The owner expressly deferred confirmation. No destination or complete cross-system curve is invented, no continuation/stub is rendered, and a validated cross-system renderer remains necessary even after later source confirmation.

## Actual collision findings and visual inspection

The confirmed-lyric source baseline rule was fixed before its real run. It was not retuned after contact measurements:

| Measurement | A | G |
|---|---:|---:|
| Displayed owner-verified musical events | 26 | 26 |
| Confirmed printed chords | 2 | 2 |
| Aligned lyric syllables / continuation marks | 36 / 4 | 36 / 4 |
| Unique lyric/music contact pixels | 0 | **105** |
| Lyric/lyric contact pairs | 0 | 0 |
| Lyric clipping | 0 | 0 |
| Diagnostic annotation/score contacts | 0 | 0 |
| Minimum annotation → musical ink center distance | 180px | 171px |
| Minimum annotation → all-score ink center distance | 69.354px | 69.354px |

G contacts are **60px at m2 F3→D3 with upper ‘마’**, and **45px at m4 F3→D3 with upper ‘시’**. With original x and source lyric baselines retained, the downward-transposed head reaches the lyric ink. These are exact nonzero alpha intersections, not broad text-envelope pairs. Masks are retained as `G-lyric-music-collision-mask.png`. No threshold widening, note movement, lyric-row shift or collision waiver was applied. Musical component masks remain unchanged; the composed G image is visibly unsafe at those two points and is labeled as an incomplete diagnostic.

The agent inspected the actual synthetic headers, header-only comparison and final A/G comparison after prediction freezes. Headers and A lyrics are legible for this experiment. G visibly collides at the two first low notes, so visual safety is BLOCKED. Thin local ties, beam raster edges and font-specific header choices still need musician/optical validation. This is agent visual review, not independent human optical certification.

## Validation and preservation

**242 passed, 1 skipped** (existing external MuseScore dependency), including GT-04/05/06/07/11/12/13A/13A.2/13A.3 and V3 music/gate regressions. New checks cover header scale/phase/determinism, key counts, repeat placement, invalid geometry, candidate lyric consumption across ties, unresolved-tie non-promotion, actual owner reply boundaries, no duplicate tied-stop token, m3 preservation, strict alpha collision reporting and full-system lyric signatures.

During test development, a test exposed that the reused GT-12 `lyric_signature` deliberately covers m3 only. This study adds a research-only **full_lyric_signature** over every part/measure/event. It checks all lyrics through source and A/G serialization, including measures outside m3. An earlier debug lyric run is preserved in `gt13a4-lyrics-preflight-output/`; final validated predictions have the same PNG bytes. This fix strengthens diagnostic validation and does not modify V3 or silently rewrite prior evidence.

Unchanged full V3 semantic guards pass in the header-only and owner-associated runs: source zero-shift roundtrip, A/G in-memory and A/G serialized results, each **37 measures / 169 events / 9 harmonies**, no issues. Event signatures remain identical to GT-13A.3 targets. Full lyric signatures and MusicXML roundtrips pass separately. These gates do not waive G's visual collision or the unresolved outgoing tie.

Historical GT-12, GT-13A.3, GT-13A.2 and initial GT-13A.4 outputs remain unchanged. Original source PNG and crop hashes match. No reference target pages were used. All diagnostics and copyrighted rasters remain untracked. `git diff --check` and formatting checks pass. No Full Acceptance.

## Outputs and next work

Final actual images: `/private/tmp/capomatic-v4-gt13a4/gt13a4-final-output/{original-bb.png,predicted-a.png,predicted-g.png,comparison-contact-sheet.png}`. The same directory contains the owner-approved lyric audit/reply binding, all newly rendered lyric masks, exact contact masks, semantic results, prediction freeze, visual inspection and validation summary.

Header measurements, exact header masks and source review crops remain under `gt13a4-output/`. Synthetic evidence is under `gt13a4-controls/`. Initial producer/protocol snapshots preserve the pre-owner-reply experiment. No old directory was overwritten.

Next engineering work requires an explicitly reviewed collision-safe lyric/layout contract for G while preserving the frozen note geometry, plus the still-deferred outgoing-tie destination and complete cross-system rendering contract. The owner-confirmed lyric strings and associations do not need duplicate confirmation. A separate optical/musician review is still required. No complete usable score is claimed.

No original ink removal, source PDF/raster changes, original lyric-pixel compositing, protection-mask relaxation, V1/V3 production edits, API/frontend routes, merge or deployment.
