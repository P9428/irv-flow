# IF-02 — THE RUN BAND ALONE, ON THE SAME HUNTER

STATUS: a DRAFT until `prereg/IF-02-FROZEN_AT` exists; FROZEN from the instant written there
(`python ops/freeze.py IF-02`, after the operator's ruling). ZERO CAPITAL. NO KEY. NO WALLET. NO ORDER.
NO POSITION. PAPER ONLY.

## 0. Where this came from, stated so it cannot be forgotten

IF-01 hunts the reclaim behind nine FLOW filters. In its first 22 hunter-hours (2026-10-02 15:12Z to
2026-10-03 13:20Z) the hunter closed 2,954 reclaims, 264 of them on measurable curves, and ONE FLOW
signal. At that rate IF-01's look 1 (n 300) is most of a year away and the contract most likely ends
VOID. IF-01 continues untouched; this contract neither amends nor replaces it.

Of IF-01's filters, one came from evidence: the audit of 2026-10-02 found the 2–3× run band carrying
2026-08-28 (IF-01 §0). The other seven flow filters came from the operator's description of the trade.
IF-02 asks the wider question the hunter can answer in weeks: does the reclaim clear the bar on the run
band alone. The band's thresholds are IF-01's, frozen 2026-10-02 before any forward print existed, and
are not re-read here.

**What had been seen when this was drafted (2026-10-03).** On the forward BASE population: 263
honest-filled measurable reclaims, 89 % stopped, median net on a stop −7.8 %, 13 targets near +98 %,
mean honest net between −2 % and −3 %; the run flag passes 33 % of measurable reclaims (a count). The
forward outcome of the run band itself was NOT computed by the drafter, and no instrument in the
repository reported it. In the spent corpus the band's zero-latency mean was +1.9 % to +4.0 % with a
median of −12 to −14 %, in-sample, before the −3.7 pp latency cost of mimicry §58.

**SPENT for IF-02:** every mint created at or before `prereg/IF-02-FROZEN_AT`, which includes every
line of `journal/live` written before the freeze and everything spent for IF-01. The verdict is
forward-only.

## 1. The rule

**Core:** IF-01 §1 as amended by IF-01 AMENDMENT 1, unchanged — the same `src/rule.py`, the same
`ops/hunt.py`, the same journal lines. Running max of the constant-product spot inside `LOOKBACK_S` =
900 s of create; the first print at or below `D` = 1/2 of it freezes H1; the first print in a strictly
later second with spot > H1 is the reclaim print. Exit at the first print with spot ≤ H1 (STOP), or
spot ≥ `MULTIPLE` = 2 × entry (TARGET), else the last observed print (HORIZON). Net per signal =
(exit/entry)·(1−f)/(1+f) − 1 with `FEE` = 125/10000 per side. Size `Z_LAMPORTS` = 1000000000; own
impact is NOT in the mark (IF-01 AMENDMENT 1: about −6.25 % per round trip at this size), so every
figure is an upper bound by roughly that much.

**RUN signal:** a reclaim signal with `RUN_MIN` = 2 ≤ H1 ÷ standard create spot < `RUN_MAX` = 3
(the journal's `flags.run`) on a measurable curve. Measurable is what IF-01's readout enforces:
constant product (`K_TOL` = 1/100) and the token invariant on every print of the path
(`standard_path`). That gate reads prints after entry, so it is a measurement gate and not something
a taker could apply; every readout counts the run signals that were standard at entry and excluded
by it.

**Arms:** RUN is the test arm. BASE — every measurable reclaim forward of the freeze — is the control,
never taken. ZERO and HONEST fill arms as in IF-01; exits fill at the crossing print, never at the
level. One row per mint; where the live and forward-capture journals both hold a mint, the hunter's
line is the row.

## 2. Instrument

Nothing new runs. `ops/readout.py` gains an IF-02 section that reads the same journals, keeps mints
created after `IF-02-FROZEN_AT`, and records its looks in `out/looks-IF-02.json`. With no pin it
scores nothing (`tests/test_if02.py`).

## 3. Known-answer gate

IF-01 §3 binds: `tests/test_known_answer_0828.py` green before anything is scored.

## 4. The money sentence

A positive result lets the operator write a separate live-capital preregistration for RUN signals,
with its own size, own-impact measurement and paper-vs-live slippage halt. Nothing in IF-02 places
an order.

## 5. Primary quantity and bar

Primary: mean HONEST-arm net per RUN signal, forward of the freeze, one position per mint, SE =
population standard deviation ÷ √n as `ops/readout.py` computes it. Bar `BAR` = +1.0370 % (IF-01's;
the ruling owed on re-deriving it binds both contracts and must land before either look 1).

Loss-first gates, reported on every readout and required at a PASS: drop-top-5 % HONEST mean > 0;
median hold on losers ≤ median hold on winners.

## 6. Looks and verdict

| look | n | z |
|---|---|---|
| 1 | 300 | 4.050 |
| 2 | 600 | 2.864 |
| 3 | 900 | 2.338 |
| 4 | 1,200 | 2.025 |

n counts HONEST-filled RUN signals. PASS if (mean − BAR)/SE ≥ z and both loss-first gates hold; FAIL
if (mean − BAR)/SE ≤ −z; otherwise CONTINUE (looks 1–3) or INCONCLUSIVE (look 4). Each look is taken
once, at the first readout at or past its n. No verdict may be read off-boundary.

## 7. Void and stop conditions

- V1: look 4 not reached within 60 days of the freeze → VOID (underpowered).
- V2, V3, V4: as IF-01 §7.
- S1: any threshold, fee, size, horizon, fill convention or the population rule of §1 changed → the
  run is spent; a new contract.
- S2: a key, wallet or order path appears anywhere in the repository → the program stops.
- S3: IF-01 and IF-02 are never pooled. Every FLOW signal is also a RUN signal, so the two verdicts
  are two readings of overlapping prints: a PASS here is weaker evidence than it would be alone, and
  any live-capital contract built on it must say so.

## 8. Priors, written before any forward RUN outcome was read

P(PASS at a look) ≈ 0.07. P(FAIL at a look) ≈ 0.60. P(RUN honest mean > BASE honest mean at
look 1) ≈ 0.55. HONEST-filled RUN signals per day: 40 / 85 / 150 (q10 / q50 / q90). Mean honest net
of the first 300: −5.5 % / −2.0 % / +1.5 %. The checkable ones are journalled in `journal/foresight`
under leg IF-02 before their windows open (rule 8).

## 9. Foresight debt and what was declined

No lesson carrying `owes` existed when this was drafted; nothing to pay or decline.

Declined, from the stop audit of 2026-10-03: (a) the stop cannot fire inside the entry second;
(b) HONEST fills at or below H1 are taken (31 of 263 forward, mean −0.48 % against −2.62 % for fills
above H1). Both stay as they are, so the 08-28 gate holds and IF-02 differs from IF-01 by its filter
set and nothing else.

## 10. Parameters, frozen (tests/test_if02.py reads these lines)

`RUN_MIN` = 2 · `RUN_MAX` = 3 · `K_TOL` = 1/100 · `D` = 1/2 · `MULTIPLE` = 2 · `LOOKBACK_S` = 900 ·
`Z_LAMPORTS` = 1000000000 · `FEE` = 125/10000 · `BAR` = +1.0370 %.
