"""Herdr orchestration tests use an explicit fake service, never the user's session."""
import json
from pathlib import Path
import time

import pytest
from pydantic import ValidationError
from harness.artifacts import collect, TaskManifest, write_simulated
from harness.budget import BudgetExceeded
from harness.controller import Controller
from harness.gitwork import git, manifest
from harness.herdr_adapter import HerdrAdapter, Disconnected, CLI
from harness.herdr_audit import capabilities
from harness.herdr_mock import MockHerdr
from harness.herdr_runtime import HerdrRuntime
from harness.policy import PolicyError
from harness.state import Store
from test_harness import repo, store


@pytest.fixture
def adapter(repo, store):
    run = Controller(repo, store).create('herdr-mock')
    transport = MockHerdr(store.directory)
    return HerdrAdapter(store, run, transport)


def test_provision_named_workspace_worktree_panes_and_no_adoption(adapter, repo):
    role = adapter.workspace('controller', repo)
    again = adapter.workspace('controller', repo)
    assert role == again
    assert len(adapter.transport.state['workspaces']) == 1
    target = adapter.store.directory / 'builder'
    saved = adapter.worktree('builder', repo, target, git(repo, 'rev-parse', 'HEAD'))
    assert saved['cwd'] == str(target) and target.is_dir()
    assert saved['pane']['pane_id'] != role['pane']['pane_id']
    calls = adapter.transport.state['calls']
    assert sum(c[:2] == ['workspace', 'create'] for c in calls) == 1
    assert sum(c[:2] == ['worktree', 'create'] for c in calls) == 1
    assert all('--no-focus' in c for c in calls if c[:2] in [['workspace', 'create'], ['worktree', 'create']])
    with pytest.raises(PolicyError):
        adapter.worktree('unowned', repo, target, git(repo, 'rev-parse', 'HEAD'))


def test_agent_start_prompt_lifecycle_and_duplicate_prevention(adapter, repo):
    adapter.workspace('builder', repo)
    agent = adapter.start_agent('builder', 'codex', ['--sandbox', 'workspace-write'])
    assert agent['agent_session']['value']
    adapter.prompt('builder', 'dispatch-1', 'bounded task')
    assert adapter.observe('builder')['agent_status'] == 'done'
    adapter.prompt('builder', 'dispatch-1', 'bounded task')
    calls = adapter.transport.state['calls']
    assert sum(c[:2] == ['agent', 'prompt'] for c in calls) == 1
    for state in ['working', 'blocked', 'unknown']:
        adapter.transport.state['panes'][agent['pane_id']]['agent_status'] = state
        with pytest.raises(PolicyError):
            adapter.prompt('builder', 'dispatch-2', 'do not send')


def test_disconnect_after_prompt_is_not_retried(adapter, repo):
    adapter.workspace('builder', repo)
    adapter.start_agent('builder', 'codex', [])
    adapter.transport.drop_after = ['agent', 'prompt']
    with pytest.raises(Disconnected):
        adapter.prompt('builder', 'dispatch', 'possibly delivered')
    with pytest.raises(PolicyError, match='ambiguous'):
        adapter.prompt('builder', 'dispatch', 'possibly delivered')
    assert sum(c[:2] == ['agent', 'prompt'] for c in adapter.transport.state['calls']) == 1


def test_reconnect_and_native_session_restart_mapping(adapter, repo):
    adapter.workspace('builder', repo)
    original = adapter.start_agent('builder', 'codex', [])
    adapter.transport.disconnected = True
    with pytest.raises(Disconnected):
        adapter.observe('builder')
    adapter.transport.disconnected = False
    assert adapter.reconcile('builder')['pane']['pane_id'] == original['pane_id']
    adapter.transport.restart(native_resume=True)
    resumed = HerdrAdapter(adapter.store, adapter.run_id, MockHerdr(adapter.store.directory))
    found = resumed.reconcile('builder')['pane']
    assert found['pane_id'] != original['pane_id']
    assert found['agent_session'] == original['agent_session']
    resumed.transport.restart(native_resume=False)
    with pytest.raises(PolicyError):
        resumed.reconcile('builder')


def test_changed_or_duplicate_session_identity_fails_closed(adapter, repo):
    adapter.workspace('builder', repo)
    agent = adapter.start_agent('builder', 'codex', [])
    pane = adapter.transport.state['panes'][agent['pane_id']]
    pane['agent_session']['value'] = 'different-session'
    with pytest.raises(PolicyError, match='session identity'):
        adapter.reconcile('builder')


def test_unknown_resources_are_not_closed(adapter, repo):
    owned = adapter.workspace('controller', repo)
    user = adapter.transport.create_workspace(str(repo), 'user-work')
    adapter.cleanup('controller')
    assert user['workspace']['workspace_id'] in adapter.transport.state['workspaces']
    assert owned['workspace_id'] not in adapter.transport.state['workspaces']
    with pytest.raises(PolicyError):
        adapter.cleanup('not-owned')


@pytest.fixture
def artifact(tmp_path):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    (workspace / 'note.md').write_text('bounded result\n')
    directory = tmp_path / 'outbox'
    identity = {'run_id': 'run', 'task_id': 'task', 'dispatch_id': 'dispatch', 'role': 'builder',
                'base_sha': 'a'*40, 'input_sha256': 'b'*64, 'simulated': True}
    payload = {'task_id': 'task', 'summary': 'synthetic', 'changed_paths': ['note.md'], 'status': 'implemented'}
    write_simulated(directory, identity, workspace, ['note.md'], payload)
    return directory, identity, workspace


@pytest.mark.parametrize('field,value', [('task_id', 'stale'), ('run_id', 'stale'),
    ('dispatch_id', 'stale'), ('base_sha', 'c'*40), ('input_sha256', 'c'*64), ('simulated', False)])
def test_stale_result_identity_rejected(artifact, field, value):
    directory, identity, workspace = artifact
    with pytest.raises(PolicyError, match='mismatched'):
        collect(directory, {**identity, field: value}, workspace, ['note.md'])


@pytest.mark.parametrize('name', ['manifest.json', 'payload.json', 'receipt.json'])
def test_missing_or_malformed_results_rejected(artifact, name):
    directory, identity, workspace = artifact
    (directory / name).write_text('malformed')
    with pytest.raises((PolicyError, ValueError, ValidationError)):
        collect(directory, identity, workspace, ['note.md'])
    (directory / name).unlink()
    with pytest.raises((PolicyError, ValueError, ValidationError)):
        collect(directory, identity, workspace, ['note.md'])


def test_lifecycle_done_without_manifest_never_passes(artifact):
    directory, identity, workspace = artifact
    (directory / 'manifest.json').unlink()
    with pytest.raises(PolicyError, match='missing'):
        collect(directory, identity, workspace, ['note.md'])


def test_output_hash_tamper_and_symlink(artifact):
    directory, identity, workspace = artifact
    (workspace / 'note.md').write_text('tampered')
    with pytest.raises(PolicyError, match='output hash'):
        collect(directory, identity, workspace, ['note.md'])
    (workspace / 'note.md').unlink()
    (workspace / 'note.md').symlink_to(directory / 'payload.json')
    with pytest.raises(PolicyError):
        collect(directory, identity, workspace, ['note.md'])


def test_herdr_context_and_protocol_fail_closed(adapter, monkeypatch):
    monkeypatch.delenv('HERDR_ENV', raising=False)
    cli = object.__new__(CLI)
    cli.context = {'HERDR_SOCKET_PATH': None}
    with pytest.raises(PolicyError):
        cli.call(['workspace', 'list'])
    schema = json.loads(json.dumps(adapter.transport.schema))
    schema['protocol'] = 999
    with pytest.raises(ValueError):
        capabilities(schema)


def test_no_live_worker_even_if_fake_audit_says_ready(adapter, repo):
    adapter.workspace('builder', repo)
    adapter.simulated = False
    with pytest.raises(PolicyError):
        adapter.start_agent('builder', 'codex', [])
    assert not any(c[:2] == ['agent', 'start'] for c in adapter.transport.state['calls'])


def test_pause_timeout_and_duplicate_controller(adapter, repo):
    ctl = Controller(repo, adapter.store)
    ctl.control(adapter.run_id, 'PAUSE')
    with pytest.raises(PolicyError, match='paused'):
        adapter.workspace('late', repo)
    ctl.control(adapter.run_id, 'RUN')
    with adapter.store.db:
        adapter.store.db.execute('UPDATE runs SET started=? WHERE id=?', (time.time()-28801, adapter.run_id))
    with pytest.raises(BudgetExceeded, match='duration'):
        adapter.workspace('late', repo)
    with adapter.store.lock():
        with pytest.raises(RuntimeError):
            ctl.run(adapter.run_id)


def test_full_herdr_mock_cycle_preservation_next_prompt_and_restart(repo, store):
    ctl = Controller(repo, store)
    run = ctl.create('herdr-mock')
    head = git(repo, 'rev-parse', 'HEAD')
    ctl.run(run, 2)
    assert store.run(run)['state'] == 'COMPLETED', store.report()['events'][-1]
    tasks = store.report()['tasks']
    assert len(tasks) == 2 and all(t['status'] == 'ACCEPTED' for t in tasks)
    dispatches = store.db.execute('SELECT * FROM herdr_dispatches').fetchall()
    assert len(dispatches) == 12 and all(d['status'] == 'COLLECTED' for d in dispatches)
    prompts = [json.loads(d['request']) for d in dispatches]
    followup = [p for p in prompts if p['identity']['task_id'] == 'validation-followup' and p['identity']['role'] == 'builder']
    assert tasks[0]['checkpoint'] in followup[0]['prompt']
    assert git(repo, 'rev-parse', 'HEAD') == head
    resources = [json.loads(r['data']) for r in store.db.execute('SELECT * FROM herdr_resources')]
    builder_cwds = {r['cwd'] for r in resources if 'builder' in r['label']}
    assert all(r['cwd'] not in builder_cwds for r in resources if 'reviewer' in r['label'])
    n = len(store.report()['actions'])
    Controller(repo, Store(store.directory)).run(run)
    assert len(store.report()['actions']) == n


def test_idempotency_key_cannot_change_prompt(adapter, repo):
    adapter.workspace('builder', repo)
    adapter.start_agent('builder', 'codex', [])
    adapter.prompt('builder', 'one', 'first instruction')
    with pytest.raises(PolicyError, match='different Herdr request'):
        adapter.prompt('builder', 'one', 'different instruction')


def test_reviewer_only_receives_allowed_files_without_owner_data(repo, store):
    from harness.gitwork import Worktrees
    private = repo / '.env'
    private.write_text('PRODUCTION_PASSWORD=synthetic-secret\n')
    path = repo / 'research/harness_tasks/a.md'
    path.parent.mkdir(parents=True)
    path.write_text('safe research note\n')
    snapshot, files = Worktrees(repo, store.directory).review_snapshot(repo, ['research/harness_tasks/a.md'], 'minimal')
    assert set(files) == {'research/harness_tasks/a.md'}
    assert not (snapshot / '.env').exists() and not (snapshot / 'source.txt').exists()
    assert (snapshot / 'research/harness_tasks/a.md').stat().st_mode & 0o222 == 0
    path.write_text('api_key = synthetic-sensitive-value')
    with pytest.raises(PolicyError):
        Worktrees(repo, store.directory).review_snapshot(repo, ['research/harness_tasks/a.md'], 'secret')


def test_policy_corruption_blocks_before_reviewer_launch(repo, store, monkeypatch):
    original = HerdrRuntime.implement
    def corrupt(self, task, attempt, base, worktree, prompt):
        result = original(self, task, attempt, base, worktree, prompt)
        (worktree / 'source.txt').write_text('corrupted frozen file')
        return result
    monkeypatch.setattr(HerdrRuntime, 'implement', corrupt)
    ctl = Controller(repo, store)
    run = ctl.create('herdr-mock')
    ctl.run(run)
    assert store.run(run)['state'] == 'BLOCKED'
    service = MockHerdr(store.directory)
    assert not any(c[:2] == ['agent', 'start'] and 'claude' in c for c in service.state['calls'])
    assert (repo / 'source.txt').read_text() == 'frozen evidence\n'


def test_approval_blocking_retains_waiting_state_and_no_dispatch(repo, store, monkeypatch):
    from harness import planner
    pending = {**planner.BACKLOG[0], 'id': 'needs-owner', 'requires_owner': True}
    monkeypatch.setattr(planner, 'BACKLOG', [pending])
    ctl = Controller(repo, store)
    run = ctl.create('herdr-mock')
    ctl.run(run, 2)
    assert store.run(run)['state'] == 'WAITING_OWNER_APPROVAL'
    assert not store.db.execute('SELECT 1 FROM herdr_dispatches').fetchone()
    assert any(c[:2] == ['notification', 'show'] for c in ctl.runtime.adapter.transport.state['calls'])


def test_interrupted_controller_blocks_without_replaying_herdr_mutation(adapter, repo):
    adapter.transport.drop_after = ['workspace', 'create']
    with pytest.raises(Disconnected):
        adapter.workspace('controller', repo)
    ctl = Controller(repo, adapter.store)
    ctl.run(adapter.run_id)
    assert adapter.store.run(adapter.run_id)['state'] == 'BLOCKED'
    assert sum(c[:2] == ['workspace', 'create'] for c in adapter.transport.state['calls']) == 1


def test_dispatch_requires_authoritative_controller_phase(repo, store):
    ctl = Controller(repo, store)
    run = ctl.create('herdr-mock')
    runtime = HerdrRuntime(repo, store, run)
    from harness.planner import BACKLOG
    with pytest.raises(PolicyError, match='authorized'):
        runtime.implement(BACKLOG[0], 1, git(repo, 'rev-parse', 'HEAD'), repo, 'do not dispatch')
    assert not store.db.execute('SELECT 1 FROM herdr_dispatches').fetchone()


def test_outbox_parent_symlink_is_rejected(artifact, tmp_path):
    directory, identity, workspace = artifact
    link = tmp_path / 'linked-outbox'
    link.symlink_to(directory, target_is_directory=True)
    with pytest.raises(PolicyError, match='directory symlink'):
        collect(link, identity, workspace, ['note.md'])
