"""Acceptance tests for backend/omr/contract.py (geometry, rationals, note events).

Pitch truth is a hand-written table (scientific pitch notation, C4 = MIDI 60),
not computed by any product helper.
"""
import math
from fractions import Fraction

import pytest

from backend.omr.contract import ContractError, NoteEvent, StaffSystem, check_bbox, parse_rational
from omr_guard import SENTINEL, leaks

NAN, INF = math.nan, math.inf

# (step, alter, octave, midi), hand-authored.
PITCH_TRUTH = [
    ("C", 0, 4, 60), ("D", 0, 4, 62), ("E", 0, 4, 64), ("F", 0, 4, 65),
    ("G", 0, 4, 67), ("A", 0, 4, 69), ("B", 0, 4, 71), ("B", -1, 4, 70),
    ("C", 1, 5, 73), ("B", -1, 3, 58), ("E", 1, 4, 65), ("C", -1, 5, 71),
    ("B", 1, 3, 60), ("F", 1, 4, 66), ("A", -1, 4, 68), ("A", 0, 3, 57),
    ("G", 0, 5, 79), ("C", 0, 6, 84),
]


def note(**kw):
    base = dict(system=0, measure=1, index=0, onset=Fraction(0), duration=Fraction(1, 4),
                midi=60, step="C", alter=0, octave=4, tie=None, bbox=(10, 20, 18, 28))
    base.update(kw)
    return NoteEvent(**base)


# --- check_bbox ------------------------------------------------------------

@pytest.mark.parametrize("b", [[0, 0, 10, 10], [1, 1, 5, 5], [1.5, 2.5, 3.0, 4.0]])
def test_bbox_valid(b):
    assert check_bbox(b, 10, 10) == tuple(b)


@pytest.mark.parametrize("b", [
    None, [1, 1, 5], [5, 1, 1, 5], [1, 5, 5, 1], [0, 0, 11, 5], [-1, 0, 5, 5],
    [NAN, 1, 5, 5], [1, 1, INF, 5], [1, 1, 5, NAN],
    ["1", "1", "5", "5"], [None, 1, 5, 5], 7,
])
def test_bbox_invalid_is_contract_error(b):
    with pytest.raises(ContractError):
        check_bbox(b, 10, 10)


# --- parse_rational --------------------------------------------------------

@pytest.mark.parametrize("s, expected", [
    ("0/1", Fraction(0)), ("1/4", Fraction(1, 4)), ("3/8", Fraction(3, 8)),
    ("6/16", Fraction(3, 8)), ("1/12", Fraction(1, 12)), ("2/1", Fraction(2)),
])
def test_rational_valid(s, expected):
    assert parse_rational(s) == expected


@pytest.mark.parametrize("s", [
    "1/0", "a/b", "1.5/2", "3//8", "-1/2", "+3/8", " 3/8", "3/8 ", "1_0/3", "٣/٨",
    "0.375", 0.375, Fraction(3, 8), None,
])
def test_rational_invalid_is_contract_error(s):
    # Labels schema allows only ^[0-9]+/[0-9]+$ with a non-zero denominator.
    with pytest.raises(ContractError):
        parse_rational(s)


@pytest.mark.parametrize("s", [f"{SENTINEL}/1", f"1/{SENTINEL}"])
def test_rational_error_does_not_echo_input(s):
    with pytest.raises(Exception) as e:
        parse_rational(s)
    assert isinstance(e.value, ContractError)
    assert not leaks(e.value)


# --- StaffSystem -----------------------------------------------------------

def test_staff_valid():
    s = StaffSystem(0, 10, 900, (100, 110, 120, 130, 140))
    assert s.line_ys[0] == 100


@pytest.mark.parametrize("args", [
    (0, 10, 900, (100, 110, 110, 130, 140)),
    (0, 10, 900, (100, 110, 120, 130)),
    (0, 900, 10, (100, 110, 120, 130, 140)),
    (0, 10, 900, (100, NAN, 120, 130, 140)),
    (0, 10, 900, (100, 110, 120, 130, INF)),
    (0, NAN, 900, (100, 110, 120, 130, 140)),
    (0, 10, NAN, (100, 110, 120, 130, 140)),
    (0, -5, 900, (100, 110, 120, 130, 140)),
    (0, 10, 900, (-10, 0, 10, 20, 30)),
    (-1, 10, 900, (100, 110, 120, 130, 140)),
    (0, 10, 900, ("1", "2", "3", "4", "5")),
])
def test_staff_invalid_is_contract_error(args):
    with pytest.raises(ContractError):
        StaffSystem(*args)


# --- NoteEvent -------------------------------------------------------------

@pytest.mark.parametrize("step, alter, octave, midi", PITCH_TRUTH)
def test_note_pitch_truth_accepted(step, alter, octave, midi):
    assert note(step=step, alter=alter, octave=octave, midi=midi).midi == midi


def test_rest_and_rational_rhythm_accepted():
    r = note(midi=None, step=None, octave=None, onset=Fraction(3, 8), duration=Fraction(1, 8))
    assert r.midi is None
    for tie in (None, "start", "stop", "both"):
        assert note(tie=tie).tie == tie


@pytest.mark.parametrize("kw", [
    dict(midi=61),                                   # C4 is 60
    dict(step="B", alter=-1, octave=4, midi=71),     # Bb4 is 70
    dict(step="C", alter=1, octave=5, midi=61),      # C#5 is 73 (octave error)
    dict(step="H", midi=60),
    dict(step="c", midi=60),
    dict(alter=3, midi=63),
    dict(octave=None),
    dict(midi=128, step="G", octave=9, alter=1),
    dict(midi=-1),
    dict(tie="maybe"),
    dict(midi=None, step=None, octave=None, alter=1),  # rest with accidental
    dict(onset=0.5),
    dict(duration=0.25),
    dict(duration=Fraction(0)),
    dict(onset=Fraction(-1, 4)),
    dict(duration=NAN),
    dict(bbox=(18, 20, 10, 28)),
    dict(bbox=(NAN, 20, 18, 28)),
    dict(measure=-1),
])
def test_invalid_note_is_contract_error(kw):
    with pytest.raises(ContractError):
        note(**kw)
