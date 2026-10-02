"""THE BACKUP — the live journal cannot be rebuilt; it goes off-machine every day.

Commit journal/ docs/ prereg/, push to origin, verify origin/master == HEAD. A failed push is a
HALT with its reason printed, never a silent success.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import common as C            # noqa: E402

AUTHOR = ("-c", "user.name=irvin", "-c", "user.email=irvin.1605@gmail.com")


def git(*args):
    return subprocess.run(["git", *args], cwd=C.ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")


def main():
    git("add", "journal", "docs", "prereg", "ops/SCHEDULES.md")
    if git("diff", "--cached", "--quiet").returncode:
        c = git(*AUTHOR, "commit", "-q", "-m", f"journal: {C.today()} sealed and backed up")
        print("commit", "ok" if c.returncode == 0 else f"FAILED {c.stderr.strip()[:160]}")
    push = git("push", "-q", "origin", "master")
    if push.returncode:
        print(f"⛔ BACKUP HALT: push failed — {push.stderr.strip()[:200]}")
        sys.exit(1)
    git("fetch", "-q", "origin")
    head, remote = git("rev-parse", "HEAD").stdout.strip(), git("rev-parse", "origin/master").stdout.strip()
    if head != remote:
        print(f"⛔ BACKUP HALT: origin/master {remote[:8]} != HEAD {head[:8]}")
        sys.exit(1)
    print(f"backup ok: origin/master == HEAD {head[:8]}")


if __name__ == "__main__":
    main()
