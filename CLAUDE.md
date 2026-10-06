# irv-flow — CLAUDE.md

Sibling of ~/mimicry, ~/uncapped, ~/ladder, ~/breadth, ~/persistence, ~/wallet-independence.
Those repos are READ-ONLY from here. `lib/captures.py` has no write path (tests/test_zero_capital_and_wall.py).

## What this is
IF-01: mimicry's frozen reclaim (M-MI-11) plus nine entry-observable FLOW filters, hunted live on the
keyless public websocket by `ops/hunt.py` and scored on paper. Contract: `prereg/IF-01-PREREGISTRATION.md`,
sha-pinned in `prereg/FROZEN_SHA`. Everything on disk at freeze (`prereg/FROZEN_AT`) is SPENT.
IF-02: the same reclaim on the 2–3× run band alone, same hunter, its own section of the readout and its own looks
(`out/looks-IF-02.json`). Contract: `prereg/IF-02-PREREGISTRATION.md`, pinned by `python ops/freeze.py IF-02` in
`prereg/IF-02-FROZEN_AT` + `IF-02-FROZEN_SHA`; mints created at or before that instant are SPENT for it.
IF-03: the same reclaim on every measurable curve, bought only at H1 or better 2–10 s after the signal (`src/excursion.py` cap_*),
frozen 2026-10-06 (`prereg/IF-03-PREREGISTRATION.md`, `IF-03-FROZEN_*`, `out/looks-IF-03.json`); live from the hunter's first restart
after IF-02 look 2 (morning commitment A-0001). IF-01, IF-02 and IF-03 are never pooled.

## Rules that bind every session
1. ZERO CAPITAL. No key, wallet, order or position, machine-checked. The socket only receives.
2. The prereg is never edited after freeze; write an AMENDMENT section and re-pin.
3. No verdict off a look boundary (`ops/readout.py` enforces; `out/looks.json` records).
4. Loss-first: every readout leads with meanL, payoff, hold on losers vs winners, worst loss, stop share.
5. The 08-28 replication gate (`tests/test_known_answer_0828.py`) must be green before anything is scored.
6. Journals are append-only, pin-last; `journal/MANIFEST` is the record. NO BACKFILL.
7. Every line production-grade, zero boilerplate (operator ruling 2026-09-09).
8. FORESIGHT. Every forecast is journalled before its window opens (`ops/predict.py` → `journal/foresight/`);
   the loop resolves it; every miss gets a lesson by cause; a resolution is a score, never a verdict; a lesson
   never moves a frozen parameter — it is debt the next prereg lists as paid or declined. `docs/loop/foresight.md`.

## Layout
`src/rule.py` the rule · `src/journal.py` writer · `lib/captures.py` reader · `ops/hunt.py` the hunter ·
`ops/score.py` capture scorer · `ops/readout.py` · `ops/freeze.py` the pin (IF-02 on) ·
`ops/decide.py` one decision ruled through RI (ri_core) → `docs/decisions/` + `journal/decisions/` (operator ruling 2026-10-03: decisions go through RI) · `ops/freshness.py` · `ops/loop.py` ·
`src/foresight.py` beliefs, forecasts, resolution, where a miss is laid · `ops/predict.py` its pen · `ops/calibration_ledger.py` its scorer ·
`ops/learn.py` + `src/challenger.py` IF-L01: every trade a training row (`journal/train/`), one challenger frozen a day (`journal/learn/`), scored forward only (`out/learn.txt`; `docs/contracts/IF-L01-learning-loop.md`) ·
`src/market.py` market state, the day's winners and losers, the haircut · `src/excursion.py` excursion and the 1 s / 2 s fill
(`journal/after/`, written by the hunter only once `docs/loop/hunt-excursion.patch` is applied on the operator's word) ·
`ops/digest.py` the operator's day/week/month page → `docs/digest.html` → artifact (`.claude/commands/digest.md`) ·
`ops/hunt_guard.ps1` + `ops/register_tasks.ps1` workstation tasks · `ops/systemd/` VPS unit · `tests/`.
