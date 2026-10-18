"""Written-harmony normal form experiment. Never supplies production acceptance."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from fractions import Fraction
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from backend.omr_v4.visual_graph import safe_xml
from scripts.omr_v4.chord_integrity_forensics import (
    KINDS,
    LOCATIONS,
    STEP_PC,
    dump,
    sha,
    xml_harmonies,
)


@dataclass(frozen=True, order=True)
class Spelling:
    step: str
    alter: int

    @property
    def pc(self):
        return (STEP_PC[self.step] + self.alter) % 12


@dataclass(frozen=True)
class WrittenHarmony:
    root: Spelling
    bass: Spelling | None
    # Written degree number and alteration relative to the dominant basis.
    degrees: tuple[tuple[int, int], ...]

    @property
    def pitch_classes(self):
        values = {(self.root.pc + basis(d) + a) % 12 for d, a in self.degrees}
        if self.bass is not None:
            values.add(self.bass.pc)
        return sorted(values)


def basis(degree):
    return (0, 2, 4, 5, 7, 9, 10)[(degree - 1) % 7] + 12 * ((degree - 1) // 7)


def integer(text):
    value = Fraction(text)
    if value.denominator != 1:
        raise ValueError('Microtonal/nonintegral encoding unsupported')
    return int(value)


def single(element, tag, required=True):
    children = element.findall(tag)
    if len(children) != 1 and (required or len(children) > 1):
        raise ValueError('Missing or ambiguous ' + tag)
    return children[0] if children else None


def spelling(element, prefix):
    if set(c.tag for c in element) - {prefix + '-step', prefix + '-alter'}:
        raise ValueError('Unsupported pitch content')
    step = single(element, prefix + '-step').text
    alter_el = single(element, prefix + '-alter', False)
    alter = integer(alter_el.text) if alter_el is not None else 0
    if step not in STEP_PC or abs(alter) > 2:
        raise ValueError('Unsupported root/bass spelling')
    return Spelling(step, alter)


def normalize(payload):
    h = safe_xml(payload)
    if h.tag != 'harmony' or set(c.tag for c in h) - {
        'root',
        'kind',
        'bass',
        'degree',
        'inversion',
    }:
        raise ValueError('Unsupported harmony children')
    root = spelling(single(h, 'root'), 'root')
    bass_el = single(h, 'bass', False)
    bass = spelling(bass_el, 'bass') if bass_el is not None else None
    kind_el = single(h, 'kind')
    kind = kind_el.text
    if kind not in KINDS and kind != 'other':
        raise ValueError('Unsupported MusicXML kind')
    intervals = dict(KINDS.get(kind, {}))
    seen = set()
    for element in h.findall('degree'):
        if set(c.tag for c in element) != {'degree-value', 'degree-alter', 'degree-type'}:
            raise ValueError('Incomplete or unsupported degree')
        degree = integer(single(element, 'degree-value').text)
        alteration = integer(single(element, 'degree-alter').text)
        mode = single(element, 'degree-type').text
        if not 1 <= degree <= 13 or abs(alteration) > 2 or degree in seen:
            raise ValueError('Unsupported or multiply modified degree')
        seen.add(degree)
        if mode == 'add' and degree not in intervals:
            intervals[degree] = basis(degree) + alteration
        elif mode == 'alter' and degree in intervals and kind != 'other':
            intervals[degree] += alteration
        elif mode == 'subtract' and degree in intervals and alteration == 0 and kind != 'other':
            del intervals[degree]
        else:
            raise ValueError('Ambiguous/inapplicable degree operation')
    if intervals.get(1) != 0:
        raise ValueError('Explicit unaltered root degree required')
    inversion_el = single(h, 'inversion', False)
    if inversion_el is not None:
        if len({v % 12 for v in intervals.values()}) != len(intervals):
            raise ValueError('Ambiguous inversion with repeated pitch classes')
        inversion = integer(inversion_el.text)
        ordered = sorted(intervals)
        if not 0 <= inversion < len(ordered):
            raise ValueError('Unsupported inversion')
        expected_bass_pc = (root.pc + intervals[ordered[inversion]]) % 12
        if (bass.pc if bass else root.pc) != expected_bass_pc:
            raise ValueError('Inversion/bass contradiction or implicit nonroot bass')
    degrees = tuple((d, v - basis(d)) for d, v in sorted(intervals.items()))
    if any(abs(alter) > 2 for _, alter in degrees):
        raise ValueError('Unsupported normalized degree alteration')
    result = WrittenHarmony(root, bass, degrees)
    text = kind_el.get('text', '')
    # Only these display suffixes are understood; arbitrary text is not ignored.
    profiles = {
        '': KINDS['major'],
        'm': KINDS['minor'],
        '7': KINDS['dominant'],
        'maj7': KINDS['major-seventh'],
        'M7': KINDS['major-seventh'],
        'm7': KINDS['minor-seventh'],
        'sus4': KINDS['suspended-fourth'],
        'sus2': KINDS['suspended-second'],
        '7sus4': {1: 0, 4: 5, 5: 7, 7: 10},
    }
    if text and (text not in profiles or profiles[text] != intervals):
        raise ValueError('Unsupported/contradictory display text')
    return result


def canonical_xml(harmony):
    """Spec-explicit kind=other; diagnostic XML only, not an engraving target."""
    node = ET.Element('harmony')
    for name, value in [('root', harmony.root), ('bass', harmony.bass)]:
        if value is not None:
            child = ET.SubElement(node, name)
            ET.SubElement(child, name + '-step').text = value.step
            ET.SubElement(child, name + '-alter').text = str(value.alter)
    # MusicXML orders kind before bass.
    kind = ET.Element('kind')
    kind.text = 'other'
    node.insert(1, kind)
    for degree, alteration in harmony.degrees:
        el = ET.SubElement(node, 'degree')
        for name, value in [('value', degree), ('alter', alteration), ('type', 'add')]:
            ET.SubElement(el, 'degree-' + name).text = str(value)
    return ET.tostring(node, encoding='utf-8')


def realization(payload):
    from music21.musicxml.xmlToM21 import MeasureParser

    try:
        cs = MeasureParser().xmlToChordSymbol(safe_xml(payload))
        return {
            'status': 'OBSERVED',
            'figure': cs.figure,
            'pitches': [(p.nameWithOctave, p.midi) for p in cs.pitches],
            'pitch_classes': sorted({p.pitchClass for p in cs.pitches}),
        }
    except (ValueError, TypeError, AttributeError) as exc:
        return {'status': 'UNAVAILABLE', 'error_type': type(exc).__name__}


def diagnose(payload):
    value = normalize(payload)
    normal_xml = canonical_xml(value)
    original = realization(payload)
    canonical = realization(normal_xml)
    return {
        'written': asdict(value),
        'original_xml': payload.decode(),
        'canonical_xml': normal_xml.decode(),
        'xml_roundtrip_preserves_written_harmony': normalize(normal_xml) == value,
        'spec_pitch_classes': value.pitch_classes,
        'original_music21': original,
        'canonical_music21': canonical,
        'original_realization_matches_spec_pitch_classes': original.get('pitch_classes')
        == value.pitch_classes,
        'canonical_realization_matches_spec_pitch_classes': canonical.get('pitch_classes')
        == value.pitch_classes,
        'realized_spelled_pitches_and_octaves_equal': (
            sorted(original['pitches']) == sorted(canonical['pitches'])
            if original['status'] == canonical['status'] == 'OBSERVED'
            else None
        ),
        'printed_equivalence': 'NOT_VALIDATED',
        'production_approval': False,
    }


def conformance_controls():
    """Declared synthetic controls, not annotations or a real-score accuracy set."""

    def xml(kind, degrees='', bass=''):
        return (
            f'<harmony><root><root-step>C</root-step></root><kind>{kind}</kind>{bass}{degrees}</harmony>'
        ).encode()

    def degree(value, alter=0):
        return f'<degree><degree-value>{value}</degree-value><degree-alter>{alter}</degree-alter><degree-type>add</degree-type></degree>'

    major = xml('major')
    dominant = xml('dominant')
    sus = xml('suspended-fourth', degree(7))
    equivalent = xml(
        'dominant',
        '<degree><degree-value>3</degree-value><degree-alter>0</degree-alter><degree-type>subtract</degree-type></degree>'
        + degree(4),
    )
    cases = [
        ('major_vs_minor', major, xml('minor'), False, 'GENUINE_HARMONIC_CHANGE'),
        (
            'minor_vs_major_seventh',
            dominant,
            xml('major-seventh'),
            False,
            'GENUINE_HARMONIC_CHANGE',
        ),
        (
            'added_seventh_alteration',
            sus,
            xml('suspended-fourth', degree(7, 1)),
            False,
            'GENUINE_HARMONIC_CHANGE',
        ),
        (
            'changed_slash_bass',
            xml('major', bass='<bass><bass-step>E</bass-step></bass>'),
            xml('major', bass='<bass><bass-step>G</bass-step></bass>'),
            False,
            'GENUINE_HARMONIC_CHANGE',
        ),
        (
            'lost_slash_bass',
            xml('major', bass='<bass><bass-step>E</bass-step></bass>'),
            major,
            False,
            'GENUINE_HARMONIC_CHANGE',
        ),
        (
            'wrong_root',
            major,
            major.replace(b'<root-step>C', b'<root-step>D'),
            False,
            'GENUINE_HARMONIC_CHANGE',
        ),
        (
            'degree_2_vs_9',
            xml('major', degree(2)),
            xml('major', degree(9)),
            False,
            'WRITTEN_DEGREE_IDENTITY',
        ),
        ('equivalent_sus_encoding', sus, equivalent, True, 'REPRESENTATION_EQUIVALENCE'),
    ]
    rows = []
    for name, left, right, expected, category in cases:
        observed = normalize(left) == normalize(right)
        rows.append(
            {
                'name': name,
                'category': category,
                'left': left.decode(),
                'right': right.decode(),
                'expected_written_equal': expected,
                'observed_written_equal': observed,
                'met_expectation': observed == expected,
            }
        )
    for name, payload in [
        ('unknown_kind', xml('Neapolitan')),
        ('contradictory_display', major.replace(b'<kind>', b'<kind text="m">')),
        ('microtone', major.replace(b'</root-step>', b'</root-step><root-alter>0.5</root-alter>')),
        ('duplicate_degree', xml('suspended-fourth', degree(7) + degree(7))),
    ]:
        try:
            normalize(payload)
            rejected = False
        except ValueError:
            rejected = True
        rows.append(
            {
                'name': name,
                'category': 'UNSUPPORTED_OR_AMBIGUOUS',
                'xml': payload.decode(),
                'rejected': rejected,
                'met_expectation': rejected,
            }
        )
    return rows


def run(manifest, out):
    from music21 import converter
    import music21
    from backend.omr_v3.music_guard import validate
    from backend.omr_v3.chords import chord_text, transpose_chord_text
    from backend.chords.parser import parse_chord
    from music21 import harmony

    binding = json.loads(manifest.read_text())
    root = Path(binding['input_root']).resolve()
    if out.resolve() == root or root in out.resolve().parents or out.resolve() in root.parents:
        raise ValueError('Output overlaps evidence')
    if out.exists() and any(out.iterdir()):
        raise ValueError('New/empty output required')
    for name, digest in binding['files'].items():
        if sha((root / name).read_bytes()) != digest:
            raise ValueError('Input hash mismatch')
    protocol = Path(__file__).resolve().parents[2] / 'docs/V4_CHORD_REFERENCE_PROTOCOL.json'
    if sha(protocol.read_bytes()) != protocol.with_suffix('.sha256').read_text().strip():
        raise ValueError('Frozen protocol mismatch')
    paths = {'source': root / 'recognized.musicxml', 'target': root / 'transposed.musicxml'}
    xml = {name: xml_harmonies(path.read_bytes()) for name, path in paths.items()}
    source, target = (converter.parse(str(paths[k])) for k in ('source', 'target'))
    guard_before = validate(source, target, -2, 'key').to_dict()
    rows = []
    key_regions = json.loads((root / 'semantic-report.json').read_text())['transposition']['keys']
    for number, offset in LOCATIONS:
        pair = {
            name: diagnose(ET.tostring(data[(number, offset)], encoding='utf-8'))
            for name, data in xml.items()
        }
        a = normalize(pair['source']['original_xml'].encode())
        b = normalize(pair['target']['original_xml'].encode())
        region = max((r for r in key_regions if r['measure'] <= number), key=lambda r: r['measure'])
        measure = source.parts[0].measure(number)
        chords = [
            cs
            for cs in measure.recurse().getElementsByClass(harmony.ChordSymbol)
            if Fraction(cs.getOffsetInHierarchy(measure)) == offset
        ]
        if len(chords) != 1:
            raise ValueError('Required semantic chord ambiguous')
        expected_text = transpose_chord_text(
            chord_text(chords[0]), -2, original_key=region['original'], target_key=region['target']
        )
        parsed = parse_chord(expected_text)

        def written_name(value):
            return value.step + ('#' * value.alter if value.alter >= 0 else 'b' * -value.alter)

        expected_spelling = (
            written_name(b.root) == parsed.root
            and (written_name(b.bass) if b.bass else None) == parsed.bass
        )
        rows.append(
            {
                'event': f'{number}@{offset}',
                'expected_v1_text': expected_text,
                'target_root_bass_spelling_matches_v1': expected_spelling,
                'pair': pair,
                'written_degree_shapes_equal': a.degrees == b.degrees,
                'root_interval_correct': (b.root.pc - a.root.pc) % 12 == 10,
                'explicit_bass_presence_equal': (a.bass is None) == (b.bass is None),
                'bass_interval_correct': (
                    (b.bass.pc - a.bass.pc) % 12 == 10 if a.bass and b.bass else a.bass == b.bass
                ),
            }
        )
    guard_after = validate(source, target, -2, 'key').to_dict()
    if guard_before != guard_after:
        raise ValueError('Original score guard changed during diagnostic')
    for name, digest in binding['files'].items():
        if sha((root / name).read_bytes()) != digest:
            raise ValueError('Input changed')
    out.mkdir(parents=True)
    controls = conformance_controls()
    if not all(c['met_expectation'] for c in controls):
        raise ValueError('Conformance negative control failed')
    result = {
        'diagnostic_only': True,
        'schema': 'capomatic.harmony-boundary/1',
        'helper_sha256': sha(Path(__file__).read_bytes()),
        'music21_version': music21.__version__,
        'normal_form': 'root/bass spelling plus dominant-relative written degrees; kind=other explicit add list',
        'cases': rows,
        'controls': controls,
        'boundary_status': 'BLOCKED_FOR_RUNTIME_UNVALIDATED_REALIZATION',
        'full_guard_before': guard_before,
        'full_guard_after': guard_after,
        'bar32_fixed': False,
        'acceptance_waived': False,
        'scope': 'three known events, limited whitelist; not a universal harmony parser or renderer',
        'input_manifest_sha256': sha(manifest.read_bytes()),
        'input_sha256': binding['files'],
        'reference_protocol_sha256': sha(protocol.read_bytes()),
    }
    dump(out / 'boundary-report.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.inputs, args.out)
    print(
        json.dumps(
            {
                'events': len(result['cases']),
                'full_guard': result['full_guard_after'],
                'bar32_fixed': False,
            },
            indent=2,
        )
    )


if __name__ == '__main__':
    main()
