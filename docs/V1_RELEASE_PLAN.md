# Capomatic V1 Release Plan

This is the single source of truth for the non-MVP V1 product contract, release gates, and
go/no-go state. [`PRODUCTION_CHECKLIST.md`](PRODUCTION_CHECKLIST.md) contains procedures and
historical measurements only; if it conflicts with this file, this file wins.

## Ultimate goal

Capomatic becomes the dependable default tool a worship-team guitarist can point a phone camera
at to turn a chord sheet into an accurate, practical, transposed or capo-adjusted performance
sheet. Expansion beyond Korean sheets, one image at a time, and guitar-oriented chord notation is
future scope, not a reason to weaken V1.

## Authority and release decision

- The product owner makes the final go/no-go decision. The release executor records evidence but
  cannot waive a gate.
- Every gate below is required. A scope or threshold change is valid only after the product owner
  records the decision and rationale in this file before the candidate is tested.
- The independent unseen-sheet labeler/reviewer must not have selected OCR thresholds or tuned the
  candidate. The label is frozen before either candidate or production output is inspected.
- A release candidate is one GitHub commit SHA, one Vercel deployment built from that SHA, and one
  HF runtime commit whose message records that same SHA. Rebuilding or changing configuration
  creates a new candidate that must repeat affected gates.

## V1 product contract

### Included behavior

- The entire core journey is public: upload, PaddleOCR detection, manual chord correction,
  deterministic transposition, capo selection, Replace/Above rendering, and PNG download.
- Login and logout are optional and use Auth0. Login identifies the user but does not unlock core
  features, synchronize history, create a server-side account record, or confer an administrator
  role.
- Korean and English UI covers navigation, core actions, errors, accessibility labels, privacy,
  and terms.
- My Jobs stores at most 50 metadata entries in that browser's `tc-history` localStorage key:
  random local ID, song title, original key, target key, semitone shift, and timestamp. It stores
  neither an image nor a server detection ID and cannot reopen a prior result.

### Input and music contract

- One static PNG or JPEG is accepted based on decoded content, regardless of the supplied filename
  or MIME claim. The maximum is 20 MiB and 50,000,000 decoded pixels. Animated images and every
  other format receive a clear 4xx response. JPEG EXIF orientation is applied before OCR.
- V1 recognizes roots A through G, `#`/`b` accidentals, major/minor/dim/aug/sus qualities,
  arbitrary preserved extension text, parenthesized extensions, and slash-bass notes that the
  parser accepts. It transposes roots and slash bass independently.
- Target keys use the twelve conventional spellings C, Db, D, Eb, E, F, F#, G, Ab, A, Bb, and B.
  The UI capo selector supports frets 1 through 7; direct transposition supports -11 through +11
  semitones.
- Replace must cover each source chord at its occurrence and Above must associate the replacement
  with that same occurrence. A displacement is any label attached to the wrong source occurrence,
  covering unrelated content, or visually detached enough that the reviewer cannot identify its
  source unambiguously.

### Login contract

- The browser requests Auth0 scopes `openid profile email` and audience
  `https://capomatic-api`. Auth0 browser session/token state and profile claims are processed only
  for login display and API identity verification.
- `GET /api/auth/me` requires an `Authorization: Bearer <access-token>` header. The backend accepts
  only RS256, issuer `https://<AUTH0_DOMAIN>/`, configured `AUTH0_AUDIENCE`, and tokens containing
  `exp`, `iss`, and `sub`. Missing, expired, wrong-audience, wrong-issuer, or invalid tokens return
  401. Success returns only `sub`, `email`, and `name`.
- Login return targets must start with one `/`, contain no backslash or control character, and not
  start with `//`; rejected targets return to `/`. Logout returns to the site's own origin.

### Explicitly excluded behavior

- Administrator UI, roles, and user-list behavior are absent. `/admin/dashboard` is not built;
  `/api/auth/admin-test` and `/api/admin/users` return `410 Gone`.
- Paid GPT/OpenAI refinement is absent. `ocr_engine=paddle-gpt` returns 422 and
  `POST /detect/refine` returns `410 Gone`, both before any provider call. Production has no
  `OPENAI_API_KEY`.
- Account-synchronized history, PostgreSQL, PDF input, staff-note transposition, object storage,
  multi-page input, and multi-replica operation are excluded.

## Data lifecycle and operational limits

- The backend decodes an admitted upload, uses a temporary file for OCR, and deletes that file when
  the request finishes. Images and detections remain only in the process cache for follow-up
  rendering. The cache is bounded to 20 entries and 80,000,000 total image pixels; LRU eviction or
  process restart removes them. There is no permanent image store.
- Detection IDs are volatile capabilities. A missing, evicted, or restart-lost ID returns 404 and
  the user must upload again. Keep exactly one backend replica until state is shared or requests
  are session-affine.
- The one-worker OCR executor admits at most two requests: one active and one queued. Further
  requests return 429 with `Retry-After: 5`; they must never form an unbounded queue.
- The one-worker rendering executor admits at most four requests and returns 429 with
  `Retry-After: 2` beyond that bound, so rendering cannot block health checks or grow an unlimited
  CPU queue.
- Vercel serves the UI and may collect its documented Analytics events. HF processes the upload and
  may retain infrastructure logs under the operator's account settings. Auth0 handles login.
  Sentry receives sampled errors/performance data only when configured; default PII, backend
  request bodies, local variables, and session replay are disabled. The linked privacy notice must
  stay consistent with these facts and record any provider-retention configuration used at release.

## Required release gates

### 1. Local and CI integrity

- `python -m pytest -q`, `npm run check`, `npm audit --audit-level=high`, and
  `pip-audit -r requirements.txt` pass from cleanly installed pinned dependencies.
- The root Docker image builds from `requirements.txt`, reports the pinned PaddleOCR version, and
  starts successfully. The root `Dockerfile` is the only backend deployment definition.
- GitHub branch protection requires the backend, frontend, and Docker CI jobs on the candidate SHA. No
  secret, `.env`, local artifact, or unrelated user change is included.

### 2. OCR correctness and candidate performance

The canonical regression corpus is every JSON file in `fixtures/labels` and its named image in
`fixtures/images`, frozen at the candidate SHA. The existing corpus has informed tuning, so it is a
regression guard rather than independent evidence of general accuracy.

Run `scripts/eval_ocr.py` from a Seoul client against a ready private HF canary on the same
`cpu-basic`, single-replica Docker/runtime configuration as production. Use `--engine paddle`, a
240-second request timeout, production Vercel Origin, `--render-check`, the production API or a
frozen production report as baseline, `--deployment-sha`, and `--report-json`. The script warms the
first sheet once, then measures every selected sheet sequentially once. Cold-start timing is
recorded separately and excluded from the warm aggregate.

- Per-sheet coverage is `|detected unique ∩ expected unique| / |expected unique|`.
- Per-sheet unique precision is `|detected unique ∩ expected unique| / |detected unique|`.
- Corpus scores are the unweighted arithmetic mean of those per-sheet scores, excluding labels
  marked `strict_unseen`. Coverage must be at least 98.06% and unique precision at least 88.90%.
- Candidate output must not reduce coverage, precision, or labeled occurrence recovery, and must
  not add a new extra chord, relative to the matching baseline image SHA.
- Warm wall-clock `/detect` times across all sheets must have arithmetic mean at most 80.0 seconds
  and population standard deviation at most 20.0 seconds. P90 and maximum are recorded but are not
  separate gates. A run with fewer than the entire canonical corpus cannot pass this gate.

The independent labeler supplies one external JSON label with `strict_unseen: true`, exact
`expected_chord_sequence`, total bounds equal to that sequence length, and the source image hash.
It is added using `--extra-label` after the label and image are frozen. It must achieve 100% unique
coverage and precision, exact occurrence counts and order, no missing hard target, and no
fixture-level regression. The independent reviewer also saves Replace and Above screenshots and
records zero missing, extra, or displaced occurrences.

### 3. Browser, UX, and accessibility

Record exact OS, browser, and device versions in the evidence. Test current stable Chrome and
Safari on desktop, current stable iOS Safari on a physical iPhone, and current stable Chrome on a
physical Android phone. The release passes only when each applicable environment completes the
public core journey and produces an openable PNG.

- A keyboard-only desktop user can choose a file, start detection, correct a chord, select capo
  frets 1 and 7, switch Replace/Above, and download, with visible focus throughout.
- Invalid, corrupt, animated, unsupported, over-20-MiB, and over-50-megapixel inputs show clear
  localized 4xx errors and no 500.
- Lighthouse accessibility, using the same recorded CLI version in mobile mode, scores at least 90
  on `/`, `/history`, `/privacy`, and `/terms`. Axe reports no `critical` violation on those pages.
- Slow, 429, missing detection ID, and backend failure states tell the user what happened and how to
  retry. No internal exception or configuration detail is shown.

### 4. Login, privacy, and security

- Production Auth0 login returns to the requested safe internal page, survives a reload, and logout
  clears the session. A real production access token passes `/api/auth/me`; no token and an invalid
  token return 401.
- Privacy and terms are linked in both languages and match the release configuration for image
  memory/temp handling, browser history and Auth0 storage, Vercel Analytics, HF logs, and Sentry.
- The deployed paid and administrator endpoints behave exactly as excluded above, and HF has no
  OpenAI or database secret.
- Runtime Python and Node dependency audits contain no applicable high or critical vulnerability.
  Any later advisory requires a new assessment; an exception must name the advisory, exposure,
  mitigation, owner, and expiry in this file.

### 5. Capacity and observability

- Run three simultaneous valid `/detect` requests, repeat the burst three times after the prior
  burst drains, and save status/latency results. Per burst, at most two requests are admitted; every
  excess request returns 429 within five seconds with `Retry-After`, admitted requests return no
  5xx within the 240-second client timeout, and every returned detection ID renders successfully.
- During the burst, `/health` responds within two seconds. Process memory stays within the HF
  replica limit and returns near its post-warm baseline after cache eviction is exercised.
- Staging sends a deliberate backend exception and frontend exception to Sentry and both arrive
  without image bodies, tokens, email, or local variables. A 5xx alert fires on one event within a
  five-minute window. A `/detect` p95 latency alert uses an 80-second threshold over 15 minutes with
  at least three sampled transactions. Alert delivery to the product owner is verified.

### 6. Canary, production, and rollback

- The exact candidate passes all preceding gates in the private HF canary and paired Vercel preview.
- Before promotion, record the candidate GitHub SHA, Vercel deployment ID/source SHA, HF runtime
  SHA/source SHA, non-secret environment snapshot, and previous known-good Vercel/HF IDs.
- Production smoke covers health, CORS preflight, core journey, Korean/English, login/logout,
  `/api/auth/me`, privacy/terms, retired GPT, and retired admin behavior.
- Perform and time one canary rollback rehearsal using a forward revert/runtime snapshot and the
  prior frontend deployment. Health, CORS, detect, and render must recover within 15 minutes.

## Execution order

1. Finish local implementation, automated checks, security audits, and Docker parity.
2. Freeze the independent unseen label and assign its reviewer before running either system.
3. Create the candidate SHA, pass required GitHub checks, and deploy that exact SHA to private HF
   canary plus Vercel preview.
4. Run corpus/unseen OCR, real-browser accessibility, load, Auth0, Sentry, and rollback gates.
5. Record identities and evidence below, obtain the product owner's go decision, promote the exact
   candidate, and complete production smoke tests.

## Candidate evidence ledger

Status values are `PASS`, `FAIL`, `BLOCKED`, or `PENDING`. A local pass is not a deployment pass.

| Gate | Status | Evidence or blocker |
| --- | --- | --- |
| V1 scope retirement and upload safety | PASS (local) | Automated API tests; deployment smoke pending |
| Local backend/frontend/security checks | PASS (working tree) | 409 passed, 11 skipped from a clean tracked-only export; frontend check and both dependency audits pass; [`ISSUE_10_RC_EVIDENCE.md`](ISSUE_10_RC_EVIDENCE.md); exact candidate SHA rerun still required |
| GitHub required CI | PENDING | Candidate SHA not created |
| Docker build and dependency parity | BLOCKED | Candidate image not built; the audit workstation has no container runtime, so the build, version assertion, and startup step are all unverified ([`ISSUE_10_RC_EVIDENCE.md`](ISSUE_10_RC_EVIDENCE.md)) |
| OCR regression corpus | BLOCKED | Canary not deployed; candidate baseline report not yet recorded |
| Independent unseen sheet | FAIL | `IMG＿7710.png` was frozen and independently labeled before output; the local candidate detected 56/60 and failed exact count/order. This sheet is now a development sample, so a different unseen sheet is required after correction. |
| Browser and accessibility | PASS (local automated) | Lighthouse 13.4.1 mobile: 100 on all four pages; staging and physical-device evidence required |
| Production Auth0 login | PENDING | Production configuration and live token required |
| Capacity | PENDING | Canary load report required |
| Sentry and alerts | PENDING | DSNs, alert rules, and delivery test required |
| Rollback rehearsal | PENDING | Exact canary candidate required |
| Production identities and smoke | PENDING | All pre-production gates must pass first |

Live baseline rechecked 2026-09-16: the existing deployment still lacks privacy/terms, exposes the
administrator page, and returns old database-related 503 responses from identity/administrator
APIs. Those results confirm that no local V1 change has been promoted yet.

Independent attempt 1 was frozen at image SHA
`4ceeb3b23ed2025d3a9c3ccd93e808bf0c0af494e3e7e52f43d77fc8958c30b5` and visually labeled by
an isolated same-model reviewer without repository or OCR-output access. The local candidate found
56 of the expected 60 occurrences and failed exact count and order. The labeling prompt also used
parenthesized spellings where the service canonical form removes parentheses; correcting that
serialization alone cannot repair the remaining missing, extra, and displaced occurrences. The
result is a genuine failed gate, not release evidence. The report is
`/private/tmp/capomatic-v1-independent-local.json` for this workstation session.

The official HF MCP confirmed that `juka526/capomatic` is a Docker Space but exposes no runtime,
hardware, variable, or secret inspection operation. The official Vercel MCP authentication sees
zero teams/projects and therefore cannot reach Capomatic. Reauthorize it against the owning account
or use an approved read-only project token before treating Vercel configuration as verified.

The release remains **NO-GO** until every row is `PASS` and the product owner records the dated
go decision here.
