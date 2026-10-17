"""Bounded, ID-based reading of Audiveris 5.11 SIG data in raster coordinates."""

from __future__ import annotations

import hashlib
import math
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, replace
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

MAX_XML_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_MEMBERS = 200
MAX_PIXELS = 40_000_000
Point = tuple[float, float]
Box = tuple[float, float, float, float]  # left, top, right, bottom


class GraphError(ValueError):
    """Input cannot safely establish a visual graph."""


def safe_xml(data: bytes, *, musicxml: bool = False) -> ET.Element:
    """Reject DTDs/entities and bound XML, including alternate-encoding bypasses."""
    if len(data) > MAX_XML_BYTES or b'\0' in data:
        raise GraphError('XML too large or unsupported encoding')
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise GraphError('XML must be UTF-8') from exc
    # music21 emits this external identifier; it is removed, never resolved.
    if musicxml:
        text = re.sub(
            r'<!DOCTYPE score-partwise\s+PUBLIC\s+"-//Recordare//DTD MusicXML [\d.]+ Partwise//EN"\s+"https?://www.musicxml.org/dtds/partwise.dtd"\s*>',
            '',
            text,
        )
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise GraphError('DTD/entities are not accepted')
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise GraphError('Malformed XML') from exc
    pending = [(root, 0)]
    count = 0
    while pending:
        el, depth = pending.pop()
        count += 1
        if depth > 64 or count > 500_000:
            raise GraphError('XML structure exceeds limits')
        pending.extend((child, depth + 1) for child in el)
    return root


def finite(value: str | None) -> float:
    number = float(value)
    if not math.isfinite(number) or abs(number) > 1_000_000:
        raise ValueError('invalid coordinate')
    return number


def quarter(value: str) -> Fraction:
    result = Fraction(value) * 4
    if result < 0 or result > 100_000 or result.denominator > 1_000_000:
        raise ValueError('invalid time')
    return result


def union(boxes) -> Box | None:
    values = [b for b in boxes if b is not None]
    return (
        (
            min(b[0] for b in values),
            min(b[1] for b in values),
            max(b[2] for b in values),
            max(b[3] for b in values),
        )
        if values
        else None
    )


@dataclass(frozen=True)
class Geometry:
    bbox: Box | None = None
    pivot: Point | None = None
    line: tuple[Point, ...] = ()
    curve: tuple[Point, ...] = ()  # start, control1, control2, end
    location: Point | None = None
    thickness: float | None = None
    valid: bool = True

    @property
    def region(self) -> Box | None:
        if not self.valid:
            return None
        points = self.line + self.curve
        box = None
        if points:
            pad = (self.thickness or 0) / 2
            box = (
                min(p[0] for p in points) - pad,
                min(p[1] for p in points) - pad,
                max(p[0] for p in points) + pad,
                max(p[1] for p in points) + pad,
            )
        return union((self.bbox, box))

    @property
    def center(self) -> Point | None:
        if not self.valid:
            return None
        if self.pivot:
            return self.pivot
        if self.bbox:
            x1, y1, x2, y2 = self.bbox
            return ((x1 + x2) / 2, (y1 + y2) / 2)
        return None


@dataclass(frozen=True)
class VisualSymbol:
    id: str
    source_id: str
    kind: str
    page: str
    system: str
    staff: str | None
    shape: str | None
    pitch_position: float | None
    grade: float | None
    contextual_grade: float | None
    geometry: Geometry
    relation_ids: tuple[str, ...]
    attributes: tuple[tuple[str, str], ...]
    source_xml: str  # Retain unsupported fields without interpreting them as geometry.

    @property
    def confidence(self) -> float:
        return self.contextual_grade if self.contextual_grade is not None else self.grade or 0.0


@dataclass(frozen=True)
class Relation:
    id: str
    kind: str
    source: str
    target: str
    attributes: tuple[tuple[str, str], ...] = ()
    source_xml: str = ''


@dataclass(frozen=True)
class Staff:
    id: str
    source_id: str
    page: str
    system: str
    part: str
    number: int  # staff number within the logical part
    interline: float
    lines: tuple[tuple[Point, ...], ...]
    valid: bool
    source_xml: str


@dataclass(frozen=True)
class Slot:
    id: str
    x: float | None
    offset: Fraction | None
    suspicious: bool = False


@dataclass(frozen=True)
class Measure:
    id: str
    number: str
    page: str
    system: str
    part: str
    bounds: Box | None
    slots: tuple[Slot, ...]
    duration: Fraction | None
    symbol_ids: tuple[str, ...]
    # (chord ID, slot ID, voice ID); only BEGIN entries establish an onset.
    onsets: tuple[tuple[str, str, str], ...]
    source_xml: str
    stack_source_xml: str


@dataclass(frozen=True)
class System:
    id: str
    page: str
    bounds: Box | None
    staff_ids: tuple[str, ...]


@dataclass(frozen=True)
class Page:
    id: str  # sheet#N, independent of logical page numbering
    width: int
    height: int
    interline: float


@dataclass(frozen=True)
class ProtectedRegion:
    id: str
    page: str
    kind: str
    bbox: Box | None
    symbol_ids: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class VisualScoreGraph:
    pages: tuple[Page, ...]
    systems: tuple[System, ...]
    staves: tuple[Staff, ...]
    measures: tuple[Measure, ...]
    symbols: dict[str, VisualSymbol]
    relations: tuple[Relation, ...]
    text_protected_regions: tuple[ProtectedRegion, ...]
    issues: tuple[str, ...]
    invalid_geometry_count: int
    unsupported_constructs: tuple[str, ...]

    def neighbors(self, symbol_id: str, kinds: set[str] | None = None) -> tuple[str, ...]:
        """Return adjacent symbol IDs, optionally restricted by edge kind."""
        return tuple(
            sorted(
                {
                    r.target if r.source == symbol_id else r.source
                    for r in self.relations
                    if symbol_id in (r.source, r.target) and (kinds is None or r.kind in kinds)
                }
            )
        )

    def summary(self) -> dict:
        """Return parser coverage and diagnostics, without recognition claims."""
        return {
            'pages': len(self.pages),
            'systems': len(self.systems),
            'staves': len(self.staves),
            'measures': len(self.measures),
            'node_categories': dict(sorted(Counter(s.kind for s in self.symbols.values()).items())),
            'relation_categories': dict(sorted(Counter(r.kind for r in self.relations).items())),
            'nonfinite_invalid_geometry_count': self.invalid_geometry_count,
            'unsupported_constructs': self.unsupported_constructs,
            'issues': self.issues,
            'protected_regions_without_bounds': sum(
                p.bbox is None for p in self.text_protected_regions
            ),
        }


_SYMBOL_KINDS = {
    'head',
    'head-chord',
    'small-chord',
    'stem',
    'beam',
    'beam-hook',
    'small-beam',
    'beam-group',
    'flag',
    'small-flag',
    'augmentation-dot',
    'alter',
    'ledger',
    'key',
    'key-alter',
    'clef',
    'time-pair',
    'time-whole',
    'time-number',
    'time-top-bottom',
    'slur',
    'word',
    'sentence',
    'lyric-line',
    'lyric-item',
    'chord-name',
    'rest',
    'rest-chord',
}
_TEXT_KINDS = {'word', 'sentence', 'lyric-line', 'lyric-item'}
_REF_FIELDS = {
    'notes': 'contains',
    'beams': 'contains',
    'key-alters': 'contains',
    'words': 'contains',
    'items': 'contains',
    'chords': 'beam-chord',
}


def _geometry(el: ET.Element) -> Geometry:
    def point(p):
        return (finite(p.get('x')), finite(p.get('y')))

    try:
        box_el = el.find('bounds')
        box = None
        if box_el is not None:
            x, y, w, h = (finite(box_el.get(k)) for k in ('x', 'y', 'w', 'h'))
            if w <= 0 or h <= 0:
                raise ValueError('empty bounds')
            box = (x, y, x + w, y + h)
        line = ()
        median = el.find('median')
        if median is not None:
            line = (point(median.find('p1')), point(median.find('p2')))
        elif el.find('top') is not None or el.find('bottom') is not None:
            line = (point(el.find('top')), point(el.find('bottom')))
        curve = el.find('curve')
        cubic = (
            tuple(
                (finite(curve.get(x)), finite(curve.get(y)))
                for x, y in [('x1', 'y1'), ('ctrlx1', 'ctrly1'), ('ctrlx2', 'ctrly2'), ('x2', 'y2')]
            )
            if curve is not None
            else ()
        )
        thickness = finite(el.get('height')) if el.get('height') is not None else None
        if thickness is not None and thickness <= 0:
            raise ValueError('invalid height')
        pivot = point(el.find('pivot')) if el.find('pivot') is not None else None
        location = point(el.find('location')) if el.find('location') is not None else None
        return Geometry(box, pivot, line, cubic, location, thickness)
    except (TypeError, ValueError, AttributeError):
        # A partially valid box must never conceal a broken curve or pivot.
        return Geometry(valid=False)


def _canonical(el: ET.Element) -> str:
    return ET.canonicalize(ET.tostring(el, encoding='unicode'), strip_text=True)


def load_visual_graph(path: Path) -> VisualScoreGraph:
    """Read bounded sheet XML members without extracting archive paths."""
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise GraphError('OMR archive too large')
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_MEMBERS or sum(i.file_size for i in infos) > MAX_ARCHIVE_BYTES:
                raise GraphError('OMR uncompressed size/member limit exceeded')
            names = [i for i in infos if re.fullmatch(r'sheet#\d+/sheet#\d+\.xml', i.filename)]
            if not names or len({i.filename for i in names}) != len(names):
                raise GraphError('Missing or duplicate sheet XML')
            sheets = []
            for info in sorted(names, key=lambda i: int(i.filename.split('/')[0][6:])):
                if info.file_size > MAX_XML_BYTES:
                    raise GraphError('Sheet XML too large')
                sheets.append((info.filename.split('/')[0], safe_xml(archive.read(info))))
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise GraphError('Unreadable OMR archive') from exc
    return _build_graph(sheets)


def _build_graph(sheets) -> VisualScoreGraph:
    pages, systems, staves, measures, relations, issues = [], [], [], [], [], []
    symbols = {}
    unsupported = set()
    invalid = 0

    def edge(kind, source, target, attrs=(), xml=''):
        token = repr((kind, source, target, attrs, xml)).encode()
        relations.append(
            Relation(hashlib.sha256(token).hexdigest()[:20], kind, source, target, attrs, xml)
        )

    for page_id, root in sheets:

        def sid(raw):
            return f'{page_id}:{raw}'

        try:
            picture = root.find('picture')
            width, height = int(picture.get('width')), int(picture.get('height'))
            interline = finite(root.find('scale/interline').get('main'))
            if min(width, height, interline) <= 0 or width * height > MAX_PIXELS:
                raise ValueError('invalid page dimensions')
        except (ValueError, TypeError, AttributeError) as exc:
            raise GraphError('Invalid picture/scale geometry') from exc
        pages.append(Page(page_id, width, height, interline))
        for sys_el in root.findall('.//page/system'):
            sys_id = f'{page_id}:system:{sys_el.get("id")}'
            staff_ids = []
            for part in sys_el.findall('part'):
                part_id = part.get('id', '')
                # Staff order is explicitly derived from staff IDs, never XML order.
                try:
                    staff_elements = sorted(part.findall('staff'), key=lambda s: int(s.get('id')))
                except (TypeError, ValueError) as exc:
                    raise GraphError('Invalid staff ID') from exc
                unsupported.update(
                    el.tag for el in part if el.tag in {'one-line-staff', 'tablature'}
                )
                for number, staff in enumerate(staff_elements, 1):
                    staff_id = sid(staff.get('id'))
                    lines, valid = [], True
                    try:
                        for line in staff.findall('lines/line'):
                            points = tuple(
                                sorted(
                                    (finite(p.get('x')), finite(p.get('y')))
                                    for p in line.findall('point')
                                )
                            )
                            if len(points) < 2 or len({p[0] for p in points}) != len(points):
                                raise ValueError('invalid staff polyline')
                            lines.append(points)
                        lines.sort(key=lambda pts: sum(p[1] for p in pts) / len(pts))
                        if len(lines) != 5:
                            raise ValueError('unsupported staff line count')
                        # Use staff-local spacing, including small staves.
                        ys = [sum(p[1] for p in line) / len(line) for line in lines]
                        local_interline = (ys[-1] - ys[0]) / 4
                        if local_interline <= 0 or any(b <= a for a, b in zip(ys, ys[1:])):
                            raise ValueError('invalid staff spacing')
                    except (TypeError, ValueError):
                        invalid += 1
                        issues.append(f'{staff_id}: invalid staff geometry')
                        valid, lines, local_interline = False, [], interline
                    if any(s.id == staff_id for s in staves):
                        raise GraphError('Duplicate staff ID')
                    staves.append(
                        Staff(
                            staff_id,
                            staff.get('id'),
                            page_id,
                            sys_id,
                            part_id,
                            number,
                            local_interline,
                            tuple(lines),
                            valid,
                            _canonical(staff),
                        )
                    )
                    staff_ids.append(staff_id)
            points = [p for s in staves if s.system == sys_id for line in s.lines for p in line]
            bounds = (
                (
                    min(p[0] for p in points),
                    min(p[1] for p in points),
                    max(p[0] for p in points),
                    max(p[1] for p in points),
                )
                if points
                else None
            )
            if any(s.id == sys_id for s in systems):
                raise GraphError('Duplicate system ID')
            systems.append(System(sys_id, page_id, bounds, tuple(sorted(staff_ids))))
            # Modern SIG uses inters + containment edges; legacy inline definitions
            # and reference lists are also retained.
            definitions = list(sys_el.findall('sig/inters/*')) + list(
                sys_el.findall('sig/inter-defs/*')
            )
            definitions += [
                el
                for part in sys_el.findall('part')
                for m in part.findall('measure')
                for el in m
                if el.tag in _SYMBOL_KINDS and el.get('id')
            ]
            for el in definitions:
                raw_id = el.get('id')
                if not raw_id:
                    issues.append(f'{sys_id}: symbol without ID ({el.tag})')
                    continue
                ident = sid(raw_id)
                if ident in symbols:
                    raise GraphError(f'Duplicate symbol ID: {ident}')
                if el.tag not in _SYMBOL_KINDS:
                    unsupported.add(el.tag)
                geom = _geometry(el)
                invalid += not geom.valid
                if not geom.valid:
                    issues.append(f'{ident}: invalid geometry')

                def optional_number(name, confidence=False):
                    raw = el.get(name)
                    if raw is None:
                        return None
                    try:
                        value = finite(raw)
                        if confidence and not 0 <= value <= 1:
                            raise ValueError('invalid grade')
                        return value
                    except (TypeError, ValueError):
                        issues.append(f'{ident}: invalid {name}')
                        return None

                symbols[ident] = VisualSymbol(
                    ident,
                    raw_id,
                    el.tag,
                    page_id,
                    sys_id,
                    sid(el.get('staff')) if el.get('staff') else None,
                    el.get('shape'),
                    optional_number('pitch'),
                    optional_number('grade', True),
                    optional_number('ctx-grade', True),
                    geom,
                    (),
                    tuple(sorted(el.attrib.items())),
                    _canonical(el),
                )
                for name, kind in _REF_FIELDS.items():
                    for ref in (el.findtext(name) or '').split():
                        edge(kind, ident, sid(ref))
                if el.get('stem'):
                    edge('chord-stem', ident, sid(el.get('stem')))
                for name in ('left-extension', 'right-extension', 'mirror'):
                    if el.get(name):
                        edge(name, ident, sid(el.get(name)))
            for rel in sys_el.findall('sig/relations/relation'):
                if not rel.get('source') or not rel.get('target') or len(rel) != 1:
                    issues.append(f'{sys_id}: malformed relation')
                    continue
                child = rel[0]
                edge(
                    'contains' if child.tag == 'containment' else child.tag,
                    sid(rel.get('source')),
                    sid(rel.get('target')),
                    tuple(sorted(child.attrib.items())),
                    _canonical(child),
                )
            stacks = {}
            for stack in sys_el.findall('stack'):
                stack_id = stack.get('id', '')
                if stack_id in stacks:
                    raise GraphError('Duplicate stack ID within system')
                slots = []
                try:
                    left, right = finite(stack.get('left')), finite(stack.get('right'))
                    if right <= left:
                        raise ValueError('invalid stack bounds')
                    stack_bounds = (left, bounds[1], right, bounds[3]) if bounds else None
                except (TypeError, ValueError):
                    invalid += 1
                    left, stack_bounds = None, None
                    issues.append(f'{sys_id}: invalid stack {stack_id}')
                for slot in stack.findall('slot'):
                    try:
                        x = left + finite(slot.get('x-offset')) if left is not None else None
                        off = quarter(slot.get('time-offset')) if slot.get('time-offset') else None
                    except (TypeError, ValueError, ZeroDivisionError):
                        x, off = None, None
                        invalid += 1
                        issues.append(f'{sys_id}: invalid slot {stack_id}/{slot.get("id")}')
                    slots.append(Slot(slot.get('id', ''), x, off, slot.get('suspicious') == 'true'))
                if len({s.id for s in slots}) != len(slots):
                    raise GraphError('Duplicate slot ID within stack')
                try:
                    duration = quarter(stack.get('duration')) if stack.get('duration') else None
                except (ValueError, ZeroDivisionError):
                    duration = None
                    issues.append(f'{sys_id}: invalid stack duration')
                stacks[stack_id] = (
                    stack_bounds,
                    tuple(sorted(slots, key=lambda s: s.id)),
                    duration,
                    _canonical(stack),
                )
            for part in sys_el.findall('part'):
                for m in part.findall('measure'):
                    number = m.get('id', '')
                    ident = f'{sys_id}:part:{part.get("id")}:measure:{number}'
                    stack_data = stacks.get(number)
                    if stack_data is None:
                        issues.append(f'{ident}: missing stack (no positional fallback)')
                        stack_data = (None, (), None, '')
                    if any(existing.id == ident for existing in measures):
                        raise GraphError('Duplicate measure ID within part/system')
                    refs = set()
                    for tag in (
                        'head-chords',
                        'rest-chords',
                        'keys',
                        'clefs',
                        'times',
                        'flags',
                        'augmentations-dots',
                    ):
                        refs.update(sid(r) for r in (m.findtext(tag) or '').split())
                    refs.update(
                        sid(el.get('id')) for el in m if el.tag in _SYMBOL_KINDS and el.get('id')
                    )
                    onsets = []
                    for voice in m.findall('voice'):
                        for entry in voice.findall('slots/entry'):
                            value = entry.find('value')
                            if (
                                value is not None
                                and value.get('status') == 'BEGIN'
                                and value.get('chord')
                            ):
                                onsets.append(
                                    (
                                        sid(value.get('chord')),
                                        entry.findtext('key', ''),
                                        voice.get('id', ''),
                                    )
                                )
                    measures.append(
                        Measure(
                            ident,
                            number,
                            page_id,
                            sys_id,
                            part.get('id', ''),
                            *stack_data[:3],
                            tuple(sorted(refs)),
                            tuple(sorted(onsets)),
                            _canonical(m),
                            stack_data[3],
                        )
                    )
    if not pages or not systems:
        raise GraphError('No score systems found')
    relations = tuple(sorted(set(relations), key=lambda r: r.id))
    for r in relations:
        if r.source not in symbols or r.target not in symbols:
            issues.append(f'dangling relation: {r.kind} {r.source} -> {r.target}')
    symbols = {
        ident: replace(
            s, relation_ids=tuple(r.id for r in relations if ident in (r.source, r.target))
        )
        for ident, s in sorted(symbols.items())
    }
    # Ensemble bounds are often transient in .omr. Derive a conservative union
    # only from valid member geometry; never rehabilitate malformed geometry.
    for _ in range(3):
        for ident, s in symbols.items():
            if s.geometry.valid and s.geometry.region is None:
                children = [
                    symbols[r.target]
                    for r in relations
                    if r.kind == 'contains' and r.source == ident and r.target in symbols
                ]
                box = union(c.geometry.region for c in children)
                if box and all(c.geometry.valid for c in children):
                    symbols[ident] = replace(s, geometry=replace(s.geometry, bbox=box))
    protected = []
    for s in symbols.values():
        if s.kind not in _TEXT_KINDS:
            continue
        attrs = dict(s.attributes)
        # Only an explicit chord-name role exempts recognized chord text.
        parents = [
            symbols[r.source]
            for r in relations
            if r.kind == 'contains' and r.target == s.id and r.source in symbols
        ]
        roles = [attrs.get('role', '')] + [dict(p.attributes).get('role', '') for p in parents]
        if any(role.lower().replace('_', '') in {'chordname', 'chord'} for role in roles):
            continue
        kind = (
            'lyrics'
            if s.kind.startswith('lyric')
            else next((r for r in roles if r), 'non-chord-text')
        )
        protected.append(
            ProtectedRegion(s.id, s.page, kind, s.geometry.region, (s.id,), attrs.get('value', ''))
        )
    return VisualScoreGraph(
        tuple(pages),
        tuple(sorted(systems, key=lambda s: s.id)),
        tuple(sorted(staves, key=lambda s: s.id)),
        tuple(sorted(measures, key=lambda m: m.id)),
        symbols,
        relations,
        tuple(protected),
        tuple(sorted(set(issues))),
        invalid,
        tuple(sorted(unsupported)),
    )
