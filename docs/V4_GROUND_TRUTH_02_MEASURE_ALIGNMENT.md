# GT-02: printed-measure alignment and recognition coverage

**Decision: READY_FOR_INDEPENDENT_REFERENCE_COLLECTION.** This means native review materials and a raster-supported coordinator registration are ready for independent readers. It does **not** mean accepted ground truth, musical accuracy certification, architecture superiority, ownership approval or renderer authorization. Independent human labels collected: **0**.

**Coordinator-only report. Do not distribute this report, the private index, OMR/prediction outputs or the parent diagnostic directory to annotators.** Give readers only the native `independent-reference-packet/` and their separate working form.

## Identity, isolation and provenance

GT-02 is **post-reference-access development**, not a new blinded experiment. Worktree `/private/tmp/capomatic-v4-ground-truth-02`, branch `experiment/v4-ground-truth-02`, starting SHA **`bf5903bba4a00326288c40237a7c84ff9e32183c`**. GT-01 prediction revision remains **`9444b14e108b573f124b7ed6a14207d779aeed7c`**; no predictions or historical files were rewritten.

| Identity | Supplied PDF page | Key / requested interval | Raster SHA-256 |
| --- | ---: | --- | --- |
| Original Bb | **2** | Bb major | `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de` |
| Reference A | **1** | A major / −1 | `b094035763fc02685edcb1a57960833cc95b52e95034fb6cbaaba2c929e7fa67` |
| Reference G | **3** | G major / −3 | `2d5cae7034a78e06d62975e92dc2f9666311fb0a06659dfe49cb2fdfd8e739bc` |

Original PDF SHA-256 **`1cc64756c0ce47b1db0ea6ac21eefe4685097a04cd4589f954afc712afb605fd`**. GT-01 baseline manifest SHA-256 **`68f327663cf91011f62b16db770cba4e06aea1323d0b06bade1cbfe2c904ad49`**; its public-key fingerprint and signature, the signed final GT-01 manifest, 39 prediction files, all reference artifacts and original PDF were checked before analysis and rechecked after it. The diagnostic rejects a different baseline/key, changed source raster, wrong GT-01 final revision or changed reference hashes. The local coordinator signature proves binding to a retained key; it does not authenticate an independent human or trusted timestamp.

**Provenance correction:** the original PNGs are actually **RGB encoding with R=G=B at every pixel**, 2520×3564. GT-01's `L` storage-mode statement conflated `pdftoppm -gray` content with the PNG encoding. GT-02 uses a lossless identical-channel array view only; no source conversion, rescaling or replacement occurred. GT-01's byte-bound images and predictions remain exactly as run. The historical report/protocol were not silently edited.

## 1. Printed registration independent of OMR indices

The staff/bar proposal stage reads only source raster pixels, not Audiveris measure numbers. It finds long horizontal staff support, five-line systems and tall vertical candidates. Fixed diagnostic parameters: dark `<127`, horizontal support `>0.65×page width`, five-line cluster gap 60 px, vertical coverage ≥0.90 after excluding ±3 px staff rows, compound-column gap ≤0.75 interline, and a ten-interline system-header exclusion. The full policy is serialized in `measure-registration.json`.

These thresholds generate **review proposals only**, never source ink ownership or editing permission. Full-height stems can resemble barlines: the finalized scalar analysis found four such candidates (Bb systems 3/4/5, A system 3). Native crops show attached noteheads/beams; they were explicitly rejected as stems. An earlier exploratory three-channel projection also examined a Bb system-6 stem; that initial draft is archived. No threshold was adjusted to favor musical agreement. Every retained boundary has an explicit coordinator confirmation; extra/unreviewed confirmations fail closed.

All three native images were inspected with coordinator overlays. The proposal counts agree with the independently visible system-start numbers **1,5,9,13,17,20,25,30,34** and system measure counts **[4,4,4,4,3,5,5,4,4]**, total **37** each. This corroborates the prior hypothesis through raster evidence plus coordinator reading; it is still **not certified human ground truth**. The 111 records include page, system, printed identity, physical boundary stroke bands/centers, staff coordinates, repeat context, cross-page regions, confidence and pending independent verification.

Coordinates use original pixel units, x right/y down. An initial boundary is the original staff's left context edge, including clef/key/header, not an invented left barline. Internal boundaries use detected stroke bands; compound repeat bars retain their full uncertainty span. No playback unfolding is performed. The visible ending-1 bracket at printed 16 has **no backward-repeat dots visible** before ending 2 at 17 on any page; performance interpretation remains for human review. It does not create/delete a printed measure.

The tables below are coordinator registration data, not annotator answers. Exact stroke ranges and per-page repeat/context uncertainty are in the untracked JSON.

| Printed measure | System | Bb left–right px | A left–right px | G left–right px | Literal context |
| ---: | ---: | --- | --- | --- | --- |
| 1 | 1 | 160.00–760.00 | 160.00–780.00 | 160.00–745.50 | Forward repeat visible at system entry |
| 2 | 1 | 760.00–1374.00 | 780.00–1388.00 | 745.50–1366.00 | — |
| 3 | 1 | 1374.00–1782.00 | 1388.00–1788.50 | 1366.00–1778.00 | — |
| 4 | 1 | 1782.00–2400.00 | 1788.50–2400.00 | 1778.00–2400.00 | — |
| 5 | 2 | 160.00–638.00 | 160.00–661.00 | 160.00–623.50 | — |
| 6 | 2 | 638.00–1598.00 | 661.00–1608.00 | 623.50–1591.50 | — |
| 7 | 2 | 1598.00–1961.00 | 1608.00–1966.00 | 1591.50–1957.00 | — |
| 8 | 2 | 1961.00–2400.00 | 1966.00–2400.00 | 1957.00–2400.00 | Ending 1 and backward repeat at right |
| 9 | 3 | 160.00–806.00 | 160.00–827.00 | 160.00–793.00 | Ending 2 bracket |
| 10 | 3 | 806.00–1338.00 | 827.00–1351.00 | 793.00–1328.00 | — |
| 11 | 3 | 1338.00–1868.00 | 1351.00–1875.00 | 1328.00–1864.00 | — |
| 12 | 3 | 1868.00–2400.00 | 1875.00–2400.00 | 1864.00–2400.00 | — |
| 13 | 4 | 160.00–851.00 | 160.00–870.50 | 160.00–838.00 | — |
| 14 | 4 | 851.00–1427.00 | 870.50–1439.50 | 838.00–1419.00 | — |
| 15 | 4 | 1427.00–2093.00 | 1439.50–2096.00 | 1419.00–2090.00 | Ending 1 bracket begins |
| 16 | 4 | 2093.00–2400.00 | 2096.00–2400.00 | 2090.00–2400.00 | Ending 1 continues; no backward repeat dots visible at system right; performance interpretation UNKNOWN |
| 17 | 5 | 160.00–1360.00 | 160.00–1374.00 | 160.00–1352.00 | Ending 2 bracket |
| 18 | 5 | 1360.00–1851.00 | 1374.00–1858.00 | 1352.00–1846.50 | — |
| 19 | 5 | 1851.00–2400.00 | 1858.00–2400.00 | 1846.50–2400.00 | — |
| 20 | 6 | 160.00–649.00 | 160.00–670.00 | 160.00–636.00 | Forward repeat visible at system entry |
| 21 | 6 | 649.00–1237.50 | 670.00–1253.00 | 636.00–1227.00 | — |
| 22 | 6 | 1237.50–1605.00 | 1253.00–1614.00 | 1227.00–1599.50 | — |
| 23 | 6 | 1605.00–2194.00 | 1614.00–2197.00 | 1599.50–2191.00 | — |
| 24 | 6 | 2194.00–2400.00 | 2197.00–2400.00 | 2191.00–2400.00 | — |
| 25 | 7 | 160.00–1011.00 | 160.00–1029.00 | 160.00–1000.00 | — |
| 26 | 7 | 1011.00–1417.00 | 1029.00–1429.00 | 1000.00–1409.00 | Ending 1 bracket begins |
| 27 | 7 | 1417.00–1808.75 | 1429.00–1816.73 | 1409.00–1803.73 | Ending 1 continues; backward repeat at right |
| 28 | 7 | 1808.75–2097.50 | 1816.73–2101.00 | 1803.73–2094.50 | Ending 2 bracket |
| 29 | 7 | 2097.50–2400.00 | 2101.00–2400.00 | 2094.50–2400.00 | — |
| 30 | 8 | 160.00–766.50 | 160.00–787.00 | 160.00–752.00 | Forward repeat visible at system entry |
| 31 | 8 | 766.50–1358.00 | 787.00–1371.50 | 752.00–1349.00 | — |
| 32 | 8 | 1358.00–1808.00 | 1371.50–1815.50 | 1349.00–1803.00 | — |
| 33 | 8 | 1808.00–2400.00 | 1815.50–2400.00 | 1803.00–2400.00 | — |
| 34 | 9 | 160.00–716.00 | 160.00–737.00 | 160.00–701.00 | — |
| 35 | 9 | 716.00–1632.00 | 737.00–1642.00 | 701.00–1626.00 | — |
| 36 | 9 | 1632.00–1979.00 | 1642.00–1984.00 | 1626.00–1976.00 | — |
| 37 | 9 | 1979.00–2400.00 | 1984.00–2400.00 | 1976.00–2400.00 | Backward repeat at right |

| System | Staff support band-center y coordinates (all three pages), px |
| ---: | --- |
| 1 | 444.50, 462.50, 480.50, 498.50, 516.50 |
| 2 | 794.50, 812.50, 830.50, 848.50, 866.50 |
| 3 | 1145.00, 1163.00, 1181.00, 1199.00, 1217.00 |
| 4 | 1495.00, 1513.00, 1531.00, 1549.00, 1567.00 |
| 5 | 1845.00, 1863.00, 1881.00, 1899.00, 1917.00 |
| 6 | 2195.50, 2213.50, 2231.50, 2249.50, 2267.50 |
| 7 | 2545.50, 2563.50, 2581.50, 2599.50, 2617.50 |
| 8 | 2896.00, 2914.00, 2932.00, 2950.00, 2968.00 |
| 9 | 3246.00, 3264.00, 3282.00, 3300.00, 3318.00 |

## 2. OMR segmentation: the 37 / 34 / 36 discrepancy

Within each version, native OMR measure/stack geometry is compared with registered physical boundaries and staff support. OMR IDs are used only to trace that version's artifacts, **not** to align versions by equal numbers. A fixed quarter-interline boundary tolerance accounts for measured stroke/graph edge conventions; it is not pitch matching or ownership admission.

| Version | OMR stacks | One-region MATCHED stacks | Merged PARTIAL stacks | Printed-region mapping |
| --- | ---: | ---: | ---: | --- |
| Bb | 37 | 37 | 0 | 37 MATCHED |
| A | 34 | 31 | 3 | 31 MATCHED, 6 PARTIAL |
| G | 36 | 35 | 1 | 35 MATCHED, 2 PARTIAL |

There are no unlocated printed regions in this coordinator registration; all 111 have physical regions. Thirty printed identities have a separate one-to-one OMR stack in **all three** versions. A merged span is PARTIAL, never silently promoted. Every partial mapping retains native stack/measure XML, geometry, raster-boundary witnesses and reasons in `omr-segmentation-differences.json`.

| Version / OMR ID | Actual printed span | Internal boundary | Persisted evidence / explanation |
| --- | --- | ---: | --- |
| A / 5 | 5–6 | x=661 | Barline 18 and staff-barline 4730 exist. The OMR measure explicitly stores this as **mid-barline**, not a stack boundary; printed 5's whole A3 has no head Inter/exported event. Why Audiveris chose that representation is not proven from persistence alone. |
| A / 24 | 25–26 | x=1029 | Printed barline visible, no nearby persisted barline/staff-barline boundary. Tie/bar junction is instead associated with half-note F#4 head candidate 2398; stack duration 10 quarters. |
| A / 33 | 35–36 | x=1642 | Same missing boundary / tie-junction pattern, F#4 head candidate 2554, duration 10 quarters. |
| G / 26 | 26–27 | x=1409 | Same pattern, F#4 candidate 2124, duration 10 quarters. |

These are **recognition/segmentation differences**, not missing measures in the supplied artwork or repeat unfolding. The three junction candidates have bboxes crossing real barlines. Coordinator crops show tie/bar junction ink, but they remain **AMBIGUOUS**, not corrected/deleted notes. A printed-5 crop visibly contains whole A3; the corresponding OMR has no head and attributes a nearby ledger-region stroke to lyric-line/item. This explains a specific omission candidate, not every recognition decision in Audiveris.

The count hypothesis is coherent: A's 134 recognized heads versus Bb's 133 is compatible with one missing whole-head candidate plus two junction candidates; G's 134 is compatible with one junction candidate. Arithmetic does not certify the remaining recognized notes or establish a true full-score count.

## 3. Structure-aware event correspondence

Existing strict V4 semantic↔head matching/provenance is reused unchanged. A matched head must fall wholly inside one registered physical bar region and have one identifiable staff. Bboxes crossing boundary stroke uncertainty are AMBIGUOUS. Rests require an explicit rest-chord containment plus non-suspicious BEGIN slot/onset, or serialized measure-rest lineage; no proximity fallback.

XML offsets/durations/voices remain original. For this 4/4, single exported-stream study, an onset origin is usable only if the region's explicitly located recognized notes/rests form a contiguous four-quarter tile with no gaps, overlaps, unsupported chord continuations or voice ambiguity. Local offsets are **diagnostic fields**, not rewritten MusicXML. A merged region may rebase an otherwise complete tile from its original raw onset; the proof and origin remain recorded. No missing note/rest is filled in.

Any ambiguous boundary event blocks timing comparison for **both neighboring printed regions**. Earlier development witnesses that did not propagate this uncertainty are archived; final counts below use the stricter rule. A prefix of plausible notes is not used to authorize the rest of a questionable measure.

| Event physical status | Bb | A | G |
| --- | ---: | ---: | ---: |
| MATCHED note/rest events | 169 | 168 | 169 |
| AMBIGUOUS junction events | 0 | 2 | 1 |
| UNMATCHED recognized event geometry | 0 | 0 | 0 |

An unrecognized printed note, such as A's whole note at 5, is absent from the event stream, so the last row cannot measure missing printed ink. Exported voices are unspecified (`None`) in these streams; this is not independent verification of musical voice identity. General polyphonic/chord or non-4/4 retiming is unsupported and fails closed.

| Comparison | Unique pitched-note candidates | Requested interval agreements | Frozen prediction spelling agreements | Paired rests | Unpaired pitched left / right |
| --- | ---: | ---: | ---: | ---: | --- |
| Bb→A, −1 | 112 | 112 | 112 | 32 | 21 / 22 |
| Bb→G, −3 | 129 | 129 | 129 | 35 | 4 / 5 |
| A→G, −2 | 111 | 111 | N/A, no A-derived frozen prediction | 31 | 23 / 23 |

Pair selection uses registered physical identity, explicit lineage, onset/duration, staff/voice and structural membership. **Pitch is checked after pairing**, never used to choose a partner. Duplicate identities are not resolved by pitch/grade/nearest neighbor. The equality of interval counts is candidate agreement, **not a whole-score accuracy percentage**.

Pitch-independent whole-measure rhythm signatures separately compare notes/rests, onset, duration and voice:

- Bb/A: 32 comparable signatures agree; 4 AMBIGUOUS neighboring regions (25/26/35/36); printed 5 UNMATCHED in recognized events.
- Bb/G: 35 agree; 26/27 AMBIGUOUS.
- A/G: 31 agree; 25/26/27/35/36 AMBIGUOUS; 5 UNMATCHED.

Durationally different but individually valid four-beat signatures would report PARTIAL; they are not forced to agree. Formal independent musical denominator remains **0**. The old GT-01 full guards remain PASS for the frozen recognized-source transformations; no new full-score product is generated or guard waived here.

## 4. Full Bb harmony coverage: AUDIVERIS_ONLY

All nine Bb chord strips were reviewed, without reading A/G chord names to repair Bb. The coordinator finds **24 printed chord candidates**; **7** match exported harmonies, **17** are missing, **0** have multiple competing exported harmony candidates in this inventory. Confidence is coordinator reading only; independent transcription remains pending.

| Printed measure | Coordinator source reading | Exported harmony |
| ---: | --- | --- |
| 1 | Bb | MISSING |
| 3 | F | MISSING |
| 5 | Gm | MISSING |
| 6 | Bb/D | MATCHED |
| 7 | Eb | MISSING |
| 10 | Eb | MISSING |
| 12 | F | MISSING |
| 14 | Gm7 | MATCHED |
| 15 | Bb/D | MISSING |
| 16 | Eb | MISSING |
| 17 | Bb/D | MISSING |
| 18 | Eb | MATCHED |
| 20 | Bb | MISSING |
| 22 | F | MISSING |
| 24 | Gm7 | MISSING |
| 25 | Bb/D | MATCHED |
| 26 | Eb | MISSING |
| 27 | F | MISSING |
| 28 | Eb | MISSING |
| 30 | Bb | MATCHED |
| 32 | F | MISSING |
| 34 | Gm | MISSING |
| 35 | Bb/D | MATCHED |
| 36 | Eb | MATCHED |

Observed quality/bass coverage: simple majors **3/15**, slash majors **3/5**, minor triads **0/2**, minor sevenths **1/2**. All seven exported candidates agree with the coordinator's literal root/quality/extensions/bass reading. These are diagnostic coverage counts, not accepted accuracy rates. No altered-extension test denominator is established by this sheet.

There are **8 chord-name Inters but only 7 raw Audiveris XML harmonies**. Raw MXL → pre-ledger → post-ledger all have the same seven harmonies, so these omissions precede transposition and are not a serialization loss in the frozen V3 transformation.

Useful persisted distinctions:

- Printed 16 Eb is a typed chord-name child of sentence 4236, role **EndingText**, linked by `ending-sentence`; it has no head-chord `chord-name` relation. Raw MusicXML puts **Eb inside the first ending text**, not harmony.
- Printed 15/17 Bb/D survive as words in **Direction** sentences, exported as `1. Bb/D` / `2. Bb/D`. The unchanged V3 cleanup's chord-like prefix check does not turn those numbered strings into harmonies; its conversion count is zero.
- Printed 28 Eb is a word under **EndingNumber**; printed 26 is misread **Eh** under EndingText and appears in raw ending text `I. Eh`.
- Opening Bb is misread **Bl:** under UnknownRole; printed 20 Bb is read as Korean **마** under UnknownRole. These are text confusions, not proof they were typed as LyricItems. No Bb chord candidate has overlapping persisted lyric-item attribution in this local inventory.
- Other missing candidates have neither typed chord-name nor exported harmony evidence. Exact word/parent/relation XML is retained per candidate; absence of an Inter does not identify the precise builder failure.

The known opening Bb/F omissions are only **two of seventeen**. No source harmony was inserted, corrected or copied from reference text.

## 5. EXISTING_V3_CHORD_PATH: preregistered, unavailable

Separate preregistration commit **`2f2dfab9a588a8ba9ee81160a9bdde69d44500a8`**, [protocol](V4_GT02_CHORD_PATH_PREREGISTRATION.json), before preflight. Planned method: Bb raster only; existing `detect_chords_hybrid(..., use_ai_fallback=False)` → existing V3 alignment/merge/replace call order; unchanged production defaults and all full guards; no parameter search, external AI, downloads or new dependencies.

Offline preflight of existing image `sha256:fb3c1ff7f6428a499b18aae5dc0b71a5c8b03ee709b10ab82e3ab1f28e332b1e`: paddlepaddle **3.2.2**, paddleocr **3.7.0**, paddlex **3.7.2**, detector default **v6-medium**. Known default image cache roots (`/root/.paddlex`, `/root/.paddleocr`, `/root/.cache/huggingface`, `/app/.paddlex`) are absent; no approved required model weights found there. No alternate approved model binding was supplied.

**BLOCKED_MISSING_APPROVED_CACHED_MODELS; OCR calls 0.** This subtask stopped before model initialization or score recognition. Preflight had network disabled and no score mounted. No install/download or external service was used. There is no augmented MusicXML, measured improvement or new guard result to report; guards for a nonexistent OCR product are **NOT_RUN**, not PASS. AUDIVERIS_ONLY and EXISTING_V3_CHORD_PATH remain separate. A future run requires an explicitly approved/cache-bound model environment and a new preregistration; it must not overwrite GT-01.

## 6. Independent reference packet and denominator preparation

Untracked `ground-truth-02-output/independent-reference-packet/`: **111 native focus crops**, **27 native system contexts**, **3 original page PNG copies**, `cases.json`, neutral instructions and blank A/B forms: **145 files**. Every crop was checked against exact source pixels/mode; full pages are byte copies. Source-only here means **supplied image pixels only**, including all three versions, not only Bb.

Cases use deterministic opaque IDs and opaque page/system filenames. Forms contain **no printed identities, note/chord answers, expected matches, corrections, intervals, OMR, predictions, or algorithm classifications**. They ask readers to supply their own printed measure/system identity, boundary corrections, notes/rests, exact quarterLength durations/onsets, voices, written pitch/accidental spelling, literal chord/quality/alterations/slash bass, ties/slurs, endings, lyrics and uncertainty. UNKNOWN/PARTIAL/UNREADABLE and null unknown fields are explicit. A source crop hypothesis can be corrected using its full system/page context; an apparently neat crop is not proof of a measure.

The private case→coordinator-region linkage and file hashes stay **outside** the packet. Packet verification rejects changed/missing/added files and symlinks. Each A/B draft binds the exact cases-file SHA-256, which binds the native focus files and page hashes. Initial draft packets and development witnesses are archived, undistributed. Use only the final packet.

Collection procedure, still unexecuted:

1. Custodian externally verifies two music-literate readers uninvolved in GT-01/GT-02, recognition, architecture/planning or coordinator analysis. Record identity/expertise and exclusions: no prior predictions/OMR/coordinator answers, no other reader's submissions. Freeze separate training page hashes; all three evaluation pages are excluded from training. Blank forms do not count as labels.
2. Give A and B separate native packets and writable copies of their own form. They transcribe independently from ink, not by mentally copying/transposing another version. Record uncertainty rather than infer missing notes. Do not let readers browse the repository/coordinator directory.
3. Receive separately signed/timestamped exports. Validate schema, case SHA, fixed case order, exact rational timing and independence metadata with `validate_submission`; it returns **SCHEMA_VALID_NOT_ACCEPTED_GROUND_TRUTH**, not a truth certificate. Actual identity and disclosure cannot be verified by JSON.
4. Custodian hashes and freezes each original export separately, retains receipts through a separately controlled channel and records access/exposure. Neither primary is shown the other until **both** freezes. Never silently replace a primary. Local files do not enforce person-level privacy/authentication.
5. An eligible third reader, distinct from both primaries, adjudicates disagreements from native images plus the two frozen observations only. Bind adjudication to both hashes; retain primaries and unresolved alternatives. No predictions, OMR or coordinator answers are used for adjudication.

Only then can accepted denominators be defined for independently confirmed printed measures, notes/rests/voices, chord categories and ties/curves. The 111 candidate regions and 24 coordinator harmony readings are **preparation coverage**, not accepted denominators. Full musical accuracy must include missing/added events and unresolved correspondence explicitly; it cannot be computed only over the favorable paired subset. Actual independent submissions: **0**.

## 7. Architecture implications without a winner

**Track A:** existing source evidence remains 0 COMPLETE / 71 PARTIAL / 2 REJECTED atomic groups; 0/327 candidate symbols COMPLETE. Frozen mask approval remains **0/133 notes, 0/32 beams**. Unknown staff-crossing pixels 25,535; source-core evidence, continuation/antialias/attachment blockers and COMPLETE-only rules are unchanged. Printed registration and PARTIAL diagnostic mapping grant **no pixel ownership or edit permission**. No Phase 1.10.

**Track B:** 37 raster-supported physical measure candidates per page permit width registration without exported OMR indices. All 45 detected staff-band center coordinates agree between pages. Source-minus-reference width maximum absolute deviation is **23 px A**, **15 px G**; width-sum mean zero follows equal page/system extent and is not an accuracy result. Different key signatures/engraving can legitimately change spacing.

Using only frozen source-derived absolute targets and the strictly paired notes, detector residuals are:

| Candidate geometry | A (112 pairs) | G (129 pairs) |
| --- | --- | --- |
| Source-locked target x minus reference detected x, median / max absolute | −14.5 / 26.5 px | +10 / 18 px |
| Absolute target staff y minus reference detected y, median / max absolute | +0.00625 / 0.962584 px | +0.03125 / 0.948279 px |

These replace neither physical human annotations nor musical accuracy. The old enormous A residuals came from unsafe exported-index candidates; no frozen target coordinate was tuned. Geometry distinguishes observed head center, source/target semantic staff coordinate and **UNDEFINED replacement engraving anchor**. No replacement anchor is inferred from the detected center. Source ledger repairs were zero, so the earlier repaired-ledger anchor problem is still untested here. Beam/curve/attachment/font/chord-width reconstruction and full occupancy remain unverified; no B2/rendering.

Missing chords, merged bars and tie-junction head candidates affect **both** architectures' recognition inputs. They are not evidence that one architecture is superior. Independent physical annotation and equivalent renderer maturity are still needed before comparing output quality.

## Artifacts, validation and next step

Required artifacts are under the untracked `ground-truth-02-output/`: `measure-registration.json`, `omr-segmentation-differences.json`, `source-chord-coverage.json`, `note-correspondence-diagnostic.json`, `independent-reference-packet/`, `validation-summary.json`. Additional private witnesses include native coordinator overlays/crops, observation JSON, raw direction/ending provenance, Paddle preflight, architecture metrics, private index and archived development outputs. No copyrighted page is committed or uploaded.

Committed tools are under `scripts/research/ground_truth_02.py`, `gt02_reference_packet.py`, `gt02_architecture_metrics.py`. Reproduction needs the hash-bound local GT-01 artifacts **and coordinator observation input**, not only this Git checkout. Use new GT-02 output directories; no Audiveris rerun or prediction regeneration is needed:

```sh
python -m scripts.research.ground_truth_02 \
  --gt01 /private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output \
  --observations /path/to/retained/coordinator-observations.json --out /new/study
python -m scripts.research.gt02_reference_packet \
  --gt01 /private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output \
  --registration /new/study/measure-registration.json \
  --out /new/study/independent-reference-packet --private-index /new/study/private-index.json
python -m scripts.research.gt02_architecture_metrics \
  --gt01 /private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output --study /new/study
```

Targeted research + V4 + frozen V3 music/gate regressions: **325 passed, 1 skipped** (existing external MuseScore dependency). Controls cover original RGB preservation, explicit bar confirmation, stem rejection, barline ambiguity, merged stacks, typed rest lineage, unsupported/gapped timing, ambiguity propagation, wrong-pitch and changed-rhythm controls, duplicate ownership refusal, source/hash/signature identity boundaries, native packet crops, answer injection rejection, submission binding and independence exclusions. No Audiveris execution is required by tests. `git diff --check` passed; no Full Acceptance.

**Next action:** recruit eligible independent readers, freeze training/exclusions and collect both full-page/measure transcripts separately, then adjudicate the missing A whole note, three junction candidates, 17 Bb harmony omissions and repeat context. The independent packet is ready; the accepted reference denominator is not. Optional future Paddle execution needs approved cached model provenance before a new source-only run.

No historical GT-01 files/branches, production V1/V3 behavior, V4 ownership/acceptance/integrity gates, flags, API/frontend routes or source rasters changed. No PARTIAL promotion, source editing, renderer/B2, merge or deployment.
