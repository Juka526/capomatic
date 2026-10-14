"""Exchange boundary between chord OCR / cm2 adapters and the melody (OMR) research code.

Coordinates: every x/y/bbox is in ORIGINAL upright-image pixels (origin top-left, y down,
bbox = [x1, y1, x2, y2] with x1<x2, y1<y2, inside the source). Never band-crop or resized
coordinates. A chord with bbox None cannot be aligned automatically and is rejected.

Staff geometry: `detect_staff_systems` only yields (top_y, bottom_y); this contract needs
five validated line ys and x extents, which melody code must derive itself.

Events: rationals travel as "n/d" strings (never floats). Rests have midi None.
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import Optional

BBox = tuple[float, float, float, float]


class ContractError(ValueError):
    pass


def check_bbox(b, width: int, height: int) -> BBox:
    if b is None or len(b) != 4:
        raise ContractError("bbox required: 4 numbers in original pixels")
    x1, y1, x2, y2 = b
    if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
        raise ContractError("bbox outside original image or degenerate")
    return (x1, y1, x2, y2)


def parse_rational(s: str) -> Fraction:
    if not isinstance(s, str) or "/" not in s:
        raise ContractError("rational must be an 'n/d' string")
    return Fraction(s)  # ZeroDivisionError/ValueError on garbage: callers reject the page


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
        ys = self.line_ys
        if len(ys) != 5 or any(b <= a for a, b in zip(ys, ys[1:])):
            raise ContractError("staff needs 5 strictly increasing line ys")
        if self.x_left >= self.x_right:
            raise ContractError("staff x extent degenerate")


@dataclass(frozen=True)
class NoteEvent:
    system: int
    measure: int  # 1-based printed order; pickup = 0
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
        if self.duration <= 0 or self.onset < 0:
            raise ContractError("onset>=0 and duration>0 required")
        if (self.midi is None) != (self.step is None):
            raise ContractError("rest has no pitch; pitched event needs step")


def _selfcheck() -> None:
    assert check_bbox([1, 1, 5, 5], 10, 10) == (1, 1, 5, 5)
    for bad in (None, [1, 1, 5], [5, 1, 1, 5], [0, 0, 11, 5]):
        try:
            check_bbox(bad, 10, 10)
        except ContractError:
            continue
        raise AssertionError(bad)
    StaffSystem(0, 0, 9, (1, 2, 3, 4, 5))
    try:
        StaffSystem(0, 0, 9, (1, 2, 2, 4, 5))
        raise AssertionError("flat staff accepted")
    except ContractError:
        pass
    assert parse_rational("3/8") == Fraction(3, 8)
    print("contract selfcheck OK")


if __name__ == "__main__":
    _selfcheck()
