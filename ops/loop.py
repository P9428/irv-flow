"""THE LOOP — one command that runs every one-job instrument in order. Same fleet shape as mimicry.

THE FLEET, each deliberately narrow:

    1 freshness            IS THE HUNTER ALIVE            reads no outcome; RED gates the reading
    2 constraint_scan      WHICH STAGE IS SLOWEST         by COUNT; reads no outcome
    3 daily_monitor        IS THE RULE FIRING             reads no outcome, AST-fenced
    4 score                WRITE THE FORWARD-CAPTURE JOURNAL (WRITE ONLY)
    5 readout              WHAT DID IT PRODUCE            reads the outcome, NON-ACTIONABLE off-boundary
    6 calibration_ledger   ARE MY PRIORS ANY GOOD         resolved priors only
    7 suite                CAN THIS BOX STILL VERIFY ITSELF   full pytest, incl. the 08-28 replication gate
    8 backup               DO NOT LOSE THE DATA           off-machine = origin; HALTS loudly if the push fails
    9 dashboard            MAKE IT VISIBLE                renders the above

ORDER MATTERS. Freshness first because a reading over a dead hunter is noise. Backup before the
dashboard because losing data beats looking at it.

⛔ THIS RUNNER DECIDES NOTHING. It executes instruments and reports exit codes. Every guard fires
inside its instrument. The verdict lives only at the four n-boundaries in prereg §6.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(_HERE, ".."))
sys.path[:0] = [os.path.join(REPO, "src")]
import journal as J           # noqa: E402

LOG = os.path.join(REPO, "monitor", "loop.log")
STATUS = os.path.join(REPO, "monitor", "loop-status.json")

STEPS = (
    ("freshness.py", "⛔ IS THE HUNTER ALIVE", False),
    ("constraint_scan.py", "which stage is slowest (by count)", False),
    ("daily_monitor.py", "is the rule firing (reads no outcome)", False),
    ("score.py", "write the forward-capture journal (WRITE ONLY)", False),
    ("readout.py", "what did it produce (NON-ACTIONABLE off-boundary)", False),
    ("calibration_ledger.py", "are my priors any good", False),
    ("suite.py", "can this box still verify itself", False),
    ("backup.py", "do not lose the data (push to origin)", True),
    ("dashboard.py", "make it visible", False),
)


def seal_yesterday():
    """Pin every live day-file older than today exactly once. Append-only, never rewritten."""
    pinned = {l.rstrip("\n").split("  ", 1)[1] for l in open(J.MANIFEST, encoding="utf-8")} if os.path.exists(J.MANIFEST) else set()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    live = os.path.join(J.JOURNAL, "live")
    sealed = []
    if os.path.isdir(live):
        for f in sorted(os.listdir(live)):
            if f.endswith(".jsonl") and f[:-6] < today and f"live/{f}" not in pinned:
                J.pin(f"live/{f}"); sealed.append(f)
    return sealed


def main():
    out = []

    def say(s=""):
        out.append(s); print(s, flush=True)

    sys.stdout.reconfigure(encoding="utf-8")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    say("=" * 98); say(f"IRV-FLOW LOOP  {stamp}"); say("=" * 98)
    say(f"  sealed: {', '.join(seal_yesterday()) or 'nothing new'}")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    failed, status = [], {"stamp": stamp, "steps": {}}
    for script, job, tolerate in STEPS:
        path = os.path.join(_HERE, script)
        if not os.path.isfile(path):
            say(f"  ⛔ MISSING  {script:22} — {job}"); failed.append(script); status["steps"][script] = "MISSING"; continue
        t0 = time.monotonic()
        r = subprocess.run([sys.executable, path], cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        dt = time.monotonic() - t0
        mark = "✅" if r.returncode == 0 else ("⚠ " if tolerate else "⛔")
        if r.returncode and not tolerate:
            failed.append(script)
        status["steps"][script] = {"rc": r.returncode, "s": round(dt, 1)}
        say(f"  {mark} {script:22} {dt:6.1f}s  rc={r.returncode}  — {job}")
        if r.returncode:
            for ln in [ln for ln in (r.stdout or "").splitlines() if ln.strip()][-3:]:
                say(f"        {ln[:110]}")
            if r.stderr and r.stderr.strip():
                say(f"        stderr: {r.stderr.strip().splitlines()[-1][:110]}")
    say("")
    if failed:
        say(f"  ⛔ {len(failed)} STEP(S) FAILED: {', '.join(failed)} — a failed instrument is a blind spot; fix it before trusting today's reading.")
    else:
        say("  ✅ every instrument ran. out/readout.txt · out/constraint.txt · out/monitor.txt · out/dashboard.html")
    say("")
    say("  ⛔ NOTHING HERE IS A VERDICT. IF-01's decision authority lives ONLY at n = 300 / 600 / 900 / 1,200 (prereg §6).")
    say("=" * 98)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8", newline="\n") as fh:
        fh.write("\n" + "\n".join(out) + "\n")
    status["failed"] = failed
    with open(STATUS, "w", encoding="utf-8") as fh:
        json.dump(status, fh, indent=1, sort_keys=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
