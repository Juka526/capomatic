# Harness 0.2 security readiness

**Real pilot: blocked. Level 3: disabled.** Herdr is a terminal and agent lifecycle manager, not a filesystem sandbox, credential boundary, test oracle or metered API gateway. This release keeps the 0.1 security policy byte-identical.

| Boundary | Implemented and tested | Remaining qualification |
|---|---|---|
| Controller authority | Persisted phase checks, exact task/dependency/path policy, immutable policy hash, no planner permission overrides | No live agent dispatch admitted |
| Reviewer data minimization | Separate minimal readonly snapshot; secret/path checks before any review prompt; no original owner messages or repository credential files | POSIX chmod is not same-UID write denial; an OS-enforced reviewer launcher must be tested |
| Verifier independence | Separate full candidate snapshot; Controller gates and byte comparison; unchanged V3/V4 suite run separately | Live verifier pane execution/capture is unqualified; its entry point fails closed |
| Herdr control plane | Inherited context required; opaque IDs, owned receipts, no group close or arbitrary focused target | Workers and hooks must not inherit unrestricted Herdr socket control; qualify an own-pane reporting broker or equivalent OS restriction |
| Native restore | Session/cwd/workspace identity reconciliation; no automatic replay after uncertain delivery | Restored conversation identity does not prove original sandbox, selected credentials, argv or hard-cost limits survived |
| Credentials | Shared agent settings untouched; presence-only audit; source data withheld from reviewer | Separate Claude credential unavailable; isolated shell environments and reviewed native hooks need qualification |
| Cost and time | Existing transactional reservations, run/task deadlines, bounded Herdr request timeout | No audited hard Codex USD cap; qualify external metered enforcement before real work |
| Approvals | Exact source-packet and genuine owner-response binding unchanged; pending tasks withheld | Interactive terminal operator remains the identity trust root; no synthetic owner records |
| Recovery | Persistent dispatch/request hashes; duplicate controller lock; no resend on lost receipt | Real worker/server interruption recovery is not proven by mock fault injection |
| Music/source | Original baseline hashes, approved packet, historical outputs and unchanged V3/V4 guards | MuseScore is missing; existing skip is not waived; no rendering or source edits admitted |

The installed Herdr CLI is 0.9.0, API protocol 22. Codex integration v8 and Claude integration v9 are current relative to that installed binary. The online integration documentation describes newer hooks; no update or migration was performed. Hook/session availability is not equivalent to live restoration qualification.

The 0.1 Codex `--ignore-user-config`/ephemeral path and Claude `--bare` path conflict with loading native integration hooks and persistent conversation identity. Native argument templates therefore require a reviewed, per-worker configuration containing only the needed hooks. This release does not copy the user's global config, change shared hooks or relax settings to obtain resume functionality. Herdr workspace `--env` overrides do not clear inherited variables and must not be treated as credential isolation.

Agent-produced artifacts are untrusted claims with strong identity/hash binding. A `reported` manifest or a Herdr lifecycle observation does not establish correctness. The mock's builder, reviewer and receipts are synthetic; only actual Controller-executed checks support its verification claim. Genuine model independence and live artifact transport require a bounded, separately authorized real pilot after containment and spend qualification.

All ten unresolved SIG objects and the full repeat playback route remain withheld. Owner-confirmed source is never labeled independent ground truth. No original PDF, protected mask, production V1/V3 code, security policy, merge target or deployment is modified by an autonomous task.
