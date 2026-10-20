# Harness 0.2 validation

Verdict: **Herdr-mocked orchestration validated; real pilot blocked; Level 3 disabled.** No paid agent, active Herdr pane, socket, server lifecycle command or plugin installation was used in this session. The local Herdr installation and configuration were inspected without changing agent settings.

## Recorded checks

| Check | Actual result | Evidence |
|---|---|---|
| Harness tests, including local Git/process integration and fake Herdr orchestration | 72 passed | [harness-tests.txt](harness02/harness-tests.txt) |
| Unchanged V4 suite and V3 semantic/evaluation guards, 43 test files | 652 passed, 1 existing skip | [research-gates.txt](harness02/research-gates.txt) |
| Existing skip | MuseScore absent; not waived | `tests/test_omr_v3_gate.py:190` |
| Original source baseline | 620 tracked file hashes unchanged | [preservation-audit.json](harness02/preservation-audit.json) |
| Approved source packet and historical outputs | Packet hashes match; 49 historical artifact hashes match | Same audit |
| Security policy and user agent configuration | Byte-identical to starting policy and audited settings | Same audit |
| Durable Herdr-mocked demonstration | 2 ACCEPTED tasks, 2 revisions, 4 simulated reviews, 12 COLLECTED role dispatches | [mock-result.json](harness02/mock-result.json) |
| Completed Controller restart | All 39 action records unchanged; no repeat execution | Same mock result |
| Explicit GT-16C example | Mock research note only; completed | [gt16c-dispatch.json](harness02/gt16c-dispatch.json) |
| Pilot admission | BLOCKED; zero worker/Herdr dispatches | [pilot-admission.json](harness02/pilot-admission.json) |

Research tests used Python 3.12.2 with the isolated music21 9.9.1/NumPy 1.26.4 validation dependencies retained from Harness 0.1 at `.harness-build/.harness-state/validation-deps/`. No production dependency or test skip was changed. Existing V3/V4 test files are unchanged. MuseScore was absent both from PATH and `/Applications`.

## Herdr and configuration audit

The installed CLI is **Herdr 0.9.0**, API protocol **22**, schema version **1**. Codex is **0.163.0**, Claude Code **2.1.300**. `herdr integration status` reports Codex hook **v8** and Claude hook **v9**, current relative to the installed binary. The [audit JSON](harness02/herdr-audit.json) records the exact schema hash, installed command help and selected settings metadata without credential values or hook command bodies.

Supported installed surfaces include workspace create/list/get/close, worktree create/open/list/remove, pane current/list/get/run, agent start/get/prompt/wait, notifications and plugin actions/panes/logs. JSON responses carry opaque IDs and optional native session references. These are installed **capabilities**, not proof they were exercised against a running server.

`HERDR_ENV` is absent. The installed [Herdr skill](https://herdr.dev/docs/agent-skill/) forbids inspecting or controlling a focused live session from outside Herdr. Active server version/session, socket connectivity, actual live pane/agent APIs, plugin inventory and native restore execution therefore remain unverified. No environment variable was forged and no server was started or stopped to bypass that restriction.

Official pages read: [overview](https://herdr.dev/docs/), [CLI](https://herdr.dev/docs/cli-reference/), [automation](https://herdr.dev/docs/agent-automation/), [integrations](https://herdr.dev/docs/integrations/), [session state](https://herdr.dev/docs/session-state/), [agent skill](https://herdr.dev/docs/agent-skill/) and [plugins](https://herdr.dev/docs/plugins/). Online documentation is newer than the installed release: for example, it describes Claude integration v10 and plugin-update commands not present in local help. No undocumented local command was assumed or installed.

## Fault injection and trust boundaries

New tests cover named provisioning and non-adoption of user resources; agent startup, prompt delivery and lifecycle; different prompt text under the same idempotency key; lost receipts after server-side delivery; disconnect/reconnect; new opaque pane IDs after simulated restart with an exact native session; rejection of lost/changed native identity; missing/malformed/stale manifests; task/base/input/output hash mismatch; artifact tampering; duplicate Controller startup; phase authorization; pause/deadline handling; immutable source corruption before reviewer startup; minimal reviewer inputs; and owner-dependent tasks that remain WAITING_OWNER_APPROVAL without dispatch.

Existing tests cover budget boundaries, timeout process-group teardown, policy/path/symlink protection, source promotion rejection, review snapshot mutation detection, approval-packet mismatch, owner terminal attestation and completed-run idempotency. POSIX readonly bits and hash comparison are tested; actual same-UID OS write denial is **not** established. Live worker starts fail closed before launch.

The fake Herdr service implements topology and lifecycle JSON; its Git worktrees/commits are real. Fake model outputs and receipts remain marked simulated. The mock verifier command is recorded but not run in a terminal; Controller-owned deterministic gates run directly against a separate verifier snapshot. A Herdr badge or reported result never substitutes for those gates.

## Independence and readiness

Mock builder/reviewer agreement is not independent correctness evidence. The test designer also controls the fake responses and injected failure. The claim is limited to orchestration, actual file gates and conservative recovery. The unchanged music tests and SHA checks supply separate regression/preservation evidence, not new optical ground truth. Genuine Claude review, native artifact capture, OS containment, hard spend enforcement and real process recovery require a bounded real pilot after explicit authorization.

The remaining blockers are detailed in [security readiness](HARNESS_02_SECURITY.md). In particular, native conversation resume does not establish restored process limits, and passing the full Herdr socket to a worker would expose the Controller's terminal control plane. No real pilot was authorized or attempted. No merge, deployment, automatic push from the Controller or Level 3 execution occurred.

A fresh context-free reader reviewed the operator runbook. Setup commands, run-ID discovery, evidence/report field locations, example invocation, pause semantics and owner incident-clearance steps were clarified from its findings. A consistency audit kept the unchanged policy canonical and the historical 0.1 validation separate. No portability claim or cross-platform launcher qualification is made.
