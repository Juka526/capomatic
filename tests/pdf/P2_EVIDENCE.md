# V2-2 P2 tester evidence (cm2-test)

Product code was not changed. Mutations were temporary, restored with `git checkout`, and checked with a clean `git diff -- backend`.

## Final re-verification at 7aa0353 (supersedes 0de7a05)
- `env -i HOME=$HOME PATH=/usr/bin:/bin PDF_INDEPENDENT_PYTHON=/opt/anaconda3/bin/python .venv/bin/python -m pytest -p no:cacheprovider -q tests/pdf tests/test_sentry_privacy.py` → **95 passed, 0 skipped** at 7aa0353 (the pypdf reader test ran).
- `tests/pdf/conftest.py` blocks sockets. The known positive `test_network_blocker_catches_known_attempt` passes.
- I did not rerun the broad suite: no new failure justified it.

### Two earlier tester errors, corrected (same invariants, stricter)
- **`test_cancel_keeps_slot_and_permit_until_native_call_returns`**
  - The old version called `finish()` before B ran, then expected 3 calls.
  - It now uses a controlled schedule. Known positive: A's running page holds exactly one permit. After DELETE, A is a 404 but stays live.
  - B reserves, but starts no page and holds no permit while A runs. C gets 429 before its body is read (≤64 B).
  - After A's native call returns, A is freed: one page, no result, page 1 still pending.
  - B reaches `needs_review` with 2/2 pages, so calls are exactly 3. Only then does C get 202.
- **`test_ttl_sweep_does_not_free_a_slot_still_validating`**
  - The old version double-counted.
  - It now counts unique holder ids (`_live` ∪ jobs with `running>0`) against a latched native inspect.
  - On expiry, A is removed with `running==1` and stays in `_live`. B gets 202. C gets 429 before reading. There are at most 2 holders, and A is among them.
  - After the latch releases, A's request gets 404 and A is freed. D gets 202 only after that callback.

### New lifecycle/privacy probes (all pass)
- **Same-turn reservations after upload expiry (7aa0353 counter semantics):**
  - A job's slot is freed only when `running == 0` and `receiving == 0`, and the job is removed or failed.
  - In one loop turn after A's upload expires: B's `reserve` sweeps A, but A is still `receiving == 1`, so A keeps its slot. B gets the second slot. C's `reserve` raises 429 `pdf_busy` before any body read.
  - The unique holder ids are exactly {A, B}. This is the T5 positive: the detector sees A through `receiving`.
  - A's request then stops on its own as 404 without its body being released. Then `receiving == 0`, A is out of `_live`, and A's session is freed (the negative after actual completion).
  - A reads 0 bytes after expiry, and C gets 202 only after that.
  - No transient exception remains: at every observed point there are at most 2 holders.
- **Shutdown timeout and loop close:**
  - While the native call is latched, the slot and one permit stay held (known positive).
  - After the worker returns with the loop already closed, its own callback frees the job: data, session and permit.
  - Exactly 1 detect call, so no new pages.
- **Tombstones:** 30 failing jobs leave ≤ 8 addressable, all content-free (no title, 0 chords). The state `failed` is terminal. Timer bound: still 200 at 119 s (positive), 404 at 121 s.
- **Sentry, real SDK and local transport:**
  - With scrubbers off, the same search finds the sentinel in `contexts.trace` span data and description, and in the unmatched-route transaction name (known positives).
  - With scrubbers on, trace keys are only ids/op/status, and the name is `unknown`.
  - Malformed metadata (`capture_event` with non-string transaction, a sentinel status/span_id, tags, extra, request, user) leaks nothing.
  - With `app=None` (import-time) the event is dropped, not leaked.
  - `op`/`status` pass a `[a-z._]` regex. In app flows they are SDK constants (`http.server`, …). I did not assert any hypothetical non-app channel.

## T2
- **7aa0353:** `jobs.py` from `0de7a05` makes `test_same_turn_reservations_after_upload_expiry` fail (`DID NOT RAISE JobError`: C took a third slot while A's buffer still existed). Restored, it passes. `git diff -- backend` is clean.
- **Pre-fix:** `jobs.py` and `main.py` from `f631111` give 13 failed, 82 passed. Restored `0de7a05` gives 95 passed. The failures are the cancel, fairness, failure-cleanup, upload/validate TTL, task-cancel, shutdown, same-turn, tombstone, span-data, route-name, malformed and no-routes tests.
- **New-guard mutations:** each targeted test fails.

| Guard removed | Result |
|---|---|
| `_page_busy` | 2 failed |
| Tombstone cap | 1 failed |
| `receive` removed-check | 2 failed |
| Trace allowlist | 1 failed |
| Route-name filter | 1 failed |
| `running==0` | 4 failed |
| `_fail` title clearing | 1 failed |
- **f631111 round:** the 9 guard mutations and the Sentry `b6f4cd5` before/after all failed their target tests. The post-result cancel check is an equivalent mutant.

## T1 sources
- https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Future.cancel (a running call cannot be cancelled)
- https://docs.sentry.io/platforms/python/configuration/filtering/ (`before_send`, `before_send_transaction`, `before_breadcrumb`)
- Envelope shapes were observed with the installed sentry-sdk 2.69.1.

## NOT RUN
- Real Paddle, Linux/HF CPU p95, fairness and RSS, the real 30 s shutdown wait (simulated at 0.1 s), frontend Sentry, and the iPad.
- Single-PDF fairness was verified only with a stub (an image request admitted while a PDF page runs).
