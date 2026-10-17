# V3 acceptance

Overall verdict: **OPEN — not a final candidate or a public release**.

This revision strengthens chord-only coverage validation. It is based on `2152e8dc571927a9b7d0cf7606ef9e7a5f9279b0`; previous CI and evaluation numbers do not establish results for this revision. Feature flags remain off by default. V1 chord parsing, transposition and rendering remain authoritative and unchanged.

| Acceptance item | Status | Current revision evidence |
|---|---|---|
| Targeted gate, router and multi-page tests | PASS | 79 passed, 1 skipped locally |
| Backend regression suite | PASS | 763 passed, 12 skipped locally; new CI pending |
| Frontend tests, typecheck, production build | OPEN | Not rerun in this backend-only change; new CI pending |
| Docker build and real V1 `/detect` | OPEN | New CI pending |
| Full-score reliability | OPEN | New completed-run measurement pending |
| Chord-only confidence gate | OPEN | Local regression cases pass; real accepted/rejected outcomes and recall remain pending |
| Transposition integrity | PASS | Local targeted tests cover suffixes, slash bass, offsets and keys; real evaluation pending |
| Multi-page PDF | PASS | Local Poppler integration tests preserve ordering and partial failures; real OMR pending |
| Public readiness | OPEN | Independent real blind evaluation remains required |
| Licensing/compliance | OPEN | Review required before public release |

## Reliability rationale and limits

The previous gate could accept structurally consistent omissions: a high average head grade says little about heads missing from the exported score. It also recorded low-grade heads without gating on their proportion and treated absent grades as perfect confidence. The gate now rejects missing geometry/confidence, more than 15% low-grade heads, or more than 5% disagreement between geometry heads and exported sounding pitches. These provisional limits are runtime evidence checks, not accuracy estimates. They can reject usable polyphonic or shared-head notation. They cannot detect every confidently wrong pitch.

Chord-only output first cross-checks full-width staff detection against six narrow strips spanning the central 80% of the image. Staff regions supported by at least three strips must overlap detected systems, and each detected system must have strip support. Missing regions or absent supporting evidence reject the fallback. This addresses a circular coverage decision: a full-width detector can miss most systems on a distorted page, leaving a few high-confidence chords on its single detected system looking well distributed. The completed prior summary showed that pattern in both reported extremely sparse phone results. A local tilted-staff regression reproduces this class of failure without sample-specific seeds or runtime ground truth.

The existing per-system requirements remain: at least two valid chords at distinct locations, at least 20% page-width horizontal spread, no invalid/duplicate/unassigned detections, no confidence below 0.6, and at most 10% below 0.8. Repeated chord names at different locations are valid. A simple one-system score with two chords can pass; there is no added global chord-count floor. Coverage reports include strip-supported, uncovered and unsupported staff counts for review. Rejection retains `chord_only:insufficient_chord_coverage`, HTTP 422 and the request for a clearer PDF/image.

Strip voting is a conservative heuristic, not independent OMR or an exact recall estimate. Both views can still miss a staff; a region with no intended chords may cause unnecessary rejection. The change does not prove that no original-key chord remains. Actual outcomes and the minimum accepted chord-only recall must be measured by the next completed evaluation, rather than predicted here.

Neither 99% accuracy nor 30 seconds per page is a runtime rejection threshold.

## Document contract

PDFs accept 1–10 pages within the existing 10 MiB upload limit. Pages are split and processed sequentially, with page-local native-resolution preflight and gates. ZIPs contain the combined PDF, per-page outputs and `conversion-report.json` with document counts and ordered page details. MusicXML stays separate (`page-001-recognized.musicxml`, `page-001-transposed.musicxml`, etc.); movements, ties and layout are not combined across pages.

A rejected page has an explicit failure entry and an unmistakable failure placeholder in the combined PDF, never an untouched source page. The ZIP mode is `partial_failure`; its document summary says `complete: false`. The PDF-only endpoint returns 422 for partial failure and directs the caller to the ZIP. Integrity/service errors still fail the whole request. Single-page response filenames remain compatible.

## Pending CI closure

- Current head SHA: PENDING (record the exact SHA evaluated by the next completed run)
- CI run: PENDING
- OMR V3 evaluation: PENDING
- Returned full_score usable/unusable: PENDING
- Withheld full_score unusable/usable: PENDING
- Unsafe blind full-score: PENDING
- Chord-only accepted/rejected: PENDING
- Minimum accepted chord-only recall (offline evaluation): PENDING
- Chord-only recall/precision distribution: PENDING
- Transposition-introduced note/chord errors: PENDING
- Integrity failures: PENDING
- Real multi-page mixed-mode result: PENDING
- Existing V1 real detection regression: PENDING
- API p50/p95: PENDING
- Peak RSS (Python/tools): PENDING

Fill these fields only from completed evidence matching the evaluated SHA, cross-checking `REPORT.generated.md`, `summary.json` and API benchmark output. Do not carry prior CI numbers into these fields. GitHub Actions runs independently after push; no evaluation was rerun or monitored for this revision.

Seeds 209–212 and 73101–73104 have now influenced changes and are regression data, not fresh blind evidence. A new unseen hold-out is required before claiming blind results for this revision. Re-running the configured older seeds provides regression measurements only. Generated inputs and references must remain in the full Actions artifact with exact seeds. Synthetic hold-out shares its generator with development data and cannot replace independent real-sheet evaluation. Offline “usable” retains the report definition (pitched-note exact ≥95%); it is not a runtime gate or a musical correctness guarantee.

Full evidence stays in the `omr-v3-evidence` Actions artifact. The evidence branch receives summaries, small text outputs and at most four images with a 12 MiB bundle budget. Reproduce using `.github/workflows/omr-v3-eval.yml` and the pinned Dockerfile.

## Acceptance closure and report interpretation

Final-candidate acceptance requires zero V1 regressions, zero transposition-introduced musical errors, zero integrity regressions, and independent blind evaluation of unsafe returned scores versus unnecessary withholding. Aim for zero unsafe returns while retaining useful full-score output. If that cannot be demonstrated, keep reliability OPEN and report the tradeoff. Production additionally requires licensing/compliance approval and real blind-sheet evaluation.

Head checks apply per page. A head is an Audiveris geometry symbol; exported sounding pitches count each pitch of a music21 note or chord, excluding harmony symbols and rests. Disagreement is `abs(heads - pitches) / max(heads, pitches, 1)`. Low grade means below 0.5. Missing, invalid or nonfinite grades become zero. Missing geometry, zero heads or no recognised notes reject. Shared heads, tied/duplicate voices and percussion are not independently calibrated.

Chord duplicates mean identical bounding boxes, not repeated chord names. Zero detected staff systems reject. Staff systems missed by both full-width and strip detection can still hide missing coverage; this remains a limitation requiring independent evaluation.

An incomplete ZIP reports `"document": {"page_count": 3, "successful_pages": 2, "failed_pages": 1, "complete": false}`, `"result_mode": "partial_failure"`, and ordered `"pages"` entries numbered 1, 2, 3. Page 2 has `"mode": "failure"`, `"status": 422` and an error message; it has no MusicXML. The combined PDF retains its position with a page-numbered failure notice. If all pages fail, all positions contain failure notices and `successful_pages` is zero. A complete mixed document has `complete: true`, `failed_pages: 0`, `result_mode: "mixed"`, and per-page `full_score` or `chord_only` modes. A successful chord-only page has a PDF and PNG, with no MusicXML.
