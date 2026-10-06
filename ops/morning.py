"""MR-01, THE MORNING SCAN — irv-flow's own, before any contract fires (docs/contracts/MR-01-morning-scan.md).

    python ops/morning.py build [--date D] [--now ISO] [--dry]   reproduce the last close, re-check what changed,
                                                                  name the constraint, write out/morning/<D>.md + .json
    python ops/morning.py check [--date D]                        exit 0 only for D's complete, non-STOPPED sheet
    python ops/morning.py answer --leverage .. --inversion .. --attention .. --move .. --why ..
    python ops/morning.py explain <D-id|field> "<evidence>" --revised <belief|debt|commit|close|ruling> <ref>
    python ops/morning.py commit "<action>"        python ops/morning.py done <A-id> "<evidence>"

THE FIRST LAW (operator, 2026-10-06): reality is the final authority. The model is everything written before the
observation (yesterday's close, the preregs' priors, the spent baseline, the beliefs); the observation is what the
chain delivered to the hunter. An observation is written once and pinned; `explain` takes no value, so a
disagreement closes only by a revision of the model (a belief or debt line, a commit, a correcting close, a ruling),
never by editing what was seen, and never by touching a frozen prereg.

Journals (append-only, pin-last, journal/MANIFEST): journal/morning/close/<D>.jsonl written whole once per morning;
journal/morning/{disagreements,commitments,answers}/<D>.jsonl appended during D, sealed by the next build.
The constraint is the first rule of TABLE that fires on today's block alone. The scan reads counts, states and the
fact of a recorded look; it reads no outcome (no net, no exit branch, no look's figures), so it can name a
constraint and never a verdict. ZERO CAPITAL: it reads marks, nothing more.
"""
import argparse
import glob
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import common as C            # noqa: E402

CT = ZoneInfo("America/Chicago")
TABLE = ("STOP", "VOID", "LOOK", "BROKEN", "BLIND", "STALE", "RULING", "DISAGREE", "SAMPLE", "NONE")   # frozen at GO, 2026-10-06
CONTRACTS = (("IF-01", "looks.json", "FROZEN_SHA", "IF-01-PREREGISTRATION.md"),
             ("IF-02", "looks-IF-02.json", "IF-02-FROZEN_SHA", "IF-02-PREREGISTRATION.md"))
MODES = ("live", "forward")                 # the readout's rows, live first (foresight.rows() keeps the first per mint)
LEDGERS = ("disagreements", "commitments", "answers")
REVISIONS = ("belief", "debt", "commit", "close", "ruling")
ANSWERS = ("leverage", "inversion", "attention", "move", "why")
COUNTS = ("rows", "base", "flow", "flow_honest", "run_honest")
HB_AGE_S, EVENT_GAP_S, STREAMS_MIN = 120, 600, 2      # V4 as MR-01 reads it: heartbeat, no event for 10 min, both streams
V2_MAX = 0.10                                         # IF-01 §7 V2
IF02_VOID_DAYS = 60                                   # IF-02 §7 V1
IF01_V1_MIN = 30                                      # IF-01 §7 V1
FORWARD_N = 300                                       # IF-L01: a challenger is SAMPLE until n 300 forward
SPENT_P = 0.01                                        # a rate the program plans on is contradicted below this two-sided p
MIMICRY = os.path.normpath(os.path.join(C.ROOT, "..", "mimicry"))
CODE = ("src/*.py", "lib/*.py", "ops/*.py")
PROBES = (   # (name, argv after python, inputs whose sha proves no change); hunter liveness is not here: it is never skipped
    ("zero_capital", ("-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_zero_capital_and_wall.py"),
     CODE + ("tests/test_zero_capital_and_wall.py",)),
    ("known_answer_0828", ("-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_known_answer_0828.py"),
     CODE + ("tests/test_known_answer_0828.py", "prereg/KNOWN_ANSWER_0828.json", os.path.join(MIMICRY, "journal", "mi11", "mi-20260828*.jsonl"),
             os.path.join(MIMICRY, "snapshots", "mi-20260828T*", "*.gz"), os.path.join(MIMICRY, "snapshots", "mi-20260828T*", "meta.json"))),
    ("foresight_pen", ("-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_foresight.py::test_the_journal_on_disk_was_written_forward"),
     CODE + ("tests/test_foresight.py", "journal/foresight/*.jsonl")),
    ("learn_verify", ("ops/learn.py", "verify"), CODE + ("journal/live/*.jsonl", "journal/train/*.jsonl")),
)
NOT_COMPARED = (
    "IF-01 §8 and IF-02 §8 expected outcomes of the first 300: outcomes, read only at a look (rule 3)",
    "IF-02 §8 honest RUN per day (40 / 85 / 150): twinned to an open forecast; the calibration ledger reads it at close",
    "beliefs with an open test (e.g. B3, FLOW at most 2 a day): the calibration ledger reads them at their window's close",
)


class Refused(Exception):
    """A command the First Law or the contract refuses. Nothing has been written when it is raised."""


# ------------------------------------------------------------------ files -------------------------------------------
def _p(root, *parts):
    return os.path.join(root, *parts)


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha_obj(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def _jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _text(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return None


def manifest(root):
    """[(sha, relpath)] in pin order."""
    text = _text(_p(root, "journal", "MANIFEST")) or ""
    return [tuple(line.split("  ", 1)) for line in text.splitlines() if line]


def pin(root, rel):
    with open(_p(root, "journal", "MANIFEST"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(f"{sha_file(_p(root, 'journal', rel))}  {rel}\n")


def append(root, ledger, day, row):
    """journal/morning/<ledger>/<day>.jsonl, one line, fsynced. A sealed (pinned) day is never appended to."""
    rel = f"morning/{ledger}/{day}.jsonl"
    if rel in {r for _s, r in manifest(root)}:
        raise Refused(f"{rel} is sealed; a new line goes to today's file")
    path = _p(root, "journal", rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def ledger(root, name):
    return [r for f in sorted(glob.glob(_p(root, "journal", "morning", name, "*.jsonl"))) for r in _jsonl(f)]


def seal(root, day):
    """Pin every morning ledger day-file older than `day`, once."""
    pinned = {r for _s, r in manifest(root)}
    rels = [f"morning/{n}/{os.path.basename(f)}" for n in LEDGERS for f in sorted(glob.glob(_p(root, "journal", "morning", n, "*.jsonl")))]
    sealed = [r for r in rels if r.rsplit("/", 1)[1][:-6] < day and r not in pinned]
    for r in sealed:
        pin(root, r)
    return sealed


def inputs_sha(root, patterns):
    """sha256 over (path, sha256) of every file the patterns name, sorted: equal means nothing a check reads has moved."""
    files = sorted({os.path.normpath(f) for p in patterns for f in glob.glob(p if os.path.isabs(p) else _p(root, p))})
    return sha_obj([[os.path.relpath(f, root).replace("\\", "/"), sha_file(f)] for f in files])


# ------------------------------------------------------------------ observation -------------------------------------
def count_day(path, t0, seen):
    """One day-file: rows, base, FLOW signals, honest-filled FLOW (the readout's IF-01 n, no dedup) and honest-filled RUN
    forward of IF-02's freeze, one per mint as foresight.rows() keeps it. Honest-filled = an honest entry exists."""
    c = dict.fromkeys(COUNTS, 0)
    for r in _jsonl(path):
        first = r["mint"] not in seen
        seen.add(r["mint"])
        c["rows"] += 1
        if not r.get("standard_path"):
            continue
        filled = r.get("entry_honest") is not None
        c["base"] += 1
        if r.get("flow"):
            c["flow"] += 1
            c["flow_honest"] += filled
        if first and filled and t0 is not None and r["c0"] > t0 and r["flags"]["run"]:
            c["run_honest"] += 1
    return c


def _mints(path):
    return {r["mint"] for r in _jsonl(path)}


def _day(rel):
    return rel.rsplit("/", 1)[1][:-6]


def files(root, D, last, counter=count_day):
    """Every live / forward day-file with its counts. A day before D whose MANIFEST pin verifies and whose sha equals
    the last close's is proof of no change: its counts are carried and `counter` is not called. Everything else is counted."""
    pins = dict((r, s) for s, r in manifest(root))
    t0 = _frozen_at(root)
    t0 = t0.timestamp() if t0 else None
    old = {k[4:]: v for k, v in (last or {}).get("hold", {}).items() if k.startswith("day:")}
    out, seen = {}, set()
    for mode in MODES:
        for path in sorted(glob.glob(_p(root, "journal", mode, "*.jsonl"))):
            rel = f"{mode}/{os.path.basename(path)}"
            sha = sha_file(path)
            sealed = _day(rel) < D
            pinned = rel in pins
            ok = pinned and pins[rel] == sha
            if sealed and ok and rel in old and old[rel]["sha"] == sha:
                c, how = {k: old[rel][k] for k in COUNTS}, "carried"
                seen |= _mints(path)
            else:
                c, how = counter(path, t0, seen), "counted"
            out[rel] = {**c, "sha": sha, "sealed": sealed, "pinned": pinned, "pin_ok": ok if pinned else None, "how": how}
    return out


def _frozen_at(root):
    t = _text(_p(root, "prereg", "IF-02-FROZEN_AT"))
    return datetime.fromisoformat(t.strip()) if t else None


def looks(root):
    out = {}
    for name, fn, _pin, _doc in CONTRACTS:
        rec = C.read_json(_p(root, "out", fn))
        out[name] = None if rec is None else {k: {"n": v["n"], "at": v["at"], "sha": sha_obj(v)} for k, v in sorted(rec.items())}
    return out


def v2(root):
    """IF-01 §7 V2: share of co-observed signals (a mint in both the live and the forward-capture journal) whose
    entry-observable record disagrees (FLOW, the run flag, an honest fill). None while nothing is co-observed."""
    live = {r["mint"]: r for f in sorted(glob.glob(_p(root, "journal", "live", "*.jsonl"))) for r in _jsonl(f)}
    fwd = {r["mint"]: r for f in sorted(glob.glob(_p(root, "journal", "forward", "*.jsonl"))) for r in _jsonl(f)}
    both = sorted(set(live) & set(fwd))
    if not both:
        return None
    sig = lambda r: (bool(r.get("flow")), bool(r.get("flags", {}).get("run")), r.get("entry_honest") is not None)  # noqa: E731
    return round(sum(sig(live[m]) != sig(fwd[m]) for m in both) / len(both), 6)


def heartbeat(root, now):
    hb = C.read_json(_p(root, "monitor", "hunt-heartbeat.json"))
    if hb is None:
        return None
    t = now.timestamp()
    wall = datetime.fromisoformat(hb["wall"]).timestamp() if hb.get("wall") else None
    return {"age_s": None if wall is None else round(t - wall, 1), "gap_s": round(t - (hb.get("last_event") or 0), 1),
            "connected": hb.get("connected"), "pid": hb.get("pid")}


def loop_status(root):
    s = C.read_json(_p(root, "monitor", "loop-status.json"))
    return None if s is None else {"day": s["stamp"][:10], "failed": s.get("failed", []), "steps": sorted(s.get("steps", {}))}


def digest_day(root):
    p = _p(root, "docs", "digest.html")
    return datetime.fromtimestamp(os.path.getmtime(p), timezone.utc).astimezone(CT).strftime("%Y-%m-%d") if os.path.exists(p) else None


def rulings(root, lk):
    """Open boxes in docs/loop/rulings-owed.md (constraint_scan.rulings_owed()); one whose 'before look N' has fired is PAST ITS DEADLINE."""
    text = _text(_p(root, "docs", "loop", "rulings-owed.md"))
    if text is None:
        return None
    out = []
    for line in text.splitlines():
        if not line.strip().startswith("- [ ]"):
            continue
        what, past = line.strip()[6:], None
        m = re.search(r"before (?:either |any )?look (\d)", what, re.I)
        if m:
            fired = [(c, t[m.group(1)]["at"]) for c, t in sorted(lk.items()) if t and m.group(1) in t]
            past = f"{fired[0][0]} look {m.group(1)} taken {fired[0][1]}" if fired else None
        out.append({"what": what, "past": past})
    return out


def learn(root):
    """From out/learn.txt: IF-03 drafts owed, and each challenger's forward n. None if the file is not written."""
    text = _text(_p(root, "out", "learn.txt"))
    if text is None:
        return None, None
    owed = [line.strip()[len("RULING OWED:"):].strip() for line in text.splitlines() if line.strip().startswith("RULING OWED:")]
    born, ch = None, []
    for line in text.splitlines():
        m = re.match(r"^  (\d{4}-\d\d-\d\d)  ", line)
        if m:
            born = m.group(1)
        m = re.match(r"^    FORWARD\s+n (\d+)", line)
        if m and born:
            ch.append({"born": born, "forward_n": int(m.group(1))})
    return owed, ch


def patch_applied(root):
    """docs/loop/hunt-excursion.patch is applied when every line it adds is in ops/hunt.py."""
    patch, hunt = _text(_p(root, "docs", "loop", "hunt-excursion.patch")), _text(_p(root, "ops", "hunt.py"))
    if patch is None or hunt is None:
        return None
    added = [l[1:].strip() for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++") and l[1:].strip()]
    return all(a in hunt for a in added)


def scan_reading(root):
    """ops/constraint_scan.py's stage, by count: shown as a reading, never adopted."""
    text = _text(_p(root, "out", "constraint.txt")) or ""
    head = next((l for l in text.splitlines() if l.startswith("CONSTRAINT SCAN")), None)
    line = next((l for l in text.splitlines() if l.startswith("THE CONSTRAINT:")), None)
    return None if line is None else f"{line[len('THE CONSTRAINT: '):]}  ({head.split()[2] if head else 'unstamped'})"


def run_probe(root, argv):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, *argv], cwd=root, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").returncode


def probes(root, last, runner=None):
    """Each gate re-runs only if the sha of its inputs moved since the last close; an equal sha carries its rc."""
    old = (last or {}).get("move", {}).get("probes", {})
    out = {}
    for name, argv, inputs in PROBES:
        sha = inputs_sha(root, inputs)
        if old.get(name, {}).get("sha") == sha:
            out[name] = {"sha": sha, "rc": old[name]["rc"], "skipped": True}
        else:
            out[name] = {"sha": sha, "rc": (runner or (lambda a: run_probe(root, a)))(argv), "skipped": False}
    return out


def observe(root, D, now, last, runner=None, counter=count_day):
    """Today's block: every number the table and the close read, each from the file named beside it on the sheet.
    The gates run first; the instant observed at (`now`, the clock when None) is taken after them, before liveness is read."""
    pr = probes(root, last, runner)
    now = now or datetime.now(timezone.utc).replace(microsecond=0)
    fl = files(root, D, last, counter)
    lk = looks(root)
    owed, ch = learn(root)
    prereg = {}
    for name, _fn, pin_file, doc in CONTRACTS:
        p, d = _text(_p(root, "prereg", pin_file)), _p(root, "prereg", doc)
        prereg[name] = {"pin": p.strip() if p else None, "sha": sha_file(d) if os.path.exists(d) else None}
    man = manifest(root)
    bad = sorted(r for s, r in man if not os.path.exists(_p(root, "journal", r)) or sha_file(_p(root, "journal", r)) != s)
    t0 = _frozen_at(root)
    full = sorted({_day(r) for r in fl if r.startswith("live/") and fl[r]["sealed"]})[1:]       # the first day is partial
    run_full = [d for d in full if t0 and d > t0.strftime("%Y-%m-%d")]
    per = lambda key, days: round(sum(v[key] for r, v in fl.items() if _day(r) in days) / len(days), 3) if days else None  # noqa: E731
    return {
        "date": D, "now": now.isoformat(timespec="seconds"),
        "prereg": prereg, "if02_frozen_at": t0.isoformat() if t0 else None,
        "manifest": {"lines": len(man), "bad": bad},
        "files": fl,
        "n": {"IF-01": sum(v["flow_honest"] for v in fl.values()), "IF-02": sum(v["run_honest"] for v in fl.values())},
        "flow_signals": sum(v["flow"] for v in fl.values()),
        "rates": {"IF-01": {"per_day": per("flow_honest", full), "days": len(full)},
                  "IF-02": {"per_day": per("run_honest", run_full), "days": len(run_full)},
                  "flow_signals": {"k": sum(fl[f"live/{d}.jsonl"]["flow"] for d in full), "days": len(full)}},
        "looks": lk, "v2": v2(root),
        "probes": pr,
        "heartbeat": heartbeat(root, now), "loop": loop_status(root), "digest_day": digest_day(root),
        "rulings": rulings(root, lk), "if03_owed": owed, "challengers": ch,
        "patch_applied": patch_applied(root), "reading": scan_reading(root),
    }


# ------------------------------------------------------------------ the close: what must hold ------------------------
def holds(root, block, cut):
    """The must-hold numbers as of `cut` (a UTC day): nothing in them can legitimately move overnight."""
    fl = {r: v for r, v in block["files"].items() if _day(r) < cut}
    man = manifest(root)
    out = {f"day:{r}": {**{k: v[k] for k in COUNTS}, "sha": v["sha"]} for r, v in fl.items()}
    out["flow_honest_before_cut"] = sum(v["flow_honest"] for v in fl.values())
    out["run_honest_before_cut"] = sum(v["run_honest"] for v in fl.values())
    out["lineage"] = {r: s for s, r in man if r.split("/")[0] in ("learn", "train") and _day(r) < cut}
    for name, p in block["prereg"].items():
        out[f"prereg:{name}"] = p["pin"]
    out["prereg:IF-02-FROZEN_AT"] = block["if02_frozen_at"]
    for name, t in block["looks"].items():
        for k, v in (t or {}).items():
            out[f"look:{name}:{k}"] = v
    ka = _p(root, "prereg", "KNOWN_ANSWER_0828.json")
    out["known_answer_0828"] = sha_file(ka) if os.path.exists(ka) else None
    return out


def manifest_prefix(root, lines):
    man = manifest(root)
    return {"lines": lines, "sha": sha_obj(man[:lines]) if len(man) >= lines else None}


SRC = {"flow_honest_before_cut": "journal/live/ day-files before the cut", "run_honest_before_cut": "journal/live/ day-files before the cut",
       "lineage": "journal/MANIFEST learn/ + train/ pins", "known_answer_0828": "prereg/KNOWN_ANSWER_0828.json",
       "manifest_prefix": "journal/MANIFEST", "prereg:IF-01": "prereg/FROZEN_SHA", "prereg:IF-02": "prereg/IF-02-FROZEN_SHA",
       "prereg:IF-02-FROZEN_AT": "prereg/IF-02-FROZEN_AT"}


def _src(field):
    if field.startswith("day:"):
        return f"journal/{field[4:]}"
    if field.startswith("look:"):
        return "out/looks.json" if field.split(":")[1] == "IF-01" else "out/looks-IF-02.json"
    return SRC[field]


def closes(root):
    return {os.path.basename(f)[:-6]: f for f in sorted(glob.glob(_p(root, "journal", "morning", "close", "*.jsonl")))}


def read_close(path):
    rows = _jsonl(path)
    head = next(r for r in rows if "close" in r)
    return {"day": head["close"], "constraint": head.get("constraint"), "constraint_sha": head.get("constraint_sha"),
            "hold": {r["field"]: r["value"] for r in rows if r.get("kind") == "must-hold"},
            "move": {r["field"]: r["value"] for r in rows if r.get("kind") == "may-move"}}


def _fmt(v):
    return json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else "null" if v is None else str(v)


def reproduce(root, block, last):
    """[(field, old, new, src)] for every must-hold number of the last close that does not hold today."""
    now = holds(root, block, last["day"])
    now["manifest_prefix"] = manifest_prefix(root, last["hold"].get("manifest_prefix", {}).get("lines", 0))
    out = []
    for field, old in sorted(last["hold"].items()):
        new = now.get(field)
        if field.startswith("day:") and isinstance(old, dict) and isinstance(new, dict):
            out += [(f"{field[4:]}.{k}", old[k], new[k], _src(field)) for k in (*COUNTS, "sha") if old.get(k) != new.get(k)]
        elif old != new:
            out.append((field, old, new, _src(field)))
    return out


# ------------------------------------------------------------------ disagreements ------------------------------------
def disagreements(root):
    """{id: row} with `closed_by` set when an explain line carries a revision. Observed values come only from the opening line."""
    rows = {}
    for r in ledger(root, "disagreements"):
        if "explains" in r:
            if r["explains"] in rows and set(r) <= {"explains", "evidence", "revised", "ref", "at"}:
                rows[r["explains"]]["closed_by"] = r
        elif r.get("id") and r["id"] not in rows:
            rows[r["id"]] = dict(r, closed_by=None)
    return rows


def poisson_p(k, lam):
    """Two-sided p of a count k under Poisson(lam)."""
    pmf = lambda i: math.exp(-lam + i * math.log(lam) - math.lgamma(i + 1))  # noqa: E731
    lo = sum(pmf(i) for i in range(k + 1))
    return min(1.0, 2 * min(lo, 1 - lo + pmf(k)))


def contradictions(block):
    """Observations against a rate the program plans on. Only counts; only models with no open twin (gate, 2026-10-06)."""
    r = block["rates"]["flow_signals"]
    if not r["days"]:
        return []
    lam = C.FLOW_RATE_SPENT * r["days"]
    p = poisson_p(r["k"], lam)
    if p >= SPENT_P:
        return []
    return [{"field": "flow_signals_per_day", "observed": f"{r['k']} FLOW signals over {r['days']} full days",
             "observed_src": "journal/live/ sealed day-files", "model": C.FLOW_RATE_SPENT,
             "model_src": "src/common.py FLOW_RATE_SPENT (docs/findings/F01-spent-baseline.md)", "p": round(p, 6)}]


# ------------------------------------------------------------------ the constraint table -----------------------------
def _next_look(taken):
    return next((lk for lk in C.LOOKS if str(lk[0]) not in (taken or {})), None)


def _day_before(D):
    return (date.fromisoformat(D) - timedelta(days=1)).isoformat()


def rules(b):
    """[(id, [(fires True|False|None, text)])] in TABLE order. A pure function of today's block: no close, no sheet, no
    clock. None is unreadable and fires nothing. No part reads an outcome: counts, shas, exit codes, dates and the
    fact (n, instant) of a recorded look."""
    D, pr, lk, n = b["date"], b["probes"], b["looks"], b["n"]
    rc = lambda k: None if pr.get(k) is None else pr[k]["rc"] != 0  # noqa: E731
    stop = [(rc("zero_capital"), "S2: tests/test_zero_capital_and_wall.py red: a key, wallet or order path")]
    stop += [(None if p["pin"] is None or p["sha"] is None else p["pin"] != p["sha"], f"S1: {c} prereg sha no longer matches its pin")
             for c, p in sorted(b["prereg"].items())]
    t0 = b["if02_frozen_at"]
    void = [(None if b["v2"] is None else b["v2"] > V2_MAX, f"V2: live vs forward-capture disagree on {b['v2']} of co-observed signals"
             if b["v2"] is not None else "V2: no co-observed signal (forward-capture journal empty)")]
    void.append((None if t0 is None else
                 D > (datetime.fromisoformat(t0) + timedelta(days=IF02_VOID_DAYS)).strftime("%Y-%m-%d") and "4" not in (lk["IF-02"] or {}),
                 f"IF-02 V1: look 4 not reached by freeze + {IF02_VOID_DAYS} days"))
    void.append(("4" in (lk["IF-01"] or {}) and lk["IF-01"]["4"]["n"] < IF01_V1_MIN,
                 f"IF-01 V1: fewer than {IF01_V1_MIN} FLOW signals at look 4"))
    look = []
    for c, _fn, _p_, _d in CONTRACTS:
        nxt = _next_look(lk[c])
        look.append((nxt is not None and n[c] >= nxt[1], f"{c} look {nxt[0]} due: honest n {n[c]} at or past {nxt[1]}, not yet recorded"
                     if nxt else f"{c}: all four looks taken"))
        recent = [(k, v) for k, v in sorted((lk[c] or {}).items()) if v["at"][:10] in (_day_before(D), D)]
        look.append((bool(recent), "; ".join(f"{c} look {k} recorded {v['at']} at n {v['n']}: the readout speaks (out/readout.txt)"
                                              for k, v in recent) or f"{c}: no look recorded on {_day_before(D)} or {D}"))
    broken = [(rc("known_answer_0828"), "V3: the 08-28 known-answer gate red"),
              (bool(b["manifest"]["bad"]), "a pinned file fails its MANIFEST sha: " + ", ".join(b["manifest"]["bad"])),
              (rc("learn_verify"), "ops/learn.py verify fails"),
              (rc("foresight_pen"), "a foresight pen entry fails its check"),
              (bool(b.get("must_hold_failed")), "a must-hold number failed to reproduce: " + ", ".join(b.get("must_hold_failed") or []))]
    hb, lp = b["heartbeat"], b["loop"]
    blind = [(True, "no heartbeat file") if hb is None else
             (hb["age_s"] is None or hb["age_s"] > HB_AGE_S or hb["gap_s"] > EVENT_GAP_S or (hb["connected"] or 0) < STREAMS_MIN,
              f"hunter: heartbeat {hb['age_s']} s, last event {hb['gap_s']} s, streams up {hb['connected']}"),
             (True, "today's LOOP: monitor/loop-status.json missing") if lp is None else
             (lp["day"] != D or bool(lp["failed"]), f"today's LOOP: ran {lp['day']}, failed {', '.join(lp['failed']) or 'none'}")]
    stale = [(b["digest_day"] != D, f"docs/digest.html written {b['digest_day'] or 'never'} (Central)"),
             (None, "a forecast owed for a window that opened unwritten: not recorded")]
    rl, owed = b["rulings"], b["if03_owed"]
    past, rest = [r for r in rl or [] if r["past"]], [r for r in rl or [] if not r["past"]]
    ruling = [(None if rl is None else bool(past), "PAST ITS DEADLINE: " + "; ".join(f"{r['what'][:70]} ({r['past']})" for r in past)),
              (None if owed is None else bool(owed), "IF-03 DRAFT OWED: " + "; ".join(owed or [])),
              (None if rl is None else bool(rest), f"{len(rest)} owed, in file order: " + "; ".join(r["what"][:70] for r in rest))]
    dis = b.get("disagreements_open")
    disagree = [(None if dis is None else bool(dis), f"{len(dis or [])} open: " + "; ".join(dis or []))]
    sample = []
    for c, _fn, _p_, _d in CONTRACTS:
        nxt, rate = _next_look(lk[c]), b["rates"][c]["per_day"]
        days = f"{(nxt[1] - n[c]) / rate:.1f} days at {rate}/day over {b['rates'][c]['days']} full days" if nxt and rate else "no full-day rate yet"
        sample.append((nxt is not None and n[c] < nxt[1], f"{c}: honest n {n[c]} of {nxt[1]} for look {nxt[0]}, {days}" if nxt else f"{c}: all looks taken"))
    ch = b["challengers"]
    sample.append((None if ch is None else any(x["forward_n"] < FORWARD_N for x in ch),
                   "IF-L01: " + ("; ".join(f"challenger {x['born']} forward n {x['forward_n']} of {FORWARD_N}" for x in ch) if ch else "no challenger")))
    return [("STOP", stop), ("VOID", void), ("LOOK", look), ("BROKEN", broken), ("BLIND", blind), ("STALE", stale),
            ("RULING", ruling), ("DISAGREE", disagree), ("SAMPLE", sample), ("NONE", [(True, "nothing above fires")])]


def constrain(block):
    """Today's constraint: the first rule that fires. Returns {id, why, also, unreadable, sha}."""
    table = rules(block)
    fired = [(i, [t for f, t in parts if f is True]) for i, parts in table if any(f is True for f, _t in parts)]
    first, why = fired[0]
    return {"id": first, "why": why, "also": [i for i, _w in fired[1:] if i != "NONE"],
            "unreadable": [f"{i}: {t}" for i, parts in table for f, t in parts if f is None],
            "sha": sha_obj([[i, [[f, t] for f, t in parts]] for i, parts in table if i == first])}


# ------------------------------------------------------------------ operator actions ---------------------------------
def commitments(root):
    rows = ledger(root, "commitments")
    done = {r["done"] for r in rows if "done" in r}
    return [r for r in rows if "id" in r and r["id"] not in done]


def actions(root, block):
    out = [f"[ ] ruling owed: {r['what']}" + (f" — PAST ITS DEADLINE: {r['past']}" if r["past"] else "") for r in block["rulings"] or []]
    out += [f"[ ] IF-03 DRAFT OWED: {o}" for o in block["if03_owed"] or []]
    if block["patch_applied"] is False:
        out.append("[ ] docs/loop/hunt-excursion.patch is not applied (the operator's word)")
    out += [f"[ ] {c['id']} {c['what']} (committed {c['at']})" for c in commitments(root)]
    return out


# ------------------------------------------------------------------ the sheet ----------------------------------------
def render(s):
    b, k = s["block"], s["constraint"]
    hb = b["heartbeat"]
    head = {"STOPPED": "STOPPED — a must-hold number did not reproduce; `check` exits 1 until each row below is explained with a revision",
            "first": "baseline: first close, nothing to reproduce — NOT A PASS",
            "reproduced": "baseline reproduced"}[s["status"]]
    L = [f"MORNING SCAN  irv-flow  {s['date']}  observed {b['now']}  (MR-01; reads no outcome; names a constraint, never a verdict)",
         f"STATUS: {head}", "", "1 BASELINE — reproduce the last close"]
    bl = s["baseline"]
    if bl["against"] is None:
        L.append("  first close: nothing to reproduce")
    else:
        L.append(f"  against journal/morning/close/{bl['against']}.jsonl ({bl['held']} must-hold numbers)")
        L += [f"  no close for {d}: the scan did not run (NO BACKFILL)" for d in bl["missing"]]
        L += [f"  STOP {x['field']}: {_fmt(x['old'])} → {_fmt(x['new'])} ({x['src']})  {x['id']}" for x in bl["deltas"]]
        if not bl["deltas"]:
            L.append("  every must-hold number holds")
    L += ["", "2 DRIFT — re-check only what could have changed"]
    for rel, v in sorted(b["files"].items()):
        if v["how"] == "carried":
            L.append(f"  {rel:28s} zero drift, re-check skipped, sha {v['sha']}")
        else:
            why = ("open day, may move" if not v["sealed"] else "first count" if bl["against"] is None or rel not in bl["known"]
                   else "sha moved" if v["pin_ok"] is not False else "PIN FAILS")
            L.append(f"  {rel:28s} counted ({why}): rows {v['rows']} base {v['base']} FLOW {v['flow']} honest FLOW {v['flow_honest']}"
                     f" honest RUN {v['run_honest']}{'' if v['pinned'] or not v['sealed'] else '  (past day not sealed)'}")
    for name, p in sorted(b["probes"].items()):
        L.append(f"  {name:28s} " + (f"zero drift, re-check skipped, sha {p['sha']} (rc {p['rc']} carried)" if p["skipped"]
                                    else f"re-run, inputs sha {p['sha']}: rc {p['rc']}"))
    L.append("  hunter liveness              never skipped: " + ("no heartbeat file" if hb is None else
             f"heartbeat {hb['age_s']} s, last event {hb['gap_s']} s, streams up {hb['connected']}, pid {hb['pid']} (monitor/hunt-heartbeat.json)"))
    L += ["", "3 CONSTRAINT — from today's observations alone; first rule of the table that fires",
          f"  >> {k['id']}: " + " | ".join(k["why"])]
    if k["also"]:
        L.append(f"  also firing below it: {', '.join(k['also'])}")
    L += [f"  unreadable (fires nothing): {u}" for u in k["unreadable"]]
    y = s["yesterday"]
    L.append(f"  yesterday: {y['id']} ({'changed' if y['changed'] else 'same id, same firing inputs'})" if y else "  yesterday: not recorded")
    L.append(f"  reading, never adopted: constraint_scan.py {b['reading'] or 'not recorded'}")
    L += [f"  not compared: {x}" for x in NOT_COMPARED]
    L += ["", "4 OPERATOR ACTIONS — no DONE line"] + [f"  {a}" for a in s["actions"] or ["(none)"]]
    L += ["", "5 DISAGREEMENTS — model vs observation; closed only by a revision of the model"]
    L += [f"  {d['id']} {d['field']}: observed {_fmt(d['observed'])} ({d['observed_src']}) vs model {_fmt(d['model'])} ({d['model_src']}), "
          f"first seen {d['first_seen']} — " + (f"revised by {d['closed_by']['revised']} {d['closed_by']['ref']}" if d["closed_by"] else "OPEN")
          for d in s["disagreements"]] or ["  (none)"]
    a = s["answers"]
    owed = "owed: python ops/morning.py answer"
    L += ["", f"6 THE THREE QUESTIONS — against {k['id']}",
          f"  LEVERAGE   {a.get('leverage', owed)}", f"  INVERSION  {a.get('inversion', owed)}", f"  ATTENTION  {a.get('attention', owed)}",
          "", "7 OUTPUT", f"  Today's Highest Leverage Move: {a.get('move', owed)}", f"  Why: {a.get('why', owed)}", "", C.FOOTER]
    return "\n".join(L) + "\n"


def sheet_paths(root, D):
    d = _p(root, "out", "morning")
    return os.path.join(d, f"{D}.md"), os.path.join(d, f"{D}.json")


def write_sheet(root, s):
    md, js = sheet_paths(root, s["date"])
    os.makedirs(os.path.dirname(md), exist_ok=True)
    with open(md, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render(s))
    with open(js, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(s, sort_keys=True, indent=1) + "\n")


def load_sheet(root, D):
    return C.read_json(sheet_paths(root, D)[1])


def answers(root, D):
    out = {}
    for r in ledger(root, "answers"):
        if r.get("date") == D:
            out = {k: r[k] for k in ANSWERS}
    return out


def status(root, s):
    """first | STOPPED | reproduced, re-read from the ledger: a STOP lifts when every row it pinned carries a revision."""
    if s["baseline"]["against"] is None:
        return "first"
    rows = disagreements(root)
    ids = [x["id"] for x in s["baseline"]["deltas"]]
    return "STOPPED" if any(i not in rows or not rows[i]["closed_by"] for i in ids) else "reproduced"


# ------------------------------------------------------------------ commands -----------------------------------------
def build(root, D, now, dry=False, runner=None, counter=count_day):
    """Returns (sheet, exit code). Exit 1 when the day STOPS."""
    if not dry:
        seal(root, D)
    prior = {d: f for d, f in closes(root).items() if d < D}
    last = read_close(prior[max(prior)]) if prior else None
    block = observe(root, D, now, last, runner, counter)
    deltas = reproduce(root, block, last) if last else []
    rows = disagreements(root)
    n_rows = len(rows)
    opened = []

    def open_row(row):
        nonlocal n_rows
        same = [r for r in rows.values() if r["field"] == row["field"] and r["model"] == row["model"] and r["observed"] == row["observed"]]
        if same:
            return same[0]["id"]
        n_rows += 1
        row = dict(row, id=f"D-{n_rows:04d}", first_seen=D, at=block["now"])
        opened.append(row)
        rows[row["id"]] = dict(row, closed_by=None)
        return row["id"]

    stops = [{"field": f, "old": o, "new": n, "src": s, "id": open_row({"field": f, "observed": n, "observed_src": s, "model": o,
                                                                       "model_src": f"journal/morning/close/{last['day']}.jsonl", "stop": True})}
             for f, o, n, s in deltas]
    for c in contradictions(block):
        if not any(r["field"] == c["field"] and r["model"] == c["model"] and r["closed_by"] for r in rows.values()):
            open_row({k: c[k] for k in ("field", "observed", "observed_src", "model", "model_src")})
    block["must_hold_failed"] = [x["field"] for x in stops]
    block["disagreements_open"] = sorted(i for i, r in rows.items() if not r["closed_by"])
    k = constrain(block)
    missing = []
    if last:
        d = date.fromisoformat(last["day"]) + timedelta(days=1)
        while d.isoformat() < D:
            missing.append(d.isoformat())
            d += timedelta(days=1)
    s = {"date": D, "block": block, "constraint": k, "answers": answers(root, D), "actions": actions(root, block),
         "baseline": {"against": last["day"] if last else None, "missing": missing, "deltas": stops,
                      "held": len(last["hold"]) if last else 0, "known": sorted(f[4:] for f in (last or {"hold": {}})["hold"] if f.startswith("day:"))},
         "yesterday": {"id": last["constraint"], "changed": (last["constraint"], last["constraint_sha"]) != (k["id"], k["sha"])}
                      if last and last.get("constraint") else None,
         "disagreements": [r for _i, r in sorted(rows.items())]}
    s["status"] = "STOPPED" if any(not rows[x["id"]]["closed_by"] for x in stops) else "first" if last is None else "reproduced"
    if not dry:
        for row in opened:
            append(root, "disagreements", D, row)
        write_close(root, D, block, k, stops)
    write_sheet(root, s)
    return s, 1 if s["status"] == "STOPPED" else 0


def write_close(root, D, block, k, stops):
    """journal/morning/close/<D>.jsonl, whole, once, pinned. A second build the same day leaves the first close as written."""
    path = _p(root, "journal", "morning", "close", f"{D}.jsonl")
    if os.path.exists(path):
        return False
    hold = holds(root, block, D)
    hold["manifest_prefix"] = manifest_prefix(root, len(manifest(root)))
    move = {"probes": {n: {"sha": p["sha"], "rc": p["rc"]} for n, p in block["probes"].items()},
            "today": {r: {c: v[c] for c in COUNTS} for r, v in block["files"].items() if not v["sealed"]},
            "heartbeat": block["heartbeat"], "loop": block["loop"], "digest_day": block["digest_day"]}
    rows = [{"close": D, "now": block["now"], "constraint": k["id"], "constraint_sha": k["sha"]}]
    rows += [{"field": f, "kind": "must-hold", "value": v, "src": _src(f)} for f, v in sorted(hold.items())]
    rows += [{"field": f, "kind": "may-move", "value": v} for f, v in sorted(move.items())]
    rows += [{"corrects": x["id"], "field": x["field"], "old": x["old"], "new": x["new"]} for x in stops]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".part", "w", encoding="utf-8", newline="\n") as fh:
        fh.writelines(json.dumps(r, sort_keys=True) + "\n" for r in rows)
    os.replace(path + ".part", path)
    pin(root, f"morning/close/{D}.jsonl")
    return True


def check(root, D):
    s = load_sheet(root, D)
    if s is None:
        return 1, f"NO SHEET for {D}: run python ops/morning.py build"
    st = status(root, s)
    missing = [a for a in ANSWERS if not answers(root, D).get(a)]
    line = {"first": "FIRST CLOSE — nothing reproduced; not a pass", "STOPPED": "STOPPED — a must-hold delta is unexplained",
            "reproduced": "reproduced"}[st] + (f"; answers owed: {', '.join(missing)}" if missing else "; complete")
    return (0 if st == "reproduced" and not missing else 1), f"MORNING {D} {s['constraint']['id']}: {line}"


def answer(root, D, given, now):
    s = load_sheet(root, D)
    if s is None:
        raise Refused(f"no sheet for {D}: build first")
    empty = [a for a in ANSWERS if not (given.get(a) or "").strip()]
    if empty:
        raise Refused(f"an answer is owed for: {', '.join(empty)}")
    cid = s["constraint"]["id"]
    if not re.search(rf"\b{cid}\b", given["why"]):
        raise Refused(f"the Why must trace to today's constraint: it does not contain {cid}")
    append(root, "answers", D, {"date": D, "constraint": cid, "at": now, **{a: given[a].strip() for a in ANSWERS}})
    refresh(root, s)


def refresh(root, s):
    """Re-render a sheet after a ledger line: its answers, its disagreements and its status. The block and the constraint stay as observed."""
    s["answers"] = answers(root, s["date"])
    s["disagreements"] = [r for _i, r in sorted(disagreements(root).items())]
    s["status"] = status(root, s)
    write_sheet(root, s)


def _resolves(root, row, kind, ref):
    """Does `ref` name a revision of the model of `kind`, written on or after the row was first seen?"""
    since = row["first_seen"]
    if kind in ("belief", "debt"):
        evs = [e for f in glob.glob(_p(root, "journal", "foresight", "*.jsonl")) for e in _jsonl(f)]
        want = ("belief", "predict") if kind == "belief" else ("lesson",)
        return any(e.get("e") in want and e.get("id") == ref and e.get("at", "")[:10] >= since and (kind == "belief" or e.get("owes"))
                   for e in evs)
    if kind == "commit":
        r = subprocess.run(["git", "-C", root, "show", "-s", "--format=%cs", f"{ref}^{{commit}}"], capture_output=True, text=True)
        return r.returncode == 0 and r.stdout.strip() >= since
    if kind == "close":
        day = ref.rsplit("/", 1)[-1].removesuffix(".jsonl")
        return day >= since and any(r.get("corrects") == row["id"] for r in _jsonl(_p(root, "journal", "morning", "close", f"{day}.jsonl")))
    if kind == "ruling":
        slug = os.path.basename(ref).removesuffix(".md")
        return os.path.exists(_p(root, "docs", "decisions", f"{slug}.md")) and slug[:10] >= since
    return False


def explain(root, D, target, evidence, kind, ref, now):
    rows = disagreements(root)
    hit = [r for r in rows.values() if not r["closed_by"] and target in (r["id"], r["field"])]
    if not hit:
        raise Refused(f"no open disagreement {target}")
    if not evidence.strip():
        raise Refused("an explanation carries its evidence")
    if kind not in REVISIONS:
        raise Refused(f"a disagreement closes only by a revision of the model: {', '.join(REVISIONS)}")
    bad = [r["id"] for r in hit if not _resolves(root, r, kind, ref)]
    if bad:
        raise Refused(f"{kind} {ref} does not resolve to a revision written since {', '.join(bad)} was first seen")
    for r in hit:
        append(root, "disagreements", D, {"explains": r["id"], "evidence": evidence.strip(), "revised": kind, "ref": ref, "at": now})
    s = load_sheet(root, D)
    if s is not None:
        refresh(root, s)
    return [r["id"] for r in hit]


def commit(root, D, what, now):
    if not what.strip():
        raise Refused("a commitment says what it is")
    n = sum(1 for r in ledger(root, "commitments") if "id" in r) + 1
    row = {"id": f"A-{n:04d}", "what": what.strip(), "at": now}
    append(root, "commitments", D, row)
    return row["id"]


def done(root, D, aid, evidence, now):
    if not evidence.strip():
        raise Refused("a DONE carries its evidence")
    if aid not in {c["id"] for c in commitments(root)}:
        raise Refused(f"{aid} is not an open commitment")
    append(root, "commitments", D, {"done": aid, "evidence": evidence.strip(), "at": now})


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Refused(message)


def parser():
    day = _Parser(add_help=False)
    day.add_argument("--date", default=None, help="the UTC day (default today)")
    p = _Parser(prog="python ops/morning.py", description="MR-01, the morning scan")
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=_Parser)
    b = sub.add_parser("build", parents=[day])
    b.add_argument("--now", default=None, help="the instant observed at, ISO (default the clock); an input, printed on the sheet")
    b.add_argument("--dry", action="store_true", help="write the sheet only: no close, no ledger line, no seal")
    sub.add_parser("check", parents=[day])
    a = sub.add_parser("answer", parents=[day])
    for k in ANSWERS:
        a.add_argument(f"--{k}", required=True)
    e = sub.add_parser("explain", parents=[day])
    e.add_argument("target")
    e.add_argument("evidence")
    e.add_argument("--revised", nargs=2, metavar=("KIND", "REF"), required=True)
    c = sub.add_parser("commit", parents=[day])
    c.add_argument("what")
    d = sub.add_parser("done", parents=[day])
    d.add_argument("id")
    d.add_argument("evidence")
    return p


def main(argv, root=C.ROOT, runner=None, counter=count_day):
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        ns = parser().parse_args(argv)
        D = ns.date or C.today()
        if ns.cmd == "build":
            s, rc = build(root, D, datetime.fromisoformat(ns.now) if ns.now else None, ns.dry, runner, counter)
            print(render(s), end="")
            return rc
        if ns.cmd == "check":
            rc, line = check(root, D)
            print(line)
            return rc
        if ns.cmd == "answer":
            answer(root, D, {k: getattr(ns, k) for k in ANSWERS}, C.stamp())
        elif ns.cmd == "explain":
            print("closed: " + ", ".join(explain(root, D, ns.target, ns.evidence, *ns.revised, C.stamp())))
        elif ns.cmd == "commit":
            print(commit(root, D, ns.what, C.stamp()))
        elif ns.cmd == "done":
            done(root, D, ns.id, ns.evidence, C.stamp())
        return 0
    except Refused as why:
        print(f"REFUSED: {why}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
