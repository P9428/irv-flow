"""Batch scorer over mimicry captures (read-only). Forward = captures strictly after prereg/FROZEN_AT.

  python ops/score.py                 score every unjournalled forward capture -> journal/forward/
  python ops/score.py --day 2026-08-28  score one SPENT day -> out/spent-<day>.jsonl (never journal/)
  python ops/score.py --spent         score the whole spent corpus -> out/spent-all.jsonl
"""
import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "lib")]
import captures as C          # noqa: E402
import journal as J           # noqa: E402
import rule as R              # noqa: E402

FROZEN_AT = open(os.path.join(ROOT, "prereg", "FROZEN_AT"), encoding="utf-8").read().strip()
OUT = os.path.join(ROOT, "out")


def score(cap):
    creates = list(C.stream(C.ROOT, cap, "creates.jsonl", ("mint", "timestamp")))
    trades = list(C.stream(C.ROOT, cap, "trades.jsonl", C.TRADE_FIELDS))
    return R.score_capture(creates, trades, cap)


def forward():
    done = {f[:-6] for f in os.listdir(os.path.join(J.JOURNAL, "forward"))} if os.path.isdir(os.path.join(J.JOURNAL, "forward")) else set()
    n = 0
    for cap in C.captures():
        if cap <= FROZEN_AT or cap in done:
            continue
        recs = score(cap)
        J.write_file("forward", cap, recs)
        n += 1
        print(f"{cap}  signals {len(recs)}  flow {sum(r['flow'] for r in recs)}", flush=True)
    print(f"forward captures scored this run: {n}")


def spent(day=None):
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, f"spent-{day or 'all'}.jsonl")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        for cap in C.captures():
            if cap > FROZEN_AT or (day and C.day_of(cap) != day):
                continue
            for r in score(cap):
                fh.write(json.dumps(r, sort_keys=True) + "\n")
            print(cap, flush=True)
    print(out)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--day"]:
        spent(a[1])
    elif a[:1] == ["--spent"]:
        spent()
    else:
        forward()
