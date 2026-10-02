"""Batch scorer over mimicry captures (read-only). Forward = captures strictly after prereg/FROZEN_AT.

  python ops/score.py                  journal every unjournalled forward capture -> journal/forward/
  python ops/score.py --day 2026-08-28 score one SPENT day -> out/spent-2026-08-28.jsonl (never journal/)
  python ops/score.py --spent          score the whole spent corpus -> out/spent-all.jsonl
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import captures as CAP        # noqa: E402
import common as C            # noqa: E402
import journal as J           # noqa: E402
import rule as R              # noqa: E402

with open(os.path.join(C.ROOT, "prereg", "FROZEN_AT"), encoding="utf-8") as _fh:
    FROZEN_AT = _fh.read().strip()


def score(cap):
    creates = list(CAP.stream(CAP.ROOT, cap, "creates.jsonl", ("mint", "timestamp")))
    trades = list(CAP.stream(CAP.ROOT, cap, "trades.jsonl", CAP.TRADE_FIELDS))
    return R.score_capture(creates, trades, cap)


def forward():
    done_dir = os.path.join(J.JOURNAL, "forward")
    done = {f[:-6] for f in os.listdir(done_dir)} if os.path.isdir(done_dir) else set()
    todo = [cap for cap in CAP.captures() if cap > FROZEN_AT and cap not in done]
    for cap in todo:
        recs = score(cap)
        J.write_file("forward", cap, recs)
        print(f"{cap}  signals {len(recs)}  flow {sum(r['flow'] for r in recs)}", flush=True)
    print(f"forward captures scored this run: {len(todo)}")


def spent(day=None):
    os.makedirs(C.OUT, exist_ok=True)
    out = os.path.join(C.OUT, f"spent-{day or 'all'}.jsonl")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        for cap in CAP.captures():
            if cap > FROZEN_AT or (day and CAP.day_of(cap) != day):
                continue
            fh.writelines(json.dumps(r, sort_keys=True) + "\n" for r in score(cap))
            print(cap, flush=True)
    print(out)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--day"]:
        spent(args[1])
    elif args[:1] == ["--spent"]:
        spent()
    else:
        forward()
