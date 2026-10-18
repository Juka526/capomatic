"""Bounded harmony-representation study. Never authorizes or changes V3 guards."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from fractions import Fraction
import hashlib
import inspect
import json
from pathlib import Path
from xml.etree import ElementTree as ET
import zipfile

from backend.omr_v4.visual_graph import safe_xml

RAW_MXL_SHA = '087a7c77b993e76ca03c777191308c8821ea4e5bd7b426a0014119c3fb5f25fd'

LOCATIONS = ((4, Fraction(2)), (20, Fraction(0)), (32, Fraction(3, 4)))
KINDS = {
    'major': {1: 0, 3: 4, 5: 7},
    'minor': {1: 0, 3: 3, 5: 7},
    'dominant': {1: 0, 3: 4, 5: 7, 7: 10},
    'major-seventh': {1: 0, 3: 4, 5: 7, 7: 11},
    'minor-seventh': {1: 0, 3: 3, 5: 7, 7: 10},
    'suspended-fourth': {1: 0, 4: 5, 5: 7},
    'suspended-second': {1: 0, 2: 2, 5: 7},
}
STEP_PC = dict(zip('CDEFGAB', (0, 2, 4, 5, 7, 9, 11)))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')


def xml_harmonies(payload):
    """Read actual harmony snippets with rational onset, not regenerated figures."""
    root = safe_xml(payload, musicxml=True)
    parts = root.findall('part')
    if len(parts) != 1:
        raise ValueError('This diagnostic requires one part')
    divisions, result = 1, {}
    for measure in parts[0].findall('measure'):
        time, previous_note = Fraction(0), Fraction(0)
        for child in measure:
            if child.tag == 'attributes' and child.findtext('divisions'):
                divisions = int(child.findtext('divisions'))
                if divisions <= 0:
                    raise ValueError('Invalid divisions')
            elif child.tag == 'harmony':
                key = (
                    int(measure.get('number')),
                    time + Fraction(child.findtext('offset', '0')) / divisions,
                )
                if key in result:
                    raise ValueError('Duplicate harmony onset')
                result[key] = child
            elif child.tag in {'backup', 'forward'}:
                time += (
                    Fraction(child.findtext('duration', '0'))
                    / divisions
                    * (-1 if child.tag == 'backup' else 1)
                )
            elif child.tag == 'note' and child.find('grace') is None:
                if child.find('chord') is None:
                    previous_note = time
                    time = previous_note + Fraction(child.findtext('duration', '0')) / divisions
    return result


def _pc(element, prefix):
    step = element.findtext(prefix + '-step')
    if step not in STEP_PC:
        raise ValueError('Unsupported pitch step')
    alteration = Fraction(element.findtext(prefix + '-alter', '0'))
    if alteration.denominator != 1:
        raise ValueError('Microtonal harmonies are outside this diagnostic')
    return (STEP_PC[step] + int(alteration)) % 12


def spec_profile(harmony):
    """Small independent MusicXML 4.0 oracle, not a replacement chord parser.

    degree-type=add is dominant-relative, including a MINOR seventh at alter=0.
    Unknown kinds/modifications fail closed; no pitch-class-only equivalence.
    """
    kind = harmony.findtext('kind')
    if kind not in KINDS:
        raise ValueError('Unsupported diagnostic harmony kind: ' + str(kind))
    degrees = dict(KINDS[kind])
    for degree in harmony.findall('degree'):
        value = int(degree.findtext('degree-value'))
        alter = Fraction(degree.findtext('degree-alter'))
        if value < 1 or value > 13 or alter.denominator != 1:
            raise ValueError('Unsupported degree')
        mode = degree.findtext('degree-type')
        if mode == 'add':
            base = (0, 2, 4, 5, 7, 9, 10)[(value - 1) % 7]
            degrees[value] = (base + int(alter)) % 12
        elif mode == 'alter' and value in degrees:
            degrees[value] = (degrees[value] + int(alter)) % 12
        elif mode == 'subtract' and value in degrees:
            del degrees[value]
        else:
            raise ValueError('Unsupported/missing degree operation')
    root = harmony.find('root')
    if root is None:
        raise ValueError('Root required')
    root_pc = _pc(root, 'root')
    bass = harmony.find('bass')
    return {
        'root_pc': root_pc,
        'bass_pc': _pc(bass, 'bass') if bass is not None else None,
        'explicit_bass': bass is not None,
        'degree_profile': sorted(degrees.items()),
        'pitch_classes': sorted({(root_pc + v) % 12 for v in degrees.values()}),
    }


def equivalent_shift(source, target, semitones):
    a, b = spec_profile(source), spec_profile(target)
    return (
        a['degree_profile'] == b['degree_profile']
        and (b['root_pc'] - a['root_pc']) % 12 == semitones % 12
        and a['explicit_bass'] == b['explicit_bass']
        and (not a['explicit_bass'] or (b['bass_pc'] - a['bass_pc']) % 12 == semitones % 12)
    )


def snapshot(score, harmonies):
    from music21 import harmony
    from backend.omr_v3.chords import chord_text
    from backend.chords.parser import parse_chord

    rows = {}
    for number, offset in LOCATIONS:
        measure = score.parts[0].measure(number)
        chords = [
            c
            for c in measure.recurse().getElementsByClass(harmony.ChordSymbol)
            if Fraction(c.getOffsetInHierarchy(measure)) == offset
        ]
        if len(chords) != 1 or (number, offset) not in harmonies:
            raise ValueError('Missing/ambiguous required chord')
        cs = chords[0]
        text = chord_text(cs)
        rows[f'{number}@{offset}'] = {
            'figure': cs.figure,
            'chord_text': text,
            'parsed': asdict(parse_chord(text)),
            'root': cs.root().name,
            'bass': cs.bass().name,
            'kind': cs.chordKind,
            'kind_text': cs.chordKindStr,
            'modifications': [
                (m.modType, m.degree, m.interval.chromatic.semitones)
                for m in cs.getChordStepModifications()
            ],
            'music21_pitch_classes': sorted({p.pitchClass for p in cs.pitches}),
            'pitches': [p.nameWithOctave for p in cs.pitches],
            'xml_harmony': ET.tostring(harmonies[(number, offset)], encoding='unicode'),
            'spec_profile': spec_profile(harmonies[(number, offset)]),
        }
    return rows


def run(inputs, out):
    import copy
    import music21
    from music21 import converter
    from music21.musicxml.m21ToXml import GeneralObjectExporter
    from backend.omr_v3.chords import transpose_chord_text
    from backend.omr_v3.music_guard import validate
    from backend.omr_v3.transpose import transpose_score

    protocol_path = Path(__file__).resolve().parents[2] / 'docs/V4_CHORD_REFERENCE_PROTOCOL.json'
    protocol_sha = sha(protocol_path.read_bytes())
    if protocol_sha != protocol_path.with_suffix('.sha256').read_text().strip():
        raise ValueError('Frozen reference protocol mismatch')
    binding = json.loads(inputs.read_text())
    root = Path(binding['input_root']).resolve()
    output = out.resolve()
    if root == output or root in output.parents or output in root.parents:
        raise ValueError('Read-only evidence/output overlap')
    if out.exists() and any(out.iterdir()):
        raise ValueError('New/empty output directory required')
    for name, expected in binding['files'].items():
        if sha((root / name).read_bytes()) != expected:
            raise ValueError('Input mismatch: ' + name)
    raw = root / 'audiveris.mxl'
    if not raw.is_file():
        raise ValueError('Raw exported MXL required')
    if sha(raw.read_bytes()) != RAW_MXL_SHA:
        raise ValueError('Frozen raw Audiveris hash mismatch')
    with zipfile.ZipFile(raw) as archive:
        if sum(i.file_size for i in archive.infolist()) > 128 * 1024 * 1024:
            raise ValueError('Raw archive size bound')
        container = safe_xml(archive.read('META-INF/container.xml'))
        names = [e.get('full-path') for e in container.iter() if e.tag.split('}')[-1] == 'rootfile']
        if len(names) != 1:
            raise ValueError('One raw rootfile required')
        raw_xml = archive.read(names[0])
    payloads = {'raw_audiveris': raw_xml}
    for label, name in [
        ('pre_ledger', 'pre-ledger.musicxml'),
        ('corrected', 'recognized.musicxml'),
        ('persisted_target', 'transposed.musicxml'),
    ]:
        payloads[label] = (root / name).read_bytes()
    input_hashes = {name: sha((root / name).read_bytes()) for name in binding['files']}
    input_hashes['audiveris.mxl'] = sha(raw.read_bytes())
    # Freeze complete forensic inputs before invoking transformation/export.
    out.mkdir(parents=True)
    dump(out / 'input-bindings.json', input_hashes)
    for data in payloads.values():
        xml_harmonies(data)  # Reject unapproved DTD/entities before library parsing.
    scores = {
        name: converter.parseData(data.decode(), format='musicxml')
        for name, data in payloads.items()
    }
    fresh = copy.deepcopy(scores['corrected'])
    summary = transpose_score(fresh, -2)
    # Snapshot the in-memory state before the exporter can update any lazy caches.
    from music21 import harmony

    memory_fields = {}
    for number, offset in LOCATIONS:
        measure = fresh.parts[0].measure(number)
        cs = [
            c
            for c in measure.recurse().getElementsByClass(harmony.ChordSymbol)
            if Fraction(c.getOffsetInHierarchy(measure)) == offset
        ][0]
        memory_fields[f'{number}@{offset}'] = {
            'kind': cs.chordKind,
            'kind_text': cs.chordKindStr,
            'figure': cs.figure,
            'modifications': [
                (m.modType, m.degree, m.interval.chromatic.semitones)
                for m in cs.getChordStepModifications()
            ],
            'pitch_classes': sorted({p.pitchClass for p in cs.pitches}),
        }
    memory_guard = validate(scores['corrected'], fresh, -2, 'key', summary).to_dict()
    payloads['fresh_serialized'] = GeneralObjectExporter(fresh).parse()
    scores['fresh_serialized'] = converter.parseData(
        payloads['fresh_serialized'].decode(), format='musicxml'
    )
    harmonies = {name: xml_harmonies(data) for name, data in payloads.items()}
    stages = {name: snapshot(scores[name], harmonies[name]) for name in scores}
    expected = {}
    for number, offset in LOCATIONS:
        key = f'{number}@{offset}'
        original_text = stages['corrected'][key]['chord_text']
        region = max(
            (k for k in summary['keys'] if k['measure'] <= number), key=lambda k: k['measure']
        )
        expected[key] = {
            'text': transpose_chord_text(
                original_text, -2, original_key=region['original'], target_key=region['target']
            ),
            'region': region,
            'persisted_xml_spec_equivalent': equivalent_shift(
                harmonies['corrected'][(number, offset)],
                harmonies['persisted_target'][(number, offset)],
                -2,
            ),
            'fresh_roundtrip_spec_equivalent': equivalent_shift(
                harmonies['corrected'][(number, offset)],
                harmonies['fresh_serialized'][(number, offset)],
                -2,
            ),
        }
    source_function = inspect.getsource(harmony.ChordSymbol._adjustPitchesForChordStepModifications)
    result = {
        'scope': 'three frozen chord events; no guard changes or broader equivalence claim',
        'music21_version': music21.__version__,
        'reference_protocol_sha256': protocol_sha,
        'helper_sha256': sha(Path(__file__).read_bytes()),
        'stages': stages,
        'fresh_in_memory': memory_fields,
        'expected_v1_text': expected,
        'guards': {
            'memory': memory_guard,
            'persisted_pair': validate(
                scores['corrected'], scores['persisted_target'], -2, 'key', summary
            ).to_dict(),
            'fresh_roundtrip': validate(
                scores['corrected'], scores['fresh_serialized'], -2, 'key', summary
            ).to_dict(),
        },
        'music21_adjust_function_sha256': sha(source_function.encode()),
        'source_reference': 'music21.harmony.ChordSymbol._adjustPitchesForChordStepModifications/typeAdd',
        'spec_reference': 'https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/degree-alter/',
        'editing_authorized': False,
    }
    for name, expected_hash in input_hashes.items():
        if sha((root / name).read_bytes()) != expected_hash:
            raise ValueError('Inputs changed during analysis: ' + name)
    dump(out / 'harmony-stages.json', result)
    dump(
        out / 'manifest.json',
        {
            'input_sha256': input_hashes,
            'output_sha256': {
                'harmony-stages.json': sha((out / 'harmony-stages.json').read_bytes())
            },
            'source_unchanged': True,
        },
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.inputs, args.out)
    print(
        json.dumps(
            {'guards': result['guards'], 'expected_v1_text': result['expected_v1_text']}, indent=2
        )
    )


if __name__ == '__main__':
    main()
