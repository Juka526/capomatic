# V2-3 research preparation verification

Owner approved the plan and local AGPL license/research preparation on 2026-10-14. This report covers tested contracts/readiness code. Real engine assets, independent musician labels and the comparison are still NOT READY; no OMR result is claimed.

Implemented: explicit capo/key-change intent, original-coordinate geometry and rational musical-event contracts, strict label/Lock A-B templates, immutable upstream dependency/license register and fail-closed preparation checks. Actual asset/license byte verification is mandatory, including when a caller passes the old `strict_files=False` keyword. No API, UI, OCR, legacy overlay, model or deployment changes.

| Check | Result |
| --- | --- |
| Clean-shell `/opt/anaconda3/bin/python -m pytest tests/omr -q -p no:cacheprovider` | 246 passed; sockets blocked with a deliberate known-positive guard control. |
| T2 before/after | Scratch trees: `926dd67` 105 failures / 141 passes; `b6e0f27` 12 failures / 234 passes; `699682f` 246 passes. |
| Focused T5 controls | 28 passed: synthetic positive register/lock, leak/network detector calibration and missing/unsafe/mismatched asset/license byte negatives. |
| Upstream license pins | Ten tag/commit-pinned license URLs match their recorded hashes. Asset-byte verification remains pending for real engine dependencies. |
| Current CLI | NOT READY, exit 1, 32 missing/unresolved prerequisite problems; self-check passes with actual temporary synthetic bytes. |
| Existing unit suite | 827 passed, 11 skipped before the last strict-file change; not redundantly rerun after that narrow fix. |
| Musical quality/cost | Engines, real assets, scorer, human study, accuracy, correction time and HF cost: NOT RUN. |

Tests independently use hand-written rational/pitch/geometry cases and synthetic calibration assets; no product-generated musical truth. The draft tester-owned `SCORER_SPEC.md` is not an approved implemented scorer. A positive calibration fixture never establishes real rights, provenance or human independence.

Current gate: obtain rights-cleared real snippets, disjoint readers/correctors/raters, verified engine/runtime/font bytes and the independently reviewed scorer before research. oemer weights remain blocked. Any model/rendering comparison uses development/tuning snippets only, is exploratory, then freezes one candidate for one held-out evaluation. Product implementation follows the research decision gate; no hosted AGPL adoption is implied.

Tester: Opus 5.5, final token `c3tstk`, both markers recovered. Product at `699682f`; tests separately committed by orchestrator. Privacy policy references use main `3929ed8` despite this retained PR #51 base. No legal-page edits, hosted setup or history rewriting. Rollback removes the isolated experiment by an ordinary new commit.
