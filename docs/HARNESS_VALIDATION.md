# Harness 0.1 validation

Verdict: the bounded mock controller is validated; real worker dispatch and Level 3 activation are blocked. No paid Codex or Claude task was invoked. No source, production file, protected mask, original PDF or historical output was changed.

## Executed checks

| Check | Result | Evidence |
|---|---|---|
| Harness unit, synthetic and local Git/process integration tests | 44 passed | `python -m pytest tests/harness -q` |
| Existing V4 suite and unchanged V3 semantic/evaluation guards, 43 test files | 652 passed, 1 existing skip | [research-gates.txt](harness/research-gates.txt) |
| Existing skipped V3 fast-path test | MuseScore absent; not waived | `tests/test_omr_v3_gate.py:190` |
| Exact baseline tracked bytes | 620 files unchanged | [preservation-audit.json](harness/preservation-audit.json), [baseline-sha256.json](harness/baseline-sha256.json) |
| GT-16B approved packet | All bound source hashes match | [preservation-audit.json](harness/preservation-audit.json) |
| Historical rendered artifacts listed in validation records | 49 hashes match | [preservation-audit.json](harness/preservation-audit.json) |
| Two-task durable mock | COMPLETED, two revisions, four simulated reviews, two detached commits | [mock-result.json](harness/mock-result.json) |
| Pilot admission | BLOCKED; zero worker dispatches | [pilot-result.json](harness/pilot-result.json) |
| CLI/bootstrap audit | Codex 0.163.0, Claude Code 2.1.300; required flags present | [doctor.json](harness/doctor.json) |

The Python 3.12.2 interpreter has Pydantic 2.13.4 and pytest. The initial research test attempt could not collect because music21 was absent. Pinned music21 9.9.1 and NumPy 1.26.4 were installed only into `.harness-state/validation-deps/`; the successful research run used that directory in `PYTHONPATH`. The system and repository production requirements were not modified. The committed doctor report uses this validation environment. Plain `python -m harness doctor` without that path also reports the missing music21 dependency.

The minimal macOS OS-sandbox probe returned exit 71, `sandbox_apply: Operation not permitted`. The isolated reviewer has no ANTHROPIC_API_KEY; existing CLI subscription credentials were not read or copied. Codex has no audited hard monetary cap in the installed exec flags, so an external metered gateway is required. In addition, release 0.1 has no qualified OS worker/verifier launcher. These are explicit blockers, not permissions to weaken containment.

## What the mock establishes

The demonstration ran against the exact baseline in detached Git worktrees. Its implementation and review responses are synthetic. It actually wrote bounded research notes, validated schemas and file permissions, recorded manifests, injected a gate failure, generated revision feedback, revised the content, created two research checkpoint commits, selected a dependency-ready next task and saved SQLite receipts outside `/private/tmp`. The local evidence directory and checkpoint IDs are recorded in the mock result. There was no remote push from the controller.

Tests also exercise malformed implementation/review output, forbidden paths and symlinks, extra untracked edits, changed frozen bytes, sensitive content, forbidden source promotion, invalid dependencies, merge/deploy/push requests, monetary/time limits, process timeout and cancellation, output flooding, concurrent controller locking, interrupted dispatch, duplicate reservations/actions, mismatched approval packets and source hashes, terminal-only owner approval, reviewer snapshot mutation detection and safe unrelated scheduling while an owner task waits.

Interruption recovery is conservative: a STARTED action becomes BLOCKED without replay. A completed run is idempotent on restart. Crash-window reconciliation between an external Git commit and its SQLite receipt remains manual. These tests do not prove live model cooperation, OS write denial, optical completeness, or automatic recovery of every crash boundary.

## Independence and claim audit

The mock builder, reviewer and synthetic failure are controller-designed. Treating their agreement as independent correctness would be shared hallucination or a verifier grading its own recipe. The remedy is to restrict the claim to controller mechanics and require a separate real Claude process, exact snapshot binding and independently executed deterministic gates before a live task can be accepted. Even real agent agreement cannot create owner verification. Owner approval remains an attributable terminal-attested response bound to exact source packet bytes; it is not independent ground truth.

A fresh context-free reader reviewed the runbook. The review found missing operator context, expected outcomes and recovery details; these were added. A consistency audit checked limits and provenance against the immutable policy and existing GT-16B records. No historical source was consolidated or rewritten. Portability cleanup was inapplicable because these are concrete CLI operational instructions. External capability claims are limited to locally captured CLI help/version output and actual probe results.

## Level 3 readiness

Not ready. Before any activation, qualify OS-enforced builder/reviewer/verifier isolation, hard Codex spend enforcement, selected-worker credentials, real structured review and verification receipts, and real-process interruption recovery. Resolve the existing MuseScore skip without weakening the gate. Review the implemented configuration and obtain explicit owner authorization. This release has no Level 3 start command and never starts the eight-hour loop.
