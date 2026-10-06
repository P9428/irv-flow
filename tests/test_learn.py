"""IF-L01: every trade is a training row, a challenger is frozen at birth and scored only on trades it never saw."""
import os
import sys
from datetime import datetime, timezone

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "ops")]
import challenger as L        # noqa: E402
import common as C            # noqa: E402
import foresight as F         # noqa: E402
import journal as J           # noqa: E402
import learn as O             # noqa: E402
import market as MK           # noqa: E402


def feats(**kw):
    return {k: 1.0 for k in L.FEATURES} | kw


def live(mint, day, hour, net, standard=True, flow=False, **kw):
    c0 = int(datetime(2999, 1, day, hour, tzinfo=timezone.utc).timestamp())
    return {"mint": mint, "c0": c0, "t_entry_s": 60, "standard_path": standard, "net_honest": net, "why_honest": "STOP",
            "hold_honest_s": 3, "flow": flow, "flags": {"run": False}, "features": feats(**kw)}


def test_a_day_table_holds_each_measurable_honest_fill_entered_that_day_once():
    rows = [live("a", 1, 1, -0.1), live("a", 1, 2, 0.5), live("b", 1, 3, None), live("c", 1, 4, -0.2, standard=False),
            live("d", 2, 1, 0.3)]
    t = L.table(rows, "2999-01-01")
    assert [r["mint"] for r in t] == ["a"] and t[0]["net_honest"] == -0.1
    assert set(t[0]["features"]) == set(L.FEATURES)


def planted(n=200):
    """pace < 0.5 pays in both halves; buyers >= 50 pays only in the early half (a fluke the learner must refuse)."""
    rows = []
    for i in range(n):
        early = i < n // 2
        good = i % 4 == 0
        fluke = i % 4 == 1
        net = 0.30 if good else (0.40 if fluke and early else -0.20)
        rows.append({"mint": f"m{i:04d}", "entry": i, "day": "2999-01-01", "net_honest": net, "flow": False,
                     "features": feats(pace=0.1 if good else 0.9, buyers=60.0 if fluke else 10.0)})
    return rows


def test_the_learner_keeps_a_cut_that_holds_in_both_halves_and_refuses_one_that_holds_in_one():
    ch = L.fit(planted(), 0.0)
    assert [c[0] for c in ch["cuts"]] == ["pace"] and ch["cuts"][0][1] == "<"
    assert ch["train"]["trim"] > 0 > ch["train_all"]["trim"]


def test_nothing_learned_is_recorded_as_no_cut():
    rows = [{"mint": f"m{i}", "entry": i, "day": "2999-01-01", "net_honest": -0.1, "flow": False, "features": feats()}
            for i in range(100)]
    assert L.fit(rows, 0.0)["cuts"] == [] and "no cut" in L.describe([])


@pytest.fixture
def box(tmp_path, monkeypatch):
    monkeypatch.setattr(J, "JOURNAL", str(tmp_path / "journal"))
    monkeypatch.setattr(J, "MANIFEST", str(tmp_path / "journal" / "MANIFEST"))
    monkeypatch.setattr(C, "OUT", str(tmp_path / "out"))
    rulings = tmp_path / "rulings-owed.md"
    rulings.write_text("# RULINGS OWED\n", encoding="utf-8")
    monkeypatch.setattr(O, "RULINGS", str(rulings))
    monkeypatch.setattr(F, "rows", lambda: [])
    monkeypatch.setattr(MK, "haircut", lambda rs: {"total": -0.07})
    return tmp_path


def run_on(monkeypatch, day, rows):
    monkeypatch.setattr(C, "today", lambda: day)
    for r in rows:
        J.append_line("live", "all", r)
    return O.main(["learn.py"])


def test_a_challenger_is_frozen_once_a_day_and_scored_only_on_trades_entered_from_its_birth(box, monkeypatch):
    early = [live(f"e{i}", 1, i % 24, -0.1, pace=0.9) for i in range(40)]
    assert run_on(monkeypatch, "2999-01-02", early) == 0
    lineage = J.read("learn")
    assert [c["born"] for c in lineage] == ["2999-01-02"] and lineage[0]["train_to"] == "2999-01-01"
    assert len(J.read("train")) == 40
    run_on(monkeypatch, "2999-01-02", [])
    assert len(J.read("learn")) == 1 and len(J.read("train")) == 40                      # the second run writes nothing
    later = [live(f"f{i}", 2, i % 24, 0.05) for i in range(10)]
    run_on(monkeypatch, "2999-01-03", later)
    c = O.shadow(J.read("train"), J.read("learn"))[0]
    assert c["fwd"]["n"] == 10 and abs(c["fwd"]["mean"] - (0.05 - 0.07)) < 1e-12           # day 1 never scores it
    assert open(os.path.join(C.OUT, "learn.txt"), encoding="utf-8").read().startswith("IF-L01 LEARNING LOOP")
    assert O.verify() == 0


def test_a_promotable_forward_record_owes_one_ruling_and_the_machine_never_ticks_it(box, monkeypatch):
    c = {"born": "2999-01-02", "cuts": [["pace", "<", 0.5]], "haircut": 0.0}
    rec = {"n": 300, "mean": 0.02, "se": 0.005, "trim": 0.01}
    assert L.promotable(rec) and not L.promotable(rec | {"trim": -0.01}) and not L.promotable(rec | {"n": 299})
    assert len(O.owe([c | {"fwd": rec}])) == 1 and O.owe([c | {"fwd": rec}]) == []
    text = open(O.RULINGS, encoding="utf-8").read()
    assert text.count("- [ ] IF-03 DRAFT OWED") == 1 and "[x]" not in text


def test_verify_catches_a_table_that_no_longer_re_derives(box, monkeypatch):
    run_on(monkeypatch, "2999-01-02", [live(f"e{i}", 1, 1, -0.1) for i in range(5)])
    path = os.path.join(J.JOURNAL, "train", "2999-01-01.jsonl")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(open(path, encoding="utf-8").readline())
    assert O.verify() == 1
