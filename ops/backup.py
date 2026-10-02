"""THE BACKUP — the live journal is the one thing this program cannot rebuild; it goes off-machine.

The hunter's journal cannot be regenerated: a print the chain emitted and this machine missed is
gone. Code is in git; the forward-capture journal is derived from pinned captures. So the backup
is: commit journal/ docs/ prereg/ and PUSH to origin, then verify origin/master == HEAD. A push that
fails is a HALT with the reason printed, never a silent success.
"""
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def g(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")


def main():
    g("add", "journal", "docs", "prereg", "ops/SCHEDULES.md")
    if g("diff", "--cached", "--quiet").returncode:
        c = g("-c", "user.name=irvin", "-c", "user.email=irvin.1605@gmail.com", "commit", "-q", "-m",
              f"journal: {datetime.now(timezone.utc).strftime('%Y-%m-%d')} sealed and backed up")
        print("commit", "ok" if c.returncode == 0 else f"FAILED {c.stderr.strip()[:160]}")
    r = g("push", "-q", "origin", "master")
    if r.returncode:
        print(f"⛔ BACKUP HALT: push failed — {r.stderr.strip()[:200]}"); sys.exit(1)
    g("fetch", "-q", "origin")
    head, remote = g("rev-parse", "HEAD").stdout.strip(), g("rev-parse", "origin/master").stdout.strip()
    if head != remote:
        print(f"⛔ BACKUP HALT: origin/master {remote[:8]} != HEAD {head[:8]}"); sys.exit(1)
    print(f"backup ok: origin/master == HEAD {head[:8]}")


if __name__ == "__main__":
    main()
