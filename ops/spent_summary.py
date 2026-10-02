"""Summarise out/spent-all.jsonl -> docs/findings/F01-spent-baseline.md. COUNTS ON SPENT DATA, NEVER EVIDENCE."""
import json
import os
import statistics as st
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import captures as CAP        # noqa: E402
import common as C            # noqa: E402
import rule as R              # noqa: E402

Z = R.Z_LAMPORTS / 1e9


def row(name, rs, key):
    v = [r[key] for r in rs if r.get(key) is not None]
    if not v:
        return f"| {name} | 0 | | | | | | |"
    w, l = [x for x in v if x > 0], [x for x in v if x <= 0]
    trim = sorted(v)[:max(1, int(len(v) * 0.95))]
    days = defaultdict(list)
    for r in rs:
        if r.get(key) is not None:
            days[CAP.day_of(r["capture"])].append(r[key])
    scored = [x for x in days.values() if len(x) >= 5]
    return (f"| {name} | {len(v)} | {st.mean(v)*100:+.2f} % | {st.median(v)*100:+.2f} % | {len(w)/len(v)*100:.1f} % | "
            f"{st.mean(l)*100 if l else 0:+.1f} % / {st.mean(w)*100 if w else 0:+.1f} % | {st.mean(trim)*100:+.2f} % | "
            f"{sum(1 for x in scored if st.mean(x) > 0)}/{len(scored)} |")


def main():
    with open(os.path.join(C.OUT, "spent-all.jsonl"), encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh]
    std = [r for r in rows if r["standard_path"]]
    dyn = [r for r in rows if not r["standard_path"]]
    flow = [r for r in std if r["flow"]]
    days = {CAP.day_of(r["capture"]) for r in rows}
    L = ["# F01 — the spent-corpus baseline (counts, never evidence)", "",
         f"Scored {len(rows)} reclaim signals over {len(days)} days of captures ≤ FROZEN_AT. Every number here was in-sample at freeze and may not be cited for IF-01.", "",
         f"- constant-product (standard) signals: {len(std)}; dynamic-curve signals: {len(dyn)} ({len(dyn)/len(rows)*100:.1f} % of all)",
         f"- FLOW signals: {len(flow)} = {len(flow)/len(days):.1f} per day; winners (zero arm) {sum(1 for r in flow if r['net_zero'] > 0)}", "",
         "| arm | n | mean | median | win | meanL / meanW | drop-top-5 % | days mean>0 |", "|---|---|---|---|---|---|---|---|",
         row("FLOW zero-latency", flow, "net_zero"), row("FLOW honest (next print)", flow, "net_honest"),
         row("BASE standard, zero", std, "net_zero"), row("BASE standard, honest", std, "net_honest"),
         row("BASE dynamic (excluded), zero", dyn, "net_zero"), row("BASE dynamic (excluded), honest", dyn, "net_honest"), "",
         "## FLOW by day (honest arm)", "", "| day | FLOW n | FLOW net SOL | FLOW win | BASE std n | BASE std net SOL |", "|---|---|---|---|---|---|"]
    byd = defaultdict(lambda: ([], []))
    for r in std:
        if r.get("net_honest") is not None:
            d = CAP.day_of(r["capture"])
            byd[d][1].append(r["net_honest"])
            if r["flow"]:
                byd[d][0].append(r["net_honest"])
    L += [f"| {d} | {len(f)} | {sum(f)*Z:+.3f} | {sum(1 for x in f if x > 0)}/{len(f)} | {len(b)} | {sum(b)*Z:+.3f} |" for d, (f, b) in sorted(byd.items())]
    L += ["", "## Filter funnel on standard-curve signals (each filter alone)", ""]
    L += [f"- {k}: {sum(1 for r in std if r['flags'][k]) / max(1, len(std)) * 100:.1f} %" for k in R.FILTERS]
    L += ["", "## Every FLOW signal in the spent corpus", "", "| day | mint | age s | run x | buyers | pace | zero | honest |", "|---|---|---|---|---|---|---|---|"]
    L += [f"| {CAP.day_of(r['capture'])} | {r['mint'][:12]} | {r['features']['age_s']} | {r['features']['run_x']:.2f} | {r['features']['buyers']} | "
          f"{r['features']['pace']:.2f} | {r['why_zero']} {r['net_zero']*100:+.1f} % | {r['why_honest']} {(r['net_honest'] or 0)*100:+.1f} % |"
          for r in sorted(flow, key=lambda r: r["capture"])]
    L += ["", C.FOOTER]
    out = os.path.join(C.ROOT, "docs", "findings", "F01-spent-baseline.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(L[:14]))


if __name__ == "__main__":
    main()
