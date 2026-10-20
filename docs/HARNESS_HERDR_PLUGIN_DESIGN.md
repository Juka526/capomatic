# Optional local Herdr plugin design

Design only. No plugin is linked, installed or activated by this release.

Use a local `herdr-plugin.toml` with explicit action argv arrays, as described in the [official plugin API](https://herdr.dev/docs/plugins/). The installed 0.9.0 CLI exposes `plugin link`, action invocation, plugin panes and logs. Newer online commands absent from installed help are not used.

Proposed plugin ID: `capomatic.harness`. Actions: status, current-task, report, approvals, pause and resume. Read actions call the Python Controller's existing CLI. Pause/resume require an owner-selected persisted run ID and use its existing control methods; they cannot start a new run, change a task, approve source or unfreeze an uncertain action. No startup/event hook automatically begins work.

An owner-maintained local config holds the absolute research checkout, durable state directory and selected run ID. The launcher validates paths and run existence, builds argument arrays and executes `python -m harness`. It never interpolates terminal text or agent responses into a shell. Herdr invocation context identifies presentation only; it cannot grant Controller authority.

Illustrative action entry:

```toml
[[actions]]
id = "status"
title = "Harness status"
contexts = ["workspace"]
command = ["python", "capomatic_plugin.py", "status"]
```

A future reviewed launcher would resolve the configured checkout/state and invoke `python -m harness --repo REPO --state-dir STATE status`. Reports and approvals stay local because they may contain private paths and owner text. A board may use a Herdr-owned terminal pane; no new UI framework or runtime state store is needed. Plugins inherit user capabilities and are not sandboxed, so review the final manifest and launcher before any manual link. No third-party plugin dependency is proposed.
