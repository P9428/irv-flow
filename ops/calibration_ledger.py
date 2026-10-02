"""THE CALIBRATION LEDGER — every prior in the prereg, scored when it resolves. Brier beside the count.

prereg/PRIORS.json holds each prior as written before any forward signal existed: id, statement,
p, what resolves it, outcome (null until resolved by the operator or by an instrument's count).
Brier = mean((p - outcome)^2) over resolved priors; 0.25 is the score of always saying 50 %.
"""
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PRIORS = os.path.join(ROOT, "prereg", "PRIORS.json")
OUT = os.path.join(ROOT, "out", "calibration.txt")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    pr = json.load(open(PRIORS, encoding="utf-8"))
    L = [f"CALIBRATION LEDGER  {datetime.now(timezone.utc).isoformat(timespec='seconds')}"]
    res = [x for x in pr if x["outcome"] is not None]
    for x in pr:
        st = "RESOLVED" if x["outcome"] is not None else "OPEN"
        L.append(f"  {x['id']:6s} p={x['p']:.2f} {st:8s} {x['statement'][:80]}" + (f"  -> {x['outcome']}" if x["outcome"] is not None else f"  (resolves: {x['resolves'][:50]})"))
    if res:
        brier = sum((x["p"] - x["outcome"]) ** 2 for x in res) / len(res)
        L.append(f"  Brier {brier:.4f} over n={len(res)} resolved (0.25 = coin; n<5 is a number, not evidence)")
    else:
        L.append(f"  Brier: nothing resolved yet ({len(pr)} open priors)")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
