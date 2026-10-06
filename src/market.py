"""THE MARKET, THE DAY'S EXTREMES, THE EXCURSION AND THE HAIRCUT — readings of the journal that no rule reads.

  state(rs)      the market the filters fished in: measurable reclaims, BASE honest win rate and mean, target exits,
                 median buyers and pace. BASE is the market; FLOW and RUN are selections from it.
  extremes(rs)   the measurable reclaims that paid most and least on the honest arm, the filters each failed, who took it
  kept(rs)       the share of target exits FLOW and RUN kept, and the single filter that turned away the most winners
  excursion(rs)  how far price ran for and against the honest entry, before the exit and after it (x, src/excursion.py)
  haircut(rs)    ONE standing number for the gap between the honest arm and a real taker: latency + own impact
  economic_bar(h) the honest mean a signal must clear to break even once the haircut is paid (operator, 2026-10-06)

The haircut is seeded and then measured. Own impact: −6.2509 % median per round trip at 1.00 SOL at create depth
(~/mimicry out/mi86-create-own-impact.txt, RESULTS §82), read 2026-10-03. Latency: −3.7 pp, the figure IF-01 §8 cites
as mimicry §58; on 2026-10-03 it could NOT be found in ~/mimicry as a latency cost (§58 measures a follower that
improves with latency), so it stands as the operator's seed until x.lag_2s has HAIRCUT_MIN_N measurable rows, and is
then replaced by their mean. Diagnostics, never a verdict: no look, bar or frozen parameter reads any of this.
"""
import statistics as st

import common as C
import foresight as F
import rule as R

SEED = {"latency": -0.037, "impact": -0.062509}
HAIRCUT_MIN_N = 300
FILTERS = tuple(k for k in R.FILTERS if k != "standard")        # standard is the measurement gate, true on every measurable row


def fills(rs):
    return [r for r in rs if F.POPS["base"](r) and r.get("net_honest") is not None]


def state(rs):
    """Market figures over the measurable reclaims in rs, or None when there are none."""
    base = [r for r in rs if F.POPS["base"](r)]
    v = fills(base)
    if not base:
        return None
    return {"reclaims": len(base), "fills": len(v), "win": sum(r["net_honest"] > 0 for r in v) / len(v) if v else None,
            "mean": st.mean(r["net_honest"] for r in v) if v else None, "targets": sum(r["why_honest"] == "TARGET" for r in v),
            "buyers": st.median(r["features"]["buyers"] for r in base), "pace": st.median(r["features"]["pace"] for r in base)}


def by_day(rs):
    days = {}
    for r in rs:
        days.setdefault(C.utc_day(F.entry(r)), []).append(r)
    return days


def taken(r):
    """Which contract held the position on paper: FLOW (IF-01), RUN (IF-02, mints created after its freeze), or neither."""
    t0 = C.frozen_at("IF-02")
    return "FLOW" if r.get("flow") else "RUN" if r["flags"]["run"] and t0 and r["c0"] > t0.timestamp() else "-"


def failed(r):
    return [k for k in FILTERS if not r["flags"][k]]


def extremes(rs, k=5):
    """(most, least): the k best and k worst honest nets among measurable fills, best and worst first."""
    v = sorted(fills(rs), key=lambda r: r["net_honest"])
    return v[::-1][:k], v[:k]


def kept(rs):
    """What the filters did to the winners: target exits kept by FLOW and by RUN, and the filter failing the most winners."""
    v = fills(rs)
    targets, winners = [r for r in v if r["why_honest"] == "TARGET"], [r for r in v if r["net_honest"] > 0]
    away = {k: sum(not r["flags"][k] for r in winners) for k in FILTERS}
    worst = max(away, key=away.get) if winners else None
    return {"targets": len(targets), "flow": sum(bool(r.get("flow")) for r in targets), "run": sum(r["flags"]["run"] for r in targets),
            "winners": len(winners), "filter": worst, "turned_away": away[worst] if worst else 0}


def excursion(rs):
    """Medians over measurable fills that carry x, split by outcome, or None before the hunter records it."""
    v = [r for r in fills(rs) if "mfe" in r.get("x", {})]
    if not v:
        return None
    w, l = [r["x"] for r in v if r["net_honest"] > 0], [r["x"] for r in v if r["net_honest"] <= 0]
    stopped = [r["x"] for r in v if r["why_honest"] == "STOP" and "post_mfe" in r["x"]]
    med = lambda xs, k: st.median(x[k] for x in xs) if xs else None                 # noqa: E731
    return {"n": len(v), "mfe_w": med(w, "mfe"), "mae_w": med(w, "mae"), "mfe_l": med(l, "mfe"), "mae_l": med(l, "mae"),
            "stopped": len(stopped), "back_above_entry": sum(x["post_mfe"] > 0 for x in stopped),
            "to_target": sum(x["post_mfe"] >= float(R.MULTIPLE) - 1 for x in stopped)}


def haircut(rs):
    lag = [r["x"]["lag_2s"] for r in rs if F.POPS["base"](r) and r.get("x", {}).get("lag_2s") is not None]
    measured = len(lag) >= HAIRCUT_MIN_N
    latency = st.mean(lag) if measured else SEED["latency"]
    return {"latency": latency, "impact": SEED["impact"], "total": latency + SEED["impact"], "n": len(lag), "measured": measured}


def economic_bar(h):
    """BAR re-derived from operator economics, ruled 2026-10-06 (docs/decisions/2026-10-06-economic-bar.md): break-even
    after the haircut, with no fixed cost because a paid feed is vetoed on funds. It replaces M-MI-11's +1.0370 %, which
    is the struck $30M target's growth rate over signal density, in every live-capital prereg. IF-01 and IF-02 keep
    their frozen BAR (IF-02 look 1 was taken under it); this is printed beside their looks and read by none."""
    return -h["total"]


def haircut_text(h):
    return (f"haircut {h['total'] * 100:+.2f} pp = latency {h['latency'] * 100:+.2f} "
            f"({'measured on ' + str(h['n']) + ' 2 s fills' if h['measured'] else f'seed, source not found in mimicry §58; {h['n']} of {HAIRCUT_MIN_N} 2 s fills'}) "
            f"+ own impact {h['impact'] * 100:+.2f} at 1 SOL (mimicry §82)")
