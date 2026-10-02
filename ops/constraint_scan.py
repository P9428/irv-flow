"""THE DAILY CONSTRAINT SCAN — the production line, instrumented. NAMES ONE CONSTRAINT, BY COUNT.

    1 COLLECT     is the hunter receiving the chain         heartbeat age, event gap, drops this hour
    2 INSTRUMENT  are signals becoming closed positions      closed / signals
    3 SIGNAL      is FLOW firing                             FLOW per day vs the spent corpus
    4 ACCRUE      n toward look 1 and days to get there      honest-filled FLOW vs 300 at the trailing rate
    5 DECIDE      rulings owed and unanswered                open boxes in docs/loop/rulings-owed.md
    6 MACHINE     can this box still run its own gate        out/suite.json from the last loop

The constraint is the stage with the least headroom (0..1). Headroom is a count ratio, never a
reading. Reads no outcome: no net, no exit branch.
"""
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import common as C            # noqa: E402
import journal as J           # noqa: E402

RULINGS = os.path.join(C.ROOT, "docs", "loop", "rulings-owed.md")
LOOK1 = C.LOOKS[0][1]
DROPS_PER_HOUR_FLOOR = 30


def drops_this_hour():
    hour = C.stamp()[:13]
    if not os.path.exists(C.HUNT_LOG):
        return 0
    with open(C.HUNT_LOG, encoding="utf-8") as fh:
        return sum(1 for line in fh if " drop " in line and line[:13] == hour)


def rulings_owed():
    if not os.path.exists(RULINGS):
        return []
    with open(RULINGS, encoding="utf-8") as fh:
        return [line.strip()[6:] for line in fh if line.strip().startswith("- [ ]")]


def main():
    hb, age = C.heartbeat()
    hb = hb or {}
    rows = J.read("live")
    stages = {}
    gap = time.time() - (hb.get("last_event") or 0)
    drops = drops_this_hour()
    stages["COLLECT"] = ((1.0 if age < 60 and gap < 60 else 0.0) * max(0.0, 1 - drops / DROPS_PER_HOUR_FLOOR),
                         f"heartbeat {age:.0f} s, last event {gap:.0f} s ago, drops this hour {drops}, streams up {hb.get('connected')}, lag {hb.get('lag_s')} s")
    sig, closed = hb.get("signals", 0), hb.get("closed", 0)
    stages["INSTRUMENT"] = (min(1.0, closed / sig) if sig else 1.0, f"signals {sig}, closed {closed}, open {hb.get('open', 0)} (this hunter process)")
    per_day = Counter(C.utc_day(r["c0"] + r["t_entry_s"]) for r in rows if r.get("flow"))
    full = [d for d in per_day if d < C.today()]
    rate = sum(per_day[d] for d in full) / len(full) if full else float(per_day.get(C.today(), 0))
    stages["SIGNAL"] = (min(1.0, rate / C.FLOW_RATE_SPENT),
                        f"FLOW {rate:.1f}/day over {len(full)} full days (today {per_day.get(C.today(), 0)}) vs {C.FLOW_RATE_SPENT}/day in the spent corpus")
    n = sum(1 for r in rows if r.get("flow") and r.get("entry_honest") is not None)
    stages["ACCRUE"] = (min(1.0, n / LOOK1), f"honest-filled FLOW n {n} of {LOOK1} for look 1; {(LOOK1 - n) / rate if rate else float('inf'):.0f} days at the trailing rate")
    owed = rulings_owed()
    stages["DECIDE"] = (1.0 / (1 + len(owed)), f"{len(owed)} rulings owed: " + "; ".join(o[:60] for o in owed))
    suite = C.read_json(os.path.join(C.OUT, "suite.json"))
    stages["MACHINE"] = ((1.0 if suite["rc"] == 0 else 0.0, f"last suite {suite['stamp']} rc {suite['rc']} ({suite['summary'][:60]})")
                         if suite else (0.5, "no suite record yet"))
    binding = min(stages, key=lambda k: stages[k][0])
    L = [f"CONSTRAINT SCAN  {C.stamp()}  (by count; reads no outcome)"]
    L += [f"  {'>>' if k == binding else '  '} {k:10s} headroom {h:5.2f}  {txt}" for k, (h, txt) in stages.items()]
    L += ["", f"THE CONSTRAINT: {binding} — {stages[binding][1]}", "NEXT: fix the named stage; re-run. Effort on any other stage yields zero today."]
    C.emit("constraint", L)


if __name__ == "__main__":
    main()
