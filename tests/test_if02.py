"""IF-02: a draft scores nothing, a pin is whole, the freeze splits spent from forward, the text declares the code."""
import hashlib
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "ops")]
import common as C            # noqa: E402
import foresight as F         # noqa: E402
import readout                # noqa: E402
import rule as R              # noqa: E402

BASE = os.path.join(ROOT, "prereg", "IF-02")
T0 = datetime(2026, 10, 4, tzinfo=timezone.utc)


def row(mint, c0, run=True, standard_path=True):
    return {"mint": mint, "c0": c0, "t_entry_s": 60, "h1": 1.0, "standard_path": standard_path,
            "flags": {"run": run, "standard": True}, "flow": False,
            "net_zero": -0.05, "hold_zero_s": 4, "why_zero": "STOP", "exit_zero": 0.97,
            "entry_honest": 1.03, "net_honest": -0.08, "hold_honest_s": 3, "why_honest": "STOP", "exit_honest": 0.97}


def test_pin_is_absent_or_whole():
    at, sha = (os.path.exists(f"{BASE}-{x}") for x in ("FROZEN_AT", "FROZEN_SHA"))
    assert at == sha
    if sha:
        with open(f"{BASE}-PREREGISTRATION.md", "rb") as fh:
            assert hashlib.sha256(fh.read()).hexdigest() == open(f"{BASE}-FROZEN_SHA", encoding="utf-8").read().strip(), \
                "IF-02 prereg changed after freeze: write an AMENDMENT, then python ops/freeze.py IF-02"


def test_a_draft_scores_nothing(monkeypatch):
    monkeypatch.setattr(C, "frozen_at", lambda contract: None)
    monkeypatch.setattr(F, "rows", lambda: [row("a", T0.timestamp() + 10)])
    L = []
    readout.if02(L)
    assert len(L) == 3 and "DRAFT" in L[2]


def test_only_mints_created_after_the_freeze_in_the_band_on_measurable_curves_are_scored(monkeypatch, tmp_path):
    t = T0.timestamp()
    monkeypatch.setattr(C, "frozen_at", lambda contract: T0)
    monkeypatch.setattr(C, "OUT", str(tmp_path))
    monkeypatch.setattr(F, "rows", lambda: [row("spent", t), row("in", t + 1), row("off-band", t + 2, run=False),
                                            row("unmeasurable", t + 3, standard_path=False)])
    L = []
    readout.if02(L)
    text = "\n".join(L)
    assert "3 reclaims, 2 measurable, RUN 1 (+1 standard at entry" in text
    assert "NO LOOK: honest RUN n 1, next look at n 300" in text
    assert not os.listdir(tmp_path)


def test_prereg_declares_the_rule_the_code_scores():
    text = open(f"{BASE}-PREREGISTRATION.md", encoding="utf-8").read()
    for k, v in (("RUN_MIN", R.FLOW["RUN_MIN"]), ("RUN_MAX", R.FLOW["RUN_MAX"]), ("K_TOL", R.K_TOL), ("D", R.D),
                 ("MULTIPLE", R.MULTIPLE), ("LOOKBACK_S", R.LOOKBACK_S), ("Z_LAMPORTS", R.Z_LAMPORTS), ("FEE", "125/10000")):
        assert f"`{k}` = {v}" in text, k
    assert f"`BAR` = {C.BAR * 100:+.4f} %" in text
    for _k, n, z in C.LOOKS:
        assert f"| {n:,} | {z:.3f} |" in text


def test_the_economic_bar_is_break_even_after_the_haircut_and_moves_no_look(monkeypatch, tmp_path):
    import market as MK
    t = T0.timestamp()
    monkeypatch.setattr(C, "frozen_at", lambda contract: T0)
    monkeypatch.setattr(C, "OUT", str(tmp_path))
    monkeypatch.setattr(F, "rows", lambda: [row("in", t + 1)])
    h = {"latency": -0.0072, "impact": -0.062509, "total": -0.069709}
    L = []
    readout.if02(L, h["total"])
    text = "\n".join(L)
    assert MK.economic_bar(h) == 0.069709 and C.BAR == 0.010370
    assert f"distance to bar {(-0.08 - C.BAR) * 100:+.3f} pp" in text
    assert "ECONOMIC BAR +6.97 % (break-even after the haircut, ruled 2026-10-06; reads no look): honest RUN mean -8.000 %, distance -14.971 pp" in text
    assert not os.listdir(tmp_path)
