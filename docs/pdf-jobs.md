# PDF analysis jobs (V2-2 P2)

Setup: `/opt/anaconda3/bin/python -m venv .venv && .venv/bin/pip install -r requirements.txt` (a P2 check without Paddle: install every pin except `paddle*`; OCR is then stubbed). Dev CORS origin is process config, e.g. `CORS_ORIGINS=http://localhost:3201`.

API (all job calls need header `X-PDF-Job-Capability`; responses are `Cache-Control: no-store`):
- `POST /pdf/jobs` — body is the raw PDF bytes (not multipart). Optional `X-PDF-Session`; if absent a session token is minted. 202 returns `job_id`, `job_capability` and (if minted) `session_token` once. 409 `pdf_session_busy`, 429 `pdf_busy` (+Retry-After), 413/422 fixed `pdf_*` codes.
- `GET /pdf/jobs/{id}` — state (`queued|analyzing|needs_review|failed`), stage, `pages_done/pages_total`, per-page size/rotation/title/key/chord_count. No grouping is proposed yet (P3).
- `GET /pdf/jobs/{id}/pages/{n}/source` — JPEG preview (<=1200 px) made during analysis; 409 until that page is done.
- `DELETE /pdf/jobs/{id}` — 204.
Unknown id and wrong capability both give the same 404.

Limits: 2 live jobs, 1 per session token, 15 min idle / 30 min hard TTL, 600 s analysis budget (checked between pages), 128 MiB source+previews per job.

Resource rules: every native call (inspect or page) keeps its slot until it actually returns, even after cancel, expiry, task cancellation or loop close; completion callbacks run on worker threads under a lock. Only one PDF page is in the OCR executor at a time and a waiting job holds no OCR permit. A failed job drops its source, previews and detected results at once; its status shell (state + fixed error code only) is kept for at most 8 jobs / 2 minutes. An expired or removed upload stops being read immediately and its slot is freed only after its buffered chunks are dropped. The 600 s budget is checked before every new page; a page already running (or the last page) can finish past it because a native call cannot be killed.

Limitations: cancel/expiry cannot kill a running OCR call; the slot and OCR permit stay held until it returns, then output is discarded. Expired/canceled jobs read as 404 (no `expired` state). Jobs are lost on restart. Source bytes live in memory only; each page's PNG is a temp file deleted when its OCR call returns. Sentry: every breadcrumb is dropped and events are rebuilt from an allowlist (exception values/messages redacted); transaction names are limited to the app's route templates (`/pdf/*` for PDF routes, else `unknown`) and trace context keeps only validated ids.
