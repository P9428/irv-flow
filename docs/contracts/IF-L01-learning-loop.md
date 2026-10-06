TASK — Every irv-flow trade becomes training data, and a challenger rule is refit on all of them every day, frozen
the day it is born and scored only on trades it never saw (IF-L01)

OBJECTIVE
Operator, 2026-10-06: "every trade in irv-flow should be recorded and used as training data to improve upon daily";
"a recursive learning loop that refines the model over time". GO 2026-10-06.
Ship `ops/learn.py`, a step of `ops/loop.py`, such that each daily run:
1. TABLE — writes `journal/train/<day>.jsonl` once for every finished UTC day not yet written: one row per measurable
   reclaim (BASE: standard path, honest fill) entered that day, entry-time features and outcomes, pinned in MANIFEST.
2. LEARN — fits one challenger on every table row entered before today and writes it once to
   `journal/learn/<today>.jsonl`, pinned: the rule, the training window, its training figures, the haircut it is
   scored with, and the sha256 of the rows it saw.
3. SHADOW — scores every challenger ever born on the trades entered on or after its birth day, and nothing earlier.
4. REPORT — writes `out/learn.txt`: the lineage, loss-first, each challenger beside BASE and FLOW on the same window
   and against the economic bar.
Measured by: `python ops/learn.py` exits 0 and is idempotent (a second run the same day writes nothing new);
`python -m pytest` green with the 08-28 gate; the run takes under 60 s on the full journal.

THE UNIT, THE FEATURES, THE OUTCOME (frozen by this contract; a change is IF-L02)
- Unit: one mint, `foresight.rows()`, BASE (`standard_path`) with `net_honest` not None. Day = UTC day of entry.
- Features: entry-time only, `features.*` from `src/rule.py` — age_s, run_x, buyers, n_pre, pace, buy_sol, sell_sol,
  big_buy_share, big_sell_share, dip_sellers, dip_top_share. Never an exit, a hold, an excursion (`x.*`) or a fill
  figure: a rule must be decidable at the signal.
- Outcome: `net` = net_honest + haircut, the haircut being `market.haircut` at the challenger's birth (own impact at
  1 SOL plus the measured latency). Break-even is net 0, which is the economic bar (docs/decisions/2026-10-06-economic-bar.md).

THE LEARNER (loss-first, the same family as the FLOW filters, so a promoted rule reads as a prereg)
- A challenger is a conjunction of at most 3 cuts `feature >= q` or `feature < q`, q from the training deciles.
- Objective: the drop-top-5 % mean of `net` (the lottery guard of IF-01 §5), never the plain mean.
- Greedy: add the cut that raises the objective most, kept only if it raises it in BOTH the earlier and the later half
  of the training window (by entry time) and leaves at least max(30, 5 %) of the training rows. Stop when none does.
- A challenger with no cut is recorded as such: nothing learned is a result.

RECURSION
Each day's training window is every trade before today, so it holds every day earlier challengers were shadowed on.
The report ranks the lineage by forward record; the next challenger starts from the data, never from a rival's cuts,
so a lucky rule cannot entrench itself.

PROMOTION (the only way a learned rule reaches money; the machine flags, the operator rules)
A challenger whose forward record reaches n >= 300 with mean net / SE >= 2.025 and drop-top-5 % mean > 0 is flagged
"IF-03 DRAFT OWED". That is a ruling owed (docs/loop/rulings-owed.md), not a verdict: the draft is a new prereg, frozen,
tested forward from its own FROZEN_AT, and run only on the operator's GO. Many challengers are born, so a flag is
expected by chance alone; the fresh prereg is what pays for that.

WHAT THIS NEVER DOES
- Moves an IF-01 or IF-02 parameter, look, bar or the hunter's rule (CLAUDE.md rules 2, 3, 8).
- Rewrites a table or challenger file once written (rule 6); the tables are derived from pinned live/after files and
  re-derive byte-identically, which `ops/learn.py verify` checks.
- Scores a challenger on a trade entered before its birth day.
- Places an order (rule 1).

VERIFY
`python ops/learn.py` twice (the second writes nothing) · `python ops/learn.py verify` exits 0 · `python -m pytest` green
· `out/learn.txt` leads with the loss-first figures · `python ops/loop.py` lists the learn step.
