# V3 acceptance — CLOSED

**ENGINEERING ACCEPTANCE CLOSED — PASS as a feature-flagged merge candidate; PUBLIC/PRODUCTION RELEASE HOLD.**

Engineering acceptance permits human review for a feature-flagged merge. It does not authorize public release, deployment, or enabling either feature flag. `CAPOMATIC_ENABLE_OMR_V3` and `NEXT_PUBLIC_ENABLE_SCORE_V3` remain OFF by default.

V3 algorithmic development is frozen. Future reliability, layout, OCR-semantic and selective-reconstruction improvements belong to V4 unless a true regression or release-blocking bug is found.

## Canonical evidence and scope

- Evaluated runtime SHA: `d5756433c8bb0ae18cd9aa7507340ffd478ef8f5`.
- Canonical Full Acceptance run: [39006649835](https://github.com/Juka526/capomatic/actions/runs/39006649835).
- Fresh synthetic holdout seeds: `156026599340`, `156026599341`, `156026599342`, `156026599343`.
- The acceptance artifact records the checked-out source in `source-revision.txt`; full reports, JSON, PDFs, MusicXML, images and logs belong to that run's `omr-v3-evidence` artifact.

The acceptance evidence belongs to runtime SHA `d5756433c8bb0ae18cd9aa7507340ffd478ef8f5`. Any subsequent closure commit changes documentation / CI orchestration only and does not invalidate that runtime evidence. This closure neither reruns evaluation nor tunes the completed holdout.

## Full-score gate outcomes

| Corpus | Returned usable full_score | Returned unsafe full_score | Withheld unusable | Withheld usable | Errors |
|---|---:|---:|---:|---:|---:|
| Real/dev | 6 | 0 | 2 | 0 | 0 |
| Synthetic-dev | 26 | 0 | 15 | 14 | 22 |
| Fresh synthetic-holdout | 7 | 0 | 4 | 8 | 8 |

Error counts are reported separately; do not sum the columns into a population count. Offline “usable” follows the report's pitched-note exact threshold of 95%; this is not a runtime accuracy gate or a guarantee of musical correctness.

There were **zero unsafe returned full-score cases in this completed evaluation**. The conservative gate unnecessarily withheld **8 usable fresh-holdout scores**. These observations do not establish that every real score is safe.

Fresh-holdout pooled accuracy of returned full scores:

| Metric | Result |
|---|---:|
| Pitched notes exact | 99.7% of 1050 notes |
| Pitch-only | 99.9% |
| Chord recall | 98.9% |
| Chord precision | 98.9% |

## Chord-only fallback

| Metric | Result |
|---|---:|
| Accepted | 14 |
| Rejected for insufficient coverage/confidence | 29 |
| Pooled accepted reference chords | 415 |
| Pooled drawn chords | 414 |
| Pooled recall | 98.1% |
| Pooled precision | 98.3% |
| Minimum accepted recall | 92.6% — `syn156026599343-scan` |
| Precision of that weakest-recall fallback | 96.2% |
| Real `naui` fallback recall / precision | 94.8% / 94.8% |

The `naui` full-score path was withheld at **77.8% note exact**. Chord-only fallback is not perfect: accidental and slash-bass semantic OCR errors remain possible. Structural coverage passing does **not** prove semantic chord correctness or that every printed chord was transposed.

Runtime `recall_estimate` remains `null`. Confidence and staff coverage are abstention signals, not calibrated accuracy. The recall and precision above are offline reference measurements; none enters the runtime gate.

## Error attribution

Across measured full-score paths, including broad diagnostic reconstruction:

| Error class | Count |
|---|---:|
| Recognition note errors | 624 |
| Chord recognition errors | 260 |
| Chord mapping errors | 65 |
| MuseScore/rendering note-level discrepancies | 13 |
| Transposition-introduced note errors | 0 |
| Chord transposition errors | 0 |
| Integrity failures | 0 |

The 13 MuseScore/render note-level discrepancies remain part of the evidence even though transposition-introduced errors were zero. XML transposition integrity does not imply a discrepancy-free rendered PDF.

## Multi-page, API and regression validation

The real multi-page result contained **3 pages**, **3 successful pages**, **0 failed pages**, and `complete: true`. Original order was preserved with modes `full_score`, `chord_only`, `full_score`. MusicXML remains per-page; it is not combined across page boundaries.

| Validation / performance item | Result |
|---|---|
| API benchmark completed | 3/3 |
| API p50 | 24.5197 s |
| API p95 (nearest rank) | 25.2878 s |
| API maximum | 25.2878 s |
| API container memory snapshot | 1.077 GiB |
| Fast CI backend suite | 786 passed / 11 skipped |
| Real V1 `/detect` smoke | PASS |

The memory value is a container snapshot, not a peak-RSS measurement. Three API requests do not establish an SLA. **99% accuracy and 30 seconds/page remain report-only targets**, not runtime rejection thresholds and not an SLA.

## Real-sheet development/reference evidence

| Sheet | Returned mode | Full-score notes exact | Chord recall / precision | Key signature |
|---|---|---:|---:|---:|
| jusim | full_score | 97.1% | 86.8% / 97.1% | 100% |
| jayu | full_score | 100% | 98.4% / 98.4% | 100% |
| chingu | full_score | 100% | 94.4% / 94.4% | 100% |
| naui | chord_only; full-score reconstruction withheld | 77.8% (withheld) | 94.8% / 94.8% (fallback) | — |

These real sheets are development/reference evidence, **not an independent blind corpus**. The synthetic holdout shares its generator family with development data. The completed holdout must not be tuned against; once its results inform changes, its seeds are regression data rather than unseen evidence.

## CI operation after closure

**PR Fast CI is regression/smoke only.** It runs automatically on relevant pull-request changes and cannot establish full acceptance accuracy or blind results.

**Full Acceptance Evaluation is manual-only (`workflow_dispatch`), not required on every commit.** The temporary PR #62 label trigger has been removed. Manual inputs remain `publish=false`, `fresh_holdout=true`, and optional `holdout_seeds`. Empty seeds with fresh holdout enabled derive four seeds from `GITHUB_RUN_ID`; recorded seeds and source SHA preserve reproducibility. Artifact upload remains enabled. Evidence-branch publication requires an explicit manual request and remains a bounded review bundle; full evidence stays in the Actions artifact.

## Public / production release — HOLD

1. Independent real-sheet blind evaluation is still required.
2. Audiveris AGPL-3.0 deployment, corresponding-source and compliance obligations need review.

Engineering acceptance is closed; these public-release obligations remain unresolved. PR #62 remains open for human merge review. Neither release nor production feature-flag activation is authorized by this record.
