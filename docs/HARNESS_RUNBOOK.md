# Harness 0.2 operator runbook

The experimental build worktree in this checkout is `/Users/juahnkim/transchord/.harness-02`, branch `experiment/capomatic-harness-02-herdr`. Use Python 3.12+. A minimal isolated setup for mock execution is:

```bash
cd /Users/juahnkim/transchord/.harness-02
python -m venv .venv
source .venv/bin/activate
python -m pip install -r harness/requirements.txt pytest
```

For the music regression gates, also install the pinned application dependencies from `requirements.txt` into that environment. The mock does not load OCR or music models.

```bash
python -m harness herdr-audit
python -m harness doctor
python -m harness plan
python -m harness start --mode herdr-mock --max-tasks 2
python -m harness status
python -m harness report
python -m pytest tests/harness -q
```

`herdr-audit` inspects installed CLI help/schema, local integration versions and selected configuration metadata without changing settings. Outside Herdr it does not inspect sockets, panes, active sessions or the plugin inventory. To complete those checks, launch this Controller inside a Herdr-managed pane and rerun the audit. Do not export `HERDR_ENV=1` to imitate a managed pane or point at another user's focused session.

Global `--repo PATH --state-dir PATH` precedes the subcommand. Runtime state defaults to `.harness-state/` and stays outside `/private/tmp`. Its own `.gitignore` protects runtime artifacts from accidental Git staging. Back up SQLite, worktrees, snapshots, artifacts and evidence together. Reports contain local paths and research text; inspect before sharing.

## Expected mock outcome

The two-task demonstration prints `state: COMPLETED`, `mode: herdr-mock`. The report contains two ACCEPTED research tasks, two attempts per task, four simulated Claude reviews and two checkpoint commits. Twelve role dispatches are COLLECTED: builder, reviewer and verifier for each attempt. The next task's prompt includes the previous accepted checkpoint and actual gate results. Completing this bounded demonstration does not establish source completeness or live readiness.

The `id` printed by `start` is the run ID; `python -m harness status` lists it again. `STATE_DIR` means the absolute `--state-dir` value (default: the checkout's `.harness-state/`). The SQLite file is `STATE_DIR/state.sqlite3`. Dispatch IDs appear in report events with kind `HERDR_QUEUED` and in the database queue. `RUN-TASK` is the run ID plus task ID, joined with a hyphen.

Check `report.runs[].state`, `report.tasks[].status/attempts/checkpoint`, and count `report.events[].kind` values REVIEWING and REVISING. Inspect COLLECTED rows in SQLite's `herdr_dispatches` for role dispatch counts.

Inspect `STATE_DIR/artifacts/DISPATCH_ID/{manifest,payload,receipt}.json`, `STATE_DIR/evidence/RUN-TASK/`, the `herdr_resources` mappings and `herdr_dispatches` queue in SQLite. Mock workspaces and agents are fake; detached/experimental worktree commits and preservation checks are real. No paid CLI or user's terminal is controlled by mock mode. `--mode mock` retains the local 0.1 compatibility path.

The [GT-16C example](harness02/gt16c-dispatch.json) is an explicitly selected, text-only research readiness task delivered through the fake Herdr API. It does not authorize adaptive engraving edits, source promotion or an assumed sequential next GT milestone. Reproduce it with a fresh state directory using this separate module command (it has no subcommand/global-option split):

```bash
python -m harness.example_gt16c --repo "$PWD" --state-dir "$PWD/.harness-state/gt16c-example"
```

## Controls and recovery

```bash
python -m harness pause --run-id ID
python -m harness resume --run-id ID
python -m harness stop --run-id ID
python -m harness report --run-id ID
```

Use the run ID from `start` in place of `ID`. Pause/stop persists in SQLite and prevents subsequent mutations/checkpoints. An already submitted Herdr request may settle or time out; pause is cooperative and does not kill its agent or cancel an in-flight tool call. Legacy local mock mode checks controls at task boundaries. Unqualified live process cancellation remains a pilot blocker. Stop cannot be reversed. The single-controller filesystem lock prevents duplicate startup. The OS releases the lock on exit; deleting the lock file is not recovery.

On disconnect, do not repeat a prompt based on an idle/done badge. Preserve the QUEUED request and action receipt. Reconnect to the same inherited server context and reconcile exact native session references, cwd and resource ownership. Missing processes, a shell fallback or changed session identities require owner review. Never restart the main Herdr server for a test; restart scenarios are fault-injected in the fake service.

An interrupted STARTED mutation or incomplete Controller phase remains BLOCKED. Record the run/task/action IDs, dispatch manifest, worktree HEAD, task trailer, native session identity, receipt hashes and gate results in a private incident record. A Git commit may have completed before its SQLite receipt. Do not delete action keys or resend it. There is no force-unblock command. The project owner who requested this run receives the private incident record. Start a new bounded run only after that owner records a decision identifying any accepted checkpoint, abandoned/retained work, remaining processes and the fresh task permitted next. This is clearance for a new bounded run, never permission to delete old keys or replay an uncertain mutation.

Cleanup operates only on resources created and receipted for that run. It never uses group close, deletes a branch, force-removes a worktree, stops a server, or closes the caller's Controller pane. Evidence/worktrees are retained for inspection. An unowned resource with a matching label is not adopted.

## Owner approvals

The [packet](../harness/schemas/packet.json) and [response](../harness/schemas/approval.json) contracts and genuine interactive-owner requirement are unchanged. Choose candidate IDs from the actual source inventory and hash exact source images with `shasum -a 256`. Keep the review directory source-only; the program checks hashes but cannot infer image subject matter.

```bash
python -m harness approvals --enqueue packet.json --source-root /durable/source-packet
python -m harness approve --response response.json --evidence owner-message.txt --source-root /durable/source-packet
```

The owner must inspect the exact packet, supply an attributable genuine response and retype its hash in an interactive terminal. Neither Herdr nor agent agreement can approve source. Pending owner tasks remain withheld while independent permitted tasks may proceed. With no ready task, the run stays WAITING_OWNER_APPROVAL. Recording a response does not enlarge worker permissions or automatically promote OMR evidence.

## Real pilot and Level 3

`start --mode herdr-pilot --max-tasks 1` records admission blockers and dispatches no worker. This request did not authorize a real pilot. Do not bypass the gate, copy production credentials, alter shared hooks, install plugins or enable automatic resume as a substitute for qualified containment. The live verifier command also refuses execution.

Before requesting a real pilot, resolve every item in [security readiness](HARNESS_02_SECURITY.md), including OS-enforced execution and socket isolation, separate credentials, hard-cost enforcement, restored-process restrictions and the MuseScore skip. Herdr does not provide those security guarantees. There is no Level 3 activation command in 0.2.
