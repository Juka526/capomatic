"""Fail-closed readiness check for the melody research (M0/M1). Reports NOT READY, never guesses.

    python research/melody/readiness.py              # real state; exit 1 unless READY
    python research/melody/readiness.py --selfcheck  # known-positive/negative control

This only checks that prerequisites exist and are consistent. It is NOT the acceptance scorer
(tests/omr/scorer.py, tester-owned) and measures nothing.
"""
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
HEX = re.compile(r"^[0-9a-f]{64}$")
BANNED = ("gifted", "친구야", "hey_buddy")  # rights refused by owner
ROLES = ("labelers", "correctors", "raters", "developers", "heldout_readers")
MIN_ROLE = {"labelers": 2, "correctors": 2, "raters": 3, "developers": 1, "heldout_readers": 1}


def check_register(reg: dict) -> list[str]:
    out = []
    for e in reg["entries"]:
        if not e["required"]:
            continue
        miss = [k for k in ("license_sha256", "asset_sha256") if not e.get(k)]
        if e["status"] != "cleared" or miss:
            out.append(f"asset {e['id']}: status={e['status']}, missing {miss or 'none'}")
    return out


def check_lock(lock: dict, root: Path = ROOT) -> list[str]:
    out = []
    snips = lock.get("snippets") or []
    for split, n in (("dev", 6), ("heldout", 2)):
        got = sum(s.get("split") == split for s in snips)
        if got != n:
            out.append(f"{split} snippets: {got} != {n}")
    for s in snips:
        sid = s.get("id")
        for k in ("source_sha256", "labels_sha256", "chord_snapshot_sha256"):
            if not HEX.match(str(s.get(k))):
                out.append(f"snippet {sid}: {k} not a sha256")
        if not s.get("rights_evidence"):
            out.append(f"snippet {sid}: no rights evidence")
        if any(b in str(s.get("source_file", "")).lower() for b in BANNED):
            out.append(f"snippet {sid}: excluded material")
    if sum(s.get("event_count") or 0 for s in snips if s.get("split") in ("dev", "heldout")) < 500:
        out.append("fewer than 500 labeled events across dev+heldout")
    if len(lock.get("rejection_cases") or []) != 32:
        out.append("rejection cases != 32")
    if not lock.get("thresholds_frozen"):
        out.append("thresholds not frozen")
    if not lock.get("alignment_metric") or not lock.get("timebox_days"):
        out.append("alignment metric / timebox missing")
    if not 1 <= len(lock.get("candidate_engines") or []) <= 2:
        out.append("candidate engines must be 1..2")
    if lock.get("heldout_sealed") is not True:
        out.append("held-out not sealed")
    roles = lock.get("roles") or {}
    seen = {}
    for r in ROLES:
        ids = roles.get(r) or []
        if len(set(ids)) < MIN_ROLE[r]:
            out.append(f"role {r}: need >= {MIN_ROLE[r]} distinct humans")
        for h in set(ids):
            if h in seen:
                out.append(f"role overlap: {h} in {seen[h]} and {r}")
            seen[h] = r
    sc = lock.get("scorer") or {}
    p = root / str(sc.get("path", ""))
    if not p.is_file():
        out.append("scorer missing (tester must author tests/omr/scorer.py)")
    elif hashlib.sha256(p.read_bytes()).hexdigest() != sc.get("sha256"):
        out.append("scorer sha256 does not match lock")
    if not sc.get("reviewer"):
        out.append("scorer has no second reviewer")
    return out


def readiness(reg: dict, lock: dict | None, root: Path = ROOT) -> list[str]:
    problems = check_register(reg)
    problems += ["lock_a.json missing"] if lock is None else check_lock(lock, root)
    return problems


def _selfcheck() -> None:
    import tempfile
    reg = json.loads((HERE / "rights_register.json").read_text())
    assert check_register(reg), "real register must NOT be ready"
    good_reg = copy.deepcopy(reg)
    for e in good_reg["entries"]:
        e.update(status="cleared", license_sha256="a" * 64, asset_sha256="b" * 64)
    assert check_register(good_reg) == []
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "tests/omr").mkdir(parents=True)
        (root / "tests/omr/scorer.py").write_text("x")
        h = "c" * 64
        sn = lambda i, sp: dict(id=i, split=sp, source_file=f"s{i}.png", source_sha256=h, labels_sha256=h,
                                chord_snapshot_sha256=h, rights_evidence="doc", event_count=70)
        good = dict(snippets=[sn(i, "dev") for i in range(6)] + [sn(6, "heldout"), sn(7, "heldout")],
                    rejection_cases=[{}] * 32, thresholds_frozen=True, alignment_metric="m", timebox_days=5,
                    candidate_engines=["audiveris"], heldout_sealed=True,
                    roles={"labelers": ["a", "b"], "correctors": ["c", "d"], "raters": ["e", "f", "g"],
                           "developers": ["h"], "heldout_readers": ["i"]},
                    scorer=dict(path="tests/omr/scorer.py", sha256=hashlib.sha256(b"x").hexdigest(), reviewer="r"))
        assert check_lock(good, root) == [], check_lock(good, root)
        breaks = {
            "overlap": lambda l: l["roles"]["raters"].__setitem__(0, "a"),
            "few readers": lambda l: l["roles"].__setitem__("labelers", ["a"]),
            "banned": lambda l: l["snippets"][0].__setitem__("source_file", "GIFTED_1.png"),
            "bad hash": lambda l: l["snippets"][0].__setitem__("labels_sha256", "zz"),
            "unsealed": lambda l: l.__setitem__("heldout_sealed", False),
            "scorer hash": lambda l: l["scorer"].__setitem__("sha256", h),
            "few events": lambda l: l["snippets"][0].__setitem__("event_count", 1),
            "rejections": lambda l: l.__setitem__("rejection_cases", []),
        }
        for name, brk in breaks.items():
            bad = copy.deepcopy(good)
            brk(bad)
            assert check_lock(bad, root), f"control failed to fire: {name}"
    print(f"readiness selfcheck OK (1 positive, {len(breaks)} negative controls fired)")


def main() -> int:
    if "--selfcheck" in sys.argv:
        _selfcheck()
        return 0
    reg = json.loads((HERE / "rights_register.json").read_text())
    lp = HERE / "lock_a.json"
    problems = readiness(reg, json.loads(lp.read_text()) if lp.exists() else None)
    if problems:
        print("NOT READY")
        print("\n".join(f"- {p}" for p in problems))
        return 1
    print("READY (prerequisites present; no experiment or measurement has been run)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
