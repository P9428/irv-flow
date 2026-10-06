"""IF-L01, the learner — every trade is training data; a challenger is refit daily, frozen at birth, scored only forward.

  table(live, day)        the day's training rows: one per measurable reclaim (BASE, honest fill) entered that day
  fit(rows, haircut)      one challenger: at most MAX_CUTS entry-time cuts, chosen greedily on the drop-top-5 % mean
  record(rows, haircut)   the loss-first figures every report and every promotion test reads
  promotable(rec)         the forward record IF-L01 flags as "IF-03 DRAFT OWED" — a ruling owed, never a verdict

Contract: docs/contracts/IF-L01-learning-loop.md. Nothing here moves an IF-01 / IF-02 parameter, look or bar.
"""
import hashlib
import json
import math
import statistics as st
from datetime import datetime, timezone

FEATURES = ("age_s", "run_x", "buyers", "n_pre", "pace", "buy_sol", "sell_sol",
            "big_buy_share", "big_sell_share", "dip_sellers", "dip_top_share")
MAX_CUTS = 3
MIN_SUPPORT, MIN_SHARE = 30, 0.05
PROMOTE_N, PROMOTE_Z = 300, 2.025         # IF-01's look-1 size and look-4 boundary: the strictest pairing it declares


def day_of(unix):
    return datetime.fromtimestamp(unix, timezone.utc).strftime("%Y-%m-%d")


def table(live, day):
    """Training rows for one UTC entry day, from the hunter's live journal: first record per mint wins, as rows() does."""
    seen, out = set(), []
    for r in live:
        if r["mint"] in seen:
            continue
        seen.add(r["mint"])
        entry = r["c0"] + r["t_entry_s"]
        if day_of(entry) != day or not r.get("standard_path") or r.get("net_honest") is None:
            continue
        out.append({"mint": r["mint"], "entry": entry, "day": day, "net_honest": r["net_honest"],
                    "why_honest": r["why_honest"], "hold_honest_s": r["hold_honest_s"],
                    "flow": bool(r.get("flow")), "run": bool(r["flags"]["run"]),
                    "features": {k: r["features"][k] for k in FEATURES}})
    return sorted(out, key=lambda x: (x["entry"], x["mint"]))


def sha(rows):
    return hashlib.sha256("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows).encode()).hexdigest()


def trimmed(v):
    """The readout's lottery guard: the mean with the top 5 % of outcomes dropped."""
    return st.mean(sorted(v)[:max(1, int(len(v) * 0.95))])


def passes(row, cuts):
    return all(row["features"][f] >= q if op == ">=" else row["features"][f] < q for f, op, q in cuts)


def _deciles(v):
    s = sorted(set(v))
    return sorted({s[int(len(s) * k / 10)] for k in range(1, 10)}) if len(s) > 1 else []


def fit(rows, haircut):
    """Greedy, loss-first. A cut is kept only if it raises the drop-top-5 % mean of net in BOTH the earlier and the
    later half of the window and leaves enough rows; the cut that raises the whole window's most wins."""
    rows = sorted(rows, key=lambda r: (r["entry"], r["mint"]))
    early = {r["mint"] for r in rows[:len(rows) // 2]}
    floor = max(MIN_SUPPORT, math.ceil(len(rows) * MIN_SHARE))
    cuts, kept = [], rows

    def obj(rs):
        return trimmed([r["net_honest"] + haircut for r in rs]) if len(rs) >= 2 else -math.inf

    while len(cuts) < MAX_CUTS and len(kept) >= 2:
        base = (obj(kept), obj([r for r in kept if r["mint"] in early]), obj([r for r in kept if r["mint"] not in early]))
        best = None
        for f in FEATURES:
            if any(c[0] == f for c in cuts):
                continue
            for q in _deciles([r["features"][f] for r in kept]):
                for op in (">=", "<"):
                    sub = [r for r in kept if passes(r, [(f, op, q)])]
                    if len(sub) < floor:
                        continue
                    a = [r for r in sub if r["mint"] in early]
                    b = [r for r in sub if r["mint"] not in early]
                    if len(a) < 2 or len(b) < 2:
                        continue
                    gain = (obj(sub), obj(a), obj(b))
                    if gain[1] > base[1] and gain[2] > base[2] and gain[0] > base[0] and (best is None or gain[0] > best[0]):
                        best = (gain[0], (f, op, q), sub)
        if best is None:
            break
        cuts.append(best[1])
        kept = best[2]
    return {"cuts": [list(c) for c in cuts], "train": record(kept, haircut), "train_all": record(rows, haircut)}


def record(rows, haircut):
    """Loss-first: meanL, worst and the trimmed mean before the mean; None when nothing was taken."""
    if not rows:
        return None
    v = [r["net_honest"] + haircut for r in rows]
    losses, wins = [x for x in v if x <= 0], [x for x in v if x > 0]
    return {"n": len(v), "meanL": st.mean(losses) if losses else 0.0, "worst": min(v), "trim": trimmed(v),
            "mean": st.mean(v), "se": st.pstdev(v) / math.sqrt(len(v)) if len(v) > 1 else math.inf,
            "win": len(wins) / len(v), "net_sol": sum(v)}


def promotable(rec):
    return bool(rec and rec["n"] >= PROMOTE_N and math.isfinite(rec["se"]) and rec["se"] > 0
                and rec["mean"] / rec["se"] >= PROMOTE_Z and rec["trim"] > 0)


def describe(cuts):
    return " AND ".join(f"{f} {op} {q:.4g}" for f, op, q in cuts) or "no cut (BASE: nothing beat it in both halves)"
