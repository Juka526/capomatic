"""Independent tool-restricted reviewer; OS containment is additionally mandatory."""
import json
from pathlib import Path
from .process import execute, ProcessFailure
from .schemas import validate


async def review(snapshot, prompt, timeout, env, budget, control=None):
    schema = json.loads((Path(__file__).parent / 'schemas' / 'review.json').read_text())
    argv = ['claude', '-p', '--bare', '--no-chrome', '--output-format', 'json', '--json-schema', json.dumps(schema),
            '--restricted', '--tools', 'Read,Glob,Grep', '--disallowedTools', 'Bash,Edit,Write,NotebookEdit',
            '--permission-mode', 'plan', '--permission-prompts', 'none', '--strict-mcp-config',
            '--mcp-config', '{"mcpServers":{}}', '--setting-sources', '',
            '--disable-slash-commands', '--no-session-persistence', '--max-budget-usd', str(budget)]
    evidence = await execute(argv, snapshot, timeout, env, prompt, control)
    envelope = json.loads(evidence['stdout'])
    if evidence['exit_code'] or envelope.get('is_error'):
        raise ProcessFailure('Claude review failed')
    return validate('review', envelope['structured_output']), evidence
