"""Run with python -m harness; durable state defaults to .harness-state/."""
import argparse
import json
from pathlib import Path
from .approvals import approve_interactive, enqueue
from .controller import Controller
from .doctor import doctor
from .state import Store
from .reports import build_report


def main():
    parser = argparse.ArgumentParser(prog='harness')
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--state-dir', type=Path, default=Path.cwd() / '.harness-state')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    sub.add_parser('herdr-audit')
    sub.add_parser('qualify')
    recover = sub.add_parser('recover-artifact')
    recover.add_argument('--capture-id', required=True)
    for name in ('plan', 'status', 'pause', 'resume', 'stop', 'report'):
        p = sub.add_parser(name)
        p.add_argument('--run-id')
    start = sub.add_parser('start')
    start.add_argument('--mode', choices=['mock', 'pilot', 'herdr-mock', 'herdr-pilot'], default='herdr-mock')
    start.add_argument('--max-tasks', type=int, choices=range(1, 7), default=2)
    approval = sub.add_parser('approvals')
    approval.add_argument('--enqueue', type=Path)
    approval.add_argument('--source-root', type=Path)
    approve = sub.add_parser('approve')
    approve.add_argument('--response', type=Path, required=True)
    approve.add_argument('--evidence', type=Path, required=True)
    approve.add_argument('--source-root', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'herdr-audit':
        from .herdr_audit import audit
        print(json.dumps(audit(), indent=2))
        return
    if args.command == 'doctor':
        print(json.dumps(doctor(), indent=2))
        return
    store = Store(args.state_dir)
    ctl = Controller(args.repo, store)
    if args.command == 'qualify':
        from .qualification import qualify
        print(json.dumps(qualify(args.repo, store), indent=2))
    elif args.command == 'recover-artifact':
        from .capture import Capture
        with store.lock():
            print(json.dumps(Capture(store).recover(args.capture_id), indent=2))
    elif args.command == 'start':
        run_id = ctl.create(args.mode)
        ctl.run(run_id, args.max_tasks)
        print(json.dumps(store.run(run_id), indent=2))
    elif args.command == 'plan':
        run_id = args.run_id or ctl.create()
        print(json.dumps({'run_id': run_id, **ctl.plan(run_id)}, indent=2))
    elif args.command in ('status', 'report'):
        result = build_report(store, args.run_id) if args.command == 'report' else (
            store.run(args.run_id) if args.run_id else store.report()['runs'])
        print(json.dumps(result, indent=2))
    elif args.command in ('pause', 'resume', 'stop'):
        if not args.run_id:
            parser.error('--run-id is required for run controls')
        ctl.control(args.run_id, {'pause': 'PAUSE', 'resume': 'RUN', 'stop': 'STOP'}[args.command])
        if args.command == 'resume':
            ctl.run(args.run_id)
        print(json.dumps(store.run(args.run_id), indent=2))
    elif args.command == 'approvals':
        if args.enqueue:
            if not args.source_root:
                parser.error('--source-root is required when enqueuing')
            enqueue(store, json.loads(args.enqueue.read_text()), args.source_root)
        print(json.dumps(store.report()['approvals'], indent=2))
    else:
        approve_interactive(store, json.loads(args.response.read_text()), args.source_root, args.evidence)


if __name__ == '__main__':
    main()
