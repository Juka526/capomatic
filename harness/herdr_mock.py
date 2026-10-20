"""Explicit fake Herdr service for tests; no terminal or paid agent is launched."""
import json
from pathlib import Path
import uuid
from .gitwork import git
from .herdr_adapter import Disconnected


class MockHerdr:
    simulated = True

    def __init__(self, directory):
        self.path = directory / 'mock-herdr.json'
        self.context = {'mock_server': str(self.path.resolve())}
        self.schema = json.loads(Path(__file__).with_name('herdr_contract.json').read_text())
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {'workspaces': {}, 'panes': {}, 'calls': []}
        self.disconnected = False
        self.drop_after = None

    def save(self):
        self.path.write_text(json.dumps(self.state, sort_keys=True))

    def create_workspace(self, cwd, label):
        workspace_id, pane_id, terminal_id = [uuid.uuid4().hex for _ in range(3)]
        pane = {'pane_id': pane_id, 'workspace_id': workspace_id, 'terminal_id': terminal_id,
                'cwd': cwd, 'agent': None, 'name': None, 'agent_status': 'idle', 'agent_session': None}
        workspace = {'workspace_id': workspace_id, 'label': label}
        self.state['workspaces'][workspace_id] = workspace
        self.state['panes'][pane_id] = pane
        return {'workspace': workspace, 'root_pane': pane, 'tab': {'tab_id': uuid.uuid4().hex}}

    def call(self, args, timeout=15):
        if self.disconnected:
            raise Disconnected('synthetic socket disconnection')
        self.state['calls'].append(args)
        group, operation = args[:2]
        def flag(name):
            return args[args.index(name) + 1]
        if (group, operation) == ('workspace', 'list'):
            result = {'type': 'workspace_list', 'workspaces': list(self.state['workspaces'].values())}
        elif (group, operation) == ('worktree', 'list'):
            result = {'type': 'worktree_list', 'worktrees': [w['worktree'] for w in self.state['workspaces'].values() if 'worktree' in w]}
        elif (group, operation) in (('workspace', 'create'), ('worktree', 'create')):
            cwd = flag('--cwd')
            if group == 'worktree':
                cwd = flag('--path')
                Path(cwd).parent.mkdir(parents=True, exist_ok=True)
                # This is the fake server's implementation of Herdr's worktree API.
                git(Path(flag('--cwd')), 'worktree', 'add', '-b', flag('--branch'), cwd, flag('--base'))
            result = self.create_workspace(cwd, flag('--label'))
            result['type'] = 'worktree_created' if group == 'worktree' else 'workspace_created'
            if group == 'worktree':
                result['worktree'] = {'path': cwd, 'branch': flag('--branch')}
                result['workspace']['worktree'] = result['worktree']
        elif (group, operation) == ('workspace', 'get'):
            result = {'type': 'workspace_info', 'workspace': self.state['workspaces'][args[2]]}
        elif (group, operation) == ('pane', 'list'):
            result = {'type': 'pane_list', 'panes': [p for p in self.state['panes'].values() if p['workspace_id'] == flag('--workspace')]}
        elif (group, operation) == ('agent', 'start'):
            pane = self.state['panes'][flag('--pane')]
            if any(p.get('name') == args[2] for p in self.state['panes'].values()):
                raise ValueError('duplicate live agent name')
            pane.update(agent=flag('--kind'), name=args[2], agent_status='idle',
                        agent_session={'source': 'mock-integration', 'agent': flag('--kind'), 'kind': 'id', 'value': uuid.uuid4().hex})
            result = {'type': 'agent_started', 'agent': pane, 'argv': args[args.index('--') + 1:]}
        elif (group, operation) in (('agent', 'prompt'), ('agent', 'get')):
            pane = self.state['panes'][args[2]]
            if operation == 'prompt':
                pane['agent_status'] = 'done'
            result = {'type': 'agent_prompted' if operation == 'prompt' else 'agent_info', 'agent': pane}
        elif (group, operation) == ('pane', 'run'):
            result = {'type': 'ok'}
        elif (group, operation) == ('notification', 'show'):
            result = {'type': 'notification_show', 'shown': True, 'reason': 'shown'}
        elif (group, operation) == ('workspace', 'close'):
            del self.state['workspaces'][args[2]]
            result = {'type': 'ok'}
        else:
            raise ValueError(f'unimplemented mock API: {args[:2]}')
        self.save()
        if self.drop_after == args[:2]:
            self.drop_after = None
            raise Disconnected('synthetic receipt lost after server mutation')
        # Copy the receipt so later mock mutations cannot change saved observations.
        return json.loads(json.dumps({'id': uuid.uuid4().hex, 'result': result}))

    def restart(self, native_resume=True):
        """Change public pane/terminal IDs; only native session identity may reconcile."""
        panes = {}
        for pane in self.state['panes'].values():
            pane['pane_id'], pane['terminal_id'] = uuid.uuid4().hex, uuid.uuid4().hex
            pane['agent_status'] = 'idle'
            if not native_resume:
                pane.update(agent=None, name=None, agent_session=None)
            panes[pane['pane_id']] = pane
        self.state['panes'] = panes
        self.save()
