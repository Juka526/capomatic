"""Unpaid actual-process recovery qualification; never launches an AI CLI."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

from .capture import Capture, canonical, inventory
from .controller import Controller
from .gitwork import git
from .policy import PolicyError
from .state import Store


def demonstrate(repo, directory):
    case = directory.resolve() / uuid.uuid4().hex
    workspace = case / 'builder'
    workspace.mkdir(parents=True)
    store = Store(case / 'controller')
    capture = Capture(store)
    run = Controller(repo, store).create('mock')
    base = git(repo, 'rev-parse', 'HEAD')
    task = {'id': 'runtime-capture-note', 'operation': 'research',
            'paths': ['research/harness_tasks/runtime-capture.md'], 'depends_on': [], 'requires_owner': False,
            'instruction': 'Produce one harmless local runtime capture fixture note.'}
    payload = {'task_id': task['id'], 'summary': 'actual Python fixture; no Codex invoked',
               'changed_paths': task['paths'], 'status': 'implemented'}
    code = ('import pathlib; p=pathlib.Path(' + repr(task['paths'][0]) + '); '
            'p.parent.mkdir(parents=True,exist_ok=True); p.open("a").write("runtime fixture once\\n"); '
            'print(' + repr(json.dumps(payload)) + ')')
    attempt = uuid.uuid4().hex
    saved = []
    def crash(capture_id):
        saved.append(capture_id)
        raise RuntimeError('qualification interruption after seal')
    try:
        asyncio.run(capture.run(run, task, 'builder', base, workspace, [sys.executable, '-c', code],
                                attempt_id=attempt, after_seal=crash))
    except RuntimeError as exc:
        if str(exc) != 'qualification interruption after seal':
            raise
    builder = Capture(Store(store.directory)).recover(saved[0])
    duplicate = asyncio.run(capture.run(run, task, 'builder', base, workspace,
                            [sys.executable, '-c', code], attempt_id=attempt))
    assert duplicate['capture_id'] == builder['capture_id']
    assert (workspace / task['paths'][0]).read_text() == 'runtime fixture once\n'

    reviewer = case / 'reviewer'
    note = reviewer / task['paths'][0]
    note.parent.mkdir(parents=True)
    note.write_bytes((workspace / task['paths'][0]).read_bytes())
    note.chmod(0o444)
    sha = hashlib.sha256(canonical(inventory(reviewer))).hexdigest()
    review = {'task_id': task['id'], 'snapshot_sha256': sha, 'verdict': 'pass', 'findings': [],
              'summary': 'deterministic Python schema fixture; no Claude invoked'}
    reviewer_result = asyncio.run(capture.run(run, task, 'reviewer', base, reviewer,
        [sys.executable, '-c', 'import pathlib; assert pathlib.Path(' + repr(task['paths'][0]) +
         ').read_text()=="runtime fixture once\\n"; print(' + repr(json.dumps(review)) + ')'], review_sha=sha))

    verifier = case / 'verifier'
    verifier.mkdir()
    (verifier / 'test_capture_probe.py').write_text('def test_actual_process_arithmetic():\n    assert 2 + 2 == 4\n')
    verification = asyncio.run(capture.run(run, task, 'verifier', base, verifier,
        [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', 'test_capture_probe.py'],
        kind='deterministic_test', timeout=30))

    negative = case / 'readonly-negative'
    negative.mkdir()
    target = negative / 'readonly.txt'
    target.write_text('synthetic canary'); target.chmod(0o444)
    sha = hashlib.sha256(canonical(inventory(negative))).hexdigest()
    detected = False
    try:
        asyncio.run(capture.run(run, task, 'reviewer', base, negative,
            [sys.executable, '-c', 'import pathlib; p=pathlib.Path("readonly.txt"); p.chmod(0o644); p.write_text("changed")'],
            review_sha=sha))
    except PolicyError:
        detected = True
    assert detected and target.read_text() == 'changed'
    names = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'HERDR_SOCKET_PATH', 'PRODUCTION_PASSWORD']
    parent_presence = {n: bool(os.environ.get(n)) for n in names}
    env_code = 'import os,json; print(json.dumps({n:n in os.environ for n in ' + repr(names) + '}))'
    env_capture = asyncio.run(capture.run(run, task, 'verifier', base, verifier,
                              [sys.executable, '-c', env_code]))
    child_presence = json.loads((capture.root / env_capture['capture_id'] / 'stdout.txt').read_text())
    assert not any(child_presence.values())
    nonzero = None
    try:
        asyncio.run(capture.run(run, task, 'verifier', base, verifier,
            [sys.executable, '-c', 'print("all tests passed"); raise SystemExit(7)']))
    except PolicyError:
        row = store.db.execute('SELECT * FROM process_captures ORDER BY rowid DESC LIMIT 1').fetchone()
        failure = json.loads((capture.root / row['id'] / 'sealed.json').read_text())['receipt']
        nonzero = {'exit_code': failure['exit_code'], 'status': row['status']}
    assert nonzero == {'exit_code': 7, 'status': 'BLOCKED'}
    return {'case_directory': str(case), 'base_sha': base, 'paid_workers_invoked': 0,
            'classification': 'ACTUAL_LOCAL_PROCESS_FIXTURES_NOT_AI_WORKERS',
            'builder': builder, 'reviewer': reviewer_result, 'verifier': verification,
            'crash_after_seal_reconciled': True, 'duplicate_side_effect_count': 1,
            'same_uid_readonly_write_denied': False, 'same_uid_mutation_detected': detected,
            'live_worker_recovery_qualified': False, 'false_pass_process': nonzero,
            'credential_environment': {'parent_presence': parent_presence, 'child_presence': child_presence,
                                       'scope': 'local diagnostic only; no isolated worker authentication'}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--state-dir', type=Path, default=Path.cwd() / '.harness-state/runtime-recovery')
    args = parser.parse_args()
    print(json.dumps(demonstrate(args.repo, args.state_dir), indent=2))


if __name__ == '__main__':
    main()
