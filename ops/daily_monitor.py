"""THE DAILY MONITOR — operational health of the hunt. COSTS ZERO ALPHA.

Reads no outcome: no net, no exit branch. It answers only: is the hunter alive, how many mints
did it watch, how many reclaims fired, how many were on measurable curves, how many were FLOW,
what each filter alone admits, and did the honest arm get a fill. tests/test_loop_fleet.py fails
if an outcome field name appears in this file's body.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import common as C            # noqa: E402
import journal as J           # noqa: E402
import rule as R              # noqa: E402


def main():
    hb, age = C.heartbeat()
    L = [f"DAILY MONITOR  {C.stamp()}  (reads no outcome)"]
    if hb:
        L.append(f"  hunter pid {hb['pid']} streams up {hb['connected']} drops {hb['drops']} lag {hb['lag_s']} s heartbeat {age:.0f} s | "
                 f"creates {hb['creates']} trades {hb['trades']} watching {hb['watching']} | signals {hb['signals']} flow {hb['flow']} "
                 f"open {hb['open']} closed {hb['closed']} since {C.utc_day(hb['started'])}")
    else:
        L.append("  hunter: NO HEARTBEAT")
    rows = J.read("live")
    byd = defaultdict(list)
    for r in rows:
        byd[C.utc_day(r["c0"] + r["t_entry_s"])].append(r)
    L += ["", "  day         reclaims  measurable  FLOW  honest-filled"]
    for d, rs in sorted(byd.items()):
        std = [r for r in rs if r.get("standard_path")]
        fl = [r for r in std if r.get("flow")]
        L.append(f"  {d}  {len(rs):8d}  {len(std):10d}  {len(fl):4d}  {sum(1 for r in fl if r.get('entry_honest') is not None):13d}")
    std = [r for r in rows if r.get("standard_path")]
    L += ["", "  filter funnel on measurable reclaims (each alone):"]
    L += [f"    {k:12s} {sum(1 for r in std if r['flags'].get(k)) / max(1, len(std)) * 100:5.1f} %" for k in R.FILTERS]
    if os.path.exists(C.ALERTS):
        with open(C.ALERTS, encoding="utf-8") as fh:
            tail = [line.rstrip("\n")[:120] for line in fh][-5:]
        L += ["", "  last FLOW alerts:"] + [f"    {t}" for t in tail]
    C.emit("monitor", L)


if __name__ == "__main__":
    main()
