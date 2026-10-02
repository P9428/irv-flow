"""THE SUITE GATE — can this box still verify itself. Runs the full pytest and records the result.
The constraint scan reads out/suite.json as stage 6 MACHINE; a red suite is a blind spot by definition."""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "out", "suite.json")


def main():
    r = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    summary = [l for l in (r.stdout or "").splitlines() if l.strip()][-1:] or [""]
    rec = {"stamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "rc": r.returncode, "summary": summary[0]}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(rec, open(OUT, "w", encoding="utf-8"), indent=1)
    print(f"SUITE rc={r.returncode}: {summary[0]}")
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
