"""Explicit owner-requested GT-16C research-note example through fake Herdr only."""
import argparse
import json
from pathlib import Path
from .controller import Controller
from .planner import compile_prompt
from .state import Store

TASK = {'id': 'gt16c-readiness-note', 'operation': 'research',
        'paths': ['research/harness_tasks/gt16c-readiness.md'], 'depends_on': [], 'requires_owner': False,
        'instruction': 'Summarize GT-16C adaptive engraving readiness and optical collision validation blockers. '
                       'Produce only a research note; no music, rendering or source edits.'}


class ExampleController(Controller):
    def plan(self, run_id):
        context = self.context(run_id)
        done = any(row['id'].endswith(':' + TASK['id']) for row in context['accepted'])
        task = None if done else dict(TASK)
        return {'task': task, 'prompt': compile_prompt(task, context) if task else None, 'context': context}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--state-dir', type=Path, default=Path.cwd() / '.harness-state/gt16c-example')
    args = parser.parse_args()
    store = Store(args.state_dir)
    controller = ExampleController(args.repo, store)
    run_id = controller.create('herdr-mock')
    controller.run(run_id, max_tasks=1)
    dispatches = [json.loads(row['request']) for row in store.db.execute(
        'SELECT request FROM herdr_dispatches WHERE run_id=?', (run_id,))]
    print(json.dumps({'run': store.run(run_id), 'task': TASK, 'dispatches': dispatches,
                      'paid_workers_invoked': False, 'classification': 'MOCK_RESEARCH_NOTE_ONLY'}, indent=2))


if __name__ == '__main__':
    main()
