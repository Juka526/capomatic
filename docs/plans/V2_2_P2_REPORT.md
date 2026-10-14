# V2-2 P2: ephemeral PDF job API verification

Owner approved the plan on 2026-10-14. P2 is implemented and independently tested at product commit `7aa0353`; grouping, transposition controls/export UI and the tablet reader are subsequent slices.

API: raw-body POST reserves admission before reading bytes; unpredictable job id plus separate header-only job capability; separate anonymous session token, at most two resource-holding jobs globally and one per token. GET status and source JPEG preview, DELETE cancellation, fixed errors/no-store and CORS. PDF pages share the existing OCR callable/executor/admission, with at most one PDF page admitted globally; a waiting PDF holds no OCR permit. Pages are not inserted into the legacy image cache.

Resource cleanup follows actual upload-buffer and concurrent native-future lifetimes, including timeout, task cancellation, loop shutdown and expiry. No slot is released while buffered source or native work still holds it. Failure clears detected metadata/source/results, retaining only up to eight content-free status records for 120 seconds. Existing limits remain 20MiB input, ten pages, 8MP per raster, 128MiB encoded job bytes, 15-minute inactivity/30-minute hard TTL and a 600-second between-page execution budget. A native call already running may outlive cancellation or the budget; its output is discarded after removal. Temporary page PNGs are deleted after OCR; there is no durable user-file persistence.

| Check | Result |
| --- | --- |
| Clean-shell `env -i HOME=$HOME PATH=/usr/bin:/bin PDF_INDEPENDENT_PYTHON=/opt/anaconda3/bin/python .venv/bin/python -m pytest -p no:cacheprovider -q tests/pdf tests/test_sentry_privacy.py` | **95 passed, 0 skipped**; independent strict PDF reader ran. |
| Legacy API | 65 passed at initial P2 verification; real Paddle replaced by a controlled stub. |
| T2 | Initial product `f631111`: 13 failures against the extended tests; `0de7a05` passes those guards. Final same-turn upload-buffer bound fails before `7aa0353`, passes afterwards; product files restored clean. Seven new guard mutations each fail their target checks. |
| T5 | Same detectors catch running permits/resource holders, saturated rejection before body read, live failure record at 119s, deliberate socket connection and synthetic Sentry payloads before accepting negatives. |
| Real SDK privacy | Locally intercepted sentry-sdk 2.69.1 errors/transactions: raw messages, request headers/bodies, score text, custom trace data, unmatched route content, tags, users, locals and breadcrumbs are stripped; normal exception type/release remain captured. No telemetry sent to production. |
| Formal runtime/device gates | Real Paddle PDF integration, Linux/HF p95 fairness/RSS, full-duration native shutdown, frontend Sentry and iPad: **NOT RUN**. |

The tester corrected two independent-test scheduling/counting errors rather than weakening the max-two and single-PDF-page requirements. The final probe charges an expired upload until its actual receive cleanup has dropped its chunks; no transient exception remains.

Detailed independent commands, controls and limitations: [P2_EVIDENCE.md](../../tests/pdf/P2_EVIDENCE.md). Both `c2p2final` Roundtrip return markers recovered. Tests were authored by Opus 5.5, product changes by Sonnet 5.5. No model performance claim, source-rights assumption, home/protected-asset/legal edit, deployment or console change. Rollback disables PDF admission/routes through an ordinary commit, with jobs lost on restart.
