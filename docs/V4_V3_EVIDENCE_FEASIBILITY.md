# V4 Phase 1.9e: upstream evidence feasibility

Decision: **READY_FOR_V3_EVIDENCE_EXPORT**. This authorizes no ownership promotion or rendering. Existing 1.9d remains **NEEDS_HANDOFF_FIXES**; 1.10 did not run. Phase 1.8 remains COMPLETE-only: 0/249 notes and 0/66 beam groups approved.

Analyzed branch `feature/score-v4-layout-preserve`, starting commit `22bb345f81eb94bdeed0f550d00ec6a3894b872d`. This study reads existing jayu artifacts and exact Audiveris source revision `7a36078e7ba0c006052c1f661b949cf9b729f505`. It does not run recognition, isolation or handoff classification again. Prior results in [ink isolation](V4_SYMBOL_INK_ISOLATION.md), [forensics](V4_INK_PROVENANCE_FORENSICS.md) and [handoff](V4_REFINEMENT_HANDOFF.md) remain historical results.

## 1. Actual archive inventory

The OMR contains exactly `book.xml` (1,751 bytes), directory `sheet#1/`, `sheet#1/BINARY.png` (176,726 bytes), and `sheet#1/sheet#1.xml` (2,340,107 bytes). Image declarations are not image resources: XML declares GRAY, BINARY and HEAD_SPOTS, but only BINARY exists.

| Evidence | Availability in this OMR | Limits |
|---|---|---|
| Input path, software/build, completed stages, page dimensions | PERSISTED_IN_OMR | No original-input cryptographic digest or original image bytes |
| GRAY, original source PNG, HEAD_SPOTS raster | NOT_PERSISTED | Source PNG is an external V3 diagnostic artifact |
| BINARY raster | PERSISTED_IN_OMR | Adaptive processed raster, not original grayscale ownership |
| NO_STAFF raster | DERIVABLE_FROM_OMR | Exact persisted-state replay; no retained runtime snapshot |
| Staff geometry, thickness, line/glyph IDs, glyph runs | PERSISTED_IN_OMR | Attribution is not physical ink separation |
| Staff holes/recovery history, intermediate filament section DAG | NOT_PERSISTED | Cannot recover an original editing mask from absent history |
| Head/stem/beam/hook/flag/dot/key-alter final glyph references and runs | PERSISTED_IN_OMR | Construction recipe and candidate-to-final DAG are not serialized |
| Slur/tie glyphs, cubic curves, endpoints, extension references | PERSISTED_IN_OMR | Extensions do not establish a missing endpoint owner |
| Articulation/fermata glyphs and typed relations | PERSISTED_IN_OMR | Explicit relationship does not prove raster completeness |
| Ledgers, glyphs, staff ledger-index membership | PERSISTED_IN_OMR | No explicit head-ledger ownership edge in this sheet |
| SIG, containment, systems/staves/stacks/slots/voices | PERSISTED_IN_OMR | Some edges are explicit IDREF fields rather than SIG relation elements |

There are 1,735 glyphs: 944 without a group tag, 509 SYMBOL, 282 VERTICAL_SEED. Final Inter references include 249 heads, 249 stems, 115 beams, 4 hooks, 14 flags, 11 dots, 8 key alters, **67 slurs, 38 articulations, 2 fermatas and 11 ledgers**. All 249 final stems reference a VERTICAL_SEED-tagged glyph. This is a persisted identity/tag, not a reconstructed compound ancestry.

Raw SIG includes 249 head-stem, 340 beam-stem, 249 chord-stem, 545 containment, 130 slur-head, 53 beam-beam, 38 chord-articulation, 2 fermata-chord, 14 flag-stem and 11 augmentation relations. It also contains text, clef/key, bar-group, time, dynamics and pedal relations. The V4 graph additionally retains two left-extension and two right-extension IDREF edges. All glyph support means all 1,735 persisted glyph run tables, not all original-raster ink or all runtime intermediate support. Attribution covers every existing PARTIAL handoff group against those persisted resources; unmatched pixels remain unknown. The exact sheet XML is exported to avoid losing unmodeled fields.

## 2. NO_STAFF verdict and source-code basis

Verdict **B for the serialized state**: `NO_STAFF = BINARY with exactly the serialized staff-glyph union painted white`. There is no approximation, inferred staff pixel or logical-line rasterization in this operation. There is **no captured runtime NO_STAFF** to compare against, so historical cache equality remains **UNVERIFIED**, not an asserted byte/pixel match.

The pinned source establishes the operation:

- [Picture.buildNoStaffBuffer / getSource](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sheet/Picture.java): BINARY copy, white rendering of every StaffLine glyph; NO_STAFF is a lazy derived source.
- [RunTable.render](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/run/RunTable.java): integer horizontal/vertical run rectangles at glyph top-left; no line interpolation.
- [StaffFilament.toStaffLine](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sheet/grid/StaffFilament.java) and [StaffLineCleaner.process](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sheet/grid/StaffLineCleaner.java): filament simplification retains an original glyph while runtime section collections are removed/rebuilt.

Replay on jayu uses all **40 lines / 278,419 distinct staff-attributed pixels**. Unit tests independently verify run coordinates and whitening only those pixels, including gaps that must remain untouched. This proves the persisted-state transformation, not temporal equality to a buffer cached earlier in recognition. A historical snapshot would require retained runtime evidence; this pass does not instrument or rerun Audiveris.

## 3. Staff evidence and construction lineage

Every line exports staff ID, line number, serialized polyline and thickness, glyph ID and exact RLE attribution. Logical geometry and attributed pixels remain separate. Musical glyph intersections are measurable; absent attribution does not establish absence of physical staff ink. No removed/recovered pixel journal is present.

| Symbol | Proven class-level construction | Recoverable instance evidence / missing history |
|---|---|---|
| Head | [NoteHeadsBuilder](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sheet/note/NoteHeadsBuilder.java) supplies BINARY to [HeadInter.retrieveGlyph](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sig/inter/HeadInter.java); template foreground becomes glyph runs | Final glyph, head-stem and chord membership; template sampling history not serialized |
| Stem | [StemBuilder.createStem](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sheet/stem/StemBuilder.java) uses seed or compound glyph | Final glyph/tag and relations; no source-chunk/filament parent list; Inter bounds are not glyph clips |
| Beam/hook | [BeamsBuilder](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sheet/beam/BeamsBuilder.java) uses NO_STAFF | Final glyph, beam-stem/beam-beam/group references; candidate/final history absent |
| Flag/dot/alter family | [SymbolsFilter.process](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/sheet/symbol/SymbolsFilter.java) cleans a NO_STAFF buffer before symbol retrieval | Final glyph and typed relation when present; no per-instance builder/crop log. Jayu has key-alters, no standalone alter-head examples |
| Slur/tie/articulation/fermata/ledger | Final support and geometry survive | No claim of complete original-source ownership; no reconstruction performed |

[Glyph](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/glyph/Glyph.java) serializes position and run table, not construction parents. [GlyphFactory.buildGlyph](https://github.com/Audiveris/audiveris/blob/7a36078e7ba0c006052c1f661b949cf9b729f505/app/src/main/java/org/audiveris/omr/glyph/GlyphFactory.java) unions parts into a new run table without storing their membership. Class-level source knowledge must not be promoted to an instance history. SlurInter serializes curve/tie/extensions, while its richer `SlurInfo` construction object is transient.

## 4. All 99 continuation blockers

`blocker-attribution.json` contains a separate row for every PARTIAL group. This is exact support intersection measurement, not a new handoff verdict. The existing remote guard already excludes staff context, staff-attributed pixels, group support and some known attachment support. Consequently zero hits in those excluded classes are **not evidence that upstream staff/group topology is absent**.

| Direct attribution | Groups with hits | Pixel references |
|---|---:|---:|
| Ledger glyph | 8 | 120 |
| Slur glyph | 27 | 43 |
| BINARY foreground without referenced symbol support | 17 | 229 |
| Outside persisted BINARY | 99 | 8,372 |
| Staff / same-group / neighboring head-stem-beam / articulation-fermata / other referenced glyph | 0 | 0 |

There are **8,764 distinct remote pixels**, of which **163** intersect extra persisted glyph support. **0/99 groups are fully explained**. Group counts can overlap; none is eligibility. No seed/compound DAG survives to resolve the remaining points.

The source values are not uniformly dark: 4,282 remote pixels have grayscale 254. Handoff uses `gray < local_background` within a finite radius-four guard adjacent to local visible pixels, not a measured page-wide remote connected component. Thus these points cannot all be called unexplained remote musical ink. Original grayscale variation/antialias boundaries remain unresolved; BINARY exclusion does not prove background ownership either. The full intensity histogram is exported. No threshold or handoff rule changed.

Primary answer: **D, combination**. Missing V4 use of persisted slur/ledger support explains a small measured subset (A); transient construction history is absent (B); attribution of remaining original-raster boundary/topology is not established by processed support (C). Confidence HIGH for these observations; the physical cause of each unassigned pixel is UNKNOWN. Existing broader local continuation categories remain unchanged rather than being relabeled as proven ownership.

## 5. Moving attachments in the 87 blocked groups

Counts below distinguish repeated group references from unique symbols. Explicit relation availability is not proof that an attachment belongs exclusively to that atomic group: a slur can connect two groups.

| Category | Group references | Unique symbols |
|---|---:|---:|
| EXPLICIT_RELATION_AND_GEOMETRY_AVAILABLE | 162 | 103 |
| CROSS_SYSTEM_EXTENSION | 4 | 4 |
| PIXEL_SUPPORT_AVAILABLE_BUT_RELATION_AMBIGUOUS | 16 | 11 |
| RELATION_AVAILABLE_BUT_PIXEL_SUPPORT_MISSING / NOT_PERSISTED / UNKNOWN | 0 | 0 |

The 162 explicit references comprise 120 slurs, 40 articulations and 2 fermatas. The 16 ambiguous references are ledgers: glyphs and staff/index membership are present, but no head-ledger edge proves ownership. The four cross-system slur/tie segments retain their extension references and remain unresolved. Every row retains symbol and relation IDs, support pixel count and `group_ownership_proven: false`.

## 6. Bundle and implementation boundary

Implemented **A: pure offline OMR extractor**, with **B: V4-only packaging of existing semantic snapshots**. No optional production mode or Audiveris changes are needed.

Run from the repository using existing artifacts:

```sh
python -m scripts.omr_v4.extract_v3_evidence \
  v4-jayu-provenance-diagnostic \
  --out v4-jayu-provenance-diagnostic/v3-evidence
```

Run from the repository root in the existing V4 Python environment (Pillow, numpy, OpenCV and the project test dependencies); Audiveris is not required. The input directory must retain the source/OMR, semantic snapshots/report, 1.9c summary/evidence and 1.9d handoff used above. A new/empty output is required. The local generated bundle is untracked. Manifest schema `capomatic.v3-evidence/1` binds each output hash to source SHA, native raster digest/mode, OMR SHA, pinned build, dimensions, original XY coordinates, extraction method and exact/derived/external status. Original `book.xml` and sheet XML accompany source/BINARY, derived NO_STAFF, staff evidence, all glyph support, symbol references, relations and per-group blocker attribution.

`pre-ledger.musicxml`, `post-ledger.musicxml`, ledger repair provenance and integrity report are copies of **external existing diagnostic artifacts**, not recoverable OMR resources. Their availability and hashes are explicit. The chord-only warning remains in the integrity report; export never becomes production integrity approval. Hash checks verify the historical artifact pair supplied by 1.9c and handoff bindings; OMR itself does not cryptographically authenticate its original input. These are distinct claims.

Source encoded SHA-256: `e53c52dd7c31f0196b7c5a99231afd4f77bc522f8a02483277179a79c84dc0cb`.
OMR SHA-256: `e5076145d9b682f77d3bcf333996d9dd33c3c0b5cb6a597caf7b330c6981e29b`.

The extractor rejects unknown builds, mismatched hashes/dimensions, invalid glyph coordinates, missing BINARY, missing staff glyphs and dangling symbol glyph references. No absent pixels or parent relations are inferred. It never constructs OwnedInk or calls an eligibility/mask planner.

## 7. Expected value to V4

| Current blocker | Upstream value | What improves / what remains |
|---|---|---|
| Antialias boundary, 99 groups | LOW | Processed-vs-original distinction becomes explicit; no original alpha/stroke ownership map exists |
| Continuation, 99 | MEDIUM | Slur/ledger supports explain 163 pixels; most boundary points and all group-level blockers remain unresolved |
| Moving attachments, 87 | HIGH | Typed edges plus final glyphs exist for most references; ownership across connected groups still needs analysis |
| Staff, 23 | MEDIUM | Exact staff attribution and persisted-state NO_STAFF support topology studies; holes and original-source restoration are not solved |
| Other, 15 | LOW | Full XML/support inventory helps name contacts; it cannot automatically authorize a partition |

Blocker counts are overlapping subsets of the 99 PARTIAL groups among 105 atomic groups; they are not a partition and are not counts of the 249 notes or 66 beam groups. These counts measure resource availability, not matching accuracy or source ownership. Synthetic tests check decoder/export mechanics independently of jayu. No real-sheet validation of new ownership rules occurred, and no empirical pass threshold was introduced. Export succeeds operationally when required resources and provenance checks pass and every listed file verifies against the manifest hash; this does not certify ownership or historical runtime equality.

## 8. Validation and stopping point

Targeted V4 tests plus `tests/test_omr_v3_music.py` and `tests/test_omr_v3_gate.py`: **285 passed, 1 skipped**. New extractor tests cover hash binding, dimensions, BINARY copy, staff decoding, exact/derived labels, persisted-state NO_STAFF replay, missing resources, deterministic bytes/JSON, source invariance, external snapshot labels and attribution without ownership. `git diff --check` passed.

Only feasibility documentation, V4 offline helper/CLI and tests changed. No V1/V3 runtime change, Audiveris rerun, original raster edit, renderer, API/frontend/runtime route, merge or deployment. Phase 1.9d and 1.10 did not run. Next work requires a separately authorized analysis design using the richer support; **READY_FOR_V3_EVIDENCE_EXPORT is not Phase 1.9 success**.
