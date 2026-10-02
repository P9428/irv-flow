"""What every instrument shares: paths, the UTC stamp, and one way to emit a report."""
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "out")
MON = os.path.join(ROOT, "monitor")
HEARTBEAT = os.path.join(MON, "hunt-heartbeat.json")
HUNT_LOG = os.path.join(MON, "hunt.log")
ALERTS = os.path.join(MON, "flow-alerts.log")
LOOKS = ((1, 300, 4.050), (2, 600, 2.864), (3, 900, 2.338), (4, 1200, 2.025))
BAR = 0.010370                      # +1.0370 % net per signal, inherited from M-MI-11 (prereg §5)
FLOW_RATE_SPENT = 3.5               # FLOW signals/day in the spent corpus (docs/findings/F01), a count not evidence
FOOTER = "ZERO CAPITAL. NO KEY. NO WALLET. NO ORDER. NO POSITION. MARKS, NOT MONEY."


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def utc_day(unix):
    return datetime.fromtimestamp(unix, timezone.utc).strftime("%Y-%m-%d")


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def heartbeat():
    """The hunter's last heartbeat and its age in seconds, or (None, inf)."""
    try:
        with open(HEARTBEAT, encoding="utf-8") as fh:
            return json.load(fh), datetime.now(timezone.utc).timestamp() - os.path.getmtime(HEARTBEAT)
    except (FileNotFoundError, ValueError):
        return None, float("inf")


def emit(name, lines):
    """Write out/<name>.txt and print it. Every instrument reports through here."""
    sys.stdout.reconfigure(encoding="utf-8")
    text = "\n".join(lines) + "\n"
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{name}.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(text, end="")


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=True)
    os.replace(tmp, path)


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, ValueError):
        return default
