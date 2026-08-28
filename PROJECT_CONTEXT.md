# Capomatic Project Context

## Product

Capomatic is a chord-sheet image transposition tool for Korean worship-team guitarists.
It detects printed chord symbols, transposes them deterministically, and renders replacement
or above-chord overlays. It does not transpose staff notation or sell/distribute scores.

Product rules:

- Detect first, transpose second.
- OCR/AI may detect or refine chord text; Python code owns transposition.
- Support slash chords and common extensions such as sus, add, maj/min, dim, aug, 6/7/9/11/13.
- Prefer practical target-key spellings over theoretical names such as E#, Cb, Fb, or B#.
- Optimize for Korean worship sheets without tuning to one publisher.

## Current production

- Frontend: Next.js on Vercel at `https://capomatic.vercel.app`
- Backend: FastAPI/PaddleOCR Docker Space at `https://juka526-capomatic.hf.space`
- Space: `juka526/capomatic`, Docker SDK, port `7860`, one `cpu-basic` replica
- Required HF variable: `CORS_ORIGINS=https://capomatic.vercel.app`
- Browser API target: `NEXT_PUBLIC_API_URL=https://juka526-capomatic.hf.space`
- Database/Auth0: not configured in the current public-only deployment
- OpenAI: optional refinement secret is present; the public cost-control boundary is unresolved

GitHub `main` is the canonical source and Vercel deploys it directly. HF uses a runtime-only
snapshot because GitHub history contains binary test fixtures that do not belong in the Space;
each HF deployment commit records its source GitHub SHA.
See `docs/PRODUCTION_CHECKLIST.md` for the audited state and release gates.

## Request and state flow

1. `POST /detect` runs PaddleOCR and returns chords plus a `detection_id`.
2. The backend keeps up to 20 detections in a process-local LRU cache.
3. `POST /detect/refine` optionally refines a cached detection with OpenAI.
4. `POST /render` deterministically transposes and returns Replace/Above images as base64 JSON.
5. The frontend stores user history in browser `localStorage`.

Detection IDs disappear on restart and are not safe across multiple replicas. Keep one replica
until this state moves to a shared store or requests gain session affinity.

## OCR configuration

- PaddleOCR remains the primary detector.
- Code defaults to the server detector for local runs.
- The production Dockerfile selects the mobile detector for HF CPU latency.
- The Dockerfile pins the production canvas safeguards:
  `PADDLE_MAX_STITCHED_PIXELS=900000`,
  `PADDLE_STITCH_MAX_SAFE_PIXELS=900000`, and
  `PADDLE_MIN_STITCH_RESIZE_SCALE=0.85`.
- Oversized stitched canvases fall back to per-staff-band OCR to preserve small chord text.

Evaluate OCR changes against labeled fixtures and report coverage, OCR/predict time, stitched
pixel count, quality-gate result, and fallback usage.

## Optional auth/admin

Auth0 JWT verification and a PostgreSQL-backed user/admin list exist in code but are not enabled
in production. Public OCR works without `DATABASE_URL`. Enabling auth/admin requires
`DATABASE_URL`, `AUTH0_DOMAIN`, and `AUTH0_AUDIENCE` together, plus an explicit admin-role,
migration, backup, and restore procedure.

## Current priorities

1. Keep reviewed releases synchronized across GitHub, Vercel, and HF, then decide whether
   historical HF storage should be reclaimed.
2. Put an authentication, rate-limit, or budget boundary around paid public GPT refinement,
   or disable its production secret.
3. Continue reducing OCR latency only when fixture coverage remains acceptable.
4. Validate OCR changes on unseen Korean worship sheets.

## Change rules

- Keep changes minimal and local.
- Preserve deterministic parsing/transposition and OCR debug metadata.
- Do not add PDF or staff-note transposition without an explicit scope change.
- Run backend tests and the frontend production build before release.
- Never commit environment files, tokens, local virtual environments, or generated build output.
