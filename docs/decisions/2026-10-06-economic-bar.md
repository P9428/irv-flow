# Decision · The owed ruling: re-derive BAR from operator economics before look 1, or confirm the inherited +1.0370 %. IF-02's look 1 was taken at 2026-10-06T10:20Z under the inherited bar. Amend IF-01's BAR to the economic figure, or keep both frozen bars and carry the economic bar beside every look and into any live-capital prereg?

2026-10-06 · asked by the operator, 2026-10-06: 're-derive BAR from operator economics', then 'B' on the two ways to land it · log root `a9f3b6756e5d8fa1a15b20c7a7f519cd88e02c910bbd444a623e161a6cc7a7df` · size 21

## REALITY
Looked at before reasoning: prereg/IF-01-PREREGISTRATION.md section 5 (the operator may re-derive BAR by amendment before look 1, never after), section 7 S1, AMENDMENT 1 (paper size 1 SOL; own impact about -6.25 % a round trip at that size is NOT in the mark); prereg/IF-02-PREREGISTRATION.md section 5: BAR is IF-01's, and the ruling on re-deriving it binds both contracts and must land before either look 1; out/looks-IF-02.json: look 1 taken 2026-10-06T10:20:05Z, n 322, honest RUN mean -2.276 %, z_obs -1.794, CONTINUE, against +1.0370 %; ~/mimicry docs/loop/rules.md AMENDMENT 2 (2026-08-21): +1.0370 % is 0.319393 x 1.0 SOL / (616 x 0.05), the daily growth for 1 SOL to $30M in 43 days, and that target is struck by the operator's cash-machine ruling; ~/mimicry docs/loop/divergence.md AMENDMENT 4: the BAR row carries a $200/SOL assumption and a linear-deployment model; no cost of trading enters it; src/market.py haircut: own impact -6.2509 % at 1.00 SOL (mimicry RESULTS section 82) plus latency measured on 1,121 2 s fills, -0.72 pp; total -6.97 pp at this readout; docs/decisions/2026-10-05-hunter-free-tier.md: a paid feed is vetoed on funds, so the hunter's fixed cost is zero; python ops/readout.py 2026-10-06: honest FLOW n 16 mean -11.918 %; honest RUN n 332 mean -2.278 %; NOT looked: network and priority fees per transaction on a real order (no order exists, rule 1); a profit floor above break-even (the operator's to name); own impact at a size other than 1 SOL on the reclaim's own entries.
- **FACT** · The inherited +1.0370 % is the struck $30M target's daily growth over signal density; no trading cost is in it · _USABLE_
- **FACT** · The honest arm leaves out own impact (-6.25 pp at 1 SOL) and latency past the next print (-0.72 pp measured on 1,121 2 s fills); a paid feed is vetoed on funds, so fixed cost is zero. Break-even honest mean is +6.97 % · _USABLE_
- **FACT** · IF-02 look 1 was taken at 2026-10-06T10:20Z against +1.0370 %; IF-02 section 5 requires the bar ruling before either look 1 · _USABLE_
- **FACT** · IF-01 FLOW has 16 honest fills of 300 for look 1; its own section 5 still allows an amendment · _USABLE_
- **FACT** · The operator ruled re-derive, then B · _USABLE_
- **FACT** · THE CONSTRAINT: ACCRUE — honest-filled FLOW n 16 of 300 for look 1; 87 days at the trailing rate · _USABLE_
- **INFERENCE** · A pass against +1.0370 % on the honest arm would still lose about 6 pp a trade at 1 SOL; the frozen bar measures a dead target, not money · _USABLE_
- **INFERENCE** · Amending IF-01 alone breaks IF-02's frozen text, which ties both contracts to one bar ruling landed before either look 1 · _USABLE_
- **UNKNOWN** · Per-transaction network and priority fees on a real order; the operator's profit floor above break-even · _UNVERIFIED_

## OPTIONS

| option | status | do | circle | door |
|---|---|---|---|---|
| A-amend-IF-01 | VETOED | Write IF-01 AMENDMENT 2 setting BAR to break-even after the haircut (+6.97 % today) and re-pin; IF-02 keeps +1.0370 % | inside | IRREVERSIBLE |
| B-economic-bar-beside | open | Keep both frozen BARs. Print the economic bar (break-even after the measured haircut, +6.97 % today) beside every IF-01 and IF-02 look, read by none; every live-capital prereg inherits it in place of +1.0370 % | inside | reversible |
| C-confirm-inherited | VETOED | Confirm +1.0370 % and close the box | inside | reversible |

## SURVIVAL
- **A-amend-IF-01** fails if IF-02's section 5 is read as binding IF-01 too, so the amendment lands after the deadline the contracts set together; and the two sibling contracts then judge the same reclaim against bars 6.7x apart · VETOED: rule 2 and IF-02 section 5: the bar ruling had to land before either look 1, and IF-02's look 1 fired at 10:20Z
- **B-economic-bar-beside** fails if a reader takes a frozen-bar PASS as money without reading the line under it; or the haircut's own impact figure (one measurement at create depth) is wrong for the reclaim's entries and the economic bar with it
- **C-confirm-inherited** fails if the bar keeps measuring a struck target and a pass reads as money while losing about 6 pp a trade · VETOED: F05: the operator ruled re-derive

## INCENTIVES
- Claude first: Claude proposed B and wrote the readout line that carries it, so the ruling ships Claude's code and Claude's framing; Claude also wrote this morning's MR-01 move that sent the operator here after IF-02's look 1 had already fired, and B is the option that does not expose that miss by forcing an amendment. The check is that A is laid out with its numbers and its only veto is IF-02's own frozen text, which Claude did not write. The operator: wants a bar that means money; a pass against +1.0370 % would read as a win while losing about 6 pp a trade. Nobody else: zero capital, no counterparty.

## SYSTEM EFFECT
- **A-amend-IF-01**: a frozen deadline is passed by reading one contract's text over its sibling's
- **B-economic-bar-beside**: no frozen parameter moves after a look; the readout states the gap between the contract's bar and money on every reading
- **C-confirm-inherited**: a dead target's number is ratified as the program's money test

## THE DOOR
- Reversible, decided now: the readout line and src/market.py economic_bar: both revert with a commit and read no look
- Irreversible, gated: none on this contract; the economic bar becomes binding only in a future live-capital prereg, which is its own ruling

## RECOMMENDATION
**B-economic-bar-beside.** RULED: keep IF-01's and IF-02's frozen +1.0370 %; carry the economic bar, break-even after the measured haircut (+6.97 % today, no fixed cost), beside every look and into every live-capital prereg. A amends after IF-02's look 1 against both contracts' joint deadline; C ratifies the struck $30M target and the operator ruled re-derive. · _USABLE_

## Gates on the irreversible half

| gate | rule | measured | holds | reading | from |
|---|---|---|---|---|---|
| suite-green | tests_passed >= 49 | 49 | **YES** | BELIEF | python -m pytest, 2026-10-06, after the economic-bar change |
| known-answer-0828 | gate_0828_green >= 1 | 1 | **YES** | BELIEF | tests/test_known_answer_0828.py in that run |
| operator-ruled | operator_ruled_B >= 1 | 1 | **YES** | BELIEF | the operator, 2026-10-06: 'B' |

## Ledger

| claim | layer | label | ruling | m(alive) | m(dead) |
|---|---|---|---|---|---|
| F01 | L0 | FACT | **USABLE** | 0.95 | 0.00 |
| F02 | L0 | FACT | **USABLE** | 0.95 | 0.00 |
| F03 | L0 | FACT | **USABLE** | 0.95 | 0.00 |
| F04 | L0 | FACT | **USABLE** | 0.95 | 0.00 |
| F05 | L0 | FACT | **USABLE** | 0.70 | 0.00 |
| I01 | L2 | INFERENCE | **USABLE** | 0.60 | 0.00 |
| I02 | L2 | INFERENCE | **USABLE** | 0.60 | 0.00 |
| U01 | L0 | UNKNOWN | **UNVERIFIED** | 0.00 | 0.00 |
| M01 | L1 | FACT | **USABLE** | 0.95 | 0.00 |
| opt-A-amend-IF-01 | L3 | INFERENCE | **KILLED** | 0.00 | 0.60 |
| opt-B-economic-bar-beside | L3 | INFERENCE | **USABLE** | 0.60 | 0.00 |
| opt-C-confirm-inherited | L3 | FACT | **KILLED** | 0.00 | 0.60 |
| R01 | L4 | INFERENCE | **USABLE** | 0.60 | 0.00 |
