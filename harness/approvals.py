"""Source-only packets; only an interactive owner may bind a genuine response."""
import hashlib
import json
import sys
from pathlib import Path
from .policy import digest, PolicyError
from .schemas import validate


def packet_sha(packet):
    return hashlib.sha256(json.dumps(packet, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def validate_packet(packet, source_root):
    validate('packet', packet)
    if packet['owner_answer'] is not None or packet['owner_corrections'] is not None:
        raise PolicyError('new packet cannot contain an invented owner answer')
    if set(packet['candidate_ids']) != set(packet['interpretations']):
        raise PolicyError('interpretations must match candidate scope exactly')
    for name, sha in packet['manifest'].items():
        path = source_root / name
        if Path(name).is_absolute() or not path.resolve().is_relative_to(source_root.resolve()):
            raise PolicyError('packet source path escape')
        if path.is_symlink() or not path.is_file() or digest(path) != sha:
            raise PolicyError('packet manifest mismatch')
    if not set(packet['images']) <= set(packet['manifest']):
        raise PolicyError('source images are not hash-bound')
    for name in packet['images']:
        if Path(name).suffix.lower() not in ('.png', '.jpg', '.jpeg'):
            raise PolicyError('review images must be source images')


def enqueue(store, packet, source_root):
    validate_packet(packet, source_root)
    sha = packet_sha(packet)
    with store.db:
        existing = store.db.execute('SELECT packet_sha FROM approvals WHERE id=?', (packet['id'],)).fetchone()
        if existing and existing['packet_sha'] != sha:
            raise PolicyError('request ID already bound to different source packet')
        store.db.execute('INSERT OR IGNORE INTO approvals VALUES(?,?,?,NULL)',
                         (packet['id'], json.dumps(packet, sort_keys=True), sha))
    return sha


def record_response(store, response, source_root, evidence_path, owner_identity):
    validate('approval', response)
    row = store.db.execute('SELECT * FROM approvals WHERE id=?', (response['request_id'],)).fetchone()
    if not row:
        raise PolicyError('unknown approval request')
    packet = json.loads(row['packet'])
    validate_packet(packet, source_root)
    if (row['packet_sha'] != response['packet_sha256']
            or set(packet['candidate_ids']) != set(response['candidate_ids'])
            or response['owner_identity'] != owner_identity
            or digest(evidence_path) != response['source_response_sha256']
            or evidence_path.read_text().strip() != response['response_text'].strip()):
        raise PolicyError('owner response does not bind this packet and evidence')
    if response['answer'] == 'correct' and not response['corrections'].strip():
        raise PolicyError('correction answer requires corrections')
    encoded = json.dumps(response, sort_keys=True)
    with store.db:
        if row['response'] == encoded:
            return
        if row['response'] and row['response'] != encoded:
            raise PolicyError('response already recorded; create a new packet for changes')
        store.db.execute('UPDATE approvals SET response=? WHERE id=?', (encoded, response['request_id']))
        store.event(None, 'OWNER_RESPONSE', {'request_id': response['request_id'], 'packet_sha': row['packet_sha']})


def approve_interactive(store, response, source_root, evidence_path):
    if not sys.stdin.isatty():
        raise PolicyError('owner approval requires an interactive owner terminal')
    identity = input('Owner identity (attributable to the source response): ').strip()
    print(json.dumps(response, indent=2))
    confirm = input('Type the exact packet SHA-256 to attest this is your genuine response: ').strip()
    if confirm != response['packet_sha256']:
        raise PolicyError('owner attestation mismatch')
    record_response(store, response, source_root, evidence_path, identity)
