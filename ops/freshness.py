"""Gate: is the hunter alive? Exit 0 GREEN, 1 RED. Prints one line either way.

RED if monitor/hunt-heartbeat.json is older than RED_S, or the hunter has seen no event for
RED_S while claiming to be connected. The capture stream's age is reported for information
only; the hunter does not depend on it.
"""
import json
import os
import sys
import time

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "lib")]
import captures as C          # noqa: E402

HB = os.path.join(ROOT, "monitor", "hunt-heartbeat.json")
RED_S = 600


def main():
    now = time.time()
    try:
        hb = json.load(open(HB, encoding="utf-8"))
        age = now - os.path.getmtime(HB)
        quiet = now - (hb.get("last_event") or 0)
        red = age > RED_S or quiet > RED_S
        print(f"HUNTER {'RED' if red else 'GREEN'}: heartbeat {age:.0f} s old, last event {quiet:.0f} s ago, "
              f"creates {hb.get('creates')} trades {hb.get('trades')} signals {hb.get('signals')} flow {hb.get('flow')} "
              f"closed {hb.get('closed')} drops {hb.get('drops')} watching {hb.get('watching')} open {hb.get('open')}")
    except (FileNotFoundError, ValueError):
        red = True
        print("HUNTER RED: no heartbeat file")
    print(f"capture stream (informational): newest mimicry capture {C.newest_age_hours():.1f} h old")
    sys.exit(1 if red else 0)


if __name__ == "__main__":
    main()
