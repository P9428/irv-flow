"""THE DASHBOARD — the production line, visible. Regenerates out/dashboard.html from the other instruments' outputs."""
import html
import json
import os
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "out", "dashboard.html")
FILES = (("readout", "out/readout.txt"), ("constraint", "out/constraint.txt"), ("monitor", "out/monitor.txt"),
         ("calibration", "out/calibration.txt"), ("flow alerts", "monitor/flow-alerts.log"))


def rd(rel, tail=None):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return "(none yet)"
    lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
    return "\n".join(lines[-tail:] if tail else lines)


def main():
    try:
        hb = json.load(open(os.path.join(ROOT, "monitor", "hunt-heartbeat.json"), encoding="utf-8"))
        alive = time.time() - os.path.getmtime(os.path.join(ROOT, "monitor", "hunt-heartbeat.json")) < 120 and hb.get("connected")
    except (FileNotFoundError, ValueError):
        hb, alive = {}, False
    pill = f'<span class="pill {"g" if alive else "r"}">HUNTER {"ALIVE" if alive else "DOWN"}</span>'
    body = "".join(f"<h2>{html.escape(n)}</h2><pre>{html.escape(rd(rel, 40 if n == 'flow alerts' else None))}</pre>" for n, rel in FILES)
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>irv-flow</title>
<style>body{{font:14px/1.4 ui-monospace,Consolas,monospace;background:#111;color:#ddd;margin:24px}}
h1{{font-size:18px}}h2{{font-size:14px;color:#9cf;margin-top:28px}}pre{{white-space:pre-wrap;background:#181818;padding:12px;border:1px solid #333}}
.pill{{padding:3px 10px;border-radius:12px;font-weight:bold}}.g{{background:#153}}.r{{background:#622}}</style></head><body>
<h1>irv-flow — IF-01 {pill} <small>{datetime.now(timezone.utc).isoformat(timespec='seconds')}</small></h1>
<p>signals {hb.get('signals')} · flow {hb.get('flow')} · closed {hb.get('closed')} · open {hb.get('open')} · watching {hb.get('watching')} · drops {hb.get('drops')}</p>
<p><b>ZERO CAPITAL. NO KEY. NO WALLET. NO ORDER. NO POSITION. MARKS, NOT MONEY. Nothing here is a verdict off a look boundary.</b></p>
{body}</body></html>"""
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8", newline="\n").write(page)
    print(f"dashboard -> {OUT}")


if __name__ == "__main__":
    main()
