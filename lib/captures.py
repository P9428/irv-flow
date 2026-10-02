"""Read-only stream over ~/mimicry/snapshots.

The captures are mimicry's artifact. This module only reads them; tests/test_zero_capital_and_wall.py
walks its AST and fails on any write-capable call. A capture is yielded one record at a time,
projected to the fields the rule reads.
"""
import gzip
import json
import os
import re
import time
from datetime import datetime, timezone

CAPTURE_ID = re.compile(r"mi-\d{8}T\d{4}Z")          # anything else under snapshots/ (probes, unpinned/) is not a capture
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mimicry", "snapshots"))
TRADE_FIELDS = ("mint", "timestamp", "slot", "is_buy", "sol_amount", "token_amount", "user",
                "virtual_sol_reserves", "virtual_token_reserves", "real_sol_reserves", "sol_offset_standard", "invariant_ok")


def captures(root=ROOT):
    """Every capture directory holding a creates payload, sorted by id, which is by time."""
    if not os.path.isdir(root):
        return ()
    return tuple(sorted(d for d in os.listdir(root) if CAPTURE_ID.fullmatch(d)
                        and any(os.path.exists(os.path.join(root, d, n)) for n in ("creates.jsonl", "creates.jsonl.gz"))))


def payload_path(root, capture, name):
    plain = os.path.join(root, capture, name)
    return (plain, False) if os.path.exists(plain) else (plain + ".gz", True)


def stream(root, capture, name, fields=None):
    path, is_gz = payload_path(root, capture, name)
    with (gzip.open if is_gz else open)(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                o = json.loads(line)
                yield {k: o.get(k) for k in fields} if fields else o


def day_of(capture):
    return f"{capture[3:7]}-{capture[7:9]}-{capture[9:11]}"


def newest_age_hours(root=ROOT):
    caps = captures(root)
    if not caps:
        return float("inf")
    ts = datetime.strptime(caps[-1][3:16], "%Y%m%dT%H%M").replace(tzinfo=timezone.utc).timestamp()
    return (time.time() - ts) / 3600
