# Ordinary scan renderer: FUNCTIONALLY_INCOMPLETE

Understood as: implement a proof-carrying ordinary-scan transposition path in an isolated checkout; count only a complete nonzero real-score output with pixel preservation and independent musical review. Keep unsupported cases at 422.

No ordinary scan passed the first real transposition milestone. This implementation adds the source-image input path and retains useful OMR evidence, but does not implement the ordinary-scan music replacement renderer. No playing-readiness claim is made.

Base commit: `2a0398bd152e63d26ea5de02ed37a58471b11c58`. Branch: `feature/ordinary-scan-first-transposition`. Checkout: `/private/tmp/capomatic-ordinary-scan`. Existing workspaces, original PDFs and frozen evaluation files were not edited. The three historical `docs/evidence` files were compared byte-for-byte with the base commit; their hashes and the five input hashes are in [the evaluation manifest](evidence/ORDINARY_SCAN_EVALUATION.json).

## Implemented behavior

For a single-page PDF containing exactly one DeviceRGB JPEG drawn with `q cm Do Q`, recognition uses that JPEG's decoded RGB grid directly. The original PDF bytes retain the compressed stream. Evidence records the stream hash, decoded RGB hash, placement matrix, all page boxes, rotation and both directions of the image-to-PDF transform. Page clipping remains explicit and separate from the full image grid. The PNG is rebuilt from RGB samples so embedded JPEG ICC metadata cannot alter its interpretation. No crop, resize or one-pixel tolerance is used.

Extra drawing, custom clipping, annotations, masks, unverified color handling, multiple image objects or unsupported stream syntax defer to the existing conservative raster path. Malformed accepted structures raise a score error. Content expansion is bounded before PDF operation parsing. This is an input adapter; there is no replacement-image PDF writer in this change.

The source-layout Audiveris invocation keeps GRAY and continues to disable full-page text OCR. Its OMR archive retains BINARY, glyph run tables, staff models, SIG objects and relations. Source pixels are compared to GRAY using Audiveris's RGB-maximum conversion rather than Pillow luminance. The cache still owns immutable PNG/OMR/evidence bytes and accounts for their size under its existing ownership, expiry and capacity rules.

`raster_identity_ready` reports the image comparison separately. Neither a matching image nor zero/nonzero skew establishes the execution's object coordinate plane. Accordingly, ordinary-scan `geometry_ready` stays false with `OMR_OBJECT_COORDINATE_PLANE_UNVERIFIED`; no inverse is invented. The existing verified native control path remains separate.

The evaluation-only capture server saves the exact immutable `SourcePage` payloads without changing recognition decisions or adding an HTTP endpoint. The offline inventory checks each glyph's serialized foreground runs against the saved BINARY at its stored coordinates, and records object IDs and available bounding regions. A bbox is only a diagnostic region. Matching runs grant no pixel ownership, lyric separation or edit authorization. The complete source page remains protected.

## Five-score results and selection

All five source hashes match the previous development evaluation. Each was recognized anew under the same settings, with shifts 0, +1 and −1 semitone. The table follows the original input order; it is not a ranking.

| Input | Original image grid | SIG objects | Glyphs with BINARY support | Nonzero PDF / PNG |
|---|---:|---:|---:|---|
| 주님 난 알고 싶어요 | 2363 × 3342 | 960 | 1847 / 1847 | 422 / 422 in both directions |
| 자유 | 2481 × 3507 | 1295 | 2085 / 2085 | 422 / 422 in both directions |
| 우리가 주를 더욱 사랑하고 | 3780 × 3780 | 1308 | 1821 / 1821 | 422 / 422 in both directions |
| 나의 꿈, 내 소망 | 2953 × 2586 | 857 | 1578 / 1578 | 422 / 422 in both directions |
| 본향을 향해 | 2717 × 3507 | 1288 | 1880 / 1880 | 422 / 422 in both directions |

The 3507px source grids are now distinct from the former 3508px PDF rendering grids. All five GRAY images match their source samples, and all 9,211 glyph run tables have BINARY foreground support. These are recognition evidence checks, not successful rendered-output checks.

No candidate was selected. The requested lexicographic selection cannot be completed while counts of unresolved required semantics, unsupported required notation, ambiguous touching components, target collisions and replacement objects are `UNKNOWN`. Those values are explicitly unknown in the ten direction-specific selection records. Choosing the smallest object count would skip higher-priority criteria. No output was used to switch candidates.

Every nonzero request is blocked by the unverified object plane, unverified event/relation mapping and unavailable automatic lyric separation. Source-ink safety also reports unavailable complete pixel ownership. These are shared adapter/compositor gaps, not evidence that the scores contain irreducible musical ambiguity. Detected symbols include heads, stems, beams, dots, flags, ledgers, slurs and additional notation; the native whole-note contract was not applied to them.

The final real HTTP run made five `/detect` requests (all 200), fifteen PDF `/render` requests (five byte-identical zero-shift originals and ten 422 responses), and ten additional nonzero PNG requests (all 422). Nonzero HTTP success, output-preservation pass and musical-review pass are each **0**. Zero-shift responses are identity only. Source files were rehashed after every request.

## Unimplemented requirements

There is no complete MusicXML-to-SIG event matcher, execution-bound object-plane validator, music/staff/lyric ownership producer, lyric/extender separator, or general fixed-layout replacement compositor. Written-pitch placement, accidentals, stems, beams, slurs/ties, chord replacement and lossless replacement-PDF output are therefore unfinished for ordinary scans.

No target anchors, residual old ink, reconstructed staff/background, collisions, clipping or protected-pixel output differences were measured. They remain unknown, never zero. No independent source/output musical transcriptions were produced because no candidate qualified and no nonzero output exists. The result is **not AGENT_REVIEWED for music**. The separate agent review was a code review of the input adapter only; no review transcription or manual answer was supplied to runtime recognition.

## Verification and independence

The full regression run passed **862 tests**, skipped 11, and emitted one optional ccache warning. Production code did not change after that run. Two security tests and one evaluator test were then added: the final coordinate/run-table recheck passed **41 tests**, and the evaluator test passed separately. Those targeted runs cover the three tests added after the full run. The evaluator test confirms that identity HTTP successes do not count as transposition or preservation success. `git diff --check` passed.

The preliminary real-HTTP compatibility run also exercised the unchanged native controls: two identity successes, two supported nonzero successes and two unsupported 422 responses. Its PDF/PNG checks passed. These controls are development checks and are excluded from ordinary-scan success counts.

The fresh code reviewer identified unbounded content expansion and inherited ICC metadata. Both were corrected and tested. Affine finiteness/invertibility is enforced by the existing `Affine` type, and decoded image dimensions must match the prechecked PDF image dimensions. The reviewer did not evaluate music.

The independence audit finds that OMR/V3 consistency and the run-table checks reuse producer evidence. They cannot establish correct music or unique pixel ownership. The independent musical comparison remains unperformed, so recognition accuracy is `UNVERIFIED`. The five scores are development inputs, with no hidden evaluation set. The consistency audit treats earlier implementation/evaluation documents as historical snapshots; their earlier zero-skew coordinate inference is superseded here, and their bytes were preserved.

## Reproduce and artifacts

Raw artifacts are under `/private/tmp/capomatic-ordinary-scan-results`: `final-http` contains all fifteen PDF responses and ten PNG refusals; `source-evidence` contains source PNG, OMR, coordinates, ownership diagnostics and per-object pixel support. `run_eval.py` is the exact final HTTP driver. Logs, review notes, code hashes and 66 raw artifact hashes are listed in [the manifest](evidence/ORDINARY_SCAN_EVALUATION.json). No successful nonzero PDF/PNG or before/after comparison exists.

The evaluation used local image `capomatic-v4-local:latest` (`fb3c1ff7f6428a499b18aae5dc0b71a5c8b03ee709b10ab82e3ab1f28e332b1e`) with this checkout and input/model mounts read-only, pypdf 6.1.1, and authentication disabled only inside the local evaluation. The existing binaries come from the pinned Dockerfile toolchain. The inspected Audiveris source is commit `7a36078e7ba0c006052c1f661b949cf9b729f505`, including `Picture.adjustImageFormat`, `ImageUtil.maxRgbToGray`, `BinaryStep` and `RunTable.RunSequence`.

To repeat the exact evaluation on this machine with the existing local Docker image and preserved dependency copy, create a new results directory and run:

```sh
mkdir /private/tmp/capomatic-ordinary-scan-recheck
cp /private/tmp/capomatic-ordinary-scan-results/inputs.json \
   /private/tmp/capomatic-ordinary-scan-results/run_eval.py \
   /private/tmp/capomatic-ordinary-scan-recheck/
docker run -d --name capomatic-ordinary-recheck -p 127.0.0.1:8017:8000 \
  -v /private/tmp/capomatic-ordinary-scan:/code:ro -w /code \
  -v /Users/juahnkim/Downloads:/inputs:ro \
  -v /Users/juahnkim/.paddlex:/models:ro \
  -v /private/tmp/capomatic-pypdf:/usr/local/lib/python3.12/site-packages/pypdf:ro \
  -v /private/tmp/capomatic-ordinary-scan-recheck:/results \
  -e CAPOMATIC_OMR_REQUIRE_AUTH=0 -e CAPOMATIC_OMR_RATE_LIMIT=200/3600 \
  -e PADDLE_PDX_CACHE_HOME=/models -e PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
  --entrypoint python capomatic-v4-local:latest \
  -m scripts.ordinary_scan_evidence_server --out /results/source-evidence
curl --fail http://127.0.0.1:8017/health
```

After `/health` returns 200, run the evaluator and inventory (the server above runs detached):

```sh
docker exec capomatic-ordinary-recheck python /results/run_eval.py
docker exec capomatic-ordinary-recheck \
  python -m scripts.ordinary_scan_inventory /results/source-evidence
```

The preserved `inputs.json` lists the five actual paths below `/inputs/악보` in the same order as the table; the read-only `/inputs` mount maps them to `/Users/juahnkim/Downloads/악보`. The exact NFC filenames and required hashes are in each manifest `scans` entry. The final driver asserts those hashes before sending requests. Outputs go to the new results directory. Originals and large images remain outside git.

For other environments, install `requirements.txt` and the pinned Dockerfile toolchain. The reusable `scripts/score_geometry_eval.py` accepts five explicit paths and `--baseline baseline.json`, an NFC-filename-to-SHA-256 map derived from the manifest. Without a baseline it labels historical equivalence unverified. The capture server needs a new evidence directory; when run directly it stays in the foreground, so use another terminal for HTTP evaluation.

## Next implementation step

Implement an execution-bound object-plane validator using the retained GRAY/BINARY, glyph runs, staff model and the exact Audiveris build. Its acceptance criterion is a justified forward/inverse map for every required object's coordinates, with round-trip and source-support checks; dimensions or skew alone must not pass it. Keep nonzero rendering at 422 until a unique full-page event/relation matcher, ownership separation and connected-symbol compositor also pass their independent gates.
