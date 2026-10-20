"""Runtime qualification records observations, never grants execution authority."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import time
import uuid

from .doctor import doctor
from .herdr_audit import audit, local_command
from .herdr_adapter import Pane
from .policy import PolicyError

STARTING_SHA = '3bf1e9ff9b8f53cb7bb219eff6a17a859a7ce71b'


def session_audit():
    """Verify only the inherited caller's socket and pane, never a focused session."""
    names = ('HERDR_ENV', 'HERDR_PANE_ID', 'HERDR_WORKSPACE_ID', 'HERDR_SOCKET_PATH')
    env = {n: os.environ.get(n) for n in names}
    report = {'status': 'BLOCKED', 'inside_herdr': env['HERDR_ENV'] == '1',
              'pane_context_present': bool(env['HERDR_PANE_ID']),
              'socket_context_present': bool(env['HERDR_SOCKET_PATH']), 'live_requests': 0}
    if env['HERDR_ENV'] != '1' or any(not env[n] for n in names[1:]):
        report['reason'] = 'Inherited authorized Herdr pane/socket context is absent; no live session inspected'
        return report
    try:
        socket = Path(env['HERDR_SOCKET_PATH'])
        info = socket.lstat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
            raise PolicyError('Herdr socket is not a same-owner Unix socket')
        report['live_requests'] += 1
        proc = local_command(['pane', 'current', '--current'])
        if proc.returncode:
            raise PolicyError('inherited pane query failed')
        result = json.loads(proc.stdout)['result']
        if result.get('type') != 'pane_current':
            raise PolicyError('unexpected caller-pane response')
        pane = Pane.model_validate(result['pane'])
        if pane.pane_id != env['HERDR_PANE_ID'] or pane.workspace_id != env['HERDR_WORKSPACE_ID']:
            raise PolicyError('caller pane ownership/context mismatch')
        report.update(status='VERIFIED_CALLER_ONLY', socket_owner_matches=True,
                      pane_id=pane.pane_id, workspace_id=pane.workspace_id,
                      reason='Caller verified; worker operation and restoration still require real qualification')
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        report['reason'] = str(exc)
    return report


def isolation_audit(directory):
    """Probe sandbox startup with synthetic canaries; no secret or source is accessed."""
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    case = directory / f'case-{time.time_ns()}'
    case.mkdir(mode=0o700)
    canary = case / 'protected-canary.txt'
    canary.write_text('synthetic, not a credential or protected score\n')
    marker = case / 'child-started'
    result = {'status': 'BLOCKED', 'system': platform.system(), 'vm_candidates': {},
              'negative_access_tests': 'NOT_RUN', 'secrets_used': False, 'paid_workers': 0}
    for name in ('docker', 'podman', 'limactl', 'colima', 'qemu-system-aarch64'):
        result['vm_candidates'][name] = bool(shutil.which(name))
    if shutil.which('docker'):
        try:
            proc = subprocess.run(['docker', 'version', '--format', '{{json .}}'],
                                  capture_output=True, text=True, timeout=10)
            data = json.loads(proc.stdout) if proc.stdout else {}
            result['docker'] = {'exit_code': proc.returncode, 'client_version': data.get('Client', {}).get('Version'),
                                'server_available': bool(data.get('Server')), 'error': proc.stderr.strip()[:1000]}
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            result['docker'] = {'server_available': False, 'error': str(exc)}
    if platform.system() == 'Darwin' and shutil.which('sandbox-exec'):
        script = ('import json,pathlib,sys; '
                  'p=pathlib.Path(sys.argv[1]); '
                  'print(json.dumps({"child_started":True}),flush=True); '
                  'p.write_text("unexpected write"); '
                  'pathlib.Path(sys.argv[2]).read_bytes()')
        # Startup is necessary, but not sufficient. If it succeeds, evaluate write/read separately below.
        profile = '(version 1)(allow default)(deny file-write*)(deny file-read* (literal ' + json.dumps(str(canary)) + '))'
        try:
            proc = subprocess.run(['sandbox-exec', '-p', profile, sys.executable, '-c', script,
                                   str(marker), str(canary)], capture_output=True, text=True, timeout=5,
                                  env={'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'PYTHONDONTWRITEBYTECODE': '1'})
            result['seatbelt'] = {'exit_code': proc.returncode, 'stdout': proc.stdout[:1000],
                                  'stderr': proc.stderr[:1000], 'child_marker_exists': marker.exists()}
            started = '"child_started": true' in proc.stdout
            result['negative_access_tests'] = 'INCOMPLETE_WRITE_PROBE' if started else 'NOT_RUN_LAUNCHER_FAILED'
            if started:
                # An independent read probe is mandatory; write denial alone is insufficient.
                read = subprocess.run(['sandbox-exec', '-p', profile, sys.executable, '-c',
                                       'import pathlib,sys; pathlib.Path(sys.argv[1]).read_bytes()', str(canary)],
                                      capture_output=True, text=True, timeout=5,
                                      env={'PATH': os.environ.get('PATH', '/usr/bin:/bin')})
                result['seatbelt']['read_exit_code'] = read.returncode
                result['negative_access_tests'] = 'LIMITED_CANARY_DENIAL' if proc.returncode and read.returncode and not marker.exists() else 'FAILED'
        except (OSError, subprocess.TimeoutExpired) as exc:
            result['seatbelt'] = {'error': str(exc)}
    result['reason'] = ('No qualified builder/reviewer VM or OS launcher. Canary probes, even if denied, '
                        'do not qualify personal-file, socket, credential, process or network isolation.')
    return result


def credentials_audit():
    """Do not copy, print or authenticate with ambient user credentials."""
    return {'status': 'UNVERIFIED', 'ambient_presence_only': {n: bool(os.environ.get(n)) for n in
            ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY')}, 'provider_auth_requests': 0,
            'credentials_copied': False, 'actual_worker_auth_verified': False,
            'reason': 'No isolated worker environment or separately scoped worker credentials qualified'}


def cost_audit():
    return {'status': 'UNVERIFIED_ACCOUNT_CONFIGURATION',
            'openai': {'documented_hard_limits': True, 'enforcement_instantaneous': False,
                       'account_project_binding_verified': False,
                       'source': 'https://developers.openai.com/api/docs/guides/spend-limits'},
            'anthropic': {'documented_workspace_spend_limits': True, 'account_workspace_binding_verified': False,
                          'source': 'https://platform.claude.com/docs/en/manage-claude/workspaces'},
            'time_or_request_limits_are_monetary_caps': False, 'provider_settings_changed': False,
            'reason': 'No readback of dedicated account limits, residual allowance, billing route or overshoot bound'}


def qualify(repo, store):
    """Prepare exactly one harmless task; missing evidence cannot be replaced by a flag."""
    herdr = audit()
    from .gitwork import git
    from .policy import Policy
    task = {'id': 'runtime-pilot-note', 'operation': 'research',
            'paths': ['research/harness_tasks/runtime-pilot.md'], 'depends_on': [],
            'requires_owner': False,
            'instruction': 'Write a short harmless runtime research note from the qualification summary. '
                           'Do not edit any source evidence, production or policy files.'}
    Policy().task(task, set())
    report = {'prepared_task': task, 'observed_head': git(repo, 'rev-parse', 'HEAD'), 'version': '0.3', 'starting_sha': STARTING_SHA, 'generated_at': time.time(),
              'herdr': herdr, 'session': session_audit(),
              'isolation': isolation_audit(store.directory / 'isolation-probes'),
              'credentials': credentials_audit(), 'cost': cost_audit(), 'cli': doctor(),
              'pilot': {'status': 'BLOCKED', 'paid_authorization': 'NOT_GRANTED', 'paid_workers_invoked': 0,
                        'max_tasks': 1, 'max_codex_implementations': 1, 'max_claude_reviews': 1,
                        'proposed_timeout_seconds': 300, 'proposed_usd_ceiling': '2.00',
                        'next_prompt': 'propose only; never dispatch'},
              'level3_ready': False}
    report['blockers'] = [
        'authorized in-Herdr worker context not qualified', 'OS containment not qualified',
        'actual isolated worker authentication and permissions not qualified',
        'account-bound monetary enforcement and overshoot allowance not qualified',
        'live Codex/Claude capture and real-worker restart recovery not qualified',
        'mandatory skip-free regression evidence not qualified in a reproducible runtime', 'explicit paid execution authorization absent',
    ]
    directory = store.directory / 'qualifications'
    directory.mkdir(exist_ok=True)
    path = directory / f'{uuid.uuid4().hex}.json'
    encoded = json.dumps(report, indent=2, sort_keys=True)
    with path.open('x') as out:
        out.write(encoded + '\n')
    with store.db:
        store.event(None, 'RUNTIME_QUALIFICATION', {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                                'pilot': 'BLOCKED'})
    return report
