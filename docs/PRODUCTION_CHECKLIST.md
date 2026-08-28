# Production Deployment Checklist

Current runtime topology:

```text
Browser ──> Vercel frontend (capomatic.vercel.app)
   └──────> HF API (juka526-capomatic.hf.space)
```

## Audited state (2026-08-28)

Confirmed:

- [x] Vercel production URL is `https://capomatic.vercel.app`.
- [x] The deployed frontend bundle uses `https://juka526-capomatic.hf.space`.
- [x] HF reports Docker SDK, port `7860`, one `cpu-basic` replica, and `RUNNING`/`READY`.
- [x] HF has an `OPENAI_API_KEY` secret; its value was not inspected.
- [x] HF `CORS_ORIGINS` is `https://capomatic.vercel.app`; `/health` and the POST preflight return 200 with the matching CORS header.
- [x] Local verification: 296 backend tests passed, 10 live integration tests skipped, the Next.js 16 production build passed, and `npm audit` reports zero vulnerabilities.
- [x] HF pre-sync commit `ad28e00ef7344d2f9ca0154da59ac23bbb190366` removed `.venv/`, `.idea/`, and `.claude/settings.local.json`; the canonical tree also excludes them.

Audit-start deployment identities, before this remediation release:

- Local/GitHub base HEAD: `1cfe2637f724a15d0fcc812946ac889e19abf6a3` (the fixes in this audit are still uncommitted)
- Vercel Next.js build ID: `nJ4GX0fwsyzlwOs3oNI4V` (the public deployment does not expose its source SHA)
- HF runtime SHA: `ad28e00ef7344d2f9ca0154da59ac23bbb190366`

Intentionally disabled in the current public-only deployment:

- HF has no database or Auth0 variables. Public OCR works; auth/admin stays disabled.

Remediation outcome:

- [x] GitHub `main`, the Vercel source release, and HF `main` use the reviewed canonical history.
- [x] The optional-database fix is deployed; an unconfigured database no longer triggers a localhost connection attempt.

Remaining operational decisions:

- [ ] HF historical storage still reports about 662 MB after current-tree cleanup; reclaiming history needs a separate reviewed decision.
- [ ] **Release blocker:** GPT refinement is public and uses a paid API key. Add an auth/rate/budget boundary or disable the secret.

The local/GitHub source tree and current HF tree now exclude local environments. Historical HF
storage still needs a separate reviewed reclamation decision.

## 1. Local release gate

- [ ] `python -m pytest`
- [ ] `cd frontend && npx tsc --noEmit`
- [ ] `cd frontend && npm run build`
- [ ] Review `git status --short`; do not include local artifacts or unrelated fixture changes.
- [ ] Confirm no `.env`, tokens, or credentials are tracked.
- [ ] Confirm the root `Dockerfile` is the only backend deployment definition.

## 2. Vercel

- [ ] Git repository: `Juka526/capomatic`
- [ ] Root directory: `frontend`
- [ ] Production domain: `https://capomatic.vercel.app`
- [ ] Production variable:

  ```env
  NEXT_PUBLIC_API_URL=https://juka526-capomatic.hf.space
  ```

- [ ] If Auth0 is enabled, set `NEXT_PUBLIC_AUTH0_DOMAIN` and
  `NEXT_PUBLIC_AUTH0_CLIENT_ID`.
- [ ] Confirm the production deployment was built from the intended GitHub SHA.
- [ ] If Git integration does not create that deployment, use Vercel **Deployments → Create Deployment** with the exact Git SHA.

## 3. Hugging Face Space

- [ ] Space: `juka526/capomatic`
- [ ] SDK: Docker
- [ ] App port: `7860`
- [ ] Production OCR model and canvas thresholds come from the root `Dockerfile`.
- [ ] Required variable:

  ```env
  CORS_ORIGINS=https://capomatic.vercel.app
  ```

- [ ] Optional secret for GPT refinement: `OPENAI_API_KEY`
- [ ] Optional auth/admin variables, configured together:

  ```env
  DATABASE_URL=postgresql+asyncpg://...
  AUTH0_DOMAIN=your-domain.auth0.com
  AUTH0_AUDIENCE=https://capomatic-api
  ```

- [ ] `GET https://juka526-capomatic.hf.space/health` returns
  `{"status":"ok"}`.
- [ ] A request with `Origin: https://capomatic.vercel.app` returns
  `Access-Control-Allow-Origin: https://capomatic.vercel.app`.
- [ ] The deployed HF SHA matches the intended backend release.
- [ ] No manually uploaded `.venv/` or `.idea/` files remain in the Space repository.
- [ ] The Docker build context excludes frontend code, fixtures, tests, docs, and local artifacts.

## 4. Functional smoke test

- [ ] Load `https://capomatic.vercel.app` without console errors.
- [ ] Upload a PNG or JPEG and detect chords.
- [ ] Change capo position and render both overlay modes.
- [ ] Use AI refinement when `OPENAI_API_KEY` is enabled.
- [ ] Confirm history persists after a page reload in the same browser.
- [ ] Confirm Korean/English switching and image download.
- [ ] If auth/admin is enabled, test login, `/api/auth/me`, and `/api/admin/users`.

## 5. Release synchronization

GitHub `main` is the canonical source. Vercel deploys it through Git integration; HF uses the
repository configured locally as the `hf` remote. The HF history was reconciled once on
2026-08-28. Do not repeat that force operation during normal releases. If divergence is suspected:

```bash
git fetch origin main
git fetch hf main
git log --left-right --graph --oneline origin/main...hf/main
```

Authenticate Git access with `hf auth login --add-to-git-credential` if needed. Do not make
force-pushing part of the normal release procedure.

After reconciliation, the normal release is `git push origin main` followed by `git push hf main`.
Confirm or create the Vercel deployment for the exact Git SHA. For every release, record:

- [ ] GitHub `main` SHA
- [ ] Vercel production source SHA
- [ ] HF Space runtime SHA, or its explicit source-SHA mapping while histories differ
- [ ] Previous known-good deployment IDs and the non-secret environment-variable snapshot

Do not diagnose a code regression until all three point to the intended source tree.

## 6. Rollback

1. **Code:** create a forward revert with `git revert <bad-release-sha>`; do not push an ancestor or force-push.
2. **Frontend:** push the revert, then confirm Vercel deployed that SHA or redeploy the recorded known-good deployment.
3. **Backend:** push the same revert commit to `hf main` after the repositories are reconciled.
4. **Configuration:** restore the recorded non-secret values and secret keys from the external secret store, then restart HF.
5. **Verify:** repeat `/health`, POST preflight, upload/detect, and render smoke tests.
6. **Database:** restore a backup only if the optional database mode was enabled and a migration caused the incident.

## Runtime characteristics

- HF `cpu-basic` can have a slow cold start and PaddleOCR model warm-up.
- Detection IDs live in one backend process and disappear on restart.
- Keep one replica until detection state moves to a shared store or requests gain session affinity.
- History lives in browser `localStorage`, not PostgreSQL.
- Auth/admin endpoints intentionally return unavailable until database and Auth0 settings exist.
