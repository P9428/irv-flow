---
description: Run the irv-flow battery (nine instruments), then the constraint scan and the kill scan, and report
---

Run the battery, then scan, then report. Same engine as mimicry's loop.

```bash
cd /c/Users/newce/irv-flow && python ops/loop.py
```

Then read, in this order, and do not skip one: `out/readout.txt`, `out/constraint.txt`, `out/monitor.txt`,
`out/calibration.txt`, the last 10 lines of `monitor/flow-alerts.log`, `monitor/loop-status.json`.

Then perform `docs/loop/constraint.md` (the binding-constraint scan, six-line output) and
`docs/loop/kill-scan.md` (eight passes; "nothing new today" is the expected answer most days), grounding
every item in a file, count, hash or git state. `CALIBRATION` for priors is `prereg/PRIORS.json`.

Report, briefly and in this order:
1. **Hunter** — alive or down, drops, mints watched, reclaims, FLOW signals today and per day.
2. **Loss-first panel** for FLOW honest arm — meanL, payoff, hold on losers vs winners, worst, stop share — then the mean, median, drop-top-5 %, and n toward the next look. Say plainly "NOT A VERDICT" unless a look fired.
3. **The constraint** — the one stage the scan named, by count, and the single move completable today.
4. **Kill scan** — the items that are real, or "nothing new today" with what was checked.
5. **Backup** — whether origin/master == HEAD.

Rules: no figure from the spent corpus may be cited as evidence. No verdict off a look boundary. Do not propose
work below the binding constraint. Report and STOP; no contract, no amendment, no starting the move.
