# Harness 0.1 runbook

In this checkout the experimental worktree is `/Users/juahnkim/transchord/.harness-build` on branch `experiment/capomatic-autonomous-harness`. Run from that worktree with Python 3.12+ and `python -m pip install -r harness/requirements.txt`. `python -m harness` is the equivalent of the requested `harness` executable. The application dependencies in the repository requirements are also required for real research gates.

```bash
python -m harness doctor
python -m harness plan
python -m harness start --mode mock --max-tasks 2
python -m harness status
python -m harness report
python -m harness approvals
python -m pytest tests/harness -q
```

Use global `--repo PATH --state-dir PATH` before the subcommand to select paths. State must remain on durable local storage outside temporary directories. The default `.harness-state/` is gitignored; back it up together with its worktrees, snapshots and evidence. Never commit credentials, runtime databases, worker sessions or owner response text into a public repository.

`start` prints the run ID. Use `pause --run-id ID`, `resume --run-id ID` and `stop --run-id ID`. Controls persist in SQLite. The process watchdog supports interruption polling; mock actions check controls at task boundaries. Stop is terminal and cannot be reversed. Resume continues only at safe boundaries. An ambiguous interrupted action stays BLOCKED and must not be replayed. A completed run remains unchanged on resume.

The mock creates detached research checkpoint commits and never pushes them. The two-task demonstration intentionally revises each task once and stops. `start --mode pilot --max-tasks 1` saves exact bootstrap blockers and launches no paid worker in 0.1. Do not remove the code-level live gate to force a pilot. Level 3 activation has no CLI entry point.

A successful mock start prints `state: COMPLETED` and `mode: mock`. The report must show two ACCEPTED tasks, two attempts per task, four REVIEWING transitions and two research checkpoints. Evidence is under `STATE_DIR/evidence/RUN-TASK/`; inspect `prompt.txt`, `revision-prompt.txt`, `review-1.json`, `review-2.json`, `frozen.json` and `verification.json`. `doctor` prints installed CLI versions, required flag availability, credential-presence booleans and exact pilot blockers. It never prints a credential value.

Record `git rev-parse HEAD` and `git status --porcelain` in the primary checkout before and after a demonstration to verify it stayed unchanged. Checkpoints exist only in detached worktrees under `STATE_DIR/worktrees/`.

## Owner review queue

Choose a unique request ID, such as a UUID, and candidate IDs from the actual source inventory; never derive IDs from an assumed next GT number. Compute each source file hash with `shasum -a 256 PATH`. The approval queue reports the canonical packet hash after enqueueing. Create a packet matching [packet.json](../harness/schemas/packet.json). Bind the exact source manifest hashes, source image paths, candidate IDs, proposed interpretations, null answer/correction fields and explicitly withheld items. Keep packets source-only; do not include target transposition references. Paths are relative to an owner-selected source-only directory. The controller checks exact bytes and image membership, but cannot infer whether an image depicts a source or target; the owner must inspect the packet.

```bash
python -m harness approvals --enqueue packet.json --source-root /durable/source-only-packet
python -m harness approve --response response.json --evidence owner-message.txt --source-root /durable/source-only-packet
```

The response must match [approval.json](../harness/schemas/approval.json), including request ID, exact packet hash, candidate IDs, attributable owner identity, actual response text and SHA-256 of the original response file. Approval requires an interactive owner terminal and retyping the packet hash. Files alone are not evidence of authenticity: the owner terminal is the trust root. Agents must never invoke this command as an owner. Repeating the identical response is idempotent; replacing it requires a new packet. Corrections do not promote candidates automatically. Worker permissions remain unchanged after approval.

## Recovery and rollback

Stop the controller before copying or inspecting SQLite and back up its directory. An active controller owns `controller.lock`. Read `report`, action status and evidence before taking further action. A STARTED action can mean a worker or commit finished without saving its receipt. Inspect the detached worktree's Git log and run/task trailer; do not delete the key and rerun. Release 0.1 deliberately has no automatic force-unblock or action-reset command. For reconciliation, save a local incident record containing the run/task/action keys, original phase, process receipts, worktree HEAD, commit trailer, changed-file list and gate result hashes. If a checkpoint exists but its receipt is absent, preserve it and mark the incident as requiring owner review; do not repeat or cherry-pick it automatically. If an implementation result is uncertain, retain the worktree and investigate remaining processes before beginning another run. Keep this incident record outside public Git. This release does not provide a command to repair the old run's state. Start a new bounded run only after the owner has reconciled the evidence. The OS releases an `fcntl` lock when its holder exits; the presence of `controller.lock` alone is not a stale lock, and deleting it can permit competing controllers. No changes land in the primary checkout, and no production rollback is needed for these research-only commits.

Reports contain local paths and research text; review before sharing. The committed validation summary excludes credential values and private owner responses.
