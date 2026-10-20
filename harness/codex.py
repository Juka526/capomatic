"""Codex CLI adapter. No shell, approval bypass or shared worker session."""
from pathlib import Path
from .process import execute, ProcessFailure
from .schemas import load


async def implement(worktree, prompt, timeout, env, control=None):
    schema = Path(__file__).parent / 'schemas' / 'result.json'
    result_file = worktree / 'research/harness_tasks/result.json'
    argv = ['codex', 'exec', '--sandbox', 'workspace-write', '--ignore-user-config',
            '--ephemeral', '--json', '--cd', str(worktree), '--output-schema', str(schema),
            '--output-last-message', str(result_file), '-']
    evidence = await execute(argv, worktree, timeout, env, prompt, control)
    if evidence['exit_code']:
        raise ProcessFailure('Codex failed; inspect durable process evidence')
    result = load('result', result_file.read_text())
    result_file.unlink()
    return result, evidence
