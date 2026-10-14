"""Exchange boundary between chord OCR / cm2 adapters and the melody (OMR) research code.

Coordinates: every x/y/bbox is in ORIGINAL upright-image pixels (origin top-left, y down,
bbox = [x1, y1, x2, y2] with 0<=x1<x2, 0<=y1<y2, finite, inside the source where a source
size is known). Never band-crop or resized coordinates. A chord with bbox None cannot be
aligned automatically and is rejected.

Staff geometry: `detect_staff_systems` only yields (top_y, bottom_y); this contract needs
five validated line ys and x extents, which melody code must derive itself.

Events: rationals travel as ASCII "n/d" strings with d>0 (never floats). Pitch is
conventional: step A-G, alter -2..2, octave -1..9, midi 0..127 and midi must equal
12*(octave+1)+step_offset+alter. Rests have midi/step/octave None, alter 0 and no tie.
There is no octave folding anywhere.

Errors are ContractError with FIXED messages: input values are never echoed.
"""
import math
import re
from dataclasses import dataclass
from fractions import Fraction
from typing import Optional

BBox = tuple[float, float, float, float]
_RATIONAL = re.compile(r"[0-9]+/[0-9]+")
_STEP_OFFSET = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_TIES = (None, "start", "stop", "both")


class ContractError(ValueError):
    pass


def _num(v) -> float:
    if type(v) not in (int, float) or not math.isfinite(v) or v < 0:
        raise ContractError("coordinate must be a finite non-negative number")
    return v


def _nonneg_int(v) -> int:
    if type(v) is not int or v < 0:
        raise ContractError("index must be a non-negative integer")
    return v


def _bbox(b) -> BBox:
    if not isinstance(b, (list, tuple)) or len(b) != 4:
        raise ContractError("bbox required: 4 numbers in original pixels")
    x1, y1, x2, y2 = (_num(v) for v in b)
    if not (x1 < x2 and y1 < y2):
        raise ContractError("bbox degenerate")
    return (x1, y1, x2, y2)


def check_bbox(b, width: int, height: int) -> BBox:
    x1, y1, x2, y2 = _bbox(b)
    if x2 > width or y2 > height:
        raise ContractError("bbox outside original image")
    return (x1, y1, x2, y2)


def parse_rational(s) -> Fraction:
    if type(s) is not str or not _RATIONAL.fullmatch(s):
        raise ContractError("rational must be an ASCII 'n/d' string")
    n, d = s.split("/")
    if int(d) == 0:
        raise ContractError("rational denominator must be positive")
    return Fraction(int(n), int(d))


@dataclass(frozen=True)
class Source:
    width: int
    height: int
    sha256: str  # of the upright RGB source bytes as received


@dataclass(frozen=True)
class ChordItem:
    text: str
    confidence: float
    bbox: BBox
    style: Optional[str] = None  # cm1 style hint; opaque here


@dataclass(frozen=True)
class StaffSystem:
    index: int  # top to bottom, 0-based
    x_left: float
    x_right: float
    line_ys: tuple[float, float, float, float, float]  # top line .. bottom line, validated

    def __post_init__(self):
        _nonneg_int(self.index)
        _num(self.x_left), _num(self.x_right)
        if not self.x_left < self.x_right:
            raise ContractError("staff x extent degenerate")
        if not isinstance(self.line_ys, (list, tuple)) or len(self.line_ys) != 5:
            raise ContractError("staff needs 5 line ys")
        ys = tuple(_num(v) for v in self.line_ys)
        if any(b <= a for a, b in zip(ys, ys[1:])):
            raise ContractError("staff line ys must strictly increase")
        object.__setattr__(self, "line_ys", ys)


@dataclass(frozen=True)
class NoteEvent:
    system: int
    measure: int  # printed order; pickup = 0
    index: int  # left-to-right within measure
    onset: Fraction  # whole-note units from measure start
    duration: Fraction
    midi: Optional[int]  # None = rest
    step: Optional[str]  # A..G
    alter: int
    octave: Optional[int]
    tie: Optional[str]  # None|"start"|"stop"|"both"
    bbox: BBox  # notehead/rest in original pixels
    lyric_anchor: Optional[str] = None  # opaque label id, see labels.schema.json
    chord_anchor: Optional[str] = None

    def __post_init__(self):
        for v in (self.system, self.measure, self.index):
            _nonneg_int(v)
        if not (isinstance(self.onset, Fraction) and isinstance(self.duration, Fraction)):
            raise ContractError("onset/duration must be Fraction")
        if self.onset < 0 or self.duration <= 0:
            raise ContractError("onset>=0 and duration>0 required")
        if self.tie not in _TIES:
            raise ContractError("unknown tie")
        if type(self.alter) is not int or not -2 <= self.alter <= 2:
            raise ContractError("alter must be an integer in -2..2")
        for a in (self.lyric_anchor, self.chord_anchor):
            if a is not None and type(a) is not str:
                raise ContractError("anchor must be a string id")
        object.__setattr__(self, "bbox", _bbox(self.bbox))
        if self.midi is None:
            if self.step is not None or self.octave is not None or self.alter != 0 or self.tie is not None:
                raise ContractError("rest carries no pitch, accidental or tie")
            return
        if type(self.midi) is not int or not 0 <= self.midi <= 127:
            raise ContractError("midi must be an integer in 0..127")
        if self.step not in _STEP_OFFSET or type(self.octave) is not int or not -1 <= self.octave <= 9:
            raise ContractError("pitched event needs step A-G and octave -1..9")
        if self.midi != 12 * (self.octave + 1) + _STEP_OFFSET[self.step] + self.alter:
            raise ContractError("midi does not match step/alter/octave")


def _selfcheck() -> None:
    import math as m
    assert check_bbox([1, 1, 5, 5], 10, 10) == (1, 1, 5, 5)
    for bad in (None, [1, 1, 5], [5, 1, 1, 5], [0, 0, 11, 5], [m.nan, 1, 5, 5], ["1", 1, 5, 5]):
        try:
            check_bbox(bad, 10, 10)
        except ContractError:
            continue
        raise AssertionError(bad)
    StaffSystem(0, 0, 9, (1, 2, 3, 4, 5))
    for args in ((0, 0, 9, (1, 2, 2, 4, 5)), (0, 0, 9, (-1, 2, 3, 4, 5))):
        try:
            StaffSystem(*args)
            raise AssertionError(args)
        except ContractError:
            pass
    assert parse_rational("3/8") == Fraction(3, 8)
    for bad in ("1/0", "-1/2", "٣/٨", 0.5):
        try:
            parse_rational(bad)
            raise AssertionError(bad)
        except ContractError:
            pass
    ok = dict(system=0, measure=1, index=0, onset=Fraction(0), duration=Fraction(1, 4), midi=70,
              step="B", alter=-1, octave=4, tie=None, bbox=(1, 1, 2, 2))
    NoteEvent(**ok)
    try:
        NoteEvent(**{**ok, "midi": 71})
        raise AssertionError("wrong midi accepted")
    except ContractError:
        pass
    print("contract selfcheck OK")


if __name__ == "__main__":
    _selfcheck()
