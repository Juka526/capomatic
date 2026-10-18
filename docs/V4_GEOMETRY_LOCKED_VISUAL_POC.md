# GT-04 geometry-locked visual prototype

**Decision: VISUAL_POC_NEEDS_REFINEMENT.** Actual isolated transposed notation PNGs were rendered. They have zero measured unexpected ink collisions in the selected scope, but maximum notehead raster-anchor residual is **1.0 px**, failing the preregistered **0.5 px** per-axis criterion. No offset was adjusted after seeing this result. This is a MUSIC-ONLY, incomplete developer experiment, not a usable score, production renderer, completed B2 gate or architecture winner.

Starting SHA `4a2e1eddc74f1d67b4598da7325e55cac13c7718`; worktree `/private/tmp/capomatic-v4-gt04-visual`, branch `experiment/v4-gt04-visual-rendering`. Preregistration: `924da25`; actual rendering code: **`b64107b3a437ea8611c3add342bdd4b900c60c29`**. Only diagnostic scripts/tests/docs are changed. Later post-freeze reference comparison code cannot regenerate predictions.

## Immutable inputs and selection

Source remains **Bb major, PDF page 2**. Targets are **A major −1** and **G major −3**, from the same frozen source recognition/transposition. Reference pages 1/3 are used only after prototype freeze. This is post-reference-access development, not a blinded experiment.

| Input | SHA-256 |
| --- | --- |
| Original three-page PDF | `1cc64756c0ce47b1db0ea6ac21eefe4685097a04cd4589f954afc712afb605fd` |
| Bb source PNG | `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de` |
| A reference PNG | `b094035763fc02685edcb1a57960833cc95b52e95034fb6cbaaba2c929e7fa67` |
| G reference PNG | `2d5cae7034a78e06d62975e92dc2f9666311fb0a06659dfe49cb2fdfd8e739bc` |

GT-01 signed manifests and bound artifacts were verified before preparation and after analysis. GT-02's retained manifest, 145-file packet and source-only registration evidence, plus GT-03's original 14-case schedule, remain unchanged. Source PNG mode stays RGB with identical channels; dimensions remain **2520×3564**, no rotation/rescaling. No A/G pixels, chord answers or note positions construct the prototype.

The preregistered rule takes the earliest two non-system-initial source measures with uniquely located events, a complete undotted four-quarter note/rest stream and no required beam/flag/curve/attachment/repeat/ending/explicit-accidental support. Missing source chords permit an explicitly incomplete music-only layer, never a complete score. `render-input/selection.json` records all prior rejected candidates and blockers before image generation. No replacement excerpt or second rendering run occurred.

This selects **printed 3 and 32**:

| Scope | Physical region | Frozen source music | A prediction | G prediction |
| --- | --- | --- | --- | --- |
| m3, system 1 | x=1374–1782 | quarter rest; Bb3, C4, F4 quarters | rest; A3, B3, E4 | rest; G3, A3, D4 |
| m32, system 8 | x=1358–1808 | quarter rest; D5, D5, Bb4 quarters | rest; C#5, C#5, A4 | rest; B4, B4, G4 |

Other earlier source measures fail on system-initial context, rhythm, connected beam/flag/curve, ending or no pitched content. Both selected scopes have complete recognized note/stem groups and no linked curve or moving articulation/fermata. This is source-side recognized evidence, not independent certification of the printed notes. It deliberately does not test a beam group or solve the repaired-ledger anchor problem.

## Engraving and placement contract

The existing Docker image's **GNU FreeSerif** font is copied locally, never downloaded or committed. SHA-256: `c1dd2270ff624d66a7f1cd23075b5ce05a662f560be06a70a9599065ce008355`. The retained installed license describes GPL-3+ with Special Font Exception for font files; this experiment does not make a new licensing conclusion or bundle a font. Bravura/SMuFL is not introduced.

FreeSerif supplies real musical Unicode glyphs: black notehead **U+1D158** and quarter rest **U+1D13D**. Stems, staff polylines, ledger segments and simple boundary barlines use explicit geometric strokes. These are newly drawn musical symbols, not source head crops, coordinate arrows or reference-target images.

Four coordinate concepts are kept distinct:

1. **Detected physical head center**: original Audiveris bbox/pivot-derived x/y, retained as evidence only.
2. **Semantic staff coordinate**: the frozen GT-01 absolute target y, checked independently against written target diatonic pitch: `staff_middle_polyline_y(x) + (35 − diatonicNoteNum) × interline / 2` for this G-clef context. It is not the raw detected source y plus a universal offset.
3. **Font-specific placement anchor**: center of the font glyph's design-outline bbox, with y-up font units transformed to the explicit y-down baseline. `font_size = round(1.25 × interline × unitsPerEm / black_head_outline_width)`, giving 94 px at the 18 px interline. This is a documented design contract, not an independent optical/musical anchor measurement.
4. **Rendered raster ink bounds/center**: actual nonzero glyph-mask pixels after FreeType/Pillow rasterization. Residuals compare their pixel-index-center bbox center to the design anchor; they are measured, not assumed zero.

Each target head retains source x. Up/down stems follow semantic staff side, attach to the actual rendered head edge, and extend 3.5 interlines; ledger strokes occur at logical even staff positions outside the five lines, width 1.75 interlines. Original head centers are not used to calibrate font offsets. No source/reference-based optical adjustment was performed.

Staff center polylines are retained point-for-point with clipping only at the original measure edges; stroke style is a new 2 px diagnostic stroke, not a claim to reproduce original antialiasing. Simple barlines remain at the registered source boundaries. No global MuseScore stretching is used.

The internal notation canvas retains the full 2520×3564 page coordinate system. Export panels are native-resolution viewports, not new page layouts: `panel_x = page_x − viewport_left`, `panel_y = page_y − viewport_top + 84` for the outside label margin. The contact sheet stacks those viewports for inspection; it does not claim to preserve full-page vertical spacing in the contact-sheet arrangement. Rendering software was Pillow 12.3.0, FreeType 2.14.3, fontTools 4.67.0, NumPy 1.26.4 and music21 9.9.1.

The excerpts are mid-system contextual notation: **G clef and target key are stated outside the notation as text**. Key/clef glyphs are not inserted at a nonexistent mid-measure boundary. All selected notes are in the declared target key, so no local accidental glyph is required. No standalone staff opening, key-signature rendering or general accidental algorithm is claimed. A required out-of-key accidental or unsupported attachment blocks this renderer instead of being omitted.

## Actual outputs and freeze

Local untracked `ground-truth-04-output/visual-prototype/` contains:

- `original-bb.png`: two bounded, unchanged native source crops with labels outside their pixels.
- `predicted-a.png`, `predicted-g.png`: newly rendered music-only layers, not annotation overlays or reference images.
- `comparison-contact-sheet.png`: original beside A/G layers at native scale, with no pixel compositing between them.
- `rendering-metrics.json`, `rendering-limitations.json`, `prototype-freeze.json` and technical per-excerpt alpha masks.

The four score-view PNGs clearly state **DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE** and **INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING**. Technical alpha masks are binary/coverage instrumentation, not score-view outputs. No PDF was generated; PNG suffices. `prototype-freeze.json` binds ten output files plus selection/code hashes before reference evidence is opened. The comparison verifies the complete frozen file inventory and never invokes the renderer. No image or metric was regenerated after reference access.

## Geometry, completeness and collision measurements

Rendering runtime: **2.359 seconds** for both selected measures in both target keys, excluding preparation and later comparison. Peak memory was not captured; it is not reported as an estimate disguised as measurement.

| Check | m3 A | m3 G | m32 A | m32 G |
| --- | ---: | ---: | ---: | ---: |
| Notes / quarter rests | 3 / 1 | 3 / 1 | 3 / 1 | 3 / 1 |
| Logical note x deviation | 0 px | 0 px | 0 px | 0 px |
| Target y formula deviation | 0 px | 0 px | 0 px | 0 px |
| Semantic diatonic vertical move | +9 px | +18 px | +9 px | +18 px |
| Staff/measure vector-coordinate deviation | 0 / 0 px | 0 / 0 px | 0 / 0 px | 0 / 0 px |
| Maximum notehead raster-anchor residual | **1.0 px** | **1.0 px** | **1.0 px** | **1.0 px** |
| Unexpected rendered ink-intersection pairs | 0 | 0 | 0 | 0 |
| New music vs protected-region source dark pixels | 0 | 0 | 0 | 0 |
| New notation page/viewport clipping | 0 | 0 | 0 | 0 |
| Missing / duplicated selected semantic events | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

The **0.5 px anchor criterion fails** on one head per measure/target: x residual −1.0 px. Other head x residuals are −0.5 px; y residual maximum is 0.5 px. The failed criterion is retained; no tolerance widening, offset tuning or replacement excerpt is used. Logical coordinate invariants passing does not mean rendered pixel centers passed.

Actual per-symbol alpha masks determine intersections, not bbox overlap. Staff crossings and same-note head/stem/ledger contacts are separately recorded as intended topology. Head/stem intersections are nonempty (12 or 13 pixels per note). A different note's stem cannot inherit same-note exemption. No beams or curves exist in these two scopes, so their endpoint continuity is **NOT APPLICABLE**, not validated globally.

Protected-source contact counts intersect actual new notation ink with source pixels `<127` inside retained protected text regions. They are conservative raster-contact diagnostics, **not** proof of exact text ink ownership or permission to edit. They cannot authorize erasure of original musical ink. COMPLETE-only Track A gates stay unchanged.

## Lyrics and incomplete chords

There is **no target lyric composite**. The new layer is shown beside an untouched original crop; Korean lyrics are neither OCR'd nor retyped. Source-crop bytes/mode beneath the outside labels compare exactly with the original crop. This preserves all visible original lyric pixels in that bounded panel, not an entire-page lyric claim. The m3 viewport truncates part of the lower verse at its context edge; no source file/text was deleted, and that cropped context is not presented as a complete lyric transcription. New notation has no clipping, which is a separate check.

Source chord coverage remains 7 harmonies out of 24 coordinator candidates. Both chosen printed regions contain a coordinator-identified **F** chord absent from frozen harmonies. No E/D reference answer is imported into predictions. Target panels omit the chord layer explicitly and remain **MUSIC-ONLY / INCOMPLETE**; original chord pixels remain visible in the original panel. There are no recognized harmonies within these scopes to render or measure. Actual rendered chord text width/conflicts are **NOT APPLICABLE**, not “zero width risk” or complete chord preservation. All seven recognized harmonies elsewhere remain protected by the full baseline integrity check, without being rendered here.

## Musical integrity and post-freeze reference evaluation

The unchanged full V3 guard was rerun on frozen source versus frozen A/G target MusicXML before rendering: **both PASS**, 37/37 measures, 169/169 note/rest events and 7/7 harmonies, no issues. That certifies the recognized stream's transformation, not recognition truth or rendered-glyph semantics. The prototype separately accounts for 6 heads and 2 rests per target, all quarter durations, with source/target pitch identities recorded. No guard was relaxed, normalized or bypassed.

Only after freeze, `gt04_reference_compare.py` reads the supplied reference evidence. GT-02's structurally paired candidates yield, **per target**, 6 pitched-note spelling agreements and 8 duration agreements (6 notes + 2 rests). Human-accepted denominator remains **0**, so no accuracy percentage is computed. Recognizer agreement is not independent verification.

| Reference diagnostic | A | G |
| --- | --- | --- |
| Rendered raster-center minus detected-reference x, all 8 events | −14 to −8.5 px | +5.5 to +8.5 px |
| Rendered raster-center minus detected-reference y | −1 to +0.5 px | −0.5 to +0.5 px |
| Source-minus-reference m3 width | +7.5 px | −4 px |
| Source-minus-reference m32 width | +6 px | −4 px |
| Registered staff-band coordinate difference | 0 px | 0 px |

Different key/engraving spacing explains why reference x/width is not the geometry-lock target. Those measured differences are not penalized as musical errors. Native reference context images were inspected after freeze: the small note/rest sequences are visually consistent with the candidate comparison; reference chord text is absent from our music-only layer. This is coordinator development review, not independent musical validation. Lyric ownership/composition and full text equivalence remain unverified.

## Limitations and next step

Supported in this bounded experiment: black quarter-note glyphs, quarter rests, detached stems, logical ledger lines, original staff polylines and simple in-scope barlines. Unsupported/untested required notation includes beams/hooks/flags, ties/slurs, grace/tuplets/dots, explicit accidentals, standalone clef/key/time signatures, repeats/endings, articulations/fermatas and chord rendering. Such requirements block a complete excerpt; they cannot be silently dropped to claim a complete score. General polyphony and page reconstruction are not implemented.

Next is a separately identified raster-anchor calibration/control experiment using font geometry and synthetic placements, with the 0.5 px rule unchanged, followed by an independently referenced wider-symbol excerpt. No immediate tuning against these rendered/reference examples is performed. A beam/curve example, complete chord evidence and safe lyric composition need separate validation; this easy quarter-note scope cannot choose an architecture winner.

The GT-02 111-case packet and GT-03 14-case pilot remain byte/hash-identical. **Actual independent human labels: 0**. The prototype and coordinator reports must not be shown to blinded annotators; only their existing neutral packet/schedule is distributable. No original PDF/raster editing, production V1/V3 change, ownership promotion, integrity waiver, API/frontend route, production renderer, merge, deployment or Full Acceptance occurred.

## Reproduction and verification

Tools refuse existing output directories. Reproduction requires the retained hash-bound GT-01/GT-02 evidence and locally extracted existing font, not just this Git checkout. Do not overwrite the frozen run; any later rendering belongs to a different run identity.

```sh
python -m scripts.research.gt04_visual prepare \
  --gt01 /private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output \
  --gt02 /private/tmp/capomatic-v4-ground-truth-02/ground-truth-02-output \
  --out NEW_RUN/render-input
python -m scripts.research.gt04_visual render \
  --inputs NEW_RUN/render-input --font LOCAL_EXISTING/FreeSerif.ttf \
  --out NEW_RUN/visual-prototype
# Only after prototype-freeze.json exists:
python -m scripts.research.gt04_reference_compare \
  --prototype NEW_RUN/visual-prototype \
  --gt01 /private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output \
  --gt02 /private/tmp/capomatic-v4-ground-truth-02/ground-truth-02-output \
  --out NEW_RUN/reference-comparison
```

Targeted GT-01/02/03/04, V4 and frozen V3 music/gate tests returned **342 passed, 1 skipped in 8.37 s** on the final run; the skip is the existing external MuseScore dependency. Formatting and `git diff --check` passed. Tests cover selection/rejection before outputs, actual mask intersections and per-note contact identity, finite font geometry, unchanged source pixels beneath labels, forbidden output inside GT-01/GT-02 evidence, and prototype hash verification before reference access. These are software checks, not independent musical ground truth.
