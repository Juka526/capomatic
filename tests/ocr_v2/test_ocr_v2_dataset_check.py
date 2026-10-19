"""Acceptance tests for training/chords/dataset_check.py (V2-1 S0/S1).

Truth here is written independently by the test; no production parser, OCR
or generator output is used to create it. Exit codes: 0 READY, 1 FAIL, 2 HOLD.
"""
from __future__ import annotations

import json

import pytest

from tests.ocr_v2.conftest import png

READY, FAIL, HOLD = 0, 1, 2


def run(dc, manifest) -> int:
    return dc.main(["dataset_check.py", str(manifest)])


def full_world(world, pages=60):
    for i in range(pages):
        world.page(i)
    return world.manifest()


# --- T5 controls -------------------------------------------------------------

def test_network_guard_catches_a_deliberate_local_request():
    import socket
    s = socket.socket()
    try:
        with pytest.raises(RuntimeError, match="network access attempted"):
            s.connect(("127.0.0.1", 9))
    finally:
        s.close()


def test_known_positive_full_holdout_is_ready(dc, world):
    m = full_world(world)
    errs, stats = dc.check(m)
    assert errs == []
    assert stats == {"pages": 60, "occurrences": 3000, "systems": 240}
    assert run(dc, m) == READY


# --- readiness: HOLD vs READY vs FAIL ----------------------------------------

def test_empty_manifest_is_hold(dc, world):
    assert run(dc, world.manifest()) == HOLD


def test_missing_manifest_is_fail(dc, tmp_path):
    assert run(dc, tmp_path / "absent.json") == FAIL


@pytest.mark.parametrize("pages,truth", [
    (59, {"chords": [{"text": "G", "bbox": [c, 1, c + 1, 9], "system": 0} for c in range(60)]}),
    (60, {"chords": [{"text": "G", "bbox": [c, 1, c + 1, 9], "system": 0} for c in range(49)]}),
    (60, {"staff_systems": [{"y0": 10 + 40 * s, "y1": 40 + 40 * s} for s in range(3)],
          "chords": [{"text": "G", "bbox": [c, 1, c + 1, 9], "system": 0} for c in range(50)]}),
], ids=["59-pages", "2940-occurrences", "180-systems"])
def test_one_short_of_any_primary_minimum_is_hold(dc, world, pages, truth):
    for i in range(pages):
        world.page(i, truth=truth)
    assert run(dc, world.manifest()) == HOLD


def test_valid_partial_holdout_is_hold_not_ready(dc, world):
    for i in range(3):
        world.page(i)
    m = world.manifest()
    assert dc.check(m)[0] == []
    assert run(dc, m) == HOLD


# --- independence and leakage -------------------------------------------------

def test_synthetic_holdout_fails_and_is_not_counted(dc, world):
    full_world(world)
    world.items[0]["kind"] = "synthetic"
    errs, stats = dc.check(world.manifest())
    assert errs and stats["pages"] == 59


def test_generator_page_in_holdout_fails(dc, world):
    full_world(world)
    world.items[0]["generator_id"] = "synth-v1"
    assert run(dc, world.manifest()) == FAIL


def test_family_in_holdout_and_train_fails(dc, world):
    full_world(world)
    world.page(99, split="train", kind="synthetic", family="fam0", composer="composer99")
    assert run(dc, world.manifest()) == FAIL


def test_same_bytes_in_two_splits_fails(dc, world):
    full_world(world)
    dup = dict(world.items[0], id="t0", split="train", kind="synthetic", family="other", composer="x")
    world.items.append(dup)
    assert run(dc, world.manifest()) == FAIL


def test_holdout_composer_also_in_train_fails(dc, world):
    full_world(world)
    world.page(99, split="train", kind="synthetic", family="famT", composer="composer0")
    assert run(dc, world.manifest()) == FAIL


def test_holdout_composed_by_generator_author_fails(dc, world):
    full_world(world)
    world.items[0]["composer"] = "gen-author"
    assert run(dc, world.manifest()) == FAIL


def test_reader_who_authored_generator_fails(dc, world):
    full_world(world)
    world.items.pop()
    world.page(59, truth={"readers": ["reader-a", "gen-author"]})
    assert run(dc, world.manifest()) == FAIL


@pytest.mark.parametrize("readers", [["reader-a", "reader-a "], ["", "reader-b"], [1, 2]],
                         ids=["whitespace-duplicate", "empty-name", "non-string"])
def test_readers_must_be_two_distinct_named_people(dc, world, readers):
    full_world(world, 59)
    world.page(59, truth={"readers": readers})
    assert run(dc, world.manifest()) == FAIL


# --- rights and prohibited inputs --------------------------------------------

@pytest.mark.parametrize("over", [
    {"license": "unknown"}, {"license": None}, {"user_upload": True}, {"user_upload": None},
    {"legacy_fixture": True}, {"path": "fixtures/images/친구야.jpeg"}, {"family": "GIFTED-2024"},
    {"source": "user upload 2026-10-01"},
], ids=lambda o: next(iter(o)) + "=" + str(next(iter(o.values()))))
def test_rights_and_prohibited_input_fail(dc, world, over):
    full_world(world)
    world.items[0].update(over)
    if over.get("path"):  # make every other rule pass so only the prohibited-name guard can fail it
        ref = world.write(over["path"], b"refused bytes")
        world.items[0].update(ref, truth=world.truth(0, ref["sha256"]))
    assert run(dc, world.manifest()) == FAIL


def test_plan_required_allowable_use_is_enforced(dc, world):
    full_world(world)
    del world.items[0]["allowable_use"]
    assert run(dc, world.manifest()) == FAIL


def test_plan_required_font_version_is_enforced(dc, world):
    full_world(world)
    font = world.write("training/chords/fonts/f.ttf", b"font bytes")
    world.fonts.append({**font, "license": "Bitstream-Vera-and-public-domain"})
    assert run(dc, world.manifest()) == FAIL


# --- hashing scope ------------------------------------------------------------

@pytest.mark.parametrize("rel", [".env.test", ".git/config", "backend/api/main.py"])
def test_page_path_must_be_a_data_file_not_internal_file(dc, world, rel):
    full_world(world)
    ref = world.write(rel, b"SYNTHETIC-NON-DATA")
    world.items[0].update(ref)
    world.items[0]["truth"] = world.truth(0, ref["sha256"])
    assert run(dc, world.manifest()) == FAIL


# --- malformed shapes: structured FAIL, never a crash -------------------------

MALFORMED = {
    "item-is-string": lambda w: w.items.append("oops"),
    "fonts-is-string": lambda w: setattr(w, "fonts", "oops"),
    "font-is-string": lambda w: w.fonts.append("oops"),
    "authors-is-int": lambda w: setattr(w, "authors", 5),
    "id-is-list": lambda w: w.items[0].update(id=["h0"]),
    "family-is-list": lambda w: w.items[0].update(family=["f"]),
}


@pytest.mark.parametrize("case", sorted(MALFORMED))
def test_malformed_manifest_is_structured_fail(dc, world, case):
    full_world(world)
    MALFORMED[case](world)
    assert run(dc, world.manifest()) == FAIL


def test_top_level_list_manifest_is_structured_fail(dc, world):
    m = world.manifest()
    m.write_text("[]")
    assert run(dc, m) == FAIL


def _truth_file(world, i, raw: bytes):
    item = world.items[i]
    item["truth"] = world.write(f"data/chord-ocr/truth/raw{i}.json", raw)


@pytest.mark.parametrize("raw", [b"[]", b"{not json", b"\xff\xfe\x00", b'"text"'],
                         ids=["list", "invalid-json", "not-utf8", "string"])
def test_malformed_truth_file_is_structured_fail(dc, world, raw):
    full_world(world)
    _truth_file(world, 0, raw)
    assert run(dc, world.manifest()) == FAIL


@pytest.mark.parametrize("truth", [
    {"readers": [{"n": 1}, {"n": 2}]},
    {"chords": ["G"]},
    {"staff_systems": "0-40"},
], ids=["unhashable-readers", "chord-is-string", "systems-is-string"])
def test_malformed_truth_shape_is_structured_fail(dc, world, truth):
    full_world(world, 59)
    world.page(59, truth=truth)
    assert run(dc, world.manifest()) == FAIL


# --- truth geometry -----------------------------------------------------------

@pytest.mark.parametrize("truth", [
    {"chords": [{"text": "G", "bbox": ["0", "0", "1", "1"], "system": 0}]},
    {"chords": [{"text": "G", "bbox": [5, 5, 1, 1], "system": 0}]},
    {"chords": [{"text": "G", "bbox": [-3, 0, 1, 1], "system": 0}]},
    {"chords": [{"text": "G", "bbox": [0, 0, 1, 1], "system": True}]},
    {"chords": [{"text": "G", "bbox": [0, 0, 4, 4], "system": 0}, {"text": "G", "bbox": [0, 0, 4, 4], "system": 0}]},
    {"staff_systems": [{"y0": 10, "y1": 60}, {"y0": 50, "y1": 90}],
     "chords": [{"text": "G", "bbox": [0, 0, 4, 4], "system": 0}]},
    {"staff_systems": [{"y0": 100, "y1": 140}, {"y0": 10, "y1": 40}],
     "chords": [{"text": "G", "bbox": [0, 0, 4, 4], "system": 0}]},
    {"staff_systems": [{"y0": True, "y1": 40}], "chords": [{"text": "G", "bbox": [0, 0, 4, 4], "system": 0}]},
], ids=["bbox-strings", "bbox-inverted", "bbox-negative", "system-bool", "duplicate-label",
        "overlapping-systems", "unsorted-systems", "system-y-bool"])
def test_invalid_truth_geometry_fails(dc, world, truth):
    full_world(world, 59)
    world.page(59, truth=truth)
    assert run(dc, world.manifest()) == FAIL


def test_bbox_outside_decoded_image_fails(dc, world):
    full_world(world, 59)
    world.page(59, truth={"chords": [{"text": "G", "bbox": [150, 10, 260, 30], "system": 0}]})
    assert run(dc, world.manifest()) == FAIL


def _replace_page_bytes(world, i: int, data: bytes) -> None:
    """Swap a page's bytes and keep hash and truth consistent, so only decoding can fail it."""
    ref = world.write(f"data/chord-ocr/pages/p{i}.png", data)
    world.items[i].update(ref, truth=world.truth(i, ref["sha256"]))


def test_decodable_page_control_is_ready(dc, world):
    full_world(world)
    _replace_page_bytes(world, 59, png(1000))
    errs, stats = dc.check(world.manifest())
    assert errs == [] and stats["pages"] == 60
    assert run(dc, world.manifest()) == READY


def _corrupt_idat(data: bytes) -> bytes:
    at = data.index(b"IDAT") + 8
    return data[:at] + bytes(b ^ 0xFF for b in data[at:at + 8]) + data[at + 8:]


@pytest.mark.parametrize("make", [
    lambda: b"opaque stub, not an image",
    lambda: png(1000)[:60],
    lambda: _corrupt_idat(png(1000)),
], ids=["opaque-bytes", "truncated-png", "corrupt-idat"])
def test_undecodable_real_recapture_page_fails(dc, world, make):
    full_world(world)
    _replace_page_bytes(world, 59, make())
    assert run(dc, world.manifest()) == FAIL


# --- diagnostics hygiene ------------------------------------------------------

def test_fail_output_does_not_echo_untrusted_ids_paths_or_names(dc, world, capsys):
    sentinel = "SENTINEL-7Q2"
    world.page(0, id=f"{sentinel}-id", family=f"{sentinel}-fam")
    world.page(1, family=f"{sentinel}-fam", split="train", kind="synthetic", composer="c-train")
    world.items.append({**world.items[0], "id": "h2", "path": f"data/chord-ocr/pages/{sentinel}-name.png"})
    manifest_text = world.manifest().read_text()
    assert sentinel in manifest_text  # T5: the same substring detector sees the sentinel in the input
    assert run(dc, world.root / "data/chord-ocr/manifest.json") == FAIL
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert sentinel not in out
