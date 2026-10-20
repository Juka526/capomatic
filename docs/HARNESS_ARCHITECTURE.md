# Capomatic Harness 0.2 architecture

The Python Controller owns tasks, permissions, budgets, state transitions, source provenance, approvals and verified checkpoints. Herdr owns terminals, project/worktree presentation, named agents, prompt submission, lifecycle observation and native session restoration. The default CLI start is a complete **Herdr-mocked** run. Real workers and Level 3 remain disabled.

The implementation starts at `bc9db2ca8decd1b900107905a4c4984907a3f330`. The [security policy](../harness/policy.json) is unchanged from 0.1. Existing [0.1 validation](HARNESS_VALIDATION.md) and historical evidence are retained. Current execution evidence is in [Harness 0.2 validation](HARNESS_02_VALIDATION.md).

## Reused and new responsibilities

| Component | Responsibility |
|---|---|
| Herdr workspace/worktree APIs | Workspace creation and reuse; worktree creation and presentation; no second Git worktree creation by the native adapter |
| Herdr agent APIs | Start named Codex/Claude in existing panes, submit prompts, observe lifecycle; no PTY or screen scraper in Python |
| Herdr native session references | Reassociate resumed sessions; never infer that an in-flight tool or process survived |
| Existing Controller/planner | Bounded scheduling, immutable policy validation, revision prompts, remaining dependencies, accepted checkpoints and gate results |
| Existing SQLite/approvals/budget | Durable workflow authority, transaction boundaries, owner-response binding, cost reservations and deadlines |
| Existing snapshot/verifier/checkpoint code | Independent file checks, source provenance, V3/V4 gates and research-only commits |
| `herdr_audit.py` | Local version/schema/help and integration/config audit; live session audit only inside inherited Herdr context |
| `herdr_adapter.py` | JSON transport, installed-protocol qualification, role mappings, named startup, prompt receipts, notifications and owned-resource cleanup |
| `herdr_runtime.py` | Controller-authorized role dispatch, outbox selection, structured results, snapshot separation and durable queue |
| `artifacts.py` | Strict run/task/dispatch/base/input/output/evidence binding; stale, malformed and missing result rejection |
| `herdr_mock.py` | Explicit fake Herdr service, fake agents and restart/disconnection fault injection; isolated Git worktrees are real |

No live socket is contacted without inherited `HERDR_ENV=1` and `HERDR_SOCKET_PATH`. The CLI transport validates protocol 22 and required installed help syntax. Unsupported versions fail closed until requalified; it does not update Herdr or agent settings. The checked-in method inventory is a small extraction from the installed 0.9.0 schema, not a replacement API specification.

## Roles and dispatch

CONTROLLER is the current caller pane in a future admitted native run; it is never owned for cleanup. In a mock it has a simulated workspace. Each BUILDER has a Herdr worktree workspace. Each REVIEWER gets a separate minimal readonly snapshot containing only policy-checked task files, without repository source, owner messages, credentials or `.git`. Each VERIFIER has a different complete readonly candidate snapshot. Several workspaces make different filesystem roots explicit rather than starting the reviewer in the builder's checkout.

Every role dispatch requires the corresponding persisted Controller phase. The Controller writes a durable QUEUED request before agent prompt delivery, with an expected outbox chosen by the Controller. A manifest binds run ID, task ID, dispatch ID, role, base SHA, input SHA-256, output hashes, payload hash, completion receipt and simulated/real classification. JSON artifacts, not terminal text, are collected. Herdr `idle`, `done`, `blocked` and `unknown` observations never constitute PASS.

In the mock, the fake service manages workspaces, worktrees and lifecycle responses. Synthetic builder/reviewer artifacts are explicitly marked simulated. The deterministic file/policy/whitespace gates execute in the Python Controller against the verifier snapshot; the mock verifier pane records its command without executing a terminal process. The live verifier entry point refuses execution pending qualification. There is no claim of independent pane verification or real model review from this demonstration.

## Persistence and recovery

SQLite gains `herdr_resources` and `herdr_dispatches` through additive `CREATE TABLE IF NOT EXISTS` migration. Existing 0.1 runs and approvals remain readable. Resource records bind exact returned workspace, terminal and pane IDs, cwd, native session identity and inherited server context. Agent start and prompt mutations have durable action keys and request hashes. A key cannot be reused for different prompt text.

Reconnect is read-only reconciliation. Exact terminal identity can recover a disconnected live pane; after a simulated restart, exact native session identity plus workspace and cwd can map a new pane ID. Missing, duplicated, changed or stale identities block. No shell fallback automatically restarts a lost task. A mutation whose response was lost stays uncertain and is never blindly resent, even if Herdr says the agent is ready. An interrupted Controller phase stays BLOCKED for owner reconciliation.

Detach/reattach and native resume are delegated to Herdr. The harness does not stop, replace or restart the user's server, enable handoff, replay screens or install hooks. Native conversation restoration is insufficient to prove the original OS sandbox, credentials or cost limits survived. Those properties require separate qualification before any real pilot.

The existing worktree manager remains the local mock compatibility backend and snapshot/checkpoint utility. Only the fake Herdr service uses direct Git worktree commands in tests; native provisioning uses Herdr. There is no runtime remote push, merge or deployment.
