"""IF-01 — the flow-filtered reclaim. ZERO CAPITAL. NO KEY. NO WALLET. NO ORDER. NO POSITION.

The reclaim core (spot, build_path, detect, manage, net_of) is a byte-for-byte mirror of
~/mimicry/src/mi11_reclaim.py, frozen 2026-08-18. tests/test_known_answer_0828.py proves the
mirror by reproducing every one of the 1,221 signals and 226 winners mimicry journalled on
2026-08-28. The FLOW filters below are the only addition, and their thresholds are FROZEN in
prereg/IF-01-PREREGISTRATION.md; tests/test_frozen.py fails if either side moves.
"""
from fractions import Fraction

D = Fraction(1, 2)                      # drawdown that freezes H1
MULTIPLE = Fraction(2)                  # take-profit multiple of entry
LOOKBACK_S = 900                        # seconds after create inside which everything happens
Z_LAMPORTS = 50_000_000                 # 0.05 SOL paper size
FEE = Fraction(125, 10000)              # 1.25 % per side, chain-measured (persistence F04)
K = (1 - FEE) / (1 + FEE)               # round-trip multiplier on the spot ratio
CREATE_SPOT = Fraction(30_000_000_000, 1_073_000_000_000_000)   # standard curve at create

FLOW = {
    "AGE_MIN_S": 30, "AGE_MAX_S": 300,                       # token age at the reclaim print
    "RUN_MIN": Fraction(2), "RUN_MAX": Fraction(3),           # H1 as a multiple of create spot
    "BUYERS_MIN": 20, "BUYERS_MAX": 80,                       # distinct buyers before entry
    "BIG_BUY_SHARE_MAX": Fraction(1, 5),                      # largest buy / all buy SOL
    "BIG_SELL_SHARE_MAX": Fraction(2, 5),                     # largest sell / all sell SOL
    "PACE_MAX": Fraction(1),                                  # prints per second before entry
    "DIP_SELLERS_MIN": 3,                                     # distinct sellers in the dip leg
    "DIP_TOP_SELLER_SHARE_MAX": Fraction(1, 2),               # top seller's share of dip sell SOL
}
FILTERS = ("age", "run", "buyers", "big_buy", "big_sell", "pace", "dip_sellers", "dip_top", "standard")


def spot(t):
    """Constant-product spot BEFORE the trade is applied. Exact Fraction, never a float."""
    if t["is_buy"]:
        vs = int(t["virtual_sol_reserves"]) - int(t["sol_amount"])
        vt = int(t["virtual_token_reserves"]) + int(t["token_amount"])
    else:
        vs = int(t["virtual_sol_reserves"]) + int(t["sol_amount"])
        vt = int(t["virtual_token_reserves"]) - int(t["token_amount"])
    return Fraction(vs, vt) if vs > 0 and vt > 0 else None


def build_path(trades, c0):
    """[(seconds_from_create, spot, trade)] inside the lookback, in (timestamp, slot) order."""
    out = []
    for t in sorted(trades, key=lambda x: (int(x["timestamp"]), int(x["slot"]))):
        dt = int(t["timestamp"]) - c0
        if 0 <= dt <= LOOKBACK_S:
            s = spot(t)
            if s is not None:
                out.append((dt, s, t))
    return out


def detect(path):
    """CAUSAL reclaim detection, mirror of mimicry detect(). Returns (i_entry, i_h1, i_low, h1) or None."""
    run_max, i_max, h1, t_low, i_h1, i_low = path[0][1], 0, None, None, None, None
    for i, (dt, s, _t) in enumerate(path):
        if h1 is None:
            if s > run_max:
                run_max, i_max = s, i
            elif s <= run_max * (1 - D):
                h1, t_low, i_h1, i_low = run_max, dt, i_max, i
        elif dt > t_low and s > h1:
            return i, i_h1, i_low, h1
    return None


def manage(path, t_from, entry, h1):
    """STOP at H1 · TARGET at MULTIPLE*entry · else the last observed spot. Mirror of mimicry manage()."""
    target = entry * MULTIPLE
    last, t_exit = entry, t_from
    for dt, s, _t in path:
        if dt <= t_from:
            continue
        last, t_exit = s, dt
        if s <= h1:
            return s, "STOP", dt
        if s >= target:
            return s, "TARGET", dt
    return last, "HORIZON", t_exit


def net_of(entry, exit_spot):
    """Per-signal net in units of position size: r·(1−f)/(1+f) − 1."""
    return (exit_spot / entry) * K - 1


K_TOL = Fraction(1, 100)


def constant_product(path):
    """True iff every print carries the token invariant AND vSOL·vTOK moves < 1 % print to print.

    Measured 2026-10-02 on 2026-08-28: on curves passing this, realised trade price sits within
    ±1.7 % (p10/p90) of the quoted spot; on curves failing it the quoted spot misses the realised
    price by −16 % / +24 %, and the wash-bot curves of 08-14/08-15 fail it outright. A mark is only
    a measurement where this holds, so nothing failing it is ever a position.
    """
    ks = [int(t["virtual_sol_reserves"]) * int(t["virtual_token_reserves"]) for _d, _s, t in path]
    return (all(t.get("invariant_ok") for _d, _s, t in path)
            and all(abs(Fraction(b, a) - 1) <= K_TOL for a, b in zip(ks, ks[1:]) if a))


def features(path, i_entry, i_h1, i_low, h1):
    pre = [t for _dt, _s, t in path[:i_entry + 1]]
    buys = [t for t in pre if t["is_buy"]]
    sells = [t for t in pre if not t["is_buy"]]
    bsol = sum(int(t["sol_amount"]) for t in buys)
    ssol = sum(int(t["sol_amount"]) for t in sells)
    dip = [t for _dt, _s, t in path[i_h1 + 1:i_low + 1] if not t["is_buy"]]
    dsol = sum(int(t["sol_amount"]) for t in dip)
    by_seller = {}
    for t in dip:
        by_seller[t["user"]] = by_seller.get(t["user"], 0) + int(t["sol_amount"])
    age = path[i_entry][0]
    return {
        "age_s": age,
        "run_x": h1 / CREATE_SPOT,
        "buyers": len({t["user"] for t in buys}),
        "big_buy_share": Fraction(max((int(t["sol_amount"]) for t in buys), default=0), bsol) if bsol else Fraction(1),
        "big_sell_share": Fraction(max((int(t["sol_amount"]) for t in sells), default=0), ssol) if ssol else Fraction(1),
        "pace": Fraction(len(pre), max(1, age)),
        "dip_sellers": len(by_seller),
        "dip_top_share": Fraction(max(by_seller.values(), default=0), dsol) if dsol else Fraction(1),
        "standard": constant_product(path[:i_entry + 1]),
        "n_pre": len(pre), "buy_sol": bsol, "sell_sol": ssol,
    }


def flow_flags(f):
    P = FLOW
    return {
        "age": P["AGE_MIN_S"] <= f["age_s"] < P["AGE_MAX_S"],
        "run": P["RUN_MIN"] <= f["run_x"] < P["RUN_MAX"],
        "buyers": P["BUYERS_MIN"] <= f["buyers"] < P["BUYERS_MAX"],
        "big_buy": f["big_buy_share"] < P["BIG_BUY_SHARE_MAX"],
        "big_sell": f["big_sell_share"] < P["BIG_SELL_SHARE_MAX"],
        "pace": f["pace"] < P["PACE_MAX"],
        "dip_sellers": f["dip_sellers"] >= P["DIP_SELLERS_MIN"],
        "dip_top": f["dip_top_share"] < P["DIP_TOP_SELLER_SHARE_MAX"],
        "standard": bool(f["standard"]),
    }


def _fx(x):
    return float(x) if isinstance(x, Fraction) else x


def score_mint(mint, trades, c0, capture=None):
    """One mint -> one record if the reclaim fires inside the lookback, else None.

    ZERO arm = mimicry's convention, entry AT the reclaim print (the journal's 08-28 numbers).
    HONEST arm = entry at the NEXT print after the reclaim print; no next print = no fill.
    """
    path = build_path(trades, c0)
    if len(path) < 3:
        return None
    hit = detect(path)
    if not hit:
        return None
    i_e, i_h1, i_low, h1 = hit
    t_e, entry = path[i_e][0], path[i_e][1]
    ex, why, t_x = manage(path, t_e, entry, h1)
    f = features(path, i_e, i_h1, i_low, h1)
    flags = flow_flags(f)
    rec = {
        "capture": capture, "mint": mint, "c0": c0,
        "t_entry_s": t_e, "h1": _fx(h1), "entry_zero": _fx(entry),
        "exit_zero": _fx(ex), "why_zero": why, "hold_zero_s": t_x - t_e,
        "net_zero": _fx(net_of(entry, ex)), "net_zero_exact": f"{net_of(entry, ex).numerator}/{net_of(entry, ex).denominator}",
        "exit_over_h1_zero": _fx(ex / h1 - 1) if why == "STOP" else None,
        "features": {k: _fx(v) for k, v in f.items()},
        "flags": flags, "flow": all(flags.values()),
        "standard_path": constant_product(path),
    }
    if i_e + 1 < len(path):
        t_f, fill = path[i_e + 1][0], path[i_e + 1][1]
        ex_h, why_h, t_xh = manage(path, t_f, fill, h1)
        rec.update({"entry_honest": _fx(fill), "fill_over_signal": _fx(fill / entry - 1), "t_fill_s": t_f,
                    "exit_honest": _fx(ex_h), "why_honest": why_h, "hold_honest_s": t_xh - t_f,
                    "net_honest": _fx(net_of(fill, ex_h)), "filled_below_h1": fill <= h1})
    else:
        rec.update({"entry_honest": None, "fill_over_signal": None, "t_fill_s": None, "exit_honest": None,
                    "why_honest": "NO_FILL", "hold_honest_s": None, "net_honest": None, "filled_below_h1": None})
    return rec


def score_capture(creates, trades, capture=None):
    """Mirror of mimicry ops/mi11_journal.journal_capture scoping: mints created in this capture."""
    c0s = {}
    for c in creates:
        m, ts = c["mint"], int(c["timestamp"])
        if m not in c0s or ts < c0s[m]:
            c0s[m] = ts
    by_mint = {}
    for t in trades:
        by_mint.setdefault(t["mint"], []).append(t)
    out = []
    for mint in sorted(by_mint):
        if mint in c0s:
            r = score_mint(mint, by_mint[mint], c0s[mint], capture)
            if r:
                out.append(r)
    return out
