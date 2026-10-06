TASK — Build irv-flow's own morning scan: one command that reproduces yesterday's close of the repo, re-checks only what could have changed, names the repo's single constraint from today's observations and writes the Highest Leverage Move before any contract fires (MR-01, irv-flow)

THE FIRST LAW (operator, 2026-10-06; outranks every line below)
Reality is the final authority. Your reasoning is a model of reality, not reality itself. When the model and
observed reality disagree, preserve the observation and revise the model.
In this repo the "model" is everything written before the observation: yesterday's close, the preregs' priors
(IF-01 §8, IF-02 §8, `prereg/PRIORS.json`), the spent-corpus baseline (`docs/findings/F01-spent-baseline.md`),
the foresight beliefs, the IF-L01 challengers, and the constraint scan's expectation of rates. The
"observation" is what the chain delivered to the hunter: `journal/live/`, `journal/after/`, `journal/gaps/`,
the heartbeat, `out/looks*.json`. Mechanized as: an observation is written once, append-only, pinned in
`journal/MANIFEST` (rule 6), never edited, rounded away or dropped to make a check pass. A disagreement is
closed only by revising the model, and here a revision can never touch a frozen prereg (rule 2): it is a new
foresight belief (`ops/predict.py`), a debt line for the next prereg (rule 8), a code fix with its commit, a
corrected close line citing the old one, or an operator ruling through RI (`ops/decide.py`). A prior that the
record contradicts stays frozen in its prereg AND the contradiction is carried on every sheet until revised.

OBJECTIVE
Ship `python ops/morning.py build` such that, every morning, for the irv-flow repo alone, it (1) reproduces
yesterday's close from the repo's own records and STOPS the day on any unexplained delta, (2) re-checks only
inputs whose sha256 changed, recording the hash it skipped on, (3) names one constraint for the repo from
today's observed numbers alone, (4) lists every operator action with no DONE line, and (5) writes the sheet
`out/morning/<YYYY-MM-DD>.md` (+ `.json`) ending in the three questions and one Highest Leverage Move whose Why
cites the constraint id. Measured by: build completes in under 5 minutes of machine time (fits the 25-minute
morning); a failed reproduction writes a STOPPED sheet and exits non-zero; `python ops/morning.py check` exits 0
only for today's complete, non-STOPPED sheet; every disagreement between a model and an observation found this
morning is a pinned row in `journal/morning/disagreements.jsonl`, and none is closed without a model revision.

THE CHECKLIST THIS CONTRACT MECHANIZES (operator's text, verbatim; each line is one section of the sheet)
## MORNING — before any build (≤25 min)
[ ] Reproduce the baseline. Run the scan or the saved verification block; every number matches
    yesterday's close or the day STOPS until the delta is explained.
[ ] Before re-running any check, ask: could the thing being checked have changed since I last
    checked it? If you can prove it couldn't (zero-drift confirmed), re-checking is ceremony —
    skip it. Only skip with proof of no-change. (QGIS re-open deferred Jun 12 & 15.)
[ ] Name the constraint from the observed state — re-derive, never inherit. If the inputs that
    justified yesterday's constraint changed, the constraint changed.
[ ] Open operator actions: anything I personally committed to that lacks a DONE check?
THE THREE QUESTIONS — answered against the named constraint, not in the abstract:
[ ] LEVERAGE — What action creates the largest improvement?
[ ] INVERSION — What am I doing that should stop?
[ ] ATTENTION — What deserves today's best focus?
OUTPUT — written before the first contract fires:
[ ] Today's Highest Leverage Move: ________
[ ] Why (one line, traceable to the constraint): ________

How each line becomes machine behaviour in this repo:
1. Baseline = `journal/morning/close/<day-1>.jsonl`. Every number is marked `must-hold` (cannot legitimately move
   overnight: sealed days' signal/fill counts and their MANIFEST pins, honest-filled FLOW and RUN n before
   yesterday's cut, looks already taken in `out/looks.json` / `out/looks-IF-02.json`, `prereg/FROZEN_SHA` and
   `IF-02-FROZEN_SHA`, the 08-28 known answer, the learn lineage up to yesterday) or `may-move` (today's unsealed
   journal, the heartbeat, drops this hour). A `must-hold` mismatch STOPS the day and pins a disagreement row.
2. Drift = sha256 over the exact input files of each check. Equal → "zero drift, re-check skipped, sha <hex>".
   Sealed days are the natural case: a pinned `journal/live/<day>.jsonl` whose MANIFEST sha still verifies is
   proof of no change, and its counts are carried, not recounted. The hunter's liveness has no file that proves
   it unchanged and is never skipped. Skipping without a recorded equal hash is impossible by construction.
3. Constraint = the first rule of the CONSTRAINT TABLE that fires on today's block. The function that names it
   takes no argument from yesterday's sheet. Yesterday's id is printed beside it with "changed" when the id or the
   sha of its firing inputs differs. `ops/constraint_scan.py`'s stage (by count) is shown as a reading, never adopted.
4. Operator actions = open `- [ ]` boxes in `docs/loop/rulings-owed.md` (`constraint_scan.rulings_owed()`), an
   owed ruling whose "before look N" has already fired flagged PAST ITS DEADLINE, an `IF-03 DRAFT OWED` from
   `out/learn.txt`, the un-applied `docs/loop/hunt-excursion.patch` (operator's word), and
   `journal/morning/commitments.jsonl` commit lines with no DONE line carrying evidence.
5–6. The five answers are written only through `python ops/morning.py answer`, which refuses an empty answer and a
   Why that does not contain today's constraint id.

THE CONSTRAINT TABLE (load-bearing; closed, ordered; first rule that fires wins; NULL never fires)
Rule 3 binds this table: it reads counts, states and recorded looks, never an outcome off a look boundary. There is
no EDGE rule here (hyperliquid's has one); "is FLOW profitable" is answered only at a look, by `ops/readout.py`.
| rank | id | fires when (observed, today) | source |
|---|---|---|---|
| 1 | STOP | S2: a key, wallet or order path appears (`tests/test_zero_capital_and_wall.py` red); or a prereg's sha no longer matches its pin (S1) | suite, `prereg/*FROZEN_SHA` |
| 2 | VOID | a §7 void condition is met: V2 live vs forward-capture disagreement > 10 % of co-observed signals; IF-02 V1 (look 4 not reached by freeze + 60 days = 2026-12-02); IF-01 V1 at look 4 | readout, `prereg/IF-02-FROZEN_AT` |
| 3 | LOOK | a look is due (n at or past the next look's n, not yet in `out/looks*.json`) or a look was recorded since the last close: the readout speaks, the scan names it and stops short of any verdict | `out/looks.json`, `out/looks-IF-02.json`, `common.LOOKS` |
| 4 | BROKEN | V3: the 08-28 known-answer gate red; a sealed day fails its MANIFEST sha; `ops/learn.py verify` fails; a foresight pen entry fails its check; a `must-hold` number failed to reproduce | suite, `journal/MANIFEST`, learn verify |
| 5 | BLIND | V4: hunter heartbeat older than 120 s or no event for 10 min; streams up < 2; today's LOOP (`monitor/loop-status.json`) missing or with a failed step | `monitor/hunt-heartbeat.json`, loop-status |
| 6 | STALE | `docs/digest.html` not written today (Central); a forecast owed for a window that opened unwritten | digest written-at; `out/calibration.txt` |
| 7 | RULING | an owed ruling gates a contract (PAST ITS DEADLINE first, then IF-03 DRAFT OWED, then the rest in file order) | `docs/loop/rulings-owed.md`, `out/learn.txt` |
| 8 | DISAGREE | an open row in `journal/morning/disagreements.jsonl`: an observation contradicting a prior, a baseline, a belief or a rate the program plans on (e.g. FLOW/day vs the spent corpus's 3.5, RUN/day vs IF-02 §8's 40/85/150) | the ledger |
| 9 | SAMPLE | honest-filled FLOW n below the next IF-01 look, or RUN n below the next IF-02 look, or a challenger below n 300 forward; the sheet prints days-to-look at the trailing rate | `common.LOOKS`, journal counts, `out/learn.txt` |
| 10 | NONE | nothing above fires | — |
STOP and VOID first because they end a contract regardless of anything else. LOOK above BROKEN because a look is
taken once at the first readout past its n: missing it is irreversible, a broken check is not. BROKEN above BLIND
because a wrong number read confidently costs more than a missing one. DISAGREE above SAMPLE because accruing more n
does not help a model the record already contradicts: that is the First Law. Inside a rank, IF-01 before IF-02
before IF-L01 (contract seniority). The plan gate may argue the order; once GO is given it is frozen and changes only
by a new dated line.

CONTEXT
- `CLAUDE.md` rules 1–8 (zero capital, no prereg edit, no verdict off a look, loss-first, 08-28 gate first,
  append-only pin-last journals, production-grade lines, foresight).
- `prereg/IF-01-PREREGISTRATION.md` §5–§8 and `prereg/IF-02-PREREGISTRATION.md` §5–§8, §10 (bar, looks, voids,
  priors, frozen parameters); `prereg/FROZEN_*`, `prereg/IF-02-FROZEN_*`, `prereg/PRIORS.json`.
- `ops/loop.py` STEPS (freshness first: "a reading over a dead hunter is noise"), `ops/constraint_scan.py`
  (six stages by count, `rulings_owed`), `ops/freshness.py`, `ops/readout.py`, `ops/learn.py verify`,
  `ops/calibration_ledger.py`, `src/common.py` (`LOOKS`, `BAR`, `heartbeat`), `src/journal.py` (the pinned writer).
- `docs/loop/constraint.md` (adversarial premise: the comfortable constraint needs the higher evidence bar),
  `docs/loop/kill-scan.md` (pass 1, the instrument's limit), `docs/loop/divergence.md` (rule 8's log: operator vs
  agent, the grounded one wins), `docs/loop/rulings-owed.md`, `docs/decisions/2026-10-06-economic-bar.md`.
- `~/board/contracts/MR-01-morning-run.md` + `~/board/fb/morning.py`: the cross-leg run (2026-10-05). It reads this
  repo as one leg through files and read commands; this contract is the repo's own, deeper scan; board MR-01 stays.
- Sibling: `~/hyperliquid/reports/contract_mr01.md` (2026-10-06), same checklist, same First Law.
- Inherited, by ID:
  - board MR-01 (2026-10-05). Finding kept: the constraint is computed from today's block only (poisoned-yesterday
    test); NULL fires no rule; an owed ruling whose "before look N" fired is PAST ITS DEADLINE.
  - IF-01 / IF-02 §6. Finding kept: the scan may name a constraint, never a verdict on a contract.
  - IF-L01 (2026-10-06). Finding kept: a challenger is a forward shadow; it reaches the sheet as SAMPLE or as an
    IF-03 DRAFT OWED ruling, never as a change to the hunter.
  - Economic-bar decision (2026-10-06). Finding kept: the frozen bars stay +1.0370 %; ECONOMIC BAR +6.97 % is printed
    beside them, never substituted.
- Loss-first doctrine (rule 4): when the sheet prints the readout's figures at all, meanL, worst loss, stop share and
  loser-vs-winner hold come before any mean.

SCOPE
IN:
- `ops/morning.py` (new): baseline, drift, constraint table, operator actions, disagreement ledger, sheet, `check`.
  Subcommands: `build [--date D] [--dry]`, `check`, `answer --leverage .. --inversion .. --attention .. --move ..
  --why ..`, `explain <field> "<evidence>" --revised <belief|debt|commit|close|ruling> <ref>`, `commit "<action>"`,
  `done <action-id> "<evidence>"`.
- `journal/morning/` (new, written through `src/journal.py`, pinned in `journal/MANIFEST`): `close/<day>.jsonl`,
  `disagreements.jsonl`, `commitments.jsonl`. `out/morning/<day>.md` / `.json` (the sheet).
- `.claude/commands/morning.md` (new): the unattended run's instructions.
- `ops/register_tasks.ps1`: task `irv-flow - MORNING` (S4U, WakeToRun, through `~/ops/run-hidden.vbs`, XML backed up
  in `~/ops/task-backup`); time set at the gate (proposed 06:00 Central: after LOOP 05:20 has finished, before board
  MORNING 07:10). Not a loop step: the loop is the machine's battery, the scan reads its result.
- `tests/test_morning.py` (new).
OUT (explicitly forbidden this contract):
- `prereg/` (all), `src/rule.py`, `src/challenger.py`, `src/foresight.py`, `ops/hunt.py`, `ops/hunt_guard.ps1`,
  `ops/loop.py`, `ops/readout.py`, `ops/learn.py`, `lib/captures.py`, every existing journal day and `journal/MANIFEST`
  entries already written, `out/looks*.json`, `docs/loop/*.md`. `git diff --stat` at DONE lists only SCOPE IN files.
- The working tree's uncommitted changes present at the time of writing (`ops/hunt.py`, `src/common.py`,
  `tests/test_hunt_gaps.py`, today's journal days) belong to other work: not touched, not committed, not reverted.
- The scan never forecasts, resolves, reviews, takes a look, writes a ruling or a belief. When a disagreement calls
  for a revision it names the command (`ops/predict.py`, `ops/decide.py`); the loop or the operator runs it.
- The hunter process: read its heartbeat and logs, never start, stop or restart it (HUNT GUARD owns that).
- `~/board`, `~/hyperliquid`, `~/mimicry` and every sibling repo (read-only per CLAUDE.md). No link fetched.
- No new dependencies; no network in tests or in `build` (the hunter's socket is not the scan's).

PLAN GATE
Before writing any code, report:
(1) The survey: every number proposed for the verification block, each with its exact file:field or function,
    marked `must-hold` or `may-move`, and why. Include which sealed-day pins carry counts without a recount. A
    number the repo does not write down today is NULL, and you say so.
(2) The layout: `journal/morning/` files and their MANIFEST pinning, the `.json` sheet schema, the disagreement row
    schema (observed + source, model value + source, first seen, revision ref or null), the sheet's reading order
    (baseline, drift, constraint, operator actions, the three questions, output).
(3) The load-bearing choice: the constraint table above. Argue the order or replace it. Show that no rule reads an
    outcome off a look boundary (rule 3), line by line. State which revision refs close a disagreement, why none of
    them edits a prereg, and why editing the observation is refused.
(4) Fixtures, real vs synthetic declared: a synthetic repo home per table rule, plus poisoned-yesterday, NULL, a
    look-due day, and a close-by-editing-the-observation attempt (must be refused); and one real dry run on today's
    repo whose sheet is pasted in full at the gate.
Then WAIT for GO.

CONSTRAINTS (MUST / NEVER)
- MUST: every number on the sheet carries its source; computed only from the files and functions named at the gate.
- MUST: a `must-hold` mismatch → sheet STOPPED, delta shown as `field: old → new (source)`, a disagreement row pinned,
  `check` exits 1 until `explain` records the evidence AND a model-revision ref. The first day says "baseline: first
  close, nothing to reproduce", and that is not a pass.
- MUST: observations are append-only and pinned. `explain` writes a new line; it cannot alter the observed value of
  any row (test-pinned). A wrong close is corrected by a new dated line citing the old one. NO BACKFILL (rule 6): a
  morning the scan did not run stays missing, and the next close says so.
- MUST: drift skip only on an equal sha256 (or a verifying MANIFEST pin) of named inputs; hunter liveness never skipped.
- MUST: today's constraint is a pure function of today's block (poisoned-yesterday test).
- MUST: deterministic: same inputs → byte-identical `.md`/`.json` (sorted keys, fixed float format, no clock in the
  body beyond `--date`), identical under PYTHONHASHSEED=0 and 1.
- MUST: `python ops/morning.py check` is the first line of VERIFY for every irv-flow contract written after MR-01.
- NEVER: fabricate a number. NULL renders "not recorded", fires no rule, and the rule is listed as unreadable.
- NEVER: a verdict, a mean-vs-bar comparison or a z off a look boundary, on the sheet or in an answer (rule 3).
- NEVER: render a forecaster's number for a foresight window still open.
- NEVER: change a frozen value (prereg parameters, BAR, looks, voids, the constraint table after GO) without a written,
  dated operator ruling through RI and a re-pin by amendment (rule 2).
- NEVER: a key, wallet, order or position path (rule 1).

ACCEPTANCE CRITERIA (deterministic)
- [ ] `python -m pytest` → all pass, the 08-28 known-answer gate green, and the existing 57 collected pass unchanged.
- [ ] Known answer, baseline: close says honest-filled FLOW n = 16 before the cut, today's journal says 17 before the
      same cut → STOPPED, line `flow_honest_before_cut: 16 → 17 (journal/live/… )`, one pinned disagreement row,
      `check` exit 1; `explain` without a revision ref → exit 1; with one → `check` exit 0.
- [ ] Known answer, First Law: `explain` given a new value for the observed field → refused, exit 1, bytes unchanged.
- [ ] Known answer, drift: a sealed day whose MANIFEST pin verifies → `zero drift, re-check skipped, sha <64 hex>` and
      the counter is not called (spy); one byte changed → the pin fails, BROKEN fires; the heartbeat → never skipped.
- [ ] Known answer, constraint: one fixture per table rule, each yields exactly its id; poisoned yesterday yields today's.
- [ ] Known answer, rule 3: a fixture with a FLOW mean far above BAR at n 16 → no rule fires on it, and neither the mean
      nor a z appears on the sheet.
- [ ] Known answer, NULL: missing field → "not recorded", rule listed unreadable, not fired.
- [ ] Refusals: Why without the constraint id → exit 1, nothing written; `done` without evidence → exit 1.
- [ ] Two runs of `build --date 2026-10-07 --dry` on one fixture → sha256 of `.md` and `.json` identical (pasted),
      under PYTHONHASHSEED=0 and 1.
- [ ] Real dry run completes in < 300 s (time pasted); `prereg/` sha, `journal/MANIFEST` entries before today, and the
      hunter's pid in `monitor/hunt-heartbeat.json` identical before and after (pasted).

VERIFY (fixed runbook — do not improvise)
1. `python -m pytest` (full suite) → pass count pasted, 08-28 gate line pasted.
2. `python -m pytest tests/test_morning.py` → pass count pasted.
3. `python ops/morning.py build --dry` twice → `sha256sum out/morning/<day>.md out/morning/<day>.json` both runs.
4. `python ops/morning.py check` → exit code and the sheet's STOPPED/complete line pasted.
5. `git diff --stat` → only SCOPE IN files; `git diff --stat prereg src ops/hunt.py ops/loop.py` empty of this contract's changes.
6. The acceptance list above, each item with its proof pasted.

STOP CONDITIONS
Halt and report, do not proceed, if:
- a record named at the gate is missing, or a read function changes its output or schema between gate and build
  (the uncommitted `ops/hunt.py` / `src/common.py` work landing is the named risk: re-survey before building);
- answering a gate item needs a number the repo does not record and the only way forward is to derive it from a
  published page or invent it;
- any rule of the table can only be evaluated by reading an outcome off a look boundary;
- a look reads as due, or a STOP/VOID reads as met, on the real repo: report it at once; it is the readout's and the
  operator's, not this contract's;
- any step would write to `prereg/`, an existing journal day, or touch the hunter;
- a disagreement can only be closed by changing the observation (the First Law would be violated);
- a golden file's bytes would change, or an acceptance test cannot pass without violating a MUST.
