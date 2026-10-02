"""Daily readout. Reads journal/live and journal/forward, never a capture. Writes out/readout.txt.

Every figure is a MARK at 0.05 SOL, not money. Loss-first panel leads (loss-first doctrine):
average loss, payoff ratio, hold on losers vs winners, worst loss, stop share, stop-fill gap.
The verdict is evaluated ONLY at the pre-declared n-boundaries in prereg §6; any other day
prints the counts and the distance to the bar and nothing else.
"""
import json
import math
import os
import statistics as st
import sys
from collections import defaultdict
from datetime import datetime, timezone

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "src")]
import journal as J           # noqa: E402
import rule as R              # noqa: E402

BAR = 0.010370                                  # +1.0370 % net per signal, inherited from M-MI-11
LOOKS = ((1, 300, 4.050), (2, 600, 2.864), (3, 900, 2.338), (4, 1200, 2.025))
OUT = os.path.join(ROOT, "out", "readout.txt")
Z = R.Z_LAMPORTS / 1e9
L = []


def p(s=""):
    L.append(s)


def panel(name, rows, key, hold):
    v = [r[key] for r in rows if r.get(key) is not None]
    if not v:
        p(f"  {name}: no filled positions"); return None
    w = [x for x in v if x > 0]; l = [x for x in v if x <= 0]
    hw = [r[hold] for r in rows if r.get(key) is not None and r[key] > 0 and r.get(hold) is not None]
    hl = [r[hold] for r in rows if r.get(key) is not None and r[key] <= 0 and r.get(hold) is not None]
    stops = [r for r in rows if r.get(key) is not None and r.get("why_zero" if key == "net_zero" else "why_honest") == "STOP"]
    gap = [r["exit_over_h1_zero"] for r in stops if r.get("exit_over_h1_zero") is not None]
    mean, med = st.mean(v), st.median(v)
    trim = sorted(v)[:max(1, int(len(v) * 0.95))]
    p(f"  {name}: n {len(v)}  mean {mean*100:+.3f} %  median {med*100:+.3f} %  net {sum(v)*Z:+.3f} SOL  win {len(w)/len(v)*100:.1f} %")
    p(f"    LOSS-FIRST  meanL {st.mean(l)*100 if l else 0:+.2f} %  meanW {st.mean(w)*100 if w else 0:+.2f} %  payoff {abs(st.mean(w)/st.mean(l)) if w and l else float('nan'):.2f}  "
      f"worst {min(v)*100:+.1f} %  stopped {len(stops)/len(v)*100:.1f} %  stop-fill gap median {st.median(gap)*100 if gap else 0:+.1f} %")
    hold_flag = "ALARM: holding losers longer than winners" if hl and hw and st.median(hl) > st.median(hw) else "ok"
    p(f"    hold median losers {st.median(hl) if hl else 0:.0f} s  winners {st.median(hw) if hw else 0:.0f} s  -> {hold_flag}")
    p(f"    drop-top-5% mean {st.mean(trim)*100:+.3f} %   (lottery guard: must be > 0 at a look)")
    return {"n": len(v), "mean": mean, "se": (st.pstdev(v) / math.sqrt(len(v))) if len(v) > 1 else float("inf"),
            "trim": st.mean(trim), "hold_ok": hold_flag == "ok"}


def main():
    live, fwd = J.read("live"), J.read("forward")
    rows = live + fwd
    p("IRV-FLOW READOUT  " + datetime.now(timezone.utc).isoformat(timespec="seconds"))
    p(f"  journal: live {len(live)} closed positions, forward-capture {len(fwd)} | pins {'OK' if J.verify()[0] else 'MISMATCH'}")
    base = [r for r in rows if r.get("standard_path")]
    flow = [r for r in base if r.get("flow")]
    p(f"  signals: base reclaim {len(base)} (+{len(rows)-len(base)} on non-standard curves, excluded)  FLOW {len(flow)}")
    p("")
    p("FLOW — the hunted trade")
    zf = panel("zero-latency arm", flow, "net_zero", "hold_zero_s")
    hf = panel("honest arm (fill at next print)", flow, "net_honest", "hold_honest_s")
    p("")
    p("BASE — every reclaim, the control")
    panel("zero-latency arm", base, "net_zero", "hold_zero_s")
    hb = panel("honest arm", base, "net_honest", "hold_honest_s")
    p("")
    p("BY DAY (FLOW honest / BASE honest, net SOL)")
    byd = defaultdict(lambda: [0.0, 0, 0.0, 0])
    for r in base:
        d = r.get("capture") and f"{r['capture'][3:7]}-{r['capture'][7:9]}-{r['capture'][9:11]}" or datetime.fromtimestamp(r["c0"] + r["t_entry_s"], timezone.utc).strftime("%Y-%m-%d")
        if r.get("net_honest") is not None:
            byd[d][2] += r["net_honest"] * Z; byd[d][3] += 1
            if r.get("flow"):
                byd[d][0] += r["net_honest"] * Z; byd[d][1] += 1
    for d in sorted(byd):
        f, n, b, m = byd[d]
        p(f"  {d}  FLOW {n:4d} signals {f:+.3f} SOL   BASE {m:5d} signals {b:+.3f} SOL")
    p("")
    p("FLOW FILTER FUNNEL (base signals passing each filter alone)")
    for k in R.FILTERS:
        p(f"  {k:12s} {sum(1 for r in base if r['flags'].get(k))/max(1,len(base))*100:5.1f} %")
    p("")
    n = hf["n"] if hf else 0
    taken_path = os.path.join(ROOT, "out", "looks.json")
    taken = json.load(open(taken_path, encoding="utf-8")) if os.path.exists(taken_path) else {}
    look = next((lk for lk in LOOKS if n >= lk[1] and str(lk[0]) not in taken), None)
    if hf and look:
        k, nk, z = look
        zs = (hf["mean"] - BAR) / hf["se"] if hf["se"] else 0
        verdict = ("PASS" if zs >= z and hf["trim"] > 0 and hf["hold_ok"] else
                   "FAIL" if zs <= -z else "CONTINUE" if k < 4 else "INCONCLUSIVE")
        p(f"LOOK {k} (n >= {nk}, z {z}): honest FLOW mean {hf['mean']*100:+.3f} % vs BAR {BAR*100:+.3f} %  z_obs {zs:+.3f}  -> {verdict}")
        taken[str(k)] = {"n": n, "mean": hf["mean"], "z_obs": zs, "verdict": verdict, "at": L[0]}
        os.makedirs(os.path.dirname(taken_path), exist_ok=True)
        json.dump(taken, open(taken_path, "w", encoding="utf-8"), indent=1, sort_keys=True)
    else:
        nxt = next((lk for lk in LOOKS if str(lk[0]) not in taken), None)
        p(f"NO LOOK: honest FLOW n {n}" + (f", next look at n {nxt[1]}" if nxt else " — all four looks taken") +
          (f"; distance to bar {(hf['mean']-BAR)*100:+.3f} pp" if hf else ""))
    p("")
    p("ZERO CAPITAL. NO KEY. NO WALLET. NO ORDER. NO POSITION. MARKS, NOT MONEY.")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
