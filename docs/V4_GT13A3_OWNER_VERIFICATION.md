# GT-13A.3 owner source confirmation and GT-13A.4 preparation

**FULL_SYSTEM_INCOMPLETE.** The first-system music-event verification coverage is now **26/26 OWNER_VERIFIED_SOURCE**, including 22 events previously marked OMR_PROVISIONAL. Independent ground-truth labels remain **0**. Both A/G standalone PNGs display these same 26 events and add the newly confirmed measure-1 chord. Header/repeat engraving, outgoing-tie continuation and lyric associations remain incomplete.

Base: `fe8d7cbfaff53233b0c4f8a1a418cdde4ceb61b9`. Branch: `experiment/v4-gt13a3-owner-verification`. Worktree: `/private/tmp/capomatic-v4-gt13a3`. Final commit SHA is returned with delivery; no branch merges.

## Approval and immutable review context

The actual current user message is retained verbatim in [GT13A3_OWNER_APPROVAL.txt](evidence/GT13A3_OWNER_APPROVAL.txt), including the explicit source interpretation, evidence classification and restrictions. The [protocol](V4_GT13A3_PROTOCOL.json) pins its SHA-256. The producer copies the same bytes into the untracked research output and binds them to:

- Original Bb PDF page 2 raster SHA-256 `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`.
- Frozen native first-system source crop and GT-13A.2 source-event checklist hashes.
- The frozen GT-13A.2 prediction manifest and preserved review-context files.
- The original GT-12 m3 owner confirmation, SHA-256 `961c08e8ea1011e9fa3a4ab284b1171212192a9626bba7387e10c1cee46beb2d`.

This is **coordinator post-approval artifact binding**, not a claim that the owner digitally signed hashes or supplied a new independent transcription. No reviewer identity/signature was fabricated. No duplicate lyric confirmation was requested. Original GT-12 confirmation bytes and its checklist were not replaced.

`owner-normalized-checklist.json` represents the actual explicit owner list independently of the OMR rows. Promotion requires exact event kind, written pitch, onset, duration, count and tie-role agreement. Mismatches fail closed. The frozen semantic source is checked separately against every row; no pitch/rhythm repair is performed. Old OMR recognition/candidate/renderer fields remain historical observations and do not substitute for the new owner evidence. M3's original inventory entry is preserved exactly; the new approval updates only m1/2/4 music-event evidence. Root verification scope is now m1–4.

## Confirmed source content

| Measure | Notes/rests | Verification and chord context |
|---|---|---|
| 1 | Quarter rest; Bb3, C4, F4 quarters at 0/1/2/3 | OWNER_VERIFIED_SOURCE; newly confirmed Bb major, no suffix/slash bass |
| 2 | Quarter rest at 0; eighth rest at 1; F3/D4/C4/C4/C4/Bb3/C4 at 1.5/2/2.5/2.75/3/3.25/3.75 | OWNER_VERIFIED_SOURCE; C4 tie 2.75→3; no newly printed chord identified |
| 3 | Existing GT-12 quarter rest + Bb3/C4/F4 | Original OWNER_VERIFIED_SOURCE, F→E/D and both lyric rows unchanged |
| 4 | Same rhythm as m2, with final Bb3 | OWNER_VERIFIED_SOURCE; C4 tie 2.75→3; outgoing tie starts at last Bb3; destination/full cross-system geometry UNVERIFIED; no newly printed chord identified |

Durations for m2/4 are 1, 1/2, 1/2, 1/2, 1/4, 1/4, 1/4, 1/2, 1/4. There are **20 notes and 6 rests**, displayed without adding or dropping musical events. No new harmony is inferred in m2/4 and no chord-carry interpretation is added.

Previously approved Korean strings remain `OWNER_CONFIRMED_LYRIC_TRANSCRIPTION`. Exact m2/4 syllable-to-note associations are **PENDING**; their strings remain footer transcription context. The earlier provisional m1 syllable placement is retained in amber and conservatively remains unverified as an association: this message explicitly verifies notes/rhythm/chord but does not explicitly resolve that separate association. M3 lyrics and their verified associations are untouched. No words or missing syllables are invented.

## Rendering and chord semantics

All musical glyph geometry is imported from the frozen GT-13A.2 component PNGs; note x, pitch y, rhythm spacing, stems, beams/hooks, flags, rests, ledgers and two local ties are not re-engraved. Geometry/hash bindings are recorded. The source-verified musical ink is recolored black; amber distinguishes the unresolved m1 lyric placement. Recoloring is a diagnostic evidence cue, not a coordinate or glyph change.

For m1 chord placement, a source-only display-measurement window [380,350,450,414) was fixed in the protocol before rendering. The existing GT-12 `ink_bbox` placement method gives original Bb ink bounds **[402,370,438,399)**. This is alignment evidence only, never source-ink ownership. The unchanged GT-12 FreeSerif40 fixed-phase text renderer preserves ink left/top **[402,370]**:

| Target | New chord | Rendered bounds | Actual ink width / advance | Added-chord contacts / clipping |
|---|---|---|---|---|
| A major (-1) | A major | [402,370,431,397) | 29px / 29px | 0 / 0 |
| G major (-3) | G major | [402,370,430,397) | 28px / 29px | 0 / 0 |

Bb→A/G uses existing V3/V1 chord semantics. A separate research semantic source adds Bb at m1 offset 0 as measure-start harmony context; exact print position comes from source pixels and is not attached to the first pitched note (onset 1). This does not claim independently measured sub-beat harmony timing. The original GT-12 F harmony stays E/D in m3. No new recognition or target-reference access occurred.

The complete new chord alpha is checked against the existing notation/text/staff union, with zero nonzero-alpha contacts. It stays inside the fixed viewport and outside m3. M3's entire native image region is byte-identical to GT-13A.2; its original combined alpha and actual owner record are unchanged.

## Three completion levels and inspection

| Level | Current result |
|---|---|
| Source event verification | Listed 26 notes/rests and specified local ties/chords OWNER_VERIFIED_SOURCE; NOT_INDEPENDENT_GROUND_TRUTH. This does not establish an independent whole-score accuracy denominator or absence of all unlisted symbols. |
| Rendering completeness | INCOMPLETE: all 26 event bodies and two confirmed printed chords displayed; header/repeat, outgoing tie and lyric associations remain unresolved. |
| Visual quality | ACCEPTABLE_FOR_OWNER_VERIFIED_DIAGNOSTIC / NEEDS_REFINEMENT_FOR_USABLE_SCORE. Actual comparison PNG inspected by the agent after freeze; not independent optical validation. |

Both panels are 2300×820 with unchanged native 2300×410 notation viewports; source/A/G contact sheet is 2300×2460. Each has 15 diagnostic text items outside that viewport. Actual annotation/notation-region and annotation/ink contacts are **0**. Minimum pixel-center clearance to musical glyphs remains **A180px / G171px**, and to all score ink including lyrics/chords/staff **69px** both. These are actual nonzero-alpha distance measurements under the unchanged GT-13A.2 contract, not optical quality scores. Cached max head raster-anchor residual remains **0.5px**.

Agent visual inspection found the confirmed A/G chord at the original Bb print anchor, black musical groups in their original positions, unchanged m3, amber m1 lyric placement, and clearly separated m2/4 footer strings. Missing key/clef/repeat and outgoing tie prevent a usable complete score. Existing thin sampled ties and raster beam edges remain prototype quality.

## Validation and preservation

**226 tests passed, 1 skipped** (existing external MuseScore dependency). The 11 new tests cover content mismatch rejection, missing/duplicate events, changed local tie roles, unchanged original m3 record, lyric-association non-promotion, immutable source chord insertion, existing Bb→A/G transposition, correct measure-start context and absence of added m2/4 harmonies. Relevant GT-04/05/06/07/11/12/13A/13A.2 and V3 music/gate regressions pass. No Full Acceptance.

The unchanged full V3 guard passes:

- Owner-augmented source serialization at shift 0.
- A and G in-memory semantic transpositions.
- A and G MusicXML write/read roundtrips.

Each comparison reports **37 measures / 169 events / 9 harmonies**, no issues. Nine harmonies are the global augmented stream (previous eight plus m1 Bb), not a claim that all printed harmonies of the full score are recognized. All note/rest signatures across the full streams match frozen GT-12 targets, and existing lyric signatures remain identical. No guard was bypassed or relaxed.

GT-12, GT-13A, and both frozen prior GT-13A.2 output trees are hashed before/after and unchanged. The source raster and original source-crop PNG remain unchanged. Final outputs were frozen before visual review; review/validation/context-preservation reports are separate post-freeze metadata. `git diff --check` and formatting checks pass before commit.

## Actual outputs and GT-13A.4 preparation

Untracked `/private/tmp/capomatic-v4-gt13a3/gt13a3-output/` contains actual `original-bb.png`, `predicted-a.png`, `predicted-g.png`, `comparison-contact-sheet.png`, owner approval/checklist/binding, source inventory, owner-augmented source and target MusicXML, rendering report, exact alpha masks, integrity results and prediction freeze. Real score images/MusicXML are excluded from commits. A fresh reproduction is `python -m scripts.research.gt13a3_owner_verification --out NEW-output`; existing output directories are rejected.

GT-13A.4 is **prepared, not executed**. Its remaining inputs/contracts are: next-system evidence for the outgoing tie and a validated cross-system connection; clef/key/time/repeat engraving; exact m2/4 lyric associations (and explicit resolution of m1 placement if desired); musical/optical review of resulting complete notation. Existing lyric strings do not need reconfirmation. None of these follow from event-count or semantic-guard passes alone.

No original ink removal, original lyric-pixel compositing, PDF/source-raster changes, protection-mask relaxation, Track A promotion, V1/V3 production edits, API/frontend routes, merge or deployment occurred.
