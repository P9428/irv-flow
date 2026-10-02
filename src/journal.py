"""Append-only journal. One file per capture (batch) or per UTC day (live); pin-last MANIFEST.

A file is written whole to .part and renamed, so a crash never leaves a half journal. Once a
file exists it is never rewritten (NO BACKFILL). The MANIFEST line is the sha256 of the bytes
the reader will see; tests re-hash on read.
"""
import hashlib
import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
JOURNAL = os.path.join(ROOT, "journal")
MANIFEST = os.path.join(JOURNAL, "MANIFEST")


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pin(relpath):
    with open(MANIFEST, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(f"{_sha(os.path.join(JOURNAL, relpath))}  {relpath}\n")


def write_file(mode, name, records):
    """journal/<mode>/<name>.jsonl, whole, once. Returns path or None if it already exists."""
    d = os.path.join(JOURNAL, mode)
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, f"{name}.jsonl")
    if os.path.exists(out):
        return None
    tmp = out + ".part"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        for r in records:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    os.replace(tmp, out)
    pin(f"{mode}/{name}.jsonl")
    return out


def append_line(mode, name, record):
    """Live journal: one closed position per line, fsynced. Sealed (pinned) by ops/loop.py next day."""
    d = os.path.join(JOURNAL, mode)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{name}.jsonl"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def read(mode):
    d = os.path.join(JOURNAL, mode)
    if not os.path.isdir(d):
        return []
    out = []
    for f in sorted(os.listdir(d)):
        if f.endswith(".jsonl"):
            with open(os.path.join(d, f), encoding="utf-8") as fh:
                out.extend(json.loads(l) for l in fh if l.strip())
    return out


def verify():
    """(ok, [(relpath, status)]) over every MANIFEST line."""
    if not os.path.exists(MANIFEST):
        return True, []
    rows, ok = [], True
    for line in open(MANIFEST, encoding="utf-8"):
        sha, rel = line.rstrip("\n").split("  ", 1)
        p = os.path.join(JOURNAL, rel)
        st = "OK" if os.path.exists(p) and _sha(p) == sha else "MISMATCH"
        ok &= st == "OK"
        rows.append((rel, st))
    return ok, rows
