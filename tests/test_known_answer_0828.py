"""THE REPLICATION GATE. The engine must reproduce 2026-08-28 from mimicry's journal to a tee:
every signal, every exit branch, every mark, all 1,221 positions and all 226 winners.
Reads mimicry's captures and journal read-only. Fails on the first divergence."""
import glob
import json
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "lib"), os.path.join(ROOT, "ops")]
import captures as C          # noqa: E402
import rule as R              # noqa: E402

MIMICRY_JOURNAL = os.path.normpath(os.path.join(ROOT, "..", "mimicry", "journal", "mi11"))
DAY = "20260828"
EXPECTED_SIGNALS, EXPECTED_WINNERS = 1221, 226


@pytest.fixture(scope="module")
def ours():
    out = {}
    for cap in C.captures():
        if cap[3:11] != DAY:
            continue
        creates = list(C.stream(C.ROOT, cap, "creates.jsonl", ("mint", "timestamp")))
        trades = list(C.stream(C.ROOT, cap, "trades.jsonl", C.TRADE_FIELDS))
        for r in R.score_capture(creates, trades, cap):
            out[(cap, r["mint"])] = r
    return out


@pytest.fixture(scope="module")
def theirs():
    out = {}
    for f in glob.glob(os.path.join(MIMICRY_JOURNAL, f"mi-{DAY}*.jsonl")):
        cap = os.path.basename(f)[:-6]
        for l in open(f, encoding="utf-8"):
            r = json.loads(l)
            out[(cap, r["mint"])] = r
    return out


def test_mimicry_journal_present(theirs):
    assert len(theirs) == EXPECTED_SIGNALS


def test_every_signal_reproduced(ours, theirs):
    assert set(ours) == set(theirs), f"missing {len(set(theirs)-set(ours))}, extra {len(set(ours)-set(theirs))}"


def test_every_exit_and_mark_reproduced(ours, theirs):
    bad = []
    for k, t in theirs.items():
        o = ours[k]
        if o["why_zero"] != t["exit_branch"] or abs(o["net_zero"] - t["mark_net"]["approx"]) > 1e-9 \
                or o["t_entry_s"] != t["t_entry_s"] or abs(o["h1"] - t["h1"]["approx"]) > 1e-18:
            bad.append((k, o["why_zero"], t["exit_branch"], o["net_zero"], t["mark_net"]["approx"]))
    assert not bad, bad[:5]


def test_every_winner_reproduced(ours, theirs):
    w_theirs = {k for k, t in theirs.items() if t["mark_net"]["approx"] > 0}
    w_ours = {k for k, o in ours.items() if o["net_zero"] > 0}
    assert len(w_theirs) == EXPECTED_WINNERS
    assert w_ours == w_theirs


def test_day_net_reproduced(ours, theirs):
    assert abs(sum(o["net_zero"] for o in ours.values()) - sum(t["mark_net"]["approx"] for t in theirs.values())) < 1e-6


def test_flow_filter_counts_are_recorded(ours):
    """Descriptive, pinned so a silent change in the filters shows up here first."""
    flow = [o for o in ours.values() if o["flow"]]
    winners = [o for o in flow if o["net_zero"] > 0]
    pinned = json.load(open(os.path.join(ROOT, "prereg", "KNOWN_ANSWER_0828.json"), encoding="utf-8"))
    assert {"flow_signals": len(flow), "flow_winners": len(winners)} == pinned
