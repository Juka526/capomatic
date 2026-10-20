"""Version-qualified Herdr lifecycle API; SQLite and artifacts remain authoritative."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

from .containment import admit_live
from .doctor import doctor
from .herdr_audit import capabilities, local_command
from .policy import PolicyError, Policy
from .budget import Budget


class Disconnected(RuntimeError):
    """Delivery may have occurred; never automatically retry a mutation."""


class NativeSession(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')
    source: str = Field(min_length=1)
    agent: str = Field(min_length=1)
    kind: Literal['id', 'path']
    value: str = Field(min_length=1)


class Pane(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')
    pane_id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    terminal_id: str = Field(min_length=1)
    cwd: str | None = None
    agent: str | None = None
    name: str | None = None
    agent_status: Literal['idle', 'working', 'blocked', 'done', 'unknown']
    agent_session: NativeSession | None = None


class CLI:
    simulated = False

    def __init__(self):
        raw = local_command(['api', 'schema', '--json'])
        if raw.returncode:
            raise PolicyError('Herdr schema unavailable')
        self.schema = json.loads(raw.stdout)
        self.capabilities = capabilities(self.schema)
        for group, fragments in {
                'agent': ['herdr agent start', 'herdr agent prompt', '--wait', '--timeout'],
                'workspace': ['herdr workspace create', '--no-focus'],
                'worktree': ['herdr worktree create', 'herdr worktree open', '--base', '--path'],
                'pane': ['herdr pane run', 'herdr pane current']}.items():
            help_result = local_command([group])
            text = help_result.stdout + help_result.stderr
            if any(fragment not in text for fragment in fragments):
                raise PolicyError(f'installed CLI missing required {group} syntax')
        # These are caller context, not a search for a focused session.
        self.context = {k: os.environ.get(k) for k in ('HERDR_SOCKET_PATH', 'HERDR_WORKSPACE_ID', 'HERDR_PANE_ID')}

    def call(self, args, timeout=15):
        if os.environ.get('HERDR_ENV') != '1' or not self.context['HERDR_SOCKET_PATH']:
            raise PolicyError('live Herdr access requires inherited HERDR_ENV and socket context')
        if any(os.environ.get(k) != v for k, v in self.context.items()):
            raise PolicyError('Herdr caller context changed; reconcile in the original session')
        try:
            result = subprocess.run(['herdr', *args], capture_output=True, text=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Disconnected('Herdr request uncertain; do not resend') from exc
        try:
            body = json.loads(result.stdout if not result.returncode else result.stderr)
        except ValueError as exc:
            raise Disconnected('Herdr returned no valid JSON receipt') from exc
        if result.returncode or 'error' in body:
            raise Disconnected('Herdr rejected or interrupted the request')
        return body


class HerdrAdapter:
    def __init__(self, store, run_id, transport=None):
        self.store, self.run_id = store, run_id
        self.transport = transport or CLI()
        self.simulated = self.transport.simulated
        self.context = self.transport.context
        capabilities(self.transport.schema)

    def _check(self):
        run = self.store.run(self.run_id)
        if run['control'] != 'RUN':
            raise PolicyError('workflow paused or stopped')
        active = self.store.db.execute(
            "SELECT MIN(started) started FROM tasks WHERE run_id=? AND status='ACTIVE'",
            (self.run_id,)).fetchone()['started']
        self.policy = Policy()
        if self.policy.sha != run['policy_sha']:
            raise PolicyError('immutable policy binding changed')
        Budget(self.store, self.policy, self.run_id).check_time(active)

    def call(self, args, kind, timeout=15):
        body = self.transport.call(args, timeout)
        if not isinstance(body, dict) or not isinstance(body.get('id'), str):
            raise PolicyError('malformed Herdr envelope')
        result = body.get('result')
        if not isinstance(result, dict) or result.get('type') != kind:
            raise PolicyError(f'unexpected Herdr result for {args[:2]}')
        return result

    def once(self, key, args, kind, timeout=15):
        self._check()
        key = f'{self.run_id}:herdr:{key}'
        request_sha = hashlib.sha256(json.dumps(args).encode()).hexdigest()
        receipt = self.store.done(key)
        if receipt is not None:
            if receipt.get('request_sha256') != request_sha:
                raise PolicyError('idempotency key reused for a different Herdr request')
            return receipt['result']
        if not self.store.claim(key):
            raise PolicyError('ambiguous Herdr mutation; reconcile, never resend')
        remaining = self.policy.data['max_run_seconds'] - (time.time() - self.store.run(self.run_id)['started'])
        result = self.call(args, kind, min(timeout, remaining))
        self._check()
        self.store.finish(key, {'request_sha256': request_sha, 'result': result})
        with self.store.db:
            self.store.event(self.run_id, 'HERDR_RECEIPT', {'key': key, 'type': kind, 'simulated': self.simulated})
        return result

    def mapping(self, role):
        row = self.store.db.execute('SELECT data FROM herdr_resources WHERE run_id=? AND role=?',
                                    (self.run_id, role)).fetchone()
        return json.loads(row['data']) if row else None

    def save(self, role, result, cwd, owned=True):
        pane = Pane.model_validate(result['root_pane']).model_dump()
        workspace = result['workspace']
        if owned and workspace.get('label') != f'capomatic-{self.run_id}-{role}':
            raise PolicyError('resource creation returned an unowned label')
        if not isinstance(workspace.get('workspace_id'), str) or pane['workspace_id'] != workspace['workspace_id']:
            raise PolicyError('workspace/pane response mismatch')
        if Path(pane['cwd']).resolve() != cwd.resolve():
            raise PolicyError('role cwd does not match provisioned path')
        record = {'pane': pane, 'workspace_id': workspace['workspace_id'], 'label': workspace['label'],
                  'cwd': str(cwd.resolve()), 'context': self.context, 'owned': owned}
        with self.store.db:
            self.store.db.execute('INSERT INTO herdr_resources VALUES(?,?,?)',
                                  (self.run_id, role, json.dumps(record, sort_keys=True)))
        return record

    def bind_controller(self, cwd):
        if self.simulated:
            return self.workspace('controller', cwd)
        saved = self.mapping('controller')
        if saved:
            return self.reconcile('controller')
        pane = self.call(['pane', 'current', '--current'], 'pane_current')['pane']
        workspace = self.call(['workspace', 'get', pane['workspace_id']], 'workspace_info')['workspace']
        record = self.save('controller', {'root_pane': pane, 'workspace': workspace}, cwd, owned=False)
        record['owned'] = False
        with self.store.db:
            self.store.db.execute('UPDATE herdr_resources SET data=? WHERE run_id=? AND role=?',
                                  (json.dumps(record, sort_keys=True), self.run_id, 'controller'))
        return record

    def workspace(self, role, cwd):
        saved = self.mapping(role)
        if saved:
            return self.reconcile(role)
        label = f'capomatic-{self.run_id}-{role}'
        # Never adopt a similarly named user's workspace.
        live = self.call(['workspace', 'list'], 'workspace_list')['workspaces']
        if any(w.get('label') == label for w in live):
            raise PolicyError('unreceipted matching workspace; owner reconciliation required')
        result = self.once(f'workspace:{role}', ['workspace', 'create', '--cwd', str(cwd),
            '--label', label, '--no-focus'], 'workspace_created')
        return self.save(role, result, cwd)

    def worktree(self, role, repo, path, base):
        saved = self.mapping(role)
        if saved:
            self.reconcile(role)
            if saved['cwd'] != str(path.resolve()):
                raise PolicyError('restored worktree path mismatch')
            return saved
        inventory = self.call(['worktree', 'list', '--cwd', str(repo)], 'worktree_list')['worktrees']
        if path.exists() or any(w.get('path') == str(path) for w in inventory):
            raise PolicyError('existing worktree has no owned receipt; refusing adoption')
        branch = f'experiment/harness-{self.run_id}-{role}'
        result = self.once(f'worktree:{role}', ['worktree', 'create', '--cwd', str(repo), '--base', base,
            '--branch', branch, '--path', str(path), '--label', f'capomatic-{self.run_id}-{role}',
            '--no-focus'], 'worktree_created')
        if result['worktree']['path'] != str(path):
            raise PolicyError('Herdr returned an unexpected worktree path')
        return self.save(role, result, path)

    def reconcile(self, role):
        saved = self.mapping(role)
        if not saved or (not saved['owned'] and role != 'controller') or saved['context'] != self.context:
            raise PolicyError('resource ownership/session context mismatch')
        workspace = self.call(['workspace', 'get', saved['workspace_id']], 'workspace_info')['workspace']
        if workspace.get('label') != saved['label']:
            raise PolicyError('workspace identity changed')
        panes = self.call(['pane', 'list', '--workspace', saved['workspace_id']], 'pane_list')['panes']
        candidates = []
        previous = saved['pane']
        for item in panes:
            pane = Pane.model_validate(item).model_dump()
            same_terminal = pane['terminal_id'] == previous['terminal_id']
            session = previous.get('agent_session')
            same_session = session is not None and session == pane.get('agent_session')
            if ((same_terminal or same_session) and pane['workspace_id'] == saved['workspace_id']
                    and pane['cwd'] == saved['cwd']):
                candidates.append(pane)
        if len(candidates) != 1:
            raise PolicyError('missing, duplicated or changed native session; no automatic restart')
        pane = candidates[0]
        if previous.get('agent_session') and pane.get('agent_session') != previous['agent_session']:
            raise PolicyError('resumed native session identity differs')
        saved['pane'] = pane
        with self.store.db:
            self.store.db.execute('UPDATE herdr_resources SET data=? WHERE run_id=? AND role=?',
                                  (json.dumps(saved, sort_keys=True), self.run_id, role))
        return saved

    def start_agent(self, role, kind, args):
        if kind not in ('codex', 'claude'):
            raise PolicyError('unsupported worker')
        if not self.simulated:
            admit_live(doctor())
        saved = self.reconcile(role)
        name = 'h' + hashlib.sha256(f'{self.run_id}:{role}'.encode()).hexdigest()[:24]
        if saved['pane']['agent']:
            if saved['pane'].get('name') != name or saved['pane']['agent'] != kind:
                raise PolicyError('pane occupied by an unexpected agent')
            return saved['pane']
        result = self.once(f'start:{role}', ['agent', 'start', name, '--kind', kind, '--pane',
            saved['pane']['pane_id'], '--timeout', '30000', '--', *args], 'agent_started', 35)
        agent = Pane.model_validate(result['agent']).model_dump()
        if agent['pane_id'] != saved['pane']['pane_id'] or agent['agent'] != kind or agent['name'] != name:
            raise PolicyError('wrong agent started')
        saved['pane'] = agent
        with self.store.db:
            self.store.db.execute('UPDATE herdr_resources SET data=? WHERE run_id=? AND role=?',
                                  (json.dumps(saved, sort_keys=True), self.run_id, role))
        return agent

    def prompt(self, role, dispatch_id, prompt, timeout=30):
        if not self.simulated:
            admit_live(doctor())
        saved = self.reconcile(role)
        pane = saved['pane']
        if pane['agent_status'] not in ('idle', 'done'):
            raise PolicyError('agent is not ready for a new prompt')
        return self.once(f'prompt:{dispatch_id}', ['agent', 'prompt', pane['pane_id'], prompt,
            '--wait', '--timeout', str(int(timeout * 1000))], 'agent_prompted', timeout + 2)

    def observe(self, role):
        saved = self.reconcile(role)
        agent = self.call(['agent', 'get', saved['pane']['pane_id']], 'agent_info')['agent']
        value = Pane.model_validate(agent).model_dump()
        with self.store.db:
            self.store.event(self.run_id, 'HERDR_OBSERVATION', {'role': role, 'state': value['agent_status']})
        return value

    def notify(self, title, body):
        return self.call(['notification', 'show', title, '--body', body, '--sound', 'none'], 'notification_show')

    def cleanup(self, role):
        # No group close, worktree removal, branch deletion or adoption by label.
        saved = self.reconcile(role)
        if not saved['owned']:
            raise PolicyError('refusing cleanup of the caller-owned controller pane')
        if saved['pane']['agent_status'] not in ('idle', 'done'):
            raise PolicyError('refusing cleanup of a working agent')
        return self.once(f'close:{role}', ['workspace', 'close', saved['workspace_id']], 'ok')
