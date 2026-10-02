"""Synthetic paths: the mirror detects and manages exactly as mimicry's rule, and every FLOW
filter trips on the threshold it declares."""
import os
import sys
from fractions import Fraction

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "src")]
import rule as R              # noqa: E402

VS0, VT0 = 30_000_000_000, 1_073_000_000_000_000


def trade(ts, slot, buy, sol, user, vs, vt):
    """A record whose PRE-trade spot is vs/vt (rule.spot undoes the trade)."""
    tok = sol * vt // vs if sol else 0
    if buy:
        return {"timestamp": ts, "slot": slot, "is_buy": True, "sol_amount": sol, "token_amount": tok, "user": user,
                "virtual_sol_reserves": vs + sol, "virtual_token_reserves": vt - tok, "sol_offset_standard": True, "invariant_ok": True}
    return {"timestamp": ts, "slot": slot, "is_buy": False, "sol_amount": sol, "token_amount": tok, "user": user,
            "virtual_sol_reserves": vs - sol, "virtual_token_reserves": vt + tok, "sol_offset_standard": True, "invariant_ok": True}


def path_runs_then_dips_then_reclaims(n_buyers=30, dip_sellers=5, run=Fraction(5, 2)):
    """Build a mint: many small buys lift spot to run*create, several sellers drop it 50 %, then a print above H1."""
    c0, ts, slot, trades = 1_000_000, 1_000_000, 1, []
    vs, vt = VS0, VT0
    target = R.CREATE_SPOT * run
    i = 0
    while Fraction(vs, vt) < target:
        sol = 500_000_000
        trades.append(trade(ts + i * 2, slot + i, True, sol, f"buyer{i % n_buyers}", vs, vt))
        tok = sol * vt // vs; vs, vt = vs + sol, vt - tok; i += 1
    h1 = Fraction(vs, vt)
    while Fraction(vs, vt) > h1 / 2:
        sol = 400_000_000
        trades.append(trade(ts + i * 2, slot + i, False, sol, f"seller{i % dip_sellers}", vs, vt))
        tok = sol * vt // vs; vs, vt = vs - sol, vt + tok; i += 1
    while Fraction(vs, vt) <= h1:
        sol = 1_000_000_000
        trades.append(trade(ts + i * 2, slot + i, True, sol, f"late{i}", vs, vt))
        tok = sol * vt // vs; vs, vt = vs + sol, vt - tok; i += 1
    trades.append(trade(ts + i * 2, slot + i, True, 10_000_000, "reclaimer", vs, vt))      # the print ABOVE H1
    t_last = ts + i * 2
    for j in range(1, 4):                                                                     # three more prints, flat
        trades.append(trade(t_last + j, slot + i + j, True, 1_000_000, f"after{j}", vs, vt))
    return trades, c0 - 10, h1          # create 10 s before the first print; age lands inside [30, 300)


def test_detect_freezes_h1_at_first_half_drawdown_and_enters_on_first_print_above():
    trades, c0, h1 = path_runs_then_dips_then_reclaims()
    path = R.build_path(trades, c0)
    hit = R.detect(path)
    assert hit is not None
    i_e, i_h1, i_low, got_h1 = hit
    assert got_h1 == h1 and path[i_h1][1] == h1 and path[i_e][1] > h1 and all(s <= h1 for _d, s, _t in path[i_low:i_e])


def test_manage_stop_target_horizon():
    p = [(0, Fraction(1), {}), (1, Fraction(2), {}), (2, Fraction(5, 4), {}), (3, Fraction(1, 2), {})]
    assert R.manage(p, 0, Fraction(1), Fraction(9, 10))[:2] == (Fraction(2), "TARGET")
    assert R.manage(p, 1, Fraction(2), Fraction(3, 2))[:2] == (Fraction(5, 4), "STOP")
    assert R.manage(p, 2, Fraction(5, 4), Fraction(1, 4))[:2] == (Fraction(1, 2), "HORIZON")


def test_net_of_is_round_trip_fee_on_the_spot_ratio():
    assert R.net_of(Fraction(1), Fraction(2)) == 2 * Fraction(79, 81) - 1
    assert R.net_of(Fraction(1), Fraction(1)) == Fraction(79, 81) - 1


def test_flow_passes_the_synthetic_winner_shape():
    trades, c0, _h1 = path_runs_then_dips_then_reclaims()
    rec = R.score_mint("m", trades, c0)
    assert rec is not None and rec["flow"], rec["flags"]


def test_each_filter_trips_on_its_own_threshold():
    base = {"age_s": 60, "run_x": Fraction(5, 2), "buyers": 30, "big_buy_share": Fraction(1, 10), "big_sell_share": Fraction(1, 10),
            "pace": Fraction(1, 2), "dip_sellers": 5, "dip_top_share": Fraction(1, 4), "standard": True}
    assert all(R.flow_flags(base).values())
    for k, v, flag in (("age_s", 29, "age"), ("age_s", 300, "age"), ("run_x", Fraction(199, 100), "run"), ("run_x", Fraction(3), "run"),
                       ("buyers", 19, "buyers"), ("buyers", 80, "buyers"), ("big_buy_share", Fraction(1, 5), "big_buy"),
                       ("big_sell_share", Fraction(2, 5), "big_sell"), ("pace", Fraction(1), "pace"), ("dip_sellers", 2, "dip_sellers"),
                       ("dip_top_share", Fraction(1, 2), "dip_top"), ("standard", False, "standard")):
        f = dict(base, **{k: v})
        flags = R.flow_flags(f)
        assert not flags[flag] and sum(not x for x in flags.values()) == 1, (k, v)


def test_honest_arm_fills_at_the_next_print_and_no_next_print_is_no_fill():
    trades, c0, _ = path_runs_then_dips_then_reclaims()
    rec = R.score_mint("m", trades, c0)
    assert rec["t_fill_s"] > rec["t_entry_s"] and rec["entry_honest"] is not None
    cut = [t for t in trades if t["timestamp"] <= c0 + rec["t_entry_s"]]
    rec2 = R.score_mint("m", cut, c0)
    assert rec2["why_honest"] == "NO_FILL" and rec2["net_honest"] is None
