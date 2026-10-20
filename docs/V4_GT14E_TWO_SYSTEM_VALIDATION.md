# GT-14E — Two-system integration and visual validation

GT-14E produces actual A-major and G-major standalone previews for printed measures 1–8. It reuses frozen notation rather than engraving or correcting any musical content. The integration is **byte-identical to GT-14D's existing full-coordinate combined alpha**, now shown as two systems together.

Base: `c300e0217f1a36cecb930c55d67a2dd75408ea12`. Branch: `experiment/v4-gt14e-two-system-validation`. Worktree: `/private/tmp/capomatic-v4-gt14e`. Final revision is the commit containing this report, obtainable with `git rev-parse HEAD` on this branch.

Understood as: retain the owner-confirmed inventory and original registration, validate the joined preview without retuning it, inspect G's dense areas, and report export gaps. No new source interpretation, notation, source removal or production renderer is authorized.

## Frozen source and assembly

Source: original Bb PDF page 2 raster; SHA-256 `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`. The source PNG is 2520×3564 RGB and remains unchanged. Only that Bb raster is used for visual source comparison. No A/G reference page was accessed for prediction, comparison or retuning.

The [protocol](V4_GT14E_PROTOCOL.json) was saved before output generation. It uses page-coordinate masks on the existing 2520×1100 research canvas:

1. Copy y<700 from the frozen GT-13A.6 layer, which equals the GT-13A.5 first-system mask plus its confirmed outgoing tie segment.
2. Copy y≥700 from GT-14D's combined alpha, retaining the entire second system, incoming tie and six confirmed continuation marks.
3. Require the union to equal the complete frozen GT-14D combined alpha byte for byte.

The split is in blank inter-system space; no glyph, staff or lyric is translated. All component masks remain in their original page coordinate system. Shorter masks are zero-padded. A full-page GT-12 chord mask is cropped only through proven-empty padding; any nonzero ink outside the analysis canvas causes rejection. The initial `gt14e-output/` development attempt stopped at that input-size check before producing predictions; the final run uses the lossless padding check. No score geometry or acceptance threshold changed.

The displayed viewport is page `[130,310,2430,1030)`, 2300×720 pixels. Each PNG has a separate 140px diagnostic banner, producing 2300×860 images. Mapping is `PNG x = page x − 130`, `PNG y = page y − 310 + 140`, scale 1. These are cropped research previews, not full-page exports. The comparison source crop includes a small amount of following-system context at its lower edge; no third system is rendered in predictions.

## Content and registration

| Item | First system | Second system | Total retained |
|---|---:|---:|---:|
| Note/rest events | 26 | 13 | 39 |
| Chord symbols | 2 | 3 | 5 |
| Korean syllables | 36 | 14 | 50 |
| Lyric continuation marks | 4 | 6 | 10 |

Counts refer to the frozen owner-confirmed inventory and preserved render layers. They are not a fresh independent optical event count. No additional notes, chords, syllables or endpoints were invented.

Source-derived horizontal boundaries remain first-system `[159,760,1375,1783,2400]` and second-system `[159,639,1598,1961,2397]`. Measure widths are respectively `[601,615,408,617]` and `[480,959,363,436]`. Internal barlines are **not** forced to align vertically across systems with different original measure widths. Integration translation and width change are 0px; actual alpha is unchanged. Original staff polyline metadata is retained without flattening or stretching.

The source middle-staff separation at page x=200,1200,2300 is approximately 350.09999, 350.09975 and 350.09949px. These are evaluations of the retained source polylines, not independent raster line re-fitting. Source-derived staff metadata and glyph x/y registration change by 0px in integration. The correctness of the original detected staff/measure geometry is not independently revalidated by this identity-transform test. Existing notehead maximum raster-anchor residual remains the inherited 0.5px per axis; no new head rasterization or optical-anchor validation is claimed.

First-system lyric baselines are 624/670px before frozen displacement. A shifts are `[0,0,0,0]` by measure; G shifts are `[0,8,0,9]`. Measure 3 stays unchanged. Second-system baselines remain A 963/1008px and G 971/1016px. Chord alpha bounds are recorded in the validation JSON and remain at their frozen source-derived positions.

## Cross-system tie

The confirmed source Bb3 at m4 onset 3.75, duration 0.25, tie START continues to m5 Bb3 whole note at onset 0, duration 4, tie STOP. Frozen source curves 4818/4798 and both rendered segment masks are retained. A endpoints remain A3→A3; G endpoints remain G3→G3.

Outgoing and incoming curves remain separate visible segments. There is no connector through the physical system gap. Target pitch, order, duration and START/STOP signatures match the frozen semantic evidence. Tie/lyric contacts are 0 in both targets. These checks preserve the earlier owner-confirmed connection; they do not invent or newly classify an endpoint.

## Actual alpha contacts and clipping

The 40 frozen first-system text components are losslessly placed using only the prior displacement records, then required to equal the saved GT-13A.5 lyric alpha. The second system reuses 14 syllable masks plus all 6 confirmed extenders. All 60 lyric components (50 syllable glyphs plus 10 continuation marks) are present in the final alpha. The 5 chord text masks are counted separately among notation obstacles, not in those 60 components.

“Independent” masks here means separately persisted render layers, not independently human-verified evidence. Notation obstacles use separately persisted event, chord, header, rest, ending/repeat and tie masks, plus conservative actual-alpha staff bands. Lyrics are **not subtracted from notation** to infer a zero-contact result. Every nonzero alpha value, including faint coverage, counts. Staff/head/stem/beam/ledger contacts belonging to the same connected notation are not falsely treated as unrelated collisions.

| Measurement | A | G |
|---|---:|---:|
| Lyric components/notation unique contact pixels | 0 | 0 |
| Lyric-component pair contacts | 0 | 0 |
| Minimum text/notation ink-center distance | 2px | 2px |
| Cross-system layer contact pixels | 0 | 0 |
| Gap between first-system ink bottom and second-system ink top | 46px | 37px |
| Ink in blank page-y interval [700,720) | 0 | 0 |
| Clipped text or preview ink | 0 | 0 |
| Independently stored notation-layer contact | 44px | 15px |

The 46/37px values measure the blank vertical interval between complete system ink bounding boxes, not local lyric spacing. The 2px values are minimum Euclidean pixel-center distances from lyrics to notation; they are not pixel-edge clearances.

The last row is the **intentional m5 whole-note head/ledger intersection**, exactly matching the earlier GT-13A.6 contact count. No other contacts occur between the coarse independently persisted notation masks. The postfreeze `notation-component-contact-audit.json` records exact pairs. Contacts inside a previously merged note/stem/beam layer are inherited from earlier component gates rather than exhaustively re-enumerated here. Thus the report does not certify a new global per-symbol collision audit or professional engraving quality.

All 80 retained coarse component masks are supported by the integrated alpha. Full mask bounds fit the display viewport. Detail crops intentionally frame only parts of the staff and are not used to declare full-canvas clipping.

## Actual visual review

The actual integrated A/G PNGs and four native G details were opened after prediction freeze. They were compared with the original Bb source as source evidence, not with A/G reference geometry.

- A: **ACCEPTABLE_FOR_EXPERIMENT_WITH_LIMITATIONS**. Both systems, headers, chords, lyrics, repeats, local ties and separated cross-system tie segments are distinguishable.
- G: **READABLE_BUT_NEEDS_VISUAL_REFINEMENT_REVIEW**. At m2 the low D3 sits very close above 마, and at m4 above 시. The inherited 2px minimum passes the existing contact/clearance checks but gives limited optical breathing room. Adjacent first-system syllables also look crowded at the preserved source horizontal anchors.
- G m5: the open head, ledger lines, incoming curve and two continuation marks remain distinct in the native detail.
- G m6–7: local ties, ledger lines, Korean rows and both-row continuation marks remain distinguishable, but the lower-register area is visually dense. Inherited sloped beam raster edges also appear uneven in close-up; no beam geometry was retuned.

The source comparison also exposes content outside the frozen music/lyric inventory: section text, composer/transcriber credit and the printed measure-number label are not recreated in these standalone layers. Their absence is disclosed rather than counted as a verified full-source reconstruction.

No visual spacing, note geometry, lyric baseline or threshold was changed after this inspection. These are **agent judgments**, not independent optical validation, musician acceptance or owner acceptance of the new PNGs.

## MusicXML continuation gap

The frozen source and A/G MusicXML each contain 50 `<lyric>` elements and 10 note `<tie>` elements in the first eight measures, but **0 `<lyric><extend>` elements**. Ten continuation marks are present visually through the diagnostic rendering contracts and JSON associations. Note ties alone are not an explicit serialization of the lyric continuation instructions.

`lyric-extender-serialization-audit.json` records the exact file hashes and counts. No new MusicXML is exported and no production pipeline is modified. An explicit research serialization/roundtrip contract remains necessary if these previews are later exported as editable notation.

## Separate verdicts and blockers

- **SOURCE_VERIFICATION:** listed content is OWNER_VERIFIED_SOURCE; independent source recognition completeness remains UNVERIFIED.
- **SEMANTIC_CORRECTNESS:** unchanged V3 full guards and exact event/lyric/tie signatures PASS. This is transposition consistency, not recognition ground truth.
- **RENDERING_COMPLETENESS:** all frozen first-two-system inventory layers are retained, including six second-system extenders and the confirmed m4→m5 tie. It is not full-score or continuation-export completeness.
- **VISUAL_READABILITY:** A is acceptable for experiment with limitations; G is readable but requires visual refinement review. Zero alpha contacts do not imply professional optical spacing.
- **REMAINING_UNSUPPORTED/UNVERIFIED:** explicit MusicXML lyric-extender serialization; new exhaustive within-group per-symbol optical/collision validation; independent musician review; content beyond measure 8/full-score readiness. No newly encountered symbol was silently omitted or simplified in this integration.

Overall: **TWO_SYSTEM_PREVIEW_VALIDATED_WITH_VISUAL_LIMITATIONS**. The images remain developer-only, incomplete and not for performance or printing.

## Outputs and validation

Final untracked directory: `/private/tmp/capomatic-v4-gt14e/gt14e-final-output/`.

- `A-two-systems.png`
- `G-two-systems.png`
- `Bb-A-G-two-system-comparison.png`
- `G-detail-m2-ledger-tie-lyrics.png`, `G-detail-m4-outgoing.png`, `G-detail-m5-incoming.png`, `G-detail-m6-m7-ledger-tie-lyrics.png`
- `two-system-visual-validation.json`: frozen pre-inspection geometry/contact metrics; its visual field is intentionally pending at freeze time.
- `visual-inspection-report.json`, `final-validation.json`: authoritative post-inspection readability verdicts.
- `notation-component-contact-audit.json`, `lyric-extender-serialization-audit.json`, `semantic-integrity.json`, input/prediction freezes and `preservation-verification.json`.

[GT14E_VALIDATION.json](evidence/GT14E_VALIDATION.json) commits compact results and image hashes, not copyrighted rasters or full score XML.

Targeted regressions: **437 passed, 1 skipped**. The existing skip requires external MuseScore. Ten new tests cover exact page-coordinate assembly, rejection of altered/overlapping/misaligned inputs, removal of empty padding only, independent faint-alpha collision detection, pair contacts/clipping, deterministic integration and read-only MusicXML gap inspection. Full Acceptance was not run.

Unchanged V3 guards pass for source roundtrip, A/G in-memory transposition and frozen serialized targets. Event order, pitch shift, duration, voice, lyric and tie signatures are preserved. Historical GT-12 prediction freeze, GT-13A.3–6 and GT-14A–D artifact bindings/directories are hash-verified unchanged. The current prediction freeze and original source hash also match. `git diff --check` passes.

Reproduce with existing local inputs and a fresh output directory:

```bash
cd /private/tmp/capomatic-v4-gt14e
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt14e_two_system_validation \
  --out /private/tmp/capomatic-v4-gt14e/gt14e-repeat-output
```

Next step is a separately scoped visual review/refinement study for G's low-register lyric clearance and dense syllable spacing, followed by independent musician review. It must preserve the confirmed musical inventory and distinguish optical spacing from collision thresholds. MusicXML continuation export is a separate implementation contract.

No source ink removal, original PDF/raster edit, original lyric-pixel composition, protection-mask or ownership change, production V1/V3/API/frontend modification, merge or deployment occurred. No architecture winner or completed performance score is claimed.

A fresh-context wording check was used to separate independent layer storage from independent human evidence, define the 60 lyric components, and distinguish whole-system gaps from local ink-center clearance. It checked report clarity only, not images or musical truth. Historical reports remain unchanged rather than being rewritten to match the current integration scope.
