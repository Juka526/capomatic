# GT-07A protected text provenance

**TEXT_PROVENANCE_EVIDENCE_READY** means the persisted lineage, diagnostic support maps and source-only review packet are ready for inspection. It does **not** mean text ownership is confirmed or protection may be refined. Independently confirmed text extent/intersection remains **UNKNOWN**; human labels collected: **0**. All protection envelopes remain unchanged.

Branch `experiment/v4-gt07-text-provenance`; worktree `/private/tmp/capomatic-v4-gt07-text`. Exact base **`cdb50339d89db475f016c922f4a8f6d40e7383fd`**. [Audit protocol](V4_GT07_TEXT_AUDIT_PROTOCOL.json) committed as `c7ba676` before measurement; execution revision **`4638c8103cc30b0b0c423d631f57e5001595165f`**. The final report SHA is supplied in the final handoff and local validation manifest; identify the report commit with `git log -1 --format=%H -- docs/V4_GT07_TEXT_PROVENANCE.md`.

## Original persisted objects

The source is unchanged GT-01 Bb, PDF page 2. `recognized.omr` has `book.xml`, `sheet#1/BINARY.png`, and `sheet#1/sheet#1.xml`. The helper checks raw Inter attributes/containment against the frozen visual graph by ID, never XML ordering. Coordinates are original **2520×3564**, RGB raster coordinates, with no rescaling.

| Object | Raw Inter / role | Raw bbox | Persisted glyph | Support pixels |
| --- | --- | --- | --- | ---: |
| `4134` | **sentence**, role `Direction`, staff 2 | [945,588,1290,1011] | none; contains words 4135/4136/4138 | 0 of its own |
| `4135` | **word**, shape TEXT; no own role | [945,588,1054,968] | 4128 | 2,656 |
| `4136` | word, shape TEXT | [1067,591,1118,1011] | 4123 | 2,079 |
| `4138` | word, shape TEXT | [1248,591,1290,1011] | 4126 | 1,928 |

The often-called “Direction 4135” is a word whose protection label inherits its sentence's role. The unchanged [visual graph protection builder](../backend/omr_v4/visual_graph.py) propagates explicit parent roles. Parent 4134's bbox is exactly the union of these three child word bboxes. Word 4135's location is [945,591]; its raw font identifier is `S-400`; sentence font is `S-382`. Exact raw XML, OCR strings, fonts, grades, locations and graph edges are retained in local `text-provenance-report.json`. OCR strings are not human transcriptions.

There are three raw containment edges from 4134 to 4135/4136/4138. No other persisted graph edge to a musical chord/articulation/fermata is found for these four objects. Absence of an edge does not prove physical independence. Why the upstream recognizer grouped these text fragments this way, and whether `Direction` is the appropriate semantic role, is not established from the saved objects alone.

Supplemental exact glyph-set intersection finds other text counterparts, **not extra SIG edges**: word 4135 shares 1,107 pixels with lyric-item 4106, 546 with lyric-item 4107, and 405 with word 4177; word 4136 shares 951 with lyric-item 4109 and 1,128 with word 4178; word 4138 shares 802 with lyric-item 4111 and 1,126 with word 4180. All counterpart glyph IDs differ. This demonstrates overlapping/derived text support rather than forced disjoint ownership. It does not prove construction ancestry or a complete physical text partition. `related-text-support.json` preserves IDs, bboxes, glyph IDs, counts and the exact-intersection method for independent inspection.

**The broad geometry is already in the OMR, not manufactured by the Python parser.** Child glyph support itself spans widely separated vertical bands. For example, word 4135 has occupied y bands **588–628, 634–673, 929–967**: no glyph-support pixels in the large intervening region that contains staff/music. Words 4136/4138 extend to y=1010. The source-only context visually shows separated Korean text rows around a staff system. This is coordinator inspection, not an independent transcription or permission to reassign pixels.

## Diagnostic categories, not ownership

Union descendant word support contains **6,663 distinct pixels**, all 6,663 agreeing with persisted Audiveris BINARY foreground. This corroborates processed-raster provenance, not exact original grayscale text ownership. Only 4,544 are <127 in the original grayscale; the threshold is descriptive and never used to admit/delete pixels.

Categories depend only on source OMR support, not A/G reference images:

- **TEXT_INK_CANDIDATE:** descendant word-glyph support not also musical-glyph support.
- **MUSIC_INK_CANDIDATE:** musical Inter glyph support not also these words' support.
- **SHARED_OR_AMBIGUOUS:** exact overlap of those two support sets.
- **UNCLASSIFIED:** neither set, including background, fringe, staff ink not covered by these Inter glyphs, or unrecognized content. Absence of support never clears a pixel.

At the original-resolution context [900,548,1330,1051]:

| Category | Coordinates | Original gray <127, descriptive |
| --- | ---: | ---: |
| TEXT_INK_CANDIDATE | 6,663 | 4,544 |
| MUSIC_INK_CANDIDATE | 8,427 | 7,203 |
| SHARED_OR_AMBIGUOUS | 0 | 0 |
| UNCLASSIFIED | 201,200 | 6,107 |

Zero shared support is **not** zero ambiguity in the source. Many source pixels remain unattributed and no complete source ownership is certified. Diagnostic map colors: blue=text candidate, orange=music candidate, purple=shared, gray=unclassified. This map is not an edit mask.

## GT-06 intersection audit

To audit the frozen GT-06 measurements, the helper replays only its documented component **masks**, verifies their complete union byte-for-byte against the frozen alpha PNG, and verifies the exact historical intersection totals. It emits no new score or changed prediction. A/G reference pixels are not used for source classification.

| Target | Broad envelopes, unique pixels | Confirmed text | Text-support candidate | Shared support | Music-support candidate | Unclassified |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| A | **1,982** | **UNKNOWN** | 0 | 0 | 1,661 | 321 |
| G | **2,026** | **UNKNOWN** | 0 | 0 | 652 | 1,374 |

These are source support categories at proposed target coordinates, not accepted ink ownership or an accuracy denominator. Independently confirmed source musical-ink intersections are likewise **UNKNOWN**; 1,661/652 are only persisted musical-glyph support candidates. The older original-dark measurements are reproduced exactly: A 1,543 / G 556. They are not verified lyric counts.

Both 4134 and 4135 yield the same target hit sets here, so their per-region counts are **not additive**. Nested parent/child protection can duplicate pair counts; union pixel totals stay 1,982/2,026. Both protections remain logically active. Lack of text-glyph overlap at these GT-06 target coordinates does not justify discarding a region that includes real text elsewhere.

## Source-only human extent review

Untracked root `/private/tmp/capomatic-v4-gt07-text/gt07-text-output/` contains:

- `direction-context-source.png`, individual `object-4134/4135/4136/4138-source.png` crops.
- Matching grayscale and source-alpha images; source RGB is opaque, so alpha is uniformly 255, **not** glyph opacity or an ownership mask.
- `text-glyph-support.png`, `music-glyph-support.png`, `diagnostic-support-categories.png`.
- `text-provenance-report.json`, exact glyph RLE/relations/raw XML, `source-category-summary.json` with grayscale histograms, `related-text-support.json`, `custodian-only.json`.
- `independent-review-packet/`: **5 overlapping source-only cases**, 8 files, opaque case IDs, separate blank A/B forms and instructions. No OCR values, predictions, support maps, region classifications or suggested extents.

The custodian must distribute **only** the packet, never the surrounding output directory/report. Each independent reader declares prior exposure and exclusions, traces text extents/uncertain regions in crop-local pixel-center coordinates, and may choose UNKNOWN or MIXED. Original observations are preserved and separately hash-frozen; only after both freezes may a separate adjudicator review disagreements in a new record. Do not overwrite either original. No submissions were collected, frozen or adjudicated in this task. These overlapping cases are targeted forensic evidence, not independent accuracy samples.

The historical GT-02 111-case packet and GT-03 14-case pilot remain separate and unchanged. This packet does not replace them. Any later proposal to refine masks requires source-only independent extent evidence, persisted lineage, preservation of every text/fringe pixel and explicit separate authorization. Uncertainty remains protected.

## Provenance, validation and limits

Source PNG SHA-256: `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`.
OMR SHA-256: `857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638`.
Graph SHA-256: `f8725c39beaaecc877ccf48b803b79a419c2d6e60aa73bc9428a39de11596508`.
The local report binds the protocol, GT-06 freeze, protection JSON and packet hashes. Source hash is verified again after extraction. The source-derived grayscale/alpha crops never replace source.png.

Targeted GT-01–07A/V4/V3 music/gate regressions: **382 passed, 1 skipped** (existing external MuseScore dependency). Nine new tests cover disjoint categories, missing lineage, page-coordinate escape, bbox voids, deterministic neutral packets, independent reader forms and changed freezes. Formatting/diff checks and final preservation are recorded in `validation-summary.json`. No Audiveris/OCR execution or Full Acceptance.

Original V3 musical-integrity results remain the frozen GT-06 A/G PASS (37 measures, 169 events, 7 harmonies each); this track creates no new semantic score and waives no guard. Source recognition completeness and physical text ownership remain unresolved. Next step: collect the independent extent observations and adjudication; do not implement protection refinement from this audit alone.

No source PDF/raster editing, protection/ownership-gate change, Track A PARTIAL promotion, V1/V3 production change, renderer/B2 change, API/frontend/runtime route, merge or deployment.
