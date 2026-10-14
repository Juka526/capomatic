"""Acceptance tests for backend/omr/intent.py (capo vs key change).

Expected values are hand-written from the plan's contract
(docs/plans/V2_3_MELODY.md section 2), not derived from the module.
"""
import types

import pytest

from backend.omr.intent import IntentError, parse_intent
from omr_guard import SENTINEL, leaks


# --- T5 positive controls: legitimate requests are accepted first ----------

@pytest.mark.parametrize("raw, chord_shift, melody_shift", [
    ({"intent": "capo", "capo_fret": 0}, 0, 0),
    ({"intent": "capo", "capo_fret": 2}, -2, 0),
    ({"intent": "capo", "capo_fret": 7}, -7, 0),
    ({"intent": "key_change", "semitones": 0, "transpose_notes": True}, 0, 0),
    ({"intent": "key_change", "semitones": -2, "transpose_notes": True}, -2, -2),
    ({"intent": "key_change", "semitones": -2, "transpose_notes": False}, -2, 0),
    ({"intent": "key_change", "semitones": -11, "transpose_notes": True}, -11, -11),
    ({"intent": "key_change", "semitones": 11, "transpose_notes": True}, 11, 11),
    ({"intent": "key_change", "semitones": 5, "transpose_notes": False}, 5, 0),
])
def test_valid_intents(raw, chord_shift, melody_shift):
    i = parse_intent(raw)
    assert (i.chord_shift, i.melody_shift) == (chord_shift, melody_shift)


def test_read_only_mapping_is_accepted():
    i = parse_intent(types.MappingProxyType({"intent": "capo", "capo_fret": 3}))
    assert (i.chord_shift, i.melody_shift) == (-3, 0)


def test_capo_never_moves_melody_for_any_fret():
    for fret in range(0, 8):
        assert parse_intent({"intent": "capo", "capo_fret": fret}).melody_shift == 0


# --- Negative guards -------------------------------------------------------

@pytest.mark.parametrize("raw", [
    {},
    {"semitones": -2},                     # same -2 must not pick a mode
    {"capo_fret": 2},
    {"intent": "CAPO", "capo_fret": 2},
    {"intent": "capo"},
    {"intent": "capo", "capo_fret": 8},
    {"intent": "capo", "capo_fret": -1},
    {"intent": "capo", "capo_fret": 2.0},
    {"intent": "capo", "capo_fret": True},
    {"intent": "capo", "capo_fret": "2"},
    {"intent": "capo", "capo_fret": 2, "semitones": 0},
    {"intent": "capo", "capo_fret": 2, "transpose_notes": True},
    {"intent": "capo", "capo_fret": 2, "transpose_notes": 0},
    {"intent": "key_change", "semitones": 12, "transpose_notes": True},
    {"intent": "key_change", "semitones": -12, "transpose_notes": True},
    {"intent": "key_change", "semitones": 1.0, "transpose_notes": True},
    {"intent": "key_change", "semitones": 1},
    {"intent": "key_change", "semitones": 1, "transpose_notes": 1},
    {"intent": "key_change", "semitones": 1, "transpose_notes": "true"},
    {"intent": "key_change", "semitones": 1, "transpose_notes": True, "capo_fret": 0},
])
def test_contradictory_or_out_of_range_rejected(raw):
    with pytest.raises(IntentError):
        parse_intent(raw)


@pytest.mark.parametrize("raw", [None, ["intent"], "intent", 3, b"capo"])
def test_non_mapping_input_is_a_422_not_a_crash(raw):
    with pytest.raises(IntentError):
        parse_intent(raw)


def test_non_string_unknown_keys_are_a_422_not_a_crash():
    # Mixed key types made sorted() raise TypeError instead of IntentError.
    with pytest.raises(IntentError):
        parse_intent({"intent": "capo", "capo_fret": 1, "zz": 1, 1: "x"})


# --- Content-free errors (Sentry) -----------------------------------------

def test_unknown_field_name_is_not_echoed():
    with pytest.raises(IntentError) as e:
        parse_intent({"intent": "capo", "capo_fret": 1, SENTINEL: 1})
    assert not leaks(e.value)


@pytest.mark.parametrize("field", ["intent", "capo_fret", "semitones", "transpose_notes"])
def test_user_values_are_not_echoed(field):
    raw = {"intent": "key_change", "semitones": 1, "transpose_notes": True}
    raw[field] = SENTINEL
    with pytest.raises(IntentError) as e:
        parse_intent(raw)
    assert not leaks(e.value)


def test_intent_error_is_422():
    assert IntentError.status_code == 422
