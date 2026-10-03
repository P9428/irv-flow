"""THE DIGEST — the operator's morning page: day, week, month. docs/digest.html, published as an artifact.

Built by the loop before the backup, so the push carries it; a cloud routine then publishes it (.claude/commands/digest.md).
Each horizon covers complete UTC days ending yesterday, shown in Central time, and reads in this order:
the bottom line · the hunted trade and its control, loss-first, on paper, each honest figure beside its haircut
figure · the market the filters fished in, and what they did to its winners · what the foresight journal resolved,
misses first, each laid on the market, the filters or the fill · where each belief stands. Above the horizons: what
needs the operator, and the open forecasts he has not answered, shown without anyone's numbers (rule 8). Below: what
resolves next. NOTHING ON THE PAGE IS A VERDICT; IF-01 and IF-02 are decided only at their looks (prereg §6).
"""
import html
import os
import statistics as st
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import common as C                        # noqa: E402
import foresight as F                     # noqa: E402
import market as MK                       # noqa: E402
import rule as R                          # noqa: E402
from calibration_ledger import brier, got  # noqa: E402
from constraint_scan import rulings_owed  # noqa: E402

CT = ZoneInfo("America/Chicago")
Z = R.Z_LAMPORTS / 1e9
LOOK1 = C.LOOKS[0][1]
HORIZONS = (("day", "Day", 1), ("week", "Week", 7), ("month", "Month", 30))
esc = html.escape

STYLE = """
/* layout: one reading column; a status header, what needs you, three horizons behind tabs, what resolves next */
:root{--bg:#f2f5f3;--panel:#ffffff;--fg:#17211e;--mute:#5b6964;--line:#d5ddd9;--accent:#0f6b5c;--good:#1d7a46;--warn:#946000;--bad:#b3261e;
--sans:"IBM Plex Sans",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Consolas,monospace;--cond:"IBM Plex Sans Condensed","IBM Plex Sans",system-ui,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f1513;--panel:#161e1b;--fg:#e1e9e5;--mute:#93a39c;--line:#2a3531;--accent:#63c7b0;--good:#63c58a;--warn:#e0a84a;--bad:#ef7d74;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0f1513;--panel:#161e1b;--fg:#e1e9e5;--mute:#93a39c;--line:#2a3531;--accent:#63c7b0;--good:#63c58a;--warn:#e0a84a;--bad:#ef7d74;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font:16px/1.55 var(--sans);padding-inline:16px;padding-block:28px 48px}
main{max-width:46rem;margin-inline:auto;display:flex;flex-direction:column;gap:22px}
h1{font:600 1.7rem/1.15 var(--cond);margin:0;text-wrap:balance}
h2{font:600 .78rem/1.2 var(--sans);letter-spacing:.09em;text-transform:uppercase;color:var(--mute);margin:0 0 8px}
p,ul{margin:0}ul{padding-left:1.15rem;display:flex;flex-direction:column;gap:6px}
.meta{color:var(--mute);font-size:.9rem}
.top{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center}
.pill{font:600 .78rem var(--mono);padding:3px 10px;border-radius:99px;border:1px solid currentColor}
.good{color:var(--good)}.warn{color:var(--warn)}.bad{color:var(--bad)}
.box{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:14px 16px}
.lead{font-size:1.06rem}
nav{display:flex;gap:6px;border-bottom:1px solid var(--line)}
nav button{font:600 .95rem var(--sans);color:var(--mute);background:none;border:0;border-bottom:3px solid transparent;padding:8px 14px;cursor:pointer}
nav button[aria-selected="true"]{color:var(--accent);border-bottom-color:var(--accent)}
nav button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
section{display:flex;flex-direction:column;gap:20px}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font:.86rem var(--mono);font-variant-numeric:tabular-nums}
th,td{padding:6px 10px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th{font:600 .72rem var(--sans);color:var(--mute)}
th:first-child,td:first-child{text-align:left;font-family:var(--sans);font-weight:600}
td.claim{white-space:normal;text-align:left;font-family:var(--sans);min-width:15rem}
.id{font:600 .85rem var(--mono);color:var(--accent)}
.note{color:var(--mute);font-size:.88rem}
footer{color:var(--mute);font-size:.82rem;border-top:1px solid var(--line);padding-top:12px}
"""

SCRIPT = """
const tabs=[...document.querySelectorAll('nav button')];
function show(k){tabs.forEach(b=>{const on=b.dataset.k===k;b.setAttribute('aria-selected',on);document.getElementById(b.dataset.k).hidden=!on})}
tabs.forEach(b=>b.addEventListener('click',()=>show(b.dataset.k)));
if(tabs.some(b=>b.dataset.k===location.hash.slice(1)))show(location.hash.slice(1));
const age=(Date.now()-Date.parse(document.body.querySelector('main').dataset.made))/36e5;
if(age>30){const s=document.getElementById('stale');s.hidden=false;s.textContent='This page is '+Math.round(age)+' hours old: the daily loop or its publish did not run.'}
"""


def ct(dt):
    d = dt.astimezone(CT)
    return f"{d:%a %b} {d.day}, {d.hour % 12 or 12}:{d:%M} {'am' if d.hour < 12 else 'pm'}"


def said(p):
    return f"{p['p'] * 100:.0f}% likely" if p["kind"] == "binary" else f"expected {p['q10']:g} to {p['q90']:g}"


def pct(x):
    return f"{x * 100:+.1f}%"


def stats(rs, cut=0.0):
    """Loss-first figures on the honest arm, every net moved by the haircut `cut` first; None when nothing filled."""
    v = [dict(r, net_honest=r["net_honest"] + cut) for r in rs if r.get("net_honest") is not None]
    if not v:
        return None
    w, l = [r for r in v if r["net_honest"] > 0], [r for r in v if r["net_honest"] <= 0]
    mw, ml = (st.mean(r["net_honest"] for r in x) if x else None for x in (w, l))
    return {"n": len(v), "won": len(w), "meanL": ml, "payoff": abs(mw / ml) if mw and ml else None,
            "holdL": st.median(r["hold_honest_s"] for r in l) if l else None, "holdW": st.median(r["hold_honest_s"] for r in w) if w else None,
            "worst": min(r["net_honest"] for r in v), "stop": sum(r["why_honest"] == "STOP" for r in v) / len(v),
            "mean": st.mean(r["net_honest"] for r in v), "sol": sum(r["net_honest"] for r in v) * Z}


def market(rs, cut):
    """The market the filters fished in, what they did to its winners, the excursion and the per-signal score, for one horizon."""
    s = MK.state(rs)
    if not s:
        return "<div><h2>The market, and what the filters did with it</h2><p class='note'>No measurable reclaim in this window.</p></div>"
    k, e, (most, least) = MK.kept(rs), MK.excursion(rs), MK.extremes(rs, 3)
    ps = F.per_signal(rs, F.functions())
    out = ["<div><h2>The market, and what the filters did with it</h2><div class='scroll'><table><tr><th></th><th>reclaims / day</th><th>won</th><th>avg</th>"
           "<th>targets</th><th>median buyers</th><th>median prints/s</th></tr>"
           f"<tr><td>BASE</td><td>{s['reclaims'] / len(MK.by_day(rs)):,.0f}</td><td>{'–' if s['win'] is None else f'{s['win'] * 100:.1f}%'}</td>"
           f"<td>{'–' if s['mean'] is None else pct(s['mean'])}</td><td>{s['targets']}</td><td>{s['buyers']:.0f}</td><td>{s['pace']:.2f}</td></tr></table></div>",
           f"<p>Of {k['targets']} target exits, FLOW kept {k['flow']} and RUN kept {k['run']}."
           + (f" Of {k['winners']} winners, {k['turned_away']} failed <b>{esc(k['filter'])}</b>, the filter that turned away the most." if k["winners"] else "") + "</p>",
           "<div class='scroll'><table><tr><th>paid most and least</th><th>net</th><th>exit</th><th>held</th><th>took</th><th style='text-align:left'>filters failed</th></tr>"]
    out += [f"<tr><td>{esc(r['mint'][:10])}</td><td>{pct(r['net_honest'])}</td><td>{esc(r['why_honest'])}</td><td>{r['hold_honest_s']}s</td><td>{MK.taken(r)}</td>"
            f"<td class='claim'>{esc(', '.join(MK.failed(r)) or 'none')}</td></tr>" for r in most + least[::-1]]
    out.append("</table></div>")
    out.append(f"<p>Excursion ({e['n']} fills): winners ran a median {pct(e['mfe_w'] or 0)} above entry, losers {pct(e['mfe_l'] or 0)} above and {pct(e['mae_l'] or 0)} below before the exit. "
               f"Of {e['stopped']} stops with later prints, {e['back_above_entry']} traded back above the entry and {e['to_target']} reached the target level.</p>" if e else
               "<p class='note'>Excursion and the 1 s / 2 s fills: no reclaim in this window carries them. The hunter records them from 2026-10-03 16:05 UTC on.</p>")
    out.append(f"<p>Per-signal forecast ({len(ps):,} reclaims): Brier {brier(ps, 2):.4f} against {brier(ps, 3):.4f} for the BASE running rate.</p>" if ps else
               "<p class='note'>Per-signal forecast: nothing scored in this window.</p>")
    out.append(f"<p class='note'>Diagnostic, not a verdict, and it moves no frozen filter. Haircut used above: {cut * 100:+.2f} pp.</p></div>")
    return "".join(out)


def trade_row(name, s):
    if not s:
        return f"<tr><td>{name}</td><td colspan='8'>no filled positions</td></tr>"
    dash = lambda x, f: "–" if x is None else f(x)                                    # noqa: E731
    slow = s["holdL"] is not None and s["holdW"] is not None and s["holdL"] > s["holdW"]
    return (f"<tr><td>{name}</td><td>{s['n']:,}</td><td>{dash(s['meanL'], pct)}</td><td>{dash(s['payoff'], lambda x: f'{x:.1f}×')}</td>"
            f"<td class='{'bad' if slow else ''}'>{dash(s['holdL'], lambda x: f'{x:.0f}s')} / {dash(s['holdW'], lambda x: f'{x:.0f}s')}</td>"
            f"<td>{pct(s['worst'])}</td><td>{s['stop'] * 100:.0f}%</td><td>{pct(s['mean'])}</td><td>{s['won']}/{s['n']}</td></tr>")


def horizon(key, days, rows, beliefs, preds, today, first_day, hidden, cut):
    d0, d1 = (today - timedelta(days=days)).isoformat(), (today - timedelta(days=1)).isoformat()
    since = (today - timedelta(days=days - 1)).isoformat()
    rs = [r for r in rows if d0 <= C.utc_day(F.entry(r)) <= d1]
    base = [r for r in rs if F.POPS["base"](r)]
    flow = [r for r in rs if F.POPS["flow"](r)]
    sf = stats(flow)
    start = datetime.combine(date.fromisoformat(d0), datetime.min.time(), timezone.utc)
    live_days = max(0, (date.fromisoformat(d1) - max(date.fromisoformat(d0), first_day)).days + 1) if first_day else 0
    res = [p for p in preds.values() if p["res"] and p["res"]["at"][:10] >= since]
    misses = [p for p in res if F.missed(p)]
    line = [f"The hunter closed reclaims in {len({F.entry(r) // 3600 for r in rs})} of {24 * live_days} hours." if live_days else "No complete day of hunting in this window yet.",
            f"{len(rs):,} reclaims, {len(base):,} on measurable curves, {len(flow)} FLOW.",
            f"FLOW on paper: {sf['won']} of {sf['n']} won, {sf['sol']:+.2f} SOL at {Z:g} SOL a signal." if sf else "No FLOW position was filled.",
            f"{len(res)} forecasts resolved, {len(misses)} missed." if res else "No forecast resolved."]
    out = [f"<section id='{key}'{' hidden' if hidden else ''}>",
           f"<p class='meta'>{ct(start)} to {ct(start + timedelta(days=days))} Central · {days} complete UTC day{'s' if days > 1 else ''}</p>",
           f"<p class='lead'>{esc(' '.join(line))}</p>",
           "<div><h2>The trade on paper, losses first (honest arm)</h2><div class='scroll'><table><tr><th></th><th>n</th><th>avg loss</th><th>payoff</th>"
           "<th>hold L / W</th><th>worst</th><th>stopped</th><th>avg</th><th>won</th></tr>"
           + trade_row("FLOW", sf) + trade_row("FLOW after haircut", stats(flow, cut))
           + trade_row("BASE (control)", stats(base)) + trade_row("BASE after haircut", stats(base, cut)) + "</table></div>"
           f"<p class='note'>Not a verdict. FLOW is decided only at n = 300 / 600 / 900 / 1,200, on the honest arm as frozen. "
           f"The haircut ({cut * 100:+.2f} pp) is what a real taker is expected to lose to latency and own impact on top of it.</p></div>",
           market(rs, cut),
           "<div><h2>Forecasts resolved, misses first</h2>"]
    if not res:
        out.append("<p class='note'>Nothing closed in this window.</p>")
    else:
        out.append("<ul>")
        for p in misses:
            lesson = " ".join(f"Lesson ({esc(l['cause'])}): {esc(l['text'])}" for l in p["lessons"]) or "<b class='warn'>Lesson owed.</b>"
            out.append(f"<li><span class='id'>{p['id']}</span> <b class='bad'>MISS</b> {esc(p['who'])} said {esc(said(p))}, got {esc(got(p))}. {esc(p['q'])}. "
                       f"<b>Laid on {{}}</b> ({{}}). ".format(*map(esc, F.blame(p, preds)))
                       + f"<span class='note'>Agreed beforehand to mean: {esc(F.reading(p))}</span> {lesson}</li>")
        out += [f"<li><span class='id'>{p['id']}</span> <b class='good'>{'VOID' if p['res']['y'] is None else 'HELD'}</b> {esc(p['who'])} said {esc(said(p))}, got {esc(got(p))}. {esc(p['q'])}</li>"
                for p in res if p not in misses]
        out.append("</ul>")
    out.append("</div><div><h2>The model: how sure we are of each belief</h2><div class='scroll'><table><tr><th></th><th>now</th><th>change</th><th>tested by</th><th style='text-align:left'>belief</th></tr>")
    for b in beliefs.values():
        was = next((c for at, c, _ in reversed(b["trail"]) if at[:10] < since), b["trail"][0][1])
        test = next((p["id"] for p in preds.values() if p["res"] is None and p.get("test", {}).get("belief") == b["id"]), None)
        out.append(f"<tr><td>{b['id']}</td><td>{b['c']:.2f}</td><td>{'–' if b['c'] == was else f'{b['c'] - was:+.2f}'}</td>"
                   f"<td>{test or '<span class=warn>untested</span>'}</td><td class='claim'>{esc(b['claim'])}</td></tr>")
    out.append("</table></div></div></section>")
    return "".join(out)


def main():
    today = date.fromisoformat(C.today())
    beliefs, preds, lessons = F.fold()
    rows = F.rows()
    first_day = date.fromisoformat(C.utc_day(F.entry(rows[0]))) if rows else None
    hb, age = C.heartbeat()
    alive = age < 120 and (hb or {}).get("connected", 0) > 0
    n = sum(1 for r in rows if F.POPS["flow"](r) and r.get("entry_honest") is not None)
    span = min(14, (today - first_day).days) if first_day else 0
    recent = sum(1 for r in rows if F.POPS["flow"](r) and (today - timedelta(days=span)).isoformat() <= C.utc_day(F.entry(r)) < today.isoformat())
    eta = f"about {(LOOK1 - n) * span / recent:,.0f} days at the pace of the last {span} day{'s' if span > 1 else ''}" if recent else "no pace yet"
    open_ = sorted((p for p in preds.values() if p["res"] is None), key=lambda p: p.get("m", {}).get("to") or p.get("due") or "9")
    needs = ([] if alive else ["<b class='bad'>The hunter is down.</b> No heartbeat in the last two minutes or no stream connected."])
    needs += [f"Write the lesson for <span class='id'>{p['id']}</span>: {esc(p['q'])}" for p in preds.values() if F.missed(p) and not p["lessons"]]
    needs += [f"Resolve <span class='id'>{p['id']}</span> by hand (due {p['due']}): {esc(p['q'])}" for p in open_ if "m" not in p and p["due"] < today.isoformat()]
    blind = [b["id"] for b in beliefs.values() if not any(p["res"] is None and p.get("test", {}).get("belief") == b["id"] for p in preds.values())]
    needs += [f"No open forecast can test {', '.join(blind)}. Until one can, that part of the model is taken on faith."] if blind else []
    rulings = rulings_owed()
    needs += [f"{len(rulings)} rulings owed: " + esc("; ".join(r.split(":")[0].split(" (")[0][:70] for r in rulings)) + "."] if rulings else []
    owed = [l for l in lessons if l.get("owes")]
    blind_q = F.untwinned(preds)
    hidden = {p["id"] for p in blind_q}
    h = MK.haircut(rows)
    now = datetime.now(timezone.utc)
    page = [f"<title>irv-flow Foresight Digest</title><link rel='stylesheet' href='https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Sans+Condensed:wght@600&display=swap'>",
            f"<style>{STYLE}</style><main data-made='{now.isoformat(timespec='seconds')}'>",
            f"<header><h1>irv-flow Foresight Digest</h1><p class='meta'>Made {ct(now)} Central by the daily loop · paper only, zero capital</p></header>",
            "<p id='stale' class='box bad' hidden></p>",
            f"<div class='top'><span class='pill {'good' if alive else 'bad'}'>HUNTER {'ALIVE' if alive else 'DOWN'}</span>"
            f"<span>Look 1: <b>{n} of {LOOK1}</b> FLOW fills, {eta}</span></div>",
            "<div class='box'><h2>Needs you</h2>" + ("<ul>" + "".join(f"<li>{x}</li>" for x in needs) + "</ul>" if needs else "<p>Nothing.</p>") + "</div>",
            "<div class='box'><h2>Yours to answer blind</h2>" + (
                f"<p class='note'>{len(blind_q)} open forecasts carry no number of yours. Nobody's numbers are shown for them anywhere on this page. "
                "Answer with <span class='id'>python ops/predict.py twin F-0000 …</span>, then read the agent's.</p><ul>"
                + "".join(f"<li><span class='id'>{p['id']}</span> {esc(F.measure(p['m'], rows, C.today())[2] if 'm' in p else 'by hand, due ' + p['due'])} · "
                          f"{'yes / no' if p['kind'] == 'binary' else 'low / middle / high'} · {esc(F.blind_q(p))}</li>" for p in blind_q) + "</ul>"
                if blind_q else "<p>Every open forecast has your number.</p>") + "</div>",
            f"<p class='note'>{esc(MK.haircut_text(h))}.</p>",
            "<nav role='tablist'>" + "".join(f"<button role='tab' data-k='{k}' aria-selected='{str(i == 0).lower()}'>{label}</button>" for i, (k, label, _) in enumerate(HORIZONS)) + "</nav>"]
    page += [horizon(k, days, rows, beliefs, preds, today, first_day, i > 0, h["total"]) for i, (k, _label, days) in enumerate(HORIZONS)]
    page.append("<div><h2>Resolves next</h2><ul>" + "".join(
        f"<li><span class='id'>{p['id']}</span> {esc(F.measure(p['m'], rows, C.today())[2] if 'm' in p else 'by hand, due ' + p['due'])} · {esc(p['who'])}: {'your answer first' if p['id'] in hidden else esc(said(p))} · {esc(F.blind_q(p) if p['id'] in hidden else p['q'])}</li>"
        for p in open_[:6]) + f"</ul><p class='note'>{len(open_)} forecasts open in all.</p></div>")
    if owed:
        page.append("<div><h2>The next leg owes</h2><ul>" + "".join(f"<li><span class='id'>{l['id']}</span> {esc(l['owes'])}</li>" for l in owed) + "</ul></div>")
    page.append(f"<footer>{esc(C.FOOTER)} A resolved forecast is a score on our model, never a verdict on the contract.</footer></main><script>{SCRIPT}</script>")
    out = os.path.join(C.ROOT, "docs", "digest.html")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(page))
    print(f"digest -> {out}")


if __name__ == "__main__":
    main()
