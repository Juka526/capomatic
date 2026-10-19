"""Shared fixtures for the V2-1 chord-OCR data and CI-safety tests.

The files under test can be swapped for mutated copies through environment
variables (CM1_DATASET_CHECK, CM1_CI_YML, CM1_DOCKERIGNORE,
CM1_INTEGRATION_CONFTEST, CM1_GEN_FIXTURE) so mutation checks never edit product files.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import socket
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def repo_file(env: str, rel: str) -> Path:
    return Path(os.environ.get(env) or ROOT / rel)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def png(i: int = 0, w: int = 200, h: int = 200) -> bytes:
    """A real, decodable self-made page; one marker pixel makes the bytes distinct per index.

    Synthetic calibration only, never human holdout evidence."""
    img = Image.new("L", (w, h), 255)
    img.putpixel((i % w, h - 1 - (i // w) % h), 0)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class NetworkBlocked(RuntimeError):
    pass


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """T3: any socket connect inside this suite is an error."""
    def refuse(self, *args, **kwargs):
        raise NetworkBlocked(f"network access attempted: {args!r}")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)


def load_dataset_check(root: Path | None = None):
    path = repo_file("CM1_DATASET_CHECK", "training/chords/dataset_check.py")
    spec = importlib.util.spec_from_file_location("dataset_check_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if root is not None:
        mod.ROOT = root
    return mod


class World:
    """A throwaway repo root with independently written pages and truth files."""

    def __init__(self, root: Path):
        self.root = root
        self.items: list[dict] = []
        self.fonts: list[dict] = []
        self.authors = ["gen-author"]

    def write(self, rel: str, data: bytes) -> dict:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return {"path": rel, "sha256": sha(data)}

    def truth(self, i: int, image_sha: str, **over) -> dict:
        t = {
            "image_sha256": image_sha,
            "readers": ["reader-a", "reader-b"],
            "staff_systems": [{"y0": 10 + 40 * s, "y1": 40 + 40 * s} for s in range(4)],
            "chords": [
                {"text": "G", "bbox": [2 * c, 1 + 40 * (c % 4), 2 * c + 1, 9 + 40 * (c % 4)], "system": c % 4}
                for c in range(50)
            ],
        }
        t.update(over)
        return self.write(f"data/chord-ocr/truth/t{i}.json", json.dumps(t).encode())

    def page(self, i: int, *, truth: dict | None = None, **over) -> dict:
        # 200x200 covers every default label: systems end at y=160, boxes at x<=99, y<=129.
        ref = self.write(f"data/chord-ocr/pages/p{i}.png", png(i))
        item = {
            "id": f"h{i}", "path": ref["path"], "sha256": ref["sha256"],
            "split": "holdout", "kind": "real_recapture", "family": f"fam{i}",
            "source": "independent composer, phone recapture", "license": "CC0-1.0",
            "rights_holder": "independent composer", "composer": f"composer{i}",
            "allowable_use": "evaluation", "user_upload": False, "legacy_fixture": False,
            "independent_composition": True,
            "truth": self.truth(i, ref["sha256"], **(truth or {})),
        }
        item.update(over)
        self.items.append(item)
        return item

    def manifest(self, **over) -> Path:
        m = {"schema": 1, "generator_authors": self.authors, "fonts": self.fonts, "items": self.items}
        m.update(over)
        p = self.root / "data/chord-ocr/manifest.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(m))
        return p


@pytest.fixture
def world(tmp_path) -> World:
    return World(tmp_path)


@pytest.fixture
def dc(tmp_path):
    return load_dataset_check(tmp_path)
