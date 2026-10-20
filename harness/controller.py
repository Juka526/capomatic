"""Persisted bounded controller. Live dispatch remains fail-closed in release 0.2."""
import hashlib
import json
from pathlib import Path
import time
import uuid
from .budget import Budget, BudgetExceeded
from .doctor import doctor
from .gitwork import Worktrees, git, manifest
from .planner import next_task, compile_prompt
from .policy import Policy, PolicyError
from .schemas import validate
from .verify import freeze, verify, check_paths


def tree_sha(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


class Controller:
    def __init__(self, repo, store):
        self.runtime = None
        self.repo, self.store, self.policy = repo.resolve(), store, Policy()
        self.worktrees = Worktrees(repo, store.directory)

    def create(self, mode='mock'):
        if mode not in ('mock', 'pilot', 'herdr-mock', 'herdr-pilot'):
            raise PolicyError('Level 3 activation is not available in 0.2')
        run_id = uuid.uuid4().hex
        with self.store.db:
            self.store.db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?)',
                                  (run_id, 'PLANNING', 'RUN', time.time(), mode, self.policy.sha))
            self.store.event(run_id, 'CREATED', {'mode': mode, 'baseline': self.policy.data['baseline']})
        return run_id

    def context(self, run_id):
        accepted = [dict(r) for r in self.store.db.execute(
            "SELECT id,checkpoint FROM tasks WHERE run_id=? AND status='ACCEPTED' ORDER BY started,id", (run_id,))]
        evidence = [dict(r) for r in self.store.db.execute(
            "SELECT kind,payload FROM events WHERE run_id=? AND kind IN ('CHECKPOINTING','GATE_FAILURE')",
            (run_id,))]
        return {'accepted': accepted, 'actual_results': evidence,
                'approved_scope': self.policy.data['scope'],
                'withheld': self.policy.data['withheld'],
                'blockers': ['independent optical completeness unproven', 'repeat playback withheld'],
                'budget': dict(self.store.db.execute('SELECT COALESCE(SUM(usd),0) spent FROM reservations WHERE key LIKE ?',
                                                           (run_id + ':%',)).fetchone()),
                'seconds_remaining': max(0, self.policy.data['max_run_seconds'] -
                                         (time.time() - self.store.run(run_id)['started']))}

    def plan(self, run_id):
        context = self.context(run_id)
        completed = {r['id'].split(':')[-1] for r in context['accepted']}
        blocked = {r['id'].split(':')[-1] for r in self.store.db.execute(
            "SELECT id FROM tasks WHERE run_id=? AND status='WAITING_OWNER_APPROVAL'", (run_id,))}
        task = next_task(completed, blocked)
        return {'task': task, 'prompt': compile_prompt(task, context) if task else None, 'context': context}

    def recover(self, run_id):
        """Never replay an ambiguous worker or commit action after a crash."""
        run = self.store.run(run_id)
        if run['state'] in ('COMPLETED', 'FAILED', 'BUDGET_EXCEEDED'):
            return
        if run['policy_sha'] != self.policy.sha:
            raise PolicyError('persisted policy differs from executable policy')
        pending = self.store.db.execute("SELECT key FROM actions WHERE status='STARTED' AND key LIKE ?",
                                        (run_id + ':%',)).fetchall()
        if pending:
            if run['state'] != 'BLOCKED':
                self.store.transition(run_id, 'BLOCKED', {'reason': 'ambiguous interrupted action',
                                                        'actions': [r['key'] for r in pending]})
            return
        if run['state'] not in ('PLANNING', 'NEXT_TASK', 'BLOCKED', 'WAITING_OWNER_APPROVAL'):
            self.store.transition(run_id, 'BLOCKED', {'reason': 'interrupted phase requires evidence reconciliation'})

    def control(self, run_id, action):
        if action not in ('RUN', 'PAUSE', 'STOP'):
            raise ValueError('invalid control')
        with self.store.db:
            old = self.store.run(run_id)['control']
            if old == 'STOP' and action != 'STOP':
                raise PolicyError('stopped runs cannot resume')
            self.store.db.execute('UPDATE runs SET control=? WHERE id=?', (action, run_id))
            self.store.event(run_id, 'CONTROL', {'action': action})

    def run(self, run_id, max_tasks=2):
        with self.store.lock():
            self.recover(run_id)
            run = self.store.run(run_id)
            if run['state'] in ('BLOCKED', 'FAILED', 'BUDGET_EXCEEDED', 'COMPLETED'):
                return self.store.report()
            if run['control'] != 'RUN':
                return self.store.report()
            if run['mode'] in ('pilot', 'herdr-pilot'):
                audit = doctor()
                if run['mode'] == 'herdr-pilot':
                    from .herdr_audit import audit as herdr_audit
                    audit['blockers'] += herdr_audit()['blockers']
                    audit['blockers'].append('real Herdr pilot not explicitly authorized')
                self.store.transition(run_id, 'BLOCKED', {'pilot_blockers': audit['blockers']})
                return self.store.report()
            budget = Budget(self.store, self.policy, run_id)
            try:
                if run['mode'] == 'herdr-mock':
                    from .herdr_runtime import HerdrRuntime
                    self.runtime = HerdrRuntime(self.repo, self.store, run_id)
                    self.runtime.reconcile_all()
                for _ in range(min(max_tasks, self.policy.data['max_tasks'])):
                    if self.store.run(run_id)['control'] != 'RUN':
                        break
                    budget.check_time()
                    self.policy.unchanged()
                    count = self.store.db.execute('SELECT COUNT(*) n FROM tasks WHERE run_id=?', (run_id,)).fetchone()['n']
                    if count >= self.policy.data['max_tasks']:
                        raise BudgetExceeded('task count exhausted')
                    if self.store.run(run_id)['state'] == 'NEXT_TASK':
                        self.store.transition(run_id, 'PLANNING')
                    if self.store.run(run_id)['state'] == 'WAITING_OWNER_APPROVAL':
                        self.store.transition(run_id, 'PLANNING')
                    plan = self.plan(run_id)
                    if plan['task'] is None:
                        waiting = self.store.db.execute(
                            "SELECT 1 FROM tasks WHERE run_id=? AND status='WAITING_OWNER_APPROVAL'", (run_id,)).fetchone()
                        self.store.transition(run_id, 'WAITING_OWNER_APPROVAL' if waiting else 'COMPLETED',
                                              {'reason': 'no permitted dependency-ready tasks'})
                        break
                    self._task(run_id, plan, budget)
                    if self.store.run(run_id)['state'] == 'WAITING_OWNER_APPROVAL':
                        self.store.transition(run_id, 'PLANNING')
                        continue
                    if self.store.run(run_id)['state'] != 'NEXT_TASK':
                        break
                if self.store.run(run_id)['state'] == 'NEXT_TASK':
                    waiting = self.store.db.execute(
                        "SELECT 1 FROM tasks WHERE run_id=? AND status='WAITING_OWNER_APPROVAL'", (run_id,)).fetchone()
                    self.store.transition(run_id, 'WAITING_OWNER_APPROVAL' if waiting else 'COMPLETED',
                                          {'reason': 'configured bounded task count reached'})
            except BudgetExceeded as exc:
                self.store.transition(run_id, 'BUDGET_EXCEEDED', {'reason': str(exc)})
            except Exception as exc:
                state = self.store.run(run_id)['state']
                if state != 'BLOCKED':
                    self.store.transition(run_id, 'BLOCKED', {'reason': str(exc)})
            return self.store.report()

    def _task(self, run_id, plan, budget):
        task = plan['task']
        key = f'{run_id}:{task["id"]}'
        self.store.transition(run_id, 'POLICY_CHECK', {'task': task})
        if task['requires_owner']:
            with self.store.db:
                self.store.db.execute('INSERT INTO tasks(id,run_id,spec,status) VALUES(?,?,?,?)',
                                      (key, run_id, json.dumps(task), 'WAITING_OWNER_APPROVAL'))
            self.store.transition(run_id, 'WAITING_OWNER_APPROVAL')
            if self.runtime:
                self.runtime.adapter.notify('Owner review required', task['id'])
            return
        self.policy.task(task, {r['id'].split(':')[-1] for r in self.context(run_id)['accepted']})
        started = time.time()
        with self.store.db:
            self.store.db.execute('INSERT INTO tasks(id,run_id,spec,status,started) VALUES(?,?,?,?,?)',
                                  (key, run_id, json.dumps(task), 'ACTIVE', started))
        accepted = self.context(run_id)['accepted']
        base = accepted[-1]['checkpoint'] if accepted else git(self.repo, 'rev-parse', 'HEAD')
        worktree = (self.runtime.builder_worktree(task['id'], base) if self.runtime else
                    self.worktrees.create(key.replace(':', '-'), base))
        frozen = freeze(worktree)
        evidence_dir = self.store.directory / 'evidence' / key.replace(':', '-')
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / 'prompt.txt').write_text(plan['prompt'])
        (evidence_dir / 'frozen.json').write_text(json.dumps(frozen, sort_keys=True))
        for attempt in range(1, self.policy.data['max_attempts'] + 1):
            budget.check_time(started)
            self.store.transition(run_id, 'IMPLEMENTING', {'attempt': attempt})
            dispatch = f'{key}:build:{attempt}'
            if not self.store.claim(dispatch):
                raise PolicyError('duplicate implementation dispatch')
            budget.reserve(dispatch, 'builder', 0.1)
            with self.store.db:
                self.store.db.execute('UPDATE tasks SET attempts=? WHERE id=?', (attempt, key))
            if self.runtime:
                prompt = plan['prompt'] if attempt == 1 else (evidence_dir / 'revision-prompt.txt').read_text()
                result = self.runtime.implement(task, attempt, base, worktree, prompt)
            else:
                # Deterministic mock exercises the controller, never represents a paid agent.
                target = worktree / task['paths'][0]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('Synthetic research note.\n' + (
                    'Korean lyric validation and repeat playback remain unresolved.\n' if attempt > 1 else ''))
                result = validate('result', {'task_id': task['id'], 'summary': 'simulated implementation',
                                            'changed_paths': task['paths'], 'status': 'implemented'})
            self.store.finish(dispatch, result)
            self.store.transition(run_id, 'REVIEWING')
            check_paths(worktree, frozen, task, self.policy)
            candidate_files = manifest(worktree)
            snapshot, snap_files = self.worktrees.review_snapshot(
                worktree, task['paths'], f'{key.replace(":", "-")}-{attempt}')
            snapshot_hash = tree_sha(snap_files)
            review_key = f'{key}:review:{attempt}'
            if not self.store.claim(review_key):
                raise PolicyError('duplicate review dispatch')
            budget.reserve(review_key, 'reviewer', 0.1)
            review = validate('review', {'task_id': task['id'], 'snapshot_sha256': snapshot_hash,
                'verdict': 'pass', 'findings': [], 'summary': 'simulated independent review'})
            if self.runtime:
                review = self.runtime.review(task, attempt, base, snapshot, snapshot_hash)
            if manifest(snapshot) != snap_files:
                raise PolicyError('reviewer modified its snapshot')
            self.store.finish(review_key, review)
            (evidence_dir / f'review-{attempt}.json').write_text(json.dumps(review, indent=2))
            self.store.transition(run_id, 'VERIFYING')
            budget.check_time(started)
            verifier_snapshot, verifier_files = self.worktrees.snapshot(
                worktree, f'{key.replace(":", "-")}-{attempt}-verifier')
            gate = lambda: verify(verifier_snapshot, frozen, task, self.policy, review, snapshot_hash,
                                  mock=True, git_root=worktree)
            evidence = (self.runtime.verify(task, attempt, base, verifier_snapshot, tree_sha(verifier_files), gate)
                        if self.runtime else gate())
            if manifest(verifier_snapshot) != verifier_files or manifest(worktree) != candidate_files:
                raise PolicyError('candidate or verifier snapshot changed during gates')
            # A controller-injected gate failure tests bounded revision and feedback.
            if attempt == 1:
                with self.store.db:
                    self.store.event(run_id, 'GATE_FAILURE', {'simulated': True, 'reason': 'injected verification failure'})
                feedback = {'feedback': 'synthetic verifier requests explicit blocker note', 'actual_gate_result': evidence}
                (evidence_dir / 'revision-prompt.txt').write_text(compile_prompt(task, {**plan['context'], **feedback}))
                self.store.transition(run_id, 'REVISING', feedback)
                continue
            if manifest(snapshot) != snap_files:
                raise PolicyError('verification changed reviewer snapshot')
            evidence['snapshot_sha256'] = snapshot_hash
            (evidence_dir / 'verification.json').write_text(json.dumps(evidence, indent=2))
            budget.check_time(started)
            self.policy.unchanged()
            if self.store.run(run_id)['control'] != 'RUN':
                raise PolicyError('workflow paused or stopped before checkpoint')
            self.store.transition(run_id, 'CHECKPOINTING', evidence)
            commit_key = f'{key}:commit'
            if not self.store.claim(commit_key):
                raise PolicyError('ambiguous checkpoint; reconcile before retry')
            sha = self.worktrees.checkpoint(worktree, task['paths'], key)
            self.store.finish(commit_key, {'sha': sha})
            with self.store.db:
                self.store.db.execute("UPDATE tasks SET status='ACCEPTED',checkpoint=? WHERE id=?", (sha, key))
            self.store.transition(run_id, 'NEXT_TASK', {'checkpoint': sha, 'simulated': True})
            if self.runtime:
                from .herdr_adapter import Disconnected
                try:
                    self.runtime.adapter.notify('Capomatic checkpoint', f'{task["id"]}: {sha[:12]}')
                except (Disconnected, PolicyError):
                    with self.store.db:
                        self.store.event(run_id, 'NOTIFICATION_UNAVAILABLE', {'task_id': task['id']})
            return
        self.store.transition(run_id, 'FAILED', {'reason': 'revision limit exhausted'})
