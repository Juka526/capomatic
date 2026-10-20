"""Dispatch-bound result artifacts; lifecycle badges cannot establish completion."""
import json
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal
from pydantic import Field
from .policy import PolicyError, digest
from .schemas import Structured, Text, SHA, validate


class TaskManifest(Structured):
    run_id: Text
    task_id: Text
    dispatch_id: Text
    role: Literal['builder', 'reviewer', 'verifier']
    base_sha: Annotated[str, Field(pattern=r'^[a-f0-9]{40}$')]
    input_sha256: SHA
    output_hashes: dict[str, SHA]
    payload_sha256: SHA
    status: Literal['reported', 'blocked']
    completion_evidence: dict[str, SHA] = Field(min_length=1)
    simulated: bool


def collect(directory, expected, workspace, allowed_outputs):
    """Read only the controller-selected outbox and exact expected identity."""
    if any(path.is_symlink() for path in (directory, *directory.parents)):
        raise PolicyError('artifact directory symlink escape')
    def file(name):
        p = PurePosixPath(name)
        target = directory / name
        if p.is_absolute() or '..' in p.parts or target.is_symlink() or not target.resolve().is_relative_to(directory.resolve()):
            raise PolicyError('artifact path escape')
        if not target.is_file() or target.stat().st_size > 2_000_000:
            raise PolicyError('missing or oversized task artifact')
        return target
    record = TaskManifest.model_validate_json(file('manifest.json').read_text()).model_dump()
    for name, value in expected.items():
        if record[name] != value:
            raise PolicyError(f'stale or mismatched task artifact: {name}')
    if record['status'] != 'reported' or set(record['output_hashes']) != set(allowed_outputs):
        raise PolicyError('blocked result or unexpected output scope')
    for name, sha in record['output_hashes'].items():
        path = workspace / name
        if not path.resolve().is_relative_to(workspace.resolve()) or path.is_symlink() or digest(path) != sha:
            raise PolicyError('task output hash mismatch')
    if digest(file('payload.json')) != record['payload_sha256']:
        raise PolicyError('task payload hash mismatch')
    if set(record['completion_evidence']) != {'receipt.json'}:
        raise PolicyError('completion receipt missing')
    if digest(file('receipt.json')) != record['completion_evidence']['receipt.json']:
        raise PolicyError('completion receipt hash mismatch')
    receipt = json.loads(file('receipt.json').read_text())
    if receipt.get('dispatch_id') != expected['dispatch_id'] or receipt.get('simulated') != expected['simulated']:
        raise PolicyError('completion receipt identity mismatch')
    payload = json.loads(file('payload.json').read_text())
    role = record['role']
    if role in ('builder', 'reviewer'):
        validate('result' if role == 'builder' else 'review', payload)
        if payload['task_id'] != expected['task_id']:
            raise PolicyError('payload task mismatch')
        if role == 'builder' and (payload['status'] != 'implemented' or
                                   set(payload['changed_paths']) != set(allowed_outputs)):
            raise PolicyError('builder blocked or changed-path receipt mismatch')
    return payload


def write_simulated(directory, expected, workspace, outputs, payload):
    """Test fixture writer, never used by a live worker or as actual test evidence."""
    directory.mkdir(parents=True, exist_ok=False)
    (directory / 'payload.json').write_text(json.dumps(payload, sort_keys=True))
    (directory / 'receipt.json').write_text(json.dumps({'dispatch_id': expected['dispatch_id'], 'simulated': True}))
    record = {**expected, 'output_hashes': {n: digest(workspace / n) for n in outputs},
              'payload_sha256': digest(directory / 'payload.json'), 'status': 'reported',
              'completion_evidence': {'receipt.json': digest(directory / 'receipt.json')}}
    (directory / 'manifest.json').write_text(TaskManifest.model_validate(record).model_dump_json(indent=2))
