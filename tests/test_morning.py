"""MR-01, the morning scan, on synthetic repo homes (declared synthetic) and one read-only check against the real journals."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "ops")]
import common as C            # noqa: E402
import morning as M           # noqa: E402

D1, D2 = "2026-10-07", "2026-10-08"
NOW1, NOW2 = f"{D1}T11:00:00+00:00", f"{D2}T11:00:00+00:00"
DAYS = ("2026-10-03", "2026-10-04", "2026-10-05", "2026-10-06")
FLOWS = (1, 3, 7, 5)                       # honest FLOW per day: 16 before D1's cut
ALL_LOOKS = {str(k): {"n": n, "at": "2026-09-01T00:00:00+00:00", "mean": 0.4242, "z_obs": 9.87, "verdict": "PASS"} for k, n, _z in C.LOOKS}


def ts(iso):
    return datetime.fromisoformat(iso).timestamp()


def rec(mint, day, flow=False, hour=14, filled=True, net=None):
    r = {"mint": mint, "c0": int(ts(f"{day}T{hour:02d}:00:00+00:00")), "t_entry_s": 30, "standard_path": True, "flow": flow,
         "flags": {"run": True}, "entry_honest": 1e-5 if filled else None, "closed_wall": f"{day}T{hour:02d}:01:00+00:00"}
    return {**r, "net_honest": net} if net is not None else r


def put(root, rel, obj):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(obj if isinstance(obj, str) else json.dumps(obj, sort_keys=True, indent=1))


def lines(root, rel, rows):
    put(root, rel, "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))


def home(tmp, D=D1, flows=FLOWS, net=None):
    """A repo home on which every rule reads and none but NONE fires."""
    root = str(tmp)
    for name, _fn, pin, doc in M.CONTRACTS:
        put(root, f"prereg/{doc}", f"# {name}\n")
        put(root, f"prereg/{pin}", M.sha_file(os.path.join(root, "prereg", doc)) + "\n")
    put(root, "prereg/IF-02-FROZEN_AT", "2026-10-03T13:34:31+00:00\n")
    put(root, "prereg/KNOWN_ANSWER_0828.json", {"flow_signals": 6, "flow_winners": 3})
    put(root, "journal/MANIFEST", "")
    for d, k in zip(DAYS, flows):
        lines(root, f"journal/live/{d}.jsonl", [rec(f"{d}-f{i}", d, flow=True, net=net) for i in range(k)] + [rec(f"{d}-b{i}", d) for i in range(5)])
        M.pin(root, f"live/{d}.jsonl")
    put(root, "out/looks.json", ALL_LOOKS)
    put(root, "out/looks-IF-02.json", ALL_LOOKS)
    put(root, "out/learn.txt", "IF-L01\n  2026-10-06  buyers < 9   haircut -6.98 pp\n    FORWARD   n 400\n")
    put(root, "docs/loop/rulings-owed.md", "# RULINGS OWED\n\n- [x] ruled and closed\n")
    put(root, "docs/digest.html", "<p>digest</p>")
    os.utime(os.path.join(root, "docs/digest.html"), (ts(f"{D}T12:00:00+00:00"),) * 2)
    beat(root, D)
    put(root, "monitor/loop-status.json", {"stamp": f"{D}T10:21:35+00:00", "steps": {"freshness.py": {"rc": 0}}, "failed": []})
    return root


def beat(root, D, connected=2):
    put(root, "monitor/hunt-heartbeat.json", {"wall": f"{D}T10:59:55+00:00", "last_event": ts(f"{D}T10:59:58+00:00"),
                                              "connected": connected, "pid": 4242})


def ok(_argv):
    return 0


def build(root, D=D1, now=NOW1, dry=True, **kw):
    kw.setdefault("runner", ok)
    return M.build(root, D, datetime.fromisoformat(now), dry, **kw)


def cli(root, *argv, runner=ok):
    return M.main(list(argv), root=root, runner=runner)


def sheet(root, D):
    with open(os.path.join(root, "out", "morning", f"{D}.md"), encoding="utf-8") as fh:
        return fh.read()


# ------------------------------------------------------------------ the table, one home per rule ---------------------
def gate_red(name):
    return lambda argv: int(any(name in a for a in argv))


def _stop(root):
    return {"runner": gate_red("test_zero_capital")}


def _void(root):
    put(root, "prereg/IF-02-FROZEN_AT", "2026-08-01T00:00:00+00:00\n")
    put(root, "out/looks-IF-02.json", {k: v for k, v in ALL_LOOKS.items() if k != "4"})


def _look(root):
    put(root, "out/looks-IF-02.json", {**ALL_LOOKS, "4": {**ALL_LOOKS["4"], "at": f"{D1}T10:20:05+00:00"}})


def _broken(root):
    return {"runner": gate_red("test_known_answer_0828")}


def _blind(root):
    beat(root, D1, connected=1)


def _stale(root):
    os.utime(os.path.join(root, "docs/digest.html"), (ts("2026-10-06T12:00:00+00:00"),) * 2)


def _ruling(root):
    put(root, "docs/loop/rulings-owed.md", "- [ ] Free the VPS disk\n")


def _disagree(root):
    put(root, "journal/MANIFEST", "")
    for d in DAYS:
        lines(root, f"journal/live/{d}.jsonl", [rec(f"{d}-f{i}", d, flow=True) for i in range(20)])
        M.pin(root, f"live/{d}.jsonl")


def _sample(root):
    os.remove(os.path.join(root, "out", "looks.json"))


def _none(root):
    pass


@pytest.mark.parametrize("rule,mutate", [("STOP", _stop), ("VOID", _void), ("LOOK", _look), ("BROKEN", _broken), ("BLIND", _blind),
                                         ("STALE", _stale), ("RULING", _ruling), ("DISAGREE", _disagree), ("SAMPLE", _sample),
                                         ("NONE", _none)])
def test_each_rule_of_the_table_yields_exactly_its_id(tmp_path, rule, mutate):
    root = home(tmp_path)
    kw = mutate(root) or {}
    s, _rc = build(root, **kw)
    assert s["constraint"]["id"] == rule
    assert s["constraint"]["also"] == (["SAMPLE"] if rule == "VOID" else []), s["constraint"]   # alone, but a void look 4 is also short of n


def test_a_look_due_day_names_the_look(tmp_path):
    root = home(tmp_path, flows=(1, 3, 7, 300))
    put(root, "out/looks.json", {})
    s, _rc = build(root)
    assert s["constraint"]["id"] == "LOOK" and "IF-01 look 1 due: honest n 311 at or past 300" in s["constraint"]["why"][0]


def test_poisoned_yesterday_yields_todays_constraint(tmp_path, monkeypatch):
    clean = home(tmp_path / "clean", D=D2)
    root = home(tmp_path / "poisoned", D=D2)
    with monkeypatch.context() as m:
        m.setattr(M, "constrain", lambda b: {"id": "STOP", "why": ["poison"], "also": [], "unreadable": [], "sha": "0" * 64})
        build(root, dry=False)
    put(root, f"out/morning/{D1}.json", {"constraint": {"id": "VOID"}})
    s, _rc = build(root, D2, NOW2)
    assert s["yesterday"] == {"id": "STOP", "changed": True}
    assert s["constraint"]["id"] == build(clean, D2, NOW2)[0]["constraint"]["id"] == "NONE"
    assert M.constrain.__code__.co_varnames[:M.constrain.__code__.co_argcount] == ("block",)


def test_null_renders_not_recorded_and_fires_nothing(tmp_path):
    root = home(tmp_path)
    os.remove(os.path.join(root, "out", "learn.txt"))
    os.remove(os.path.join(root, "docs", "loop", "rulings-owed.md"))
    s, _rc = build(root)
    un = s["constraint"]["unreadable"]
    assert s["constraint"]["id"] == "NONE"
    assert any(u.startswith("RULING: PAST ITS DEADLINE") for u in un) and any(u.startswith("SAMPLE: IF-L01") for u in un)
    assert "STALE: a forecast owed for a window that opened unwritten: not recorded" in un
    assert "unreadable (fires nothing): RULING" in sheet(root, D1)


# ------------------------------------------------------------------ rule 3 ------------------------------------------
def test_a_flow_mean_far_above_bar_at_n_16_fires_nothing_and_never_reaches_the_sheet(tmp_path):
    root = home(tmp_path, net=0.9)
    os.remove(os.path.join(root, "out", "looks.json"))
    s, _rc = build(root)
    text = sheet(root, D1).replace("NOT A PASS", "")
    assert s["constraint"]["id"] == "SAMPLE" and s["block"]["n"]["IF-01"] == 16
    for tok in ("mean", "z_obs", "0.9", "90", "0.4242", "9.87", "PASS", "verdict:", "CONTINUE", "FAIL"):
        assert tok not in text, tok
    body = open(os.path.join(ROOT, "ops", "morning.py"), encoding="utf-8").read().split('"""', 2)[2]
    for tok in ("net_", "exit_", "why_honest", "why_zero", "meanL", "z_obs", '["mean"]', '["verdict"]'):
        assert tok not in body, tok


# ------------------------------------------------------------------ baseline, the First Law --------------------------
def test_a_must_hold_delta_stops_the_day_until_a_revision_closes_it(tmp_path):
    root = home(tmp_path, D=D2)
    s1, rc1 = build(root, dry=False)
    assert rc1 == 0 and s1["status"] == "first" and cli(root, "check", "--date", D1) == 1          # the first close is not a pass
    late = rec("late-flow", "2026-10-03", flow=True, hour=6)                                       # before IF-02's freeze: no RUN delta
    lines(root, "journal/forward/2026-10-05.jsonl", [late])
    s2, rc2 = build(root, D2, NOW2, dry=False)
    assert rc2 == 1 and s2["status"] == "STOPPED" and s2["constraint"]["id"] == "BROKEN"
    assert "  STOP flow_honest_before_cut: 16 → 17 (journal/live/ day-files before the cut)  D-0001" in sheet(root, D2)
    rows = M.ledger(root, "disagreements")
    assert [r["id"] for r in rows] == ["D-0001"] and rows[0]["observed"] == 17 and rows[0]["model"] == 16
    assert f"morning/close/{D2}.jsonl" in {r for _s, r in M.manifest(root)}
    assert cli(root, "check", "--date", D2) == 1
    assert cli(root, "explain", "D-0001", "a forward day-file for 10-05 appeared after the close", "--date", D2) == 1     # no revision
    assert cli(root, "explain", "D-0001", "evidence", "--revised", "commit", "deadbeef", "--date", D2) == 1             # does not resolve
    assert cli(root, "explain", "D-0001", "a forward day-file for 10-05 appeared after the close",
               "--revised", "close", f"close/{D2}", "--date", D2) == 0
    assert cli(root, "check", "--date", D2) == 1                                                  # answers still owed
    assert cli(root, "answer", "--date", D2, "--leverage", "a", "--inversion", "b", "--attention", "c", "--move", "d",
               "--why", "BROKEN: the late file") == 0
    assert cli(root, "check", "--date", D2) == 0
    assert "revised by close close/2026-10-08" in sheet(root, D2)


def test_explain_cannot_change_the_observed_value(tmp_path):
    root = home(tmp_path, D=D2)
    build(root, dry=False)
    lines(root, "journal/forward/2026-10-05.jsonl", [rec("late-flow", "2026-10-03", flow=True, hour=6)])
    build(root, D2, NOW2, dry=False)
    path = os.path.join(root, "journal", "morning", "disagreements", f"{D2}.jsonl")
    before = open(path, "rb").read()
    assert cli(root, "explain", "D-0001", "it was 16", "--revised", "close", f"close/{D2}", "--observed", "16", "--date", D2) == 1
    assert open(path, "rb").read() == before
    with open(path, "a", encoding="utf-8") as fh:                                                 # a forged line is not an explanation
        fh.write(json.dumps({"explains": "D-0001", "observed": 16, "evidence": "x", "revised": "close", "ref": "x", "at": "x"}) + "\n")
    row = M.disagreements(root)["D-0001"]
    assert row["observed"] == 17 and row["closed_by"] is None


def test_a_missing_morning_is_not_backfilled_and_the_next_close_says_so(tmp_path):
    root = home(tmp_path, D="2026-10-09")
    build(root, dry=False)
    s, rc = build(root, "2026-10-09", "2026-10-09T11:00:00+00:00")
    assert rc == 0 and s["baseline"]["missing"] == [D2] and f"no close for {D2}: the scan did not run (NO BACKFILL)" in sheet(root, "2026-10-09")


# ------------------------------------------------------------------ drift --------------------------------------------
def test_a_verified_pin_carries_its_counts_and_one_byte_breaks_it(tmp_path):
    root = home(tmp_path, D=D2)
    build(root, dry=False)
    counted, ran = [], []

    def spy(path, t0, seen):
        counted.append(os.path.basename(path))
        return M.count_day(path, t0, seen)

    s, _rc = build(root, D2, NOW2, counter=spy, runner=lambda a: ran.append(a) or 0)
    assert counted == [] and ran == []
    text = sheet(root, D2)
    for d in DAYS:
        sha = M.sha_file(os.path.join(root, "journal", "live", f"{d}.jsonl"))
        assert f"live/{d}.jsonl" in text and f"zero drift, re-check skipped, sha {sha}" in text and len(sha) == 64
    assert "hunter liveness              never skipped: heartbeat" in text
    beat(root, D2, connected=1)
    assert build(root, D2, NOW2)[0]["block"]["heartbeat"]["connected"] == 1                       # liveness is read every time
    p = os.path.join(root, "journal", "live", "2026-10-04.jsonl")
    raw = bytearray(open(p, "rb").read())
    raw[10] ^= 1
    open(p, "wb").write(bytes(raw))
    s, rc = build(root, D2, NOW2, counter=spy)
    assert counted == ["2026-10-04.jsonl"] and s["constraint"]["id"] == "BROKEN" and rc == 1
    assert "live/2026-10-04.jsonl" in s["block"]["manifest"]["bad"]


# ------------------------------------------------------------------ refusals, actions ---------------------------------
def test_refusals_write_nothing(tmp_path):
    root = home(tmp_path)
    build(root)
    answers = os.path.join(root, "journal", "morning", "answers")
    assert cli(root, "answer", "--date", D1, "--leverage", "a", "--inversion", "b", "--attention", "c", "--move", "d", "--why", "because") == 1
    assert cli(root, "answer", "--date", D1, "--leverage", " ", "--inversion", "b", "--attention", "c", "--move", "d", "--why", "NONE") == 1
    assert not os.path.exists(answers)
    assert cli(root, "commit", "Read the 24 h meter", "--date", D1) == 0
    assert cli(root, "done", "A-0001", "  ", "--date", D1) == 1
    assert [c["id"] for c in M.commitments(root)] == ["A-0001"]
    assert "[ ] A-0001 Read the 24 h meter (committed " in build(root)[0]["actions"][0]
    assert cli(root, "done", "A-0001", "meter read: out/meter.txt", "--date", D1) == 0 and M.commitments(root) == []


def test_operator_actions_flag_a_ruling_past_its_deadline(tmp_path):
    root = home(tmp_path)
    put(root, "docs/loop/rulings-owed.md", "- [ ] Re-derive BAR before look 1\n- [ ] Free the VPS disk\n")
    put(root, "out/learn.txt", "IF-L01\n  RULING OWED: IF-03 DRAFT OWED for challenger 2026-10-06\n  2026-10-06  c\n    FORWARD   n 400\n")
    s, _rc = build(root)
    assert s["constraint"]["id"] == "RULING" and s["constraint"]["why"][0].startswith("PAST ITS DEADLINE: Re-derive BAR")
    assert s["actions"][0] == "[ ] ruling owed: Re-derive BAR before look 1 — PAST ITS DEADLINE: IF-01 look 1 taken 2026-09-01T00:00:00+00:00"
    assert "[ ] IF-03 DRAFT OWED: IF-03 DRAFT OWED for challenger 2026-10-06" in s["actions"]


def test_the_ledgers_seal_the_next_morning(tmp_path):
    root = home(tmp_path, D=D2)
    build(root, dry=False)
    cli(root, "commit", "Read the 24 h meter", "--date", D1)
    build(root, D2, NOW2, dry=False)
    assert f"morning/commitments/{D1}.jsonl" in {r for _s, r in M.manifest(root)}
    assert cli(root, "commit", "late line", "--date", D1) == 1                                   # a sealed day is never appended to


# ------------------------------------------------------------------ determinism --------------------------------------
def test_same_inputs_give_byte_identical_sheets_under_any_hash_seed(tmp_path):
    root = home(tmp_path)
    code = ("import sys; sys.path[:0] = [sys.argv[2] + '/src', sys.argv[2] + '/ops']; import morning as M; "
            f"sys.exit(M.main(['build', '--date', '{D1}', '--now', '{NOW1}', '--dry'], root=sys.argv[1], runner=lambda a: 0))")
    shas = set()
    for seed in ("0", "1", "0", "1"):
        subprocess.run([sys.executable, "-c", code, root, ROOT], env=dict(os.environ, PYTHONHASHSEED=seed), check=True, capture_output=True)
        shas.add(tuple(hashlib.sha256(open(p, "rb").read()).hexdigest() for p in M.sheet_paths(root, D1)))
    assert len(shas) == 1


# ------------------------------------------------------------------ the real journals, read only ---------------------
def test_the_counts_are_the_readouts_and_foresights_on_the_real_journal(tmp_path, monkeypatch):
    """A snapshot of the real live journal: IF-01 n as ops/readout.py counts it, IF-02 n as foresight.rows() keeps it."""
    import foresight as F
    import journal as J
    snap = tmp_path / "journal"
    shutil.copytree(os.path.join(ROOT, "journal", "live"), snap / "live")
    shutil.copy(os.path.join(ROOT, "prereg", "IF-02-FROZEN_AT"), tmp_path / "IF-02-FROZEN_AT")
    os.makedirs(tmp_path / "prereg")
    shutil.move(str(tmp_path / "IF-02-FROZEN_AT"), tmp_path / "prereg" / "IF-02-FROZEN_AT")
    monkeypatch.setattr(J, "JOURNAL", str(snap))
    fl = M.files(str(tmp_path), C.today(), None)
    live = J.read("live")
    t0 = C.frozen_at("IF-02").timestamp()
    assert sum(v["flow_honest"] for v in fl.values()) == sum(1 for r in live if r.get("standard_path") and r.get("flow")
                                                              and r.get("entry_honest") is not None)
    assert sum(v["run_honest"] for v in fl.values()) == sum(1 for r in F.rows() if r["c0"] > t0 and F.POPS["run"](r)
                                                            and r.get("entry_honest") is not None)
