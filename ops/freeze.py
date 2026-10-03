"""THE PIN.   python ops/freeze.py IF-02

The first run freezes the contract: prereg/<ID>-FROZEN_AT = now (UTC) and prereg/<ID>-FROZEN_SHA = the
sha256 of prereg/<ID>-PREREGISTRATION.md. Every mint created at or before FROZEN_AT is SPENT for it.
Any later run is the re-pin after an AMENDMENT section: the sha moves, FROZEN_AT never does.
IF-01 predates this script and keeps its own pins (prereg/FROZEN_SHA, prereg/FROZEN_AT).
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import common as C            # noqa: E402


def main(contract):
    base = os.path.join(C.ROOT, "prereg", contract)
    with open(f"{base}-PREREGISTRATION.md", "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    if C.frozen_at(contract) is None:
        with open(f"{base}-FROZEN_AT", "x", encoding="utf-8", newline="\n") as fh:
            fh.write(C.stamp() + "\n")
    with open(f"{base}-FROZEN_SHA", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(sha + "\n")
    print(f"{contract} frozen at {C.frozen_at(contract).isoformat()}  sha256 {sha}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] == "IF-01":
        sys.exit(__doc__)
    main(sys.argv[1])
