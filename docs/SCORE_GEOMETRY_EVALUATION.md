# Geometry-locked API: development evaluation

Run date: 2026-10-22. This is a refusal/contract evaluation of the implemented foundation, **not a demonstration of music replacement**. Five supplied development PDFs were sent to a real Uvicorn server. Three `/detect` calls returned 200; two returned 422 with an owner-bound diagnostic ID. All fifteen `/render` calls used real detection IDs and returned diagnosed 422.

HTTP render 200 rate: **0/15**. Verified contract-passing renders: **0/15**. Diagnosed intentional render refusals: **15/15**. These three values are separate. Verified end-to-end musical success rate and music accuracy are **not calculated**. The source hashes were measured before/after and remained identical. A previous five-input hash manifest was unavailable, so historical input equivalence is **UNVERIFIED**.

The four readiness values below are semantic / geometry / lyric layer / render. `F` means false. Music recognition is UNVERIFIED for every row. None of the requests produced a PNG/PDF, so fixed-anchor displacement, target-note raster error, lyric pixel differences, alpha collisions, disconnections, duplicate symbols, clipping and output readability are **NOT MEASURED / NOT APPLICABLE**, never zero or passing.

| Input | Shift | Detect | Render | S / G / L / R | Refusal |
|---|---:|---:|---:|---|---|
| 주님 난 알고 싶어요 | +0 | 200 | 422 | F / F / F / F | Unproved OMR/lyric/ink/semantic evidence |
| 주님 난 알고 싶어요 | +1 | 200 | 422 | F / F / F / F | Unproved OMR/lyric/ink/semantic evidence |
| 주님 난 알고 싶어요 | -1 | 200 | 422 | F / F / F / F | Unproved OMR/lyric/ink/semantic evidence |
| 자유 | +0 | 422 | 422 | F / F / F / F | PDF raster size mismatch |
| 자유 | +1 | 422 | 422 | F / F / F / F | PDF raster size mismatch |
| 자유 | -1 | 422 | 422 | F / F / F / F | PDF raster size mismatch |
| 우리가 주를 더욱 사랑하고 | +0 | 200 | 422 | F / F / F / F | Unproved OMR/lyric/ink/semantic evidence |
| 우리가 주를 더욱 사랑하고 | +1 | 200 | 422 | F / F / F / F | Unproved OMR/lyric/ink/semantic evidence |
| 우리가 주를 더욱 사랑하고 | -1 | 200 | 422 | F / F / F / F | Unproved OMR/lyric/ink/semantic evidence |
| 나의 꿈, 내 소망 | +0 | 200 | 422 | F / F / F / F | Unproved OMR/lyric/ink/semantic evidence |
| 나의 꿈, 내 소망 | +1 | 200 | 422 | F / F / F / F | Unproved OMR/lyric/ink/semantic evidence |
| 나의 꿈, 내 소망 | -1 | 200 | 422 | F / F / F / F | Unproved OMR/lyric/ink/semantic evidence |
| 본향을 향해 | +0 | 422 | 422 | F / F / F / F | PDF raster size mismatch |
| 본향을 향해 | +1 | 422 | 422 | F / F / F / F | PDF raster size mismatch |
| 본향을 향해 | -1 | 422 | 422 | F / F / F / F | PDF raster size mismatch |

Full hashes, individual per-page failures, source object counts, null measurements and response hashes are in [SCORE_GEOMETRY_EVALUATION.json](evidence/SCORE_GEOMETRY_EVALUATION.json). Raw detection/response bodies and server logs are retained outside Git under `/private/tmp/capomatic-score-geometry-results/`. No original PDF, OMR, mask or large raster is tracked. There are no before/after output images or output readability passes because no output was produced. Agent visual inspection and independent musician validation were therefore not performed.

## Six separate conclusions

1. **Implementation completeness:** source retention, coordinate validation, readiness/refusal, and single-page MusicXML export are implemented. Automatic music replacement, lyric separation, a complete ownership producer, connected-symbol rendering and rendered PDF/PNG output remain unimplemented.
2. **Layout preservation accuracy:** native image pixel retention and affine contracts have regression coverage, including rotated/nonzero-origin/CropBox PDFs, decimal dimensions and mismatches. Preservation after musical transposition is not demonstrated. No fixed-anchor or target-note raster accuracy rate is available.
3. **Lyric pixel preservation accuracy:** no lyric rewriting or erasure is permitted. There is no safe isolated lyric layer or transposed output, hence no measured preservation accuracy.
4. **Music recognition accuracy:** UNVERIFIED. No independent complete musical answer set was available for these five inputs. Existing V3 self-consistency checks are not an accuracy measurement.
5. **Actual score coverage:** 3/5 completed OMR detections, 2/5 coordinate rejections; 0/15 raster renders. MusicXML export has unit/API regression coverage, not a measured production score-coverage rate.
6. **Readiness for performance:** unverified and not ready to claim. The functional rendering milestone is unfinished.

## Verification and audit limits

The final targeted regression run passed **548 tests in 48.14 seconds**, with one optional ccache warning. `git diff --check` passed. The V3 music-guard file is byte-identical to the main-workspace version. Imported files still match their source-workspace hashes. Source/GT materials were read only; no research ownership proof or owner approval was promoted to API edit authorization. Runtime tests exercised real Poppler dimensions, invalid units/rotation, OMR raster identity and skew, cache accounting, caller separation, expiry, diagnostic IDs, multi-page refusal and editable MusicXML. Full rendering-specific antialiasing, connected-ink, collision, clipping and readability acceptance tests cannot pass without the missing renderer.

`mandela` audit: using this API's own readiness flags or the V3 consistency guard to estimate musical accuracy would be circular (shared hallucination / verifier = designer). This evaluation reports HTTP behavior and missing checks only. An independent complete music reference and independent output review are required before an accuracy or end-to-end success rate can be added.

See [implementation status and reproduction commands](SCORE_GEOMETRY_LOCKED.md).
