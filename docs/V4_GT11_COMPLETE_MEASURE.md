# GT-11: fixed printed measure 3 music-layer prototype

Overall: **COMPLETE_MEASURE_INCOMPLETE**. All four recognized events were rendered in actual A/G PNGs, but independently established source-event completeness is absent. This is an offline, contextual music layer, not a complete lyric-preserving transposed score. Clef/key context is supplied by captions; chords and lyrics are not rendered.

| Completion level | Final decision | Evidence and boundary |
|---|---|---|
| SOURCE_RECOGNITION_COMPLETENESS | UNVERIFIED | Source-only inventory agrees with frozen MusicXML and visual graph; these share recognition ancestry. Independent human labels: 0. |
| RENDERING_COMPLETENESS | COMPLETE | All four recognized events and all required recognized music-layer components are present in each target. Chords and lyrics are outside this render scope. |
| VISUAL_QUALITY | ACCEPTABLE_FOR_EXPERIMENT | Agent inspected actual individual PNGs and comparison sheet after prediction freeze. This is not independent optical/human validation or professional engraving certification. |

## Revision, inputs and isolation

Base: `f3b808d3fb072d521f516ef9e8f50ef54bd59756`, directly from GT-07B. Branch: `experiment/v4-gt11-complete-measure`; worktree: `/private/tmp/capomatic-v4-gt11`. The commit containing this report is the GT-11 final research revision; its immutable SHA is reported with delivery rather than embedded into its own contents.

The source is **Bb major, original PDF page 2**, printed measure **3**, fixed before inspection. Targets are A major (-1 semitone) and G major (-3). No reference-page content was accessed in this run. No GT-10 branch or owner classifications were imported into the prediction process.

The signed GT-01 baseline was verified. Source raster SHA-256: `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`; dimensions 2520×3564, RGB. FreeSerif SHA-256: `c1dd2270ff624d66a7f1cd23075b5ce05a662f560be06a70a9599065ce008355`. Exact PDF, MusicXML, OMR, font, historical prediction and study-code hashes are bound in the local inventory/prediction manifests. No Audiveris, OCR, PDF rasterization, model download or source repair was performed.

Sequence: [protocol](V4_GT11_PROTOCOL.json), source-only crop inspection and inventory freeze, fresh unchanged V3 transposition/guards, rendering and prediction freeze, then agent visual review and read-only component inspection. Post-freeze reports do not modify frozen prediction artifacts. This is development evidence, not a blinded evaluation.

## Source inventory

The recognized stream is one part, an unspecified single voice stream (`null`, not an invented voice 1), with onsets 0–3 and quarterLength 1 per event. Four quarter-length units tile the recognized measure; the recognized context does not serialize a time signature, so this does not independently establish printed 4/4.

| Source event | Onset | Written event | Audiveris ID | Required recognized components |
|---|---:|---|---|---|
| `p1:m2:r0` | 0 | Quarter rest | `sheet#1:5592` | Quarter-rest glyph |
| `p1:m2:n0` | 1 | Bb3 (`B-3`) | `sheet#1:1830` | Head, upward stem, source ledger |
| `p1:m2:n1` | 2 | C4 | `sheet#1:1834` | Head, upward stem, source ledger |
| `p1:m2:n2` | 3 | F4 | `sheet#1:1790` | Head, upward stem |

Each note has an explicit RIGHT head-stem relation. No required beam, flag, tie, slur, articulation, fermata or explicit accidental is identified in this recognized stream and its connected graph. No unsupported required attachment was encountered; the helper would block one rather than silently drop it. This statement is limited to recognized evidence, not a certification that OMR omitted nothing.

`source-event-inventory.json` records part/voice, onset/duration, pitch, source symbol IDs, stem relations, staff coordinates, ledger requirements, graph confidence, ambiguity and renderer support for each event. All four events are RECOGNIZED and SUPPORTED. `source-completeness-audit.json` records **UNVERIFIED_SOURCE_COMPLETENESS**.

The source-only crop visibly includes an **F chord candidate**, absent from the selected measure's MusicXML harmonies (0), and Korean lyrics, absent from its semantic lyric items (0). The chord omission is recorded as MISSING_FROM_OMR with agent source-image observation as its basis, not independent human truth. No target chord was inferred. Broad graph text evidence is retained without assigning exact text-pixel ownership. The viewport `[1366,315,1791,657)` cuts part of a lower lyric row; only pixels inside that unchanged crop are preserved, not a full lyric context.

## Reused renderer and actual results

GT-05A fixed-phase raster-bbox placement is unchanged. GT-06 double-beam and GT-07B flag behavior are retained through regression tests, but neither symbol is required or newly exercised in this measure. The only edit to the existing research composer is an optional observer receiving copies of its exact component masks; its default rendering path is unchanged.

Physical source centers remain OMR bbox-derived observations. Corrected semantic source coordinates, target pitch coordinates, font-outline anchors and rendered bitmap anchors remain separate fields. No detected center is promoted into independent physical truth. Original source x positions, sloped staff polylines, system 1 and measure bounds `[1374,1782]` are retained. Measure width is 408px; interline is 18px. No global stretching occurs.

| Metric | A major | G major |
|---|---:|---:|
| Target notes | A3, B3, E4 | G3, A3, D4 |
| Recognized events rendered | All 4 | All 4 |
| Heads / rests / stems | 3 / 1 / 3 | 3 / 1 / 3 |
| Ledger lines / ledger component groups | 3 / 2 | 4 / 2 |
| Exact moving component masks | 9 | 9 |
| Additional staff/bar mask layers | 2 | 2 |
| Maximum notehead raster residual per axis | 0.5px | 0.5px |
| Requested note x / semantic target y deviation | 0 / 0px | 0 / 0px |
| Staff / measure-boundary deviation | 0 / 0px | 0 / 0px |
| Missing / duplicated recognized events | 0 / 0 | 0 / 0 |
| Unexpected ink-collision pairs | 0 | 0 |
| Music-only alpha / protected-envelope contacts | 0 | 0 |
| Rendered notation clipping | No | No |

The unchanged 0.5px raster-bbox criterion passes. Zero requested x deviation does not mean zero raster quantization residual: bitmap centers can differ by 0.5px. Coverage centroid and optical center are not the pass metric.

Each head/stem pair shares 12 nonzero-alpha pixels. Every ledger band contacts its own head or stem; a line passing through a head need not directly intersect the stem. Post-freeze `component-inspection.json` records both contacts separately. Intentional staff/rest, staff/bar and same-note contacts remain distinct from unexpected collisions. Collision metrics use actual alpha masks, not only bboxes, and apply only to this isolated scope.

Exact head, stem, rest, ledger, staff and bar masks are saved individually, with pixel/PNG hashes, plus explicit music-only and combined unions. The nine moving layers are three heads, three stems, one rest and two ledger groups; each ledger group contains all ledger lines for one note. Staff and bar add two layers, for eleven total. The complete union is byte-identical to the actual new render-engine alpha PNG and to historical GT-05A measure-3 alpha. These are producer snapshots, not masks inferred by subtracting staff or interpreting a combined image.

**Measured progress is evidence completeness, not improved engraving:** full recognized-measure accounting, fail-closed component checks and exact per-component evidence now survive the experiment. The resulting music pixels intentionally reproduce the validated historical measure-3 renderer; no new visual-quality improvement is claimed.

## Integrity and visual review

Unchanged V3 `transpose_score` and full `music_guard.validate` ran for both shifts before rendering, in memory and after MusicXML write/read. All four guard invocations passed: 37/37 measures, 169/169 events, 7/7 harmonies, no issues. Selected-measure onset, duration, event ordering, voice, tie and articulation identity checks also pass. These counts cover recognized semantics, not independently verified printed events.

The agent inspected `predicted-a.png`, `predicted-g.png` and the comparison sheet after freeze. Heads/rests are legible, upward stems visibly connect, ledger alignment is coherent and new notation is not visibly clipped. Remaining optical spacing/font style is an experimental approximation. No claim of independent optical validation follows from this inspection or automated tests.

Chords and lyrics are not rendered. No original music is removed and no source/target composite is produced. Clef and A/G key signatures are provided as caption context for a mid-system excerpt, not engraved glyphs; this is not a self-contained performance score. Beam/flag/curve endpoints are not applicable to the recognized selected stream, and support for an entire score is not implied. No A/G reference comparison was performed after freeze; historical GT-05 equality is a renderer regression, not reference accuracy.

## Artifacts and reproducibility

Untracked local output directory: `/private/tmp/capomatic-v4-gt11/gt11-output/`.

- `original-bb.png`, `predicted-a.png`, `predicted-g.png`, `comparison-contact-sheet.png`: actual labeled rendered/source panels.
- `source-event-inventory.json`, `source-completeness-audit.json`: source-first accounting.
- `rendering-metrics.json`, `unsupported-elements.json`, `semantic-integrity.json`: frozen machine checks and omissions.
- `components/A/`, `components/G/`: exact component masks and manifests.
- `prediction-freeze.json`: hashes bound before agent review.
- `visual-inspection-report.json`, `component-inspection.json`, `validation-summary.json`: separate post-freeze review and final three-level decisions.

Frozen `rendering-metrics.json` intentionally retains VISUAL_QUALITY=UNVERIFIED from the pre-review stage. The authoritative final three-level verdict is `gt11-output/validation-summary.json`, recording ACCEPTABLE_FOR_EXPERIMENT after inspection and linking the post-freeze review hashes; the frozen metric file is never rewritten.

For a new, separately identified development run, with historical local evidence present:

```sh
python -m scripts.research.gt11_complete_measure prepare --inputs NEW-input
python -m scripts.research.gt11_complete_measure render --inputs NEW-input --out NEW-output
```

Do not point these commands at frozen output directories. Human/agent visual inspection is a separate step; executing the renderer does not generate a visual-review verdict.

## Validation, limits and next work

Targeted tests: **177 passed, 1 skipped**. The existing skip requires external MuseScore. Two development-test failures (local key/clef context lookup and mock font fixture bytes) were corrected before actual rendering; no placement algorithm or threshold changed, and the frozen real source inventory remained identical. Final targeted command:

```sh
python -m pytest tests/test_v4_ground_truth_11.py tests/test_v4_ground_truth_04.py tests/test_v4_ground_truth_05_anchor.py tests/test_v4_ground_truth_06.py tests/test_v4_ground_truth_07_flags.py tests/test_v4_ground_truth_07_flag_contacts.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py -q
```

Source/inventory and historical prototype hashes, frozen prediction files, byte-level GT-05 regression, research formatting and `git diff --check` are checked before commit. No Full Acceptance run. Independent labels and accepted accuracy denominator both remain 0. Recognition/graph agreement and a verifier written alongside the renderer are consistency tests, not outside ground truth.

Next concrete task: independently account for the fixed source measure's events, attachments and omitted chord/lyric context without repairing predictions from target references. Retain this exact component-output contract in future authorized symbol experiments. A COMPLETE source-reconstruction claim must wait for outside source-completeness evidence; another rendering of these same four events cannot supply it.

V1/V3 production modules, API/frontend, integrity gates, protection envelopes and Track A COMPLETE-only ownership are unchanged. No original PDF/raster edits, source removal, lyric composition, production B2, merge or deployment occurred.
