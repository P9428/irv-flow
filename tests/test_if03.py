"""IF-03: a draft scores nothing, a pin is whole, the cap fills only at or below H1 inside its window, the text declares the code."""
import hashlib
import os
import sys
from datetime import datetime, timezone
from fractions import Fraction as Fr

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "ops")]
import common as C            # noqa: E402
import excursion as X         # noqa: E402
import foresight as F         # noqa: E402
import readout                # noqa: E402
import rule as R              # noqa: E402

BASE = os.path.join(ROOT, "prereg", "IF-03")
T0 = datetime(2026, 10, 7, tzinfo=timezone.utc)
H = {"latency": -0.0072, "impact": -0.062509, "total": -0.069709}
RECLAIM = [(0, Fr(1)), (5, Fr(10)), (10, Fr(4)), (20, Fr(11))]          # H1 = 10 frozen at t 10, reclaimed at t_e = 20


def path(*after):
    return [(dt, s, None) for dt, s in RECLAIM + [(dt, Fr(s)) for dt, s in after]]


def test_pin_is_absent_or_whole():
    at, sha = (os.path.exists(f"{BASE}-{x}") for x in ("FROZEN_AT", "FROZEN_SHA"))
    assert at == sha
    if sha:
        with open(f"{BASE}-PREREGISTRATION.md", "rb") as fh:
            assert hashlib.sha256(fh.read()).hexdigest() == open(f"{BASE}-FROZEN_SHA", encoding="utf-8").read().strip(), \
                "IF-03 prereg changed after freeze: write an AMENDMENT, then python ops/freeze.py IF-03"


def test_the_cap_fills_at_the_first_print_at_or_below_h1_inside_its_window_and_exits_by_the_frozen_rule():
    x = X.measure(path((21, 12), (22, Fr(21, 2)), (23, Fr(19, 2)), (25, Fr(39, 2))), {"t_entry_s": 20})
    assert x["cap_v"] == 1 and x["cap_t"] == 3 and x["cap_why"] == "TARGET" and x["cap_hold_s"] == 2
    assert x["cap_fill"] == float(Fr(19, 20) - 1) and x["cap_exit"] == float(Fr(39, 20) - 1)
    assert x["cap_net"] == float(R.net_of(Fr(19, 2), Fr(39, 2)))


def test_no_print_at_or_below_h1_inside_the_window_is_no_trade():
    x = X.measure(path((21, 9), (26, 12), (31, 9)), {"t_entry_s": 20})           # too early (t_e + 1), then too late (t_e + 11)
    assert x["cap_v"] == 1 and not any(k in x for k in ("cap_fill", "cap_net", "cap_why", "cap_t"))


def test_a_draft_scores_nothing(monkeypatch):
    monkeypatch.setattr(C, "frozen_at", lambda contract: None)
    L = []
    readout.if03(L, H)
    assert len(L) == 3 and "DRAFT" in L[2]


def test_only_measured_mints_created_after_the_freeze_on_measurable_curves_are_scored(monkeypatch, tmp_path):
    t = T0.timestamp()

    def row(mint, c0, x, sp=True):
        return {"mint": mint, "c0": c0, "t_entry_s": 20, "h1": 1.0, "standard_path": sp, "flags": {"run": False}, "x": x,
                "entry_honest": 1.03, "net_honest": -0.08, "hold_honest_s": 3, "why_honest": "STOP", "exit_honest": 0.97}
    cap = {"cap_v": 1, "cap_t": 3, "cap_fill": -0.01, "cap_net": -0.04, "cap_why": "STOP", "cap_hold_s": 2, "cap_exit": -0.02}
    monkeypatch.setattr(C, "frozen_at", lambda contract: T0)
    monkeypatch.setattr(C, "OUT", str(tmp_path))
    monkeypatch.setattr(F, "rows", lambda: [row("spent", t, cap), row("in", t + 1, cap), row("no-fill", t + 2, {"cap_v": 1}),
                                            row("old-hunter", t + 3, {}), row("unmeasurable", t + 4, cap, sp=False)])
    L = []
    readout.if03(L, H)
    text = "\n".join(L)
    assert "3 measurable reclaims, 2 measured for the cap (+1 written before the hunter carried it), CAP filled 1" in text
    assert "NO LOOK: honest CAP n 1, next look at n 300" in text
    assert "ECONOMIC BAR +6.25 %" in text
    assert not os.listdir(tmp_path)


def test_prereg_declares_the_rule_the_code_scores():
    text = open(f"{BASE}-PREREGISTRATION.md", encoding="utf-8").read()
    for k, v in (("CAP_LAG_S", X.CAP_LAG_S), ("CAP_WINDOW_S", X.CAP_WINDOW_S), ("K_TOL", R.K_TOL), ("D", R.D),
                 ("MULTIPLE", R.MULTIPLE), ("LOOKBACK_S", R.LOOKBACK_S), ("Z_LAMPORTS", R.Z_LAMPORTS), ("FEE", "125/10000")):
        assert f"`{k}` = {v}" in text, k
    assert f"`BAR` = {C.BAR * 100:+.4f} %" in text
    for _k, n, z in C.LOOKS:
        assert f"| {n:,} | {z:.3f} |" in text
