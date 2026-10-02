"""THE CALIBRATION LEDGER — every prior in the prereg, scored when it resolves. Brier beside the count.

prereg/PRIORS.json: id, statement, p, what resolves it, outcome (null until resolved on the record).
Brier = mean((p − outcome)²) over resolved priors; 0.25 is the score of always saying 50 %.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import common as C            # noqa: E402


def main():
    priors = C.read_json(os.path.join(C.ROOT, "prereg", "PRIORS.json"), [])
    resolved = [x for x in priors if x["outcome"] is not None]
    L = [f"CALIBRATION LEDGER  {C.stamp()}"]
    L += [f"  {x['id']:4s} p={x['p']:.2f} {'RESOLVED' if x['outcome'] is not None else 'OPEN':8s} {x['statement'][:80]}"
          + (f"  -> {x['outcome']}" if x["outcome"] is not None else f"  (resolves: {x['resolves'][:50]})") for x in priors]
    L.append(f"  Brier {sum((x['p'] - x['outcome']) ** 2 for x in resolved) / len(resolved):.4f} over n={len(resolved)} resolved (0.25 = coin; n<5 is a number, not evidence)"
             if resolved else f"  Brier: nothing resolved yet ({len(priors)} open priors)")
    C.emit("calibration", L)


if __name__ == "__main__":
    main()
