"""IF-L01, the daily learning step (docs/contracts/IF-L01-learning-loop.md). Run by ops/loop.py after the readout.

  python ops/learn.py           table every finished day, fit today's challenger once, shadow-score the lineage
  python ops/learn.py verify    every training table re-derives byte for byte from the live journal

Writes journal/train/<day>.jsonl and journal/learn/<day>.jsonl once each (pinned), out/learn.txt every run, and a box in
docs/loop/rulings-owed.md when a challenger's forward record is promotable. ZERO CAPITAL: it reads marks, nothing more.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import challenger as L        # noqa: E402
import common as C            # noqa: E402
import foresight as F         # noqa: E402
import journal as J           # noqa: E402
import market as MK           # noqa: E402

RULINGS = os.path.join(C.ROOT, "docs", "loop", "rulings-owed.md")


def _exists(mode, day):
    return os.path.exists(os.path.join(J.JOURNAL, mode, f"{day}.jsonl"))


def tabulate(live, today):
    """Write the training table of every finished entry day not yet written. Returns the days written."""
    days = sorted({L.day_of(r["c0"] + r["t_entry_s"]) for r in live})
    written = [d for d in days if d < today and not _exists("train", d)]
    for d in written:
        J.write_file("train", d, L.table(live, d))
    return written


def challenge(train, today):
    """Fit and freeze today's challenger on every trade entered before today, once."""
    seen = [r for r in train if r["day"] < today]
    if _exists("learn", today) or not seen:
        return None
    h = MK.haircut(F.rows())["total"]
    ch = L.fit(seen, h)
    J.write_file("learn", today, [{"born": today, "at": C.stamp(), "haircut": h, "cuts": ch["cuts"],
                                   "train_from": seen[0]["day"], "train_to": seen[-1]["day"], "train_sha": L.sha(seen),
                                   "train": ch["train"], "train_all": ch["train_all"]}])
    return ch


def _fig(rec):
    if rec is None:
        return "n 0"
    return (f"n {rec['n']}  meanL {rec['meanL'] * 100:+.2f} %  worst {rec['worst'] * 100:+.1f} %  "
            f"drop-top-5% {rec['trim'] * 100:+.3f} %  mean {rec['mean'] * 100:+.3f} %  win {rec['win'] * 100:.1f} %")


def shadow(train, lineage):
    """Each challenger on the trades entered on or after its birth day, beside BASE and FLOW on that same window."""
    out = []
    for c in lineage:
        window = [r for r in train if r["day"] >= c["born"]]
        fwd = L.record([r for r in window if L.passes(r, c["cuts"])], c["haircut"])
        out.append({**c, "fwd": fwd, "base": L.record(window, c["haircut"]),
                    "flow": L.record([r for r in window if r["flow"]], c["haircut"]), "promotable": L.promotable(fwd)})
    return out


def owe(promoted):
    """A promotable challenger is a ruling owed to the operator: one box each, never ticked by the machine."""
    text = open(RULINGS, encoding="utf-8").read()
    new = [f"- [ ] IF-03 DRAFT OWED: IF-L01 challenger born {c['born']} ({L.describe(c['cuts'])}) reached the promotion "
           f"test forward (n {c['fwd']['n']}, mean {c['fwd']['mean'] * 100:+.3f} % net after the haircut). Draft IF-03 "
           f"around it, or decline it with why." for c in promoted if f"challenger born {c['born']} " not in text]
    if new:
        with open(RULINGS, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(new) + "\n")
    return new


def report(train, scored, wrote, born):
    days = sorted({r["day"] for r in train})
    out = [f"IF-L01 LEARNING LOOP  {C.stamp()}",
           f"  training table: {len(train)} trades over {len(days)} days ({days[0] if days else '-'} .. {days[-1] if days else '-'})"
           f"; written this run: {', '.join(wrote) or 'nothing new'}",
           f"  today's challenger: {'fitted and frozen' if born else 'already frozen today, or no finished day to learn from'}",
           "  net = honest net + the challenger's haircut at birth; break-even (net 0) is the economic bar. Forward = trades it never saw.",
           "", "LINEAGE, best forward drop-top-5% first (a challenger with no forward trades yet sorts last)"]
    ranked = sorted(scored, key=lambda c: (c["fwd"] is None, -(c["fwd"] or {}).get("trim", 0.0), c["born"]))
    for c in ranked:
        out += [f"  {c['born']}  {L.describe(c['cuts'])}   haircut {c['haircut'] * 100:+.2f} pp"
                + ("   ** PROMOTABLE: IF-03 DRAFT OWED **" if c["promotable"] else ""),
                f"    trained ({c['train_from']} .. {c['train_to']}): {_fig(c['train'])}",
                f"    FORWARD   {_fig(c['fwd'])}",
                f"    BASE fwd  {_fig(c['base'])}",
                f"    FLOW fwd  {_fig(c['flow'])}"]
    out += ["", f"  promotion test: forward n >= {L.PROMOTE_N}, mean / SE >= {L.PROMOTE_Z}, drop-top-5% > 0. A flag is a ruling owed,"
            " never a verdict; IF-01 and IF-02 do not read this file.", "", C.FOOTER]
    return out


def verify():
    live = J.read("live")
    bad = []
    d = os.path.join(J.JOURNAL, "train")
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        with open(os.path.join(d, f), encoding="utf-8") as fh:
            on_disk = [json.loads(line) for line in fh if line.strip()]
        if L.sha(on_disk) != L.sha(L.table(live, f[:-6])):
            bad.append(f)
    print(f"train tables: {len(os.listdir(d)) if os.path.isdir(d) else 0} checked, "
          + (f"MISMATCH {', '.join(bad)}" if bad else "all re-derive from journal/live"))
    return 1 if bad else 0


def main(argv):
    if argv[1:] == ["verify"]:
        return verify()
    today = C.today()
    live = J.read("live")
    wrote = tabulate(live, today)
    train = J.read("train")
    born = challenge(train, today)
    scored = shadow(train, J.read("learn"))
    owed = owe([c for c in scored if c["promotable"]])
    lines = report(train, scored, wrote, born)
    if owed:
        lines[2:2] = [f"  RULING OWED: {o[6:]}" for o in owed]
    C.emit("learn", lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
