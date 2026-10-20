"""Transactional event journal and single-controller lease."""
import contextlib
import fcntl
import json
import sqlite3
import time
from pathlib import Path

STATES = set('PLANNING POLICY_CHECK IMPLEMENTING REVIEWING VERIFYING REVISING '
             'CHECKPOINTING NEXT_TASK WAITING_OWNER_APPROVAL BLOCKED FAILED '
             'BUDGET_EXCEEDED COMPLETED'.split())
TRANSITIONS = {
    'PLANNING': {'POLICY_CHECK', 'BLOCKED', 'COMPLETED', 'WAITING_OWNER_APPROVAL'},
    'POLICY_CHECK': {'IMPLEMENTING', 'WAITING_OWNER_APPROVAL', 'BLOCKED'},
    'IMPLEMENTING': {'REVIEWING', 'FAILED', 'BLOCKED'},
    'REVIEWING': {'VERIFYING', 'REVISING', 'BLOCKED', 'FAILED'},
    'VERIFYING': {'REVISING', 'CHECKPOINTING', 'BLOCKED', 'FAILED'},
    'REVISING': {'IMPLEMENTING', 'FAILED'},
    'CHECKPOINTING': {'NEXT_TASK', 'BLOCKED'},
    'NEXT_TASK': {'PLANNING', 'COMPLETED', 'WAITING_OWNER_APPROVAL'},
    'WAITING_OWNER_APPROVAL': {'PLANNING', 'BLOCKED'},
    'BLOCKED': {'PLANNING'},
}


class Store:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        if self.directory.is_relative_to(Path('/private/tmp')) or self.directory.is_relative_to(Path('/tmp')):
            raise ValueError('state must live outside temporary storage')
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        (self.directory / '.gitignore').write_text('*\n')
        self.db = sqlite3.connect(self.directory / 'state.sqlite3', timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, state TEXT NOT NULL,
            control TEXT NOT NULL, started REAL NOT NULL, mode TEXT NOT NULL, policy_sha TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
            spec TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
            started REAL, checkpoint TEXT);
          CREATE TABLE IF NOT EXISTS actions(key TEXT PRIMARY KEY, status TEXT NOT NULL, result TEXT);
          CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY, run_id TEXT,
            at REAL NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS reservations(key TEXT PRIMARY KEY, worker TEXT NOT NULL,
            usd REAL NOT NULL CHECK(usd >= 0));
          CREATE TABLE IF NOT EXISTS herdr_dispatches(id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
            role TEXT NOT NULL, request TEXT NOT NULL, status TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS herdr_resources(run_id TEXT NOT NULL, role TEXT NOT NULL,
            data TEXT NOT NULL, PRIMARY KEY(run_id,role));
          CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY, packet TEXT NOT NULL,
            packet_sha TEXT NOT NULL, response TEXT);
        ''')

    @contextlib.contextmanager
    def lock(self):
        with (self.directory / 'controller.lock').open('a') as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError('another controller is active') from exc
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def event(self, run_id, kind, payload):
        self.db.execute('INSERT INTO events(run_id,at,kind,payload) VALUES(?,?,?,?)',
                        (run_id, time.time(), kind, json.dumps(payload, sort_keys=True)))

    def transition(self, run_id, state, payload=None):
        if state not in STATES:
            raise ValueError(state)
        with self.db:
            old = self.run(run_id)['state']
            if state not in ('BUDGET_EXCEEDED', 'BLOCKED') and state not in TRANSITIONS.get(old, set()):
                raise ValueError(f'invalid transition {old} -> {state}')
            self.db.execute('UPDATE runs SET state=? WHERE id=?', (state, run_id))
            self.event(run_id, state, payload or {})

    def run(self, run_id):
        row = self.db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone()
        if row is None:
            raise ValueError('unknown run')
        return dict(row)

    def claim(self, key):
        with self.db:
            return self.db.execute("INSERT OR IGNORE INTO actions VALUES(?,'STARTED',NULL)",
                                   (key,)).rowcount == 1

    def finish(self, key, result):
        with self.db:
            self.db.execute("UPDATE actions SET status='DONE', result=? WHERE key=?",
                            (json.dumps(result), key))

    def done(self, key):
        row = self.db.execute('SELECT * FROM actions WHERE key=?', (key,)).fetchone()
        return json.loads(row['result']) if row and row['status'] == 'DONE' else None

    def report(self):
        return {table: [dict(r) for r in self.db.execute(f'SELECT * FROM {table}')]
                for table in ('runs', 'tasks', 'events', 'reservations', 'approvals', 'actions')}
