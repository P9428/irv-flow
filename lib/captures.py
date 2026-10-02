"""Read-only stream over ~/mimicry/snapshots.

The captures are mimicry's artifact. This module opens them for reading only; tests/test_wall.py
walks its AST and fails if any write-capable call appears. Nothing here is cached whole: a
capture's trades are yielded one record at a time, projected to the fields the rule reads.
"""
import gzip
import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", "mimicry", "snapshots"))
TRADE_FIELDS = ("mint", "timestamp", "slot", "is_buy", "sol_amount", "token_amount", "user",
                "virtual_sol_reserves", "virtual_token_reserves", "real_sol_reserves",
                "sol_offset_standard", "invariant_ok")


def captures(root=ROOT):
    """Every capture directory that holds a creates payload, sorted by id (= by time)."""
    if not os.path.isdir(root):
        return ()
    return tuple(sorted(d for d in os.listdir(root)
                        if os.path.isdir(os.path.join(root, d))
                        and (os.path.exists(os.path.join(root, d, "creates.jsonl"))
                             or os.path.exists(os.path.join(root, d, "creates.jsonl.gz")))))


def payload_path(root, capture, name):
    plain = os.path.join(root, capture, name)
    if os.path.exists(plain):
        return plain, False
    return plain + ".gz", True


def stream(root, capture, name, fields=None):
    path, is_gz = payload_path(root, capture, name)
    opener = gzip.open if is_gz else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            o = json.loads(line)
            yield {k: o.get(k) for k in fields} if fields else o


def day_of(capture):
    """mi-20260828T1236Z -> 2026-08-28."""
    return f"{capture[3:7]}-{capture[7:9]}-{capture[9:11]}"


def newest_age_hours(root=ROOT, now=None):
    import time
    caps = captures(root)
    if not caps:
        return float("inf")
    c = caps[-1]
    from datetime import datetime, timezone
    ts = datetime.strptime(c[3:16], "%Y%m%dT%H%M").replace(tzinfo=timezone.utc).timestamp()
    return ((now or time.time()) - ts) / 3600
