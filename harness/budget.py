"""Reserve worst-case worker cost before dispatch; never refund uncertain work."""
import math
import time


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    def __init__(self, store, policy, run_id):
        self.store, self.policy, self.run_id = store, policy.data, run_id

    def check_time(self, task_started=None, now=None):
        now = time.time() if now is None else now
        started = self.store.run(self.run_id)['started']
        if now - started >= self.policy['max_run_seconds']:
            raise BudgetExceeded('run duration exhausted')
        if task_started is not None and now - task_started >= self.policy['max_task_seconds']:
            raise BudgetExceeded('task duration exhausted')

    def reserve(self, key, worker, usd):
        if worker not in ('builder', 'reviewer') or not math.isfinite(usd) or usd <= 0:
            raise ValueError('invalid reservation')
        with self.store.db:
            self.store.db.execute('BEGIN IMMEDIATE')
            if self.store.db.execute('SELECT 1 FROM reservations WHERE key=?', (key,)).fetchone():
                return
            rows = self.store.db.execute('SELECT worker,SUM(usd) n FROM reservations WHERE key LIKE ? GROUP BY worker',
                                         (self.run_id + ':%',)).fetchall()
            spent = {r['worker']: r['n'] for r in rows}
            if (sum(spent.values()) + usd > self.policy['aggregate_usd']
                    or spent.get(worker, 0) + usd > self.policy[f'{worker}_usd']):
                raise BudgetExceeded('reserved cost exceeds configured limit')
            self.store.db.execute('INSERT INTO reservations VALUES(?,?,?)', (key, worker, usd))
