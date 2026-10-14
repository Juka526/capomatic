"""Fail-closed readiness check for the melody research (M0/M1). Reports NOT READY, never guesses.

    python research/melody/readiness.py              # real state; exit 1 unless READY
    python research/melody/readiness.py --selfcheck  # known-positive/negative control

Checks machine-verifiable facts only (shapes, hashes against real bytes, role disjointness).
It CANNOT establish that rights are really cleared, that humans are really independent, or
that labels are right: those need independent human review. It is NOT the acceptance scorer
(tests/omr/scorer.py, tester-owned) and measures nothing.
"""
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
HEX = re.compile(r"[0-9a-f]{64}")
BANNED = ("gifted", "친구야", "hey_buddy")  # rights refused by owner
SECRET_PART = re.compile(r"(^\.env|^\.git$|^\.claude$|secret|credential|token|\.pem$|\.key$|^id_rsa)", re.I)
NONHUMAN = {"claude", "gpt", "llm", "bot", "model", "ai", "agent", "script", "audiveris", "oemer", "homr"}
ROLES = ("labelers", "correctors", "raters", "developers", "heldout_readers")
MIN_ROLE = {"labelers": 2, "correctors": 2, "raters": 3, "developers": 1, "heldout_readers": 1}
SCORER_PATH = "tests/omr/scorer.py"
# Assets needed by every experiment (Korean text + render stack); `required` flags cannot bypass.
CORE = ("audiveris", "temurin_jre", "tessdata_kor", "tessdata_eng", "noto_sans_cjk_kr")
RENDER_STACK = ("noto_sans_cjk_kr", "verovio", "music21", "playwright")
ENGINE_ASSETS = {
    "audiveris": ("audiveris", "temurin_jre", "tessdata_kor", "tessdata_eng"),
    "oemer": ("oemer", "oemer_weights", "onnxruntime"),
}


def _ok_hash(v) -> bool:
    return type(v) is str and HEX.fullmatch(v) is not None


def _text(v) -> bool:
    return type(v) is str and bool(v.strip())


def read_repo_file(root: Path, rel) -> Path | None:
    """Resolved path of a regular file strictly inside root, else None (symlink escapes,
    absolute paths, '..', env/secret-looking names are all refused BEFORE any read)."""
    if not _text(rel) or Path(rel).is_absolute():
        return None
    base = root.resolve()
    try:
        p = (base / rel).resolve()
        parts = p.relative_to(base).parts
    except (ValueError, OSError):
        return None
    if not parts or any(SECRET_PART.search(x) for x in parts) or not p.is_file():
        return None
    return p


def file_sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _bytes_match(root: Path, rel, want) -> bool:
    p = read_repo_file(root, rel)
    return p is not None and _ok_hash(want) and file_sha(p) == want


def check_register(reg, root: Path = ROOT, extra=(), strict_files=False) -> list[str]:
    out = []
    entries = reg.get("entries") if isinstance(reg, dict) else None
    if not isinstance(entries, list) or not entries or not all(isinstance(e, dict) for e in entries):
        return ["register: entries missing or malformed"]
    ids = [e.get("id") for e in entries]
    if len(set(map(str, ids))) != len(ids):
        out.append("register: duplicate ids")
    by_id = {e.get("id"): e for e in entries}
    for e in entries:
        if type(e.get("required")) is not bool:
            out.append(f"asset {e.get('id')}: required flag missing")
    need = set(CORE) | set(RENDER_STACK) | set(extra)
    for i in sorted(need):
        e = by_id.get(i)
        if e is None:
            out.append(f"asset {i}: not in register")
            continue
        if i in CORE and e.get("required") is not True:
            out.append(f"asset {i}: core asset marked optional")
        if e.get("status") != "cleared":
            out.append(f"asset {i}: status={e.get('status')!r}, not cleared")
        for k in ("license_sha256", "asset_sha256"):
            if not _ok_hash(e.get(k)):
                out.append(f"asset {i}: {k} missing or malformed")
        for f, k in (("license_file", "license_sha256"), ("asset_file", "asset_sha256")):
            if e.get(f) is None and not strict_files:
                continue
            if not _bytes_match(root, e.get(f), e.get(k)):
                out.append(f"asset {i}: {f} missing, unsafe or bytes do not match {k}")
    return out


def _bbox_ok(b) -> bool:
    return (isinstance(b, list) and len(b) == 4 and all(type(v) in (int, float) and v == v and abs(v) != float("inf") and v >= 0 for v in b)
            and b[0] < b[2] and b[1] < b[3])


def _banned(*names) -> bool:
    for n in names:
        n = unicodedata.normalize("NFC", str(n)).casefold()
        if any(unicodedata.normalize("NFC", b) in n for b in BANNED):
            return True
    return False


def _check_snippets(snips, root) -> list[str]:
    out = []
    if not isinstance(snips, list) or not all(isinstance(s, dict) for s in snips):
        return ["snippets malformed"]
    for split, n in (("dev", 6), ("heldout", 2)):
        got = sum(s.get("split") == split for s in snips)
        if got != n:
            out.append(f"{split} snippets: {got} != {n}")
    if len({s.get("id") for s in snips}) != len(snips) or not all(_text(s.get("id")) for s in snips):
        out.append("snippet ids empty or repeated")
    events = 0
    for s in snips:
        sid = s.get("id")
        if not _text(s.get("rights_evidence")):
            out.append(f"snippet {sid}: no rights evidence")
        if not _bbox_ok(s.get("crop_bbox")):
            out.append(f"snippet {sid}: crop_bbox invalid")
        for f, k in (("source_file", "source_sha256"), ("labels_file", "labels_sha256"),
                     ("chord_snapshot_file", "chord_snapshot_sha256")):
            if not _bytes_match(root, s.get(f), s.get(k)):
                out.append(f"snippet {sid}: {f} missing, unsafe or bytes do not match {k}")
        if _banned(sid, s.get("source_file", ""), s.get("labels_file", ""), s.get("chord_snapshot_file", "")):
            out.append(f"snippet {sid}: excluded material")
        n = s.get("event_count")
        if type(n) is not int or n < 0:
            out.append(f"snippet {sid}: event_count invalid")
        elif s.get("split") in ("dev", "heldout"):
            events += n
    if events < 500:
        out.append("fewer than 500 labeled events across dev+heldout")
    for f, k in (("source_file", "source_sha256"), ("labels_file", "labels_sha256"),
                 ("chord_snapshot_file", "chord_snapshot_sha256")):
        for key in (f, k):
            vals = [str(s.get(key)) for s in snips]
            if len(set(vals)) != len(vals):
                out.append(f"duplicate {key} across snippets")
    return out


def _check_rejections(cases) -> list[str]:
    if not isinstance(cases, list) or len(cases) != 32 or not all(isinstance(c, dict) for c in cases):
        return ["rejection cases != 32"]
    out = []
    if not all(_text(c.get("id")) and _text(c.get("type")) and _text(c.get("expected_reason"))
               and _ok_hash(c.get("file_sha256")) for c in cases):
        out.append("rejection case missing id/type/reason/file_sha256")
    for k in ("id", "file_sha256"):
        if len({str(c.get(k)) for c in cases}) != 32:
            out.append(f"rejection cases repeat {k}")
    types = [str(c.get("type")) for c in cases]
    if len(set(types)) != 16 or any(types.count(t) != 2 for t in set(types)):
        out.append("rejection cases must be 16 distinct types x 2")
    return out


def _check_roles(roles, reviewer) -> list[str]:
    out, seen = [], {}
    if not isinstance(roles, dict):
        return ["roles malformed"]
    for r in ROLES:
        ids = roles.get(r)
        if not isinstance(ids, list) or not all(_text(h) for h in ids) or len(set(ids)) != len(ids):
            out.append(f"role {r}: need a list of distinct non-empty human ids")
            continue
        if len(ids) < MIN_ROLE[r]:
            out.append(f"role {r}: need >= {MIN_ROLE[r]} distinct humans")
        for h in ids:
            if set(re.split(r"[\s._:/-]+", h.casefold())) & NONHUMAN:
                out.append(f"role {r}: non-human id")
            if h in seen:
                out.append(f"role overlap between {seen[h]} and {r}")
            seen[h] = r
    if not _text(reviewer):
        out.append("scorer has no second reviewer")
    elif reviewer in (roles.get("developers") or []):
        out.append("scorer reviewer is a developer")
    return out


def check_lock(lock, root: Path = ROOT) -> list[str]:
    if not isinstance(lock, dict):
        return ["lock malformed"]
    out = []
    try:
        datetime.fromisoformat(str(lock.get("locked_at")).replace("Z", "+00:00"))
    except ValueError:
        out.append("locked_at missing or not ISO-8601")
    if not _ok_hash(lock.get("correction_procedure_sha256")):
        out.append("correction_procedure_sha256 missing or malformed")
    out += _check_snippets(lock.get("snippets"), root)
    out += _check_rejections(lock.get("rejection_cases"))
    if lock.get("thresholds_frozen") is not True:
        out.append("thresholds not frozen")
    if not _text(lock.get("alignment_metric")) or type(lock.get("timebox_days")) is not int or lock["timebox_days"] <= 0:
        out.append("alignment metric / timebox missing")
    eng = lock.get("candidate_engines")
    if not isinstance(eng, list) or not 1 <= len(eng) <= 2 or len(set(map(str, eng))) != len(eng):
        out.append("candidate engines must be 1..2 distinct")
    if lock.get("heldout_sealed") is not True:
        out.append("held-out not sealed")
    sc = lock.get("scorer") if isinstance(lock.get("scorer"), dict) else {}
    if sc.get("path") != SCORER_PATH:
        out.append(f"scorer path must be exactly {SCORER_PATH}")
    elif not _bytes_match(root, SCORER_PATH, sc.get("sha256")):
        out.append("scorer missing (tester must author it) or sha256 mismatch")
    out += _check_roles(lock.get("roles"), sc.get("reviewer"))
    return out


def engine_assets(lock) -> tuple[list[str], list[str]]:
    """(register ids the chosen engines need, problems). Unknown/blocked engines fail closed."""
    need, bad = [], []
    chosen = list(lock.get("candidate_engines") or []) if isinstance(lock, dict) else []
    lb = lock.get("lock_b") if isinstance(lock, dict) else None
    if isinstance(lb, dict) and lb.get("engine") is not None:
        if lb["engine"] not in chosen:
            bad.append("lock_b engine is not a candidate")
        chosen = [lb["engine"]]
    for e in chosen:
        if e not in ENGINE_ASSETS:
            bad.append("candidate engine unknown")
        else:
            need += ENGINE_ASSETS[e]
    return need, bad


def readiness(reg, lock, root: Path = ROOT, strict_files=False) -> list[str]:
    need, bad = engine_assets(lock) if lock is not None else ([], [])
    try:
        problems = check_register(reg, root, need, strict_files) + bad
        problems += ["lock_a.json missing"] if lock is None else check_lock(lock, root)
    except (TypeError, KeyError, AttributeError, ValueError, OSError):
        problems = ["malformed input"]  # fail closed, no details (they could echo content)
    return problems


def _selfcheck() -> None:
    import copy
    import tempfile
    reg = json.loads((HERE / "rights_register.json").read_text())
    assert check_register(reg), "real register must NOT be ready"
    assert readiness(reg, None, strict_files=True)
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)

        def put(rel, data):
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            return rel, hashlib.sha256(data).hexdigest()

        good_reg = copy.deepcopy(reg)
        for e in good_reg["entries"]:
            e["license_file"], e["license_sha256"] = put(f"lic/{e['id']}", b"L" + e["id"].encode())
            e["asset_file"], e["asset_sha256"] = put(f"asset/{e['id']}", b"A" + e["id"].encode())
            e["status"], e["required"] = "cleared", True
        assert check_register(good_reg, root, strict_files=True) == []
        snips = []
        for i in range(8):
            s = dict(id=f"s{i}", split="dev" if i < 6 else "heldout", crop_bbox=[0, 0, 9, 9],
                     rights_evidence="doc", event_count=70)
            for f, k in (("source", "source"), ("labels", "labels"), ("chord_snapshot", "chord_snapshot")):
                s[f"{f}_file"], s[f"{k}_sha256"] = put(f"data/{f}{i}", b"%s%d" % (f.encode(), i))
            snips.append(s)
        _, scorer_sha = put(SCORER_PATH, b"# scorer\n")
        good = dict(
            locked_at="2026-10-14T00:00:00Z", snippets=snips, thresholds_frozen=True, alignment_metric="m",
            timebox_days=5, candidate_engines=["audiveris"], heldout_sealed=True,
            correction_procedure_sha256="c" * 64,
            rejection_cases=[dict(id=f"r{t}{k}", type=f"t{t}", file_sha256=hashlib.sha256(b"%d%d" % (t, k)).hexdigest(),
                                  expected_reason="x") for t in range(16) for k in range(2)],
            roles={"labelers": ["a", "b"], "correctors": ["c", "d"], "raters": ["e", "f", "g"],
                   "developers": ["h"], "heldout_readers": ["i"]},
            scorer=dict(path=SCORER_PATH, sha256=scorer_sha, reviewer="r"))
        assert readiness(good_reg, good, root, strict_files=True) == []

        controls = {
            "role overlap": lambda l: l["roles"]["raters"].__setitem__(0, "a"),
            "role is a string": lambda l: l["roles"].__setitem__("labelers", "ab"),
            "banned NFD": lambda l: l["snippets"][0].__setitem__("source_file", unicodedata.normalize("NFD", "data/친구야")),
            "bytes mismatch": lambda l: l["snippets"][0].__setitem__("labels_sha256", "d" * 64),
            "dup source": lambda l: l["snippets"][7].update(source_file=l["snippets"][0]["source_file"], source_sha256=l["snippets"][0]["source_sha256"]),
            "scorer path": lambda l: l["scorer"].__setitem__("path", "../x.py"),
            "reviewer dev": lambda l: l["scorer"].__setitem__("reviewer", "h"),
            "no locked_at": lambda l: l.pop("locked_at"),
            "dup rejections": lambda l: l.__setitem__("rejection_cases", [l["rejection_cases"][0]] * 32),
            "unknown engine": lambda l: l.__setitem__("candidate_engines", ["homr"]),
            "env path": lambda l: l["snippets"][0].__setitem__("source_file", ".env"),
        }
        for name, brk in controls.items():
            bad = copy.deepcopy(good)
            brk(bad)
            assert readiness(good_reg, bad, root, strict_files=True), f"control failed to fire: {name}"
        bad_reg = copy.deepcopy(good_reg)
        next(e for e in bad_reg["entries"] if e["id"] == "noto_sans_cjk_kr")["required"] = False
        assert readiness(bad_reg, good, root, strict_files=True)
        (root / "asset/audiveris").write_bytes(b"tampered")
        assert readiness(good_reg, good, root, strict_files=True)
    print(f"readiness selfcheck OK (1 positive on real temp bytes, {len(controls) + 2} negative controls fired)")


def main() -> int:
    if "--selfcheck" in sys.argv:
        _selfcheck()
        return 0
    reg = json.loads((HERE / "rights_register.json").read_text())
    lp = HERE / "lock_a.json"
    problems = readiness(reg, json.loads(lp.read_text()) if lp.exists() else None, strict_files=True)
    if problems:
        print("NOT READY (machine checks only; human rights/provenance review is separate)")
        print("\n".join(f"- {p}" for p in problems))
        return 1
    print("READY: machine checks pass; rights/independence still need independent human review. No experiment has run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
