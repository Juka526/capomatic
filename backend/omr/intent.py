"""Intent contract: capo vs. key change. The single place that decides what moves.

capo        -> chord shapes shift by -capo_fret; melody and key signature never change.
key_change  -> chords shift by `semitones`; melody shifts only if transpose_notes is true.

The mode is always explicit: the same -2 never selects a mode. Invalid input raises
IntentError (HTTP 422 for callers) with a FIXED message: it never echoes field names or values,
because exceptions can reach error reporting. No octave folding: melody pitch is plain addition, and
out-of-range results are the caller's to reject, never to wrap.
"""
from dataclasses import dataclass
from typing import Mapping

CAPO_MAX = 7
SEMITONE_MAX = 11
_FIELDS = {"intent", "capo_fret", "semitones", "transpose_notes"}


class IntentError(ValueError):
    status_code = 422


@dataclass(frozen=True)
class Intent:
    mode: str  # "capo" | "key_change"
    capo_fret: int = 0
    semitones: int = 0
    transpose_notes: bool = False

    @property
    def chord_shift(self) -> int:
        return -self.capo_fret if self.mode == "capo" else self.semitones

    @property
    def melody_shift(self) -> int:
        return self.semitones if self.mode == "key_change" and self.transpose_notes else 0


def _int_in(raw: Mapping, key: str, lo: int, hi: int) -> int:
    v = raw.get(key)
    if type(v) is not int:  # rejects bool, float, str, None
        raise IntentError(f"{key}: integer required")
    if not lo <= v <= hi:
        raise IntentError(f"{key}: out of range")
    return v


def parse_intent(raw: Mapping) -> Intent:
    """Validate a request-shaped mapping into an Intent."""
    if not isinstance(raw, Mapping):
        raise IntentError("request must be an object")
    if set(raw) - _FIELDS:  # set math: safe for mixed-type keys, names never reported
        raise IntentError("unknown field")
    mode = raw.get("intent")
    if mode == "capo":
        if "semitones" in raw:
            raise IntentError("capo intent cannot carry semitones")
        if raw.get("transpose_notes", False) is not False:
            raise IntentError("capo intent cannot transpose notes")
        return Intent("capo", capo_fret=_int_in(raw, "capo_fret", 0, CAPO_MAX))
    if mode == "key_change":
        if "capo_fret" in raw:
            raise IntentError("key_change intent cannot carry capo_fret")
        notes = raw.get("transpose_notes")
        if type(notes) is not bool:
            raise IntentError("transpose_notes must be an explicit boolean")
        return Intent("key_change", semitones=_int_in(raw, "semitones", -SEMITONE_MAX, SEMITONE_MAX),
                      transpose_notes=notes)
    raise IntentError("intent: must be capo or key_change")


def _selfcheck() -> None:
    i = parse_intent({"intent": "capo", "capo_fret": 2})
    assert (i.chord_shift, i.melody_shift) == (-2, 0)
    i = parse_intent({"intent": "key_change", "semitones": -2, "transpose_notes": True})
    assert (i.chord_shift, i.melody_shift) == (-2, -2)
    i = parse_intent({"intent": "key_change", "semitones": -2, "transpose_notes": False})
    assert (i.chord_shift, i.melody_shift) == (-2, 0)
    assert parse_intent({"intent": "capo", "capo_fret": 0}).chord_shift == 0
    bad = [
        {}, {"semitones": -2}, {"capo_fret": 2},  # implicit mode
        {"intent": "capo"}, {"intent": "capo", "capo_fret": 8}, {"intent": "capo", "capo_fret": -1},
        {"intent": "capo", "capo_fret": 2.0}, {"intent": "capo", "capo_fret": True},
        {"intent": "capo", "capo_fret": "2"}, {"intent": "capo", "capo_fret": 2, "semitones": 0},
        {"intent": "capo", "capo_fret": 2, "transpose_notes": True},
        {"intent": "key_change", "semitones": 12, "transpose_notes": True},
        {"intent": "key_change", "semitones": -12, "transpose_notes": True},
        {"intent": "key_change", "semitones": 1.5, "transpose_notes": True},
        {"intent": "key_change", "semitones": 1},  # transpose_notes not explicit
        {"intent": "key_change", "semitones": 1, "transpose_notes": 1},
        {"intent": "key_change", "semitones": 1, "transpose_notes": True, "capo_fret": 0},
        {"intent": "key_change", "semitones": 1, "transpose_notes": True, "x": 1},
    ]
    for b in bad:
        try:
            parse_intent(b)
        except IntentError:
            continue
        raise AssertionError(f"accepted {b}")
    print(f"intent selfcheck OK ({len(bad)} rejections)")


if __name__ == "__main__":
    _selfcheck()
