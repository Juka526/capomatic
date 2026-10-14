"""Acceptance tests for research/melody/labels.schema.json.

The example label is hand-written synthetic data (no real sheet, no real reader).
jsonschema is not in requirements.txt, so this module skips where it is absent.
"""
import copy
import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

SCHEMA = json.loads((Path(__file__).resolve().parents[2] / "research/melody/labels.schema.json").read_text())


def valid_label() -> dict:
    return {
        "source_sha256": "0" * 64,
        "snippet_id": "synthetic-1",
        "reader": "la",
        "key_fifths": -1,
        "time_signature": "3/4",
        "systems": [{"index": 0, "x_left": 10, "x_right": 900, "line_ys": [100, 110, 120, 130, 140]}],
        "text": [{"kind": "lyric", "value": "가", "bbox": [10, 150, 20, 160]}],
        "events": [
            {"system": 0, "measure": 0, "event_index": 0, "onset": "0/1", "duration": "1/4",
             "midi": 70, "step": "B", "alter": -1, "octave": 4, "tie": None, "bbox": [10, 95, 18, 103]},
            {"system": 0, "measure": 1, "event_index": 0, "onset": "0/1", "duration": "1/4",
             "midi": None, "step": None, "alter": 0, "octave": None, "tie": None, "bbox": [30, 110, 38, 125]},
        ],
        "anchors": [{"kind": "lyric", "event": [0, 0, 0], "text": "가"}],
    }


def errors(doc) -> list:
    return list(jsonschema.Draft202012Validator(SCHEMA).iter_errors(doc))


def test_schema_is_valid_draft_2020_12():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)


def test_valid_synthetic_label_passes():  # T5 positive control
    assert errors(valid_label()) == []


def _set_event(field, value):
    def f(d):
        d["events"][0][field] = value
    return f


@pytest.mark.parametrize("name, mutate", [
    ("onset float string", _set_event("onset", "0.5")),
    ("negative duration", _set_event("duration", "-1/4")),
    ("midi as string", _set_event("midi", "70")),
    ("unknown tie", _set_event("tie", "maybe")),
    ("missing bbox", lambda d: d["events"][0].pop("bbox")),
    ("key_fifths 8", lambda d: d.__setitem__("key_fifths", 8)),
    ("uppercase source hash", lambda d: d.__setitem__("source_sha256", "A" * 64)),
    ("extra top-level key", lambda d: d.__setitem__("model_output", [])),
    ("four staff lines", lambda d: d["systems"][0].__setitem__("line_ys", [100, 110, 120, 130])),
    ("unknown text kind", lambda d: d["text"][0].__setitem__("kind", "chord")),
    ("anchor with 2 coords", lambda d: d["anchors"][0].__setitem__("event", [0, 0])),
])
def test_existing_schema_guards(name, mutate):
    doc = copy.deepcopy(valid_label())
    mutate(doc)
    assert errors(doc), name


@pytest.mark.parametrize("name, mutate", [
    ("step H", _set_event("step", "H")),
    ("alter 5", _set_event("alter", 5)),
    ("octave 42", _set_event("octave", 42)),
    ("midi 200", _set_event("midi", 200)),
    ("zero duration", _set_event("duration", "0/1")),
    ("zero denominator", _set_event("onset", "1/0")),
    ("unknown event field", _set_event("confidence", 0.9)),
])
def test_schema_rejects_impossible_pitch_and_rhythm(name, mutate):
    doc = copy.deepcopy(valid_label())
    mutate(doc)
    assert errors(doc), name
