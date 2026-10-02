"""THE READOUT — what the hunt produced. Reads the journals, never a capture. Marks at 0.05 SOL, not money.

Loss-first panel leads (loss-first doctrine, 2026-08-27). The verdict is evaluated only at the
n-boundaries in prereg §6, each once, recorded in out/looks.json. Any other day prints the counts
and the distance to the bar and nothing more.
"""
import math
import os
import statistics as st
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import common as C            # noqa: E402
import journal as J           # noqa: E402
import rule as R              # noqa: E402

Z = R.Z_LAMPORTS / 1e9
LOOKS_PATH = os.path.join(C.OUT, "looks.json")


def panel(L, name, rows, arm):
    net, hold, why = f"net_{arm}", f"hold_{arm}_s", f"why_{arm}"
    rs = [r for r in rows if r.get(net) is not None]
    if not rs:
        L.append(f"  {name}: no filled positions")
        return None
    v = [r[net] for r in rs]
    w, l = [x for x in v if x > 0], [x for x in v if x <= 0]
    hw = [r[hold] for r in rs if r[net] > 0]
    hl = [r[hold] for r in rs if r[net] <= 0]
    stops = [r for r in rs if r[why] == "STOP"]
    gap = [r["exit_over_h1_zero"] for r in stops if r.get("exit_over_h1_zero") is not None]
    trim = sorted(v)[:max(1, int(len(v) * 0.95))]
    mean_w, mean_l = (st.mean(w) if w else 0.0), (st.mean(l) if l else 0.0)
    hold_ok = not (hl and hw and st.median(hl) > st.median(hw))
    L.append(f"  {name}: n {len(v)}  mean {st.mean(v)*100:+.3f} %  median {st.median(v)*100:+.3f} %  net {sum(v)*Z:+.3f} SOL  win {len(w)/len(v)*100:.1f} %")
    L.append(f"    LOSS-FIRST  meanL {mean_l*100:+.2f} %  meanW {mean_w*100:+.2f} %  payoff {abs(mean_w/mean_l) if mean_l else math.inf:.2f}  "
             f"worst {min(v)*100:+.1f} %  stopped {len(stops)/len(v)*100:.1f} %  stop-fill gap median {st.median(gap)*100 if gap else 0:+.1f} %")
    L.append(f"    hold median losers {st.median(hl) if hl else 0:.0f} s  winners {st.median(hw) if hw else 0:.0f} s  -> "
             f"{'ok' if hold_ok else 'ALARM: holding losers longer than winners'}")
    L.append(f"    drop-top-5% mean {st.mean(trim)*100:+.3f} %   (lottery guard: must be > 0 at a look)")
    return {"n": len(v), "mean": st.mean(v), "se": st.pstdev(v) / math.sqrt(len(v)) if len(v) > 1 else math.inf,
            "trim": st.mean(trim), "hold_ok": hold_ok}


def look(L, hf):
    taken = C.read_json(LOOKS_PATH, {})
    n = hf["n"] if hf else 0
    due = next((lk for lk in C.LOOKS if n >= lk[1] and str(lk[0]) not in taken), None)
    if not (hf and due):
        nxt = next((lk for lk in C.LOOKS if str(lk[0]) not in taken), None)
        L.append(f"NO LOOK: honest FLOW n {n}" + (f", next look at n {nxt[1]}" if nxt else " — all four looks taken")
                 + (f"; distance to bar {(hf['mean'] - C.BAR)*100:+.3f} pp" if hf else ""))
        return
    k, nk, z = due
    zs = (hf["mean"] - C.BAR) / hf["se"] if math.isfinite(hf["se"]) and hf["se"] else 0.0
    verdict = ("PASS" if zs >= z and hf["trim"] > 0 and hf["hold_ok"] else
               "FAIL" if zs <= -z else "CONTINUE" if k < 4 else "INCONCLUSIVE")
    L.append(f"LOOK {k} (n >= {nk}, z {z}): honest FLOW mean {hf['mean']*100:+.3f} % vs BAR {C.BAR*100:+.3f} %  z_obs {zs:+.3f}  -> {verdict}")
    taken[str(k)] = {"n": n, "mean": hf["mean"], "z_obs": zs, "verdict": verdict, "at": C.stamp()}
    C.write_json(LOOKS_PATH, taken)


def main():
    live, fwd = J.read("live"), J.read("forward")
    rows = live + fwd
    base = [r for r in rows if r.get("standard_path")]
    flow = [r for r in base if r.get("flow")]
    L = [f"IRV-FLOW READOUT  {C.stamp()}",
         f"  journal: live {len(live)} closed positions, forward-capture {len(fwd)} | pins {'OK' if J.verify()[0] else 'MISMATCH'}",
         f"  signals: base reclaim {len(base)} (+{len(rows) - len(base)} on non-measurable curves, excluded)  FLOW {len(flow)}",
         "", "FLOW — the hunted trade (the only positions taken)"]
    panel(L, "zero-latency arm", flow, "zero")
    hf = panel(L, "honest arm (fill at next print)", flow, "honest")
    L += ["", "BASE — every measurable reclaim, the control (never taken)"]
    panel(L, "zero-latency arm", base, "zero")
    panel(L, "honest arm", base, "honest")
    byd = defaultdict(lambda: [0.0, 0, 0.0, 0])
    for r in base:
        if r.get("net_honest") is None:
            continue
        d = C.utc_day(r["c0"] + r["t_entry_s"])
        byd[d][2] += r["net_honest"] * Z
        byd[d][3] += 1
        if r.get("flow"):
            byd[d][0] += r["net_honest"] * Z
            byd[d][1] += 1
    L += ["", "BY DAY (FLOW honest / BASE honest, net SOL)"]
    L += [f"  {d}  FLOW {n:4d} signals {f:+.3f} SOL   BASE {m:5d} signals {b:+.3f} SOL" for d, (f, n, b, m) in sorted(byd.items())]
    L += ["", "FLOW FILTER FUNNEL (measurable reclaims passing each filter alone)"]
    L += [f"  {k:12s} {sum(1 for r in base if r['flags'].get(k)) / max(1, len(base)) * 100:5.1f} %" for k in R.FILTERS]
    L.append("")
    look(L, hf)
    L += ["", C.FOOTER]
    C.emit("readout", L)


if __name__ == "__main__":
    main()
