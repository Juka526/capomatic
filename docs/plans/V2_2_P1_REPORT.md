# V2-2 P1: bounded PDF core verification

Owner approved the plan and flattened PDF tradeoff on 2026-10-14. P1 is implemented and independently tested; job API, UI, ink and camera are subsequent slices.

Core: pypdfium2 5.14.0 checks/rasterizes sequentially under a process-wide mutex with handle cleanup. Input limits are 20 MiB / 10 pages; exact rounded pixel dimensions are checked before raster allocation (8MP). Every encrypted file is rejected, including owner-password-only files. Output consumes a page iterator and writes a fresh lossless RGB/Flate PDF with capacity checked before every append (128MiB), retaining at most one decoded producer page. No source actions/forms/links/files are copied. Effective displayed page size/orientation is preserved; output `/Rotate` is normalized to zero.

| Check | Result |
| --- | --- |
| `env -i HOME=$HOME PATH=/usr/bin:/bin PDF_INDEPENDENT_PYTHON=/opt/anaconda3/bin/python .venv/bin/python -m pytest tests/pdf -p no:cacheprovider -q` | 51 passed, 0 skipped; independent pypdf 6.18.1 strict-read check ran. |
| T2 pre-fix capacity check | `d08a147` writes past cap (1 failure); removing the new bounded-write guard fails; restored `7543c0a` passes. Product diff restored clean. |
| Independent golden cases | Hand-built PDFs: rotation 0/90/180/270, boxes/order/quadrant colours, blank white pages, exact lossless output pixels and PDF structure. |
| T5 controls | Same detector sees deliberate over-cap writes, network connection, concurrent native calls without lock, source active tokens and malformed/encrypted/limit cases before negatives are trusted. |
| Home baseline | 390×844, 820×1180, 1024×1366 and 1280×900 on Chromium 156.0.8078.4; repeated captures byte-identical. This is the original guest home, not feature UI acceptance. |
| Owner-local input compatibility | 12 unique purchased-source PDFs / 13 pages rasterized locally as RGB within 8MP; maximum 3,294,225 pixels. No export, OCR, training, source copy or upload; not formal evaluation data. |
| Linux/HF and device gates | NOT RUN. Local macOS resource probes are not HF measurements. Real iPadOS 18.1 is the owner's available test target; its checks remain pending. |

Baseline protocol: light, Korean locale, Asia/Seoul timezone, reduced motion, DPR 1, guide dismissed, guest/no history, service workers blocked. The Next dev indicator is visible bottom-left and must be identical in the later comparison. The same framework request log and resource timing catch a deliberate local favicon request. Non-local requests are blocked; the existing Vercel Analytics debug script was the only observed external attempt. The zero-difference acceptance at 390/1280 is pending the later feature comparison.

Tester: Opus 5.5, final token `c2tstk`, both markers recovered. Product at `7543c0a`; tests separately committed by orchestrator. Native API/license references and remaining package-notice inventory are in the plan. No home or protected-file edits. A source iterator must be used by the job API to retain the bounded decoded-page behavior.

Next: capability-scoped ephemeral jobs sharing existing OCR admission, then controls/export and tablet reader. User scores stay out of telemetry; real title/chord content is normal result data only. No privacy/terms edits or deployment. Rollback uses a new ordinary commit.
