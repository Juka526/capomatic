"""Local capability audit; never returns credential values."""
import importlib.util
import os
import platform
import shutil
import subprocess
import sys

REQUIRED = {
    'codex': ['--sandbox', '--output-schema', '--ignore-user-config', '--ephemeral', '--json'],
    'claude': ['--bare', '--restricted', '--json-schema', '--max-budget-usd', '--tools',
               '--permission-prompts', '--strict-mcp-config', '--setting-sources'],
}


def doctor():
    report = {'python': sys.version.split()[0], 'platform': platform.system(),
              'credentials_present': {k: bool(os.environ.get(k)) for k in
                                      ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY')}, 'cli': {}, 'blockers': []}
    for name, flags in REQUIRED.items():
        executable = shutil.which(name)
        if not executable:
            report['blockers'].append(f'{name} not installed')
            continue
        try:
            version = subprocess.run([executable, '--version'], capture_output=True, text=True, timeout=15)
            help_args = [executable, 'exec', '--help'] if name == 'codex' else [executable, '--help']
            help_result = subprocess.run(help_args, capture_output=True, text=True, timeout=15)
            missing = [f for f in flags if f not in help_result.stdout]
            report['cli'][name] = {'path': executable, 'version': version.stdout.strip(), 'missing_flags': missing}
            if missing or help_result.returncode or version.returncode:
                report['blockers'].append(f'{name} required CLI capabilities unavailable')
        except (OSError, subprocess.TimeoutExpired):
            report['blockers'].append(f'{name} capability audit failed')
    probe = ['sandbox-exec', '-p', '(version 1)(allow default)(deny file-write*)', '/usr/bin/true']
    if platform.system() == 'Darwin' and shutil.which('sandbox-exec'):
        try:
            result = subprocess.run(probe, capture_output=True, text=True, timeout=5)
            report['os_sandbox_probe'] = {'exit_code': result.returncode, 'stderr': result.stderr.strip()}
        except (OSError, subprocess.TimeoutExpired):
            report['os_sandbox_probe'] = {'exit_code': -1}
    else:
        report['os_sandbox_probe'] = {'exit_code': -1}
    if report['os_sandbox_probe']['exit_code']:
        report['blockers'].append('OS containment unavailable in this environment')
    if not report['credentials_present']['ANTHROPIC_API_KEY']:
        report['blockers'].append('ANTHROPIC_API_KEY unavailable to isolated reviewer; subscription auth not imported')
    if not report['credentials_present']['OPENAI_API_KEY']:
        report['blockers'].append('OPENAI_API_KEY unavailable to isolated builder')
    if not importlib.util.find_spec('music21'):
        report['blockers'].append('music21 unavailable for V4/V3 gates')
    # No installed Codex flag bounds monetary usage before an API call.
    report['blockers'].append('Codex hard per-worker cost cap requires an external metered gateway')
    report['blockers'].append('OS worker/verifier launcher not qualified; live dispatch disabled in 0.2')
    report['real_pilot_ready'] = not report['blockers']
    report['level3_ready'] = False
    return report
