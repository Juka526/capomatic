# Production Deployment Checklist

V1 scope and go/no-go requirements are defined only in
[`V1_RELEASE_PLAN.md`](V1_RELEASE_PLAN.md). This file records deployment procedure, historical
measurements, and release evidence.

Current runtime topology:

```text
Browser ──> Vercel frontend (capomatic.vercel.app)
   └──────> HF API (juka526-capomatic.hf.space)
```

## Live baseline recheck (2026-09-16, Asia/Seoul)

This is the currently deployed pre-V1 baseline, not candidate evidence:

- [x] Vercel `/` and `/history` return 200.
- [ ] Vercel `/privacy` and `/terms` return 404; the local candidate pages are not deployed.
- [ ] Vercel `/admin/dashboard` returns 200; the local candidate retirement is not deployed.
- [x] HF `/health` and `/` return 200.
- [ ] HF `/api/auth/me`, `/api/auth/admin-test`, and `/api/admin/users` return the old
  database-configuration 503 response; login-only V1 behavior is not deployed.
- [x] The production-origin preflight for `POST /detect` returns 200 and the exact Vercel origin.
- [x] HF CLI reports `juka526/capomatic` `RUNNING`/`READY`, one `cpu-basic` replica in `us`, and
  runtime/repository SHA `bbb7619f957a926d5d48efbc2be2cfc18c0207c6`.
- [ ] HF currently overrides the candidate Docker default with
  `CHORDTAYLOR_OCR_DET_MODEL=v6-medium`; remove or deliberately reconcile that override before a
  candidate comparison.
- [ ] HF still has an `OPENAI_API_KEY` secret. Its value was not inspected; V1 must remove it.
- [ ] HF has no `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, or `SENTRY_DSN` configuration.
- [ ] The newly authenticated official Vercel MCP sees zero teams/projects, so the account-internal
  project, environment, source-SHA, and deployment settings remain unverified.

These checks prove only that the old service is reachable and identify the post-deploy differences
that must be smoke-tested. They do not clear a V1 gate.

## Audited state (2026-08-29)

Confirmed:

- [x] Vercel production URL is `https://capomatic.vercel.app`.
- [x] The deployed frontend bundle uses `https://juka526-capomatic.hf.space`.
- [x] HF reports Docker SDK, port `7860`, one `cpu-basic` replica, and `RUNNING`/`READY`.
- [x] HF has an `OPENAI_API_KEY` secret; its value was not inspected.
- [x] HF `CORS_ORIGINS` is `https://capomatic.vercel.app`; `/health` and the POST preflight return 200 with the matching CORS header.
- [x] Local verification: 296 backend tests passed, 10 live integration tests skipped, the Next.js 16 production build passed, and `npm audit` reports zero vulnerabilities.
- [x] HF pre-sync commit `ad28e00ef7344d2f9ca0154da59ac23bbb190366` removed `.venv/`, `.idea/`, and `.claude/settings.local.json`; the canonical tree also excludes them.

Current deployment identities:

- Local/GitHub `main`: `5740b4ab4abb2bd3b30ff8eb6e611bead5378f77`
- Vercel Next.js build ID: `VPaLW_Km8pXWeei_iN0Gi` (the public deployment does not expose its source SHA)
- HF runtime SHA: `4d05f243a3053abf6f13289f16661b79ec3cbd4d`

Configuration of the 2026-08-29 deployment:

- HF had no database or Auth0 variables. Public OCR was unaffected.

Remediation outcome:

- [x] GitHub `main` drives Vercel, and HF `main` is a clean runtime snapshot whose commit message records the reviewed GitHub SHA.
- [x] The optional-database fix is deployed; an unconfigured database no longer triggers a localhost connection attempt.

Remaining operational decisions:

- [ ] HF historical storage still reports about 662 MB after current-tree cleanup; reclaiming history needs a separate reviewed decision.
- [x] The V1 candidate retires the public GPT endpoints in code.
- [ ] Remove the HF `OPENAI_API_KEY` secret while deploying V1 and verify both endpoints return
  `410 Gone`.

## Detection performance baseline (2026-08-29)

Measured against production HF SHA `4d05f243a3053abf6f13289f16661b79ec3cbd4d` on one
`cpu-basic` replica, using `POST /detect` with `ocr_engine=paddle`:

| Labeled sheet | API total | Paddle predict | Coverage | Unique precision |
| --- | ---: | ---: | ---: | ---: |
| 만왕의 왕 내주께서 | 39.68 s | 36.78 s | 100% | 100% |
| 친구야 | 62.76 s | 60.95 s | 100% | 76.47% |
| 믿음으로 나아가네 | 155.68 s | 153.14 s | 100% | 100% |

The three-case cross-fixture mean is 86.04 seconds and population standard deviation is 50.13 seconds, so the
60 ±20 second service target is not met. DNS, TCP, and TLS completed within one second; Paddle
prediction dominates. The production Vercel HTML loaded in 0.44 seconds and the frontend sends
the upload directly to HF, so Vercel is not a material part of post-upload detection latency.
This small sample records the current service bottleneck; the full labeled API gate below remains
the release decision.

Dependency screen on the same 15 labeled sheets (local Apple Silicon, so not an HF service SLA):
PaddlePaddle 3.2.2 and 3.3.1 both produced 98.07% coverage and 88.91% unique precision, while their
mean OCR times were 16.17 and 19.00 seconds respectively. Keep 3.2.2; the latest release did not earn
an HF candidate deployment because it was 17.5% slower at equal measured quality and its Linux x86
oneDNN path has a reported upstream regression.

## 1. Local release gate

- [ ] `python -m pytest`
- [ ] `cd frontend && npm run check`
- [ ] `cd frontend && npm audit --audit-level=high`
- [ ] `pip-audit -r requirements.txt`
- [ ] Required backend, frontend, and Docker CI checks are green on the candidate GitHub commit and branch protection blocks
  merging when they fail.
- [ ] Review `git status --short`; do not include local artifacts or unrelated fixture changes.
- [ ] Confirm no `.env`, tokens, or credentials are tracked.
- [ ] Confirm the root `Dockerfile` is the only backend deployment definition.

Local candidate evidence on 2026-09-16:

- [x] Backend suite in a fresh exact-dependency environment: 408 passed and 10
  credential/network-dependent integration cases skipped.
- [x] Frontend unit tests, TypeScript, and Next.js production build pass; generated routes are `/`,
  `/history`, `/privacy`, and `/terms`, with no administrator page.
- [x] `npm audit --audit-level=high` and `pip-audit -r requirements.txt` report no known
  vulnerabilities using advisory data checked on 2026-09-16. The recheck found Starlette 0.52.1
  advisories; upgrading to 1.3.1 cleared them and all 408 tests passed again.
- [x] Lighthouse 13.4.1 mobile accessibility is 100 on all four generated pages, with no failed
  scored audit. JSON reports are `/private/tmp/capomatic-lighthouse-{home,history,privacy,terms}.json`.
- [ ] Repeat all local checks from the exact candidate SHA after the fresh dependency/Docker build;
  the entries above describe the working tree and are not final release evidence.

Local OCR timing is a dependency screen, not the production latency gate. Deploy the exact
candidate commit to a private HF canary Space with the same Docker image, `cpu-basic` hardware,
and non-secret runtime variables as production. Do not replace production before this gate passes.
Set the canary URL explicitly and exercise the same browser-to-HF request path:

```bash
CANDIDATE_HF_API_URL=https://juka526-capomatic-perf-canary.hf.space
CANDIDATE_HF_SHA=<recorded-canary-runtime-sha>
python scripts/eval_ocr.py --engine paddle \
  --api-url "$CANDIDATE_HF_API_URL" \
  --baseline-api-url https://juka526-capomatic.hf.space \
  --render-check --deployment-sha "$CANDIDATE_HF_SHA" \
  --report-json /private/tmp/capomatic-v1-canary-ocr.json
```

Run from the Seoul client against a ready, warmed Space, sequentially once for every one of the 15
JSON labels in `fixtures/labels`; each label names its image in `fixtures/images`. The evaluator uses
a 240-second per-request timeout and sends `Origin: https://capomatic.vercel.app`, so it also verifies
the production browser CORS boundary. It warms both APIs once before the measured pass and compares
every candidate fixture against production quality. Record that warm-up as the cold-start result only
when the Space was restarted immediately before the command; it is not mixed into the warm aggregate.

The full labeled suite must keep at least the current 98.06% coverage and 88.90% unique-chord
precision. A warm run must have a cross-fixture mean at most 80 seconds and population standard
deviation at most 20 seconds; P90 and maximum are recorded as diagnostics. The deviation describes
workload spread across sheets, not repeated-request jitter. A run omitting any canonical label is
only a smoke test and cannot pass the release gate.

Because the existing fixtures have informed OCR tuning, an independent reviewer who did not tune
the model must label and freeze one new sheet before inspecting either deployment. Pass it with
`--extra-label`; its JSON must set `strict_unseen: true`, include the exact chord sequence, and use
equal minimum/maximum counts. The candidate must have 100% unique-chord coverage and precision,
exact count/order, and a manual Replace/Above review with no missing, extra, or displaced chord.
Do not release if either the regression corpus or this independent check fails.

Attempt 1 used `fixtures/images/IMG＿7710.png`, frozen at SHA-256
`4ceeb3b23ed2025d3a9c3ccd93e808bf0c0af494e3e7e52f43d77fc8958c30b5`. An isolated same-model
reviewer labeled 60 occurrences before either output was inspected. The local candidate detected
56, failed exact count/order, and therefore failed the gate. This image is now a development sample;
after any correction, freeze and review a different previously unused image for the release gate.

## 2. Vercel

The official Vercel MCP was authenticated on 2026-09-16 but returned zero visible teams/projects.
Its project-internal configuration cannot be release evidence until it is reauthorized against the
account/team that owns Capomatic (or an approved read-only API credential is used).

- [ ] Git repository: `Juka526/capomatic`
- [ ] Root directory: `frontend`
- [ ] Production domain: `https://capomatic.vercel.app`
- [ ] Production variable:

  ```env
  NEXT_PUBLIC_API_URL=https://juka526-capomatic.hf.space
  ```

- [ ] Set V1 `NEXT_PUBLIC_AUTH0_DOMAIN` and `NEXT_PUBLIC_AUTH0_CLIENT_ID`.
- [ ] Set `NEXT_PUBLIC_SENTRY_DSN`; trigger a staging client error and confirm receipt.
- [ ] Confirm the production deployment was built from the intended GitHub SHA.
- [ ] If Git integration does not create that deployment, use Vercel **Deployments → Create Deployment** with the exact Git SHA.

## 3. Hugging Face Space

The official HF MCP can confirm the public Docker Space identity but does not expose runtime,
hardware, variable, or secret inspection operations. The HF CLI live snapshot above remains the
available read-only evidence; secret values were never inspected.

- [ ] Space: `juka526/capomatic`
- [ ] SDK: Docker
- [ ] App port: `7860`
- [ ] Production OCR model and canvas thresholds come from the root `Dockerfile`.
- [ ] Required variable:

  ```env
  CORS_ORIGINS=https://capomatic.vercel.app
  ```

- [ ] Confirm `OPENAI_API_KEY` and `DATABASE_URL` are absent for V1.
- [ ] Configure the login identity endpoint:

  ```env
  AUTH0_DOMAIN=your-domain.auth0.com
  AUTH0_AUDIENCE=https://capomatic-api
  ```

- [ ] Set `SENTRY_DSN`, `SENTRY_ENVIRONMENT=production`, and the candidate
  `SENTRY_RELEASE`; trigger a staging backend error and confirm receipt.
- [ ] Configure Sentry alerts for a new 5xx issue and sustained transaction latency.

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
- [ ] Confirm `POST /detect/refine` and `ocr_engine=paddle-gpt` cannot invoke paid refinement.
- [ ] Confirm history persists after a page reload in the same browser.
- [ ] Confirm Korean/English switching and image download.
- [ ] Test login, logout, and `/api/auth/me` with a production token.
- [ ] Confirm `/admin/dashboard` is not found and administrator APIs return `410 Gone`.
- [ ] Open the linked privacy notice and terms in Korean and English.

## 5. Release synchronization

GitHub `main` is the canonical source and Vercel deploys it through Git integration. HF receives
a runtime-only snapshot because binary test fixtures in GitHub history are excluded from the
Docker runtime and rejected by the Hub's normal Git path. Every HF deployment commit must record
its source GitHub SHA.

The previous HF history is recoverable at tag `pre-github-sync-2026-08-28`. Do not repeat the
one-time force operation during normal releases. When runtime files change, publish from the
canonical repository root through a fresh clone of the clean HF history:

```bash
release_dir="$(mktemp -d)"
git clone --depth 1 https://huggingface.co/spaces/juka526/capomatic "$release_dir/space"
git -C "$release_dir/space" rm -r --ignore-unmatch -- \
  .dockerignore .env.example Dockerfile README.md requirements.txt backend
git archive HEAD .dockerignore .env.example Dockerfile README.md requirements.txt backend \
  | tar -x -C "$release_dir/space"
git -C "$release_dir/space" add -A
git -C "$release_dir/space" commit -m "Deploy GitHub $(git rev-parse HEAD)"
git -C "$release_dir/space" push origin main
```

Authenticate with `hf auth login --add-to-git-credential` if needed. Confirm or create the Vercel
deployment for the exact Git SHA. For every release, record:

- [ ] GitHub `main` SHA
- [ ] Vercel production source SHA
- [ ] HF Space runtime SHA and its source GitHub SHA from the deployment commit message
- [ ] Previous known-good deployment IDs and the non-secret environment-variable snapshot

Do not diagnose a code regression until all three point to the intended source tree.

## 6. Rollback

1. **Code:** create a forward revert with `git revert <bad-release-sha>`; do not push an ancestor or force-push.
2. **Frontend:** push the revert, then confirm Vercel deployed that SHA or redeploy the recorded known-good deployment.
3. **Backend:** publish a new HF runtime snapshot from the forward-revert GitHub commit.
4. **Configuration:** restore the recorded non-secret values and secret keys from the external secret store, then restart HF.
5. **Verify:** repeat `/health`, POST preflight, upload/detect, and render smoke tests.
6. **Database:** restore a backup only if the optional database mode was enabled and a migration caused the incident.

## Runtime characteristics

- HF `cpu-basic` can have a slow cold start and PaddleOCR model warm-up.
- The Vercel frontend sends uploads directly to HF; Vercel page load is not part of `/detect`
  processing time. API-mode evaluation still sends the production Vercel `Origin` header.
- Detection IDs live in one backend process and disappear on restart.
- Keep one replica until detection state moves to a shared store or requests gain session affinity.
- History lives in browser `localStorage`, not PostgreSQL.
- Auth0 login is supported without a database; administrator features and paid GPT refinement
  are intentionally unavailable in V1.
