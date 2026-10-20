"""Reviewable report projection without exposing owner response text."""
import json


def build_report(store, run_id=None):
    raw = store.report()
    runs = [r for r in raw['runs'] if run_id is None or r['id'] == run_id]
    ids = {r['id'] for r in runs}
    runtime = []
    for row in store.db.execute('SELECT * FROM herdr_resources'):
        if row['run_id'] in ids:
            data = json.loads(row['data'])
            runtime.append({'run_id': row['run_id'], 'role': row['role'],
                            'pane_id': data['pane']['pane_id'], 'workspace_id': data['workspace_id'],
                            'lifecycle': data['pane']['agent_status'],
                            'native_session_known': bool(data['pane'].get('agent_session'))})
    return {
        'runs': runs,
        'herdr_resources': runtime,
        'tasks': [r for r in raw['tasks'] if r['run_id'] in ids],
        'events': [r for r in raw['events'] if r['run_id'] in ids],
        'approvals': [{'id': r['id'], 'packet_sha256': r['packet_sha'],
                       'answered': r['response'] is not None} for r in raw['approvals']],
        'scope': 'Mock evidence does not establish live readiness or source approval.',
    }
