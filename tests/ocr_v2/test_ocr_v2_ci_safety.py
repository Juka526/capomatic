"""CI/fixture safety for V2-1: refused fixture gone, cleared fixture pinned,
training/data excluded from the image, CI chord assertion has teeth."""
from __future__ import annotations

import io
import json
import re
import struct
import subprocess
import sys
import textwrap

from PIL import Image, ImageChops

from tests.ocr_v2.conftest import ROOT, load_dataset_check, repo_file, sha

REFUSED = re.compile(r"친구야|hey_buddy|gifted", re.I)
CLEARED = "fixtures/images/ci-selfmade.png"
CI_CHORDS = "G D/F# Em7 C Am7 D7 Bm7 Em C G/B Am7 D".split()  # read off the drawn page, not from OCR


def _manifest_item(path: str) -> dict:
    m = json.loads((ROOT / "training/chords/manifest.json").read_text())
    return next(i for i in m["items"] if i["path"] == path)


# --- refused fixture ----------------------------------------------------------

def test_refused_fixture_detector_known_positive():
    assert REFUSED.search('-F "image=@fixtures/images/친구야.jpeg"')
    assert REFUSED.search('TEST_IMAGE = "fixtures/images/친구야.jpeg"')


def test_ci_workflow_does_not_reference_refused_fixture():
    text = repo_file("CM1_CI_YML", ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert not REFUSED.search(text)
    assert f"image=@{CLEARED}" in text


def test_integration_input_is_the_cleared_fixture():
    text = repo_file("CM1_INTEGRATION_CONFTEST", "tests/integration/conftest.py").read_text(encoding="utf-8")
    assert not REFUSED.search(text)
    assert f'TEST_IMAGE = "{CLEARED}"' in text


def test_cleared_fixture_matches_manifest_rights_record():
    item = _manifest_item(CLEARED)
    assert sha((ROOT / CLEARED).read_bytes()) == item["sha256"]
    assert item["split"] == "ci_diagnostic" and item["kind"] == "synthetic"
    assert item["license"] == "CC0-1.0"
    assert item["user_upload"] is False and item["legacy_fixture"] is False


def test_repository_manifest_is_valid_and_on_hold():
    dc = load_dataset_check(ROOT)
    errs, stats = dc.check(ROOT / "training/chords/manifest.json")
    assert errs == []
    assert stats == {"pages": 0, "occurrences": 0, "systems": 0}
    assert dc.main(["dataset_check.py"]) == 2


# --- Docker image exclusions ----------------------------------------------------

def _ignored(text: str) -> set[str]:
    return {ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")}


def test_dockerignore_parser_known_positive():
    assert "fixtures" in _ignored(repo_file("CM1_DOCKERIGNORE", ".dockerignore").read_text())


def test_dockerignore_excludes_training_and_data():
    assert {"training", "data"} <= _ignored(repo_file("CM1_DOCKERIGNORE", ".dockerignore").read_text())


# --- the CI chord assertion itself ------------------------------------------------

def _ci_assertion() -> str:
    text = repo_file("CM1_CI_YML", ".github/workflows/ci.yml").read_text(encoding="utf-8")
    m = re.search(r"python3 - <<'PY'\n(.*?)\n\s*PY\n", text, re.S)
    assert m, "CI chord assertion block not found"
    return textwrap.dedent(m.group(1))


def _run_ci_assertion(tmp_path, texts: list[str]) -> subprocess.CompletedProcess:
    (tmp_path / "detect.json").write_text(json.dumps({"chords": [{"text": t} for t in texts]}))
    return subprocess.run([sys.executable, "-I", "-c", _ci_assertion()], cwd=tmp_path,
                          capture_output=True, text=True, timeout=60)


def test_ci_assertion_accepts_known_positive_12_chords(tmp_path):
    r = _run_ci_assertion(tmp_path, CI_CHORDS)
    assert r.returncode == 0, r.stderr
    assert "12/12 expected chords" in r.stdout


def test_ci_assertion_rejects_known_negative_one_chord(tmp_path):
    r = _run_ci_assertion(tmp_path, ["G"])
    assert r.returncode != 0
    assert "does not read the known chords" in r.stderr


def test_ci_assertion_rejects_nine_of_twelve(tmp_path):
    r = _run_ci_assertion(tmp_path, CI_CHORDS[:9])
    assert r.returncode != 0


# --- font pin and generator reproducibility -----------------------------------------

def _font_version(data: bytes) -> str:
    """nameID 5 from the TrueType name table (no font library needed)."""
    for i in range(struct.unpack(">H", data[4:6])[0]):
        tag, _, off, _ = struct.unpack(">4sIII", data[12 + 16 * i:28 + 16 * i])
        if tag != b"name":
            continue
        _, count, strings = struct.unpack(">HHH", data[off:off + 6])
        for j in range(count):
            pid, _, _, nid, length, o = struct.unpack(">6H", data[off + 6 + 12 * j:off + 18 + 12 * j])
            if nid == 5:
                raw = data[off + strings + o:off + strings + o + length]
                return raw.decode("utf-16-be" if pid in (0, 3) else "latin-1")
    raise AssertionError("no version string")


def test_font_file_matches_manifest_hash_and_version():
    m = json.loads((ROOT / "training/chords/manifest.json").read_text())
    (font,) = m["fonts"]
    data = (ROOT / font["path"]).read_bytes()
    assert sha(data) == font["sha256"]
    assert _font_version(data) == "Version " + font["version"].split()[0]
    assert (ROOT / font["notice"]).read_text().startswith("Fonts are (c) Bitstream")


def _generator(monkeypatch):
    """Fresh import of the real generator, always in --check mode so it never writes the fixture."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "gen_ci_fixture_under_test", repo_file("CM1_GEN_FIXTURE", "training/chords/gen_ci_fixture.py"))
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    monkeypatch.setattr(sys, "argv", ["gen_ci_fixture.py", "--check"])
    return gen


def test_generator_renders_the_committed_fixture_pixels(monkeypatch):
    """Build-dependent: holds for the Pillow/FreeType build that made the fixture."""
    rendered = _generator(monkeypatch).render()
    committed = Image.open(io.BytesIO((ROOT / CLEARED).read_bytes())).convert("RGB")
    assert ImageChops.difference(rendered, committed).getbbox() is None


def test_generator_check_known_positive(monkeypatch):
    assert _generator(monkeypatch).main() == 0


def test_generator_check_catches_regeneration_drift(monkeypatch):
    gen = _generator(monkeypatch)
    before = sha((ROOT / CLEARED).read_bytes())
    original = gen.render

    def drifted():
        img = original()
        img.putpixel((0, 0), (0, 0, 0))
        return img

    monkeypatch.setattr(gen, "render", drifted)
    assert gen.main() == 1
    assert sha((ROOT / CLEARED).read_bytes()) == before


def test_generator_check_catches_manifest_hash_mismatch(monkeypatch, tmp_path):
    gen = _generator(monkeypatch)
    m = json.loads((ROOT / "training/chords/manifest.json").read_text())
    for item in m["items"]:
        if item["path"] == CLEARED:
            item["sha256"] = "0" * 64
    (tmp_path / "manifest.json").write_text(json.dumps(m))
    monkeypatch.setattr(gen, "MANIFEST", tmp_path / "manifest.json")
    assert gen.main() == 1
