"""The daily loop: seal yesterday's live journal, score any forward captures, gate, read out.
Exit 1 if the hunter is RED so the scheduled task's LastResult shows it."""
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "src")]
import journal as J           # noqa: E402

PY = sys.executable


def seal_yesterday():
    """Pin every live day-file older than today exactly once."""
    pinned = {l.rstrip("\n").split("  ", 1)[1] for l in open(J.MANIFEST, encoding="utf-8")} if os.path.exists(J.MANIFEST) else set()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    live = os.path.join(J.JOURNAL, "live")
    if not os.path.isdir(live):
        return
    for f in sorted(os.listdir(live)):
        if f.endswith(".jsonl") and f[:-6] < today and f"live/{f}" not in pinned:
            J.pin(f"live/{f}")
            print(f"sealed live/{f}")


def run(name):
    r = subprocess.run([PY, os.path.join(ROOT, "ops", name)], capture_output=True, text=True)
    print(r.stdout.rstrip())
    if r.stderr.strip():
        print(r.stderr.rstrip())
    return r.returncode


def push_journal():
    """Commit and push the journal and finding files so a dead laptop never loses a day. Record only."""
    g = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)
    g("add", "journal", "docs", "prereg")
    if g("diff", "--cached", "--quiet").returncode:
        g("-c", "user.name=irvin", "-c", "user.email=irvin.1605@gmail.com", "commit", "-q", "-m",
          f"journal: {datetime.now(timezone.utc).strftime('%Y-%m-%d')} sealed")
    r = g("push", "-q", "origin", "master")
    print("push", "ok" if r.returncode == 0 else f"FAILED: {r.stderr.strip()[:200]}")


def main():
    print("IRV-FLOW LOOP", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    seal_yesterday()
    run("score.py")
    red = run("freshness.py")
    run("readout.py")
    push_journal()
    sys.exit(1 if red else 0)


if __name__ == "__main__":
    main()
