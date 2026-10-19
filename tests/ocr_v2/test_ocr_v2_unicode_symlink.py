"""Unicode-normalised policy and symlink scope for dataset_check.py (S1 guards).

All files are synthetic temporaries under tmp_path; the hidden target uses a
harmless sentinel name, never a real dotfile.
"""
from __future__ import annotations

import os
import unicodedata
from pathlib import Path

import pytest

from tests.ocr_v2.conftest import png

FAIL = 1
NFD = lambda s: unicodedata.normalize("NFD", s)  # noqa: E731


def run(dc, manifest) -> int:
    return dc.main(["dataset_check.py", str(manifest)])


def full_world(world, pages=60):
    for i in range(pages):
        world.page(i)
    return world.manifest()


@pytest.fixture
def reads(monkeypatch):
    """Records every resolved file the validator reads or hashes."""
    seen: list[Path] = []
    real_bytes, real_text = Path.read_bytes, Path.read_text

    def read_bytes(self):
        seen.append(self.resolve())
        return real_bytes(self)

    def read_text(self, *a, **k):
        seen.append(self.resolve())
        return real_text(self, *a, **k)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setattr(Path, "read_text", read_text)
    return seen


def _link_page(world, i: int, target_rel: str) -> Path:
    """Page i becomes a symlink to target_rel holding valid page bytes; hash and truth stay consistent."""
    target = world.root / target_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    data = png(5000 + i)
    target.write_bytes(data)
    link = world.root / world.items[i]["path"]
    link.unlink()
    link.symlink_to(os.path.relpath(target, link.parent))
    ref = world.write(f"data/chord-ocr/pages/copy{i}.png", data)
    world.items[i]["sha256"] = ref["sha256"]
    world.items[i]["truth"] = world.truth(i, ref["sha256"])
    (world.root / ref["path"]).unlink()
    return target.resolve()


# --- Unicode-normalised prohibited names and identities -------------------------

@pytest.mark.parametrize("field", ["source", "family"])
def test_nfd_prohibited_source_or_family_fails(dc, world, field):
    full_world(world)
    world.items[0][field] = NFD("친구야 sheet")
    assert run(dc, world.manifest()) == FAIL


def test_nfd_prohibited_page_path_fails_without_reading(dc, world, reads):
    full_world(world)
    rel = "data/chord-ocr/pages/" + NFD("친구야") + ".png"
    ref = world.write(rel, png(4000))
    world.items[0].update(ref, truth=world.truth(0, ref["sha256"]))
    m = world.manifest()
    assert NFD("친구야") != "친구야"  # the input really is decomposed
    assert run(dc, m) == FAIL
    assert (world.root / rel).resolve() not in reads


def test_benign_nfd_actual_path_is_allowed_and_read(dc, world, reads):
    full_world(world)
    rel = "data/chord-ocr/pages/" + NFD("café") + ".png"
    ref = world.write(rel, png(4001))
    world.items[0].update(ref, truth=world.truth(0, ref["sha256"]))
    errs, stats = dc.check(world.manifest())
    assert errs == [] and stats["pages"] == 60
    assert (world.root / rel).resolve() in reads


@pytest.mark.parametrize("readers", [
    ["José", NFD("José")],
    ["reader-a", "ｒｅａｄｅｒ-ａ"],
], ids=["nfc-vs-nfd", "fullwidth"])
def test_canonically_equivalent_readers_are_one_person(dc, world, readers):
    full_world(world, 59)
    world.page(59, truth={"readers": readers})
    assert run(dc, world.manifest()) == FAIL


@pytest.mark.parametrize("author,reader", [("gén-author", NFD("Gén-author")), ("gen-author", "ＧＥＮ-author")],
                         ids=["nfd", "fullwidth"])
def test_reader_equivalent_to_generator_author_fails(dc, world, author, reader):
    world.authors = [author]
    full_world(world, 59)
    world.page(59, truth={"readers": ["reader-a", reader]})
    assert run(dc, world.manifest()) == FAIL


def test_composer_equivalent_to_generator_author_fails(dc, world):
    full_world(world)
    world.items[0]["composer"] = "ＧＥＮ-AUTHOR"
    assert run(dc, world.manifest()) == FAIL


# --- symlinks: target re-checked before any read ---------------------------------

def test_in_scope_symlink_is_allowed_and_target_read(dc, world, reads):
    """T5 positive: the same read detector sees the resolved in-scope target."""
    full_world(world)
    target = _link_page(world, 0, "data/chord-ocr/pages/real0.png")
    errs, stats = dc.check(world.manifest())
    assert errs == [] and stats["pages"] == 60
    assert target in reads


@pytest.mark.parametrize("target_rel", [
    ".sentinel-hidden/page.png",
    "data/chord-ocr/.sentinel-hidden/page.png",
    "backend/sentinel/page.png",
    "data/chord-ocr/pages/친구야.png",
], ids=["hidden-root", "hidden-in-scope-dir", "out-of-scope", "prohibited"])
def test_symlink_to_refused_target_fails_with_zero_reads(dc, world, reads, capsys, target_rel):
    full_world(world)
    target = _link_page(world, 0, target_rel)
    assert run(dc, world.manifest()) == FAIL
    assert target not in reads
    assert "sentinel" not in capsys.readouterr().out


def test_directory_symlink_to_hidden_dir_fails_with_zero_reads(dc, world, reads):
    full_world(world)
    hidden = world.root / ".sentinel-hidden"
    hidden.mkdir()
    data = png(4100)
    (hidden / "p.png").write_bytes(data)
    (world.root / "data/chord-ocr/linked").symlink_to(os.path.relpath(hidden, world.root / "data/chord-ocr"))
    ref = {"path": "data/chord-ocr/linked/p.png", "sha256": world.write("data/chord-ocr/tmp.png", data)["sha256"]}
    (world.root / "data/chord-ocr/tmp.png").unlink()
    world.items[0].update(ref, truth=world.truth(0, ref["sha256"]))
    assert run(dc, world.manifest()) == FAIL
    assert (hidden / "p.png").resolve() not in reads


def test_truth_symlink_out_of_scope_fails_with_zero_reads(dc, world, reads):
    full_world(world)
    truth_rel = world.items[0]["truth"]["path"]
    target = world.root / "backend/sentinel/t0.json"
    target.parent.mkdir(parents=True)
    (world.root / truth_rel).rename(target)
    (world.root / truth_rel).symlink_to(os.path.relpath(target, (world.root / truth_rel).parent))
    assert run(dc, world.manifest()) == FAIL
    assert target.resolve() not in reads
