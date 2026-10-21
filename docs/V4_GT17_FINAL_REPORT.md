# Capomatic V4 GT17 FINAL research release

This release generates new standalone A-major (−1 semitone) and G-major (−3 semitones) experimental scores from the original B-flat page-2 evidence. It covers nine systems and 37 printed measures with 169 approved recognized note/rest cores, 24 chords, 167 Korean syllables and exact onset associations, and 50 visible continuation marks. It does not establish independent source-recognition completeness, a unique full repeat traversal, or performance readiness.

All score exports carry **DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / INCOMPLETE — NOT FOR PERFORMANCE OR PRINTING**. No architecture winner is selected.

## Release identity and history

One worktree: `/private/tmp/capomatic-v4-gt17-final`. One branch: `experiment/v4-gt17-final`. Exact base: `dab7562fa504130be9f13f7a9df8ca7afca9b847`. The final revision is the commit containing this report; it is reported separately after commit to avoid a self-referential hash. In this checkout, `git log -1 --format=%H -- docs/V4_GT17_FINAL_REPORT.md` identifies that containing revision; the post-commit local release record binds it to the final artifact manifest.

| Stage | Frozen revision | Contribution retained |
|---|---|---|
| GT16C | `4da717a8e8675db84ea6a6b941bec3d4dacc86a5` | Owner-approved experimental optical-layout baseline |
| GT17 | `36a6b153aa40f44986b30ca112e73114e8c8ec79` | Fifth-system audit and provisional notation |
| GT17B | `1c532c4a6cfa332a50e889740088aed064511996` | Nine-system provisional full-score rendering |
| GT17B owner integration | `ff4dd9dbb12a21807ba3b3672eac5b519ebbc5f3` | Approved text/chords and source-supported curves |
| GT17C | `477b418d982c95c430531ba46d999cd40448e2e2` | Remaining accuracy and delta-review audit |
| GT17D | `55b72a2fb2162ee4ba913b99310932fbb26fcfab` | Removed only erroneous 4867 semantic slur |
| GT17E | `ad0a249e3621d4755b70ee82dbd20e79f48a1c7a` | All event cores; SYS6 lyric onsets approved |
| GT17F | `dab7562fa504130be9f13f7a9df8ca7afca9b847` | Final 39 lyric-onset approvals |
| GT17 FINAL | containing commit | Consolidated classifications, extension semantics, fresh engraving and validation |

Systems retain printed ranges **1–4, 5–8, 9–12, 13–16, 17–19, 20–24, 25–29, 30–33, 34–37**. Recognized inventory agreement is not an independently verified accuracy denominator.

## Frozen source and preservation

| Input | SHA-256 |
|---|---|
| Original three-page PDF, whole-file hash only | `1cc64756c0ce47b1db0ea6ac21eefe4685097a04cd4589f954afc712afb605fd` |
| Original B-flat page-2 raster | `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de` |
| Persisted original OMR | `857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638` |
| Original visual graph | `f8725c39beaaecc877ccf48b803b79a419c2d6e60aa73bc9428a39de11596508` |
| FreeSerif font, unchanged GT05 identity | `c1dd2270ff624d66a7f1cd23075b5ce05a662f560be06a70a9599065ce008355` |
| AppleGothic | `def69dc2b5e12746049a5dcb189f95341ec460589f47587938567313af3020b1` |

The PDF is 3,574,780 bytes. This run hashes it without parsing or rasterizing reference pages 1/3. Existing B-flat source raster, source objects and approved records provide all prediction inputs. The original RGB raster is wrapped in a separate diagnostic canvas, never edited in place.

`final-preservation-verification.json` binds the historical file inventory; 1,298 recorded historical files were rechecked at closeout. All original frozen evidence files retain their hashes. One unrelated `.Rhistory` addition in the historical GT17C output directory is explicitly recorded as an unbound non-evidence addition; it is not used as an input, removed, or treated as an evidence-content waiver. No bound file changed or disappeared. The snapshot includes that addition for subsequent unchanged-run checking. Directory identity beyond the original freeze is therefore qualified, not silently asserted.

Source masks, protection envelopes, raw OMR/SIG records, independent review packets and production files are unchanged. No source ink was removed. Copyrighted raster/XML/PDF artifacts remain outside commits.

## Consolidated approval coverage

| Field | Owner-approved coverage | Limitation |
|---|---:|---|
| Recognized note/rest cores | 169/169 | No independent missing-event assessment |
| Chord interpretations | 24/24 | Not a general recognition-accuracy denominator |
| Korean wording and row | 167/167 | Newly typeset, not original lyric pixels |
| Exact syllable/onset associations | 167/167 | Existing event identities retained |
| Visible continuation classifications | 49 of 50 known marks | M28 ancestry remains unresolved |
| Newly approved raw SIG classifications | 27/27 | Interpretation layer only; raw observations unchanged |
| Independent ground truth / musician review | 0 / 0 | Owner approval is not independent validation |

The exact current approval excerpt is retained in [GT17_FINAL_OWNER_APPROVAL.txt](evidence/GT17_FINAL_OWNER_APPROVAL.txt). The generated ledger binds it to the GT17F interpretation, remaining plan and output-freeze hashes. Full `sheet#1:` IDs and source bboxes are retained.

Nineteen new visible continuation approvals and 27 raw-object classifications are integrated. Nineteen raw continuation objects have recorded source-region overlap links to existing canonical continuation records. Links are spatial evidence, not count matching. Canonical strokes are drawn once. Six Korean glyph-stroke interpretations and two ending punctuation interpretations add no duplicated glyph or independent articulation. Object 5747 remains part of existing ‘하’; 4867 remains part of ‘되’, never restored as a slur.

## Semantic changes and preservation

Actual `Bb-final-experimental.musicxml`, `A-final-experimental.musicxml` and `G-final-experimental.musicxml` are generated from the separate approved semantic source. The approved B-flat 169 event cores retain their pitches, durations, onsets and voices. Each target retains those relationships at its specified −1/−3-semitone transposition, with correct target chord roots and slash basses. Relative to the preceding approved interpretation, no note core, chord meaning, syllable/row/onset, or approved tie/slur relationship changes. A/G in-memory and serialized unchanged V3 full guards pass. The m21→22, m33 and m35 ties remain; the sole retained slur is the approved m31 unequal-pitch slur. False 4867 is absent.

New music-semantic elements are the justified lyric extensions. Three already approved plain section labels, Pre-Chorus/Chorus/Tag, are also retained as MusicXML words with no playback command. Work and movement titles carry the experimental warning. The inherited unverified OCR title is preserved in miscellaneous metadata rather than silently certified. The PNG heading uses the user-provided score identity as research metadata.

## MusicXML lyric extensions

The research serializer resolves original-side event paths from approved syllable onsets plus explicit approved same-pitch ties or the approved slur. It rejects ambiguous/missing paths and derives semantic spans before serialization. A visible dash is not equated with an XML element.

Of 50 known visible mark records, **49 have unambiguous lineage and map to 49 distinct spans**. B-flat, A and G each contain **49 `start` and 49 `stop` records (98 total); zero real-score `continue` records**. Synthetic multi-event, cross-measure and two-row tests exercise `continue`, sustained/repeated notes, legacy missing-type starts, roundtrip preservation, malformed roles, overlaps, orphan endpoints and accidental new syllables.

**Exception:** `continuation-m28-r1-stroke-0` remains printed in the visual score but is excluded from speculative XML lineage. Its held-syllable ancestry depends on unresolved repeat interpretation. Two older approved lower-row underlay marks lack persisted exact source bboxes; this absence is recorded explicitly. Their semantic paths use prior approved event/onset evidence, and their visual typography reuses the validated underlay contract; no source rectangle is copied from the other row.

The implementation follows the MusicXML definition of [extend](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/extend/) within [lyric](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/lyric/). Explicit event-row role signatures, not element totals alone, are tested. Exact official W3C v4.0 schemas are stored as untracked validation data with URL/hash provenance; all three final XMLs and all three consumer-adapted XMLs validate offline without schema edits.

Unadapted music21 exports drop all extension records. The research adapter reattaches verified lineage and checks its exact signature. Production export is unchanged. Actual MuseScore consumption also exposes a limitation: it exports 49 legacy starts but drops explicit stops. Thus raw native roundtrip is **not** lossless. A separate research adapter verifies each legacy start's exact event/row identity, restores the retained original-side endpoints, and passes signature, XSD and unchanged V3 guard checks. That restoration requires the bound lineage evidence; raw MuseScore output alone cannot recover the endpoints. Native consumer outputs are diagnostics and are not substituted for final engraving.

## Repeat playback

Visible notation is preserved: forward repeats at 1/20/30, backward repeats at 8/27/37; first endings at 8, 15–16, 26–27; second endings at 9/17/28. [Repeat](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/repeat/) and [ending](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/ending/) conventions do not manufacture a missing source repeat at 16.

The source m15–17 relationship is not uniquely resolved. Actual music21 repeat expansion raises `ExpanderException: cannot expand Stream: badly formed repeats or repeat expressions`. Alternative hypotheses remain documented in `final-repeat-playback-status.json`; no candidate is installed as a performance traversal. Owner-confirmed complete traversal: none. The printed 37-measure score remains reviewable independently of playback.

## Engraving method and alternatives

All nine systems are freshly rendered from existing calibrated glyph components; historical PNGs are not copied as new notation. Existing head/rest/stem/beam/flag and curve geometry is reused. A small research-only half-rest dispatch uses the existing calibrated half-rest glyph and verifies the persisted source shape. No production rendering code changes.

Protocol revision 2 is frozen in [V4_GT17_FINAL_PROTOCOL.json](V4_GT17_FINAL_PROTOCOL.json). Both lyric rows and their marks move together by the smallest integer displacement in 0–48 px that satisfies actual alpha safety, at least 6 px music-ink center clearance, and the measured prior minimum wherever available. Horizontal lyric/note anchors and row order/separation are unchanged. The first local-per-measure candidate was rejected because baseline steps were visually uneven and some historical clearances decreased. It remains frozen under `/private/tmp/gt17-final-local-candidate-frozen`; it is not the release.

The final uniform-per-system candidate maintains consistent lyric baselines. This new canvas can move the formerly frozen GT12 measure-3 lyric region; that is an explicitly separate experimental layout. Historical GT12, GT16B and GT16C bytes remain intact. Final A/G system-wise lyric shifts are respectively **[6,6,7,8,0,11,9,9,11] px** and **[15,15,16,17,4,20,18,18,20] px** relative to the declared fresh pre-layout masks.

Source x coordinates, measure widths, pitches, staff shapes and within-system musical geometry are retained. Whole-system vertical translations A=[0,0,18,13,9,0,0,15,0], G=[0,0,27,31,36,6,0,24,0] px are explicit in the transformed coordinate manifest. The 140-px warning band is outside source-page registration. No sounding octave is changed. Final canvases are **2520×3704 px**; one custom 604.8×888.96-point research PDF page embeds each 300-dpi canvas. This is not an A4 performance-print claim.

## Measured optical results

| Metric, per target | A | G |
|---|---:|---:|
| Rendered events / chords / syllables / marks | 169 / 24 / 167 / 50 | 169 / 24 / 167 / 50 |
| Maximum notehead residual per axis | 0.5 px | 0.5 px |
| Minimum lyric/music ink-center clearance | 6 px | 6 px |
| Exact pixel-square edge clearance minimum | 5 px | 5 px |
| Actual lyric/music contacts | 0 | 0 |
| Unexpected notation-mask contacts | 0 | 0 |
| Clipped systems / lost lyric pixels | 0 / 0 | 0 / 0 |
| Accepted 4× beam / curve components | 57 / 34 | 57 / 34 |
| Mean beam centerline absolute RMS, before→after | 0.3758→0.0467 px | 0.4100→0.0482 px |
| Intentional staff/curve contact pixels | 261 | 519 |

The fresh pre-layout minimum was 0 px; this is a development control, **not** a claim that every frozen historical score collided. Thirty of 32 lyric-bearing measure regions improve in A and 32/32 in G against that control. Fifteen later-system historical mask comparisons per target are measured separately; none loses its prior center clearance. Detailed per-measure values and component hashes are in `final-rendering-validation.json` and `final-consolidated-validation.json`.

4× BOX sampling preserves declared beam endpoints/control points and tested stem/beam connections, without ringing-based support. All 91 candidates per target pass the predeclared checks. All 64 checked curve endpoints per target retain source event/head identities; measured endpoint/head ink-center distances span 2.5–15.133 px within the specified staff-relative attachment window. A tie curve deliberately clears the head rather than requiring physical ink overlap. No broken required head/stem/beam/flag connection is accepted. Intentional staff/curve contacts are measured and remain an optical limitation, not relabeled zero.

## Actual image and PDF inspection

The final A/G PNGs and actual 300-dpi Poppler renders of both PDFs were opened. Native-pixel G m13, G m21–22, G m31 and A m21–22 details were also inspected. Korean rows and low notes are separated, beam edges are smoother, and chord/section/ending ordering is readable. Dense horizontal lyric groups and small staff-crossing curves remain visually constrained at reduced display sizes. Agent verdict: **ACCEPTABLE_FOR_EXPERIMENT_WITH_OPTICAL_LIMITATIONS**. No independent optical or musician validation occurred.

The PDFs embed byte-identical RGB pixels from the final PNGs. Poppler's actual rendered rasters are not byte-identical: A has 463,682 differing RGB pixels (RGB RMSE 26.399), G 457,333 (26.481), at matching dimensions. Embedded-image identity and viewer rasterization are distinct measurements. Visual review found the same content and no missing page region; exact viewer-pixel identity is not claimed. Native diagnostic window edges intentionally crop neighboring content and are not full-score clipping failures.

## Artifacts and reproducibility

All paths below are inside `/private/tmp/capomatic-v4-gt17-final/gt17-final-output/`:

- `Bb-final-experimental.musicxml`, `A-final-experimental.musicxml`, `G-final-experimental.musicxml`
- `A-final-full-score.png`, `G-final-full-score.png`, `Bb-A-G-final-comparison.png`
- `A-final-full-score.pdf`, `G-final-full-score.pdf`
- All required `final-source-coverage`, `final-semantic-integrity`, `final-lyric-extender-validation`, `final-repeat-playback-status`, `final-rendering-validation`, `final-preservation-verification`, `final-owner-approval-ledger` JSON reports
- `final-visual-inspection.md`, `final-consolidated-validation.json`, `final-artifact-manifest.json` and detached manifest SHA-256
- `prediction-freeze.json`, 1,655 pre-inspection artifact hashes, exact producer hashes, protocol hash, software versions; native component maps/masks retain placement coordinates and hashes
- `native-consumer/`, `standards/`, `pdf-validation/`, font and original-PDF verification records

The final artifact manifest inventories actual relative paths, byte sizes and SHA-256 of all release files except itself and its detached checksum. The checksum binds the manifest; this is hash binding, not a fabricated digital signature. The tracked validation record binds the manifest after closeout. Historical untracked source evidence and exact fonts are required for reproduction; this is not a self-contained distributable score package. The bound historical input paths and individual hashes are enumerated in `final-preservation-verification.json`; original PDF and font paths are in `final-original-pdf-verification.json` and `final-font-validation.json`. The named virtual environment and immutable image must already exist. If any prerequisite is absent, reproduction is blocked rather than downloading substitutes. No model provisioning or dependency installation is part of this release.

Generate into a **new, absent directory**, never over the frozen release:

```sh
cd /private/tmp/capomatic-v4-gt17-final
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt17_final --output /private/tmp/gt17-final-reproduction-new
/private/tmp/capomatic-v4-venv/bin/python -m pytest tests/test_omr_v4*.py tests/test_v4*.py -q -ra
```

The producer records fixed configuration date 2026-10-21 and deterministic instrument IDs; this is not an owner-signature timestamp. Runtime measured before prediction freeze: **114.384 s**, parent peak RSS **464,814,080 bytes**, child peak RSS **191,545,344 bytes**. Parent/child maxima are separate peaks, not a summed simultaneous-memory figure.

## Regression and native integration results

| Check | Actual result |
|---|---|
| Relevant V4 suite, including 29 new cases | 780 passed, 0 skipped |
| Complete V3 `tests/test_omr_v3*.py` in existing immutable Docker image | 165 passed, 0 skipped |
| Source/A/G in-memory and serialized full V3 guards | Pass, unchanged guard |
| music21 research-adapted extension roundtrips | Exact event/row/role signatures retained |
| Actual MuseScore import/export | Bb/A/G exit 0; raw explicit extension endpoints lost, documented above |
| Native legacy-start identity validation and lineage restoration | 49 origins / 98 restored roles per file; unchanged guard passes |
| Official MusicXML 4.0 offline XSD | 3 final + 3 native-adapted files validate |
| Frozen prediction, original input and historical bound hashes | Preserved |
| Black formatting / `git diff --check` | Pass at closeout |

V4 ran with `/private/tmp/capomatic-v4-venv/bin/python`. V3 and actual `/usr/bin/mscore3` ran in existing image `sha256:fb3c1ff7f6428a499b18aae5dc0b71a5c8b03ee709b10ab82e3ab1f28e332b1e`, read-only repo, no network, isolated Qt environment and temporary working directory. The normally conditional `test_musicxml_fast_path_skips_gate_and_passes_integrity` actually executed and passed; it is already included in the 165 total.

Initial environment failures are not hidden: local V3 collection lacked FastAPI; a noexec container `/tmp` prevented three synthetic fake-tool tests; a plain native consumer call timed out before using the existing V3 isolated tool runner. No dependencies or models were installed and no tests/thresholds were weakened. The same unchanged V3 suite passes in the available image with executable temporary workspace. Exact source execution logs are preserved where generated; final passing suite logs are in the release directory.

The manual `.github/workflows/omr-v3-eval.yml` Full OMR V3 Acceptance Evaluation is **NOT RUN / DEPENDENCY BLOCKED**: the available image has MuseScore but lacks Java/Audiveris required for the full recognition stack. Paddle/PaddleOCR modules are present, but were not loaded or used for new recognition. Its Audiveris direct run, PaddleOCR end-to-end evaluation and API latency/multipage stages are not claimed passed. No new image build, model download, deployment, API server or feature-flag change was performed to force completion. This is separate from the 945 relevant unit/regression tests that actually passed.

## Separate quality gates and final scope

| Gate | State |
|---|---|
| `GT17_RESEARCH_WORKFLOW_COMPLETED` | TRUE, bounded research release |
| `PRINTED_SCORE_EXPERIMENTAL_OUTPUT_READY` | TRUE, for source/visual review |
| `MUSICXML_SEMANTIC_COVERAGE_PARTIAL_OR_COMPLETE` | PARTIAL: m28 extension excluded; consumer endpoint caveat |
| `FULL_REPEAT_PLAYBACK_VERIFIED_OR_UNRESOLVED` | UNRESOLVED |
| `SOURCE_COMPLETENESS_VERIFIED_OR_UNVERIFIED` | UNVERIFIED |
| `PERFORMANCE_READY_FALSE` | TRUE |

**Source recognition completeness:** UNVERIFIED. Owner-approved recognized fields are accounted for, but independent omission/completeness assessment remains absent. **Rendering completeness:** complete for the declared approved recognized music/text and 50 visible-mark inventory; not a complete reconstruction claim for every source pixel/object. **Visual quality:** acceptable for experimental review with the optical limitations above. Semantic consistency, numerical layout safety and agent inspection are separate gates.

This release closes GT17 implementation and evidence consolidation without inventing m28 ancestry or performance traversal. It does not finish production V4/B2, original-ink removal, lyric-pixel preservation, independent musician review, or general real-score validation. Source credits and unapproved page text outside the declared musical layer are not a certified complete transcription.

Next practical action is one consolidated musician review of these final experimental pages, with focused decisions about m15–17 playback and m28 ancestry, followed by a separate independent source-completeness and optical assessment. Native XML consumer endpoint loss must remain visible unless that consumer/export behavior is separately repaired and retested. No further GT17 rendering expansion or automatic approval promotion is authorized by this release.
