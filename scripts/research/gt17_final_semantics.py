"""Research-only explicit lyric extension lineage and MusicXML roundtrip adapter."""

import copy
from fractions import Fraction
import xml.etree.ElementTree as ET
from pathlib import Path

from music21 import stream
from scripts.research.gt11_complete_measure import read, require, events_of
from scripts.research.gt17c_accuracy_audit import OWNER

GROUP_COUNTS = {
    'SYS6_CONTINUATION': 8,
    'SYS7_CONTINUATION': 5,
    'SYS8_CONTINUATION': 4,
    'SYS9_CONTINUATION': 2,
}
RAW = {
    'LYRIC_CONTINUATION_STROKE': '5591 5649 5833 5841 5902 5903 5927 5949 5975 5984 6058 6067 6185 6191 6199 6218 6219 6228 6233'.split(),
    'KOREAN_LYRIC_GLYPH_STROKE': '5660 5896 5948 6127 6150 6189'.split(),
    'ENDING_NUMERAL_PUNCTUATION': '6184 6198'.split(),
}


def source_marks(inventory, graph):
    """Read 30 earlier approved strokes and 20 later visible records; no mirrored rows."""
    marks = []

    def add(ident, m, onset, row, box, origin, held=None):
        matches = [
            e
            for e in inventory['events']
            if e['printed_measure'] == m and Fraction(e['onset']) == Fraction(onset)
        ]
        require(
            len(matches) == 1 and matches[0]['kind'] == 'NOTE', 'Ambiguous stroke event ' + ident
        )
        marks.append(
            {
                'id': ident,
                'measure': m,
                'onset': str(Fraction(onset)),
                'row': row,
                'source_bbox': box,
                'event_id': matches[0]['id'],
                'provenance': origin,
                'held_syllable_candidate': held,
                'classification': 'UNRESOLVED_M28' if m == 28 else 'OWNER_VERIFIED_VISIBLE_STROKE',
            }
        )

    # Earlier approval verifies the tied-note underlay, not a complete source-pixel extent.
    # Do not manufacture a lower-row bbox by mirroring the upper SIG.
    audit = read(
        '/private/tmp/capomatic-v4-gt13a4/gt13a4-final-output/lyric-association-audit.json'
    )
    for m, raw in [(2, '5591'), (4, '5649')]:
        reviewed = next(mm for mm in audit['measures'] if mm['printed_measure'] == m)
        event = next(e for e in reviewed['events'] if e['onset'] == '3')
        require(
            event['classification'] == 'OWNER_VERIFIED_LYRIC_ASSOCIATION'
            and event['candidate_relation'] == 'TIED_CONTINUATION_NO_NEW_SYLLABLE',
            'Missing prior continuation approval',
        )
        for row, key in [(1, 'upper_candidate'), (2, 'lower_candidate')]:
            box = graph['symbols']['sheet#1:' + raw]['geometry']['bbox'] if row == 1 else None
            add(
                f'GT13-m{m}-r{row}',
                m,
                '3',
                row,
                box,
                'GT13A4 owner association; exact lower source extent not persisted',
                event[key],
            )
    base = Path('/private/tmp/capomatic-v4-gt14c/gt14c-final-output')
    d = read(base / 'lyric-continuation-inventory.json')
    for r in d['confirmed_records'] + d['new_candidates']:
        if r.get('symbol_id') == 'sheet#1:5747':
            continue
        add(
            r.get('id', r.get('symbol_id')),
            r['measure'],
            r['onset'],
            r['row'],
            r['source_bbox'],
            'GT14B/GT14D approval',
            r.get('held_syllable', r.get('associated_syllable_candidate')),
        )
    d = read('/private/tmp/capomatic-v4-gt15b/gt15b-final-output/owner-interpretation-layer.json')
    for r in d['items']:
        if r['kind'] == 'CONTINUATION_STROKE':
            c = r['candidate']
            add(
                r['id'],
                c['measure'],
                c['onset_candidate'],
                c['row'],
                c['source_bbox_dark_support'],
                'GT15B owner interpretation',
                c.get('associated_syllable_candidate'),
            )
    d = read('/private/tmp/capomatic-v4-gt16b/gt16b-final-output/owner-interpretation-layer.json')
    for r in d['candidate_continuation_marks']:
        add(
            r['id'],
            r['printed_measure'],
            r['onset_candidate'],
            r['row'],
            r['diagnostic_dark_support_bbox'],
            'GT16B owner interpretation',
        )
    d = read('/private/tmp/capomatic-v4-gt17/gt17-final-output/source-fifth-system-inventory.json')
    for r in d['continuation_candidates']:
        add(
            r['id'],
            r['measure'],
            r['onset'],
            r['row'],
            r['source_dark_bbox'] if 'source_dark_bbox' in r else r['source_object_bbox'],
            'GT17B fifth-system approval',
            r['associated_syllable_candidate'],
        )
    require(len(marks) == 30, 'Earlier visible stroke count mismatch')
    for r in inventory['continuations']:
        add(
            'continuation-' + r['id'],
            r['measure'],
            r['onset'],
            r['row'],
            r['source_dark_bbox'],
            'GT17 FINAL approval' if r['measure'] != 28 else 'Unresolved historical printed stroke',
            r['held_syllable_candidate'],
        )
    require(
        len(marks) == 50 and len({(r['measure'], r['onset'], r['row']) for r in marks}) == 50,
        'Duplicate/missing stroke identity',
    )
    return marks


def lineage(score, marks):
    nodes = []
    for m, measure in enumerate(score.parts[0].getElementsByClass(stream.Measure), 1):
        for j, n in enumerate(events_of(measure)):
            nodes.append(
                {
                    'measure': m,
                    'onset': str(Fraction(n.getOffsetInHierarchy(measure))),
                    'index': j,
                    'note': n,
                }
            )
    positions = {(r['measure'], r['onset']): i for i, r in enumerate(nodes)}
    slurs = {
        tuple(id(n) for n in s.getSpannedElements())
        for s in score.recurse().getElementsByClass('Slur')
    }
    spans, exceptions = [], []
    for mark in marks:
        if mark['measure'] == 28:
            exceptions.append(
                {
                    'stroke_id': mark['id'],
                    'reason': 'M28_HELD_SYLLABLE_ANCESTRY_REPEAT_DEPENDENT_UNRESOLVED',
                }
            )
            continue
        end = positions[(mark['measure'], mark['onset'])]
        row = mark['row']
        start = end
        while start >= 0 and not any(
            l.number == row and l.text for l in nodes[start]['note'].lyrics
        ):
            start -= 1
        reason = None
        if start < 0 or start == end:
            reason = 'NO_DISTINCT_APPROVED_SYLLABLE_ORIGIN'
        else:
            for i in range(start, end):
                a, b = nodes[i]['note'], nodes[i + 1]['note']
                tied = (
                    a.isNote
                    and b.isNote
                    and a.pitch == b.pitch
                    and a.tie
                    and b.tie
                    and a.tie.type in ('start', 'continue')
                    and b.tie.type in ('stop', 'continue')
                )
                slurred = (id(a), id(b)) in slurs
                if not (tied or slurred):
                    reason = 'NO_EXPLICIT_TIE_OR_APPROVED_SLUR_PATH'
                    break
            text = next(l.text for l in nodes[start]['note'].lyrics if l.number == row and l.text)
            if mark.get('held_syllable_candidate') and text != mark['held_syllable_candidate']:
                reason = 'HELD_SYLLABLE_CANDIDATE_DISAGREEMENT'
        if reason:
            exceptions.append({'stroke_id': mark['id'], 'reason': reason})
            continue
        path = [{k: r[k] for k in ('measure', 'onset', 'index')} for r in nodes[start : end + 1]]
        key = (row, tuple((p['measure'], p['index']) for p in path))
        existing = next((s for s in spans if s['key'] == key), None)
        if existing:
            existing['stroke_ids'].append(mark['id'])
        else:
            spans.append(
                {
                    'key': key,
                    'row': row,
                    'text': text,
                    'path': path,
                    'stroke_ids': [mark['id']],
                    'lineage_evidence': 'EXPLICIT_APPROVED_TIE_OR_SLUR_AND_OWNER_VERIFIED_SYLLABLE_ONSET',
                }
            )
    return spans, exceptions


def xml_nodes(root):
    result = {}
    for p, part in enumerate(root.findall('part')):
        require(p == 0, 'Multi-part extension mapping unsupported')
        for m, measure in enumerate(part.findall('measure'), 1):
            require(
                not measure.findall('backup') and not measure.findall('forward'),
                'Ambiguous XML voices',
            )
            for j, n in enumerate(measure.findall('note')):
                result[(m, j)] = n
    return result


def add_extensions(root, spans):
    result = copy.deepcopy(root)
    nodes = xml_nodes(result)
    seen = set()
    require(not result.findall('.//lyric/extend'), 'Base XML already has extensions')
    for span in spans:
        require(len(span['path']) >= 2, 'Extension requires a verified endpoint')
        for i, p in enumerate(span['path']):
            row = str(span['row'])
            key = (p['measure'], p['index'], row)
            require(key not in seen, 'Overlapping semantic extension')
            seen.add(key)
            n = nodes[(p['measure'], p['index'])]
            ls = [l for l in n.findall('lyric') if l.get('number', '1') == row]
            require(len(ls) <= 1, 'Duplicate lyric row')
            if i == 0:
                require(
                    len(ls) == 1
                    and ''.join(t.text or '' for t in ls[0].findall('text')) == span['text'],
                    'Origin lyric mismatch',
                )
            else:
                require(not ls, 'Continuation would overwrite an existing syllable')
            l = ls[0] if ls else ET.SubElement(n, 'lyric', number=row)
            ET.SubElement(
                l,
                'extend',
                type='start' if i == 0 else ('stop' if i == len(span['path']) - 1 else 'continue'),
            )
    return result


def extension_signature(root):
    """Read modern roles and legacy no-type=start, enforcing balanced row-specific spans."""
    open_rows = {}
    completed = []
    for address, n in xml_nodes(root).items():
        for lyric in n.findall('lyric'):
            ex = lyric.findall('extend')
            require(len(ex) <= 1, 'Duplicate extension role')
            row = lyric.get('number', '1')
            text = ''.join(t.text or '' for t in lyric.findall('text'))
            if text and row in open_rows:
                raise ValueError('New lyric before extension stop')
            if not ex:
                continue
            role = ex[0].get('type', 'start')
            require(role in ('start', 'continue', 'stop'), 'Invalid extension role')
            if role == 'start':
                require(row not in open_rows and text, 'Invalid extension start')
                open_rows[row] = {'row': row, 'text': text, 'roles': [(address, role)]}
            else:
                require(row in open_rows and not text, 'Orphan continuation/stop')
                open_rows[row]['roles'].append((address, role))
                if role == 'stop':
                    completed.append(open_rows.pop(row))
    require(not open_rows, 'Unclosed extension')
    return sorted(completed, key=lambda s: (s['roles'][0][0], s['row']))


def strip_extensions(root):
    result = copy.deepcopy(root)
    for n in result.findall('.//note'):
        for l in list(n.findall('lyric')):
            for e in list(l.findall('extend')):
                l.remove(e)
            if len(l) == 0:
                n.remove(l)
    return result


def text_signature(score):
    return [
        [[(l.number, l.text, l.syllabic) for l in n.lyrics if l.text] for n in events_of(m)]
        for m in score.parts[0].getElementsByClass(stream.Measure)
    ]
