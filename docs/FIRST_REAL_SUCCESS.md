# First real ordinary-scan transposition: FUNCTIONALLY_INCOMPLETE

Understood as: preserve `e4fb603` and demonstrate one complete existing scan through source-ink separation, fixed geometry, and independently verified nonzero PDF/PNG output. Recognition correction and new research scores are out of scope.

**No real nonzero transposition succeeded.** This change fixes typed SIG relationship capture, adds conservative RGB component evidence and immutable masks, and performs independent source-only musical readings. It does not complete shared-staff decomposition, verified Korean lyric extraction, or the ordinary-scan replacement compositor. It must not be described as a completed renderer.

Base: `e4fb603fae2edaa5ce405cb3ae955a6d659d7d4d`. Branch: `feature/ordinary-scan-first-real-success`. Checkout: `/private/tmp/capomatic-first-real-success`. Original PDFs, prior workspaces, GT research, and existing frozen evidence remain unchanged. The consolidated machine-readable results are in [FIRST_REAL_EVALUATION.json](evidence/FIRST_REAL_EVALUATION.json).

## What the implementation establishes

Audiveris stores a relationship's actual kind inside a `<relation>` wrapper. The previous inventory recorded the wrapper tag for every such edge. The adapter now preserves kinds such as `head-stem`, `beam-stem`, `slur-head`, `containment` and their diagnostic attributes. Existing direct-tag fixtures remain compatible.

The new component analyzer checks glyph run tables against BINARY, associates their source coordinates with actual decoded RGB components, and tracks music, staff and other recognized glyph support. It rejects malformed runs, missing glyphs, duplicate IDs and dangling object relations from provisional coverage. Diagnostic records bind page, system, object, glyph, available bounds, raw RGB component IDs and measure candidates. Those references are not a complete event matcher or coordinate-plane proof.

Source RGB components include **every sample different from white**. This deliberately retains JPEG/antialias fringes and watermark connections that binarization discards. A component is provisionally covered only when every source sample belongs to validated music runs, with no staff or other-glyph contact. Even then, component coverage grants **no edit authorization**: semantic matching and object-plane proof remain separate requirements. Shared music/staff components still require an unimplemented reconstruction proof.

`SourcePage` now retains immutable PNG mask bytes for component coverage, staff support, protection and unresolved contact. Coverage/protection form a checked complementary partition; the staff/contact masks are diagnostic overlays and may overlap protection. Cache accounting includes all new mask and evidence bytes under the existing owner, expiry and capacity rules. The native rendering path, identity path and MusicXML export remain separate.

Residual components below staff systems are protected candidates, **not identified Korean syllables or lyric rows**. Titles, watermark, JPEG specks and other nonmusic can be among them. No OCR, manual crop, threshold-based boundary shrink or lyric replacement is used. This is conservative protection, not completed automatic lyric-layer extraction.

## Existing inputs and candidate admission

All five original PDF hashes match the preserved development manifest. Five independent source-only full-page readings were frozen without showing OMR, implementation output or prior answers. A second blind reader transcribed the first systems of inputs 1, 2, 4 and 5. The frozen readings are preserved in [first-real-readings](evidence/first-real-readings/). They are agent readings, not musician-adjudicated ground truth; exact chord-change timing was not independently encoded.

| Existing input | Musical admission evidence | Unresolved RGB components containing music run support |
|---|---|---:|
| 주님 난 알고 싶어요 | The two source readers disagree on measure 4 tie endpoints. The first reader's mismatch with OMR is not a confirmed OMR error. | 58 |
| 자유 | Both first-system readers omit an initial C4 tie present in the exported measure 1. | 64 |
| 우리가 주를 더욱 사랑하고 | The source reader reports a whole-measure rest in measure 4. The export has multivoice timing; the review mapper refuses to flatten it. | 51 |
| 나의 꿈, 내 소망 | Both first-system readers omit a tie between the adjacent G3 sixteenths in measure 3; exported MusicXML includes it. | 26 |
| 본향을 향해 | Both first-system readers report F natural in measure 4; exported MusicXML gives F sharp. | 40 |

These are admission disagreements or unsupported mapping, not a full accuracy score. The single-read comparisons for inputs 2, 4 and 5 are consistent with the second read, but the readers can share errors. Input 1 explicitly lacks consensus. Input 3 is classified as unsupported review mapping rather than a verdict derived from flattened voices. The source-only records were never supplied to recognition or rendering.

No candidate/direction was selected: none obtained verified semantic admission. This respects the agreed choice to move to another candidate rather than expand recognition correction. Unknown total semantic-error counts, unsupported-required-notation counts and target collisions remain unknown. Object count alone did not select a winner, and no output was used to change the selection order.

The component counts above include all decoded RGB components intersecting music run support that fail the provisional coverage check; they exclude components with no music run support and are not counts of lyric collisions.

The RGB component analysis also finds no complete provisional component coverage for any of the five sources. All source pixels therefore remain protected from replacement. This is a limitation of this conservative algorithm, **not proof that the source pages are intrinsically inseparable**. JPEG components can be broad; their connection alone does not establish a genuine lyric collision. Further layer decomposition and explicit shared-staff reconstruction remain missing implementation.

## Real HTTP results and preservation limits

The final evaluation used the final runtime code hashes recorded in the manifest. It recognized each source anew and made five `/detect` requests, fifteen PDF `/render` requests at 0, +1 and −1 semitones, ten additional nonzero PNG requests, and five zero-shift MusicXML diagnostic exports.

| Result | Count |
|---|---:|
| `/detect` HTTP 200 | 5 / 5 |
| Byte-identical zero-shift original PDF | 5 / 5 |
| Nonzero PDF HTTP success | 0 / 10 |
| Nonzero PNG HTTP success | 0 / 10 |
| Nonzero PDF / PNG evidence refusals | 10 / 10 each |
| Verified nonzero preservation passes | 0 |
| Output music review passes | 0 |

The actual API first blocker remains `OMR_OBJECT_COORDINATE_PLANE_UNVERIFIED`. Secondary reasons include unverified semantic events/relations, unavailable automatic lyric separation and unavailable complete pixel ownership. Per-object regions, component contacts and decoded-source fringes are now retained alongside those gates. The ordinary-scan geometry flag remains false because the execution-bound object-plane validator is still missing; this is not a measured displacement failure.

Identity responses were compared byte-for-byte to their source PDFs. Source hashes were checked before recognition and after each render. The mask partition was checked independently from decoded mask PNGs. No source or protection mask was edited during rendering.

There is no successful nonzero output from which to measure lyric RGB difference, fixed-anchor displacement, residual old ink, target raster errors, reconstructed staff/background, double notation, clipping or genuine unavoidable collisions. These remain **UNMEASURED**, never zero. No transposed before/after comparison exists. No output qualifies as `AGENT_REVIEWED` for music or ready for performance. Musical recognition accuracy is **UNVERIFIED**, with no percentage inferred from these selected negative checks or from another dataset's approximately 70% result.

## Verification and review

The final full regression on the final runtime and test tree passed **881 tests, skipped 11**, with one optional ccache warning. It includes the dangling-relation, selected-measure, size-boundary and comparison-input guards. The 16-test targeted recheck is a subset of that full suite and is not added to its pass total. The full suite includes score API, V3 guards, native geometry, cache owner/expiry/capacity and multi-page atomic failure controls. `git diff --check` passed.

`pytest -rs` explicitly identified all skips: ten live integration cases have module-wide `TEST_TOKEN not set` marks, and one staff-system test lacks the untracked local image `fixtures/images/순간이-삶이-되어.png`. The ten include health, negative-auth and retired-endpoint cases as well as authenticated cases; those skipped cases are not claimed as tested by the local score evaluation. No credentials were invented or skip assertions changed. The initial local source-layout run lacked `music21`; the complete dependency environment subsequently ran the regression successfully.

A fresh code review found that dimensions were checked after conversion, multiple voices could be flattened, vacuous/negative-index checks could yield selected agreement, and CLI provenance was incomplete. The fixes check sizes before conversion, reject unsupported selected-measure timing/voice structures, validate explicit checks and indices, and hash source image, source reading, checks and XML. Selected agreement explicitly leaves other measures and full-page accuracy unverified.

The independence audit distinguishes producer consistency from outside evidence: glyph/BINARY matching cannot validate ownership or music; the source readers saw only original pixels, but remain model readers with possible shared bias. Expected review data is confined to offline audit tools. No expected event table, review approval or score-specific override enters runtime. Historical report/evaluation files remain frozen rather than rewritten to conceal earlier claims.

## Artifacts and reproduction

Raw results are under `/private/tmp/capomatic-first-real-results`. The authoritative final run is `verified-http` plus `verified-source-evidence`; the earlier `final-http` run and early comparison files are preliminary and excluded from success counts. `verified-http` contains all fifteen PDF responses, ten PNG refusals and five recognized MusicXML files. Source capture folders contain source PNG, OMR, coordinate evidence, ownership diagnostics and `ink-masks.zip`. Original image streams remain in the cached original PDF bytes. Large images and originals are outside git.

The manifest hashes final HTTP responses, captured data, masks, source-reading artifacts and tested runtime code. Its `source_review_comparisons` supersede preliminary flattened comparisons, especially input 3. The frozen text files retain the original readings; the admission record explicitly records reader disagreement rather than silently correcting either reader.

The exact HTTP driver is `run_final_eval.py` in the raw results directory. The input list maps `/inputs/악보` to `/Users/juahnkim/Downloads/악보`; the five exact filenames and hashes are in the manifest. The driver verifies those hashes and uses no source-reading data. It expects this implementation's current refusal behavior, not future successful transposition.

To recreate the local run, Docker, the existing local image `capomatic-v4-local:latest`, `/private/tmp/capomatic-pypdf` (pypdf 6.1.1), the host model cache and those five original inputs must remain available. This reproduces the pinned local environment; it is not a standalone environment installer. Use a new results directory:

```sh
mkdir /private/tmp/capomatic-first-real-recheck
cp /private/tmp/capomatic-first-real-results/inputs.json \
   /private/tmp/capomatic-first-real-results/run_final_eval.py \
   /private/tmp/capomatic-first-real-results/http-code-hashes.json \
   /private/tmp/capomatic-first-real-recheck/
mkdir /private/tmp/capomatic-first-real-recheck/source-review
cp /private/tmp/capomatic-first-real-results/source-review/review-*.txt \
   /private/tmp/capomatic-first-real-results/source-review/second-read.txt \
   /private/tmp/capomatic-first-real-results/source-review/checks-*.json \
   /private/tmp/capomatic-first-real-results/source-review/admission.json \
   /private/tmp/capomatic-first-real-recheck/source-review/
docker run -d --name capomatic-first-real-recheck -p 127.0.0.1:8020:8000 \
  -v /private/tmp/capomatic-first-real-success:/code:ro -w /code \
  -v /Users/juahnkim/Downloads:/inputs:ro \
  -v /Users/juahnkim/.paddlex:/models:ro \
  -v /private/tmp/capomatic-pypdf:/usr/local/lib/python3.12/site-packages/pypdf:ro \
  -v /private/tmp/capomatic-first-real-recheck:/results \
  -e CAPOMATIC_OMR_REQUIRE_AUTH=0 -e CAPOMATIC_OMR_RATE_LIMIT=200/3600 \
  -e PADDLE_PDX_CACHE_HOME=/models -e PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
  --entrypoint python capomatic-v4-local:latest \
  -m scripts.ordinary_scan_evidence_server --out /results/verified-source-evidence
curl --fail http://127.0.0.1:8020/health
```

After `/health` returns 200, run the actual HTTP driver inside the detached server container:

```sh
docker exec capomatic-first-real-recheck python /results/run_final_eval.py
```

For the offline source-reading comparison, copy the source-only images from the hash-bound captures; the text/checks remain the frozen original agent records:

```sh
cd /private/tmp/capomatic-first-real-success
python - <<'PYTHON'
from pathlib import Path
import json, shutil
root = Path('/private/tmp/capomatic-first-real-recheck')
captures = {json.loads((p/'coordinates.json').read_text())['png_sha256']: p
            for p in (root/'verified-source-evidence').iterdir()}
for index in range(1, 6):
    data = json.loads((root/'verified-http'/f'score-{index}'/'detect.json').read_text())
    sha = data['pages'][0]['source_coordinates']['png_sha256']
    shutil.copyfile(captures[sha]/'source.png', root/'source-review'/f'source-{index}.png')
PYTHON
python -m scripts.first_real_report \
  --results /private/tmp/capomatic-first-real-recheck \
  --baseline docs/evidence/ORDINARY_SCAN_EVALUATION.json \
  --out /private/tmp/capomatic-first-real-recheck/evaluation.json
```

This requires the repository's Python dependencies. The existing Dockerfile specifies the pinned external tools for rebuilding the environment. Normal API security remains enabled outside the isolated local evaluation. Existing native-control regressions are compatibility checks, not real-fixture successes. Reuse of frozen development readings does not create a hidden or newly independent evaluation set.

The ordinary-scan renderer remains incomplete. Further work requires an admissible, independently reconciled source interpretation and a source-pixel layer decomposition that can justify shared staff/background reconstruction and lyric preservation. This iteration supplies narrower evidence and clearer failure reasons; it does not establish the requested first full-score transposition.
