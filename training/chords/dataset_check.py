"""Fail-closed manifest / split / readiness validator for chord-OCR data.

Exit 0 = valid AND primary-holdout ready, 1 = invalid (any rule broken),
2 = valid but HOLD (primary gate minima not met). Missing/empty input is HOLD,
never ready. Counts come from the verified truth files, not manifest claims.
Usage: python training/chords/dataset_check.py [manifest.json]
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "training/chords/manifest.json"

MIN_PAGES, MIN_OCCURRENCES, MIN_SYSTEMS = 60, 3000, 200  # primary holdout gate
SPLITS = {"train", "dev", "holdout", "ci_diagnostic"}
KINDS = {"synthetic", "real_recapture"}
LICENSES = {"CC0-1.0", "CC-BY-4.0", "owner-original-grant"}  # rights must be explicit
PROHIBITED = re.compile(r"gifted|친구야|hey_buddy|upload", re.I)
ITEM_KEYS = ("id", "path", "sha256", "split", "kind", "family", "source", "license", "rights_holder", "composer")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file(rel: object, want: object, errs: list[str], ctx: str) -> Path | None:
    """Resolve a repo-relative path and verify its hash; None on any failure."""
    if not isinstance(rel, str) or not isinstance(want, str):
        errs.append(f"{ctx}: path/sha256 missing")
        return None
    p = (ROOT / rel).resolve()
    if ROOT not in p.parents or not p.is_file():
        errs.append(f"{ctx}: file missing or outside repo: {rel}")
    elif _sha(p) != want:
        errs.append(f"{ctx}: sha256 mismatch: {rel}")
    else:
        return p
    return None


def _truth(item: dict, authors: set, errs: list[str], ctx: str) -> tuple[int, int] | None:
    """Validate a holdout truth file; return (chord_occurrences, staff_systems)."""
    ref = item.get("truth")
    if not isinstance(ref, dict):
        errs.append(f"{ctx}: holdout item needs truth")
        return None
    p = _file(ref.get("path"), ref.get("sha256"), errs, f"{ctx} truth")
    if p is None:
        return None
    t = json.loads(p.read_text(encoding="utf-8"))
    n0 = len(errs)
    if t.get("image_sha256") != item["sha256"]:
        errs.append(f"{ctx}: truth image_sha256 differs from page")
    readers = t.get("readers")
    if not isinstance(readers, list) or len(set(readers)) < 2:
        errs.append(f"{ctx}: truth needs >=2 distinct human readers")
    elif set(readers) & authors:
        errs.append(f"{ctx}: reader is a generator/model author")
    systems, chords = t.get("staff_systems"), t.get("chords")
    if not isinstance(systems, list) or not isinstance(chords, list):
        errs.append(f"{ctx}: truth needs staff_systems and chords lists")
        return None
    for s in systems:
        if not (isinstance(s, dict) and isinstance(s.get("y0"), int) and isinstance(s.get("y1"), int) and s["y0"] < s["y1"]):
            errs.append(f"{ctx}: bad staff system")
    for c in chords:
        b = c.get("bbox") if isinstance(c, dict) else None
        if not (isinstance(c.get("text"), str) and c["text"] and isinstance(b, list) and len(b) == 4
                and isinstance(c.get("system"), int) and 0 <= c["system"] < len(systems)):
            errs.append(f"{ctx}: bad chord label")
    return (len(chords), len(systems)) if len(errs) == n0 else None


def check(manifest: Path) -> tuple[list[str], dict]:
    errs: list[str] = []
    stats = {"pages": 0, "occurrences": 0, "systems": 0}
    try:
        m = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"manifest unreadable: {type(e).__name__}"], stats
    if m.get("schema") != 1 or not isinstance(m.get("items"), list):
        return ["manifest: schema must be 1 with an items list"], stats
    authors = set(m.get("generator_authors", []))
    for f in m.get("fonts", []):
        _file(f.get("path"), f.get("sha256"), errs, "font")
        if f.get("license") not in LICENSES | {"Bitstream-Vera-and-public-domain"}:
            errs.append(f"font {f.get('path')}: license not allowed")
    ids, hashes = set(), {}
    fam_split: dict[str, set] = defaultdict(set)
    composers: dict[str, set] = defaultdict(set)
    for item in m["items"]:
        ctx = f"item {item.get('id')}"
        missing = [k for k in ITEM_KEYS if not item.get(k)]
        if missing:
            errs.append(f"{ctx}: missing {missing}")
            continue
        if item["id"] in ids:
            errs.append(f"{ctx}: duplicate id")
        ids.add(item["id"])
        if item["split"] not in SPLITS or item["kind"] not in KINDS:
            errs.append(f"{ctx}: bad split/kind")
            continue
        if item["license"] not in LICENSES:
            errs.append(f"{ctx}: license unknown/not allowed")
        if item.get("user_upload") is not False or item.get("legacy_fixture") is not False:
            errs.append(f"{ctx}: must state user_upload=false and legacy_fixture=false")
        if PROHIBITED.search(f"{item['path']} {item['source']} {item['family']}"):
            errs.append(f"{ctx}: prohibited input")
        if _file(item["path"], item["sha256"], errs, ctx) is None:
            continue
        if item["sha256"] in hashes:
            errs.append(f"{ctx}: same image bytes as {hashes[item['sha256']]}")
        hashes[item["sha256"]] = item["id"]
        fam_split[item["family"]].add(item["split"])
        composers[item["composer"]].add(item["split"])
        if item["split"] == "ci_diagnostic" and item["kind"] != "synthetic":
            errs.append(f"{ctx}: ci_diagnostic must be synthetic")
        if item["split"] == "holdout":
            if item["kind"] != "real_recapture":
                errs.append(f"{ctx}: synthetic output is not independent holdout truth")
            elif item.get("generator_id"):
                errs.append(f"{ctx}: holdout page must not come from a training generator")
            elif item.get("independent_composition") is not True:
                errs.append(f"{ctx}: holdout needs independent_composition=true")
            else:
                got = _truth(item, authors, errs, ctx)
                if got:
                    stats["pages"] += 1
                    stats["occurrences"] += got[0]
                    stats["systems"] += got[1]
    for fam, splits in fam_split.items():
        if len(splits - {"ci_diagnostic"}) > 1:
            errs.append(f"family {fam}: spans splits {sorted(splits)}")
    for comp, splits in composers.items():
        if "holdout" in splits and splits & {"train", "dev"}:
            errs.append(f"composer {comp}: in holdout and train/dev")
    return errs, stats


def main(argv: list[str]) -> int:
    errs, st = check(Path(argv[1]) if len(argv) > 1 else DEFAULT_MANIFEST)
    for e in errs:
        print("FAIL:", e)
    short = [f"{k} {st[k]}/{lim}" for k, lim in (("pages", MIN_PAGES), ("occurrences", MIN_OCCURRENCES), ("systems", MIN_SYSTEMS)) if st[k] < lim]
    print("holdout counts:", st)
    if errs:
        return 1
    if short:
        print("HOLD: primary gate not met:", ", ".join(short))
        return 2
    print("READY: manifest valid and primary minima met (acceptance scoring is tester-owned)")
    return 0


def selftest() -> None:
    """Positive + negative oracle: ready fixture passes, each broken rule fails."""
    import copy
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix=".selftest-", dir=ROOT))  # inside ROOT: _file rejects outside paths
    img = tmp / "p.png"
    img.write_bytes(b"page")
    truth = {"image_sha256": _sha(img), "readers": ["r1", "r2"], "staff_systems": [{"y0": 0, "y1": 9}],
             "chords": [{"text": "G", "bbox": [0, 0, 1, 1], "system": 0}]}
    tp = tmp / "t.json"
    tp.write_text(json.dumps(truth))
    rel = lambda p: str(p.relative_to(ROOT))
    base = {"id": "a", "path": rel(img), "sha256": _sha(img), "split": "holdout", "kind": "real_recapture",
            "family": "f1", "source": "own", "license": "CC0-1.0", "rights_holder": "x", "composer": "c1",
            "user_upload": False, "legacy_fixture": False, "independent_composition": True,
            "truth": {"path": rel(tp), "sha256": _sha(tp)}}

    def run(**over) -> list[str]:
        it = {**copy.deepcopy(base), **over}
        mp = tmp / "m.json"
        mp.write_text(json.dumps({"schema": 1, "generator_authors": ["gen"], "items": [it]}))
        return check(mp)[0]

    assert run() == [], run()
    for bad in ({"license": "unknown"}, {"user_upload": True}, {"path": "fixtures/images/친구야.jpeg"},
                {"kind": "synthetic"}, {"sha256": "0" * 64}, {"generator_id": "g"}, {"truth": None},
                {"independent_composition": False}):
        assert run(**bad), bad
    tp.write_text(json.dumps({**truth, "readers": ["r1", "gen"]}))
    assert run(truth={"path": rel(tp), "sha256": _sha(tp)}), "author-reader accepted"
    assert check(tmp / "absent.json")[0], "missing manifest must fail"
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    sys.exit(main(sys.argv))
