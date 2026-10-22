# Geometry-locked renderer: implementation and evaluation

**Overall status: FUNCTIONALLY_INCOMPLETE for ordinary scanned scores.** The existing five PDFs still have **zero successful nonzero transpositions**. There are now **two validated nonzero HTTP renders on controlled, source-object PDFs**, and five explicit byte-identical original-PDF identity responses. The controlled sources are an additional supported input contract; they do not demonstrate an ordinary scan ownership or recognition system.

Worktree: `/private/tmp/capomatic-score-renderer`. Branch: `feature/score-geometry-renderer`, derived directly from `b6e38b24c14b8038912dc37f2c932bf3eb4b5177`. No production, merge, HF upload or deployment was performed. Prior workspaces and the previous evaluation documents remain unchanged.

## Demonstrated results

| Dataset / operation | Validated successful outputs | Safe refusals | Meaning |
|---|---:|---:|---|
| Five real PDFs, 0 semitones | 5/5 | 0 | Exact original PDF bytes; no music replacement |
| Five real PDFs, +1 and -1 | 0/10 | 10 | Evidence is insufficient for editing; not proof of unavoidable collisions |
| Controlled PDFs, 0 semitones | 2/2 | 0 | Pixel-identical native-source identity |
| Controlled C→B(-1), B→C(+1) | 2/2 | 0 | Actual notes and signatures replaced; PDF and PNG verified |
| Controlled C→D-flat(+1), B→B-flat(-1) | 0/2 | 2 | Flat-signature anchor support is intentionally absent |

The real-score HTTP 200 rate is 5/15, entirely identity responses. Its **nonzero render coverage remains 0/10**. Controlled mechanism validation must not be added to that denominator or presented as independent OMR accuracy.

Actual API outputs, copied without alteration from the HTTP artifacts:

- C→B: [PDF](pr-assets/geometry-renderer/C-minus1.pdf), [PNG](pr-assets/geometry-renderer/C-minus1.png), [before/after](pr-assets/geometry-renderer/C-minus1-comparison.png), [ownership/lyric/geometry report](pr-assets/geometry-renderer/C-minus1.json), [target MusicXML](pr-assets/geometry-renderer/C-minus1.musicxml), [controlled source PDF](pr-assets/geometry-renderer/C-source.pdf).
- B→C: [PDF](pr-assets/geometry-renderer/B-plus1.pdf), [PNG](pr-assets/geometry-renderer/B-plus1.png), [before/after](pr-assets/geometry-renderer/B-plus1-comparison.png), [ownership/lyric/geometry report](pr-assets/geometry-renderer/B-plus1.json), [target MusicXML](pr-assets/geometry-renderer/B-plus1.musicxml), [controlled source PDF](pr-assets/geometry-renderer/B-source.pdf).

All five original-score PDFs and their large previews remain outside Git. Raw bodies, recognition reports, generated previews and server logs are under `/private/tmp/capomatic-renderer-results/`. The final run is `evaluation-final/`. Curated results, individual blockers, source/output hashes and separately observed anchors are in [RENDERER_COMPLETION_EVALUATION.json](evidence/RENDERER_COMPLETION_EVALUATION.json). Implementation/source-preservation bindings and test results are in [RENDERER_PRESERVATION.json](evidence/RENDERER_PRESERVATION.json).

## What the original fifteen failures actually meant

The old `/render` implementation unconditionally rejected PDF/PNG/ZIP before invoking any compositor. Thus every old render had **missing implementation** as an immediate blocker. The source failures were not all the same:

| Source | Earlier detect | Actual source blockers and retained data | Other detectable issues |
|---|---:|---|---|
| 주님 난 알고 싶어요 | 200 | Source PNG and OMR retained; OMR GRAY (saved grayscale raster) absent; no verified inverse for nonzero skew; no complete ownership/lyric producer | OMR reports stems, beams, slurs, flags, rests and articulations; a bar-length warning is retained |
| 자유 | 422 | Original PDF retained but no page bundle: expected raster 2481×3507; actual 2481×3508 | Native-layer profile absent; ordinary event matching and lyric extraction not reached |
| 우리가 주를 더욱 사랑하고 | 200 | Source PNG and OMR retained; OMR GRAY absent; nonzero-skew map unverified; ownership/lyric producer absent | OMR reports connected notation and two bar-length warnings |
| 나의 꿈, 내 소망 | 200 | Source PNG and OMR retained; skew zero but GRAY absent; ownership/lyric producer absent | Existing reliability decision is `chord_only`: too many inconsistent bars; connected notation remains unsupported |
| 본향을 향해 | 422 | Original PDF retained but no page bundle: expected raster 2717×3507; actual 2717×3508 | Native-layer profile absent; semantic and lyric analysis not reached |

Both `pdftoppm` and `pdftocairo` reproduce the extra raster row on 자유 and 본향을 향해. This is a strict raster-extent-contract mismatch, not evidence of a Korean/music collision. No resizing, trimming, changed DPI or special-case acceptance was used to hide it. Nonzero raster editing still rejects these cases.

Missing OMR GRAY is **missing persisted evidence**; it does not establish that the music and lyrics overlap. The source raster is retained separately, but that alone does not certify the OMR coordinate plane or ownership. The old hardcoded lyric/semantic false values were implementation gaps, not measured unsafe separation. OMR-reported beams/flags/etc are secondary unsupported constructs in the narrow new native profile; their independent recognition correctness is unverified. Actual real-score collisions and pixel ambiguity have not been localized, so they are reported as **NOT EVALUATED**, rather than fabricated collision counts.

The blanket zero-semitone refusal was unnecessarily broad for an explicitly requested identity operation. Ordinary PDF identity now verifies the PDF metadata, returns the exact uploaded bytes and identifies its path as `lossless_original_pdf_identity` / `X-Capomatic-Identity: true`. It makes no semantic or isolated-lyric readiness claim. A malformed native-source claim cannot use this identity fallback. Nonzero ordinary rendering still preserves the original gates and reports the first encountered blocker plus all already detectable secondary blockers. For early recognition failures the render's surface blocker is missing source layout, with the original raster-size failure preserved in its secondary recognition diagnostic.

## All fifteen real HTTP attempts

The five source SHA-256 values match the previous frozen evaluation records. Source bytes remained unchanged after the run. Each row below used a real Uvicorn HTTP request, not TestClient or a substituted cached result.

| Source | Detect | Shift | Render | Validated result / root blocker |
|---|---:|---:|---:|---|
| 주님 난 알고 싶어요 | 200 | 0 | 200 | Original PDF bytes identical |
| 주님 난 알고 싶어요 | 200 | +1 | 422 | Missing verified OMR plane, complete music ownership and lyric extraction |
| 주님 난 알고 싶어요 | 200 | -1 | 422 | Same source blockers; no target edit authorized |
| 자유 | 422 | 0 | 200 | Original PDF bytes identical; diagnostic detection ID used |
| 자유 | 422 | +1 | 422 | Raster extent mismatch → missing source page evidence |
| 자유 | 422 | -1 | 422 | Same extent/evidence blocker |
| 우리가 주를 더욱 사랑하고 | 200 | 0 | 200 | Original PDF bytes identical |
| 우리가 주를 더욱 사랑하고 | 200 | +1 | 422 | Missing verified OMR plane, ownership and lyric extraction |
| 우리가 주를 더욱 사랑하고 | 200 | -1 | 422 | Same source blockers |
| 나의 꿈, 내 소망 | 200 | 0 | 200 | Original PDF bytes identical |
| 나의 꿈, 내 소망 | 200 | +1 | 422 | Missing OMR plane/ownership/lyrics; unreliable semantic recognition |
| 나의 꿈, 내 소망 | 200 | -1 | 422 | Same source blockers |
| 본향을 향해 | 422 | 0 | 200 | Original PDF bytes identical; diagnostic detection ID used |
| 본향을 향해 | 422 | +1 | 422 | Raster extent mismatch → missing source page evidence |
| 본향을 향해 | 422 | -1 | 422 | Same extent/evidence blocker |

All ten nonzero refusals are safe evidence-gate refusals. All ten lack a complete ordinary-source ownership/lyric proof; four also fail before page capture on geometry. Six have retained OMR-reported notation outside the supported native subset, and two of those have the existing unreliable-recognition decision. These are overlapping categories, not ten disjoint causes. Genuine unavoidable real-score collision count, ownership ambiguity regions and lyric separation accuracy remain unmeasured.

## Implemented source-ink and lyric contract

The new `native_pdf` adapter accepts only an explicitly self-describing PDF with `CapomaticSource` data, source MusicXML, fixed staff/event geometry and three actual PDF image layers: Staff, Music and Lyrics. The fixture generator creates this format automatically. Ordinary user scans are never retrofitted with invented layers or semantic truth. This is source-provided notation data, **not OCR recognition**.

An attached mask or role label is insufficient. Before a source becomes renderable, the adapter:

1. Bounds and parses the source profile, verifies the exact font identities and accepts only a small explicit MusicXML grammar. Unknown mandatory constructs cannot silently disappear in music21 parsing.
2. Checks one treble staff, 4/4, one diatonic whole note per measure, one key signature containing 0–7 sharps (C, G, D, A, E, B, F-sharp or C-sharp major), globally unique fixed note x slots and ordered measure boundaries. Source and target signatures must fit the original header; flat signatures are unsupported. Shorter values, rests, chords, stems, beams, flags, ties, slurs, articulations, explicit accidentals and unsupported key signatures are rejected.
3. Derives every source music alpha pixel from those semantic events, staff geometry, canonical font outlines and the fixed-phase registration algorithm. Key symbols, clef and time marks are included. Supported ledgers have explicit note relations.
4. Reads the actual source PDF image objects and compares complete alpha bytes against the canonically derived layers. Undeclared drawing commands/resources, altered coverage, predictor/encoding tricks, stray single antialias pixels and source/glyph mismatch fail closed. Decompression is bounded.
5. Rasterizes the actual PDF with the explicit native 300 dpi Cairo pixel grid. Every displayed RGB source pixel must match the verified layer composition exactly. Dimensions and boxes must agree. No resize or threshold erosion is permitted.

The lyric layer is read from the original PDF's pixels, with automatic per-row ink bounds and extender support. The native source provides Korean text/placement for verifying its source layer; it is not an OCR result. Its canonical font rendering is used only to **verify** the source pixels. Output lyrics are copied from the source RGB canvas; they are never redrawn from that text. Multiple rows and extenders remain at their original coordinates. A music/lyric or staff/lyric alpha-support overlap, clipped row or ambiguous row intersection is rejected. Outside this source-object profile, automatic Korean lyric separation from ordinary scans is still missing.

## Transposition and preservation evidence

The compositor uses the unchanged V3 MusicXML transposer (`transpose_score`) and semantic consistency checker (`music_guard`), then checks the serialized target MusicXML again. Whole-note y positions derive from written pitch relative to the original treble E4 bottom line; x slots, systems, bar lines, page dimensions and lyric coordinates remain fixed. It rebuilds supported signatures/ledgers only when they fit the original geometry. It has no MuseScore call or reflow fallback.

Source rasters, alpha objects, OMR and cached bundles are immutable. Output starts on a separate source copy. Only verified old music support is cleared. Exposed staff pixels are reconstructed from the verified source staff model; uncovered background is reconstructed separately. Neither is described as original-preserved pixels. New alpha is then composited, and the entire result must equal a fresh staff + target-music + original-lyric composition, preventing old/new double notation. Pixels outside the edit support and every original lyric-support RGB pixel are compared byte for byte.

| Measurement | C→B(-1) | B→C(+1) |
|---|---:|---:|
| Source music-owned pixels | 3,692 | 6,762 |
| Staff pixels reconstructed, not called preserved | 66 | 280 |
| Background pixels reconstructed | 3,626 | 6,482 |
| Original lyric ink pixels preserved | 5,856 | 5,856 |
| Lyric RGB pixel differences | 0 | 0 |
| Observed source-to-target note x displacement | 0 px | 0 px |
| Largest observed note x / y anchor error | 0.5 / 0 px | 0.5 / 0 px |
| Entire result vs separately generated target-source raster | 0 differing pixels | 0 differing pixels |
| Output PDF embedded RGB vs output PNG | Identical | Identical |
| Actual Cairo PDF raster vs output PNG | 0 differing pixels | 0 differing pixels |
| Page count / all page boxes | Identical | Identical |
| Old music residue / unexplained alpha collision | 0 / 0 | 0 / 0 |
| V3 in-memory / serialized semantic guards | Pass / Pass | Pass / Pass |

A separate validator consumes actual HTTP ZIP/PDF/PNG/MusicXML, compares literal expected pitches, measures note centers from output pixels, compares paired source rasters, and checks protected/removed support directly. The paired target source is generated from literal target MusicXML without calling V3 transposition, but uses the same canonical glyph renderer. It is therefore not independent engraving truth. The fixed-x metric compares observed source and output centers (0 px displacement); the 0.5 px metric compares each observed center with its nominal requested coordinate. Old residue counts cleared source-music-only pixels that are not white; unexplained collisions count target music support overlapping protected lyric support. These checks cover the narrow verified layer profile, not arbitrary flattened scans. Supplementary fixed-x measurements were rerun on the saved real HTTP artifacts; engine code and outputs were unchanged. The output PDF embeds RGB with Flate compression and interpolation disabled; PNG carries the native 300 dpi resolution. The source/object profile currently rejects rotated/cropped/nonzero-origin native pages rather than pretending output support. Ordinary byte-identity output preserves such metadata exactly when the existing PDF metadata validator accepts it.

Actual nonzero comparison images and all five actual identity PDF previews were opened and inspected by the agent. The controls are legible, with no observed double heads or clipping; original-score appearance is unchanged. This is **not independent musician validation**. Different viewer resampling policies can affect screen display; the exact pixel claims above name the tested native Cairo grid and embedded RGB data.

## Tests, preservation and reproducibility

The final targeted run passed **565 tests**, with one optional ccache warning. It includes existing score API/V3 music/legacy API/quality gates/multi-page/cache regressions and the new native-source ownership, Korean pixel, fixed-geometry, forged-provenance, one-antialias-pixel, collision, unsupported-notation and multi-page atomicity controls. Existing test assertions were not weakened or changed.

Existing V4 (research rendering) tests also passed: **12** fixed-phase anchor tests applied to the ported glyph module, and **31** selected generic header/whole-note tests using the identical-hash installed FreeSerif font. The 19 score-specific owner-confirmation controls in those two historical files were explicitly deselected because no owner/score-specific research authority is used by this implementation. Assertions were unchanged. The ported glyph function's AST is identical to its research source. The only font-design calibration reused is the FreeSerif clef anchor, not a score coordinate or A/G-only rule.

The V3 guard and previous evaluation files are byte-identical to the starting workspace. Original inputs match prior hashes. All original/GT paths were read only; no existing protection mask was shrunk. New profile data is included in the existing cache byte accounting; caller binding, 30-minute expiry and the 32 MiB aggregate budget remain enforced. Tests exercise cache caller isolation, expiration, repeated renders, preserved original bundles and a second-page failure returning no partial PDF.

The tested environment was the existing `capomatic-v4-local:latest` image (`fb3c1ff7f6428a499b18aae5dc0b71a5c8b03ee709b10ab82e3ab1f28e332b1e`), with current code mounted read only, pypdf 6.1.1 and Debian `fonts-freefont-ttf` installed. Dockerfile now includes that font package. Its FreeSerif SHA-256 is pinned and checked; unavailable/mismatched fonts cannot silently substitute another face. Model caches and the five real sources were mounted read only. Authentication was disabled only inside the isolated local evaluation, with a 100/hour test rate limit; defaults remain protected.

```sh
cd /private/tmp/capomatic-score-renderer
python -m pytest tests/test_native_geometry_render.py tests/test_source_layout.py tests/test_score_api.py tests/test_api.py tests/test_omr_v3_core.py tests/test_omr_v3_music.py tests/test_omr_v3_router.py tests/test_omr_v3_multipage.py tests/test_omr_v3_gate.py tests/test_paddle_ocr_path_selection.py tests/test_paddle_ocr_filter.py tests/test_chords_transpose.py -q
git diff --check
```

The evaluation script, profile implementation and automatic generator are respectively `scripts/renderer_completion_eval.py`, `backend/omr_v3/native_pdf.py` and `scripts/controlled_native_score.py`. The profile identifier is `capomatic-native-layers-v1`. The generator CLI creates C major; `make_fixture(5)` creates the B major paired source. The evaluator generates both without editing real source inputs.

For reproduction on this host, the pinned base image, downloaded models, five original files and the saved input-path manifest must still be available. Use a new container name and new evaluation output directory. These commands reconstruct the tested environment (they are not a claim that the modified Dockerfile image was built):

```sh
docker run -d --name capomatic-renderer-repro \
  -e CAPOMATIC_OMR_REQUIRE_AUTH=0 -e CAPOMATIC_OMR_RATE_LIMIT=100/3600 \
  -e PADDLE_PDX_CACHE_HOME=/models -e PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
  -v /private/tmp/capomatic-score-renderer:/code:ro \
  -v /Users/juahnkim/Downloads:/inputs:ro \
  -v /Users/juahnkim/.paddlex:/models:ro \
  -v /private/tmp/capomatic-renderer-results:/results \
  --entrypoint sleep sha256:fb3c1ff7f6428a499b18aae5dc0b71a5c8b03ee709b10ab82e3ab1f28e332b1e infinity
docker exec capomatic-renderer-repro apt-get update
docker exec capomatic-renderer-repro apt-get install -y fonts-freefont-ttf
docker exec capomatic-renderer-repro pip install pypdf==6.1.1
docker exec -d -w /code capomatic-renderer-repro uvicorn backend.api.main:app --host 127.0.0.1 --port 7861
docker exec -w /code capomatic-renderer-repro python -m scripts.renderer_completion_eval \
  --api http://127.0.0.1:7861 --inputs /results/inputs.json --out /results/reproduction-new
```

Wait for Uvicorn startup before the evaluator. The five-path JSON manifest remains at `/private/tmp/capomatic-renderer-results/inputs.json`; its exact paths and expected hashes are also captured in the curated evidence. The evaluator checks input hashes against the frozen previous evaluation before requests. Its output directory must not already exist. The original final run used container `capomatic-renderer-completion`, code `/code`, port **7861**, and `/results/evaluation-final`. `code_sha256` in the curated JSON identifies every tested implementation/script file; the final Git commit identifies the delivered checkout.

For the 565-test run above, execute the shown pytest command with `docker exec -w /code capomatic-renderer-repro` as its prefix. The supplementary V4 test commands used read-only copies of the historical research code/tests under container `/tmp/v4`. Import substitution directs the unchanged original assertions to the ported production glyph implementation. The second command redirects only the font path to the identical-hash installed font:

```sh
docker exec -w /code capomatic-renderer-completion python -c 'import sys; sys.path.insert(0,"/tmp/v4"); import backend.omr_v3.raster_anchor as port; sys.modules["scripts.research.gt05_raster_anchor"]=port; import pytest; raise SystemExit(pytest.main(["/tmp/v4/tests/test_v4_ground_truth_05_anchor.py","-q","-o","cache_dir=/tmp/v4-pytest-cache"])))'
docker exec -w /code capomatic-renderer-completion python -c 'import sys; from pathlib import Path; sys.path.insert(0,"/tmp/v4"); import backend.omr_v3.raster_anchor as port; sys.modules["scripts.research.gt05_raster_anchor"]=port; import scripts.research.gt11_complete_measure as spec; spec.FONT=Path("/usr/share/fonts/truetype/freefont/FreeSerif.ttf"); import pytest; raise SystemExit(pytest.main(["/tmp/v4/tests/test_v4_ground_truth_13a4.py","/tmp/v4/tests/test_v4_ground_truth_13a6_rendering.py","-k","actual_header_symbols or header_rejects or open_whole_note_independent","-q","-o","cache_dir=/tmp/v4-pytest-cache"])))'
```

The original research checkout is `/private/tmp/capomatic-v4-gt17f`; the copies include its `scripts/research`, `backend/omr_v4`, the three named test files and GT05 preregistration JSON. They are supplementary historical checks, not dependencies of the new renderer or fixture generator.

Verified source-object PDFs can also be uploaded directly from the committed controlled examples. Use `/detect` with `processing=score`, then `/render` with `mode=key`, semitones and `output_format=pdf|png|zip`. A successful native source detection is not a promise that every target key fits or is implemented. ZIP contains PDF, per-page PNG, target MusicXML and the preservation report. MusicXML-only export still states that it guarantees neither original layout nor lyric pixels. This branch is suitable for reviewing a narrow development implementation; it is not ready for general scanned-score use, merge or deployment.

## Six separate completion conclusions

| Area | Demonstrated conclusion |
|---|---|
| Implementation completeness | Partial: native-layer whole-note compositor works; ordinary raster/OMR ownership production is missing |
| Layout preservation | Controlled nonzero outputs preserve boxes, page count and observed note x anchors exactly; target center error is at most 0.5 px per axis |
| Lyric pixel preservation | Controlled nonzero outputs preserve all 5,856 identified lyric ink pixels exactly; ordinary identity responses preserve all PDF bytes; ordinary lyric separation remains unimplemented |
| Musical recognition accuracy | UNVERIFIED; V3 consistency and supplied native semantics are not independent recognition truth |
| Actual score coverage | Five real identity outputs, zero real nonzero outputs; two controlled nonzero outputs with one staff, whole notes and supported sharp signatures |
| Readiness for performance | UNVERIFIED; no independent musician review or successful ordinary-score transposition |

## Remaining limits and accuracy audit

The native source adapter proves a narrow composition mechanism. It does **not** implement a general automatic raster/OMR ownership producer, deskew inverse verification, Korean lyric extraction from flattened scans, complex rhythm or connected-symbol rendering. Those are the blockers to the five real nonzero cases. For these sources, exact-byte identities preserve all original ink; refused nonzero requests produce no edited score. No fake success responses, synthetic replacements for rejected user scores or silent partial scores were returned.

Recognition accuracy for the five real PDFs remains **UNVERIFIED**. There are development hand transcriptions for two matching input hashes, but no independently reviewed complete truth set for the current five-input evaluation. Native controls supply their semantics explicitly and are not OCR accuracy tests. The paired controls and evaluator were authored during this work, so shared-designer/verification bias remains: exact raster and semantic contracts can establish mechanism correctness in these cases, not unknown-score musical accuracy. No verified end-to-end real-score accuracy rate or readiness for performance is claimed.

The highest-value remaining engineering work is an independently checked ordinary-source object-to-ink/lyric evidence producer with complete attachment support. Until that exists and passes real nonzero HTTP evaluation, the ordinary scanned-score mission remains **FUNCTIONALLY_INCOMPLETE**, despite the successful controlled renders.
