# irv-flow — CLAUDE.md

Sibling of ~/mimicry, ~/uncapped, ~/ladder, ~/breadth, ~/persistence, ~/wallet-independence.
Those repos are READ-ONLY from here. `lib/captures.py` has no write path (tests/test_zero_capital_and_wall.py).

## What this is
IF-01: mimicry's frozen reclaim (M-MI-11) plus nine entry-observable FLOW filters, hunted live on the
keyless public websocket by `ops/hunt.py` and scored on paper. Contract: `prereg/IF-01-PREREGISTRATION.md`,
sha-pinned in `prereg/FROZEN_SHA`. Everything on disk at freeze (`prereg/FROZEN_AT`) is SPENT.

## Rules that bind every session
1. ZERO CAPITAL. No key, wallet, order or position, machine-checked. The socket only receives.
2. The prereg is never edited after freeze; write an AMENDMENT section and re-pin.
3. No verdict off a look boundary (`ops/readout.py` enforces; `out/looks.json` records).
4. Loss-first: every readout leads with meanL, payoff, hold on losers vs winners, worst loss, stop share.
5. The 08-28 replication gate (`tests/test_known_answer_0828.py`) must be green before anything is scored.
6. Journals are append-only, pin-last; `journal/MANIFEST` is the record. NO BACKFILL.
7. Every line production-grade, zero boilerplate (operator ruling 2026-09-09).

## Layout
`src/rule.py` the rule · `src/journal.py` writer · `lib/captures.py` reader · `ops/hunt.py` the hunter ·
`ops/score.py` capture scorer · `ops/readout.py` · `ops/freshness.py` · `ops/loop.py` ·
`ops/hunt_guard.ps1` + `ops/register_tasks.ps1` workstation tasks · `ops/systemd/` VPS unit · `tests/`.
