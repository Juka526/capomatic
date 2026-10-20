"""Actual local process evidence; no test launches Codex, Claude or a paid request."""
import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock
import uuid

import pytest

from harness.capture import Capture, canonical, inventory
from harness.controller import Controller
from harness.gitwork import git
from harness.planner import BACKLOG
from harness.policy import PolicyError
from harness.qualification import session_audit, cost_audit
from harness.state import Store
from test_harness import repo, store


@pytest.fixture
def job(repo, store, tmp_path):
    run = Controller(repo, store).create('mock')
    workspace = tmp_path / 'worker'
    workspace.mkdir()
    return Capture(store), run, dict(BACKLOG[0]), git(repo, 'rev-parse', 'HEAD'), workspace


def builder_command(task):
    payload = {'task_id': task['id'], 'summary': 'actual local fixture output',
               'changed_paths': task['paths'], 'status': 'implemented'}
    code = ('import pathlib,json; p=pathlib.Path(' + repr(task['paths'][0]) + '); '
            'p.parent.mkdir(parents=True,exist_ok=True); '
            'p.open("a").write("side effect once\\n"); print(' + repr(json.dumps(payload)) + ')')
    return [sys.executable, '-c', code]


def run_builder(job, **kwargs):
    capture, run, task, base, workspace = job
    return asyncio.run(capture.run(run, task, 'builder', base, workspace, builder_command(task), **kwargs))


def test_actual_subprocess_signed_artifact_and_diff(job):
    result = run_builder(job)
    capture, run, task, base, workspace = job
    receipt = result['receipt']
    assert receipt['exit_code'] == 0 and receipt['pid'] > 0 and receipt['finished'] >= receipt['started']
    assert receipt['changed'] == {task['paths'][0]: 'added'}
    assert result['payload']['task_id'] == task['id']
    assert (workspace / task['paths'][0]).read_text() == 'side effect once\n'
    assert capture.store.report()['events'][-1]['kind'] == 'PROCESS_CAPTURE_ACCEPTED'


def test_crash_after_receipt_before_checkpoint_recovers_without_side_effect_repeat(job):
    capture, run, task, base, workspace = job
    saved = []
    attempt = uuid.uuid4().hex
    def crash(capture_id):
        saved.append(capture_id)
        raise RuntimeError('controller interruption after durable seal')
    with pytest.raises(RuntimeError):
        run_builder(job, attempt_id=attempt, after_seal=crash)
    # A fresh SQLite connection and collector simulate an actual Controller restart.
    recovered = Capture(Store(capture.store.directory)).recover(saved[0])
    assert recovered['receipt']['attempt_id'] == attempt
    assert (workspace / task['paths'][0]).read_text().count('side effect once') == 1
    rows = len(capture.store.report()['events'])
    result = run_builder(job, attempt_id=attempt)
    assert result['capture_id'] == recovered['capture_id']
    assert len(capture.store.report()['events']) == rows
    assert (workspace / task['paths'][0]).read_text().count('side effect once') == 1


def test_duplicate_id_cannot_change_command_or_scope(job):
    capture, run, task, base, workspace = job
    attempt = uuid.uuid4().hex
    run_builder(job, attempt_id=attempt)
    with pytest.raises(PolicyError, match='different command or scope'):
        asyncio.run(capture.run(run, {**task, 'instruction': 'changed scope'}, 'builder', base,
                    workspace, builder_command(task), attempt_id=attempt))


def test_signed_receipt_tamper_rejected(job):
    result = run_builder(job)
    capture = job[0]
    path = capture.root / result['capture_id'] / 'sealed.json'
    doc = json.loads(path.read_text()); doc['receipt']['task_id'] = 'stale'; path.write_text(json.dumps(doc))
    with pytest.raises(PolicyError, match='authentication'):
        capture.recover(result['capture_id'])


def test_output_mutated_after_acceptance_rejected(job):
    result = run_builder(job)
    capture, _, task, _, workspace = job
    (workspace / task['paths'][0]).write_text('changed after checkpoint')
    with pytest.raises(PolicyError, match='sealed output'):
        capture.recover(result['capture_id'])


def test_nonzero_real_process_cannot_forge_test_pass(job):
    capture, run, task, base, workspace = job
    with pytest.raises(PolicyError, match='exit code'):
        asyncio.run(capture.run(run, task, 'verifier', base, workspace,
                    [sys.executable, '-c', 'print("all tests passed"); raise SystemExit(7)'], kind='deterministic_test'))
    row = capture.store.db.execute('SELECT * FROM process_captures').fetchone()
    receipt = json.loads((capture.root / row['id'] / 'sealed.json').read_text())['receipt']
    assert receipt['exit_code'] == 7 and row['status'] == 'BLOCKED'


def test_timeout_records_actual_killed_exit_and_never_reexecutes(job):
    capture, run, task, base, workspace = job
    with pytest.raises(TimeoutError):
        asyncio.run(capture.run(run, task, 'verifier', base, workspace,
                    [sys.executable, '-c', 'import time; print("started",flush=True); time.sleep(20)'], timeout=0.1))
    row = capture.store.db.execute('SELECT * FROM process_captures').fetchone()
    failure = json.loads((capture.root / row['id'] / 'failure.json').read_text())
    assert failure['exit_code'] != 0 and failure['pid'] > 0
    with pytest.raises(PolicyError, match='no action replay'):
        Capture(Store(capture.store.directory)).recover(row['id'])


def test_malformed_structured_agent_fixture_result_blocks(job):
    capture, run, task, base, workspace = job
    with pytest.raises((ValueError, PolicyError)):
        asyncio.run(capture.run(run, task, 'reviewer', base, workspace,
                    [sys.executable, '-c', 'print("not structured JSON")'],
                    review_sha=hashlib.sha256(canonical(inventory(workspace))).hexdigest()))
    assert not capture.store.db.execute("SELECT 1 FROM process_captures WHERE status='ACCEPTED'").fetchone()


def test_actual_reviewer_fixture_mutation_detected_not_claimed_as_os_denial(job):
    capture, run, task, base, workspace = job
    note = workspace / 'readonly.txt'; note.write_text('readonly input'); note.chmod(0o444)
    sha = hashlib.sha256(canonical(inventory(workspace))).hexdigest()
    code = 'import pathlib; p=pathlib.Path("readonly.txt"); p.chmod(0o644); p.write_text("same UID bypass")'
    with pytest.raises(PolicyError, match='changed its input'):
        asyncio.run(capture.run(run, task, 'reviewer', base, workspace, [sys.executable, '-c', code], review_sha=sha))
    assert note.read_text() == 'same UID bypass'  # Detection is not OS-enforced denial.
    row = capture.store.db.execute('SELECT * FROM process_captures ORDER BY rowid DESC LIMIT 1').fetchone()
    assert row['status'] == 'FAILED'
    failure = json.loads((capture.root / row['id'] / 'failure.json').read_text())
    assert failure['exit_code'] == 0 and failure['acceptance_error'] == 'PolicyError'


def test_actual_diagnostic_child_does_not_inherit_keys_or_socket(job, monkeypatch):
    capture, run, task, base, workspace = job
    names = ['OPENAI_API_KEY','ANTHROPIC_API_KEY','HERDR_SOCKET_PATH','PRODUCTION_PASSWORD']
    for name in names:
        monkeypatch.setenv(name, 'synthetic-private-marker')
    code = 'import os,json; print(json.dumps({n:n in os.environ for n in ' + repr(names) + '}))'
    result = asyncio.run(capture.run(run, task, 'verifier', base, workspace,
                        [sys.executable, '-c', code], kind='deterministic_test'))
    out = capture.root / result['capture_id'] / 'stdout.txt'
    assert json.loads(out.read_text()) == {name:False for name in names}
    assert 'synthetic-private-marker' not in out.read_text()


def test_capture_key_permissions_and_paid_guard(job):
    capture, run, task, base, workspace = job
    with pytest.raises(PolicyError, match='paid workers'):
        asyncio.run(capture.run(run, task, 'builder', base, workspace, builder_command(task), kind='paid_worker'))
    (capture.store.directory / 'controller-receipt.key').chmod(0o644)
    with pytest.raises(PolicyError, match='private'):
        Capture(capture.store)


def test_session_audit_outside_herdr_never_queries_live(monkeypatch):
    import harness.qualification as module
    monkeypatch.delenv('HERDR_ENV', raising=False)
    command = Mock(side_effect=AssertionError('must not inspect session'))
    monkeypatch.setattr(module, 'local_command', command)
    report = session_audit()
    assert report['status'] == 'BLOCKED' and report['live_requests'] == 0
    command.assert_not_called()


def test_cost_controls_distinguish_documented_feature_and_account_qualification():
    report = cost_audit()
    assert report['openai']['documented_hard_limits'] is True
    assert report['openai']['account_project_binding_verified'] is False
    assert report['openai']['enforcement_instantaneous'] is False
    assert report['time_or_request_limits_are_monetary_caps'] is False


@pytest.mark.parametrize('xml,code,status', [
    ('<testsuites><testsuite><testcase name="ok"/></testsuite></testsuites>',0,'PASS'),
    ('<testsuites><testsuite><testcase name="skip"><skipped message="dependency absent"/></testcase></testsuite></testsuites>',0,'BLOCKED'),
    ('<testsuites tests="100" failures="0"/>',0,'BLOCKED'),
    ('<testsuite><testcase name="false-pass"/></testsuite>',7,'BLOCKED'),
])
def test_regression_gate_uses_actual_junit_cases_and_never_waives_skip(tmp_path, xml, code, status):
    from harness.regression_evidence import summarize
    path=tmp_path/'junit.xml';path.write_text(xml)
    assert summarize(path,code)['mandatory_gate']==status


def test_lost_receipt_key_does_not_create_replacement_for_existing_work(job):
    run_builder(job)
    capture=job[0]
    key=capture.store.directory/'controller-receipt.key';key.unlink()
    with pytest.raises(PolicyError,match='refusing replacement'):
        Capture(Store(capture.store.directory))
    assert not key.exists()


def test_shared_controller_state_directory_cannot_hold_signing_authority(job):
    capture=job[0]
    capture.store.directory.chmod(0o755)
    with pytest.raises(PolicyError,match='state directory must be private'):
        Capture(capture.store)
