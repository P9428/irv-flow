# IF-01 — THE FLOW-FILTERED RECLAIM, HUNTED LIVE

STATUS: FROZEN 2026-10-02. ZERO CAPITAL. NO KEY. NO WALLET. NO ORDER. NO POSITION. PAPER ONLY.

## 0. Where this came from, stated so it cannot be forgotten

On 2026-10-02 every Solana memecoin program on this machine was audited. Nothing taker-side ever
cleared a bar. The one real green day across ~830,000 paper positions was 2026-08-28 on the
mimicry reclaim (M-MI-11): 1,221 signals, 226 winners, +1.51 SOL at 0.05 SOL per signal. Profiling
those 226 against the 995 losers found the winners indistinguishable at the median on every
pre-entry flow feature, with one band carrying the whole day: tokens that had already run 2–3×
from create. On the other 34 days that band had a positive mean on 19–22 of 33 days (+1.9 % to
+4.0 % at zero latency, median −12 to −14 %), versus 10 of 34 days for all signals.

**Every number above was read in-sample, including on the "other" days.** Therefore every
capture on disk at freeze (`prereg/FROZEN_AT` = `mi-20260929T1040Z`, the newest) is SPENT. No
figure from it may be cited as evidence for IF-01. The verdict is forward-only.

The operator's instruction (2026-10-02, verbatim): *"a token 30 seconds to 5 minutes old that
had already run 2 to 3x, with a few dozen different buyers, no single whale on either side,
trading at under one print per second, that dropped 50% because many small holders sold rather
than one wallet dumping, and then printed back above its high."* and *"we need to actively
search and hunt for this winning trade/strategy all day everyday and never miss 24/7"* and
*"the program should replicate every single winning trade from 8-28 to a tee."*

## 1. The rule

**Core (unchanged mirror of M-MI-11, frozen 2026-08-18 in mimicry):** for every pump.fun create,
inside `LOOKBACK_S` = 900 s of the create timestamp, track the running max of the constant-product
spot (pre-trade state). The first print at or below `D` = 1/2 of the running max freezes
H1 = that running max. The first later print (strictly later second) with spot > H1 is the
reclaim print. Exit at the first print with spot ≤ H1 (STOP), or spot ≥ `MULTIPLE` = 2 × entry
(TARGET), else the last observed print inside the lookback (HORIZON). Net per signal =
(exit/entry)·(1−f)/(1+f) − 1 with `FEE` = 1.25 % per side (K = 79/81). Size `Z_LAMPORTS` =
0.05 SOL. One signal per mint.

**FLOW filters, all computed from the mint's prints up to and including the reclaim print:**

| filter | definition | frozen threshold |
|---|---|---|
| age | seconds from create to the reclaim print | `AGE_MIN_S` = 30 ≤ age < `AGE_MAX_S` = 300 |
| run | H1 ÷ standard create spot (30 SOL / 1.073e9 tokens) | `RUN_MIN` = 2 ≤ run < `RUN_MAX` = 3 |
| buyers | distinct buying wallets | `BUYERS_MIN` = 20 ≤ n < `BUYERS_MAX` = 80 |
| big_buy | largest single buy ÷ total buy SOL | < `BIG_BUY_SHARE_MAX` = 1/5 |
| big_sell | largest single sell ÷ total sell SOL | < `BIG_SELL_SHARE_MAX` = 2/5 |
| pace | prints ÷ age | < `PACE_MAX` = 1 per second |
| dip_sellers | distinct sellers between the H1 print and the trough print | ≥ `DIP_SELLERS_MIN` = 3 |
| dip_top | top seller's share of dip-leg sell SOL | < `DIP_TOP_SELLER_SHARE_MAX` = 1/2 |
| standard | every print up to entry carries the token invariant AND the constant product vSOL·vTOK moves < `K_TOL` = 1/100 print to print | required |

A signal passing all nine is a **FLOW** signal. All reclaim signals on standard curves form the
**BASE** control arm. The `standard` filter is the measurement gate: on curves failing it the quoted spot
misses the realised trade price by −16 %/+24 % (p10/p90, measured 2026-08-28), and the wash-bot curves
that produced the fake +366 SOL window of 2026-08-14 fail it outright. On 2026-08-28 only 241 of the
1,221 reclaim signals were on constant-product curves. Nothing failing it is ever a position.

**Two fill arms on every signal:** ZERO = entry at the reclaim print (mimicry's convention, the
one that reproduces 08-28); HONEST = entry at the next print after the reclaim print, no next
print = no fill. Exits in both arms fill at the crossing print, never at the level.

## 2. What is hunted and how

`ops/hunt.py` holds a keyless `logsSubscribe(mentions=[pump.fun], processed)` websocket on the
public RPC 24/7, decodes CreateEvent/TradeEvent exactly as wallet-independence's collector did,
runs the rule on every print of every new mint for 900 s, and writes one line per closed
position to `journal/live/<utc-day>.jsonl`. FLOW signals are appended to
`monitor/flow-alerts.log` the second they fire. The hunter is kept alive by a 5-minute guard
task and restarted on logon. `ops/score.py` additionally scores any mimicry capture that
arrives after `FROZEN_AT`, into `journal/forward/`, as a second, independent witness.

## 3. Known-answer gate (V3)

`tests/test_known_answer_0828.py` must reproduce mimicry's 2026-08-28 journal exactly: the same
1,221 (capture, mint) signals, the same exit branch and net on each, the same 226 winners, the
same day total. `prereg/KNOWN_ANSWER_0828.json` pins how many of those 1,221 are FLOW signals and
how many of those won, so a drift in the filters is visible before it reaches the verdict.

## 4. The money sentence

A positive result lets the operator run the same hunter with a key at the declared size on
FLOW signals only, after a separate live-capital preregistration with its own paper-vs-live
slippage halt. Nothing in IF-01 places an order.

## 5. Primary quantity and bar

Primary: mean HONEST-arm net per FLOW signal, forward only (live journal plus forward captures),
SE clustered by signal (one position per mint). Bar `BAR` = +1.0370 % net per signal (inherited
from M-MI-11; the operator may re-derive it by amendment before look 1, never after).

Loss-first gates (loss-first doctrine, 2026-08-27) are reported on every readout and are
required at a PASS: drop-top-5 % HONEST mean > 0; median hold on losers ≤ median hold on winners.

## 6. Looks and verdict

Four n-indexed looks on HONEST-filled FLOW signals, O'Brien–Fleming boundaries as in M-MI-11:

| look | n | z |
|---|---|---|
| 1 | 300 | 4.050 |
| 2 | 600 | 2.864 |
| 3 | 900 | 2.338 |
| 4 | 1,200 | 2.025 |

At a look: PASS if (mean − BAR)/SE ≥ z and both loss-first gates hold; FAIL if (mean − BAR)/SE ≤
−z; otherwise CONTINUE (looks 1–3) or INCONCLUSIVE (look 4). Each look is taken once, the first
readout at or past its n, and recorded in `out/looks.json`. No verdict may be read off-boundary.

## 7. Void and stop conditions

- V1: fewer than 30 FLOW signals at look 4 → VOID (underpowered).
- V2: the hunter's own live journal and the forward-capture journal disagree on more than 10 %
  of co-observed signals → VOID (instrument), and the disagreement is published.
- V3: known-answer gate red → nothing is scored until it is green again.
- V4: the hunter RED (no heartbeat or no event for 10 min) → the gap is logged; the day is not
  backfilled; the contract continues.
- S1: any threshold, fee, size, horizon or fill convention changed → the run is spent; a new
  contract with a fresh `FROZEN_AT`.
- S2: a key, wallet or order path appears anywhere in the repository → the program stops.

## 8. Priors, written before any forward signal exists

P(FLOW honest mean clears BAR at a look) ≈ 0.20. P(FLOW honest mean > BASE honest mean) ≈ 0.65.
P(the hunter fires fewer than 15 FLOW signals per day) ≈ 0.50 (base rate in the spent corpus is
measured and recorded in `out/spent-all.summary.txt` after this freeze, as a count, not evidence).
Expected honest FLOW mean, from the spent corpus and the −3.7 pp latency cost measured in
mimicry §58: between −2 % and +1 %.

## 9. Parameters, frozen (tests/test_frozen.py reads these lines)

`AGE_MIN_S` = 30 · `AGE_MAX_S` = 300 · `RUN_MIN` = 2 · `RUN_MAX` = 3 · `BUYERS_MIN` = 20 ·
`BUYERS_MAX` = 80 · `BIG_BUY_SHARE_MAX` = 1/5 · `BIG_SELL_SHARE_MAX` = 2/5 · `PACE_MAX` = 1 ·
`DIP_SELLERS_MIN` = 3 · `DIP_TOP_SELLER_SHARE_MAX` = 1/2 · `K_TOL` = 1/100 · `D` = 1/2 · `MULTIPLE` = 2 ·
`LOOKBACK_S` = 900 · `Z_LAMPORTS` = 50000000 · `FEE` = 125/10000 · `BAR` = +1.0370 %.
