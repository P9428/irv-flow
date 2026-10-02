"""THE DAILY MONITOR — operational health of the hunt. COSTS ZERO ALPHA.

Reads NO OUTCOME: no net, no exit branch, no win. It answers only: is the hunter alive, how many
mints did it watch, how many reclaims fired, how many were on measurable curves, how many were FLOW,
what each filter alone admits, and did the honest arm get a fill. tests/test_loop_fleet.py walks
this file's source and fails if an outcome field name appears.
"""
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "src")]
import journal as J           # noqa: E402
import rule as R              # noqa: E402

HB = os.path.join(ROOT, "monitor", "hunt-heartbeat.json")
ALERTS = os.path.join(ROOT, "monitor", "flow-alerts.log")
OUT = os.path.join(ROOT, "out", "monitor.txt")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    L = []; p = L.append
    p(f"DAILY MONITOR  {datetime.now(timezone.utc).isoformat(timespec='seconds')}  (reads no outcome)")
    try:
        hb = json.load(open(HB, encoding="utf-8"))
        p(f"  hunter pid {hb.get('pid')} connected {hb.get('connected')} drops {hb.get('drops')} | creates {hb.get('creates')} trades {hb.get('trades')} "
          f"watching {hb.get('watching')} | signals {hb.get('signals')} flow {hb.get('flow')} open {hb.get('open')} closed {hb.get('closed')} (since {datetime.fromtimestamp(hb.get('started', 0), timezone.utc).isoformat(timespec='seconds')})")
    except (FileNotFoundError, ValueError):
        p("  hunter: NO HEARTBEAT")
    rows = J.read("live")
    byd = defaultdict(list)
    for r in rows:
        byd[datetime.fromtimestamp(r["c0"] + r["t_entry_s"], timezone.utc).strftime("%Y-%m-%d")].append(r)
    p("")
    p("  day         reclaims  measurable  FLOW  honest-filled")
    for d in sorted(byd):
        rs = byd[d]; std = [r for r in rs if r.get("standard_path")]; fl = [r for r in std if r.get("flow")]
        p(f"  {d}  {len(rs):8d}  {len(std):10d}  {len(fl):4d}  {sum(1 for r in fl if r.get('entry_honest') is not None):13d}")
    std = [r for r in rows if r.get("standard_path")]
    p("")
    p("  filter funnel on measurable reclaims (each alone):")
    for k in R.FILTERS:
        p(f"    {k:12s} {sum(1 for r in std if r['flags'].get(k))/max(1, len(std))*100:5.1f} %")
    if os.path.exists(ALERTS):
        tail = [l.rstrip("\n") for l in open(ALERTS, encoding="utf-8")][-5:]
        p(""); p("  last FLOW alerts:"); [p("    " + t[:120]) for t in tail]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
