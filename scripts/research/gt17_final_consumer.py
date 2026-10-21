"""Optional existing MuseScore consumer check; diagnostics only, no renderer substitution."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from backend.omr_v3.core import _run, ScoreError
import xml.etree.ElementTree as ET

from music21 import converter, stream
from backend.omr_v3.music_guard import validate


def extend_records(root):
    return [
        (m, j, l.get('number', '1'), e.get('type', 'start'))
        for m, measure in enumerate(root.findall('./part/measure'), 1)
        for j, n in enumerate(measure.findall('note'))
        for l in n.findall('lyric')
        for e in l.findall('extend')
    ]


def run(directory, output):
    executable = shutil.which('mscore3') or shutil.which('mscore')
    if not executable:
        raise RuntimeError('Existing MuseScore dependency unavailable; no installation attempted')
    output.mkdir(exist_ok=True, parents=True)
    reports = []
    for target in ['Bb', 'A', 'G']:
        source = directory / f'{target}-final-experimental.musicxml'
        dest = output / f'{target}-consumer-roundtrip.musicxml'
        command = [executable, '-o', str(dest), str(source)]
        try:
            with tempfile.TemporaryDirectory(prefix='gt17-native-') as temporary:
                p = _run(command, 120, Path(temporary), 'GT17 MusicXML consumer')
            stdout = p.stdout.decode('utf-8', 'replace')
        except ScoreError as exc:
            reports.append(
                {
                    'target': target,
                    'command': command,
                    'exit_status': None,
                    'status': 'EXTERNAL_CONSUMER_BLOCKED',
                    'error': str(exc),
                    'input_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                }
            )
            for pending in ['Bb', 'A', 'G'][['Bb', 'A', 'G'].index(target) + 1 :]:
                reports.append(
                    {
                        'target': pending,
                        'status': 'NOT_ATTEMPTED_SHARED_CONSUMER_BLOCKER',
                        'exit_status': None,
                    }
                )
            break
        report = {
            'target': target,
            'command': [executable, '-o', str(dest), str(source)],
            'exit_status': p.returncode,
            'stdout': stdout,
            'stderr': '',
            'input_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        }
        if p.returncode == 0 and dest.exists():
            before = converter.parse(str(source))
            after = converter.parse(str(dest))
            report['unchanged_v3_guard'] = validate(before, after, 0, 'key').to_dict()
            a = extend_records(ET.fromstring(source.read_bytes()))
            b = extend_records(ET.fromstring(dest.read_bytes()))
            report.update(
                {
                    'input_extend_records': a,
                    'output_extend_records': b,
                    'exact_event_row_role_records_preserved': a == b,
                    'output_sha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
                    'output_size_bytes': dest.stat().st_size,
                }
            )
        reports.append(report)
    data = {
        'consumer': executable,
        'execution_environment': 'Existing unchanged V3 _run isolated tool environment and temporary working directory',
        'diagnostic_only': True,
        'not_used_for_final_engraving': True,
        'reports': reports,
    }
    (output / 'consumer-validation.json').write_text(
        json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    )
    print(
        json.dumps(
            {
                'targets': [
                    {
                        'target': r['target'],
                        'exit': r['exit_status'],
                        'guard': r.get('unchanged_v3_guard', {}).get('ok'),
                        'extend_records_preserved': r.get('exact_event_row_role_records_preserved'),
                    }
                    for r in reports
                ]
            }
        )
    )


def validate_legacy_origins(root, spans):
    expected = sorted(
        (s['path'][0]['measure'], s['path'][0]['index'], str(s['row']), 'start') for s in spans
    )
    actual = extend_records(root)
    if sorted(actual) != expected:
        raise ValueError('Consumer legacy origins differ from retained approved lineage')
    return len(actual)


def restore_native(directory, output):
    # Endpoint identities come from retained original-side evidence, never inferred
    # from an ambiguous legacy export or the final rendered picture.
    from scripts.research.gt17_final_semantics import (
        strip_extensions,
        add_extensions,
        extension_signature,
    )

    spans = json.loads((directory / 'final-lyric-extender-validation.json').read_text())[
        'semantic_spans'
    ]
    reports = []
    for target in ['Bb', 'A', 'G']:
        path = output / f'{target}-consumer-roundtrip.musicxml'
        root = ET.fromstring(path.read_bytes())
        existing = extend_records(root)
        validate_legacy_origins(root, spans)
        restored = add_extensions(strip_extensions(root), spans)
        expected = extension_signature(
            ET.fromstring((directory / f'{target}-final-experimental.musicxml').read_bytes())
        )
        if extension_signature(restored) != expected:
            raise ValueError('Consumer adapter endpoint mismatch')
        dest = output / f'{target}-consumer-adapted.musicxml'
        dest.write_bytes(
            b'<?xml version="1.0" encoding="utf-8"?>\n'
            + ET.tostring(restored, encoding='utf-8')
            + b'\n'
        )
        guard = validate(converter.parse(str(path)), converter.parse(str(dest)), 0, 'key').to_dict()
        if not guard['ok']:
            raise ValueError('Consumer adapter musical guard failed')
        reports.append(
            {
                'target': target,
                'verified_legacy_start_origins': len(existing),
                'restored_start_stop_records': len(extend_records(restored)),
                'explicit_endpoint_signature_restored': True,
                'unchanged_v3_guard': guard,
                'output_sha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
                'output_size_bytes': dest.stat().st_size,
            }
        )
    (output / 'consumer-adapter-validation.json').write_text(
        json.dumps(
            {
                'method': 'Research-only restoration from retained hash-bound original-side lineage; raw MuseScore re-export alone does not preserve explicit endpoints',
                'raw_consumer_export_loss_not_waived': True,
                'reports': reports,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + '\n'
    )
    print('Restored checked original-side extension lineage after legacy consumer export')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--restore-only', action='store_true')
    a = p.parse_args()
    (restore_native if a.restore_only else run)(a.directory, a.output)
