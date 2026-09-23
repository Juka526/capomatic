# Issue #10 — V1 release candidate audit and CI evidence

Scope: audit the `v1/issue-10-release-candidate` branch diff against `origin/main`, run every
release-gate check that is practical on a local workstation, inspect the Docker/CI/deployment
definitions, and record what could not be verified. Gate definitions live in
[`V1_RELEASE_PLAN.md`](V1_RELEASE_PLAN.md); this file records one execution of them and does not
change any threshold.

Nothing here was inferred. Every `PASS` row below is a command that ran in this environment with
the quoted result. External systems (GitHub Actions, Docker, branch protection, Vercel, Hugging
Face, Auth0, Sentry) were **not** contacted, so their gates are recorded as blockers, not passes.

## Environment

| Item | Value |
| --- | --- |
| Date | 2026-09-23 |
| Host | Darwin arm64 workstation (no container runtime) |
| Merge base | `bc42f8dbb070044b2491704cc3f91546b36999ea` |
| Python | 3.12.2, fresh `.venv`, `pip install -r requirements.txt` from the pinned file |
| Node / npm | v25.2.0 / 11.16.0 (CI pins Node 22; not reproduced locally) |
| pytest / pip-audit | 9.1.1 / 2.10.1 |

## Diff audit (gate 1: "no secret, `.env`, local artifact, or unrelated user change")

- Added lines across the whole diff (lockfile excluded) were scanned for private keys, `sk-`
  tokens, AWS keys, GitHub/Slack tokens, `client_secret`, and inline passwords. **No credential
  material found.** Every hit was a placeholder or an `os.environ` lookup: `.env.example` and
  `frontend/.env.local.example` carry `https://public-key@o0.ingest.sentry.io/project-id`, and the
  Sentry configs read `SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN` from the environment.
- No personal paths, machine identifiers, or unrelated user changes. The `/private/tmp/...` strings
  in `V1_RELEASE_PLAN.md` are labelled workstation-session report paths, not shipped artifacts.
- Two tracked build artifacts were found and removed from the index (both already matched
  `.gitignore`, so they were stale index entries, not new files):
  - `output.png` (674 KB stray render output at the repository root)
  - `frontend/tsconfig.tsbuildinfo` (TypeScript incremental cache; `next build` rewrites it on
    every run, and a committed cache can let `tsc --noEmit` skip work in CI)
- `frontend/next-env.d.ts` was refreshed to the form Next 16.3.3 generates; the committed copy was
  stale relative to the pinned Next version.

## Checks run

All backend and frontend checks were re-run against a **clean export of tracked files only**
(`git archive` of the staged tree into an empty directory), which is the closest local equivalent
of a fresh CI checkout.

| Check | Command | Result |
| --- | --- | --- |
| Backend dependency install | `pip install -r requirements.txt` in a fresh 3.12 venv | PASS — resolved to the pinned `paddleocr 3.7.0` / `paddlepaddle 3.2.2` |
| Backend tests | `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True python -m pytest -q` | PASS — `409 passed, 11 skipped` |
| Backend tests, clean tracked-only tree | same, in the `git archive` export | PASS — `409 passed, 11 skipped` |
| Python advisories | `pip-audit -r requirements.txt` | PASS — `No known vulnerabilities found` |
| Frontend install | `npm ci` | PASS — 266 packages, `found 0 vulnerabilities` |
| Frontend advisories | `npm audit --audit-level=high` | PASS — `found 0 vulnerabilities` |
| Frontend tests + typecheck + build | `npm run check` | PASS — `pass 8 / fail 0`, `tsc --noEmit` clean, `next build` compiled, routes `/`, `/history`, `/privacy`, `/terms`, `/404` |
| Frontend, clean tracked-only tree | `npm ci && npm audit --audit-level=high && npm run check` | PASS — identical results |
| API startup under the Dockerfile's environment | `uvicorn backend.api.main:app` from a directory filtered to what `.dockerignore` admits | PASS — `/health` returned `{"status":"ok"}` about 4 s after start; `/` 200; `/api/admin/users` 410 |
| CI workflow syntax | `yaml.safe_load(".github/workflows/ci.yml")` | PASS — jobs `backend`, `frontend`, `docker` |

The 11 skips are the 10 `tests/integration` cases that need `TEST_TOKEN` plus the fixture skip
described below.

## Issues found and fixed on this branch

1. **`tests/test_preprocess.py` failed on any clean checkout.**
   `TestDetectStaffSystems::test_fixture_moment_life_detects_all_staff_systems` opened
   `fixtures/images/순간이-삶이-되어.png`. That image was never committed (`git log --all` for the
   path is empty) and is absent from both this worktree and the tracked corpus, so the first fresh
   run failed with `FileNotFoundError`. Because `.github/workflows/ci.yml` is new on this branch,
   this would have been a red build on the first CI run. The test now skips with an explicit reason
   when the sample is absent, and still asserts when a local copy exists. The image could not be
   recovered or reconstructed, so the assertion remains unexercised in CI — see blockers.
2. **The `docker` CI job did not check that the image starts.** Gate 1 requires the image to build,
   report its pinned PaddleOCR version, *and* start successfully; the job only covered the first
   two. A step now runs the container and polls `/health` (5 min budget, dumps `docker logs` and
   fails on timeout). This step's syntax was validated but it has **not** been executed — no
   container runtime exists here.
3. Stale tracked artifacts removed, as listed in the diff audit above.

Inspected and found correct, no change needed: `.dockerignore` excludes `.git`, `.venv`, `.env*`,
and the frontend/test/fixture trees, and no `backend/` module reads any excluded path; the
`docker` job's version assertions (`3.7.0` / `3.2.2`) match `requirements.txt`; the retired
surfaces behave as the plan specifies (`/api/admin/users` and `/api/auth/admin-test` return 410,
`POST /detect/refine` returns 410 for a well-formed request, covered by `tests/test_api.py`).

## Blockers — external gates not verifiable here

None of the following was contacted, simulated, or estimated.

| Gate | Blocker |
| --- | --- |
| Docker build and dependency parity | No container runtime on this host: `docker: command not found`, no `Docker.app`, no `podman`/`colima`/`nerdctl`. The image was never built, so the build, the version assertion, and the new startup step are all unverified. The file-context substitute above is not a substitute for the image. |
| GitHub required CI | The workflow has never executed. This work was not pushed and no PR was opened, so no run, no check result, and no candidate SHA status exist. |
| Branch protection | Repository settings were not read. Whether `backend`, `frontend`, and `docker` are required checks is unknown. |
| Candidate SHA | Gate 1 requires the checks to pass on the exact candidate SHA. The results above are for this branch's tree and must be repeated on the candidate. |
| Vercel / Hugging Face / Auth0 / Sentry | No deployment, configuration read, or credential inspection was performed. The `OPENAI_API_KEY` secret the plan says must be removed from the HF Space was neither inspected nor changed. |
| Untracked regression sample | `fixtures/images/순간이-삶이-되어.png` is not in the repository. Either commit the image (it has no `fixtures/labels` entry, so it is not part of the canonical corpus) or delete the test; until then that staff-detection assertion never runs in CI. |

## Residual risk

The new `docker` startup step is the only change here that cannot be exercised locally. If it is
wrong, the failure surfaces as a red `docker` job on the first CI run rather than as a bad release.
