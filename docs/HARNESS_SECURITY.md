# Harness 0.1 security and threat model

Assets include original music evidence, approved provenance, protected masks, historical results, production code, owner identity, credentials, budget and the integrity of controller decisions. Threats include repository prompt injection, malformed agent output, path traversal and symlinks, worker filesystem abuse, forged approval, fabricated test results, duplicate dispatch after interruption, secret disclosure and unbounded processes or spend.

| Threat | Implemented boundary | Remaining limitation |
|---|---|---|
| Repository instructions request deployment or policy edits | Controller-defined task catalog, strict operation/path policy, frozen bytes | Prompt text itself provides no security; adversarial model behavior needs live containment tests |
| Agent forges success | Strict JSON Schema, controller-owned process results and gates | Live receipt/review integration remains unqualified |
| Reviewer writes | Read tools only, separate snapshot, readonly modes, byte manifest comparison | Same UID can chmod; OS denial is required before dispatch |
| Approval fabrication | Exact packet/source hashes, original response bytes, interactive owner attestation | Terminal operator authenticity is trusted; no cryptographic remote identity verification |
| Secret leakage | Presence-only audit, changed-content checks, per-worker environment constructor | Regex checks are defense in depth; isolated credential stores and network policy need qualification |
| Timeout/stall | Deadline, output cap, process-group kill and reap, pause/stop polling | Absolute deadline bounds stalls; no semantic activity detector; escaped process groups need OS containment |
| Cost overrun | Transactional worst-case aggregate/per-worker reservations | Codex CLI lacks an audited hard USD cap here; metered gateway needed; live blocked |
| Duplicate actions | SQLite unique keys, lock, fail-closed uncertain recovery, commit trailer | Crash between Git commit and receipt blocks for manual reconciliation |
| Source promotion or erasure | No source/production edits allowed; frozen hashes and bound approval queue | 0.1 never promotes source candidates, even after a response is recorded |

`doctor` probes the installed binaries and flags, a minimal OS sandbox invocation, required research dependencies and credential presence. It does not disclose credentials or assume a logged-in CLI subscription can be safely copied into a worker. The audit records an OS sandbox failure in this session. No automatic permission bypass, unrestricted worker, `--yolo`, auto-push, merge or deployment exists.

The canonical scope remains the owner-confirmed GT-16B interpretation, not independent ground truth. All ten unresolved SIG objects and the full repeat playback route remain withheld. The binding and validation artifacts remain unchanged. The planner uses dependencies rather than assuming a sequential GT identifier means the next task.

Activation requires a new reviewed implementation, real harmless pilot receipts, OS write-denial and credential-exclusion tests, metered cost enforcement, complete deterministic music/source verification and explicit owner authorization. Passing mock tests is evidence about the controller only.
