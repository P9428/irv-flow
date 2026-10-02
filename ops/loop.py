"""THE LOOP — one command that runs every one-job instrument in order. Same fleet shape as mimicry.

    1 freshness           IS THE HUNTER ALIVE                 reads no outcome; RED gates the reading
    2 constraint_scan     WHICH STAGE IS SLOWEST              by count; reads no outcome
    3 daily_monitor       IS THE RULE FIRING                  reads no outcome
    4 score               WRITE THE FORWARD-CAPTURE JOURNAL   write only
    5 readout             WHAT DID IT PRODUCE                 reads the outcome; non-actionable off-boundary
    6 calibration_ledger  ARE MY PRIORS ANY GOOD              resolved priors only
    7 suite               CAN THIS BOX STILL VERIFY ITSELF    full pytest, incl. the 08-28 replication gate
    8 backup              DO NOT LOSE THE DATA                push to origin; halts loudly on failure
    9 dashboard           MAKE IT VISIBLE                     renders the above

Freshness runs first because a reading over a dead hunter is noise. Backup runs before the
dashboard because losing data beats looking at it. THIS RUNNER DECIDES NOTHING: it executes
instruments and reports exit codes; every guard fires inside its instrument.
"""
import os
import subprocess
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import common as C            # noqa: E402
import journal as J           # noqa: E402

STEPS = (
    ("freshness.py", "is the hunter alive", False),
    ("constraint_scan.py", "which stage is slowest (by count)", False),
    ("daily_monitor.py", "is the rule firing (reads no outcome)", False),
    ("score.py", "write the forward-capture journal", False),
    ("readout.py", "what did it produce (non-actionable off-boundary)", False),
    ("calibration_ledger.py", "are my priors any good", False),
    ("suite.py", "can this box still verify itself", False),
    ("backup.py", "do not lose the data (push to origin)", True),
    ("dashboard.py", "make it visible", False),
)


def seal_yesterday():
    """Pin every live day-file older than today, once. Append-only; nothing is rewritten."""
    pinned = set()
    if os.path.exists(J.MANIFEST):
        with open(J.MANIFEST, encoding="utf-8") as fh:
            pinned = {line.rstrip("\n").split("  ", 1)[1] for line in fh}
    live = os.path.join(J.JOURNAL, "live")
    names = sorted(os.listdir(live)) if os.path.isdir(live) else []
    sealed = [f for f in names if f.endswith(".jsonl") and f[:-6] < C.today() and f"live/{f}" not in pinned]
    for f in sealed:
        J.pin(f"live/{f}")
    return sealed


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    lines = ["=" * 98, f"IRV-FLOW LOOP  {C.stamp()}", "=" * 98, f"  sealed: {', '.join(seal_yesterday()) or 'nothing new'}"]
    failed, status = [], {}
    for script, job, tolerate in STEPS:
        t0 = time.monotonic()
        r = subprocess.run([sys.executable, os.path.join(C.ROOT, "ops", script)], cwd=C.ROOT, env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        dt = time.monotonic() - t0
        bad = r.returncode != 0
        mark = "✅" if not bad else "⚠ " if tolerate else "⛔"
        if bad and not tolerate:
            failed.append(script)
        status[script] = {"rc": r.returncode, "s": round(dt, 1)}
        lines.append(f"  {mark} {script:22} {dt:6.1f}s  rc={r.returncode}  — {job}")
        if bad:
            lines += [f"        {ln[:110]}" for ln in r.stdout.splitlines() if ln.strip()][-3:]
            if r.stderr.strip():
                lines.append(f"        stderr: {r.stderr.strip().splitlines()[-1][:110]}")
    lines += ["", (f"  ⛔ {len(failed)} STEP(S) FAILED: {', '.join(failed)} — a failed instrument is a blind spot; fix it before trusting today's reading."
                   if failed else "  ✅ every instrument ran. out/readout.txt · out/constraint.txt · out/monitor.txt · out/dashboard.html"),
              "", "  ⛔ NOTHING HERE IS A VERDICT. IF-01's decision authority lives ONLY at n = 300 / 600 / 900 / 1,200 (prereg §6).", "=" * 98]
    text = "\n".join(lines)
    print(text)
    os.makedirs(C.MON, exist_ok=True)
    with open(os.path.join(C.MON, "loop.log"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write("\n" + text + "\n")
    C.write_json(os.path.join(C.MON, "loop-status.json"), {"stamp": C.stamp(), "steps": status, "failed": failed})
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
