"""THE SUITE GATE — can this box still verify itself. Full pytest, result recorded for the constraint scan."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import common as C            # noqa: E402


def main():
    r = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=C.ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    summary = next((line for line in reversed(r.stdout.splitlines()) if line.strip()), "")
    C.write_json(os.path.join(C.OUT, "suite.json"), {"stamp": C.stamp(), "rc": r.returncode, "summary": summary})
    print(f"SUITE rc={r.returncode}: {summary}")
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
