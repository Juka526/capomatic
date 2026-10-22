# Geometry-locked score API: implementation status

Understood as: replace score reflow with automatic, source-coordinate music replacement, while preserving original lyric pixels and refusing unproved edits. A safe refusal is useful evidence, but is not a completed transposition renderer.

**The production music-replacement renderer is not implemented.** This branch implements retained source evidence, coordinate validation, diagnostic readiness and safe refusal. Every PDF/PNG/ZIP score render currently returns 422, including zero semitones. No request can silently reach MuseScore. The existing image chord-overlay routes and opt-in V3 routes remain separate.

## What is implemented

`SourceLayoutBundle` retains original document bytes and immutable page PNG/OMR/coordinate/evidence bytes. SHA-256 binds original bytes, page PNG and OMR. Cache accounting includes all retained source payloads and reports under the existing 32 MiB aggregate budget, owner binding and 30-minute expiry. Source objects do not retain temporary filenames. Multi-page bundles retain the original document once, with failed pages explicit.

The new raster path preserves RGB/grayscale image pixels at native dimensions. It rejects unverified EXIF orientation and alpha/palette conversions. PDF rasterization retains MediaBox, CropBox, TrimBox, BleedBox, ArtBox, quarter-turn rotation and unit metadata. PDF/raster affine maps have explicit inverses; image/raster and raster/output maps are identities. Non-unit PDF UserUnit, invalid page boxes, unsupported rotations and raster dimension mismatch are rejected without resizing. Exact rational extent calculation avoids a binary-float ceiling error. Poppler outputs which still differ from that contract are deliberately refused.

An OMR/raster identity is considered established only when dimensions agree, the serialized skew is exactly zero, and the saved OMR GRAY pixels equal the source raster converted to grayscale. Missing GRAY, nonzero/unknown skew or differing pixels leaves that map unverified. This verifies a coordinate plane, not note recognition or anchor placement. Unrendered measurements remain null.

Only this new raster path passes `org.audiveris.omr.text.tesseract.TesseractOCR.useOCR=false`. The option was checked against the installed Audiveris JAR. PaddleOCR chord assistance runs in its own process. Lyrics are never reconstructed by this path.

`POST /detect` with `processing=score` selects this score path for either an image or PDF; PDF/MusicXML also select it automatically. `POST /render` uses the returned detection ID, and `output_format=musicxml` selects editable export on that same route. These score detection and rejected render responses expose `semantic_ready`, `geometry_ready`, `lyric_layer_ready`, `render_ready`, per-page reasons and separate `source_ink_safety` records. The latter retain OMR object/glyph/relation identifiers without treating those identifiers or bounding boxes as authorization. Protection remains the entire page. No research approval or protected mask is imported. A failed recognition remains HTTP 422; a cached, owner-bound diagnostic ID can be used for later `/render` requests to obtain the refusal evidence. The evaluator exercises those requests, too.

Single-page MusicXML export retains the V3 transposition consistency guard and skips PDF rendering. Its `X-Capomatic-Preservation` header states that editable semantics do not guarantee source layout or lyric pixels. Multi-page editable export is refused. Raster OMR semantics remain unverified; imported MusicXML can be semantically ready when the existing single-part checks find no warnings. Neither status is a claim of independent musical correctness.

## Missing work and limits

There is no complete automatic source-ink ownership producer or validator, no verified lyric/music separation, no general event-to-OMR relationship matcher, and no connected-symbol replacement compositor. Consequently there are no verified target-note raster anchors, actual alpha-collision/attachment/duplicate/clipping measurements, or lossless rendered PDF outputs. These checks are not represented as passing. A bbox, binary mask, relation list or a zero-semitone source copy would not close these gaps.

Raster semantic readiness is deliberately false until a supported, unique event/relation mapping can be established. The current source-ink inventory is diagnostic only. Its measure identifiers may be null when Audiveris does not expose a direct measure reference; the adapter does not invent one from a bbox.

This implementation therefore does not satisfy the plan's functional music-replacement milestone. It must not be described as ready for playing from, or as demonstrated lyric/layout preservation after transposition.

## Reproduce

The branch is `feature/score-geometry-locked`, in `/private/tmp/capomatic-score-geometry`. Imported files are SHA-bound in [SCORE_API_IMPORT.json](SCORE_API_IMPORT.json); the source workspace was left unchanged. Install the repository dependencies and the existing Dockerfile's Audiveris/Poppler tools. `pypdf==6.1.1` is the only added Python dependency.

```sh
cd /private/tmp/capomatic-score-geometry
python -m pytest tests/test_source_layout.py tests/test_score_api.py tests/test_api.py tests/test_omr_v3_core.py tests/test_omr_v3_music.py tests/test_omr_v3_router.py tests/test_omr_v3_multipage.py tests/test_omr_v3_gate.py tests/test_paddle_ocr_path_selection.py tests/test_paddle_ocr_filter.py tests/test_chords_transpose.py -q
CAPOMATIC_OMR_REQUIRE_AUTH=0 CAPOMATIC_OMR_RATE_LIMIT=100/3600 PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True uvicorn backend.api.main:app --port 7861
python scripts/score_geometry_eval.py http://127.0.0.1:7861 input1.pdf input2.pdf input3.pdf input4.pdf input5.pdf --out /private/tmp/geometry-eval
```


The final regression command passed **548 tests** (one optional ccache warning). The actual evaluation made five detection and fifteen render HTTP requests; all fifteen renders were refused. Code SHA-256 values in [the evaluation evidence](evidence/SCORE_GEOMETRY_EVALUATION.json) pin the tested bytes independently of the mutable branch name.

The tested environment used the existing local `capomatic-v4-local:latest` Docker image with repository code mounted read only and `pypdf==6.1.1` installed in the container. Its image ID was `fb3c1ff7f6428a499b18aae5dc0b71a5c8b03ee709b10ab82e3ab1f28e332b1e`. To reproduce with that already available image and host model cache:

```sh
cd /private/tmp/capomatic-score-geometry
docker run --rm --name capomatic-geometry-check -p 127.0.0.1:7861:7861 \
  -v "$PWD":/code:ro -w /code \
  -v /Users/juahnkim/.paddlex:/models:ro \
  -e PADDLE_PDX_CACHE_HOME=/models -e PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
  -e CAPOMATIC_OMR_REQUIRE_AUTH=0 -e CAPOMATIC_OMR_RATE_LIMIT=100/3600 \
  --entrypoint sh capomatic-v4-local:latest \
  -c 'pip install pypdf==6.1.1 && uvicorn backend.api.main:app --host 0.0.0.0 --port 7861'
```

An explicit request sequence is:

```sh
curl -sS http://127.0.0.1:7861/detect -F 'image=@input.pdf' -F processing=score
curl -sS http://127.0.0.1:7861/render -F detection_id=RETURNED_ID -F semitones=1 -F mode=key -F output_format=pdf
```

A successful detection exposes the ID at `detection_id`. A failed recognition exposes it at `detail.detection_id` while retaining HTTP 422; request validation/authentication/service failures may have no diagnostic ID. Raster render refusals have `detail.message` and `detail.report`, including the four readiness booleans and per-page reasons. Changing the second request to `output_format=musicxml` requests editable semantics when recognition is complete; it does not bypass raster safety checks.

Authentication is disabled only for the isolated local evaluation. Normal score API authentication, rate limiting and process semaphore remain enforced. `--baseline baseline.json` verifies a pre-existing NFC-filename-to-SHA-256 map before any request. Without that map, historical input equivalence is **UNVERIFIED**, even when the files were supplied under the same names. Originals and large diagnostic images must stay outside commits.

The actual evaluation results and six separate conclusions are recorded in [SCORE_GEOMETRY_EVALUATION.md](SCORE_GEOMETRY_EVALUATION.md). An agent image inspection, where applicable, is not an independent musician review.
