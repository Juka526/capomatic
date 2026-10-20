"""Controller-sealed receipts for actual local process tests; no paid dispatch."""
import asyncio
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import uuid
from typing import Literal

from pydantic import Field
from .gitwork import manifest
from .policy import Policy, PolicyError, digest
from .process import execute
from .budget import Budget
from .schemas import Structured, Text, SHA, validate


def inventory(root):
    files = manifest(root)
    return {name: {'sha256': sha, 'mode': (root / name).stat().st_mode & 0o777}
            for name, sha in files.items()}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


class ProcessReceipt(Structured):
    run_id: Text
    task_id: Text
    attempt_id: Text
    role: Literal['builder', 'reviewer', 'verifier']
    kind: Literal['fixture_process', 'deterministic_test']
    base_sha: str = Field(pattern=r'^[a-f0-9]{40}$')
    request_sha256: SHA
    input_sha256: SHA
    output_sha256: SHA
    payload_sha256: SHA
    stdout_sha256: SHA
    stderr_sha256: SHA
    exit_code: int
    pid: int = Field(gt=0)
    started: float
    finished: float
    changed: dict[str, str]


class Capture:
    """The private signing key and ledger must remain outside every worker's filesystem."""
    def __init__(self, store):
        self.store = store
        info = store.directory.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise PolicyError('controller state directory must be private and same-owner')
        self.root = store.directory / 'process-captures'
        self.root.mkdir(exist_ok=True, mode=0o700)
        if self.root.is_symlink() or self.root.stat().st_mode & 0o077:
            raise PolicyError('capture directory must be private and not a symlink')
        key_path = store.directory / 'controller-receipt.key'
        ledger_exists = store.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='process_captures'").fetchone()
        if not key_path.exists() and ledger_exists and store.db.execute('SELECT 1 FROM process_captures LIMIT 1').fetchone():
            raise PolicyError('receipt key missing for existing captures; refusing replacement')
        try:
            fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            fd = None
        if fd is not None:
            with os.fdopen(fd, 'wb') as out:
                out.write(secrets.token_bytes(32))
                out.flush()
                os.fsync(out.fileno())
        if key_path.is_symlink() or key_path.stat().st_mode & 0o077 or key_path.stat().st_uid != os.getuid():
            raise PolicyError('receipt key must be a private controller-owned file')
        self.key = key_path.read_bytes()
        if len(self.key) != 32:
            raise PolicyError('invalid receipt key')
        store.db.execute('''CREATE TABLE IF NOT EXISTS process_captures(
          id TEXT PRIMARY KEY, run_id TEXT NOT NULL, request TEXT NOT NULL,
          status TEXT NOT NULL, pid INTEGER, receipt_sha256 TEXT)''')
        store.db.commit()

    def _write(self, path, value):
        """Exclusive durable publication: a sealed result is never overwritten."""
        raw = canonical(value)
        with path.open('xb') as out:
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        return hashlib.sha256(raw).hexdigest()

    def _key(self, run_id, task_id, role, attempt_id):
        return hashlib.sha256(canonical([run_id, task_id, role, attempt_id])).hexdigest()

    def recover(self, capture_id):
        """Accept an authenticated finished receipt, otherwise block without rerunning anything."""
        row = self.store.db.execute('SELECT * FROM process_captures WHERE id=?', (capture_id,)).fetchone()
        if row is None:
            raise PolicyError('unknown capture')
        directory = self.root / capture_id
        try:
            if directory.is_symlink():
                raise PolicyError('capture directory is a symlink')
            path = directory / 'sealed.json'
            if path.is_symlink() or path.stat().st_size > 2_000_000:
                raise PolicyError('invalid sealed receipt path')
            envelope = json.loads(path.read_text())
            receipt = ProcessReceipt.model_validate(envelope['receipt']).model_dump()
            signature = hmac.new(self.key, canonical(receipt), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(envelope['signature'], signature):
                raise PolicyError('receipt authentication failed')
            request = json.loads(row['request'])
            if receipt['input_sha256'] != request['expected_input_sha256']:
                raise PolicyError('sealed input is not the registered input')
            if receipt['request_sha256'] != hashlib.sha256(canonical(request)).hexdigest():
                raise PolicyError('capture request binding changed')
            for name in ('run_id', 'task_id', 'attempt_id', 'role', 'kind', 'base_sha'):
                if receipt[name] != request[name]:
                    raise PolicyError('capture identity mismatch')
            for name, key in [('payload.json', 'payload_sha256'), ('stdout.txt', 'stdout_sha256'), ('stderr.txt', 'stderr_sha256')]:
                p = directory / name
                if p.is_symlink() or digest(p) != receipt[key]:
                    raise PolicyError('captured evidence changed')
            accepted = digest(path)
            if row['receipt_sha256'] and row['receipt_sha256'] != accepted:
                raise PolicyError('accepted receipt was replaced')
            # Seal input/output byte inventories, not only a claim about them.
            for name, key in [('input.json', 'input_sha256'), ('output.json', 'output_sha256')]:
                p = directory / name
                if p.is_symlink() or digest(p) != receipt[key]:
                    raise PolicyError('captured filesystem inventory changed')
            if inventory(Path(request['workspace'])) != json.loads((directory / 'output.json').read_text()):
                raise PolicyError('workspace differs from sealed output')
            if receipt['exit_code'] != 0:
                raise PolicyError('actual process failed; exit code is not zero')
            if row['status'] == 'ACCEPTED':
                return {'capture_id': capture_id, 'receipt': receipt,
                        'payload': json.loads((directory / 'payload.json').read_text())}
            with self.store.db:
                self.store.db.execute("UPDATE process_captures SET status='ACCEPTED',receipt_sha256=? WHERE id=?",
                                      (accepted, capture_id))
                self.store.event(receipt['run_id'], 'PROCESS_CAPTURE_ACCEPTED',
                                 {'capture_id': capture_id, 'receipt_sha256': accepted, 'kind': receipt['kind']})
            return {'capture_id': capture_id, 'receipt': receipt,
                    'payload': json.loads((directory / 'payload.json').read_text())}
        except (OSError, ValueError, KeyError) as exc:
            with self.store.db:
                self.store.db.execute("UPDATE process_captures SET status='BLOCKED' WHERE id=?", (capture_id,))
            raise PolicyError(f'capture blocked; no action replay: {exc}') from exc

    async def run(self, run_id, task, role, base, workspace, argv, *, attempt_id=None,
                  kind='fixture_process', timeout=5, after_seal=None, review_sha=None):
        """Capture a trusted local diagnostic argv. This entry point cannot run paid workers."""
        if kind not in ('fixture_process', 'deterministic_test') or role not in ('builder', 'reviewer', 'verifier'):
            raise PolicyError('paid workers and unqualified process kinds are disabled')
        validate('task', task)
        Policy().task(task, set())
        # Local fixture/test execution is not an alternative worker launch interface.
        if Path(argv[0]).resolve() != Path(__import__('sys').executable).resolve():
            raise PolicyError('only the trusted Python diagnostic/test interpreter is admitted')
        if not argv[1:] or not (argv[1] == '-c' or list(argv[1:3]) == ['-m', 'pytest']):
            raise PolicyError('only controller-defined Python probes or pytest processes admitted')
        if timeout <= 0 or timeout > 300:
            raise PolicyError('capture timeout outside pilot diagnostic bound')
        run = self.store.run(run_id)
        if run['policy_sha'] != Policy().sha:
            raise PolicyError('capture policy binding changed')
        Budget(self.store, Policy(), run_id).check_time()
        if run['control'] != 'RUN':
            raise PolicyError('run is paused or stopped')
        attempt_id = attempt_id or uuid.uuid4().hex
        if len(attempt_id) != 32 or any(c not in '0123456789abcdef' for c in attempt_id):
            raise PolicyError('attempt ID must be a UUID hex string')
        workspace = workspace.resolve()
        if workspace.is_relative_to(self.store.directory) or self.store.directory.is_relative_to(workspace):
            raise PolicyError('worker/test workspace and controller state must be disjoint')
        before = inventory(workspace)
        expected_input = hashlib.sha256(canonical(before)).hexdigest()
        if role == 'reviewer' and review_sha != expected_input:
            raise PolicyError('review input hash is not the actual immutable inventory')
        request = {'task': task, 'expected_input_sha256': expected_input, 'run_id': run_id, 'task_id': task['id'], 'attempt_id': attempt_id, 'role': role,
                   'kind': kind, 'base_sha': base, 'workspace': str(workspace), 'argv': list(argv),
                   'timeout': timeout, 'review_sha': review_sha}
        capture_id = self._key(run_id, task['id'], role, attempt_id)
        with self.store.lock():
            old = self.store.db.execute('SELECT request FROM process_captures WHERE id=?', (capture_id,)).fetchone()
            if old:
                original = json.loads(old['request'])
                stable_original = {k: v for k, v in original.items() if k != 'expected_input_sha256'}
                stable_request = {k: v for k, v in request.items() if k != 'expected_input_sha256'}
                if stable_original != stable_request:
                    raise PolicyError('capture identity reused with different command or scope')
                return self.recover(capture_id)
            with self.store.db:
                self.store.db.execute("INSERT INTO process_captures VALUES(?,?,?,'CLAIMED',NULL,NULL)",
                                      (capture_id, run_id, json.dumps(request, sort_keys=True)))
            directory = self.root / capture_id
            directory.mkdir(mode=0o700)
            if inventory(workspace) != before:
                raise PolicyError('input changed before process launch')
            input_sha = self._write(directory / 'input.json', before)
            def spawned(pid):
                with self.store.db:
                    self.store.db.execute("UPDATE process_captures SET status='RUNNING',pid=? WHERE id=?", (pid, capture_id))
            result = None
            try:
                result = await execute(argv, workspace, timeout,
                    env={'PATH': '/usr/bin:/bin', 'HOME': str(directory / 'empty-home'),
                         'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'}, on_spawn=spawned,
                    control=lambda: self.store.run(run_id)['control'])
                (directory / 'stdout.txt').write_text(result['stdout'])
                (directory / 'stderr.txt').write_text(result['stderr'])
                after = inventory(workspace)
                changed = {n: ('added' if n not in before else 'deleted' if n not in after else 'modified')
                           for n in before.keys() | after.keys() if before.get(n) != after.get(n)}
                if role == 'builder':
                    if not changed or not set(changed) <= set(task['paths']) or 'deleted' in changed.values():
                        raise PolicyError('actual process diff violates task scope')
                    for name in changed:
                        Policy().path(name, workspace)
                        Policy().content((workspace / name).read_bytes())
                elif changed:
                    raise PolicyError('reviewer/verifier changed its input filesystem')
                if role == 'verifier':
                    payload = {'actual_exit_code': result['exit_code'], 'kind': kind}
                else:
                    payload = validate('result' if role == 'builder' else 'review', json.loads(result['stdout']))
                    if payload['task_id'] != task['id']:
                        raise PolicyError('structured process report task mismatch')
                    if role == 'builder' and (payload['status'] != 'implemented' or set(payload['changed_paths']) != set(changed)):
                        raise PolicyError('builder report differs from actual filesystem changes')
                    if role == 'reviewer' and (payload['snapshot_sha256'] != review_sha or payload['verdict'] != 'pass' or payload['findings']):
                        raise PolicyError('review is not bound to the reviewed input or requests changes')
                receipt = {'run_id': run_id, 'task_id': task['id'], 'attempt_id': attempt_id,
                    'role': role, 'kind': kind, 'base_sha': base, 'request_sha256': hashlib.sha256(canonical(request)).hexdigest(),
                    'input_sha256': input_sha, 'output_sha256': self._write(directory / 'output.json', after),
                    'payload_sha256': self._write(directory / 'payload.json', payload),
                    'stdout_sha256': digest(directory / 'stdout.txt'), 'stderr_sha256': digest(directory / 'stderr.txt'),
                    'exit_code': result['exit_code'], 'pid': result['pid'], 'started': result['started'],
                    'finished': result['finished'], 'changed': changed}
                receipt = ProcessReceipt.model_validate(receipt).model_dump()
                self._write(directory / 'sealed.json', {'receipt': receipt,
                    'signature': hmac.new(self.key, canonical(receipt), hashlib.sha256).hexdigest()})
                with self.store.db:
                    self.store.db.execute("UPDATE process_captures SET status='SEALED' WHERE id=?", (capture_id,))
                if after_seal:
                    after_seal(capture_id)
                return self.recover(capture_id)
            except BaseException as exc:
                failure = getattr(exc, 'process_evidence', None) or result
                if failure is not None and not (directory / 'sealed.json').exists():
                    failure = {**failure, 'acceptance_error': type(exc).__name__}
                    self._write(directory / 'failure.json', failure)
                    with self.store.db:
                        self.store.db.execute("UPDATE process_captures SET status='FAILED' WHERE id=?", (capture_id,))
                # Preserve ambiguous state and every existing byte for owner reconciliation.
                with self.store.db:
                    self.store.event(run_id, 'PROCESS_CAPTURE_INTERRUPTED', {'capture_id': capture_id})
                raise
