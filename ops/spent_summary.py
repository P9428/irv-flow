"""Summarise out/spent-all.jsonl -> docs/findings/F01-spent-baseline.md. COUNTS ON SPENT DATA, NOT EVIDENCE.

Answers three questions the prereg leaves open as counts: how often FLOW fires per day, what the
spent corpus says about FLOW vs BASE on both fill arms, and whether the reclaim behaves differently
on constant-product curves than on dynamic ones.
"""
import json
import os
import statistics as st
import sys
from collections import defaultdict

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "src")]
import rule as R              # noqa: E402

Z = R.Z_LAMPORTS / 1e9
rows = [json.loads(l) for l in open(os.path.join(ROOT, "out", "spent-all.jsonl"), encoding="utf-8")]
day = lambda r: f"{r['capture'][3:7]}-{r['capture'][7:9]}-{r['capture'][9:11]}"
L = []
p = L.append


def stats(name, rs, key, hold):
    v = [r[key] for r in rs if r.get(key) is not None]
    if not v:
        p(f"| {name} | 0 | | | | | | |"); return
    w = [x for x in v if x > 0]; l = [x for x in v if x <= 0]
    trim = sorted(v)[:max(1, int(len(v) * 0.95))]
    days = defaultdict(list)
    for r in rs:
        if r.get(key) is not None:
            days[day(r)].append(r[key])
    pos_days = sum(1 for d, x in days.items() if len(x) >= 5 and st.mean(x) > 0)
    n_days = sum(1 for x in days.values() if len(x) >= 5)
    p(f"| {name} | {len(v)} | {st.mean(v)*100:+.2f} % | {st.median(v)*100:+.2f} % | {len(w)/len(v)*100:.1f} % | "
      f"{st.mean(l)*100 if l else 0:+.1f} % / {st.mean(w)*100 if w else 0:+.1f} % | {st.mean(trim)*100:+.2f} % | {pos_days}/{n_days} |")


p("# F01 — the spent-corpus baseline (counts, never evidence)")
p("")
p(f"Scored {len(rows)} reclaim signals over {len({day(r) for r in rows})} days of captures ≤ FROZEN_AT. "
  f"Every number here was in-sample at freeze and may not be cited for IF-01.")
p("")
std = [r for r in rows if r["standard_path"]]
dyn = [r for r in rows if not r["standard_path"]]
flow = [r for r in std if r["flow"]]
p(f"- constant-product (standard) signals: {len(std)}; dynamic-curve signals: {len(dyn)} ({len(dyn)/len(rows)*100:.1f} % of all)")
p(f"- FLOW signals: {len(flow)} = {len(flow)/max(1,len({day(r) for r in rows})):.1f} per day; winners (zero arm) {sum(1 for r in flow if r['net_zero']>0)}")
p("")
p("| arm | n | mean | median | win | meanL / meanW | drop-top-5 % | days mean>0 |")
p("|---|---|---|---|---|---|---|---|")
stats("FLOW zero-latency", flow, "net_zero", "hold_zero_s")
stats("FLOW honest (next print)", flow, "net_honest", "hold_honest_s")
stats("BASE standard, zero", std, "net_zero", "hold_zero_s")
stats("BASE standard, honest", std, "net_honest", "hold_honest_s")
stats("BASE dynamic (excluded), zero", dyn, "net_zero", "hold_zero_s")
stats("BASE dynamic (excluded), honest", dyn, "net_honest", "hold_honest_s")
p("")
p("## FLOW by day (honest arm)")
p("")
p("| day | FLOW n | FLOW net SOL | FLOW win | BASE std n | BASE std net SOL |")
p("|---|---|---|---|---|---|")
byd = defaultdict(lambda: {"f": [], "b": []})
for r in std:
    if r.get("net_honest") is None:
        continue
    byd[day(r)]["b"].append(r["net_honest"])
    if r["flow"]:
        byd[day(r)]["f"].append(r["net_honest"])
for d in sorted(byd):
    f, b = byd[d]["f"], byd[d]["b"]
    p(f"| {d} | {len(f)} | {sum(f)*Z:+.3f} | {sum(1 for x in f if x>0)}/{len(f)} | {len(b)} | {sum(b)*Z:+.3f} |")
p("")
p("## Filter funnel on standard-curve signals (each filter alone)")
p("")
for k in R.FILTERS:
    p(f"- {k}: {sum(1 for r in std if r['flags'][k])/max(1,len(std))*100:.1f} %")
p("")
p("## Every FLOW signal in the spent corpus")
p("")
p("| day | mint | age s | run x | buyers | pace | zero | honest |")
p("|---|---|---|---|---|---|---|---|")
for r in sorted(flow, key=day):
    f = r["features"]
    p(f"| {day(r)} | {r['mint'][:12]} | {f['age_s']} | {f['run_x']:.2f} | {f['buyers']} | {f['pace']:.2f} | {r['why_zero']} {r['net_zero']*100:+.1f} % | "
      f"{r['why_honest']} {(r['net_honest'] or 0)*100:+.1f} % |")
p("")
p("ZERO CAPITAL. NO KEY. NO WALLET. NO ORDER. NO POSITION. MARKS, NOT MONEY.")
out = os.path.join(ROOT, "docs", "findings", "F01-spent-baseline.md")
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
sys.stdout.reconfigure(encoding="utf-8")
print("\n".join(L[:14]))
