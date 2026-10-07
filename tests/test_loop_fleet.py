"""The fleet is complete, the monitor reads no outcome, the priors are on the ledger."""
import json
import os
import re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUTCOME_TOKENS = ("net_zero", "net_honest", "why_zero", "why_honest", "exit_zero", "exit_honest", "mark_net", "win", "meanL", "meanW")


def test_every_loop_step_exists():
    src = open(os.path.join(ROOT, "ops", "loop.py"), encoding="utf-8").read()
    steps = re.findall(r'\("([a-z_]+\.py)", "', src)
    assert len(steps) == 11
    for s in steps:
        assert os.path.isfile(os.path.join(ROOT, "ops", s)), s


def test_daily_monitor_and_constraint_scan_read_no_outcome():
    for f in ("daily_monitor.py", "constraint_scan.py"):
        src = open(os.path.join(ROOT, "ops", f), encoding="utf-8").read()
        body = src.split('"""', 2)[2]                       # past the docstring, which may name what it avoids
        for tok in OUTCOME_TOKENS:
            assert tok not in body, (f, tok)


def test_priors_ledger_matches_prereg():
    pr = json.load(open(os.path.join(ROOT, "prereg", "PRIORS.json"), encoding="utf-8"))
    ids = [x["id"] for x in pr]
    assert ids == sorted(set(ids)) and all(0 < x["p"] < 1 for x in pr) and all("resolves" in x for x in pr)
    text = open(os.path.join(ROOT, "prereg", "IF-01-PREREGISTRATION.md"), encoding="utf-8").read()
    for x in pr:
        assert f"{x['p']:.2f}" in text, x["id"]


def test_loop_command_runs_the_battery():
    cmd = open(os.path.join(ROOT, ".claude", "commands", "loop.md"), encoding="utf-8").read()
    assert "python ops/loop.py" in cmd and "docs/loop/constraint.md" in cmd and "docs/loop/kill-scan.md" in cmd


def test_loop_status_if_present_has_every_step():
    p = os.path.join(ROOT, "monitor", "loop-status.json")
    if os.path.exists(p):
        st = json.load(open(p, encoding="utf-8"))
        src = open(os.path.join(ROOT, "ops", "loop.py"), encoding="utf-8").read()
        assert sorted(st["steps"]) == sorted(re.findall(r'\("([a-z_]+\.py)", "', src))
