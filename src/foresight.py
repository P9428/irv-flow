"""THE FORESIGHT JOURNAL — what we said would happen, written before it could be known, scored when it is.

Four events, one JSON line each, append-only in journal/foresight/<utc-day>.jsonl, sealed like the live journal:

  belief   a causal claim the program runs on, with a credence c. Revised only by appending.
  predict  a forecast whose window opens strictly after the day it is written. binary (p that value OP x)
           or interval (q10 / q50 / q90, an 80 % interval). It carries its reasoning, what the author had
           already seen, and what each outcome will be taken to mean — written before the outcome exists.
           `test` makes a binary forecast an experiment on a belief: p_true and p_false are its likelihoods.
  resolve  written by the machine from the journals, or by hand with evidence where no metric exists.
           A belief under test moves by Bayes on the likelihoods declared with the forecast.
  lesson   why a forecast missed, by cause, and what the next leg's prereg owes because of it. It is drawn from
           resolved forecasts, or from a stated belief when the debt is known before anything resolves.
  given    names, for a FLOW or RUN forecast already in the journal without one, the market forecast it stands on.
  function a per-signal forecaster: P(net_honest > 0) for every measurable reclaim from its `from` day, as a logistic
           on the entry-observable flags. Fixed here before that day; scored by Brier against the BASE running rate.
  trade    every measurable honest fill from TRADES_FROM, written by the machine once its UTC day is over: the
           function in force, its P at entry, the BASE running rate beside it, what happened. Each trade is training
           data (operator, 2026-10-06); its full record joins it in out/foresight-training.jsonl. From 2026-10-06 it
           also carries when it was entered (`when`): UTC and Central time, the UTC weekday, and the trading session.
  rebase   a trade's BASE running rate as the record now gives it, written by the machine when a row entered before the
           trade reached the journal after it was scored (a late forward-capture witness): `recorded` is the rate the
           trade carries, `now` the re-derived one. Only the reference moves; p, function and outcome never do
           (ruled through RI 2026-10-07, docs/decisions/2026-10-07-running-rate-late-rows.md).

Three kinds of forecast, by what they measure: MARKET (pop all | base), SELECTION (pop flow | run), FILL (a fill
field). A SELECTION forecast names the MARKET forecast it is conditional on (`given`; the pen refuses one without
it), so its miss can be laid on the market or on the filters; a FILL miss is the fill's.

A resolution is a score on a forecast. It is NEVER a verdict on the contract (prereg §6), and a lesson
never moves a frozen parameter: it is debt the next prereg pays.
"""
import math
import re
import statistics as st
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import common as C
import journal as J

MODE = "foresight"
CAUSES = ("instrument", "model", "regime", "calibration", "variance")
C_MIN, C_MAX = 0.02, 0.98               # no belief becomes unfalsifiable
Z80 = 2.563                             # an 80 % interval is 2.563 sigma wide
REBASE_EPS = 1e-12                       # a running rate the record still gives, to float noise
TRADES_FROM = "2026-10-05"              # operator, 2026-10-06: every trade from yesterday on is training data here
CT = ZoneInfo("America/Chicago")
# The trading session by UTC hour of entry, fixed in UTC all year (no daylight saving shift); operator, 2026-10-06.
SESSIONS = ((0, 7, "Asia"), (7, 13, "Europe"), (13, 16, "Europe/US overlap"), (16, 21, "US"), (21, 24, "US late"))
WHEN = ("entry_utc", "entry_ct", "weekday", "session")
OPS = {"<": lambda v, x: v < x, "<=": lambda v, x: v <= x, ">": lambda v, x: v > x, ">=": lambda v, x: v >= x}
POPS = {"all": lambda r: True, "base": lambda r: bool(r.get("standard_path")),
        "flow": lambda r: bool(r.get("standard_path") and r.get("flow")),
        "run": lambda r: bool(r.get("standard_path") and r["flags"]["run"])}
STATS = ("count", "per_day", "hours", "mean", "median", "frac")
SELECTION = ("flow", "run")
FILL_FIELDS = ("fill_over_signal", "filled_below_h1")       # and every x.* field (src/excursion.py)


def entry(r):
    return r["c0"] + r["t_entry_s"]


def rows():
    """One row per mint, the contract's unit, in entry order. Live first, so the hunter's record wins a tie."""
    late = {a["mint"]: a["x"] for a in J.read("after")}
    by = {}
    for r in J.read("live") + J.read("forward"):
        by.setdefault(r["mint"], r)
    return sorted(({**r, "x": late[r["mint"]]} if r["mint"] in late else r for r in by.values()), key=entry)


def field(r, path):
    for k in path.split("."):
        r = r.get(k) if isinstance(r, dict) else None
    return r


def measure(m, rs, today):
    """(closed, value, progress). Closed with value None is VOID: the window shut on nothing measurable.

    pop all | base | flow | run · from = first UTC day · to = last full UTC day, or n = the first n rows ·
    field = dotted path, rows where it is null are not in the population (unfilled is not a position) ·
    stat count | per_day | hours (share of UTC hours with a closed reclaim) | mean | median | frac (gt / eq / truthy);
    count and per_day with gt / eq count only the rows that hit.
    """
    f = m.get("field")
    hit = (lambda v: v > m["gt"]) if "gt" in m else (lambda v: v == m["eq"]) if "eq" in m else None
    rs = [r for r in rs if POPS[m["pop"]](r) and C.utc_day(entry(r)) >= m["from"] and (not f or field(r, f) is not None)]
    if "n" in m:
        if len(rs) < m["n"]:
            return False, None, f"{len(rs)} of {m['n']}"
        rs = rs[:m["n"]]
    else:
        if today <= m["to"]:
            return False, None, f"closes {m['to']}"
        rs = [r for r in rs if C.utc_day(entry(r)) <= m["to"]]
        days = (date.fromisoformat(m["to"]) - date.fromisoformat(m["from"])).days + 1
    s = m["stat"]
    if hit and s in ("count", "per_day"):
        rs = [r for r in rs if hit(field(r, f))]
    if s == "count":
        return True, len(rs), ""
    if s == "per_day":
        return True, len(rs) / days, ""
    if s == "hours":
        return True, len({entry(r) // 3600 for r in rs}) / (24 * days), ""
    vals = [field(r, f) for r in rs]
    if not vals:
        return True, None, ""
    if s == "frac":
        return True, sum(map(hit or bool, vals)) / len(vals), ""
    return True, (st.mean if s == "mean" else st.median)(vals), ""


def fold(events=None):
    """The journal folded into the present: beliefs with their credence trail, forecasts with their resolution, lessons."""
    beliefs, preds, lessons = {}, {}, []
    for ev in J.read(MODE) if events is None else events:
        if ev["e"] == "belief":
            b = beliefs.setdefault(ev["id"], {"id": ev["id"], "claim": ev.get("claim"), "trail": []})
            b["trail"].append((ev["at"], ev["c"], ev["because"]))
            b["c"] = ev["c"]
        elif ev["e"] == "predict":
            preds[ev["id"]] = dict(ev, res=None, lessons=[])
        elif ev["e"] == "resolve":
            preds[ev["id"]]["res"] = ev
        elif ev["e"] == "given":
            preds[ev["id"]]["given"] = ev["on"]
        elif ev["e"] == "lesson":
            lessons.append(ev)
            for i in ev["on"]:
                if i in preds:
                    preds[i]["lessons"].append(ev)
    return beliefs, preds, lessons


def need(ok, why):
    if not ok:
        raise ValueError(why)


def text(ev, *keys):
    for k in keys:
        need(isinstance(ev.get(k), str) and ev[k].strip(), f"{ev.get('id', ev['e'])}: `{k}` is required")


def kind(p):
    """market | selection | fill, by what the forecast measures; None where no metric says (hand-resolved)."""
    m = p.get("m")
    if not m:
        return None
    f = m.get("field", "")
    return "fill" if f in FILL_FIELDS or f.startswith("x.") else "selection" if m["pop"] in SELECTION else "market"


def blame(p, preds):
    """Where a miss is laid: (MARKET | FILTERS | FILL | OPEN | UNASSIGNED, why). A reading of two scores, never a verdict."""
    k = kind(p)
    if k != "selection":
        return {"market": ("MARKET", "a market forecast"), "fill": ("FILL", "a fill forecast")}.get(k, ("UNASSIGNED", "no metric"))
    g = p.get("given") or preds.get(p.get("twin"), {}).get("given")
    if not g:
        return "UNASSIGNED", "names no market forecast"
    mk = preds[g]["res"]
    if mk is None or mk["y"] is None:
        return ("OPEN", f"{g} has not resolved") if mk is None else ("UNASSIGNED", f"{g} was VOID")
    if missed(preds[g]):
        return "MARKET", f"{g} missed too: the market was not the one this stood on"
    return "FILTERS", f"{g} held: the market came in as forecast, the selection did not"


def untwinned(preds):
    """Open forecasts the operator has not answered: his to write blind (rule 8)."""
    done = {p["twin"] for p in preds.values() if "twin" in p}
    return [p for p in preds.values() if p["res"] is None and "twin" not in p and p["who"] != "operator" and p["id"] not in done]


def blind_q(p):
    """The question with its author's own numbers struck out, for a reader who has not answered it yet."""
    q = p["q"]
    for v in (p.get(k) for k in ("p", "q10", "q50", "q90")):
        for s in (f"{v:g}", f"{v * 100:g}") if v is not None else ():
            q = re.sub(rf"(?<![\d.\-]){re.escape(s)}(?![\d.\-])", "…", q)
    return q


def functions(events=None):
    return [ev for ev in (J.read(MODE) if events is None else events) if ev["e"] == "function"]


def in_force(rs, fns):
    """(row, day, function, p, running rate, won) for every measurable honest fill a function was in force for.

    In force = the last function whose `from` is on or before the entry day. The reference is the BASE running rate:
    the share of winners among every measurable honest fill before this one, which needs no model at all.
    """
    won, n = 0, 0
    for r in rs:
        if not POPS["base"](r) or r.get("net_honest") is None:
            continue
        day, y = C.utc_day(entry(r)), r["net_honest"] > 0
        fn = next((f for f in reversed(fns) if f["from"] <= day), None)
        if fn and n:
            z = fn["spec"]["b"] + sum(w for k, w in fn["spec"]["w"].items() if r["flags"].get(k))
            yield r, day, fn, 1 / (1 + math.exp(-z)), won / n, y
        won, n = won + y, n + 1


def per_signal(rs, fns):
    """[(day, function id, p, running rate, won)], in_force without the row."""
    return [(day, fn["id"], p, run, y) for _r, day, fn, p, run, y in in_force(rs, fns)]


def when(unix):
    """When a trade was entered: UTC time, Central time, the UTC weekday and the session (SESSIONS)."""
    t = datetime.fromtimestamp(unix, timezone.utc)
    return {"entry_utc": t.isoformat(timespec="seconds"), "entry_ct": t.astimezone(CT).strftime("%Y-%m-%d %H:%M:%S %Z"),
            "weekday": t.strftime("%A"), "session": next(name for lo, hi, name in SESSIONS if lo <= t.hour < hi)}


def trades(events=None):
    """The trades already scored in the journal, by mint, each carrying its latest rebased running rate."""
    out = {}
    for ev in J.read(MODE) if events is None else events:
        if ev["e"] == "trade":
            out[ev["mint"]] = ev
        elif ev["e"] == "rebase":
            out[ev["mint"]] = dict(out[ev["mint"]], running=ev["now"])
    return out


def score_trades(today=None):
    """Write every measurable honest fill from TRADES_FROM whose UTC day is over and is not yet in the journal, then a
    rebase for every scored trade whose running rate the record no longer gives. Returns the events written."""
    today = today or C.today()
    past = J.read(MODE)
    done = trades(past)
    forced = list(in_force(rows(), functions(past)))
    evs = [{"e": "trade", "mint": r["mint"], "day": day, "fn": fn["id"], "p": p, "running": run, "y": y, "brier": (p - y) ** 2,
            **when(entry(r))}
           for r, day, fn, p, run, y in forced if TRADES_FROM <= day < today and r["mint"] not in done]
    evs += [{"e": "rebase", "mint": r["mint"], "recorded": done[r["mint"]]["running"], "now": run}
            for r, _day, _fn, _p, run, _y in forced if r["mint"] in done and abs(done[r["mint"]]["running"] - run) > REBASE_EPS]
    return add(evs) if evs else []


def mix(c, t):
    return c * t["p_true"] + (1 - c) * t["p_false"]


def check(ev, beliefs, preds, today, events=()):
    """Refuse anything that could not have been a forecast: a window already open, a number without a reason.
    `events` is the journal before `ev`: a trade is checked against the functions and trades already in it."""
    e = ev["e"]
    if e == "trade":
        fns = [f for f in functions(events) if f["from"] <= ev["day"]]
        need(fns and fns[-1]["id"] == ev["fn"], f"{ev['mint']}: scored by the function in force on {ev['day']}")
        need(TRADES_FROM <= ev["day"] < today, f"{ev['mint']}: a trade is scored after its UTC day is over, from {TRADES_FROM}")
        need(ev["mint"] not in trades(events), f"{ev['mint']} is already scored")
        need(0 < ev["p"] < 1 and 0 <= ev["running"] <= 1 and isinstance(ev["y"], bool)
             and abs(ev["brier"] - (ev["p"] - ev["y"]) ** 2) < 1e-12, f"{ev['mint']}: p, running, y and brier agree")
        if any(k in ev for k in WHEN):                         # every trade written from 2026-10-06 carries them
            utc = datetime.fromisoformat(ev["entry_utc"]).timestamp()
            need(ev["entry_utc"][:10] == ev["day"] and {k: ev.get(k) for k in WHEN} == when(utc),
                 f"{ev['mint']}: entry time, weekday and session agree with each other and the day")
    elif e == "rebase":
        t = trades(events).get(ev["mint"])
        need(t is not None, f"{ev['mint']}: a rebase goes on a trade already scored")
        need(t and abs(ev["recorded"] - t["running"]) < 1e-12, f"{ev['mint']}: recorded is the running rate the trade carries")
        need(0 <= ev["now"] <= 1 and abs(ev["now"] - ev["recorded"]) > REBASE_EPS, f"{ev['mint']}: now is a rate and differs from recorded")
    elif e == "belief":
        need(re.fullmatch(r"B\d+", ev["id"]) and C_MIN <= ev["c"] <= C_MAX, f"{ev['id']}: id B<n>, c inside [{C_MIN}, {C_MAX}]")
        text(ev, "because", *(() if ev["id"] in beliefs else ("claim",)))
    elif e == "lesson":
        need(ev["cause"] in CAUSES, f"cause is one of {CAUSES}")
        need(ev["on"] and all(i in beliefs or (i in preds and preds[i]["res"]) for i in ev["on"]), "a lesson is drawn from resolved forecasts or stated beliefs")
        text(ev, "text")
    elif e == "given":
        p = preds.get(ev["id"], {})
        need(kind(p) == "selection" and p["res"] is None and "twin" not in p and "given" not in p and p["m"]["from"] > today,
             f"{ev['id']}: `given` goes on an open SELECTION forecast that names no market forecast, before its window opens")
        need(kind(preds.get(ev["on"], {})) == "market" and "twin" not in preds[ev["on"]], f"{ev['on']} is not a MARKET forecast")
        text(ev, "because")
    elif e == "function":
        need(ev["from"] > today, "a function is fixed before the first day it scores")
        need(isinstance(ev["spec"]["b"], (int, float)) and ev["spec"]["w"] and all(isinstance(v, (int, float)) for v in ev["spec"]["w"].values()),
             "spec is a logistic: b, and w by flag")
        text(ev, "because", "seen")
    else:
        need(e == "predict" and ev["who"] in ("agent", "operator") and ev["kind"] in ("binary", "interval"), "who agent|operator, kind binary|interval")
        text(ev, "leg", "q", "because")
        twin = ev.get("twin")
        if twin:
            need(twin in preds and preds[twin]["res"] is None and "twin" not in preds[twin], f"{twin} is not an open original")
            need(ev["who"] != preds[twin]["who"] and not any(p.get("twin") == twin and p["who"] == ev["who"] for p in preds.values()),
                 f"{ev['who']} has already answered {twin}: one answer per forecaster per question")
        else:
            text(ev, "seen")
        if ev["kind"] == "binary":
            text(ev, "if_yes", "if_no")
            need(0 < ev["p"] < 1, "0 < p < 1")
        else:
            text(ev, "if_low", "if_high")
            need(ev["q10"] < ev["q50"] < ev["q90"], "q10 < q50 < q90")
        m = ev.get("m")
        if m:
            need(m["pop"] in POPS and m["stat"] in STATS and ("to" in m) != ("n" in m), "m: pop, stat, and exactly one of to / n")
            need(m["from"] > today and m.get("to", m["from"]) >= m["from"], "the window opens after the day the forecast is written")
            need("field" in m or m["stat"] in ("count", "per_day", "hours"), f"stat {m['stat']} needs a field")
            need("to" in m or m["stat"] not in ("per_day", "hours"), f"stat {m['stat']} needs a dated window")
            need(ev["kind"] == "interval" or (ev["op"] in OPS and isinstance(ev["x"], (int, float))), "a binary forecast on a metric needs op and x")
            if "given" in ev:
                need(kind(ev) == "selection" and kind(preds.get(ev["given"], {})) == "market" and "twin" not in preds[ev["given"]],
                     "given goes on a FLOW or RUN forecast and names a MARKET forecast (pop all | base)")
        else:
            need(ev["kind"] == "binary" and ev["due"] > today, "a hand-resolved forecast is binary and due after today")
            text(ev, "by")
        t = ev.get("test")
        if t:
            need(ev["kind"] == "binary" and not twin and t["belief"] in beliefs, "a test is an original binary forecast on a stated belief")
            need(0 < t["p_true"] < 1 and 0 < t["p_false"] < 1 and t["p_true"] != t["p_false"], "likelihoods inside (0, 1) and different, or it tests nothing")
            need(not any(p["res"] is None and p.get("test", {}).get("belief") == t["belief"] for p in preds.values()),
                 f"{t['belief']} already has an open test; two on overlapping evidence would count it twice")
            need(abs(ev["p"] - mix(t["c"], t)) < 1e-9, "p of a test is the credence-weighted mix of its likelihoods")


def add(events):
    """Validate every event against the journal as it stands, then append them all, or none. Returns the stamped events."""
    past, staged, today = J.read(MODE), [], C.today()
    for ev in events:
        ev = dict(ev, at=C.stamp())
        if ev["e"] in ("trade", "rebase"):                      # neither reads a belief or forecast: no fold
            check(ev, {}, {}, today, past + staged)
            staged.append(ev)
            continue
        beliefs, preds, lessons = fold(past + staged)
        if ev["e"] == "predict":
            ev["id"] = f"F-{len(preds) + 1:04d}"
            if "test" in ev and ev["test"].get("belief") in beliefs:
                ev["test"] = dict(ev["test"], c=beliefs[ev["test"]["belief"]]["c"])
                ev["p"] = mix(ev["test"]["c"], ev["test"])
        elif ev["e"] == "lesson":
            ev["id"] = f"L-{len(lessons) + 1:04d}"
        elif ev["e"] == "function":
            ev["id"] = f"P-{len(functions(past + staged)) + 1:04d}"
        check(ev, beliefs, preds, today, past + staged)
        staged.append(ev)
    for ev in staged:
        J.append_line(MODE, today, ev)
    return staged


def score(p, v, y):
    if y is None:
        return {}
    if p["kind"] == "binary":
        return {"brier": (p["p"] - y) ** 2, "bits": -math.log2(p["p"] if y else 1 - p["p"])}
    return {"z": (v - p["q50"]) / ((p["q90"] - p["q10"]) / Z80)}


def settle(p, beliefs, v=None, y=None, evidence=None):
    """Append the resolution. y: binary = the event happened; interval = the value fell inside; None = VOID."""
    if v is not None:
        y = OPS[p["op"]](v, p["x"]) if p["kind"] == "binary" else p["q10"] <= v <= p["q90"]
    ev = {"e": "resolve", "id": p["id"], "at": C.stamp(), "value": v, "y": y, **score(p, v, y), **({"evidence": evidence} if evidence else {})}
    J.append_line(MODE, C.today(), ev)
    t = p.get("test")
    if t and y is not None:
        b = beliefs[t["belief"]]
        lt, lf = (t["p_true"], t["p_false"]) if y else (1 - t["p_true"], 1 - t["p_false"])
        c = min(C_MAX, max(C_MIN, b["c"] * lt / (b["c"] * lt + (1 - b["c"]) * lf)))
        J.append_line(MODE, C.today(), {"e": "belief", "id": b["id"], "at": C.stamp(), "c": round(c, 4), "was": b["c"],
                                        "because": f"{p['id']} resolved {'YES' if y else 'NO'} (p_true {t['p_true']}, p_false {t['p_false']})"})
        b["c"] = round(c, 4)
    return ev


def settle_due(today=None):
    """Resolve every open forecast whose window has closed. Returns the resolutions written."""
    today = today or C.today()
    beliefs, preds, _ = fold()
    rs, out = rows(), []
    for p in preds.values():
        if p["res"] is None and "m" in p:
            closed, v, _ = measure(p["m"], rs, today)
            if closed:
                out.append(settle(p, beliefs, v))
    return out


def missed(p):
    """A binary forecast that leaned the wrong way, or an interval the value fell outside."""
    y = p["res"]["y"] if p["res"] else None
    return y is not None and ((p["p"] >= 0.5) != y if p["kind"] == "binary" else not y)


def reading(p):
    """What the author said, before the outcome, this outcome would mean."""
    r = p["res"]
    if p["kind"] == "binary":
        return p["if_yes"] if r["y"] else p["if_no"]
    return "" if r["y"] else p["if_low"] if r["value"] < p["q10"] else p["if_high"]
