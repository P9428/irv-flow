"""A miss is laid on the market, the filters or the fill; the pieces that make that possible, one test each."""
import importlib.util
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from fractions import Fraction

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "ops")]
import calibration_ledger     # noqa: E402
import common as C            # noqa: E402
import digest                 # noqa: E402
import excursion as X         # noqa: E402
import foresight as F         # noqa: E402
import journal as J           # noqa: E402
import market as MK           # noqa: E402
import predict                # noqa: E402
import readout                # noqa: E402
import rule as R              # noqa: E402

WHY = {"because": "b", "seen": "s"}
BIN = {"e": "predict", "who": "agent", "leg": "T", "kind": "binary", "q": "q", "if_yes": "y", "if_no": "n", **WHY}
IV = {"e": "predict", "who": "agent", "leg": "T", "kind": "interval", "q": "q", "if_low": "lo", "if_high": "hi", "q10": 0.0, "q50": 0.1, "q90": 0.2, **WHY}
WEEK = {"from": "2999-01-01", "to": "2999-01-07"}
FLAGS = dict.fromkeys(R.FILTERS, True)
PATCH = os.path.join(ROOT, "docs", "loop", "hunt-excursion.patch")


def row(mint, day, net=-0.1, why="STOP", flow=False, **flags):
    c0 = int(datetime(2999, 1, day, tzinfo=timezone.utc).timestamp())
    return {"mint": mint, "c0": c0, "t_entry_s": 60, "standard_path": True, "flow": flow, "flags": {**FLAGS, **flags},
            "features": {"buyers": 10 * day, "pace": 0.5 * day}, "net_honest": net, "why_honest": why, "hold_honest_s": 5,
            "entry_honest": 1.0, "fill_over_signal": 0.0, "h1": 1.0, "exit_honest": 0.9}


@pytest.fixture
def journal(tmp_path, monkeypatch):
    monkeypatch.setattr(J, "JOURNAL", str(tmp_path / "journal"))
    monkeypatch.setattr(C, "OUT", str(tmp_path / "out"))
    return lambda rows, mode="live": [J.append_line(mode, "2999-01", r) for r in rows]


def test_a_selection_miss_is_laid_on_the_market_or_the_filters_and_a_fill_miss_on_the_fill(journal, tmp_path):
    journal([row("a", 1), row("b", 2), row("c", 3, flow=True)])
    base = {"pop": "base", **WEEK}
    F.add([{**IV, "m": {**base, "stat": "mean", "field": "net_honest"}},                                   # F-0001 market, misses (-0.1)
           {**IV, "q10": 1, "q50": 3, "q90": 5, "m": {**base, "stat": "count"}},                            # F-0002 market, holds (3)
           {**BIN, "p": 0.8, "m": {"pop": "flow", "stat": "count", **WEEK}, "op": ">=", "x": 5, "given": "F-0001"},
           {**BIN, "p": 0.8, "m": {"pop": "flow", "stat": "count", **WEEK}, "op": ">=", "x": 5, "given": "F-0002"},
           {**IV, "q10": 0.5, "q50": 0.6, "q90": 0.7, "m": {**base, "stat": "median", "field": "fill_over_signal"}},
           {**BIN, "p": 0.8, "m": {"pop": "run", "stat": "count", **WEEK}, "op": ">=", "x": 5}])             # F-0006 names nothing
    assert [F.kind(p) for p in F.fold()[1].values()] == ["market", "market", "selection", "selection", "fill", "selection"]
    with pytest.raises(ValueError):                                                                         # given must name a market forecast
        F.add([{**BIN, "p": 0.8, "m": {"pop": "flow", "stat": "count", **WEEK}, "op": ">=", "x": 5, "given": "F-0003"}])
    F.add([{"e": "given", "id": "F-0006", "on": "F-0002", "because": "b"}])
    with pytest.raises(ValueError):
        F.add([{"e": "given", "id": "F-0006", "on": "F-0001", "because": "b"}])                             # it already names one
    assert F.blame(F.fold()[1]["F-0003"], F.fold()[1])[0] == "OPEN"
    F.settle_due("2999-01-08")
    preds = F.fold()[1]
    assert all(F.missed(preds[i]) for i in ("F-0001", "F-0003", "F-0004", "F-0005", "F-0006")) and not F.missed(preds["F-0002"])
    assert [F.blame(preds[i], preds)[0] for i in ("F-0001", "F-0003", "F-0004", "F-0005", "F-0006")] == ["MARKET", "MARKET", "FILTERS", "FILL", "FILTERS"]
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([{**BIN, "p": 0.5, "m": {"pop": "flow", "stat": "count", "from": "2999-02-01", "to": "2999-02-07"}, "op": ">=", "x": 1}]))
    with pytest.raises(ValueError, match="conditional on"):                                                 # the pen refuses a selection forecast alone
        predict.main("add", str(bad))


def test_market_state_and_the_target_count_metric(journal):
    rs = [row("a", 1, net=0.9, why="TARGET"), row("b", 1), row("c", 2, net=0.9, why="TARGET"), row("d", 2, net=None, why="NO_FILL")]
    s = MK.state(rs)
    assert (s["reclaims"], s["fills"], s["targets"], s["buyers"]) == (4, 3, 2, 15) and s["win"] == pytest.approx(2 / 3)
    assert MK.state([dict(row("z", 1), standard_path=False)]) is None and sorted(MK.by_day(rs)) == ["2999-01-01", "2999-01-02"]
    targets = {"pop": "base", "field": "why_honest", "eq": "TARGET", **WEEK}
    assert F.measure({**targets, "stat": "count"}, rs, "2999-01-08")[1] == 2
    assert F.measure({**targets, "stat": "per_day"}, rs, "2999-01-08")[1] == pytest.approx(2 / 7)
    assert F.measure({**targets, "stat": "frac"}, rs, "2999-01-08")[1] == 0.5              # of rows carrying the field, NO_FILL included


def test_the_days_extremes_and_what_the_filters_did_to_the_winners(monkeypatch):
    monkeypatch.setattr(C, "frozen_at", lambda contract: datetime(2999, 1, 1, 12, tzinfo=timezone.utc))
    rs = [row("w1", 2, net=1.0, why="TARGET", flow=True), row("w2", 2, net=0.9, why="TARGET", flow=False, pace=False, run=True),
          row("w3", 2, net=0.2, why="HORIZON", pace=False, run=False), row("l1", 2, net=-0.5, buyers=False), row("old", 1, net=-0.9, run=True)]
    most, least = MK.extremes(rs, 2)
    assert [r["mint"] for r in most] == ["w1", "w2"] and [r["mint"] for r in least] == ["old", "l1"]
    assert [MK.taken(r) for r in rs] == ["FLOW", "RUN", "-", "RUN", "-"]                 # `old` was created before IF-02 froze
    assert MK.failed(rs[2]) == ["run", "pace"]
    k = MK.kept(rs)
    assert (k["targets"], k["flow"], k["run"], k["winners"], k["filter"], k["turned_away"]) == (2, 1, 2, 3, "pace", 2)


def prints(c0=1000):
    """create at c0; H1 = 200 after a halving; reclaim at +5 s (210); next print 220; stop at +8 s; three prints after it."""
    spots = [(1, 100), (2, 200), (3, 90), (5, 210), (6, 220), (7, 260), (8, 190), (9, 150), (10, 500), (12, 180)]
    return [{"mint": "m", "timestamp": c0 + dt, "slot": n, "is_buy": True, "sol_amount": 0, "token_amount": 0, "user": "u",
             "virtual_sol_reserves": s, "virtual_token_reserves": 1000, "invariant_ok": True} for n, (dt, s) in enumerate(spots)]


def test_excursion_and_the_later_fills_from_a_reclaims_own_prints():
    rec = R.score_mint("m", prints(), 1000)
    x = X.measure(R.build_path(prints(), 1000), rec)
    k = float(R.K)
    assert (rec["t_entry_s"], rec["why_honest"], rec["hold_honest_s"]) == (5, "STOP", 2)
    assert x["mfe"] == pytest.approx(260 / 220 - 1) and x["mae"] == pytest.approx(190 / 220 - 1)
    assert x["post_n"] == 3 and x["post_mfe"] == pytest.approx(500 / 220 - 1) and x["post_mae"] == pytest.approx(150 / 220 - 1)
    assert x["fill_1s"] == pytest.approx(rec["fill_over_signal"]) and x["lag_1s"] == pytest.approx(0)       # the next print is the 1 s print here
    assert x["fill_2s"] == pytest.approx(260 / 210 - 1) and x["why_2s"] == "STOP" and x["net_2s"] == pytest.approx(190 / 260 * k - 1)
    assert x["lag_2s"] == pytest.approx(190 * k * (1 / 260 - 1 / 220))
    assert X.measure(R.build_path(prints()[:4], 1000), R.score_mint("m", prints()[:4], 1000)) == {}        # no print after the signal: nothing measured
    assert X.measure(R.build_path(prints(), 1000), dict(rec, t_entry_s=4)) is None                          # the record is of another path
    late = dict(row("a", 1), x=x)
    assert F.measure({"pop": "base", "stat": "mean", "field": "x.lag_2s", "from": "2999-01-01", "n": 1}, [late, row("b", 1)], "2999-01-02")[1] == pytest.approx(x["lag_2s"])


def hunters(tmp_path):
    """The hunter on disk, and the hunter with docs/loop/hunt-excursion.patch applied if it is not applied yet."""
    live = os.path.join(ROOT, "ops", "hunt.py")
    paths = [live]
    if "import excursion" not in open(live, encoding="utf-8").read():
        os.makedirs(tmp_path / "ops")
        with open(live, "rb") as src, open(tmp_path / "ops" / "hunt.py", "wb") as dst:
            dst.write(src.read())
        subprocess.run(["git", "apply", PATCH], cwd=tmp_path, check=True)
        paths.append(str(tmp_path / "ops" / "hunt.py"))
    out = []
    for i, p in enumerate(paths):
        spec = importlib.util.spec_from_file_location(f"hunt_{i}", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        out.append(mod)
    return out


def test_the_hunter_change_writes_the_same_live_line_and_one_after_line(tmp_path, monkeypatch):
    pytest.importorskip("websockets")
    monkeypatch.setattr(C, "MON", str(tmp_path / "mon"))
    monkeypatch.setattr(C, "HUNT_LOG", str(tmp_path / "mon" / "hunt.log"))
    lines = []
    for i, mod in enumerate(hunters(tmp_path)):
        monkeypatch.setattr(J, "JOURNAL", str(tmp_path / f"journal{i}"))
        h = mod.Hunter()
        h.on_create({"mint": "m", "name": "n", "symbol": "s", "creator": "c", "timestamp": 1000})
        for t in prints():
            h.on_trade(t)
        assert h.stats["closed"] == 1 and h.stats["trades"] == 7                # the three prints after the close are not counted as hunted
        h.mints["m"].seen = 0
        h.expire()
        (live,) = J.read("live")
        lines.append(({k: v for k, v in live.items() if k not in ("closed_wall", "signal_wall")}, J.read("after")))
    assert lines[0][0] == lines[-1][0]                                          # the change moves nothing in the live line
    (after,) = lines[-1][1]
    assert after["mint"] == "m" and after["x"]["post_n"] == 3 and after["x"]["lag_2s"] < 0
    monkeypatch.setattr(J, "JOURNAL", str(tmp_path / f"journal{len(lines) - 1}"))
    assert F.rows()[0]["x"] == after["x"]                                       # the reader joins it to its reclaim by mint


def test_a_function_scores_every_measurable_fill_against_the_running_rate(journal):
    with pytest.raises(ValueError):
        F.add([{"e": "function", "who": "agent", "from": C.today(), "spec": {"b": 0, "w": {"pace": 1}}, **WHY}])
    (fn,) = F.add([{"e": "function", "who": "agent", "from": "2999-01-02", "spec": {"b": 0.0, "w": {"pace": 1.0}}, **WHY}])
    rs = [row("a", 1, net=0.5), row("b", 1), row("c", 2, net=0.5), row("d", 2, pace=False), row("e", 2, net=None), dict(row("f", 2), standard_path=False)]
    ps = F.per_signal(rs, F.functions())
    assert fn["id"] == "P-0001" and len(ps) == 2                                 # day 1 predates the function; unfilled and unmeasurable are not scored
    assert ps[0] == ("2999-01-02", "P-0001", pytest.approx(1 / (1 + math.exp(-1))), 0.5, True)
    assert ps[1][2:] == (0.5, pytest.approx(2 / 3), False)
    assert calibration_ledger.brier(ps, 2) == pytest.approx(((1 / (1 + math.exp(-1)) - 1) ** 2 + 0.25) / 2)
    assert F.fold()[1] == {}                                                     # a function is not a forecast and takes no F id


def test_every_trade_from_trades_from_enters_the_journal_once_its_day_is_over_with_its_full_record(journal, monkeypatch):
    F.add([{"e": "function", "who": "agent", "from": "2999-01-02", "spec": {"b": 0.0, "w": {"pace": 1.0}}, **WHY}])
    journal([row("a", 1, net=0.5), row("b", 2), row("c", 2, net=0.5, pace=False), row("d", 3), row("e", 3, net=None)])
    monkeypatch.setattr(C, "today", lambda: "2999-01-03")
    wrote = F.score_trades("2999-01-03")
    assert [(t["mint"], t["day"], t["fn"], t["y"]) for t in wrote] == [("b", "2999-01-02", "P-0001", False), ("c", "2999-01-02", "P-0001", True)]
    assert wrote[0]["p"] == pytest.approx(1 / (1 + math.exp(-1))) and wrote[0]["running"] == 1.0 and wrote[1]["running"] == 0.5
    assert F.score_trades("2999-01-03") == []                                    # once; day 3 is not over
    with pytest.raises(ValueError):
        F.add([dict(wrote[0], at=None)])                                         # a trade is scored once
    with pytest.raises(ValueError):
        F.add([dict(wrote[0], mint="z", brier=0.0)])                             # p, y and brier must agree
    monkeypatch.setattr(C, "today", lambda: "2999-01-04")
    assert [t["mint"] for t in F.score_trades("2999-01-04")] == ["d"]
    beliefs, preds, _ = F.fold()
    calibration_ledger.training(preds, F.rows())
    with open(os.path.join(C.OUT, "foresight-training.jsonl"), encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh]
    assert [r["id"] for r in rows] == ["trade/b", "trade/c", "trade/d"]
    assert rows[1]["record"]["net_honest"] == 0.5 and rows[1]["record"]["flags"]["pace"] is False and rows[1]["rivals"] == {"running": 0.5}


def test_every_trade_in_the_journal_on_disk_re_derives_from_the_live_journal():
    """The journal's trades are the function's own reading of the hunter's record: p, rival and outcome, mint for mint."""
    scored = F.trades()
    derived = {r["mint"]: (day, fn["id"], p, run, y) for r, day, fn, p, run, y in F.in_force(F.rows(), F.functions()) if r["mint"] in scored}
    assert set(derived) == set(scored)
    for m, t in scored.items():
        assert (t["day"], t["fn"], t["y"]) == (derived[m][0], derived[m][1], derived[m][4]) and t["p"] == pytest.approx(derived[m][2])
        assert t["running"] == pytest.approx(derived[m][3]), m


def test_the_haircut_is_seeded_then_measured_and_every_honest_figure_is_printed_beside_it(journal):
    rs = [row(f"m{i}", 1, net=0.05) for i in range(MK.HAIRCUT_MIN_N)]
    h = MK.haircut(rs)
    assert h == {"latency": -0.037, "impact": -0.062509, "total": pytest.approx(-0.099509), "n": 0, "measured": False}
    short = MK.haircut([dict(r, x={"lag_2s": -0.01}) for r in rs[1:]])
    full = MK.haircut([dict(r, x={"lag_2s": -0.01}) for r in rs])
    assert not short["measured"] and short["latency"] == -0.037 and full["measured"] and full["total"] == pytest.approx(-0.072509)
    L = []
    hf = readout.honest(L, "honest arm", rs, h["total"])
    assert hf["mean"] == pytest.approx(0.05)                                     # a look reads the honest arm as frozen
    assert "mean +5.000 %" in L[0] and "win 100.0 %" in L[0] and "after the haircut (-9.95 pp)" in L[4] and "mean -4.951 %" in L[4] and "win 0.0 %" in L[4]
    assert digest.stats(rs, h["total"])["won"] == 0 and digest.stats(rs)["won"] == len(rs)
    F.add([{"e": "belief", "id": "B5", "c": 0.6, "claim": "c", "because": "b"}])
    (lesson,) = F.add([{"e": "lesson", "who": "agent", "on": ["B5"], "cause": "instrument", "text": "t", "owes": "the bar is set after the haircut"}])
    assert lesson["id"] == "L-0001" and F.fold()[2][0]["owes"].startswith("the bar")


def test_the_training_export_carries_open_forecasts(journal, tmp_path):
    F.add([{**BIN, "p": 0.3, "m": {"pop": "base", "stat": "count", **WEEK}, "op": ">=", "x": 2}])
    calibration_ledger.training(F.fold()[1], [])
    (line,) = open(tmp_path / "out" / "foresight-training.jsonl", encoding="utf-8")
    assert json.loads(line)["resolved"] is None and json.loads(line)["kind_of"] == "market" and json.loads(line)["missed"] is None


def test_the_digest_lists_untwinned_forecasts_without_anyones_number(journal, tmp_path, monkeypatch):
    monkeypatch.setattr(C, "ROOT", str(tmp_path))
    os.makedirs(tmp_path / "docs")
    assert F.blind_q({"q": "mean over 2026-10-04..10-10 (fraction: -0.012 = -1.2 %)", "q10": -0.04, "q50": -0.012, "q90": 10}) == \
        "mean over 2026-10-04..10-10 (fraction: … = … %)"                         # the author's midpoint goes; dates stay
    F.add([{**BIN, "q": "will it rain", "p": 0.83, "m": {"pop": "base", "stat": "count", **WEEK}, "op": ">=", "x": 2}])
    digest.main()
    page = open(tmp_path / "docs" / "digest.html", encoding="utf-8").read()
    assert "Yours to answer blind" in page and page.count("will it rain") == 2 and "83% likely" not in page and "your answer first" in page
    predict.main("twin", "F-0001", "0.4", "why")
    assert F.untwinned(F.fold()[1]) == []
    with pytest.raises(ValueError, match="already answered"):                    # one answer per forecaster per question
        predict.main("twin", "F-0001", "0.6", "second thoughts")
    with pytest.raises(ValueError, match="already answered"):                    # and the author cannot twin his own
        F.add([{**BIN, "p": 0.5, "twin": "F-0001", "m": {"pop": "base", "stat": "count", **WEEK}, "op": ">=", "x": 2}])
    assert len(F.fold()[1]) == 2
    digest.main()
    page = open(tmp_path / "docs" / "digest.html", encoding="utf-8").read()
    assert "Every open forecast has your number" in page and "83% likely" in page
