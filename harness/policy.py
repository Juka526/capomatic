"""Immutable controller-owned capability and provenance boundaries."""
import hashlib
import json
import re
from pathlib import Path, PurePosixPath


class PolicyError(ValueError):
    """A requested capability is not authorized."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Policy:
    def __init__(self):
        self.config_path = Path(__file__).with_name('policy.json')
        self.sha = digest(self.config_path)
        self.data = json.loads(self.config_path.read_text())

    def unchanged(self):
        if digest(self.config_path) != self.sha:
            raise PolicyError('controller policy changed during execution')

    def path(self, name: str, root: Path | None = None):
        p = PurePosixPath(name)
        if (not name.startswith(self.data['allowed_prefix']) or p.is_absolute()
                or '..' in p.parts or '\\' in name or any(x.startswith('.') for x in p.parts)
                or p.suffix not in ('.md', '.txt')
                or p.name.upper() in ('AGENTS.MD', 'CLAUDE.MD', 'RTK.MD')
                or any(ord(c) < 32 for c in name)):
            raise PolicyError(f'forbidden research path: {name}')
        if root:
            full = root / name
            if not full.resolve().is_relative_to(root.resolve()) or any(
                    x.is_symlink() for x in [full, *full.parents] if x != root.parent):
                raise PolicyError('symlink or path escape')

    def task(self, task: dict, completed: set[str]):
        from .schemas import validate
        validate('task', task)
        if task['operation'] != 'research' or not task['paths']:
            raise PolicyError('only bounded research tasks are authorized')
        for name in task['paths']:
            self.path(name)
        if task['id'] in task['depends_on'] or not set(task['depends_on']) <= completed:
            raise PolicyError('invalid or incomplete dependencies')
        if task['requires_owner']:
            raise PolicyError('task requires a bound owner approval')
        if re.search(r'\b(deploy|merge|push|OWNER_VERIFIED_SOURCE|INDEPENDENT_GROUND_TRUTH)\b',
                     task['instruction'], re.I):
            raise PolicyError('instruction requests a protected operation or provenance change')

    def content(self, content: bytes):
        text = content.decode('utf-8')
        if re.search(r'(?:sk-[A-Za-z0-9_-]{16,}|-----BEGIN .*PRIVATE KEY|'
                     r'(?:api_key|password|secret|token)\s*[:=]\s*["\']?\S{8,})', text, re.I):
            raise PolicyError('possible sensitive content')
        if re.search(r'OWNER_VERIFIED_SOURCE|INDEPENDENT_GROUND_TRUTH', text):
            raise PolicyError('autonomous provenance promotion is forbidden')
