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

## Where a miss is laid: the market, the filters, or the fill

Every metric forecast is one of three kinds, by what it measures (`kind()` in `src/foresight.py`):

| kind | measures | a miss is laid on |
|---|---|---|
| MARKET | `pop` all or base: the water every filter fishes in. Reclaims a day, BASE win rate and mean, target exits, median buyers and pace (`src/market.py`) | the market |
| SELECTION | `pop` flow or run | the market if the market forecast it named missed too; the filters if that one held |
| FILL | `fill_over_signal`, or any `x.*` field | the fill |

- **A FLOW or RUN forecast names the market forecast it is conditional on**: `"given": "F-0014"`. The pen refuses one
  without it. A forecast already in the journal without one takes a `given` line, allowed only before its window opens.
- The ledger and the digest print the assignment beside each miss. It is a reading of two scores, never a verdict, and
  it moves no filter: which filter turned away the most winners is debt for the next prereg, not a change to this one.
- **Per signal.** A `function` line fixes P(net_honest > 0) for every measurable reclaim from its `from` day, as a
  logistic on the entry-observable flags. It is scored by Brier against the BASE running rate (the win share of every
  measurable fill before that one). About 270 a day: the fast loop. A new function is a new line with a later `from`.
- **Excursion and the later fill** (`src/excursion.py`, field `x`): how far price ran for and against the honest entry
  before the exit and after it, and the fill and net one and two seconds after the signal. The live journal keeps no
  prints, so `x` exists only from the day the hunter writes `journal/after/` (`docs/loop/hunt-excursion.patch`);
  forward-only, read by no rule.
- **The haircut** (`market.haircut`): one standing number for honest arm minus real taker = latency + own impact.
  Seeded −3.70 pp (the operator's figure; not found in mimicry as a latency cost on 2026-10-03) and −6.25 % at 1 SOL
  (mimicry `out/mi86-create-own-impact.txt`); the latency half becomes the measured mean of `x.lag_2s` at 300 fills.
  The readout and the digest print every honest figure with it and without. Looks read the honest arm as frozen.

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
  forecasters on one question is the only way to know whose judgment to weight on what. The digest lists the open
  forecasts he has not answered and shows nobody's number for them.
- **Numbers are fractions** (0.01 = 1 %), days are full UTC days, populations are `all` (every reclaim),
  `base` (measurable curves), `flow` (the hunted trade), `run` (IF-02: measurable, 2–3× run band). One row per mint.

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
{"e": "given", "id": "F-0001", "on": "F-0011", "because": "..."}
{"e": "function", "who": "agent", "from": "2026-10-04", "spec": {"b": -1.77, "w": {"pace": 0.77, "...": 0}}, "because": "...", "seen": "..."}
```

A lesson is drawn from resolved forecasts, or from a stated belief (`"on": ["B5"]`) when the debt is known before
anything resolves. `count` and `per_day` with `gt` / `eq` count only the rows that hit (target exits a day).

Without `test`, a binary forecast carries its own `p`. Without `m`, it carries `due` and `by` and is settled
with `resolve`, citing the artifact. Metric grammar: `measure()` in `src/foresight.py`.
