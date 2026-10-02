"""THE DASHBOARD — the production line, visible. Regenerates out/dashboard.html from the instruments' outputs."""
import html
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import common as C            # noqa: E402

PANELS = (("readout", os.path.join(C.OUT, "readout.txt"), None), ("constraint", os.path.join(C.OUT, "constraint.txt"), None),
          ("monitor", os.path.join(C.OUT, "monitor.txt"), None), ("calibration", os.path.join(C.OUT, "calibration.txt"), None),
          ("flow alerts", C.ALERTS, 40))
STYLE = ("body{font:14px/1.4 ui-monospace,Consolas,monospace;background:#111;color:#ddd;margin:24px}h1{font-size:18px}"
         "h2{font-size:14px;color:#9cf;margin-top:28px}pre{white-space:pre-wrap;background:#181818;padding:12px;border:1px solid #333}"
         ".pill{padding:3px 10px;border-radius:12px;font-weight:bold}.g{background:#153}.r{background:#622}")


def text_of(path, tail):
    if not os.path.exists(path):
        return "(none yet)"
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    return "\n".join(lines[-tail:] if tail else lines)


def main():
    hb, age = C.heartbeat()
    hb = hb or {}
    alive = age < 120 and hb.get("connected", 0) > 0
    panels = "".join(f"<h2>{html.escape(n)}</h2><pre>{html.escape(text_of(p, t))}</pre>" for n, p, t in PANELS)
    page = (f'<!doctype html><html><head><meta charset="utf-8"><title>irv-flow</title><style>{STYLE}</style></head><body>'
            f'<h1>irv-flow — IF-01 <span class="pill {"g" if alive else "r"}">HUNTER {"ALIVE" if alive else "DOWN"}</span> <small>{C.stamp()}</small></h1>'
            f"<p>signals {hb.get('signals')} · flow {hb.get('flow')} · closed {hb.get('closed')} · open {hb.get('open')} · "
            f"watching {hb.get('watching')} · drops {hb.get('drops')} · lag {hb.get('lag_s')} s</p>"
            f"<p><b>{C.FOOTER} Nothing here is a verdict off a look boundary.</b></p>{panels}</body></html>")
    os.makedirs(C.OUT, exist_ok=True)
    out = os.path.join(C.OUT, "dashboard.html")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    print(f"dashboard -> {out}")


if __name__ == "__main__":
    main()
