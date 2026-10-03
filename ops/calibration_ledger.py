"""THE CALIBRATION LEDGER — resolves every forecast whose window has closed, then reports. MISSES FIRST.

Reads journal/foresight (src/foresight.py) and the prereg's own priors (prereg/PRIORS.json, resolved by hand).
Order of the report: what resolved this run · every miss with what its author said beforehand that outcome
would mean, where the miss is laid (market, filters or fill) and whether its lesson has been written · the score ·
the per-signal function against the BASE running rate · the market by day · the haircut · the beliefs and how far
each has moved · what is still open, by kind · what the next leg owes. out/foresight-training.jsonl is the same
record, one forecast per line (open ones with `resolved` null), joined to its reasoning, outcome, score and lessons.

Brier = mean((p − outcome)²), 0.25 is always saying 50 %. bits = −log2(p given to what happened), 1.0 is a coin.
An 80 % interval is calibrated when 8 in 10 land inside; z is the miss in the forecaster's own sigma.
A RESOLUTION IS A SCORE ON A FORECAST, NEVER A VERDICT ON THE CONTRACT.
"""
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import common as C            # noqa: E402
import foresight as F         # noqa: E402
import market as MK           # noqa: E402


def said(p):
    return f"p {p['p']:.2f}" if p["kind"] == "binary" else f"80% [{p['q10']:g}, {p['q90']:g}] mid {p['q50']:g}"


def got(p):
    r = p["res"]
    if r["y"] is None:
        return "VOID"
    v = "" if r["value"] is None else f" at {r['value']:.4g}"
    return ("YES" if r["y"] else "NO") + v if p["kind"] == "binary" else f"{r['value']:.4g} ({'inside' if r['y'] else f'OUTSIDE, z {r['z']:+.1f}'})"


def score_lines(done):
    L = []
    for who in sorted({p["who"] for p in done}):
        b = [p["res"] for p in done if p["who"] == who and p["kind"] == "binary"]
        i = [p["res"] for p in done if p["who"] == who and p["kind"] == "interval"]
        L.append(f"  {who:8s} binary n {len(b)}" + (f"  Brier {st.mean(r['brier'] for r in b):.4f} (coin 0.25)  bits {st.mean(r['bits'] for r in b):.2f} (coin 1.00)" if b else "")
                 + f" | interval n {len(i)}" + (f"  inside-80% {sum(r['y'] for r in i)}/{len(i)}  median |z| {st.median(abs(r['z']) for r in i):.2f}" if i else ""))
    return L or ["  nothing resolved yet; n < 5 per forecaster is a number, not evidence"]


def training(preds):
    """Every forecast, one line each. An open one carries `resolved` null: the file was empty until the first window closed."""
    path = os.path.join(C.OUT, "foresight-training.jsonl")
    os.makedirs(C.OUT, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for p in preds.values():
            r = p["res"]
            row = {k: v for k, v in p.items() if k not in ("res", "lessons", "e")}
            row.update({"kind_of": F.kind(p), "resolved": r and {k: v for k, v in r.items() if k not in ("e", "id")},
                        "missed": F.missed(p) if r else None, "laid_on": F.blame(p, preds)[0] if r and F.missed(p) else None,
                        "reading": F.reading(p) if r and r["y"] is not None else "",
                        "lessons": [{k: l.get(k) for k in ("id", "cause", "text", "owes")} for l in p["lessons"]]})
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def brier(v, i):
    return st.mean((x[i] - x[4]) ** 2 for x in v)


def signal_lines(rs):
    fns = F.functions()
    ps = F.per_signal(rs, fns)
    L = ["", "PER SIGNAL — P(net_honest > 0) for every measurable reclaim, from a function fixed before its first day"]
    if not ps:
        return L + [f"  {len(fns)} function(s) journalled" + (f"; {fns[-1]['id']} scores from {fns[-1]['from']}" if fns else "") + "; nothing scored yet"]
    for d in sorted({x[0] for x in ps})[-7:] + ["all"]:
        v = [x for x in ps if d in ("all", x[0])]
        L.append(f"  {d:10s} n {len(v):5d}  Brier function {brier(v, 2):.4f}  running rate {brier(v, 3):.4f}  skill {1 - brier(v, 2) / brier(v, 3):+.3f}")
    return L + ["  skill > 0: the function beats quoting the BASE win rate so far. A score on the function, never a verdict."]


def market_lines(rs):
    L = ["", "MARKET — BASE by UTC day: the water FLOW and RUN fish in (last 7 days)",
         "  day         reclaims  fills  win %   mean %  targets  med buyers  med pace/s"]
    for d, v in sorted(MK.by_day(rs).items())[-7:]:
        s = MK.state(v)
        if s:
            L.append(f"  {d}  {s['reclaims']:8d}  {s['fills']:5d}  " + (f"{s['win'] * 100:5.1f}  {s['mean'] * 100:+7.2f}" if s["fills"] else "    -        -")
                     + f"  {s['targets']:7d}  {s['buyers']:10.0f}  {s['pace']:10.2f}")
    return L


def main():
    today = C.today()
    fresh = {r["id"] for r in F.settle_due(today)}
    beliefs, preds, lessons = F.fold()
    rs = F.rows()
    done = [p for p in preds.values() if p["res"]]
    scored = [p for p in done if p["res"]["y"] is not None]
    misses = [p for p in scored if F.missed(p)]
    L = [f"CALIBRATION LEDGER  {C.stamp()}  (a resolution is a score on a forecast, NEVER a verdict on the contract)",
         f"  forecasts {len(preds)}: open {len(preds) - len(done)}, resolved {len(scored)}, void {len(done) - len(scored)} | resolved this run: {', '.join(sorted(fresh)) or 'none'}",
         "", "MISSES FIRST — what was said, what happened, what it was agreed beforehand to mean"]
    for p in misses:
        L += [f"  {p['id']} {p['who']:8s} {said(p)} -> {got(p)}   {p['q'][:110]}",
              "         laid on {}: {}".format(*F.blame(p, preds)),
              f"         pre-committed reading: {F.reading(p)[:150]}"]
        L += [f"         {l['id']} {l['cause'].upper()}: {l['text'][:140]}" for l in p["lessons"]] or ["         LESSON OWED"]
    L += [] if misses else ["  none"]
    L += ["", "SCORE"] + score_lines(scored)
    L += [f"  {p['id']} {p['who']:8s} {said(p)} -> {got(p)}   {p['q'][:110]}" for p in done if p not in misses]
    L += signal_lines(rs) + market_lines(rs) + ["", "HAIRCUT — " + MK.haircut_text(MK.haircut(rs))]
    L += ["", "MODEL — credence now (at first statement), and the open forecast that can move it"]
    for b in beliefs.values():
        test = next((p["id"] for p in preds.values() if p["res"] is None and p.get("test", {}).get("belief") == b["id"]), None)
        L.append(f"  {b['id']:3s} {b['c']:.2f} ({b['trail'][0][1]:.2f}, {len(b['trail']) - 1} revisions)  {test or 'UNTESTED — nothing open can move this':9s}  {b['claim'][:120]}")
    L += ["", "OPEN"]
    for p in sorted((p for p in preds.values() if p["res"] is None), key=lambda p: p.get("m", {}).get("to") or p.get("due") or "9"):
        L.append(f"  {p['id']} {p['who']:8s} {(F.kind(p) or 'hand') + (' on ' + p['given'] if p.get('given') else ''):19s} {said(p):34s} "
                 f"{F.measure(p['m'], rs, today)[2] if 'm' in p else ('RESOLVE BY HAND, due ' if p['due'] < today else 'by hand, due ') + p['due']:22s} {p['q'][:110]}")
    owed = [l for l in lessons if l.get("owes")]
    L += ["", f"LESSONS OWED: {sum(1 for p in misses if not p['lessons'])} misses without one | THE NEXT LEG OWES: {len(owed)}"]
    L += [f"  {l['id']} ({l['cause']}) {l['owes'][:150]}" for l in owed]
    priors = C.read_json(os.path.join(C.ROOT, "prereg", "PRIORS.json"), [])
    resolved = [x for x in priors if x["outcome"] is not None]
    L += ["", "PREREG PRIORS (prereg §8, resolved by hand on the record)"]
    L += [f"  {x['id']:4s} p={x['p']:.2f} {'RESOLVED' if x['outcome'] is not None else 'OPEN':8s} {x['statement'][:80]}"
          + (f"  -> {x['outcome']}" if x["outcome"] is not None else f"  (resolves: {x['resolves'][:50]})") for x in priors]
    L.append(f"  Brier {sum((x['p'] - x['outcome']) ** 2 for x in resolved) / len(resolved):.4f} over n={len(resolved)} resolved (0.25 = coin; n<5 is a number, not evidence)"
             if resolved else f"  Brier: nothing resolved yet ({len(priors)} open priors)")
    training(preds)
    C.emit("calibration", L)


if __name__ == "__main__":
    main()
