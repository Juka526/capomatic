"""Offline negative checks against frozen source-only readings.

A disagreement excludes a candidate; agreement on these selected checks does
not measure full-page recognition accuracy. Never import this into runtime.
"""
import argparse
import io
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET
import zipfile


def xml_events(data, measure_numbers=None):
    """Read written events without invoking the transposition implementation."""
    root = ET.fromstring(data)
    if len(root.findall('part')) != 1:
        raise ValueError('Expected one part for review checks')
    divisions = 1
    measures = {}
    for measure in root.findall('part/measure'):
        if measure.findtext('attributes/divisions'):
            divisions = int(measure.findtext('attributes/divisions'))
        if measure_numbers is not None and measure.get('number') not in measure_numbers:
            continue
        if measure.find('backup') is not None or measure.find('forward') is not None:
            raise ValueError('Unsupported multivoice/timing structure in measure '+measure.get('number', '?'))
        voices = {n.findtext('voice', '1') for n in measure.findall('note')}
        if len(voices) > 1:
            raise ValueError('Unsupported multiple voices in measure '+measure.get('number', '?'))
        events = []
        for note in measure.findall('note'):
            if note.find('chord') is not None or note.find('grace') is not None:
                raise ValueError('Polyphony/grace requires a complete independent mapping')
            pitch = note.find('pitch')
            name = 'R'
            if pitch is not None:
                alter = int(pitch.findtext('alter', '0'))
                name = pitch.findtext('step') + {0: '', 1: '#', -1: 'b', 2: '##', -2: 'bb'}[alter] + pitch.findtext('octave')
            events.append({'pitch': name, 'duration': str(Fraction(note.findtext('duration')) / divisions),
                           'ties': sorted(t.get('type') for t in note.findall('tie'))})
        number = measure.get('number')
        if number in measures:
            raise ValueError('Duplicate measure number')
        measures[number] = events
    return measures


def sig_location(data, measure_number, event_index):
    """Expose actual SIG IDs for the monophonic written event under review."""
    from backend.omr_v3.scan_ink import relations
    if type(event_index) is not int or event_index < 0:
        raise ValueError('Expected nonnegative integer event index')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        root = ET.fromstring(archive.read('sheet#1/sheet#1.xml'))
    for system in root.findall('page/system'):
        objects = {n.get('id'): n for n in system.findall('sig/inters/*')}
        edges = relations(system)
        for measure in system.findall('part/measure'):
            if measure.get('id') != measure_number:
                continue
            if len(measure.findall('voice')) != 1:
                return {'status': 'UNVERIFIED_MULTIVOICE'}
            events = []
            for entry in measure.findall('voice/slots/entry'):
                value = entry.find('value')
                if value.get('status') != 'BEGIN':
                    continue
                chord = value.get('chord')
                members = [e['target'] for e in edges if e['source'] == chord
                           and e['kind'] == 'containment' and objects[e['target']].tag in {'head', 'rest'}]
                if len(members) != 1:
                    return {'status': 'UNVERIFIED_CHORD_MEMBERSHIP'}
                events.append((int(entry.findtext('key')), chord, members[0]))
            events.sort()
            if event_index >= len(events):
                return {'status': 'EVENT_MISSING'}
            _, chord, ident = events[event_index]
            obj = objects[ident]; bounds = obj.find('bounds')
            return {'status': 'SIG_SLOT_REFERENCE_ONLY', 'page': 1, 'system': system.get('id'),
                    'measure': measure_number, 'chord': chord, 'object': ident,
                    'glyph': obj.get('glyph'), 'region': dict(bounds.attrib) if bounds is not None else None,
                    'relations': [e for e in edges if ident in (e['source'], e['target'])]}
    return {'status': 'MEASURE_MISSING'}


def compare(data, checks):
    """Report selected disagreements; this is not a full accuracy scorer."""
    if not isinstance(checks, list) or not checks:
        raise ValueError('Expected nonempty frozen checks')
    for check in checks:
        if 'measure' not in check or 'expected' not in check:
            raise ValueError('Missing measure or expected reading')
        if 'event_index' in check and (type(check['event_index']) is not int or check['event_index'] < 0):
            raise ValueError('Expected nonnegative integer event index')
        expected = check['expected']
        fields = [expected] if 'event_index' in check else expected
        if not isinstance(fields, list) or not fields or any(not isinstance(f, dict) or not f
                or set(f)-{'pitch', 'duration', 'ties'} for f in fields):
            raise ValueError('Expected explicit pitch, duration or tie fields')
    checked_measures = {str(c['measure']) for c in checks}
    measures = xml_events(data, checked_measures)
    results = []
    for check in checks:
        actual = measures.get(str(check['measure']))
        expected = check['expected']
        if 'event_index' in check:
            index = check['event_index']
            actual = actual[index] if actual is not None and index < len(actual) else None
            if actual is not None:
                actual = {key: actual[key] for key in expected}
        results.append({'measure': str(check['measure']), 'event_index': check.get('event_index'),
                        'expected_from_source_review': expected, 'recognized': actual,
                        'disagreement': expected != actual})
    return {'status': 'SOURCE_REVIEW_DISAGREEMENT' if any(r['disagreement'] for r in results)
            else 'SELECTED_CHECKS_AGREE_FULL_ACCURACY_UNVERIFIED',
            'full_page_accuracy': None, 'checked_measures': sorted(checked_measures),
            'other_measures_unverified': True, 'checks': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('musicxml', type=Path)
    parser.add_argument('checks', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--source-read', type=Path, required=True)
    parser.add_argument('--source-image', type=Path, required=True)
    args = parser.parse_args()
    data = args.musicxml.read_bytes()
    report = compare(data, json.loads(args.checks.read_text()))
    report['recognized_sha256'] = hashlib.sha256(data).hexdigest()
    report['checks_sha256'] = hashlib.sha256(args.checks.read_bytes()).hexdigest()
    report['source_read_sha256'] = hashlib.sha256(args.source_read.read_bytes()).hexdigest()
    report['source_image_sha256'] = hashlib.sha256(args.source_image.read_bytes()).hexdigest()
    report['runtime_injected'] = False
    args.out.write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
