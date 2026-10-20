"""Controller-authorized Herdr orchestration and artifact collection."""
import hashlib
import json
from pathlib import Path
import shlex
import sys

from .artifacts import collect, write_simulated
from .gitwork import git, manifest
from .herdr_adapter import HerdrAdapter
from .herdr_mock import MockHerdr
from .policy import PolicyError


class HerdrRuntime:
    def __init__(self, repo, store, run_id, transport=None):
        self.repo, self.store, self.run_id = repo, store, run_id
        self.adapter = HerdrAdapter(store, run_id, transport or MockHerdr(store.directory))
        self.simulated = self.adapter.simulated
        self.adapter.bind_controller(repo)

    def builder_worktree(self, task_id, base):
        role = f'builder-{task_id}'
        path = self.store.directory / 'worktrees' / f'{self.run_id}-{task_id}'
        self.adapter.worktree(role, self.repo, path, base)
        if git(path, 'rev-parse', 'HEAD') != base:
            raise PolicyError('worktree base SHA mismatch')
        return path

    def _dispatch(self, role, task, attempt, base, workspace, input_sha, prompt, payload_factory, outputs):
        expected_phase = {'builder': 'IMPLEMENTING', 'reviewer': 'REVIEWING', 'verifier': 'VERIFYING'}[role]
        if self.store.run(self.run_id)['state'] != expected_phase:
            raise PolicyError('controller has not authorized this role phase')
        dispatch_id = hashlib.sha256(f'{self.run_id}:{task["id"]}:{role}:{attempt}'.encode()).hexdigest()
        expected = {'run_id': self.run_id, 'task_id': task['id'], 'dispatch_id': dispatch_id,
                    'role': role, 'base_sha': base, 'input_sha256': input_sha, 'simulated': self.simulated}
        key = f'{role}-{task["id"]}' if role == 'builder' else f'{role}-{task["id"]}-{attempt}'
        if role != 'builder':
            self.adapter.workspace(key, workspace)
        if role in ('builder', 'reviewer'):
            kind = 'codex' if role == 'builder' else 'claude'
            args = ['--sandbox', 'workspace-write', '--ask-for-approval', 'never'] if role == 'builder' else [
                '--restricted', '--tools', 'Read,Glob,Grep', '--permission-mode', 'plan',
                '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', '--disable-slash-commands']
            self.adapter.start_agent(key, kind, args)
        outbox = self.store.directory / 'artifacts' / dispatch_id
        request = {'identity': expected, 'expected_manifest': str(outbox / 'manifest.json'),
                   'prompt': prompt, 'scope': task['paths'] if role == 'builder' else 'readonly snapshot only'}
        with self.store.db:
            self.store.db.execute('INSERT INTO herdr_dispatches VALUES(?,?,?,?,?)',
                (dispatch_id, self.run_id, key, json.dumps(request, sort_keys=True), 'QUEUED'))
            self.store.event(self.run_id, 'HERDR_QUEUED', {'dispatch_id': dispatch_id, 'role': role})
        if role in ('builder', 'reviewer'):
            self.adapter.prompt(key, dispatch_id, json.dumps(request, sort_keys=True))
            self.adapter.observe(key)  # Observations never determine success.
        else:
            # A trusted controller-defined argv, never a command proposed by an agent.
            request_path = self.store.directory / 'verifier-requests' / f'{dispatch_id}.json'
            request_path.parent.mkdir(exist_ok=True)
            request_path.write_text(json.dumps({'identity': expected, 'workspace': str(workspace),
                                               'outbox': str(outbox), 'dispatch': dispatch_id}))
            command = [sys.executable, '-m', 'harness.verifier_worker', '--request', str(request_path)]
            if not self.simulated:
                from .containment import admit_live
                from .doctor import doctor
                admit_live(doctor())
            pane = self.adapter.reconcile(key)['pane']['pane_id']
            self.adapter.once(f'verifier:{dispatch_id}', ['pane', 'run', pane, shlex.join(command)], 'ok')
        if self.simulated:
            payload = payload_factory()
            write_simulated(outbox, expected, workspace, outputs, payload)
        result = collect(outbox, expected, workspace, outputs)
        with self.store.db:
            self.store.db.execute("UPDATE herdr_dispatches SET status='COLLECTED' WHERE id=?", (dispatch_id,))
            self.store.event(self.run_id, 'HERDR_ARTIFACT', {'dispatch_id': dispatch_id,
                            'manifest': str(outbox / 'manifest.json'), 'simulated': self.simulated})
        return result

    def implement(self, task, attempt, base, worktree, prompt):
        before = hashlib.sha256(json.dumps(manifest(worktree), sort_keys=True).encode()).hexdigest()
        def synthetic():
            target = worktree / task['paths'][0]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('Synthetic Herdr research note.\n' + (
                'Korean lyric validation and repeat playback remain unresolved.\n' if attempt > 1 else ''))
            return {'task_id': task['id'], 'summary': 'simulated Codex via Herdr API',
                    'changed_paths': task['paths'], 'status': 'implemented'}
        return self._dispatch('builder', task, attempt, base, worktree, before, prompt, synthetic, task['paths'])

    def review(self, task, attempt, base, snapshot, snapshot_sha):
        prompt = json.dumps({'task_id': task['id'], 'snapshot_sha256': snapshot_sha,
                             'instruction': 'Review only this source-free implementation snapshot. Return the review schema.'})
        return self._dispatch('reviewer', task, attempt, base, snapshot, snapshot_sha, prompt,
            lambda: {'task_id': task['id'], 'snapshot_sha256': snapshot_sha, 'verdict': 'pass',
                     'findings': [], 'summary': 'simulated Claude via Herdr API'}, [])

    def verify(self, task, attempt, base, snapshot, snapshot_sha, gate):
        return self._dispatch('verifier', task, attempt, base, snapshot, snapshot_sha,
                              'Run only the controller-defined deterministic gates.', gate, [])

    def reconcile_all(self):
        roles = [r['role'] for r in self.store.db.execute(
            'SELECT role FROM herdr_resources WHERE run_id=?', (self.run_id,))]
        return {role: self.adapter.reconcile(role) for role in roles}
