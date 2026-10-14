"""Fail-closed manifest / split / readiness validator for chord-OCR data.

Exit 0 = valid AND primary-holdout ready, 1 = invalid (any rule broken or any
malformed input), 2 = valid but HOLD (primary gate minima not met). Missing or
empty input is never ready. Counts come from verified truth files, not manifest
claims. Diagnostics are fixed codes plus an item index: never ids, paths,
names or file content. The validator checks shape, hashes and policy only; it
cannot prove rights or that readers are real, independent humans.
Usage: python training/chords/dataset_check.py [manifest.json]
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "training/chords/manifest.json"

MIN_PAGES, MIN_OCCURRENCES, MIN_SYSTEMS = 60, 3000, 200  # primary holdout gate
SPLITS = {"train", "dev", "holdout", "ci_diagnostic"}
KINDS = {"synthetic", "real_recapture"}
LICENSES = {"CC0-1.0", "CC-BY-4.0", "owner-original-grant"}  # rights must be explicit
FONT_LICENSES = {"Bitstream-Vera-and-public-domain"}
PROHIBITED = re.compile(r"gifted|친구야|hey_buddy|upload", re.I)
# Hashing is scoped to data roots, checked BEFORE any filesystem access.
PAGE_ROOTS = ("data/chord-ocr/", "training/chords/")
CI_PAGE = "fixtures/images/ci-selfmade.png"
TRUTH_ROOTS = ("data/chord-ocr/",)
FONT_ROOTS = ("training/chords/fonts/",)
STR_KEYS = ("id", "path", "sha256", "split", "kind", "family", "source", "license", "rights_holder",
            "composer", "allowable_use")
SHA_RE = re.compile(r"[0-9a-f]{64}")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _name(v: object) -> str | None:
    """Normalised human/author name, or None when not a usable string."""
    return v.strip().casefold() if isinstance(v, str) and v.strip() and len(v) <= 64 else None


def _num(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _file(rel: object, want: object, roots: tuple[str, ...], errs: list[str], ctx: str, exact: str = "") -> Path | None:
    """Policy check on the string first, then resolve, then hash. None on failure."""
    if not (isinstance(rel, str) and isinstance(want, str) and SHA_RE.fullmatch(want)):
        errs.append(f"E_REF {ctx}")
        return None
    parts = PurePosixPath(rel).parts
    ok = ("\\" not in rel and "\0" not in rel and parts and not rel.startswith("/")
          and all(p not in ("", ".", "..") and not p.startswith(".") for p in parts)
          and (rel == exact or rel.startswith(roots)))
    if not ok or PROHIBITED.search(rel):
        errs.append(f"E_PATH_POLICY {ctx}")
        return None
    p = (ROOT / rel).resolve()
    if ROOT not in p.parents or not p.is_file():
        errs.append(f"E_FILE {ctx}")
    elif _sha(p) != want:
        errs.append(f"E_HASH {ctx}")
    else:
        return p
    return None


def _image_size(p: Path) -> tuple[int, int] | None:
    try:
        from PIL import Image  # noqa: PLC0415

        with Image.open(io.BytesIO(p.read_bytes())) as im:
            return im.size
    except Exception:  # noqa: BLE001  ponytail: undecodable bytes skip the bounds check (tests use stub pages); real pages must decode in the label tool
        return None


def _truth(item: dict, page: Path, authors: set, errs: list[str], ctx: str) -> tuple[int, int] | None:
    """Validate a holdout truth file; return (chord_occurrences, staff_systems)."""
    ref = item.get("truth")
    if not isinstance(ref, dict):
        errs.append(f"E_TRUTH_MISSING {ctx}")
        return None
    p = _file(ref.get("path"), ref.get("sha256"), TRUTH_ROOTS, errs, f"{ctx} truth")
    if p is None:
        return None
    try:
        t = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        errs.append(f"E_TRUTH_UNREADABLE {ctx}")
        return None
    n0 = len(errs)
    if not isinstance(t, dict):
        errs.append(f"E_TRUTH_SHAPE {ctx}")
        return None
    if t.get("image_sha256") != item["sha256"]:
        errs.append(f"E_TRUTH_IMAGE {ctx}")
    readers = t.get("readers")
    names = [_name(r) for r in readers] if isinstance(readers, list) else []
    if not names or None in names or len(set(names)) < 2:
        errs.append(f"E_READERS {ctx}")
    elif set(names) & authors:
        errs.append(f"E_READER_AUTHOR {ctx}")
    systems, chords = t.get("staff_systems"), t.get("chords")
    if not isinstance(systems, list) or not isinstance(chords, list):
        errs.append(f"E_TRUTH_SHAPE {ctx}")
        return None
    size = _image_size(page)
    last = -math.inf
    for sy in systems:  # sorted, non-overlapping vertical extents
        y0, y1 = (sy.get("y0"), sy.get("y1")) if isinstance(sy, dict) else (None, None)
        if not (_num(y0) and _num(y1) and 0 <= y0 < y1 and y0 >= last and (size is None or y1 <= size[1])):
            errs.append(f"E_SYSTEM {ctx}")
            break
        last = y1
    seen = set()
    for c in chords:
        b = c.get("bbox") if isinstance(c, dict) else None
        good = (isinstance(c, dict) and isinstance(c.get("text"), str) and c["text"].strip()
                and isinstance(b, list) and len(b) == 4 and all(_num(v) for v in b)
                and 0 <= b[0] < b[2] and 0 <= b[1] < b[3] and (size is None or (b[2] <= size[0] and b[3] <= size[1]))
                and _int(c.get("system")) and 0 <= c["system"] < len(systems))
        key = (c["text"], tuple(b), c["system"]) if good else None
        if not good or key in seen:
            errs.append(f"E_CHORD {ctx}")
            break
        seen.add(key)
    return (len(chords), len(systems)) if len(errs) == n0 else None


def _check(manifest: Path) -> tuple[list[str], dict]:
    errs: list[str] = []
    stats = {"pages": 0, "occurrences": 0, "systems": 0}
    try:
        m = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        return ["E_MANIFEST_UNREADABLE"], stats
    if not isinstance(m, dict) or m.get("schema") != 1 or not isinstance(m.get("items"), list):
        return ["E_MANIFEST_SHAPE"], stats
    raw_authors, fonts = m.get("generator_authors", []), m.get("fonts", [])
    names = [_name(a) for a in raw_authors] if isinstance(raw_authors, list) else []
    if not isinstance(raw_authors, list) or None in names or not isinstance(fonts, list):
        return ["E_MANIFEST_SHAPE"], stats
    authors = set(names)
    for i, f in enumerate(fonts):
        ok = isinstance(f, dict) and f.get("license") in FONT_LICENSES and isinstance(f.get("version"), str) and f["version"].strip()
        if not ok:
            errs.append(f"E_FONT font#{i}")
        else:
            _file(f.get("path"), f.get("sha256"), FONT_ROOTS, errs, f"font#{i}")
    ids, hashes = set(), {}
    fam_split: dict[str, set] = defaultdict(set)
    composers: dict[str, set] = defaultdict(set)
    for n, item in enumerate(m["items"]):
        ctx = f"item#{n}"
        if not isinstance(item, dict) or any(not (isinstance(item.get(k), str) and item[k].strip()) for k in STR_KEYS):
            errs.append(f"E_ITEM_FIELDS {ctx}")
            continue
        if item["id"] in ids:
            errs.append(f"E_DUP_ID {ctx}")
        ids.add(item["id"])
        if item["split"] not in SPLITS or item["kind"] not in KINDS:
            errs.append(f"E_SPLIT_KIND {ctx}")
            continue
        if item["license"] not in LICENSES:
            errs.append(f"E_LICENSE {ctx}")
        if item.get("user_upload") is not False or item.get("legacy_fixture") is not False:
            errs.append(f"E_PROVENANCE_FLAGS {ctx}")
        if PROHIBITED.search(f"{item['path']} {item['source']} {item['family']}"):
            errs.append(f"E_PROHIBITED {ctx}")
        exact = CI_PAGE if item["split"] == "ci_diagnostic" else ""
        page = _file(item["path"], item["sha256"], PAGE_ROOTS, errs, ctx, exact)
        if page is None:
            continue
        if item["sha256"] in hashes:
            errs.append(f"E_DUP_BYTES {ctx}")
        hashes[item["sha256"]] = n
        fam_split[item["family"]].add(item["split"])
        composers[_name(item["composer"]) or ""].add(item["split"])
        if item["split"] == "ci_diagnostic" and item["kind"] != "synthetic":
            errs.append(f"E_CI_KIND {ctx}")
        if item["split"] == "holdout":
            if item["kind"] != "real_recapture":
                errs.append(f"E_HOLDOUT_SYNTHETIC {ctx}")
            elif item.get("generator_id"):
                errs.append(f"E_HOLDOUT_GENERATOR {ctx}")
            elif item.get("independent_composition") is not True:
                errs.append(f"E_HOLDOUT_INDEPENDENCE {ctx}")
            elif _name(item["composer"]) in authors:
                errs.append(f"E_COMPOSER_AUTHOR {ctx}")
            else:
                got = _truth(item, page, authors, errs, ctx)
                if got:
                    stats["pages"] += 1
                    stats["occurrences"] += got[0]
                    stats["systems"] += got[1]
    for splits in fam_split.values():
        if len(splits - {"ci_diagnostic"}) > 1:
            errs.append("E_FAMILY_SPLIT")
    for comp, splits in composers.items():
        if "holdout" in splits and splits & {"train", "dev"}:
            errs.append("E_COMPOSER_SPLIT")
    return errs, stats


def check(manifest: Path) -> tuple[list[str], dict]:
    """Fail closed: any unexpected error is a FAIL, never a crash or a pass."""
    try:
        return _check(manifest)
    except Exception:  # noqa: BLE001
        return ["E_INTERNAL"], {"pages": 0, "occurrences": 0, "systems": 0}


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
    import shutil
    import tempfile

    (ROOT / "data/chord-ocr").mkdir(parents=True, exist_ok=True)  # inside a data root: path policy rejects elsewhere
    tmp = Path(tempfile.mkdtemp(prefix="selftest-", dir=ROOT / "data/chord-ocr"))
    img = tmp / "p.png"
    img.write_bytes(b"page")
    truth = {"image_sha256": _sha(img), "readers": ["r1", "r2"], "staff_systems": [{"y0": 0, "y1": 9}],
             "chords": [{"text": "G", "bbox": [0, 0, 1, 1], "system": 0}]}
    tp = tmp / "t.json"
    tp.write_text(json.dumps(truth))
    rel = lambda p: str(p.relative_to(ROOT))
    base = {"id": "a", "path": rel(img), "sha256": _sha(img), "split": "holdout", "kind": "real_recapture",
            "family": "f1", "source": "own", "license": "CC0-1.0", "rights_holder": "x", "composer": "c1", "allowable_use": "evaluation",
            "user_upload": False, "legacy_fixture": False, "independent_composition": True,
            "truth": {"path": rel(tp), "sha256": _sha(tp)}}

    def run(**over) -> list[str]:
        it = {**copy.deepcopy(base), **over}
        mp = tmp / "m.json"
        mp.write_text(json.dumps({"schema": 1, "generator_authors": ["gen"], "items": [it]}))
        return check(mp)[0]

    assert run() == [], run()
    for bad in ({"license": "unknown"}, {"user_upload": True}, {"path": "data/chord-ocr/친구야.jpeg"}, {"path": ".env"},
                {"kind": "synthetic"}, {"sha256": "0" * 64}, {"generator_id": "g"}, {"truth": None},
                {"independent_composition": False}):
        assert run(**bad), bad
    tp.write_text(json.dumps({**truth, "readers": ["r1", "gen"]}))
    assert run(truth={"path": rel(tp), "sha256": _sha(tp)}), "author-reader accepted"
    assert check(tmp / "absent.json")[0], "missing manifest must fail"
    shutil.rmtree(tmp)
    for d in (ROOT / "data/chord-ocr", ROOT / "data"):
        try:
            d.rmdir()  # only removes the dirs this selftest created
        except OSError:
            pass
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    sys.exit(main(sys.argv))
