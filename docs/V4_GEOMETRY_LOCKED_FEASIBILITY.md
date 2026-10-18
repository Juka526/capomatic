# V4 Track B: geometry-locked feasibility

**Decision: `GEOMETRY_LOCKED_POC_NEEDS_WORK`. B1 does not validate; B2 is skipped.**
This is an offline developer coordinate/collision investigation on three preregistered
jayu measures. There is no replacement notation image, production renderer, accuracy
claim, acceptance run, or comparison winner.

## Frozen scope and evidence

Branch `feature/v4-geometry-locked`, base
`04687ce6ac65eb4d9505365b92aa96c886c88530`. All 28 entries in
`/private/tmp/capomatic-v4-dual-inputs.json` were SHA-256 verified before
preregistration and before/after measurement. Its SHA-256 is
`f9e4b3e951e15609051b03530839326d99d7320865f45a82ade7501d0fdc2948`.
Inputs remain read-only at
`/private/tmp/capomatic-v4/v4-jayu-provenance-diagnostic/`.
The current artifact hashes bind this investigation; the OMR file does not embed
an original-input SHA, so they do not independently establish recognition provenance.

Before new geometry, collision, or full-guard measurements, the selection was written
to `dual-track-b-output/preregistered-excerpts.json` and frozen with SHA-256
`71d3e2012c86e83880b768498d6ac3b6b8a2a0d33f05be262cded7067b0abbfb`.
The selection algorithm scans semantic MusicXML measure order separately for each
category below, excluding measures already selected. It uses structure, never
measurement success, and takes one whole measure per excerpt:

1. First nonempty measure whose pitched events are all singleton notes: **1**.
2. First remaining measure containing a complete existing V4 beam group with at
   least two heads: **2**.
3. First remaining measure containing MusicXML harmony and lyric elements and a
   linked curve whose endpoint heads both belong to it: **3**.

An exact-byte copy of the preregistration and its hash is committed as
`docs/V4_GEOMETRY_LOCKED_EXCERPTS.json` and `.sha256`. The registration contains all 30 semantic/head IDs, nine contained beam groups,
and eight contained curves. “Chord” here means chord symbols/harmony: the selected
pitched events are single notes, not simultaneous multi-head musical chords.
Measure 1 includes beams; “simple” means singleton pitch events, not beam-free notation.
No excerpts were reselected after observing results.

## B1 coordinate contract and independent check

The helper reuses `read_semantics`, existing plan/match IDs, the Audiveris visual
parser, and the unchanged V3 transposer and full integrity guard. It does not
implement spelling or matching. Original page dimensions (2481 × 3508), system
membership, staff polylines and measure bounds are copied verbatim to
`target-geometry.json`; every target notehead x is its original visual head x.
The independent absolute target ordinate is:

```
interpolated original middle-staff-line y at original head x
  + target SemanticNote.staff_pitch × original Staff.interline / 2
```

`staff_pitch` already incorporates the MusicXML clef and corrected semantic pitch.
This keeps the original polylines; it does not fit or straighten staves. The
interline is the existing V4 staff spacing. This is a declared coordinate model,
not proof that a reconstructed glyph would land on the correct pixels.

| Excerpt | Heads | Measure width | Target-head pair envelopes | All existing-plan swept envelope pairs |
| --- | ---: | ---: | ---: | ---: |
| Measure 1 | 10 | 711 px | 0 | 49 |
| Measure 2 | 9 | 533 px | 0 | 43 |
| Measure 3 | 11 | 555 px | 0 | 54 |

Staff-polyline deviation, head-x deviation, measure-width deviation and system-break
change are all **zero by construction in the coordinate contract**. They are not
independent visible-render measurements: B2 produced no reconstructed canvas.
Expected absolute head displacements range from +10.10 to +18.05 px, downward.

The independent audit detects an existing-plan anchor discrepancy. Repaired heads
`sheet#1:2334` and `sheet#1:2335` have corrected source C4 and target B-flat3.
At their x positions, the original staff midline is 501.5 and interline is 21.3:
target staff position 7 gives **576.05 px**. The existing plan gives **568.65 px**,
a **−7.40 px** discrepancy. The existing plan shifts the raw visual head from its
original center using the corrected-source-to-target interval. A raw head whose
semantic pitch was repaired is not thereby a corrected-pitch anchor. The physical
head center also has a +3.25 px residual from its raw semantic staff position;
therefore this result is an anchor/model discrepancy, not an exact source-ink mask
or a claim that every raw center is an accurate glyph pivot. Existing V4 code and
inputs were not modified.

## Musical integrity is blocked

The fresh unchanged V3 full guard on **persisted recognized XML versus persisted
transposed XML** reports 33→33 measures, 274→274 events, 39→39 chord symbols, and
`ok=false`: **bar 32: chord semantics changed at 3/4**. This whole-artifact failure
blocks B1, even though the frozen excerpts are measures 1–3 and the earlier
note/rhythm/key-only report passes. A note-only pass cannot waive the full guard.

The fresh guard inspects the source chord as `Csus add 7`, kind
`suspended-fourth`, with an added seventh, versus target
`B-7 subtract 3 add 4`, kind `dominant-seventh`, with subtract-third/add-fourth.
Parsed suffixes agree on `7sus4`, but the unchanged full guard compares the
serialized kind/modification representation too and rejects it. This investigation
neither weakens that gate nor declares the representation discrepancy harmless.

A separate unchanged V3 transposition run **in memory** reports failures at bars
4, 20 and 32. This is a different representation stage from the persisted XML
comparison. Serialization normalization may explain the extra differences;
without a round-trip investigation they are unresolved stage discrepancies,
not additional proven V3 defects. No extra score exports were needed. Full fresh
reports and chord details are in `fresh-full-integrity.json`.

## Collisions, lyrics and unresolved notation

All counts below are scoped to the frozen excerpts:

- Target head-envelope versus target head-envelope: **0** overlaps.
- Target head-envelope versus nearby protected-text envelopes: **0** overlaps.
- Existing V4 swept note-component/beam-group/curve envelopes: **146** overlapping
  pairs, including expected attachments, containment and duplicate component
  coverage. These are conservative bounding rectangles, not 146 ink collisions.
- Existing V4 swept candidates versus nearby protected envelopes: **0** overlaps.
- **Actual complete-notation ink collision count: unknown.** No reconstructed
  stems, beams, ledgers, accidentals, keys, chord glyphs or curves were rendered.

The collision JSON retains all existing selected beam/curve geometry and endpoint
links. Uniform relative beam deltas in the old plan do not validate the absolute
target model: raw anchor residuals and ledger repairs can require different
endpoint movements. Beam slope/stem length, curve shape/tangency, ledger ownership,
accidentals and key signatures remain blocked. Linked endpoints alone do not prove
slur/tie semantics, readability or collision freedom. Bounding boxes cannot certify
actual ink clearance. A future B2 must fail closed on any protected collision.

Chord spelling/length comparisons use the existing music21 figures (including its
`-` flat notation): measure 1 `C/E` (3)→`B-/D` (4); measure 2 `B-/D` (4)→`A-/C`
(4) and `Am/C` (4)→`Gm/B-` (5); measure 3 `B-maj7` (6)→`A-maj7` (6).
Two strings grow by one character. **Rendered chord-width conflicts are unknown**:
character length is not glyph width, and no chord text was laid out or lyric OCR
retyped.

The PNGs are explicitly **DEVELOPER ANNOTATION ONLY**: blue circles show raw head
centers, red marks show absolute targets, orange rectangles show protected bboxes.
They retain source notation and must never be presented as transposed scores.
Orange borders change protected lyric pixels. `collision-report.json` measures
those differences on each whole-page annotation before cropping: 12 region
observations range from **1,311 to 6,829 changed pixels**; system-wide lyric-line
and measure-item bboxes overlap and are not disjoint pixel totals.
These are annotation differences, not an equality pass. **Replacement lyric-pixel
equality is not applicable because B2 was skipped.** Protection covers recognized
lyric bboxes, not a manually established complete ground truth for every lyric.

## Outputs and reproduction

All large outputs remain untracked in
`/private/tmp/capomatic-v4-geometry/dual-track-b-output/`:

- `preregistered-excerpts.json` and `.sha256`: frozen selection proof.
- `coordinate-map.json`, `target-geometry.json`: original geometry and absolute targets.
- `collision-report.json`, `fresh-full-integrity.json`, `summary.json`: measurements and blocks.
- `measure-1-ANNOTATED.png`, `measure-2-ANNOTATED.png`, `measure-3-ANNOTATED.png`.
- `input-verification-before.json`, `input-verification-after.json`.
- `run-resources.json`: nondeterministic timing/memory, separate from deterministic evidence.

```sh
/private/tmp/capomatic-v4-venv/bin/python -m scripts.omr_v4.geometry_locked_feasibility \
  --inputs /private/tmp/capomatic-v4-dual-inputs.json \
  --registration docs/V4_GEOMETRY_LOCKED_EXCERPTS.json \
  --out dual-track-b-output
```

A measured helper run took **0.83 seconds**, peak RSS **232,144,896 bytes** on macOS,
including imports, image annotation, XML parsing and music21. This is not renderer
performance or a production benchmark. Resource values change between runs.

All original evidence remains byte-identical under the 28-file hash contract;
no source score/raster pixels were edited. Replacement-content loss is **unknown**,
not zero, because no replacement exists. There was no Audiveris/Docker rerun,
MuseScore global stretching, production path/flag/API/frontend change, acceptance
run, merge, deployment or source overwrite.

B2 must stay skipped until the unchanged full musical guard passes and absolute
geometry, complete notation, rendered collision and protected-pixel checks can
validate the exact same frozen scope. This task does not authorize fixing existing
semantic modules or waiving their gates.

## Verification

`pytest -q tests/test_omr_v4_*.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py`:
**299 passed, 1 skipped**. Focused checks cover corrected-pitch absolute anchoring,
polyline interpolation, invalid geometry, evidence/output alias rejection, input
tampering, exact RGB pixel inequality and the committed preregistration hash.
These regression checks verify the helper's behavior; they do not establish
recognition accuracy or rendered notation quality. Black (`-S -l 100`) and
`git diff --check` are clean. No full acceptance run was performed.
