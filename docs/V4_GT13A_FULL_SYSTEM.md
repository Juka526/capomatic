# GT-13A: first-system audit and explicit-gap standalone prototype

**FULL_SYSTEM_INCOMPLETE_WITH_EXPLICIT_GAPS.** Actual A/G PNGs show the entire first-system geometry, but only owner-confirmed measure 3 contains rendered musical content. Measures 1, 2 and 4 are explicitly labeled gaps. This is not a completed full-system score or an increase in verified rendered note coverage over GT-12.

| Completion level | Result |
|---|---|
| Source completeness | UNVERIFIED for the entire system; raw OMR is incomplete for chords and separate lyric rows |
| Rendering completeness | INCOMPLETE: 4 of 26 recognized events displayed; 22 withheld, not silently omitted |
| Visual quality | NEEDS_REFINEMENT for a full-system score; the partial diagnostic and cached m3 are readable in agent inspection |

## Isolation and source evidence

Exact base: `681f4a2dec0eb0dccc8e46eac6aac19f88c44fa9`. Branch: `experiment/v4-gt13a-full-system`. Worktree: `/private/tmp/capomatic-v4-gt13a`. The final commit SHA is reported at delivery. No branches were merged. [Protocol](V4_GT13A_PROTOCOL.json) fixes the Bb source PDF page 2, system 1 and printed measures 1–4 before rendering.

The existing frozen source raster is 2520×3564 RGB, SHA-256 `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`. Review crop [130,310,2430,720) is 2300×410 native pixels and contains the full first system and both visible lyric rows. No source edits, re-rasterization, OCR/Audiveris execution, font/model downloads or target-reference comparisons occurred.

GT-11 inventory bindings and GT-12 prediction hashes were checked. The complete current GT-12 artifact tree was hashed before and after this experiment and is unchanged. GT-02 source registration/event files were checked against their existing artifact manifest. Only Bb source fields are used; the bundled reference-page mappings are neither used nor exported into the source audit.

## Fixed-system content audit

`source-system-inventory.json` enumerates every recognized event with source ID, physical head/rest bbox, written pitch, onset/duration, voice, stem direction, accidental context, beams, ties, raw lyric items and status. Related SIG symbols/relations and original cubic curve evidence are retained. OMR agreement is not independent truth.

| Printed measure | Physical boundary candidates | OMR events | Rhythmic total | Source status | Rendering action |
|---|---|---:|---:|---|---|
| 1 | 160–760 | 4: rest + Bb3/C4/F4 quarters | 4 quarterLength | OMR_RECOGNIZED; content UNVERIFIED | Explicit gap |
| 2 | 760–1374 | 9: two rests + seven notes | 4 | OMR_RECOGNIZED; content UNVERIFIED | Explicit gap |
| 3 | 1374–1782 | 4: rest + Bb3/C4/F4 quarters | 4 | OWNER_VERIFIED from GT-12 only | Exact GT-12 reuse |
| 4 | 1782–2400 | 9: two rests + seven notes | 4 | OMR_RECOGNIZED; content UNVERIFIED | Explicit gap |

There are **20 recognized notes and 6 rests**, each in the recognized unspecified single-voice stream. Measures 2 and 4 have onsets 0, 1, 3/2, 2, 5/2, 11/4, 3, 13/4, 15/4 with durations 1, 1/2, 1/2, 1/2, 1/4, 1/4, 1/4, 1/2, 1/4. Their pitches are respectively F3/D4/C4/C4/C4/Bb3/C4 and F3/D4/C4/C4/C4/Bb3/Bb3. These are OMR observations, not newly owner-confirmed notes.

The owner confirmation applies only to measure 3, even though measure 1 has similar notes and upper lyrics. It does not propagate to other measures. Independent labels remain 0; no musical accuracy percentage or independently verified whole-system denominator is reported.

### Chords and lyric rows

Raw MusicXML has zero harmonies in these four measures. Agent source-image candidates are Bb near measure 1 and F near measure 3. Only F is OWNER_VERIFIED; its cached target E/D remains at the source chord location. No extra chord is inferred for measures 2 or 4, and apparent chord absence/carry is not certified.

Raw OMR contains 13 lyric items across the system: 3/6/0/4 by measure. Many strings merge the two printed rows, such as `주광`, `님야`, `의의` in measure 1. They are not usable as confirmed Korean rows. Source-only agent candidates, explicitly UNVERIFIED outside measure 3, are:

| Measure | Upper candidate | Lower candidate | Associations |
|---|---|---|---|
| 1 | 주 / 님 / 의 | 광 / 야 / 의 | Unverified |
| 2 | 마 / 음 / 이 / 있 / 는 / 곳 | 꽃 / 을 / 피 / 우 / 시 / 고 | Unverified; tied notes/extenders require review |
| 3 | 주 / 님 / 의 | 사 / 막 / 의 | Owner-confirmed to the three pitched notes; none on rest |
| 4 | 시 / 선 / 이 / 있 / 는 / 곳 | 강 / 물 / 을 / 내 / 시 / 는 | Unverified; tied notes/extenders require review |

The candidate table is neither a source correction nor human annotation. No candidate outside measure 3 enters the target PNGs.

### Required notation and support

- **Supported existing contracts:** calibrated filled heads, upward stems, ledgers, quarter rests, chord text and newly typeset Korean text. GT-07 single upward eighth flag and GT-06 uniform double-beam pair support remain available only under their established group contracts.
- **UNSUPPORTED for this complete-system attempt:** eighth rests; mixed eighth/sixteenth beam groups and partial hooks; tie rendering; cross-system tie endpoint handling; clef/key/time/forward-repeat glyph placement. Existing pair/flag capability is not promoted into support for these complete groups.
- Measure 2 has a C4 tie between offsets 11/4 and 3. Measure 4 has the same local C4 tie plus a final Bb3 tie start continuing beyond the system. SIG curve IDs `sheet#1:4788`, `sheet#1:4790`, `sheet#1:4818` and their head relations are retained, not reconstructed.
- The source treble clef and two-flat key are OMR_RECOGNIZED. The forward repeat is recognized in MusicXML. Printed 4/4 is an agent source-image observation but is absent from the recognized MusicXML context. These facts do not establish a validated glyph-placement renderer for the header. A/G key context appears as text only, explicitly marked as not engraved.

## Geometry and the failed preflight

Original staff polylines, including intermediate points and slope, are retained with the same width-2 diagnostic drawing contract used by GT-04/12. Physical boundary candidates come from the frozen GT-02 source registration; they are not accepted independent boundary ground truth. OMR bounds differ by up to 1px: [159,760], [760,1375], [1375,1783], [1783,2400]. The experiment reports this discrepancy rather than changing GT-12's measure-3 coordinates.

The first preflight stopped with `ValueError: Outside valid polyline domain` before producing predictions: the physical end boundary is x=2400, while staff lines end at x=2399. That failed output is preserved in `gt13a-preflight-polyline-domain-failure/`. No staff extrapolation, clamping or tolerance widening was introduced.

The subsequent run requires an explicit unique persisted staff-barline bbox for an outside-domain boundary. Object `sheet#1:4581` has bbox [2398,443,2402,518], containing x=2400. Its bounds supply a diagnostic boundary skeleton at unchanged x; this is not exact glyph reconstruction. Missing or ambiguous evidence remains fatal. A focused synthetic regression checks this case. Source start/end region framing and ordinary barline scaffolds are diagnostic layout markers, not a reconstruction of the missing forward-repeat/header notation.

## Actual partial render and inspection

New output directory: `/private/tmp/capomatic-v4-gt13a/gt13a-output/`.

- `original-bb.png`: untouched full-system source crop.
- `predicted-a.png`, `predicted-g.png`: **2300×510** labeled diagnostic PNGs, with entire system staff/boundary scaffold, cached measure-3 content and orange gap annotations elsewhere.
- `comparison-contact-sheet.png`: **2300×1530**, original/A/G stacked at identical saved coordinate scale.
- `source-system-inventory.json`, `input-and-inventory-freeze.json`, `external-boundary-evidence.json`: full source audit and provenance.
- `semantic-integrity.json`, `rendering-metrics.json`, `completeness-report.json`, `prediction-freeze.json`, `visual-inspection-report.json`, `validation-summary.json`: checks and separate completion decisions.

Every target contains genuinely rendered notation, but only the same verified measure-3 material as GT-12: 4 events, E/D chord, six newly typeset syllables. Exact GT-12 combined-alpha bytes are reused; its notehead residual remains at most 0.5px per axis. No musical content is rendered inside the three unverified gap regions. Full-system clef/key/time/repeat symbols are explicitly absent rather than substituted. No source lyric pixels enter either target canvas.

The agent inspected the actual comparison PNG after freeze. Cached m3 remains readable in its source-system position and does not visibly touch gap labels. Orange gap boxes and incomplete warnings are clear. **VISUAL_QUALITY=NEEDS_REFINEMENT_FOR_FULL_SYSTEM** because 22 recognized events and required context remain unrendered. This is agent inspection, not independent optical validation. Whole-system collision/clipping/readability safety is not certified merely because a partial scene looks clear.

## Validation and next step

Targeted tests: **205 passed, 1 skipped** (existing external MuseScore dependency). Tests include GT-13A scope isolation, no confirmation inheritance, timing/pitch mismatch rejection, sloped polylines, nonfinite geometry rejection, explicit out-of-domain barline evidence, deterministic masks and source-crop preservation, plus GT-12/11/04/05/06/07 and V3 music/gate regressions.

Unchanged full V3 guards passed for A/G frozen GT-01 source/targets (37 measures, 169 events, 7 harmonies) and the separate owner-augmented GT-12 source/targets (37 measures, 169 events, 8 harmonies). These are checks of the underlying frozen semantic streams, **not** proof that the new PNG displays all their events. No integrity check was weakened. Prediction/inventory hashes, complete GT-12 preservation, formatting and `git diff --check` are checked before commit. No Full Acceptance.

To reproduce a separately identified partial-system run with existing local evidence: `python -m scripts.research.gt13a_full_system --out NEW-output`. Existing output directories are rejected.

Next concrete requirements: confirm source content/row separation/associations for measures 1, 2 and 4; validate eighth-rest, mixed-beam/hook and local/cross-system tie contracts; then add tested clef/key/time/repeat placement before claiming an entire rendered system. Source confirmation alone does not supply missing rendering contracts, and semantic guard passes do not supply human ground truth.

No original ink removal, original lyric-pixel composition, protection-mask changes, ownership-gate changes, V1/V3 production edits, API/frontend routes, merge or deployment occurred. No architecture winner or production readiness is claimed.
