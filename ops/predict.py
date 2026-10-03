"""THE FORECASTER'S PEN — the only way a line enters journal/foresight. Protocol: docs/loop/foresight.md.

  python ops/predict.py add FILE.json                      beliefs / forecasts / lessons / given / function: validated together, appended together or not at all
                                                           a FLOW or RUN forecast is refused without `given`, the MARKET forecast it is conditional on
  python ops/predict.py blind                              the open questions with nobody's numbers (RULE 8: the operator answers first)
  python ops/predict.py twin F-0003 0.40 "why"             the operator's own number on the same question
  python ops/predict.py twin F-0007 0.5 1.3 3.0 "why"      ... on an interval: q10 q50 q90
  python ops/predict.py resolve F-0016 yes "evidence"      a forecast no journal metric can settle: yes | no | void, citing the artifact
  python ops/predict.py lesson F-0003 regime "what was wrong" ["what the next prereg owes"]
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import common as C            # noqa: E402
import foresight as F         # noqa: E402

SPEC = ("leg", "q", "kind", "m", "op", "x", "due", "by", "given", "if_yes", "if_no", "if_low", "if_high")


def main(cmd, *a):
    sys.stdout.reconfigure(encoding="utf-8")
    beliefs, preds, _ = F.fold()
    if cmd == "add":
        with open(a[0], encoding="utf-8") as fh:
            evs = json.load(fh)
        F.need(all("given" in ev for ev in evs if ev["e"] == "predict" and F.kind(ev) == "selection"),
               "a FLOW or RUN forecast names the MARKET forecast it is conditional on: given = F-<n>")
        evs = F.add(evs)
    elif cmd == "twin":
        o = preds[a[0]]
        nums = [float(x) for x in a[1:-1]]
        evs = F.add([{"e": "predict", "who": "operator", "twin": o["id"], "because": a[-1], **{k: o[k] for k in SPEC if k in o},
                      **({"p": nums[0]} if o["kind"] == "binary" else dict(zip(("q10", "q50", "q90"), nums)))}])
    elif cmd == "lesson":
        evs = F.add([{"e": "lesson", "who": "operator", "on": a[0].split(","), "cause": a[1], "text": a[2], **({"owes": a[3]} if len(a) > 3 else {})}])
    elif cmd == "resolve":
        p = preds[a[0]]
        F.need("m" not in p and p["res"] is None and a[1] in ("yes", "no", "void") and len(a) > 2, "hand resolution: an open forecast with no metric, yes|no|void, and the evidence")
        evs = [F.settle(p, beliefs, y={"yes": True, "no": False, "void": None}[a[1]], evidence=a[2])]
    else:
        F.need(cmd == "blind", __doc__)
        rs = F.rows()
        evs = []
        for p in F.untwinned(preds):
            print(f"{p['id']} {p['kind']:8s} {F.measure(p['m'], rs, C.today())[2] if 'm' in p else 'due ' + p['due']:18s} {F.blind_q(p)}")
    for ev in evs:
        print(json.dumps(ev, sort_keys=True))


if __name__ == "__main__":
    try:
        main(*sys.argv[1:] or ["blind"])
    except (ValueError, KeyError, IndexError) as e:
        sys.exit(f"REFUSED: {e!r}")
