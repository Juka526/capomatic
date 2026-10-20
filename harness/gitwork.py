"""Isolated research worktrees, byte snapshots and recoverable commits."""
import hashlib
from pathlib import Path
import shutil
import subprocess


def git(root, *args):
    result = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(root), *args],
                            capture_output=True, check=True)
    return result.stdout.decode().strip()


def manifest(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if '.git' in path.relative_to(root).parts:
            continue
        if path.is_symlink():
            raise ValueError('symlink in snapshot')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


class Worktrees:
    def __init__(self, repo, state):
        self.repo, self.state = repo.resolve(), state.resolve()

    def create(self, task_id, base):
        target = self.state / 'worktrees' / task_id
        target.parent.mkdir(exist_ok=True)
        if not target.exists():
            git(self.repo, 'worktree', 'add', '--detach', str(target), base)
        elif git(target, 'rev-parse', 'HEAD') != base:
            raise ValueError('unexpected existing worktree head')
        return target

    def snapshot(self, worktree, name):
        target = self.state / 'snapshots' / name
        if target.exists():
            raise ValueError('snapshot already exists; refusing to overwrite evidence')
        shutil.copytree(worktree, target, ignore=shutil.ignore_patterns('.git', '__pycache__', '.pytest_cache'))
        before = manifest(target)
        for path in sorted(target.rglob('*'), reverse=True):
            path.chmod(0o555 if path.is_dir() else 0o444)
        target.chmod(0o555)
        return target, before

    def review_snapshot(self, worktree, paths, name):
        """Expose only policy-checked task files, never repository credentials or owner messages."""
        from .policy import Policy
        policy = Policy()
        target = self.state / 'snapshots' / name
        target.mkdir(parents=True, exist_ok=False)
        for name in paths:
            policy.path(name, worktree)
            policy.content((worktree / name).read_bytes())
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((worktree / name).read_bytes())
        files = manifest(target)
        for path in sorted(target.rglob('*'), reverse=True):
            path.chmod(0o555 if path.is_dir() else 0o444)
        target.chmod(0o555)
        return target, files

    def checkpoint(self, root, paths, task_id):
        marker = f'Harness-Task: {task_id}'
        found = git(root, 'log', '--all', '--format=%H', '--fixed-strings', '--grep', marker)
        if found:
            return found.splitlines()[0]
        git(root, 'add', '--', *paths)
        git(root, 'commit', '-m', f'research: {task_id}\n\n{marker}')
        return git(root, 'rev-parse', 'HEAD')
