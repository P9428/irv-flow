# FORESIGHT — the loop that upgrades the model

The contract (prereg) answers one question in months: does FLOW clear the bar. This journal answers many
small ones in days: is the picture of the market that produced the contract any good. Every forecast is an
experiment on that picture, written before its window opens, settled by the machine, and the picture is
re-drawn from what settled. The record is `journal/foresight/`; the code is `src/foresight.py`; the pen is
`ops/predict.py`; step 6 of the loop (`ops/calibration_ledger.py`) resolves and reports.

## The cycle, once per loop

1. **RESOLVE** — the ledger settles every forecast whose window closed. Nobody chooses when or how.
2. **MISSES FIRST** — each miss is printed beside the reading its author committed to beforehand
   (`if_yes` / `if_no` / `if_low` / `if_high`). The reading was written blind, so it cannot be bent to fit.
3. **LESSON** — every miss gets one, by cause. A miss with no lesson is counted as owed.
4. **MODEL** — a belief under test has already moved by Bayes on its declared likelihoods. Any other
   revision is a new `belief` line with its `because`. A belief no open forecast can move is printed
   UNTESTED: that is a blind spot, and the next forecast is owed there.
5. **FORECAST AGAIN** — the next window, from the revised model. Each belief keeps exactly one open test.
6. **NEXT LEG** — a lesson with `owes` is debt. The next prereg lists every one as paid or declined, with why.

## The five causes of a miss — pick one, the most upstream that applies

| cause | the miss happened because | what it changes |
|---|---|---|
| instrument | the number measured is not the thing forecast (a proxy, a gap, a dead hunter) | the instrument, before any belief |
| model | a causal belief is wrong | that belief's credence, and every forecast built on it |
| regime | the belief was right for a market that has since changed | how far back evidence is trusted |
| calibration | direction right, width or confidence wrong | the forecaster's next intervals, nothing else |
| variance | inside the stated uncertainty; a 20 % event happened | nothing. Saying so is the lesson |

A hit for the wrong reason is a miss that got lucky: file the lesson anyway.

## Rules

- **Forward only.** A window opens the UTC day after the forecast is written or later; `add` refuses otherwise,
  and `tests/test_foresight.py` replays the whole journal against that rule. `seen` states what forward data
  the author had already read. The commit that carries the line, pushed, is the proof of order.
- **A resolution is a score, never a verdict.** IF-01 is decided only at its looks (prereg §6). Forecasts on
  FLOW outcomes exist to grade the model; nothing they return changes what the hunter does.
- **A lesson never moves a frozen parameter.** S1 stands: changing the rule spends the run. Lessons are for
  the next leg.
- **One open test per belief.** Two tests on overlapping evidence would move the credence twice for one fact.
- **Credence stays inside [0.02, 0.98].** A belief at 0 or 1 can no longer learn.
- **RULE 8 applies.** The operator runs `blind`, writes his number with `twin`, then reads the agent's. Two
  forecasters on one question is the only way to know whose judgment to weight on what.
- **Numbers are fractions** (0.01 = 1 %), days are full UTC days, populations are `all` (every reclaim),
  `base` (measurable curves), `flow` (the hunted trade). One row per mint.

## What a forecast looks like (`add` takes a JSON list of these)

```json
{"e": "belief", "id": "B9", "c": 0.6, "claim": "...", "because": "..."}
{"e": "predict", "who": "agent", "leg": "IF-01", "kind": "binary", "q": "...",
 "m": {"pop": "flow", "stat": "count", "from": "2026-10-04", "to": "2026-10-10"}, "op": "<=", "x": 14,
 "test": {"belief": "B9", "p_true": 0.9, "p_false": 0.3},
 "because": "...", "seen": "...", "if_yes": "...", "if_no": "..."}
{"e": "predict", "who": "agent", "leg": "IF-01", "kind": "interval", "q": "...", "q10": 0.5, "q50": 1.3, "q90": 3.0,
 "m": {"pop": "base", "stat": "frac", "field": "net_honest", "gt": 0, "from": "2026-10-04", "n": 500},
 "because": "...", "seen": "...", "if_low": "...", "if_high": "..."}
{"e": "lesson", "who": "agent", "on": ["F-0003"], "cause": "regime", "text": "...", "owes": "..."}
```

Without `test`, a binary forecast carries its own `p`. Without `m`, it carries `due` and `by` and is settled
with `resolve`, citing the artifact. Metric grammar: `measure()` in `src/foresight.py`.
