"""Fail-closed live-worker admission boundary for release 0.2."""
import os
from pathlib import Path
from .policy import PolicyError


def worker_environment(home: Path, worker: str):
    """Pass only runtime essentials and the selected API credential, never app secrets."""
    if worker not in ('builder', 'reviewer'):
        raise ValueError('unknown worker')
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': str(home),
           'LANG': 'en_US.UTF-8', 'TMPDIR': str(home), 'PYTHONDONTWRITEBYTECODE': '1'}
    if worker == 'builder':
        env['CODEX_HOME'] = str(home / 'codex')
        credential = 'OPENAI_API_KEY'
    else:
        env['CLAUDE_CONFIG_DIR'] = str(home / 'claude')
        credential = 'ANTHROPIC_API_KEY'
    if os.environ.get(credential):
        env[credential] = os.environ[credential]
    return env


def admit_live(audit):
    """No configuration toggle can substitute for qualifying the OS launcher and cost cap."""
    if not audit.get('real_pilot_ready') or audit.get('blockers'):
        raise PolicyError('live dispatch denied: ' + '; '.join(audit.get('blockers', ['unqualified environment'])))
    # Deliberately a code-level gate: owner must review a qualified launcher release.
    raise PolicyError('Harness 0.2 has no qualified OS launcher; use mock mode')
