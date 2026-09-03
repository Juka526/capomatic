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
- Frontend Auth0 (SPA) is live on Vercel: `NEXT_PUBLIC_AUTH0_DOMAIN=dev-em2gvqp2q71brplg.us.auth0.com`,
  `NEXT_PUBLIC_AUTH0_CLIENT_ID=ftLB1Swg3LHaWrADVs0gPnnZDrqDjZ3c`, token audience `https://capomatic-api`
- Backend has no `DATABASE_URL`, so `/api/auth/*` and `/api/admin/*` are mounted but answer 503
  `Database is not configured`. Public OCR is unaffected.
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

## Auth0 and optional auth/admin

Auth0 tenant `dev-em2gvqp2q71brplg` (US-5) backs the deployed frontend.

- SPA application `Capomatic Deploy` (`ftLB1Swg3LHaWrADVs0gPnnZDrqDjZ3c`) allows
  `https://capomatic.vercel.app` with and without a trailing slash for callback, logout, and web
  origins. `frontend/lib/auth0.ts` sends `window.location.origin`, which carries no trailing slash.
- M2M application `Capomatic Branding M2M` holds only `read:branding`, `update:branding`,
  `read:prompts`, and `update:prompts` on the Management API. Its secret lives in the untracked
  `.env.auth0.local` and is never required at runtime.
- Universal Login is branded through the Management API, not the dashboard: theme `Capomatic`,
  primary `#E05D00`, page background `#F5EDD8`, links `#A33F00`, logo
  `https://capomatic.vercel.app/favicon.svg`. Links are darker than the primary on purpose so link
  text clears WCAG AA on white; `#E05D00` only reaches 3.66:1.
- Tenant default language is `ko`, supported languages are `ko` and `en`, and both carry custom
  login prompt text.

Backend JWT verification and the PostgreSQL-backed user/admin list exist in code but are not
enabled in production. Public OCR works without `DATABASE_URL`. Enabling auth/admin requires
`DATABASE_URL`, `AUTH0_DOMAIN`, and `AUTH0_AUDIENCE` together, plus an explicit admin-role,
migration, backup, and restore procedure.

Login is already exposed in the UI: `components/LoginButton.tsx` renders in the `pages/index.tsx`
nav, so a visitor can complete an Auth0 login today. `AuthProvider` calls `/api/auth/me` only to
enrich the role and swallows the failure, so ordinary login still behaves correctly. The visible
break is `pages/admin/dashboard.tsx`, whose `lib/admin-api.ts` rethrows the raw
`Database is not configured` detail from `/api/admin/users`.

## Current priorities

1. Keep reviewed releases synchronized across GitHub, Vercel, and HF, then decide whether
   historical HF storage should be reclaimed.
2. Resolve the frontend/backend auth mismatch: provision `DATABASE_URL`, `AUTH0_DOMAIN`, and
   `AUTH0_AUDIENCE` on the Space, or gate `/admin/dashboard` so it stops surfacing the raw 503.
3. Put an authentication, rate-limit, or budget boundary around paid public GPT refinement,
   or disable its production secret.
4. Continue reducing OCR latency only when fixture coverage remains acceptable.
5. Validate OCR changes on unseen Korean worship sheets.

## Change rules

- Keep changes minimal and local.
- Preserve deterministic parsing/transposition and OCR debug metadata.
- Do not add PDF or staff-note transposition without an explicit scope change.
- Run backend tests and the frontend production build before release.
- Never commit environment files, tokens, local virtual environments, or generated build output.
