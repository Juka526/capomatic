# V4 Phase 1.9b: raster / glyph provenance forensics

**READY_FOR_INK_ISOLATION_FIX**. The dominant cause is **H: combination**, specifically processed-raster and grayscale-threshold disagreement (**C/D**), expected overlapping glyph semantics (**E**), original-raster connected-component admission incompatible with staff-connected notation (**F**), and staff-attribution versus corridor mismatch (**G**). Confidence is HIGH for these measured representation differences. This is permission to design a principled isolation fix, not a successful Phase 1.9 gate or permission to render.

Starting revision: `b3df2a478eba2ed1b690e166e74f3b5716088c44`. The isolation module, threshold 127, ownership contract, masks and all V1/V3 runtime files remain unchanged. No Audiveris recognition was run. Phase 1.10 did not run. Phase 1.9 still has zero VERIFIED real-sheet records.

## 1. What the pinned Java source establishes

Source was checked out at the exact Dockerfile pin and the OMR's recorded `software-build`: [`7a36078e7ba0c006052c1f661b949cf9b729f505`](https://github.com/Audiveris/audiveris/tree/7a36078e7ba0c006052c1f661b949cf9b729f505). The local source checkout is `/private/tmp/audiveris-v4-forensics`. Its commit was verified with `git rev-parse HEAD`; XML names alone were not used to infer semantics.

| Java class / method | Established contract |
| --- | --- |
| [`RunTable.encode`, `RunTable.Itr`, `RunTable.RunSequence`](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/run/RunTable.java#L1647) | Alternating foreground/background lengths, starting at foreground; an initial zero foreground length permits an initial background gap. Serialization is a local binary mask, not original gray values. |
| [`RunTable.render`](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/run/RunTable.java#L1363), [`Run.getStop`](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/run/Run.java#L148) | Horizontal sequences are rows, vertical sequences columns. A run's final coordinate is `start + length - 1`; Python's exclusive endpoint is equivalent. |
| [`Glyph` fields/constructor/getBounds](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/glyph/Glyph.java#L93) | `left/top` are absolute sheet coordinates. Add local x/y exactly once. Width/height are ordinary image axes, independent of run orientation. |
| [`BinaryStep.runBinarizationFilter`](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/step/BinaryStep.java#L112) | Reads GRAY, obtains the configured filter, binarizes, builds a vertical RunTable and stores BINARY. |
| [`FilterDescriptor` default](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/image/FilterDescriptor.java#L147), [`AdaptiveDescriptor.getFilter`](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/image/AdaptiveDescriptor.java#L145), [`AdaptiveFilter.isFore`](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/image/AdaptiveFilter.java#L185) | Pinned default is ADAPTIVE, implemented by VerticalFilter. Foreground compares gray value with a local mean/stddev-dependent threshold, not a constant 127. |
| [`Picture.getSource`, `buildNoStaffBuffer`](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sheet/Picture.java#L258) | BINARY and NO_STAFF are distinct. NO_STAFF paints staff-line glyph masks white on BINARY. All sources share dimensions; this is pixel processing, not page reflow. |
| [`NoteHeadsBuilder` constructor](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sheet/note/NoteHeadsBuilder.java#L340), [`HeadInter.retrieveGlyph`](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sig/inter/HeadInter.java#L1066), [`Template.getForegroundPixels`](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/image/Template.java#L355) | Head glyphs select BINARY foreground beneath template foreground points. They need not be complete connected components of the original raster. This call uses the two-argument method, not the optional dilated erasure overload. |
| [`BeamsBuilder.retrieveGlyph`](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sheet/beam/BeamsBuilder.java#L1523) | Copies foreground NO_STAFF pixels inside the beam area into a local glyph. `pixelFilter` is initialized to NO_STAFF. |
| [`SpotsBuilder.getBuffer`](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sheet/beam/SpotsBuilder.java#L361) | Beam candidate retrieval also uses a NO_STAFF buffer with narrow stem runs removed, median and Gaussian filtering, followed by binarization. Candidate-search buffers and final glyph construction are different stages. |
| [`VerticalsBuilder.checkVerticals`](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sheet/stem/VerticalsBuilder.java#L143), [`StemBuilder.createStem`](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sheet/stem/StemBuilder.java#L203) | Stems can reuse vertical filament/seed glyphs or compounds of seeds/chunks. They are not disjoint per-note source-image crops. |
| [`SymbolsFilter.process/buildSymbolsGlyphs`](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sheet/symbol/SymbolsFilter.java#L170) | Symbol glyphs originate from a cleaned NO_STAFF buffer after known interpretations are erased, then connected components are built. Optional/weak glyphs also participate; not every flag/dot must have one uniform construction history. |
| [`GlyphFactory.buildGlyph`](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/glyph/GlyphFactory.java#L352), [`GlyphIndex.registerOriginal`](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/glyph/GlyphIndex.java#L391) | A compound combines part masks in sheet-relative coordinates; identical original glyphs can be reused. This is not a disjoint pixel partition across all Inters. |
| [`AbstractBeamInter.getCompetingHook`](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sig/inter/AbstractBeamInter.java#L330), [`AbstractInter` glyph/bounds fields](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sig/inter/AbstractInter.java#L129) | Different interpretations can explicitly share one glyph. Inter bounds may differ from underlying glyph bounds. Separate glyphs can overlap as independently selected or compound processed pixels. |

Therefore **the XML run table is the binary shape of that particular glyph, from its construction stage**. It is not a promise of equality to `Pillow(source).L <= 127`, nor a promise of exclusive source-pixel ownership. In this sheet every one of the 332,852 candidate glyph-pixel references is black in the saved BINARY image at zero translation. This is subset agreement, not equality of each glyph to the whole BINARY image or a proof of ownership.

## 2. Decoder audit

**Verdict: no proven Python RunTable decoder bug; no decoder change.** Source inspection confirms all of the following:

- HORIZONTAL: number of sequences = height; sequence index is local y; run coordinate is local x.
- VERTICAL: number of sequences = width; sequence index is local x; run coordinate is local y.
- Foreground lengths occupy even indices. `0 gap length` skips the empty initial foreground and starts after the gap. Empty sequences contain no ink.
- A length `n` covers exactly `n` pixels, with inclusive Java stop and exclusive Python stop equivalent.
- Local coordinates become `(glyph.left + x, glyph.top + y)`. There is no staff/system-origin subtraction or additional scaling.

The independent regression uses the literal sequence documented by pinned Java RunSequence: `0 41 25 80 2 1 2 80 25`. Foreground local coordinates are 41–65, 146–147, 149–150, 231–255: 54 pixels. The test checks literal expected sheet coordinates in both orientations with nonzero left/top. A separate nonsquare fixture covers foreground-first, empty rows and a leading background gap. The fixture does not use our encoder to generate expected answers. No full Java runtime reconstruction or OMR recognition was needed.

## 3. Source raster provenance

The unchanged pipeline is `jayu.pdf → core.rasterize → temporary source.png → core.run_audiveris → inspect_recognized → shutil.copy2(source.png, output/source.png)`. PDF rasterization is `pdftoppm -r 300 -f 1 -l 1 -gray -png -singlefile`. `run_audiveris` passes that raster path directly to the batch process. `inspect_recognized` reads it for diagnostics/ledger repair but does not write it.

The OMR book records `/tmp/capomatic-v4-hykm1rns/source.png` as both input path and book path, sheet 1, software version 5.11.0, exact pinned build. The temporary file no longer exists and no independently captured **pre-process** file digest was retained, so absolute historical byte identity cannot be cryptographically proven retroactively. Static code, recorded path and exact reproduction provide strong provenance with this explicit limit.

A single **rasterization-only** Docker reproduction used existing image `sha256:fb3c1ff7f6428a499b18aae5dc0b71a5c8b03ee709b10ab82e3ab1f28e332b1e`, with no network and read-only input mount. It produced a PNG **byte-for-byte and native-pixel identical** to the saved source. Audiveris was not invoked.

| Evidence | Dimensions / mode | SHA-256 of encoded bytes |
| --- | --- | --- |
| jayu.pdf | original development PDF | `a952070c62870cb1988e70d934c9fadbef0ea10369260996bb10a27b62c3de5b` |
| saved source.png | 2481 × 3508 / RGB | `e53c52dd7c31f0196b7c5a99231afd4f77bc522f8a02483277179a79c84dc0cb` |
| reproduced-source.png | 2481 × 3508 / RGB | same source hash |
| recognized.omr | saved archive | `e5076145d9b682f77d3bcf333996d9dd33c3c0b5cb6a597caf7b330c6981e29b` |
| embedded BINARY.png | 2481 × 3508 / L | `9a1bd749672d1b5281f6bccbc9cd628ce816c1aa898eae69cb5637515613c509` |

Source native raster digest is `0e3a6c5cb7669ba56c8217ecd8950930280473f76899d08fcae9af71784f0b3f`. Its RGB channels are identical. `Picture.adjustImageFormat` calls `ImageUtil.maxRgbToGray` for RGB, which writes each maximum channel value directly into the gray raster; for these equal channels this preserves the sample value. `BinaryStep` then internally binarizes it. The pinned default is adaptive; the CLI supplies no binarization override and uses a fresh tool home. No historical per-pixel adaptive thresholds were logged, so the actual saved BINARY is the direct processed-raster evidence, not a reconstructed filter simulation.

Source threshold-127 and saved BINARY classifications differ at **237,896 page pixels**. The OMR retains BINARY but does not contain the GRAY.png mentioned by sheet metadata. Java's `SheetStub.loadGrayImage` reloads the recorded input through ImageLoading; it does not imply a separately archived original source copy. No image resizing/rotation is called in this PNG load/picture construction path. Exact BINARY agreement at unchanged coordinates further contradicts a global coordinate mismatch.

## 4. Preregistered sample and measurements

Before measuring pixels, `sample-manifest.json` selected by graph geometry/shape only: first even-pitch filled head; median odd-pitch filled head; last filled head; first open head; spatially ordered stems 0/124/248, beams 0/114, flag 7 and dot 5. Spatial order is y then x. Systems 1, 4, 5 and 8 are represented. Even/odd staff pitch labels are geometry categories, not ownership assertions. A space-centered head can still intersect a line because its raster height exceeds the interline space.

All IDs below have prefix `sheet#1:`. Glyph bounds are **inclusive actual pixel extrema**; Inter bboxes are the graph's region coordinates, whose right/bottom can be one beyond the final pixel.

| Symbol / kind | Glyph | System | Inter region | Glyph pixel bounds | Pixels |
| --- | --- | ---: | --- | --- | ---: |
| 2205 / head | 2204 | 1 | [625.0, 511.0, 654.0, 535.0] | [625, 511, 653, 534] | 514 |
| 2685 / head | 2684 | 4 | [367.0, 1674.0, 396.0, 1698.0] | [367, 1674, 395, 1697] | 524 |
| 3260 / head | 3259 | 8 | [1818.0, 3231.0, 1847.0, 3255.0] | [1818, 3231, 1846, 3254] | 520 |
| 2668 / head | 2667 | 4 | [1594.0, 1663.0, 1623.0, 1687.0] | [1594, 1663, 1622, 1686] | 299 |
| 3764 / stem | 1 | 1 | [554.0, 437.0, 558.0, 504.0] | [555, 437, 557, 514] | 230 |
| 4969 / stem | 79 | 4 | [614.0, 1604.0, 618.0, 1688.0] | [614, 1604, 617, 1700] | 342 |
| 6226 / stem | 692 | 8 | [1153.0, 3207.0, 1158.0, 3270.0] | [1153, 3196, 1156, 3269] | 286 |
| 1444 / beam | 1445 | 1 | [453.15, 436.0, 563.85, 454.0] | [459, 437, 557, 453] | 1114 |
| 1785 / beam | 1786 | 8 | [1060.15, 3247.0, 1162.85, 3271.0] | [1066, 3248, 1156, 3269] | 1025 |
| 8559 / flag | 8010 | 5 | [2043.0, 2026.0, 2066.0, 2097.0] | [2043, 2026, 2065, 2096] | 420 |
| 8584 / augmentation-dot | 7893 | 5 | [1390.0, 2022.0, 1400.0, 2032.0] | [1390, 2022, 1399, 2031] | 83 |

| Symbol | Dark at 127 / glyph pixels | Agreement | Gray min / Q25 / median / Q75 / max | Mean gray | Corridor / centerline pixels | Shared related / unrelated | Source CC IDs |
| --- | --- | ---: | --- | ---: | --- | --- | --- |
| 2205 | 467 / 514 | 90.86% | [0.0, 0.0, 0.0, 3.75, 213.0] | 22.61 | 135 / 27 | 27 / 0 | [60] |
| 2685 | 492 / 524 | 93.89% | [0.0, 0.0, 0.0, 2.25, 205.0] | 16.74 | 124 / 29 | 27 / 0 | [491] |
| 3260 | 484 / 520 | 93.08% | [0.0, 0.0, 0.0, 1.0, 223.0] | 19.74 | 63 / 15 | 27 / 0 | [847] |
| 2668 | 252 / 299 | 84.28% | [0.0, 0.0, 8.0, 69.0, 210.0] | 43.49 | 48 / 9 | 38 / 0 | [491] |
| 3764 | 178 / 230 | 77.39% | [0.0, 9.25, 42.0, 119.5, 211.0] | 62.49 | 42 / 9 | 96 / 0 | [60] |
| 4969 | 227 / 342 | 66.37% | [0.0, 30.25, 44.0, 199.0, 221.0] | 86.62 | 88 / 18 | 111 / 0 | [491] |
| 6226 | 183 / 286 | 63.99% | [0.0, 27.25, 59.0, 167.0, 208.0] | 81.58 | 40 / 8 | 119 / 0 | [847] |
| 1444 | 1054 / 1114 | 94.61% | [0.0, 0.0, 0.0, 12.0, 217.0] | 19.41 | 0 / 0 | 114 / 0 | [60] |
| 1785 | 943 / 1025 | 92.00% | [0.0, 0.0, 0.0, 9.0, 222.0] | 22.67 | 0 / 0 | 123 / 0 | [847] |
| 8559 | 335 / 420 | 79.76% | [0.0, 0.0, 17.0, 98.75, 220.0] | 53.34 | 98 / 21 | 0 / 0 | [600] |
| 8584 | 59 / 83 | 71.08% | [0.0, 0.0, 48.0, 137.5, 194.0] | 69.24 | 0 / 0 | 0 / 0 | [601] |

Each sample is **100%** dark in embedded BINARY at **dx=0, dy=0**. Thus 0 VERIFIED did not mean 0% agreement: the exact admission rule rejects a whole symbol for even one proposed pixel above 127. These sample distributions contain meaningful antialiased/gray-edge values above 127, while every proposed pixel remains foreground in Audiveris's processed raster. Full histograms, all 49 translations, all threshold measurements and supporting group membership are retained per sample in the JSON.

### Translation measurement only

| Symbol | Translation(s) maximizing threshold-127 containment |
| --- | --- |
| 2205 | (0, 0) |
| 2685 | (0, -1), (0, 0) |
| 3260 | (1, -1) |
| 2668 | (0, 0) |
| 3764 | (-1, 1) |
| 4969 | (0, -1), (0, 0) |
| 6226 | (-1, -1/0/1/2/3) |
| 1444 | (0, 0) |
| 1785 | (1, 0) |
| 8559 | (-1, -1) |
| 8584 | (0, 0), (0, 1), (1, 0) |

There is **no common maximizing offset**. Five samples prefer a nonzero shift over zero, while others maximize at zero; thin-stroke containment can improve by moving pixels inward. This is not coordinate calibration. The metric counts proposed glyph pixels landing on source dark pixels, not symmetric image registration. No best shift was applied to any evidence or ownership. Binary agreement is already 100% at zero for all 642 candidates, which is stronger direct evidence against a shared coordinate displacement.

### Threshold measurement only

The following counts include repeated references where different glyphs share a pixel. The denominator remains 332,852 at every threshold.

| Fixed threshold | Dark glyph references | Agreement |
| --- | ---: | ---: |
| 64 | 267,987 | 80.5124% |
| 96 | 284,672 | 85.5251% |
| 127 | 298,238 | 89.6008% |
| 160 | 311,794 | 93.6735% |
| 192 | 324,056 | 97.3574% |
| saved Audiveris BINARY, zero translation | 332,852 | 100% |

This is evidence of processed-binarization/gray-edge representation mismatch. It is not a choice of a better threshold. No threshold was selected, no new ink record emitted and no source classification changed.

## 5. Shared pixels: explain 617 affected symbols

Scope is the 642 first-pass candidate symbols, unordered symbol pairs. The Java contract allows glyph reuse and compounds, but measurements must distinguish those possibilities:

| Category | Measurement |
| --- | ---: |
| A: same glyph ID referenced by multiple candidates | 0 glyph IDs / 0 symbol pairs |
| B: different glyph IDs with actual overlapping runs | 589 pairs |
| C: direct 8-neighbor contact without any shared glyph pixel | 14 pairs |
| D: overlapping pairs in one explicitly SIG-connected musical group | 589 pairs |
| E: overlapping pairs outside those groups | 0 pairs |
| Distinct pixels with multiple candidate owners | 22,710 |
| Candidate symbols affected by shared pixels | 617 |
| Same source CC without shared glyph pixels | 25,961 pairs |

All 14 direct-contact pairs are also SIG-connected; none are unrelated under this grouping. The much larger 25,961 count is **transitive source-image connectivity**, often through an entire staff system, not 25,961 direct symbol contacts. It must not be used as an overlap count.

SIG grouping reproduces the current admission check: typed head-stem, beam-stem, flag-stem, augmentation and alter-head edges with compatible endpoints; transitive closure is explicit and recorded. D establishes structural relatedness, not a proof that every pixel can safely be assigned or deleted. None of these shared pixels were authorized. In particular, same-glyph reuse is supported by Java but is **not** what caused this sheet's 617 alarms: distinct, related glyphs overlap here.

## 6. Component escape: explain 631 affected symbols

The existing rejection label combines two predicates. Measured separately:

- 631 candidates touch an original-source threshold-127 connected component not exactly covered by the SIG group's glyph union.
- 249 glyphs also extend beyond their Inter region; **all 249 are stems**.
- Those 249 are a subset of the 631. The union is still 631, not 880.

The original raster retains staff lines and pixel contacts. Processed per-symbol/compound glyphs are not required to partition each entire original-image component. For example, first-system head 2205, stem 3764 and beam 1444 all touch original component **60**, despite differing ownership groups. Fourth-system samples share component **491** and final-system samples share **847**. The dot is isolated component **601** and has no component escape, yet it still fails the fixed source-dark agreement rule.

| Sample | Source component pixels outside SIG glyph union | Centerline / staff-corridor evidence | Other notation bounds | Ledger bounds | Text bounds |
| --- | ---: | --- | ---: | ---: | ---: |
| 2205 | 68704 | 11429 / 30671 | 43968 | 1170 | 0 |
| 2685 | 62887 | 11178 / 30478 | 35426 | 0 | 0 |
| 3260 | 61784 | 11350 / 29043 | 35517 | 0 | 0 |
| 2668 | 67618 | 11556 / 32087 | 40376 | 0 | 0 |
| 3764 | 68642 | 11455 / 30798 | 43820 | 961 | 0 |
| 4969 | 64685 | 11336 / 31091 | 37359 | 0 | 0 |
| 6226 | 61610 | 11449 / 29512 | 35342 | 0 | 0 |
| 1444 | 68642 | 11455 / 30798 | 43820 | 961 | 0 |
| 1785 | 61610 | 11449 / 29512 | 35342 | 0 | 0 |
| 8559 | 56338 | 11548 / 29697 | 25056 | 41 | 0 |
| 8584 | 0 | 0 / 0 | 0 | 0 | 0 |

These are overlapping **evidence categories**, not definitive ownership labels. JSON additionally records attached head/stem/beam bounds, gray values 1–127 and unclassified counts. Ten samples have staff-connected source escapes with other notation present; zero sampled escaped pixels intersect the retained text protection bounds. Related head/stem/beam-bound counts are small but nonzero. Ledger evidence occurs in first-system samples and the flag component; most remaining pixels are connected staff/notation and gray boundaries. `gray_edge_1_to_127` identifies intermediate intensities, not proof that every such pixel is antialiasing. Roughly 2,740–3,488 residual pixels per non-dot sample remain outside these geometric/intensity labels, so their precise ownership stays unresolved.

Three sampled stems demonstrate the independent bounds mismatch: glyph 1 extends to y=514 while stem 3764's Inter region ends at y=504; glyph 79 extends to y=1700 while stem 4969 ends at y=1688; glyph 692 begins at y=3196 while stem 6226's Inter region begins at y=3207. Java explicitly permits distinct glyph/Inter bounds; seed/compound support must not be mistaken for an exact per-Inter edit mask. This observation is not authorization to widen a mask.

**F / HIGH:** demanding that a small musical group's glyph union exhaust every original-source connected component is structurally too strong for staff-connected notation. That does not by itself supply a safe replacement rule. Component splitting, clipping and staff removal were not performed.

## 7. Staff corridor: explain 569 alarms

The original five-pixel-wide corridor follows the staff polylines; it is not staff ownership. The study separately decoded the 40 explicit staff-line glyph references 197–236, containing 278,419 unique assigned pixels. These are independent of musical candidate IDs but still Audiveris's own attribution, not human ground truth.

The current 569 alarms contain **62,084 candidate pixel references** that are dark in source at 127 and inside that corridor. **Zero** of those alarm references occur in the serialized staff-line glyph assignments. All 569 alarmed candidates lack staff-glyph membership in their alarm pixels. The sample's only candidate/staff-glyph overlap is one pixel in head 2685, but that pixel is above 127 in the original source and therefore was not part of the Phase 1.9 staff alarm.

The sample table distinguishes rasterized centerline pixels from other corridor pixels. Most corridor pixels are off the one-pixel centerline: 108/135 for head 2205, 95/124 for head 2685, 48/63 for head 3260 and 39/48 for the open head. Centerline proximity still does not establish whether an original pixel belongs exclusively to staff, symbol or an inseparable crossing. Staff-line glyph attribution can omit ink around a note; absence from that assignment does **not** prove absence of physical staff-line contribution.

**G / HIGH** for representation mismatch: the corridor is detecting musical glyph pixels near/on logical line geometry, not certified staff-line ink. Java explicitly builds NO_STAFF by removing staff-glyph pixels before several glyph stages; heads use BINARY/template selection instead. Consequently neither a corridor overlap nor a NO_STAFF origin authorizes erasure/restoration of original pixels. Exact source staff ownership at crossings remains unresolved and blocked.

## 8. Decision and next principled design boundary

| Classification | Verdict / confidence |
| --- | --- |
| A: decoder bug | No defect established / HIGH confidence in audited semantics |
| B: coordinate transform mismatch | No systematic displacement supported / HIGH; all candidates agree with BINARY at zero |
| C: original vs processed raster | Dominant, demonstrated / HIGH |
| D: gray threshold / antialias representation | Dominant, demonstrated / HIGH; no improved threshold chosen |
| E: shared/compound glyph semantics | Demonstrated related different-glyph overlap / HIGH; no unrelated overlap found in this scope |
| F: component admission too strong | Demonstrated staff/system connectivity and bounds mismatch / HIGH |
| G: staff representation mismatch | Demonstrated corridor versus staff-glyph attribution / HIGH; actual crossing ownership remains unresolved |
| H: combination | **Dominant classification / HIGH** |
| I: unknown | Historical pre-process digest and exact pixel ownership at crossings remain unknown; they do not prevent identifying the representation mismatch |

**READY_FOR_INK_ISOLATION_FIX** means there is enough evidence to design a new, versioned separation of processed glyph support, original-raster pixel ownership, explicit shared-group reconciliation and staff/protection constraints. BINARY can corroborate glyph coordinates/construction; it must not become permission to claim or erase original pixels. Inter bounds and seed/compound bounds need separate meanings. Any future group reconciliation must account for each shared pixel explicitly and retain unknown/protected pixels as blockers. Independent pixel annotations are needed before making broad ownership-accuracy claims.

No isolation change is implemented here. The unchanged Phase 1.9 remains `NEEDS_INK_ISOLATION_FIXES`, with 0 VERIFIED, and Phase 1.10 remains unexecuted. These measurements do not authorize a coverage-improvement pass, renderer, font, API/frontend/runtime route or production release.

## Artifacts, reproduction and tests

Local untracked directory: `v4-jayu-provenance-diagnostic/ink-forensics/`:

- `sample-manifest.json`: fixed geometry/shape sample selected before measurements.
- `ink-forensics-summary.json`: all requested per-sample measurements, full intensity histograms, translation grid, threshold curves, shared pairs, component evidence, hashes and supplemental measurements.
- `sample-01.png` through `sample-11.png`: original-coordinate crops with panels A source, B glyph, C source-dark, D intersection, E glyph-only and F source-only. No crop is a reconstructed score; images are diagnostic montages only.
- `reproduced-source.png`, `raster-comparison.json`, `ink-forensics-supplement.json`: raster reproduction, global BINARY agreement and exact staff-attribution measurements. Extra measurements were added after the fixed sample analysis without changing any Phase 1.9 admission rule.

The helper never returns OwnedInk or calls the isolation/mask admission function. It uses an explicit preexisting manifest and refuses to overwrite an existing initial summary. Supplemental measurements only add provenance/staff analysis to that summary. To reproduce initial measurements into a new output directory:

```sh
python -m scripts.omr_v4.ink_forensics v4-jayu-provenance-diagnostic \
  --manifest v4-jayu-provenance-diagnostic/ink-forensics/sample-manifest.json \
  --out NEW_EMPTY_FORENSIC_DIRECTORY
```

After separately reproducing the input raster with the exact fixed pdftoppm command, add supplemental analysis using the same helper with `--supplement-existing --reproduced-raster PATH`. This does not run Audiveris or correct any coordinates/thresholds. No second recognition or revised ownership run occurred.

Synthetic regression tests verify the independent Java RLE fixture in both orientations, nonsquare axes/empty sequences, measurement immutability/off-page denominators, sharing categories, deterministic JSON/PNG artifacts and unchanged source bytes. Developer analysis imports the existing parser and graph relation typing; no production modules are modified. The unchanged source hash is checked again after the measurements. Targeted V4 tests and relevant V3 music/gate regressions are run; no full acceptance/holdout/browser tests or CI polling.

The binary support and labels originate from the same Audiveris run: this is provenance/representation corroboration, **not independent ground truth for musical ownership**. No general success rate is inferred from the development sheet. No source pixels were overwritten, no finished transposed score rendered, and no merge or deployment occurred.

Final validation: `python -m pytest tests/test_omr_v4_*.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py -q` — **234 passed, 1 existing environment-dependent skip**. `git diff --check` passed. Cold-read review of the handoff excerpt confirmed the distinction between processed support and original ownership; this document specifies the 642-candidate scope, typed relations, literal fixture independence and evidence paths. READY here identifies enough evidence for a future design discussion; this pass implements no isolation fix.
