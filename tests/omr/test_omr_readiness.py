"""Acceptance tests for research/melody/readiness.py (M0 register + Lock A gate).

Scope and limits:
- Every file here is innocuous synthetic bytes in pytest's tmp_path. A passing
  synthetic lock proves only that the checker is machine-consistent; it can
  never prove real rights, real human readers or real provenance.
- `labels_file`/`chord_snapshot_file` (lock) and `license_file`/`asset_file`
  (register) are the approved canonical fields: every hash is checked against
  real bytes of a repo-relative file, with no caller opt-out.
- Each negative test starts from the valid lock, which must pass first (T5).
"""
import copy
import hashlib
import importlib.util
import json
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("melody_readiness", ROOT / "research/melody/readiness.py")
readiness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(readiness)

REAL_REGISTER = json.loads((ROOT / "research/melody/rights_register.json").read_text())
# Plan section 6: the minimum asset set for an Audiveris + Korean-text experiment.
CORE_ASSETS = ("audiveris", "temurin_jre", "tessdata_kor", "tessdata_eng", "noto_sans_cjk_kr")
REJECTION_TYPES = (
    "grand_staff", "multi_voice", "transposing_instrument", "clef_change", "time_change",
    "key_change", "percussion", "tab", "handwritten", "microtonal", "grace_notes", "tuplets",
    "complex_repeats", "minor_modal", "ledger_overflow", "lyric_chord_collision",
)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write(root: Path, rel: str, data: bytes) -> str:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return sha(data)


def cleared_register(root: Path) -> dict:
    """Synthetic calibration register: each hash names real bytes written under root."""
    reg = copy.deepcopy(REAL_REGISTER)
    for e in reg["entries"]:
        lic, asset = f"assets/{e['id']}.license", f"assets/{e['id']}.bin"
        e.update(status="cleared", required=e["id"] in CORE_ASSETS or e["required"],
                 license_file=lic, license_sha256=write(root, lic, b"synthetic license " + e["id"].encode()),
                 asset_file=asset, asset_sha256=write(root, asset, b"synthetic asset " + e["id"].encode()))
    return reg


def valid_lock(root: Path) -> dict:
    snippets = []
    for i in range(8):
        split = "dev" if i < 6 else "heldout"
        snippets.append(dict(
            id=f"s{i}", split=split, crop_bbox=[0, 0, 100, 100], rights_evidence=f"rights/doc{i}.txt",
            event_count=70,
            source_file=f"data/s{i}.png", source_sha256=write(root, f"data/s{i}.png", b"src%d" % i),
            labels_file=f"data/s{i}.labels.json", labels_sha256=write(root, f"data/s{i}.labels.json", b"lab%d" % i),
            chord_snapshot_file=f"data/s{i}.chords.json",
            chord_snapshot_sha256=write(root, f"data/s{i}.chords.json", b"chd%d" % i),
        ))
    rejections = [dict(id=f"r{t}_{k}", type=name, file_sha256=sha(b"rej%d_%d" % (t, k)), expected_reason=name)
                  for t, name in enumerate(REJECTION_TYPES) for k in range(2)]
    return dict(
        locked_at="2026-10-14T00:00:00Z",
        snippets=snippets,
        rejection_cases=rejections,
        thresholds_frozen=True,
        alignment_metric="printed-order x-position match",
        timebox_days=5,
        candidate_engines=["audiveris"],
        correction_procedure_sha256=sha(b"correction procedure v1"),
        scorer=dict(path="tests/omr/scorer.py", sha256=write(root, "tests/omr/scorer.py", b"# scorer\n"),
                    reviewer="rev1"),
        roles={"labelers": ["la", "lb"], "correctors": ["ca", "cb"], "raters": ["ra", "rb", "rc"],
               "developers": ["dev1"], "heldout_readers": ["hx"]},
        heldout_sealed=True,
    )


def problems(lock: dict, root: Path, reg: dict | None = None) -> list:
    """Fail-closed view: a crash counts as NOT READY, an empty list as READY."""
    try:
        return readiness.readiness(reg or cleared_register(root), lock, root)
    except Exception as e:  # noqa: BLE001 - a crash is a fail-closed result, recorded as such
        return [f"crash:{type(e).__name__}"]


# --- Real state stays NOT READY ------------------------------------------

def test_real_register_is_not_ready():
    assert readiness.check_register(REAL_REGISTER)


def test_real_state_without_lock_is_not_ready():
    assert "lock_a.json missing" in readiness.readiness(REAL_REGISTER, None)


def test_oemer_weights_are_blocked_in_register():
    e = {x["id"]: x for x in REAL_REGISTER["entries"]}
    assert e["oemer_weights"]["status"] == "blocked"
    assert e["oemer_weights"]["license"] == "UNKNOWN"


# --- T5: the legitimate synthetic fixture passes before negatives count ----

def test_valid_register_passes(tmp_path):
    assert readiness.check_register(cleared_register(tmp_path), tmp_path) == []


def test_valid_lock_passes(tmp_path):
    assert problems(valid_lock(tmp_path), tmp_path) == []


# --- Register negatives -----------------------------------------------------

def _reg_problems(reg, root):
    try:
        return readiness.check_register(reg, root)
    except Exception as e:  # noqa: BLE001
        return [f"crash:{type(e).__name__}"]


@pytest.mark.parametrize("asset_id", CORE_ASSETS)
def test_register_missing_core_asset_not_ready(tmp_path, asset_id):
    reg = cleared_register(tmp_path)
    reg["entries"] = [e for e in reg["entries"] if e["id"] != asset_id]
    assert _reg_problems(reg, tmp_path)


def test_register_empty_not_ready(tmp_path):
    assert _reg_problems({"entries": []}, tmp_path)


@pytest.mark.parametrize("asset_id", CORE_ASSETS)
def test_register_core_asset_marked_optional_not_ready(tmp_path, asset_id):
    reg = cleared_register(tmp_path)
    next(e for e in reg["entries"] if e["id"] == asset_id)["required"] = False
    assert _reg_problems(reg, tmp_path)


@pytest.mark.parametrize("field, value", [
    ("license_sha256", "x"), ("license_sha256", "a" * 63), ("asset_sha256", "g" * 64),
    ("asset_sha256", "A" * 64), ("status", "Cleared"),
])
def test_register_malformed_hash_or_status_not_ready(tmp_path, field, value):
    reg = cleared_register(tmp_path)
    reg["entries"][0][field] = value
    assert _reg_problems(reg, tmp_path)


def test_register_entry_without_required_flag_fails_closed(tmp_path):
    reg = cleared_register(tmp_path)
    del reg["entries"][0]["required"]
    assert _reg_problems(reg, tmp_path)


# --- Register byte checks are mandatory: no caller argument may skip them ---

def _entry(reg, asset_id="audiveris"):
    return next(e for e in reg["entries"] if e["id"] == asset_id)


def _escape_outside(tmp_path, root):
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"synthetic outside bytes")
    return outside, sha(b"synthetic outside bytes")


@pytest.mark.parametrize("field", ["license_file", "asset_file"])
@pytest.mark.parametrize("asset_id", CORE_ASSETS)
def test_cleared_entry_without_file_not_ready_by_default(tmp_path, field, asset_id):
    reg = cleared_register(tmp_path)
    _entry(reg, asset_id).pop(field)
    assert readiness.check_register(reg, tmp_path)
    assert readiness.readiness(reg, valid_lock(tmp_path), tmp_path)


@pytest.mark.parametrize("field", ["license_file", "asset_file"])
def test_explicit_non_strict_argument_cannot_bypass(tmp_path, field):
    reg = cleared_register(tmp_path)
    _entry(reg)[field] = None
    for kwargs in ({"strict_files": False}, {}):
        try:
            got = readiness.check_register(reg, tmp_path, **kwargs)
        except TypeError:
            got = ["argument removed"]  # no bypass parameter at all is also acceptable
        assert got, kwargs


@pytest.mark.parametrize("case", ["missing", "mismatch", "absolute", "dotdot", "symlink", "secret_name"])
@pytest.mark.parametrize("field, hash_key", [("license_file", "license_sha256"), ("asset_file", "asset_sha256")])
def test_unsafe_or_mismatched_register_file_not_ready_by_default(tmp_path, case, field, hash_key):
    root = tmp_path / "repo"
    reg = cleared_register(root)
    e = _entry(reg)
    outside, outside_sha = _escape_outside(tmp_path, root)
    if case == "missing":
        (root / e[field]).unlink()
    elif case == "mismatch":
        (root / e[field]).write_bytes(b"different synthetic bytes")
    elif case == "absolute":
        e[field], e[hash_key] = str(outside), outside_sha
    elif case == "dotdot":
        e[field], e[hash_key] = "../outside.bin", outside_sha
    elif case == "symlink":
        (root / "assets/link.bin").symlink_to(outside)
        e[field], e[hash_key] = "assets/link.bin", outside_sha
    else:  # innocuous bytes under a secret-looking name; never a real secret
        e[field], e[hash_key] = "assets/api_token.bin", write(root, "assets/api_token.bin", b"synthetic")
    assert readiness.check_register(reg, root), case
    assert readiness.readiness(reg, valid_lock(root), root), case


@pytest.mark.parametrize("bad", ["a" * 64 + "\n", " " + "a" * 64, "a" * 65])
def test_hash_matcher_is_exact(tmp_path, bad):
    reg = cleared_register(tmp_path)
    _entry(reg)["license_sha256"] = bad
    assert readiness.check_register(reg, tmp_path)


# --- Lock negatives: existing guards (regression) ---------------------------

def _mut(root, fn):
    lock = valid_lock(root)
    fn(lock)
    return problems(lock, root)


@pytest.mark.parametrize("name, fn", [
    ("role overlap", lambda l: l["roles"]["raters"].__setitem__(0, "la")),
    ("heldout reader is labeler", lambda l: l["roles"].__setitem__("heldout_readers", ["la"])),
    ("one labeler", lambda l: l["roles"].__setitem__("labelers", ["la"])),
    ("two raters", lambda l: l["roles"].__setitem__("raters", ["ra", "rb"])),
    ("GIFTED file", lambda l: l["snippets"][0].__setitem__("source_file", "data/GIFTED_1.png")),
    ("hey_buddy file", lambda l: l["snippets"][0].__setitem__("source_file", "data/hey_buddy.png")),
    ("NFC friend file", lambda l: l["snippets"][0].__setitem__("source_file", "data/친구야.jpeg")),
    ("bad label hash", lambda l: l["snippets"][0].__setitem__("labels_sha256", "zz")),
    ("heldout unsealed", lambda l: l.__setitem__("heldout_sealed", False)),
    ("scorer hash", lambda l: l["scorer"].__setitem__("sha256", "c" * 64)),
    ("no reviewer", lambda l: l["scorer"].__setitem__("reviewer", None)),
    ("few events", lambda l: [s.__setitem__("event_count", 10) for s in l["snippets"]]),
    ("no rejections", lambda l: l.__setitem__("rejection_cases", [])),
    ("thresholds open", lambda l: l.__setitem__("thresholds_frozen", False)),
    ("three engines", lambda l: l.__setitem__("candidate_engines", ["audiveris", "oemer", "homr"])),
    ("seven dev", lambda l: l["snippets"][6].__setitem__("split", "dev")),
    ("no rights evidence", lambda l: l["snippets"][0].__setitem__("rights_evidence", "")),
])
def test_existing_lock_guards_fire(tmp_path, name, fn):
    assert _mut(tmp_path, fn), name


# --- Lock negatives: orchestrator concerns ---------------------------------

@pytest.mark.parametrize("rel", ["data/s0.png", "data/s7.labels.json", "data/s3.chords.json"])
def test_missing_snippet_file_not_ready(tmp_path, rel):
    lock = valid_lock(tmp_path)
    (tmp_path / rel).unlink()
    assert problems(lock, tmp_path)


@pytest.mark.parametrize("rel", ["data/s0.png", "data/s7.labels.json", "data/s3.chords.json"])
def test_snippet_bytes_must_match_hash(tmp_path, rel):
    lock = valid_lock(tmp_path)
    (tmp_path / rel).write_bytes(b"different synthetic bytes")
    assert problems(lock, tmp_path)


def test_dev_and_heldout_cannot_share_source(tmp_path):
    lock = valid_lock(tmp_path)
    dev, held = lock["snippets"][0], lock["snippets"][7]
    held["source_file"], held["source_sha256"] = dev["source_file"], dev["source_sha256"]
    assert problems(lock, tmp_path)


def test_dev_and_heldout_cannot_share_labels(tmp_path):
    lock = valid_lock(tmp_path)
    dev, held = lock["snippets"][0], lock["snippets"][7]
    held["labels_file"], held["labels_sha256"] = dev["labels_file"], dev["labels_sha256"]
    assert problems(lock, tmp_path)


def test_duplicate_snippet_ids_not_ready(tmp_path):
    assert _mut(tmp_path, lambda l: l["snippets"][1].__setitem__("id", "s0"))


@pytest.mark.parametrize("name, cases", [
    ("32 empty", [{}] * 32),
    ("32 copies of one case", [dict(id="r", type="tab", file_sha256="d" * 64, expected_reason="tab")] * 32),
    ("one type 32 times", [dict(id=f"r{i}", type="tab", file_sha256=sha(b"%d" % i), expected_reason="tab")
                           for i in range(32)]),
])
def test_degenerate_rejection_cases_not_ready(tmp_path, name, cases):
    assert _mut(tmp_path, lambda l: l.__setitem__("rejection_cases", cases)), name


def test_rejection_case_missing_reason_not_ready(tmp_path):
    assert _mut(tmp_path, lambda l: l["rejection_cases"][0].__setitem__("expected_reason", None))


@pytest.mark.parametrize("variant", ["absolute", "dotdot", "other_name"])
def test_scorer_must_be_tester_owned_path(tmp_path, variant):
    root = tmp_path / "repo"
    lock = valid_lock(root)
    body = b"# not the tester scorer\n"
    if variant == "other_name":
        rel = "tests/omr/other.py"
        write(root, rel, body)
        path = rel
    else:
        outside = tmp_path / "outside" / "scorer.py"
        write(tmp_path, "outside/scorer.py", body)
        path = str(outside) if variant == "absolute" else "../outside/scorer.py"
    lock["scorer"].update(path=path, sha256=sha(body))
    assert problems(lock, root)


@pytest.mark.parametrize("key", ["locked_at", "correction_procedure_sha256"])
def test_lock_metadata_required(tmp_path, key):
    assert _mut(tmp_path, lambda l: l.pop(key))


def test_correction_hash_must_be_sha256(tmp_path):
    assert _mut(tmp_path, lambda l: l.__setitem__("correction_procedure_sha256", "todo"))


def test_scorer_reviewer_cannot_be_developer(tmp_path):
    assert _mut(tmp_path, lambda l: l["scorer"].__setitem__("reviewer", "dev1"))


@pytest.mark.parametrize("ids", ["ab", ["", " "], [None, None]])
def test_role_ids_must_be_real_distinct_strings(tmp_path, ids):
    assert _mut(tmp_path, lambda l: l["roles"].__setitem__("labelers", ids))


def test_nfd_friend_filename_is_excluded(tmp_path):
    # macOS commonly stores Hangul filenames decomposed (NFD).
    nfd = unicodedata.normalize("NFD", "data/친구야.jpeg")
    assert _mut(tmp_path, lambda l: l["snippets"][0].__setitem__("source_file", nfd))


@pytest.mark.parametrize("engine", ["oemer", "homr", "not_registered"])
def test_candidate_engine_must_be_cleared_in_register(tmp_path, engine):
    reg = cleared_register(tmp_path)
    for e in reg["entries"]:
        if e["id"].startswith("oemer"):
            e["status"] = "blocked"
    lock = valid_lock(tmp_path)
    lock["candidate_engines"] = [engine]
    assert problems(lock, tmp_path, reg)


def test_lock_template_uses_canonical_file_fields():
    tpl = json.loads((ROOT / "research/melody/lock_a.template.json").read_text())
    snippet = tpl["snippets"][0]
    for f in ("source_file", "labels_file", "chord_snapshot_file"):
        assert f in snippet and f.replace("_file", "_sha256") in snippet
    assert tpl["scorer"]["path"] == "tests/omr/scorer.py"
