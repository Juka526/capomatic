"""Page geometry from an Audiveris ``.omr`` book.

The exported MusicXML carries no reliable pixel positions, but the book file
does: every measure stack has absolute x bounds and its time slots, and every
staff has its line coordinates. That is enough to put an OCR'd chord box onto
a measure and beat. Parsed with the standard library only; the XML is produced
by our own Audiveris run, and DTD/entity declarations are rejected anyway.
"""
from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree

_MAX_SHEET_XML_BYTES = 64 * 1024 * 1024


class GeometryError(ValueError):
    """The book file is missing or not in the expected layout."""


@dataclass
class Stack:
    index: int            # global measure index on the page (0-based, matches MusicXML order)
    left: float
    right: float
    slots: list[tuple[float, Fraction]]  # (absolute x, offset in quarter lengths)

    def offset_at(self, x: float, tolerance: float) -> Fraction:
        """Offset of the slot nearest *x*, nudged toward beats.

        Chord changes fall on beats far more often than on 16th positions, so a
        slot on a beat (or half beat) wins over a slightly closer off-beat slot.
        A chord before the first slot sits on that slot.
        """
        if not self.slots:
            return Fraction(0)
        first_x, first_off = self.slots[0]
        if x < first_x - tolerance:
            return first_off

        def cost(slot: tuple[float, Fraction]) -> float:
            sx, off = slot
            penalty = 0.0 if off.denominator == 1 else 0.25 if off.denominator == 2 else 0.6
            return abs(sx - x) + penalty * tolerance

        return min(self.slots, key=cost)[1]


@dataclass(frozen=True)
class Head:
    x: float
    y: float
    w: float
    h: float
    pitch: int        # staff position: 0 = middle line, +4 = bottom line, +6 = first ledger below


@dataclass
class System:
    top: float      # y of the top staff line of the first staff
    bottom: float   # y of the bottom staff line of the last staff
    stacks: list[Stack] = field(default_factory=list)
    heads: list[Head] = field(default_factory=list)
    line_ys: list[float] = field(default_factory=list)  # mean y of every staff line

    def stack_at(self, x: float) -> Stack | None:
        for s in self.stacks:
            if s.left <= x < s.right:
                return s
        if self.stacks and x < self.stacks[0].left:
            return self.stacks[0]
        return None


@dataclass
class SheetGeometry:
    width: int
    height: int
    interline: float
    head_width: float
    systems: list[System]

    @property
    def measure_count(self) -> int:
        return sum(len(s.stacks) for s in self.systems)

    def system_below(self, y: float) -> System | None:
        """System whose staff starts below *y* (chords are printed above the staff)."""
        limit = 8 * self.interline
        candidates = [s for s in self.systems if s.top >= y - self.interline and s.top - y <= limit]
        return min(candidates, key=lambda s: s.top - y) if candidates else None


def _parse_xml(data: bytes) -> ElementTree.Element:
    if b'<!DOCTYPE' in data[:4096].upper() or b'<!ENTITY' in data.upper():
        raise GeometryError('unexpected DTD in book file')
    return ElementTree.fromstring(data)


def load_geometry(omr_path: Path) -> SheetGeometry:
    """Read the first sheet of an Audiveris book."""
    try:
        with zipfile.ZipFile(omr_path) as z:
            names = [n for n in z.namelist() if n.startswith('sheet#1/') and n.endswith('.xml')]
            if not names:
                raise GeometryError('book has no sheet#1')
            info = z.getinfo(names[0])
            if info.file_size > _MAX_SHEET_XML_BYTES:
                raise GeometryError('sheet XML too large')
            root = _parse_xml(z.read(info))
    except (zipfile.BadZipFile, ElementTree.ParseError, KeyError) as exc:
        raise GeometryError(f'unreadable book: {exc}') from exc

    picture = root.find('picture')
    scale = root.find('scale')
    if picture is None or scale is None:
        raise GeometryError('book lacks picture/scale')
    interline = float(scale.find('interline').get('main'))
    head = scale.find('black-head')
    head_width = float(head.get('mean-width')) if head is not None else interline * 1.3

    systems: list[System] = []
    index = 0
    for page in root.iter('page'):
        for sys_el in page.findall('system'):
            ys = [float(p.get('y')) for staff in sys_el.iter('staff')
                  for line in staff.iter('line') for p in line.findall('point')]
            if not ys:
                continue
            system = System(top=min(ys), bottom=max(ys))
            for staff in sys_el.iter('staff'):
                for line in staff.iter('line'):
                    pts = [float(p.get('y')) for p in line.findall('point')]
                    if pts:
                        system.line_ys.append(sum(pts) / len(pts))
            for st in sys_el.findall('stack'):
                left = float(st.get('left'))
                slots = [(left + float(sl.get('x-offset')), Fraction(sl.get('time-offset')) * 4)
                         for sl in st.findall('slot')]
                slots.sort()
                system.stacks.append(Stack(index, left, float(st.get('right')), slots))
                index += 1
            for h in sys_el.iter('head'):
                b = h.find('bounds')
                try:
                    pitch = round(float(h.get('pitch')))
                except (TypeError, ValueError):
                    continue
                if b is not None:
                    system.heads.append(Head(float(b.get('x')), float(b.get('y')),
                                             float(b.get('w')), float(b.get('h')), pitch))
            systems.append(system)
    if not systems:
        raise GeometryError('no systems found')
    return SheetGeometry(int(picture.get('width')), int(picture.get('height')),
                         interline, head_width, systems)
