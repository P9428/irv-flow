# IF-03 — THE RECLAIM BOUGHT ONLY AT H1 OR BETTER

STATUS: a DRAFT until `prereg/IF-03-FROZEN_AT` exists; FROZEN from the instant written there
(`python ops/freeze.py IF-03`). Ruled by the operator, 2026-10-06, verbatim: *"make this right now"*, on the move
written that day: a zero-capital paper arm filled at H1 or better within N seconds, otherwise no trade, frozen
before its first forward day, its hunter line live after IF-02 look 2. ZERO CAPITAL. NO KEY. NO WALLET. NO ORDER.
NO POSITION. PAPER ONLY.

## 0. Where this came from, stated so it cannot be forgotten

On 2026-10-06 a pattern scan of the whole forward record (1,477 honest-filled measurable reclaims, 2026-10-02
to 2026-10-06, `journal/live` joined to `journal/after`) looked for the one constraint between the reclaim and
an edge. What it saw, all of it now SPENT for this contract:

- **The stop is a zero-width stop, so the price paid over it is the loss.** The stop sits at H1; the honest fill
  is a median +2.8 % over H1. A stop costs a median −7.8 %: fee −2.5 %, fill over H1 −2.8 %, stop fill under
  H1 −2.0 %. 89 % of fills end in it, 59 % of those inside 5 s.
- **meanL rises with the premium paid over H1, in order:** honest fill at or below H1, n 167, win 14.4 %, meanL
  −4.8 %, mean +2.60 % (SE 2.01), drop-top-5 % −3.05 %; over H1 by 0–1 %, 1–3 %, 3–6 %, over 6 %: meanL −5.9,
  −7.7, −9.8, −16.5 %, means −2.38, −1.63, −1.55, −0.45 %. At or below H1 was positive on each of the 5 days;
  forward of IF-02's freeze (unseen when IF-02 §9 declined it) n 136, mean +3.31 %.
- **At the 2 s fill, the nearest thing in the record to a taker, the loss halves and the mean does not turn:**
  2 s fill at or below H1, n 318, meanL −4.86 %, mean −0.95 % (SE 0.90), drop-top-5 % −3.83 %; over H1, n 836,
  meanL −13.53 %, mean −1.77 %. 27.6 % of 2 s fills were at or below H1.
- **Selection carries no information.** Target exits pass each FLOW filter at the rate every reclaim does (age
  0.54 vs 0.53, pace 0.14 vs 0.11, buyers 0.27 vs 0.19). FLOW kept no target exit in five days.
- **A wider stop does not rescue the stopped.** After a stop, price went back over the fill on 79 % and to 2× on
  18 %, but fell a median −59 % below it. Order-free bounds on a stop 10 / 20 / 30 / 50 % under the fill: the
  mean per stopped trade lies in [−9.3, +8.7], [−13.9, +4.6], [−19.3, +1.3], [−28.0, −4.4] % against −9.6 % now.

- **The cap measure itself, run once before the freeze on spent prints** (six mimicry captures of 2026-08-28,
  the known-answer day): 28 measurable reclaims, the cap filled 19 (0.68), mean net −4.79 %, median −4.32 %. A
  smoke test of the code on real paths, n far too small to be evidence; it moved §8.

So the question this contract asks is narrow: if the reclaim is bought only when price is at or below the stop
level, with the latency a taker really has, does the cut in the loss outlast the adverse selection of buying
into a print that is already back at H1? The 2 s result says it may not. That is the pre-mortem, and §7 S4 is
its tripwire.

**SPENT for IF-03:** every mint created at or before `prereg/IF-03-FROZEN_AT`, and every after-line without
`cap_v` (written before the hunter carried the cap measure). The verdict is forward-only.

## 1. The rule

**Core:** IF-01 §1 as amended by IF-01 AMENDMENT 1, unchanged: the same `src/rule.py` detect(), the same
H1, the same reclaim print at second `t_e`. Exit by the frozen manage() from the fill: the first print in a
strictly later second with spot ≤ H1 (STOP), or spot ≥ `MULTIPLE` = 2 × the fill (TARGET), else the last
observed print (HORIZON). Net = (exit/fill)·(1−f)/(1+f) − 1 with `FEE` = 125/10000 per side. Size
`Z_LAMPORTS` = 1000000000; own impact is not in the mark.

**Population:** BASE, every reclaim on a measurable curve (`standard_path`, `K_TOL` = 1/100). No FLOW filter and
no run band: §0 found neither carries information.

**CAP entry:** the first print at second t with `t_e` + `CAP_LAG_S` ≤ t ≤ `t_e` + `CAP_WINDOW_S` whose spot is ≤
H1, filled at that print's spot. No such print: no trade. A taker can do this on the bonding curve with a swap
capped at H1 sent on every print until the window ends; a capped swap that would pay more reverts. Because the
stop is the first later print at or below H1, a CAP fill is stopped by the next second that stays at H1 or
under. That is the frozen exit, kept so that IF-03 differs from BASE by its entry and nothing else.

**Arms:** CAP is the test arm. BASE measured for the cap (honest arm, every measurable reclaim with `cap_v`) is
the control, never taken. One row per mint, as `foresight.rows()` keeps it.

## 2. Instrument

`src/excursion.py` measures the cap from each mint's own prints when its lookback ends, and the hunter writes it
to `journal/after/<utc-day>.jsonl` (`x.cap_v`, `x.cap_t`, `x.cap_fill`, `x.cap_net`, `x.cap_why`,
`x.cap_hold_s`, `x.cap_exit`). The running hunter carries it from its first restart after this freeze, which waits
for IF-02 look 2 (the operator's move of 2026-10-06: nothing changes what look 2 reads before n 600). Lines
written before that carry no `cap_v`, are never backfilled, and are counted on every readout. `ops/readout.py`
gains an IF-03 section and records its looks in `out/looks-IF-03.json`. With no pin it scores nothing.

## 3. Known-answer gate

IF-01 §3 binds: `tests/test_known_answer_0828.py` green before anything is scored.

## 4. The money sentence

A positive result lets the operator write a separate live-capital preregistration for capped reclaim entries,
with its own size, own impact measured at entry depth, and a paper-vs-live halt. Nothing in IF-03 places an order.

## 5. Primary quantity and bar

Primary: mean CAP net per filled signal, forward of the freeze, on lines carrying `cap_v`; SE = population
standard deviation ÷ √n as `ops/readout.py` computes it. Bar `BAR` = +1.0370 % (IF-01's, unchanged). The
ECONOMIC BAR is printed beside it and moves no look: break-even after own impact alone (`src/market.py`'s seed,
−6.25 pp at 1 SOL), because the arm's latency is already in its fill.

Loss-first gates, reported on every readout and required at a PASS: drop-top-5 % CAP mean > 0; median hold on
losers ≤ median hold on winners.

## 6. Looks and verdict

| look | n | z |
|---|---|---|
| 1 | 300 | 4.050 |
| 2 | 600 | 2.864 |
| 3 | 900 | 2.338 |
| 4 | 1,200 | 2.025 |

n counts filled CAP signals. PASS if (mean − BAR)/SE ≥ z and both loss-first gates hold; FAIL if
(mean − BAR)/SE ≤ −z; otherwise CONTINUE (looks 1–3) or INCONCLUSIVE (look 4). Each look is taken once, at the
first readout at or past its n. No verdict may be read off-boundary.

## 7. Void and stop conditions

- V1: look 4 not reached within 60 days of the freeze → VOID (underpowered).
- V2, V3, V4: as IF-01 §7.
- S1: any threshold, fee, size, horizon, fill convention, `CAP_LAG_S`, `CAP_WINDOW_S` or the population of §1
  changed → the run is spent; a new contract.
- S2: a key, wallet or order path appears anywhere in the repository → the program stops.
- S3: IF-01, IF-02 and IF-03 are never pooled. Their signals overlap.
- S4, the tripwire: if the drop-top-5 % CAP mean is ≤ 0 at look 1, no further entry or exit variant of the
  reclaim is preregistered. IF-01 and IF-02 run to their own looks. Only a dated operator ruling through RI
  lifts it.

## 8. Priors, written before any forward CAP outcome exists

P(PASS at a look) ≈ 0.04. P(FAIL at a look) ≈ 0.60. P(drop-top-5 % CAP mean > 0 at look 1) ≈ 0.15. Share of
measured BASE reclaims that fill: 0.30 / 0.50 / 0.75 (q10 / q50 / q90), up from the 2 s bucket's 0.28 because the
window catches later prints, and toward the spent smoke test's 0.68. Mean CAP net of the first 300:
−6.0 % / −2.5 % / +1.5 %, between the 2 s bucket of §0 (−0.95 %) and the smoke test (−4.79 %): the later in the
window a cap fills, the more it is a print falling back through H1. The checkable one is
journalled in `journal/foresight` under leg IF-03 before its window opens (rule 8).

## 9. Foresight debt and what was declined

Paid: IF-02 §9 (b) declined fills at or below H1 to keep the 08-28 gate and IF-02's single difference; this
contract tests them as their own entry, leaving IF-01, IF-02 and the gate untouched.

Owed: own impact at entry depth. The seed is measured at create depth (30 SOL virtual); the median honest
entry sits near 61 SOL virtual, where a 1 SOL round trip is nearer −3.3 % by the curve. That is an estimate,
not a measurement. The economic bar keeps the seed until a measurement replaces it.

Declined: a wider stop (§0 bounds), any selection filter (§0), and a zero-latency cap arm (no taker gets it).

## 10. Parameters, frozen (tests/test_if03.py reads these lines)

`CAP_LAG_S` = 2 · `CAP_WINDOW_S` = 10 · `K_TOL` = 1/100 · `D` = 1/2 · `MULTIPLE` = 2 · `LOOKBACK_S` = 900 ·
`Z_LAMPORTS` = 1000000000 · `FEE` = 125/10000 · `BAR` = +1.0370 %.
