# Harness 0.3 runtime qualification

**Pilot outcome: BLOCKED before any paid worker launch. Level 3: not ready and not activated.** This release prepares one harmless research-note task and strengthens actual process evidence/recovery. It does not claim that a secure Herdr-native Codex/Claude runtime is operational.

Starting commit: `3bf1e9ff9b8f53cb7bb219eff6a17a859a7ce71b`. Branch: `experiment/capomatic-harness-03-runtime`. The [qualification record](harness03/qualification.json) is controller-generated observation, not an approval or execution permit.

## Prerequisites

| Requirement | Observed result |
|---|---|
| Authorized Herdr pane, socket and ownership | BLOCKED: inherited environment/pane/socket context absent; no live request made |
| OS isolation and negative access tests | BLOCKED: Docker daemon unavailable; Seatbelt launcher failed before starting a child |
| Separate scoped worker authentication | UNVERIFIED: no actual isolated worker exists; no provider authentication attempted |
| Hard monetary safeguards | UNVERIFIED account/project/workspace binding and overshoot allowance |
| Actual artifact recovery | Local trusted subprocess capture/recovery passes; live AI-worker transport and restoration remain unqualified |
| Mandatory regression/preservation | Source preservation passes; MuseScore-dependent regression remains skipped and blocks readiness |
| Explicit paid execution authorization | NOT_GRANTED; this conditional qualification request does not authorize paid dispatch |

The report records Herdr 0.9.0/API protocol 22, Codex 0.163.0 and Claude Code 2.1.304. Local integrations are Codex v8 and Claude v9, current relative to installed Herdr. Shared hook/settings hashes remain unchanged. Claude updated from the previously recorded 2.1.300 in the surrounding installation; this task did not run a CLI update or install hooks/plugins.

The [installed Herdr skill](https://herdr.dev/docs/agent-skill/) requires operation inside Herdr. `session_audit()` returns before socket/pane commands when inherited context is absent. Inside a genuine session it requires a same-owner Unix socket and exact inherited caller pane/workspace identities. Unit tests of this guard do not substitute for a live in-session audit.

## OS containment evidence

Docker client 29.8.2 is installed, but `docker version` cannot connect to the desktop-linux daemon socket. Podman, Lima, Colima and QEMU CLI alternatives were not found. No VM, container, daemon or third-party plugin was started or installed.

A macOS sandbox probe used only synthetic canaries in durable harness state. `sandbox-exec` returned exit 71 with `sandbox_apply: Operation not permitted`; it produced no child-start marker. Read/write negative tests inside that sandbox therefore **did not run**. A failed launcher is not evidence of effective isolation.

A separate actual subprocess demonstrated that a same-UID process can chmod and modify a POSIX-readonly canary. The collector detected the mutation and refused acceptance. That detection is not write denial. No personal file, real credential, protected score, original PDF or security-policy file was used as a canary or accessed by a worker.

A future qualified environment should use dedicated VM boundaries or an independently qualified OS launcher, minimal mounted inputs, separate writable Builder and readonly Reviewer sources, an isolated verifier, no host home/controller state, no Docker or Herdr control socket, and a narrowly scoped trusted result channel. Herdr-native restoration must preserve those boundaries; conversation restoration alone is insufficient. These are requirements, not claims about an implemented live launcher.

## Credentials and costs

Actual diagnostic subprocesses received an explicit minimal environment. The recorded child excluded OPENAI_API_KEY, ANTHROPIC_API_KEY, HERDR_SOCKET_PATH and production-secret names even when present in the parent. This establishes environment filtering for those local diagnostics only. It does not prove VM isolation, least privilege, successful provider authentication, or credential scope for Codex/Claude. No user auth store or credential file was copied; no provider authentication request was sent.

Current OpenAI documentation distinguishes alerts from enforced project/organization hard limits and warns that enforcement can lag. Actual account settings, billing identity and an allowance for overshoot have not been verified. [OpenAI spend limits](https://developers.openai.com/api/docs/guides/spend-limits)

Anthropic documents workspace spending limits, but no dedicated workspace/key or effective limit was inspected here. CLI timeouts, request/turn counts and local reservations do not establish a monetary ceiling. [Claude workspace limits](https://platform.claude.com/docs/en/manage-claude/workspaces)

The USD 2 figure is a proposed qualification budget, not evidence of a cap; maximum financial exposure is currently unknown. The proposed pilot has one Codex implementation, one independent Claude review, no automatic second task, a proposed 300-second task timeout and a proposed USD 2 ceiling. These remain a plan. Before paid execution, independently bind dedicated credentials to permitted models/projects, read back remaining enforced limits, and qualify any gateway reservations/in-flight allowance required to meet the exact owner-approved ceiling. Never put a provider admin key in a worker.

## Actual process and artifact recovery

`harness.capture` adds unique run/task/attempt identities, a request-bound process ledger, real PID/start/end/exit evidence, structured implementation/review schema validation, byte-and-mode input/output inventories, actual filesystem diffs and controller-authenticated sealed receipts. The signing key stays in private controller state outside diagnostic workspaces. This is not protection against a hostile same-UID host process; OS isolation is absent. Exclusive file creation, fsync and SHA/HMAC checks prevent silently replacing accepted evidence. Losing a key for existing captures fails closed rather than generating a replacement authority.

`harness.runtime_demo` executes actual Python subprocesses and a pytest subprocess. A forced Controller interruption after sealing the Builder receipt was reconciled using a fresh SQLite connection; retrying the same attempt did not repeat its file write. This tests that local append/sealed-receipt crash window only, not exactly-once external requests, paid workers or arbitrary distributed side effects. A process that printed a success claim but exited 7 was blocked. Readonly input mutation was detected. Reports are explicitly classified as local fixtures, **not** Codex implementation, Claude independent review or live worker recovery.

An interrupted action without an authenticated finished receipt remains blocked. A stored PID is incident evidence, not authority to kill a process after restart or assume it is still the same process. No mutation, prompt, review, commit or approval is replayed by `recover-artifact`; it only authenticates and records already-finished capture evidence. The existing Controller remains authoritative for subsequent workflow decisions and commits.

The capture entry point accepts only trusted Controller-authored local diagnostic/test argument arrays. Python `-c` is arbitrary-code capability, not containment; never compile agent text into those commands or treat a process-kind label as permission to launch a worker. There is no arbitrary-command or paid-execution CLI option.

HMAC receipts are not an OS sandbox and are not owner source approval. An unisolated same-UID adversary could access controller authority; paid workers stay disabled. Local crash-window tests do not qualify native Herdr process restoration, escaped descendants, live transcript/result capture or arbitrary real-worker interruption.

## Validation and remaining work

In the clean pinned Python environment, all **91 harness tests passed**. The exact resolved Python package hashes are in [runtime-validation.lock.txt](../harness/runtime-validation.lock.txt); this does not supply or qualify the missing native MuseScore/OS runtime.

See [harness tests](harness03/harness-tests.txt), [actual process recovery](harness03/process-recovery.json), [regression summary](harness03/regression-summary.json), [test-process command](harness03/regression-process.json), [preservation checks](harness03/preservation.json), and the [MuseScore report](HARNESS_03_MUSESCORE.md). JUnit interpretation rejects empty collections, failures, errors, nonzero exits and every skip; zero pytest exit alone is insufficient.

No mandatory gate was weakened, source interpretation promoted, private owner evidence sent to an agent, production/application source file changed, or merge/deployment performed. Harness code, tests, dependency evidence and documentation are the intended research changes. Resolve every prerequisite and obtain explicit authorization bound to the reviewed single-task plan before considering a real pilot. A successful future pilot may generate one proposed next prompt for owner review; it must not dispatch it or enable Level 3.

## Ordered next actions

1. The owner supplies an authorized Herdr-managed Controller session; rerun the caller/socket ownership audit there without altering or impersonating its context.
2. The runtime operator establishes a dedicated VM/OS boundary and proves the Builder, Reviewer, verifier, controller-state, network and socket negative tests. No credentials enter it before this passes.
3. The owner provisions dedicated scoped worker credentials and permits non-generation authentication/scope checks in the isolated environments. A Controller-side operator verifies effective account limits and a defensible maximum exposure, including enforcement delay and in-flight requests; no admin key enters a worker.
4. The runtime operator supplies a digest-identified MuseScore/native/font environment and reruns the named mandatory MusicXML-to-PDF check plus unchanged V3/V4/source guards with zero skips.
5. The engineer qualifies real CLI artifact transport and restart behavior under that boundary. Any behavior that cannot be tested without model usage remains withheld until separately authorized within the bounded pilot. Do not mistake these local fixtures for that evidence.
6. The owner reviews the exact single-task plan, timeout and qualified financial exposure, then explicitly authorizes any paid execution. Nothing here grants that authorization. No automatic second task or Level 3 follows.
