"""THE DAILY CONSTRAINT SCAN — the production line, instrumented. NAMES ONE CONSTRAINT, BY COUNT.

The line and each stage's throughput, mirrored from mimicry's scan:

    1 COLLECT     is the hunter receiving the chain         heartbeat age, event gap, drops in 24 h
    2 INSTRUMENT  are signals becoming closed positions      closed / signals, open positions stale
    3 SIGNAL      is FLOW firing                             FLOW per day vs the spent-corpus 3.5/day
    4 ACCRUE      n toward look 1 and days to get there      honest-filled FLOW vs 300, at the trailing rate
    5 DECIDE      rulings owed and unanswered                docs/loop/rulings-owed.md open boxes
    6 MACHINE     can this box still run its own gate        out/suite.json from the last loop

A stage is the CONSTRAINT when its headroom (0..1) is the smallest. Headroom is a count ratio,
never a reading. THIS READS NO OUTCOME: no net, no exit branch, no win rate.
"""
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "src")]
import journal as J           # noqa: E402

HB = os.path.join(ROOT, "monitor", "hunt-heartbeat.json")
HLOG = os.path.join(ROOT, "monitor", "hunt.log")
SUITE = os.path.join(ROOT, "out", "suite.json")
RULINGS = os.path.join(ROOT, "docs", "loop", "rulings-owed.md")
OUT = os.path.join(ROOT, "out", "constraint.txt")
LOOK1, BASE_RATE = 300, 3.5


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    now = time.time(); L = []; p = L.append
    rows = J.read("live")
    day = lambda r: datetime.fromtimestamp(r["c0"] + r["t_entry_s"], timezone.utc).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stages = {}
    # 1 COLLECT
    try:
        hb = json.load(open(HB, encoding="utf-8")); age = now - os.path.getmtime(HB); gap = now - (hb.get("last_event") or 0)
        drops24 = sum(1 for l in open(HLOG, encoding="utf-8") if " drop " in l and l[:10] == today) if os.path.exists(HLOG) else 0
        head = 1.0 if (age < 60 and gap < 60) else 0.0
        stages["COLLECT"] = (head, f"heartbeat {age:.0f} s, last event {gap:.0f} s ago, drops today {drops24}, connected {hb.get('connected')}")
    except (FileNotFoundError, ValueError):
        stages["COLLECT"] = (0.0, "no heartbeat file — the hunter is not running")
        hb = {}
    # 2 INSTRUMENT
    sig, closed, open_ = hb.get("signals", 0), hb.get("closed", 0), hb.get("open", 0)
    stages["INSTRUMENT"] = (min(1.0, closed / sig) if sig else 1.0, f"signals {sig}, closed {closed}, open {open_} (this hunter process)")
    # 3 SIGNAL
    per_day = Counter(day(r) for r in rows if r.get("flow"))
    full_days = [d for d in per_day if d < today]
    rate = (sum(per_day[d] for d in full_days) / len(full_days)) if full_days else per_day.get(today, 0)
    stages["SIGNAL"] = (min(1.0, rate / BASE_RATE), f"FLOW {rate:.1f}/day over {len(full_days)} full days (today {per_day.get(today, 0)}) vs {BASE_RATE}/day in the spent corpus")
    # 4 ACCRUE
    n = sum(1 for r in rows if r.get("flow") and r.get("entry_honest") is not None)
    days_left = (LOOK1 - n) / rate if rate else float("inf")
    stages["ACCRUE"] = (min(1.0, n / LOOK1), f"honest-filled FLOW n {n} of {LOOK1} for look 1; {days_left:.0f} days at the trailing rate")
    # 5 DECIDE
    owed = [l.strip()[6:] for l in open(RULINGS, encoding="utf-8") if l.strip().startswith("- [ ]")] if os.path.exists(RULINGS) else []
    stages["DECIDE"] = (1.0 / (1 + len(owed)), f"{len(owed)} rulings owed: " + "; ".join(o[:60] for o in owed))
    # 6 MACHINE
    try:
        s = json.load(open(SUITE, encoding="utf-8")); ok = s.get("rc") == 0
        stages["MACHINE"] = (1.0 if ok else 0.0, f"last suite {s.get('stamp')} rc {s.get('rc')} ({s.get('summary','')[:60]})")
    except (FileNotFoundError, ValueError):
        stages["MACHINE"] = (0.5, "no suite record yet")
    binding = min(stages, key=lambda k: stages[k][0])
    p(f"CONSTRAINT SCAN  {datetime.now(timezone.utc).isoformat(timespec='seconds')}  (by count; reads no outcome)")
    for k, (h, txt) in stages.items():
        p(f"  {'>>' if k == binding else '  '} {k:10s} headroom {h:5.2f}  {txt}")
    p(f"\nTHE CONSTRAINT: {binding} — {stages[binding][1]}")
    p("NEXT: fix the named stage; re-run. Effort on any other stage yields zero today.")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
