"""Stateless installed-CLI audit; live inspection requires inherited Herdr context."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tomllib

REQUIRED_METHODS = {
    'workspace.create', 'workspace.list', 'workspace.get', 'workspace.close',
    'worktree.create', 'worktree.open', 'worktree.list', 'pane.get', 'pane.list',
    'agent.start', 'agent.get', 'agent.prompt', 'agent.wait', 'notification.show',
}


def local_command(args):
    return subprocess.run(['herdr', *args], capture_output=True, text=True, timeout=15)


def capabilities(schema):
    methods = {v['properties']['method']['const'] for v in schema['schemas']['request']['oneOf']}
    missing = sorted(REQUIRED_METHODS - methods)
    if schema.get('protocol') != 22 or schema.get('schema_version') != 1 or missing:
        raise ValueError(f'unqualified Herdr API protocol or missing methods: {missing}')
    return {'protocol': schema['protocol'], 'methods': sorted(methods)}


def audit():
    result = {'available': bool(shutil.which('herdr')), 'inside_herdr': os.environ.get('HERDR_ENV') == '1',
              'live_inspection': 'not attempted outside Herdr', 'settings_changed': False,
              'plugins_installed': False, 'blockers': [], 'settings': {}}
    if not result['available']:
        result['blockers'].append('Herdr is not installed')
        return result
    try:
        version = local_command(['--version'])
        result['version'] = version.stdout.strip()
        raw = local_command(['api', 'schema', '--json'])
        if raw.returncode:
            raise ValueError('Herdr schema command failed')
        result['schema_sha256'] = hashlib.sha256(raw.stdout.encode()).hexdigest()
        result['capabilities'] = capabilities(json.loads(raw.stdout))
        integrations = local_command(['integration', 'status'])
        result['integrations'] = {k: {'status': status, 'version': int(v)} for k, status, v in
                                  re.findall(r'^(codex|claude): (\w+) \(v(\d+)\)', integrations.stdout, re.M)}
        result['help'] = {}
        for group in ('agent', 'workspace', 'pane', 'worktree', 'session', 'plugin', 'notification'):
            help_result = local_command([group])
            result['help'][group] = help_result.stdout + help_result.stderr
        for file in (Path.home() / '.codex/config.toml', Path.home() / '.codex/hooks.json',
                     Path.home() / '.claude/settings.json',
                     Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'herdr/config.toml'):
            if not file.is_file():
                continue
            raw_config = file.read_bytes()
            config = tomllib.loads(raw_config.decode()) if file.suffix == '.toml' else json.loads(raw_config)
            result['settings'][str(file)] = {
                'sha256': hashlib.sha256(raw_config).hexdigest(),
                'hook_event_names': sorted(config.get('hooks', {})),
                'has_herdr_reference': b'herdr' in raw_config,
                'has_notify': 'notify' in config,
                'native_restore_setting': config.get('session', {}).get('resume_agents_on_restore'),
            }
        if result['inside_herdr']:
            # Only inspect the inherited session; never discover or select a focused session.
            status = local_command(['status', 'server'])
            result['live_inspection'] = {'exit_code': status.returncode}
            if status.returncode:
                result['blockers'].append('inherited server/socket unavailable')
        else:
            result['blockers'].append('HERDR_ENV=1 absent; socket/session/plugin inventory not inspected')
        result['blockers'].append('isolated worker settings must preserve reviewed native-session hooks')
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result['blockers'].append(str(exc))
    return result
