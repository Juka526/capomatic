# GT-15B: owner-confirmed third-system rendering

The standalone A/G previews now display the confirmed third-system notes, chords, both Korean lyric rows and 11 continuation marks. The first three systems contain **59 owner-confirmed note/rest events, seven chords, 70 lyric syllables and 21 continuation marks**. All five disputed SIG objects remain unclassified and are not rendered as separate articulations. The previews remain developer-only and incomplete.

Base: `584b03f1ea5624c6d9d03ac57878d8d8d0b5a6a5`.
Branch: `experiment/v4-gt15b-confirmed-third-system`.
Worktree: `/private/tmp/capomatic-v4-gt15b`.
The commit containing this report identifies the final research revision. `V4_GT15B_VALIDATION.json` binds the frozen outputs and measured results.

## Owner evidence and correction

The actual user approval message is preserved verbatim as UTF-8 text with a terminal newline in `docs/evidence/GT15B_OWNER_APPROVAL.txt`. No signature or timestamp was invented. `GT15B_OWNER_BINDING.json` binds its SHA-256 to the GT-15A packet freeze, checklist and source-review image. The original packet and every blank historical answer field remain unchanged.

The derived `owner-interpretation-layer.json` separately records 63 owner-approved checklist items: 20 events, six ties, four chord/absence decisions, 20 lyric associations, 11 continuation marks, the m8/m9 ending relationship and the m10-upper-onset-1 no-dash observation. The single correction is `m11-row1-syllable-3`: **을 → 은**, onset **3 unchanged**. The old candidate survives separately. Four broad additional/absence questions were not separately attested; no blanket source-completeness claim is inferred.

The five withheld items remain `UNRESOLVED_CLASSIFICATION_EXPLICITLY_WITHHELD`:

`sheet#1:5833`, `5841`, `5896`, `5902`, `5903`.

Their original IDs, bboxes, shapes and relations remain observations. Some of their source windows overlap approved continuation marks. Those marks are rendered once from their own explicit approval; this does not reclassify the SIG objects. No TENUTO/ACCENT glyphs or duplicate lyric glyph strokes are added. Raw `candidate_status`/blank response fields and reused tie-record provenance retain their historical values; the new `interpretation_status` and actual approval binding supply current authority.

This is **OWNER_VERIFIED_SOURCE**, not independent ground truth. One actual approval message was recorded; independent human labels remain zero. No Track A ownership or original-pixel replacement permission follows from it.

## Source and semantics

The original Bb PDF page 2 remains the source. Its unchanged 2520×3564 RGB raster SHA-256 is `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`. OMR SHA-256 is `857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638`; graph SHA-256 is `f8725c39beaaecc877ccf48b803b79a419c2d6e60aa73bc9428a39de11596508`. No A/G reference pages were read for prediction or retuning.

Printed measures 9–12 retain all 20 music events and six ties. Chords are newly supplied by owner confirmation, not improved OCR:

| Source decision | A target | G target |
|---|---|---|
| m9: no new printed chord | No new event | No new event |
| m10: Eb major | D | C |
| m11: no new printed chord | No new event | No new event |
| m12: F major | E | D |

Chord glyphs retain the measured source chord's left/top placement rather than attaching to a later note. Actual ink widths are D=28px/E=24px in A, C=25px/D=28px in G; none exceeds its measure bounds.

Upper lyrics are **풀은 마르고 꽃은 시드나**; lower lyrics are **전능하신 주 거룩하신 왕**. The 20 confirmed syllable/onset associations replace four sparse/mixed OMR lyric observations in a **new research source MusicXML only**. There is no new syllable at a tied STOP, and no invented upper m10 onset-1 dash. The original recognized artifact is preserved. Eleven separately approved source continuation bounds create eleven new stroke components, using the existing 2px extender contract.

The owner-confirmed first/second-ending relationship is retained. Existing m8 first ending/backward repeat, m9 open-right second ending and six new-system tie curve masks remain unchanged. Linear MusicXML measures and repeat notation are preserved; expanded playback is not implemented or claimed.

## Frozen geometry and deterministic lyric layout

GT-15 third-system alpha masks are reused directly, without rerendering notes, rests, stems, beams, flags, ledgers or ties. Actual head-mask bbox centers are checked again against transposed staff-pitch coordinates; maximum residual remains **0.5px per axis**. The 30 existing head/stem, beam/stem and flag/stem contact checks still have no missing connections. Their known intentional overlaps are unchanged.

GT-14E first-two-system alpha masks, lyrics, chords, extenders and cross-system tie remain intact. New components contact none of their pixels. The source-position `Pre-Chorus` label and its border introduce **587 pixels** in the previously blank y1015–1030 footer/context band on each new integrated canvas. Consequently this report does not claim whole-prefix RGB equality across that added label. Existing nonzero old-layer alpha values and all historical files remain unchanged.

The preregistered `V4_GT15B_PROTOCOL.json` fixes font identity, source measurement windows and the finite placement algorithm before predictions. Korean text uses GT-12 AppleGothic44, chords use FreeSerif40. Initial lyric baselines are 1323/1369, derived by the existing display-alignment measurement rule. This is not ink-ownership segmentation. Syllables stay centered at their associated source head x coordinates.

Both lyric rows and all 11 strokes move together by the **minimum feasible nonnegative integer dy**, selected by the unchanged GT-13A.5 complete displacement-domain function. It requires nonzero-alpha disjointness and one-pixel Chebyshev clearance from fixed notation, chords and the section label, with the lower bound ending at y1408 before the next source ending. No font shrink, horizontal adjustment or changed collision tolerance is used.

| Actual measurement | A | G |
|---|---:|---:|
| Whole new-system text displacement | 3px | 12px |
| Final upper/lower baselines | 1326 / 1372 | 1335 / 1381 |
| Lyric/notation alpha contacts | 0 | 0 |
| Pairwise lyric/extender contacts | 0 | 0 |
| New chord/section/music contact pairs | 0 | 0 |
| Minimum lyric-to-fixed ink-center distance | 2px | 2px |
| Conservative unit-square edge clearance lower bound | 0.586px | 0.586px |
| Chord-to-music minimum distance, m10 / m12 | 24.187 / 46px | 24.331 / 46px |
| Section border/text-to-music distance | 9 / 26px | 9 / 26px |
| New text to frozen first-two-system contacts | 0 | 0 |
| Clipping / lost translated glyph pixels | 0 / 0 | 0 / 0 |
| Horizontal anchor / row-spacing changes | 0 / 0 | 0 / 0 |

Distances are Euclidean pixel-center distances over actual nonzero alpha support, not optical-quality scores. The smaller edge-clearance figure is stated separately. All new text/mark masks are retained for reproducible pixel checks.

### Long section-label allocation

An initial run stopped **before any target PNG** because the old short-text helper's fixed six-font-size tile clipped `Pre-Chorus`. The failed output directory is retained. Only the research section-label function was added: it allocates the complete string using measured Pillow bounds, keeps integer raster phase, and losslessly translates the unscaled bitmap to the source word position. Existing music and short-text helpers are unchanged. Synthetic short strings are byte-identical to GT-12 text placement; long strings, determinism and clipping rejection are tested before the successful visual run. The protocol records this exception before target predictions. No result-driven optical offset was introduced.

## Integrity and preservation

Unchanged full V3 guards pass for the augmented source roundtrip and both A/G targets in memory and after MusicXML serialization. Each comparison contains 37 measures, 169 events and 13 harmonies. This whole-artifact denominator includes earlier owner additions and the new two chords; it is not an OCR accuracy result. Full event signatures, voices, durations, pitch transformation, tie roles and lyric signatures are preserved through serialization. Target event signatures match GT-15's frozen targets exactly, despite the separately added confirmed text/chords.

Tests: **485 passed, 1 skipped**, including 14 new synthetic tests for owner scope/correction, withholding, source augmentation, shared minimum displacement, impossible layout, approval tampering and long-label placement. The skip is the existing external MuseScore dependency. Full Acceptance was not run.

```sh
/private/tmp/capomatic-v4-venv/bin/python -m pytest \
  tests/test_v4_ground_truth_*.py tests/test_v4_paired_ground_truth_01.py \
  tests/test_omr_v3_music.py tests/test_omr_v3_gate.py tests/test_omr_v4_integrity.py -q
```

GT-14E/GT-15 freezes, the GT-15A owner packet, GT-14A source/previous owner evidence, original source/OMR/graph and pinned font hashes are verified. Complete historical input directory hashes are compared before/after. New prediction hashes are frozen **before** agent visual inspection. Post-inspection records supplement rather than rewrite the prediction freeze. `git diff --check` passes.

The new target MusicXML contains 20 lyric elements in m9–12 but **zero `<lyric><extend>` elements** for the 11 visual strokes. These are represented in research masks/JSON only. This existing export gap is disclosed; the production export pipeline is not changed.

## Separate verdicts and actual visual inspection

- **SOURCE_VERIFICATION:** requested 20 events, six ties, chords/absence decisions, syllable associations, continuation marks and ending relationship are owner-confirmed. Overall classification/completeness remains unresolved because five SIG objects are withheld and blanket absence was not separately attested. No independent source truth is claimed.
- **SEMANTIC_CORRECTNESS — structural consistency against the augmented research source:** unchanged full V3 transposition/serialization guards and explicit signatures pass. They do not prove recognition accuracy or completeness of every visual relationship; the 11 visual lyric continuations remain unencoded in MusicXML.
- **RENDERING_COMPLETENESS:** PNG preview coverage is complete for the approved scope, retaining 59 events/7 chords/70 syllables/21 continuation marks across three systems. MusicXML contains the 20 new lyric associations but does not encode the 11 new visual continuation marks. Unknown objects are not rendered as independent articulations. Original printed measure number 9 is not newly engraved in this update; remaining score systems are outside scope.
- **VISUAL_QUALITY:** the agent inspected actual A/G PNGs, the original/A/G comparison and a 3× low-register G detail. Text correction, both lyric rows, chords and all continuation marks are visible. The previews are readable for experiment, but low-register head/ledger-to-lyric clearance is optically tight. A's existing third sharp/second-ending numeral proximity and sloped-beam raster stair-steps remain unchanged. This is **agent visual review, not independent optical validation or professional engraving approval**.

Overall: **CONFIRMED_THIRD_SYSTEM_RENDERED_WITH_LIMITATIONS / INCOMPLETE_UNRESOLVED_SIG_OBJECTS**. No performance-ready or finished full-score claim is made. Next engineering work should separately address optical spacing and explicit lyric-extend serialization; the five withheld classifications require their own actual source decision, not automatic reclassification. No repeat confirmation of approved content is requested here.

## Actual artifacts

Local output directory: `/private/tmp/capomatic-v4-gt15b/gt15b-final-output/`.

- `A-three-systems.png`, `G-three-systems.png`, `Bb-A-G-comparison.png`
- `original-bb.png`, `G-low-register-detail.png` (3× display diagnostic only)
- `owner-evidence-binding.json`, `owner-interpretation-layer.json`
- `rendering-validation.json`, `semantic-integrity.json`, `spacing-supplement.json`
- `visual-inspection-report.json`, `preservation-verification.json`, `prediction-freeze.json`
- Per-component alpha masks and newly augmented/target MusicXML, all untracked

The approval file named in the owner binding is retained in this worktree's `docs/evidence/` and as a byte-identical post-freeze metadata copy beside the output binding; the packet paths refer to preserved local GT-15A inputs. This is not a standalone portable score/evidence archive. To reproduce prediction generation in a **fresh** output directory with those inputs:

```sh
cd /private/tmp/capomatic-v4-gt15b
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt15b_confirmed_third_system \
  --out /private/tmp/gt15b-new-run
```

The independence audit identifies a shared renderer/validator design and a candidate-exposed owner review. These checks establish reproducible internal consistency and scoped owner decisions, not a blinded accuracy benchmark. Independent musical or optical validation would require separately collected evidence; none was generated here.

Only research code/tests/protocols/owner evidence/report metadata are committed. Source score images, generated canvases, masks and MusicXML remain untracked. No original source editing, ink removal, original lyric-pixel compositing, protected-mask changes, Track A PARTIAL promotion, V1/V3 production changes, API/frontend routes, merge or deployment occurred.
