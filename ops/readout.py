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
import foresight as F         # noqa: E402
import journal as J           # noqa: E402
import market as MK           # noqa: E402
import rule as R              # noqa: E402

Z = R.Z_LAMPORTS / 1e9
LOOKS_PATH = os.path.join(C.OUT, "looks.json")


def panel(L, name, rows, arm, cut=0.0):
    """Loss-first figures for one arm. `cut` is the haircut: every net is moved by it before anything is computed."""
    net, hold, why = f"net_{arm}", f"hold_{arm}_s", f"why_{arm}"
    rs = [r for r in rows if r.get(net) is not None]
    if not rs:
        L.append(f"  {name}: no filled positions")
        return None
    v = [r[net] + cut for r in rs]
    w, l = [x for x in v if x > 0], [x for x in v if x <= 0]
    hw = [r[hold] for r in rs if r[net] + cut > 0]
    hl = [r[hold] for r in rs if r[net] + cut <= 0]
    stops = [r for r in rs if r[why] == "STOP"]
    gap = [r[f"exit_{arm}"] / r["h1"] - 1 for r in stops]
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


def honest(L, name, rows, cut):
    """The honest arm, then the same positions after the haircut. Only the first is what a look reads."""
    hf = panel(L, name, rows, "honest")
    if hf:
        panel(L, f"  after the haircut ({cut * 100:+.2f} pp)", rows, "honest", cut)
    return hf


def diagnostics(L, rows):
    """What the filters did to the day's winners, and how far price ran. No rule, bar or look reads this."""
    days = MK.by_day(rows)
    L += ["", "WINNERS AND LOSERS BY DAY — measurable curves, honest arm (diagnostic; moves no frozen parameter)"]
    for d, rs in sorted(days.items()):
        k = MK.kept(rs)
        L.append(f"  {d}  target exits {k['targets']:3d}: FLOW kept {k['flow']}, RUN kept {k['run']} | winners {k['winners']:3d}"
                 + (f", {k['turned_away']} failed `{k['filter']}`, the filter that turned away the most" if k["winners"] else ""))
    done = [d for d in sorted(days) if d < C.today()]
    if done:
        most, least = MK.extremes(days[done[-1]])
        L.append(f"  {done[-1]}, paid most and least:")
        L += [f"    {r['net_honest'] * 100:+8.1f} %  {r['why_honest']:7s} {r['hold_honest_s']:4d} s  {r['mint'][:12]}  took: {MK.taken(r):4s}  failed: {', '.join(MK.failed(r)) or 'none'}"
              for r in most + least[::-1]]
    e = MK.excursion(rows)
    L += ["", "EXCURSION — how far price ran from the honest entry (fraction of entry; forward-only from the day the hunter records it)"]
    if not e:
        L.append("  no journalled reclaim carries it: the hunter records it from 2026-10-03 16:05 UTC on (journal/after)")
        return
    L += [f"  n {e['n']}  winners: best {e['mfe_w'] * 100:+.1f} % worst {e['mae_w'] * 100:+.1f} % (medians, before exit)" if e["mfe_w"] is not None else f"  n {e['n']}  no winners",
          f"  losers: best {e['mfe_l'] * 100:+.1f} % worst {e['mae_l'] * 100:+.1f} % (medians, before exit)" if e["mfe_l"] is not None else "  no losers",
          f"  after a STOP ({e['stopped']} with later prints): {e['back_above_entry']} traded back above the entry, {e['to_target']} reached the target level"]


def look(L, hf, name="FLOW", path=LOOKS_PATH):
    taken = C.read_json(path, {})
    n = hf["n"] if hf else 0
    due = next((lk for lk in C.LOOKS if n >= lk[1] and str(lk[0]) not in taken), None)
    if not (hf and due):
        nxt = next((lk for lk in C.LOOKS if str(lk[0]) not in taken), None)
        L.append(f"NO LOOK: honest {name} n {n}" + (f", next look at n {nxt[1]}" if nxt else " — all four looks taken")
                 + (f"; distance to bar {(hf['mean'] - C.BAR)*100:+.3f} pp" if hf else ""))
        return
    k, nk, z = due
    zs = (hf["mean"] - C.BAR) / hf["se"] if math.isfinite(hf["se"]) and hf["se"] else 0.0
    verdict = ("PASS" if zs >= z and hf["trim"] > 0 and hf["hold_ok"] else
               "FAIL" if zs <= -z else "CONTINUE" if k < 4 else "INCONCLUSIVE")
    L.append(f"LOOK {k} (n >= {nk}, z {z}): honest {name} mean {hf['mean']*100:+.3f} % vs BAR {C.BAR*100:+.3f} %  z_obs {zs:+.3f}  -> {verdict}")
    taken[str(k)] = {"n": n, "mean": hf["mean"], "z_obs": zs, "verdict": verdict, "at": C.stamp()}
    C.write_json(path, taken)


def economic(L, hf, bar, name="FLOW"):
    """The economic bar beside the frozen one: how far the honest mean sits from break-even. No look reads it."""
    if hf:
        L.append(f"ECONOMIC BAR {bar * 100:+.2f} % (break-even after the haircut, ruled 2026-10-06; reads no look): "
                 f"honest {name} mean {hf['mean'] * 100:+.3f} %, distance {(hf['mean'] - bar) * 100:+.3f} pp")


def if02(L, cut=0.0):
    """IF-02, the run band alone, forward of its own freeze. No pin, no score."""
    t0 = C.frozen_at("IF-02")
    L += ["", "IF-02 RUN — the 2-3x run band alone (prereg/IF-02-PREREGISTRATION.md)"]
    if t0 is None:
        L.append("  DRAFT: not frozen. Nothing is scored until the operator rules and `python ops/freeze.py IF-02` pins it.")
        return
    fwd = [r for r in F.rows() if r["c0"] > t0.timestamp()]
    base = [r for r in fwd if F.POPS["base"](r)]
    run = [r for r in base if F.POPS["run"](r)]
    gated = sum(1 for r in fwd if r["flags"]["run"] and r["flags"]["standard"] and not r.get("standard_path"))
    L.append(f"  forward of {t0.isoformat()}: {len(fwd)} reclaims, {len(base)} measurable, RUN {len(run)} "
             f"(+{gated} standard at entry, excluded by the full-path gate)")
    panel(L, "zero-latency arm", run, "zero")
    hr = honest(L, "honest arm (fill at next print)", run, cut)
    honest(L, "BASE since the freeze, honest arm (control, never taken)", base, cut)
    look(L, hr, "RUN", os.path.join(C.OUT, "looks-IF-02.json"))
    economic(L, hr, -cut, "RUN")


def main():
    live, fwd = J.read("live"), J.read("forward")
    rows = live + fwd
    base = [r for r in rows if r.get("standard_path")]
    flow = [r for r in base if r.get("flow")]
    h = MK.haircut(F.rows())
    L = [f"IRV-FLOW READOUT  {C.stamp()}",
         f"  journal: live {len(live)} closed positions, forward-capture {len(fwd)} | pins {'OK' if J.verify()[0] else 'MISMATCH'}",
         f"  signals: base reclaim {len(base)} (+{len(rows) - len(base)} on non-measurable curves, excluded)  FLOW {len(flow)}",
         f"  {MK.haircut_text(h)}. Honest figures are printed with it and without; looks read the honest arm as frozen.",
         "", "FLOW — the hunted trade (the only positions taken)"]
    panel(L, "zero-latency arm", flow, "zero")
    hf = honest(L, "honest arm (fill at next print)", flow, h["total"])
    L += ["", "BASE — every measurable reclaim, the control (never taken)"]
    panel(L, "zero-latency arm", base, "zero")
    honest(L, "honest arm", base, h["total"])
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
    economic(L, hf, MK.economic_bar(h))
    if02(L, h["total"])
    diagnostics(L, F.rows())
    L += ["", C.FOOTER]
    C.emit("readout", L)


if __name__ == "__main__":
    main()
