"""Gate: is the hunter alive? Exit 0 GREEN, 1 RED, one line either way.

RED if the heartbeat is older than RED_S, no stream is connected, or no event has arrived for RED_S.
The capture stream's age is reported for information only; the hunter does not depend on it.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import captures as CAP        # noqa: E402
import common as C            # noqa: E402

RED_S = 600


def main():
    hb, age = C.heartbeat()
    if hb is None:
        red, line = True, "HUNTER RED: no heartbeat file"
    else:
        quiet = time.time() - (hb.get("last_event") or 0)
        red = age > RED_S or quiet > RED_S or hb.get("connected", 0) == 0
        line = (f"HUNTER {'RED' if red else 'GREEN'}: heartbeat {age:.0f} s old, last event {quiet:.0f} s ago, streams up {hb.get('connected')}, "
                f"lag {hb.get('lag_s')} s, creates {hb.get('creates')} trades {hb.get('trades')} signals {hb.get('signals')} flow {hb.get('flow')} "
                f"closed {hb.get('closed')} drops {hb.get('drops')} watching {hb.get('watching')} open {hb.get('open')}")
    print(line)
    print(f"capture stream (informational): newest mimicry capture {CAP.newest_age_hours():.1f} h old")
    sys.exit(1 if red else 0)


if __name__ == "__main__":
    main()
