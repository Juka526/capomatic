"""Controller-owned verification. Agent reports never substitute for process output."""
import json
from pathlib import Path
import subprocess
import sys
from .gitwork import git, manifest
from .policy import digest, PolicyError
from .schemas import validate


def freeze(repo):
    """Bind every tracked baseline byte, including historical evidence and production."""
    names = subprocess.check_output(['git', '-C', str(repo), 'ls-files', '-z']).decode().split('\0')
    return {name: digest(repo / name) for name in names if name}


def check_frozen(root, frozen):
    for name, sha in frozen.items():
        path = root / name
        if not path.is_file() or path.is_symlink() or digest(path) != sha:
            raise PolicyError(f'frozen file changed or missing: {name}')


def check_external(root):
    binding = json.loads((root / 'docs/evidence/GT16B_OWNER_BINDING.json').read_text())
    for name, sha in binding['files'].items():
        path = Path(name) if name.startswith('/') else root / name
        if not path.is_file() or digest(path) != sha:
            raise PolicyError(f'approved source packet missing or changed: {name}')
    if binding['independent_ground_truth'] or binding['repeat_playback_route'] != 'EXPLICITLY_WITHHELD':
        raise PolicyError('source provenance contract violated')



def check_baseline(root, baseline_manifest=None):
    path = baseline_manifest or Path(__file__).parent.parent / 'docs/harness/baseline-sha256.json'
    frozen = json.loads(path.read_text())
    check_frozen(root, frozen['files'])
    return len(frozen['files'])


def check_history(root):
    checked = 0
    for path in sorted((root / 'docs').glob('V4*VALIDATION.json')):
        record = json.loads(path.read_text())
        hashes = record.get('artifact_sha256', {})
        directory = record.get('output_directory') or record.get('local_output_directory')
        if hashes and not directory:
            raise PolicyError(f'historical artifact directory not bound: {path.name}')
        for name, sha in hashes.items():
            artifact = Path(directory) / name
            if not artifact.is_file() or digest(artifact) != sha:
                raise PolicyError(f'historical artifact missing or changed: {artifact}')
            checked += 1
    return checked

def check_paths(root, frozen, task, policy):
    actual = manifest(root)
    changed = {n for n in set(actual) | set(frozen) if actual.get(n) != frozen.get(n)}
    tracked_changes = subprocess.check_output(
        ['git', '-C', str(root), 'diff', '--name-only', '-z', 'HEAD']).decode().split('\0')
    changed.update(name for name in tracked_changes if name)
    if not changed or not changed <= set(task['paths']):
        raise PolicyError(f'changed-file allowlist failed: {sorted(changed)}')
    for name in changed:
        policy.path(name, root)
        content = (root / name).read_bytes()
        policy.content(content)
        whitespace = subprocess.run(['git', 'diff', '--no-index', '--check', '--', '/dev/null',
                                     str(root / name)], capture_output=True, text=True)
        if whitespace.returncode not in (0, 1) or whitespace.stdout or whitespace.stderr:
            raise PolicyError('whitespace error in changed file')
    check_frozen(root, frozen)
    return sorted(changed)


def verify(root, frozen, task, policy, review, snapshot_sha, mock=False):
    validate('review', review)
    if review['task_id'] != task['id'] or review['snapshot_sha256'] != snapshot_sha or review['verdict'] != 'pass' or review['findings']:
        raise PolicyError('review does not approve this exact snapshot')
    changed = check_paths(root, frozen, task, policy)
    diff = git(root, 'diff', '--check')
    evidence = {'paths': changed, 'diff': diff, 'review': review, 'simulated': mock}
    if mock:
        evidence['gates'] = {'synthetic_preservation': True}
        return evidence
    evidence['baseline_files'] = check_baseline(root)
    check_external(root)
    evidence['historical_artifacts'] = check_history(root)
    tests = sorted(str(p.relative_to(root)) for p in (root / 'tests').glob('test_*v4*.py'))
    tests += ['tests/test_omr_v3_gate.py', 'tests/test_omr_v3_eval.py']
    if not tests:
        raise PolicyError('required tests missing')
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', *tests],
                            cwd=root, capture_output=True, text=True, timeout=900,
                            env={**__import__('os').environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    evidence['regression'] = {'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
    if result.returncode or ' skipped' in result.stdout:
        raise PolicyError('deterministic regression failed or skipped')
    # 0.1 permits text research only; image changes are rejected before this point.
    evidence['alpha_collision_clipping'] = 'not applicable: no image or rendering edits permitted'
    check_frozen(root, frozen)
    return evidence
