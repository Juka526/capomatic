# V3 acceptance

Overall verdict: **OPEN — not a final candidate or a public release**.

This file describes the implementation on this branch. Historical numbers in `docs/pr-assets/omr-v3/` are not evidence for this revision. Feature flags remain off by default. V1 chord parsing, transposition and rendering remain authoritative and unchanged.

| Acceptance item | Status | Current revision evidence |
|---|---|---|
| Backend regression suite | OPEN | 755 passed, 12 skipped locally; external-tool skips remain |
| Frontend tests, typecheck, production build | PASS | 49 tests passed; local `npm run check` succeeded |
| Docker build and real V1 `/detect` | OPEN | Docker unavailable locally; current-revision CI required |
| Full-score reliability | OPEN | New head/export disagreement, low-grade proportion and missing-evidence checks require fresh calibration |
| Chord-only confidence gate | PASS | Sparse, zero, duplicate, invalid and low-confidence detections reject with fixed reason and HTTP 422 |
| Transposition integrity | PASS | Regression tests cover suffixes, extensions, slash bass, offsets, removed keys and region contradictions |
| Multi-page PDF | PASS | Real Poppler splitting/combination tests with controlled conversion outcomes; mixed modes and partial failures retain page order |
| Real multi-page OMR | OPEN | Requires container run |
| Blind evaluation and performance | OPEN | Current-revision measurement pending |
| Public readiness | OPEN | Licensing/compliance review and independent real blind evaluation remain blockers |

## Reliability rationale and limits

The previous gate could accept structurally consistent omissions: a high average head grade says little about heads missing from the exported score. It also recorded low-grade heads without gating on their proportion and treated absent grades as perfect confidence. The gate now rejects missing geometry/confidence, more than 15% low-grade heads, or more than 5% disagreement between geometry heads and exported sounding pitches. These provisional limits are runtime evidence checks, not accuracy estimates. They can reject usable polyphonic or shared-head notation. They cannot detect every confidently wrong pitch.

Chord-only output requires detected staff systems, at least two distinct valid chords on every system, at least 20% page-width horizontal spread per system, no invalid/duplicate detections, no confidence below 0.6, and at most 10% below 0.8. Unknown staff coverage fails closed. Sparse but legitimate arrangements may therefore be rejected. This does not estimate exact recall or establish that no original-key chord remains. Low-confidence rejection uses `chord_only:insufficient_chord_coverage` and asks for a clearer PDF/image.

Neither 99% accuracy nor 30 seconds per page is a runtime rejection threshold.

## Document contract

PDFs accept 1–10 pages within the existing 10 MiB upload limit. Pages are split and processed sequentially, with page-local native-resolution preflight and gates. ZIPs contain the combined PDF, per-page outputs and `conversion-report.json` with document counts and ordered page details. MusicXML stays separate (`page-001-recognized.musicxml`, `page-001-transposed.musicxml`, etc.); movements, ties and layout are not combined across pages.

A rejected page has an explicit failure entry and an unmistakable failure placeholder in the combined PDF, never an untouched source page. The ZIP mode is `partial_failure`; its document summary says `complete: false`. The PDF-only endpoint returns 422 for partial failure and directs the caller to the ZIP. Integrity/service errors still fail the whole request. Single-page response filenames remain compatible.

## Required current-revision measurements

| Metric | Result |
|---|---|
| Returned full_score usable / unusable | OPEN / OPEN |
| Withheld unusable / usable (unnecessary fallback) | OPEN / OPEN |
| Unsafe blind returned full-score count | OPEN |
| Chord-only accepted / rejected for confidence | OPEN / OPEN |
| Chord-only recall / precision distribution | OPEN |
| Transposition-introduced note / chord errors | OPEN / OPEN |
| Runtime integrity failures | OPEN |
| Multi-page mixed-mode result | PASS in controlled integration tests; real OMR OPEN |
| API p50 / p95 | OPEN / OPEN |
| Peak RSS (Python / tools) | OPEN / OPEN |
| Existing V1 real detection regression | OPEN |

The next evaluation generates seeds 73101–73104 after freezing these changes. Seeds 209–212 are no longer blind because their failures informed this work. Generated inputs and references remain in the full Actions artifact, along with exact seeds. Once results influence another change, use new seeds again. Synthetic hold-out shares its generator with development data and cannot replace independent real-sheet evaluation. Offline “usable” retains the existing report definition (pitched-note exact ≥95%); it is not a musical correctness guarantee.

Full evidence stays in the `omr-v3-evidence` Actions artifact. The evidence branch receives summaries, small text outputs and at most four images with a 12 MiB bundle budget. Reproduce using `.github/workflows/omr-v3-eval.yml` and the pinned Dockerfile.

## Acceptance closure and report interpretation

Final-candidate acceptance requires zero V1 regressions, zero transposition-introduced musical errors, zero integrity regressions, and independent blind evaluation of unsafe returned scores versus unnecessary withholding. Aim for zero unsafe returns while retaining useful full-score output. If that cannot be demonstrated, keep reliability OPEN and report the tradeoff. Production additionally requires licensing/compliance approval and real blind-sheet evaluation.

Head checks apply per page. A head is an Audiveris geometry symbol; exported sounding pitches count each pitch of a music21 note or chord, excluding harmony symbols and rests. Disagreement is `abs(heads - pitches) / max(heads, pitches, 1)`. Low grade means below 0.5. Missing, invalid or nonfinite grades become zero. Missing geometry, zero heads or no recognised notes reject. Shared heads, tied/duplicate voices and percussion are not independently calibrated.

Chord duplicates mean identical bounding boxes, not repeated chord names. Zero detected staff systems reject. Missed staff systems can still hide missing coverage; this is a known limitation requiring independent evaluation.

An incomplete ZIP reports `"document": {"page_count": 3, "successful_pages": 2, "failed_pages": 1, "complete": false}`, `"result_mode": "partial_failure"`, and ordered `"pages"` entries numbered 1, 2, 3. Page 2 has `"mode": "failure"`, `"status": 422` and an error message; it has no MusicXML. The combined PDF retains its position with a page-numbered failure notice. If all pages fail, all positions contain failure notices and `successful_pages` is zero. A complete mixed document has `complete: true`, `failed_pages: 0`, `result_mode: "mixed"`, and per-page `full_score` or `chord_only` modes. A successful chord-only page has a PDF and PNG, with no MusicXML.
