# Harness 0.1 architecture

Harness 0.1 is a bounded, mocked controller with live CLI adapters and a fail-closed pilot admission gate. It is not an operational autonomous development system. `start --mode pilot` records blockers without launching either paid worker. No command activates Level 3.

The baseline is `6cc1dd558d13b7c56799c0cfda49fafbaca8ccd4`. The exact baseline file hashes are in [baseline-sha256.json](harness/baseline-sha256.json). The canonical runtime permissions and limits are [policy.json](../harness/policy.json). Owner-confirmed scope and withheld content are preserved from [GT-16B](V4_GT16B_CONFIRMED_FOURTH_SYSTEM.md); neither mock agreement nor review agreement creates source verification.

## Components

| Module | Responsibility |
|---|---|
| `controller.py` | Bounded scheduling, phase transitions, gate orchestration, recovery |
| `state.py` | SQLite WAL/FULL transactions, action keys, local process lock, control flags, event journal |
| `reports.py` | Run/event report projection with owner response text excluded |
| `planner.py` | Two controller-defined research tasks and complete prompts using accepted checkpoints, actual results, blockers, approved scope, remaining time and reservations |
| `policy.py`, `policy.json` | Strict text-only research path permissions, dependency checks, provenance and sensitive-content rejection |
| `schemas.py`, `schemas/` | JSON Schema validation for tasks, implementation responses, reviews, source packets and owner responses |
| `codex.py` | Argument-array `codex exec`, explicit workspace-write sandbox, ephemeral session and structured result |
| `claude.py` | Separate `claude -p` review, read tools only, no shell/write tools, no MCP, restricted settings and structured review |
| `containment.py`, `doctor.py` | Credential minimization, capability audit and hard denial of unqualified live dispatch |
| `process.py`, `budget.py` | Process-group timeout/cancellation, bounded output, control polling and worst-case cost reservations |
| `verify.py` | Actual controller-owned subprocess gates and file hashes, no reliance on agent test claims |
| `gitwork.py` | Detached worktrees, separate readonly snapshots, byte manifests and research checkpoint commits |
| `approvals.py` | Source-only packets and terminal-attested owner responses bound to exact hashes |

## State and evidence

The normal lifecycle is `PLANNING → POLICY_CHECK → IMPLEMENTING → REVIEWING → VERIFYING → CHECKPOINTING → NEXT_TASK`. A failed gate enters `REVISING → IMPLEMENTING` within the attempt bound. Owner-dependent tasks enter `WAITING_OWNER_APPROVAL`; the scheduler may consider unrelated permitted tasks. Errors can enter `BLOCKED`, `FAILED` or `BUDGET_EXCEEDED`. Exhausting the bounded configured demonstration enters `COMPLETED`; that means the mock demonstration completed, never musical or operational readiness.

Durable SQLite state, worktrees, snapshots, prompts and gate evidence live under `.harness-state/`, outside `/private/tmp`. A controller lock permits one active builder. Unique action keys claim dispatches and commits before execution. A finished action is never dispatched again. After a crash, an uncertain started action or interrupted phase blocks for manual reconciliation. This conservatively prevents duplicate operations; 0.1 does not automatically reconcile a commit that finished just before its SQLite receipt was saved. Mock checkpoint commits remain detached and are identified by an exact run/task trailer. There is no runtime push, merge or deployment implementation.

The mock deliberately injects one verification failure per task. The second implementation adds the requested blocker text. A revision prompt records gate feedback. Mock review and preservation evidence is labeled simulated. Actual worktree creation, hashes, schema checks, whitespace checks, commits and SQLite recovery are exercised. Synthetic cost reservations test arithmetic; they are not API usage measurements.

## Trust boundaries

The controller and its policy are outside the autonomous edit allowlist. Workers may propose only bounded `.md` or `.txt` research additions under `research/harness_tasks/`. Existing tracked bytes, production, original PDFs, protected masks, source evidence and historical outputs are frozen. No production or rendering changes are admitted, so alpha collision/clipping gates are inapplicable to the 0.1 task class. Expanding to image or rendering tasks requires controller-defined actual-alpha gates and a reviewed policy release.

Repository text is untrusted data in the prompt. A prompt instruction is not containment. Independent schema, path, operation, byte-preservation and approval checks reject authority expansion. A reviewer gets a separate byte snapshot without `.git`; POSIX readonly bits and post-review hashes detect writes but do not stop a same-UID adversary from chmod. The live gate therefore remains closed until an OS-enforced launcher is independently qualified. The verifier currently runs trusted unchanged tests; an isolated OS verifier launch is also unqualified.

## Deferred live execution

The adapters are implemented and their argument arrays can be tested with fake CLI processes. They are deliberately not reachable from an admitted live task in 0.1. Required work before a live pilot: qualify OS-enforced builder/reviewer/verifier containment; isolate per-worker homes and selected API credentials; enforce a hard Codex cost cap through a metered gateway; validate actual process receipts and independent review on a harmless task; verify interruption recovery against real process trees; then obtain owner authorization for the tested configuration. Installed CLI flags alone do not establish any of these properties.
