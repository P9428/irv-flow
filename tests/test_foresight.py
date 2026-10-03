"""The foresight journal: nothing enters after its window opens, the machine settles it, beliefs move by Bayes."""
import os
import sys
from datetime import datetime, timezone

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "src")]
import foresight as F         # noqa: E402
import journal as J           # noqa: E402

WHY = {"because": "b", "seen": "s"}
BIN = {"e": "predict", "who": "agent", "leg": "T", "kind": "binary", "q": "q", "if_yes": "y", "if_no": "n", **WHY}
WEEK = {"from": "2999-01-01", "to": "2999-01-07"}


def row(mint, day, hour=0, **kw):
    c0 = int(datetime(2999, 1, day, hour, tzinfo=timezone.utc).timestamp())
    return {"mint": mint, "c0": c0, "t_entry_s": 60, "standard_path": True, "flow": False, **kw}


@pytest.fixture
def journal(tmp_path, monkeypatch):
    monkeypatch.setattr(J, "JOURNAL", str(tmp_path))
    return lambda rows: [J.append_line("live", "2999-01", r) for r in rows]


def test_the_journal_on_disk_was_written_forward():
    """Replay every line against the state before it, on the day it was written: the pen's rules held, in order."""
    past = []
    for ev in J.read(F.MODE):
        beliefs, preds, _ = F.fold(past)
        if ev["e"] == "resolve":
            p = preds[ev["id"]]
            assert p["res"] is None and ev["at"][:10] > p.get("m", {}).get("to", ""), ev["id"]
        elif not ev.get("was"):
            F.check(ev, beliefs, preds, ev["at"][:10])
        past.append(ev)
    assert [p for p in F.fold(past)[1]] == [f"F-{i + 1:04d}" for i in range(len(F.fold(past)[1]))]


def test_a_window_that_has_opened_is_refused_and_a_bad_batch_writes_nothing(journal):
    good = {**BIN, "p": 0.3, "m": {"pop": "base", "stat": "count", **WEEK}, "op": ">=", "x": 2}
    late = {**good, "m": {"pop": "base", "stat": "count", "from": F.C.today(), "to": "2999-01-07"}}
    with pytest.raises(ValueError):
        F.add([good, late])
    with pytest.raises(ValueError):
        F.add([{k: v for k, v in good.items() if k != "if_no"}])
    assert J.read(F.MODE) == []


def test_a_test_moves_its_belief_by_bayes_and_a_second_open_test_is_refused(journal):
    journal([row("a", 2, flow=True), row("b", 3, flow=True), row("a", 4, flow=True), row("c", 8, flow=True)])
    test = {**BIN, "m": {"pop": "flow", "stat": "count", **WEEK}, "op": "<=", "x": 2, "test": {"belief": "B1", "p_true": 0.9, "p_false": 0.3}}
    F.add([{"e": "belief", "id": "B1", "c": 0.5, "claim": "c", "because": "b"}, test])
    with pytest.raises(ValueError):
        F.add([test])
    assert F.settle_due("2999-01-07") == []                                  # the last day of the window is not over
    (r,) = F.settle_due("2999-01-08")
    beliefs, preds, _ = F.fold()
    assert (r["value"], r["y"]) == (2, True) and r["brier"] == pytest.approx(0.16)      # mint a counts once; day 8 is outside
    assert preds["F-0001"]["p"] == pytest.approx(0.6) and beliefs["B1"]["c"] == 0.75    # 0.5·0.9 / (0.5·0.9 + 0.5·0.3)
    assert not F.missed(preds["F-0001"]) and F.reading(preds["F-0001"]) == "y" and F.settle_due("2999-01-09") == []


def test_intervals_n_windows_voids_and_lessons(journal):
    rows = [row(f"m{i}", 1 + i, net_honest=n) for i, n in enumerate((0.5, -0.1, None, -0.1, -0.1))]
    journal(rows)
    iv = {"e": "predict", "who": "agent", "leg": "T", "kind": "interval", "q": "q", "if_low": "lo", "if_high": "hi", **WHY}
    F.add([{**iv, "q10": 0.0, "q50": 0.1, "q90": 0.2, "m": {"pop": "base", "stat": "frac", "field": "net_honest", "gt": 0, "from": "2999-01-01", "n": 4}},
           {**iv, "q10": 0.0, "q50": 0.1, "q90": 0.2, "m": {"pop": "base", "stat": "mean", "field": "net_honest", "from": "2999-01-01", "n": 9}},
           {**iv, "q10": 0.0, "q50": 0.1, "q90": 0.2, "m": {"pop": "flow", "stat": "median", "field": "net_honest", **WEEK}}])
    with pytest.raises(ValueError):
        F.add([{"e": "lesson", "who": "agent", "on": ["F-0002"], "cause": "variance", "text": "t"}])     # still open
    F.settle_due("2999-01-08")
    _, preds, _ = F.fold()
    r1, r2, r3 = (preds[i]["res"] for i in ("F-0001", "F-0002", "F-0003"))
    assert r1["value"] == 0.25 and r1["y"] is False and r1["z"] == pytest.approx(0.15 / (0.2 / F.Z80))   # unfilled row is not in the 4
    assert r2 is None and r3["y"] is None and r3["value"] is None                                         # 4 of 9 · no FLOW: VOID
    assert F.missed(preds["F-0001"]) and F.reading(preds["F-0001"]) == "hi" and not F.missed(preds["F-0003"])
    (lesson,) = F.add([{"e": "lesson", "who": "agent", "on": ["F-0001"], "cause": "calibration", "text": "t", "owes": "o"}])
    assert lesson["id"] == "L-0001" and F.fold()[1]["F-0001"]["lessons"][0]["owes"] == "o"


def test_hand_resolution_and_the_hour_coverage_stat(journal):
    journal([row("a", 1, hour=0), row("b", 1, hour=0), row("c", 1, hour=5)])
    assert F.measure({"pop": "all", "stat": "hours", "from": "2999-01-01", "to": "2999-01-01"}, F.rows(), "2999-01-02") == (True, 2 / 24, "")
    F.add([{**BIN, "p": 0.8, "due": "2999-01-01", "by": "git log"}])
    beliefs, preds, _ = F.fold()
    r = F.settle(preds["F-0001"], beliefs, y=False, evidence="commit abc")
    assert r["bits"] == pytest.approx(2.3219, abs=1e-4) and F.missed(F.fold()[1]["F-0001"])
