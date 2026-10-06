# Decision · The public RPC cuts the hunter's streams and then refuses it with HTTP 413; a paid feed is out of reach. Restart the hunter now on the instrumented code with two streams, restart it on one stream, wait for a natural restart, or add a free keyed failover?

2026-10-05 · asked by the operator, 2026-10-05: 'fix this' on the 413 report, then 'I don't have the funds for that right now. We need to figure out how we can make this work on the free tier' · log root `b0cafb0c4eabfb8598c7598ff66a6fad0e6f759065a436270730c6801a808080` · size 26

## REALITY
Looked at before reasoning: monitor/hunt.log 2026-10-02 16:31Z to 2026-10-05 15:28Z: 854 cuts (286 a day), 720 of them absorbed by the twin stream, 134 windows with both streams down (44.8 a day), 343 blind seconds a day, median 2 s, p90 30 s, longest 2 m 24 s; 1,001 refusals with HTTP 413; journal/live since 2026-10-02 20:36Z: 330 of 6,660 records (5.0 %) have a both-down window inside the path, 153 (2.3 %) at or before the signal; mints created inside a window are not followed at all; a 90-minute receive-only diagnostic on one extra connection, 13:58Z to 15:28Z: every cut is a server Close frame whose code is outside RFC 6455 (websockets raises ProtocolError 'invalid status code' and answers 1002); the 413 that follows carries x-ratelimit-tier free, x-ratelimit-endpoint-remaining -19570 recovering about 80 a second, retry-after 30, pubsub-limit 10 with 7 remaining while three subscriptions were open; a 30-second sample: 350 messages a second, 82 % failed transactions, about 400 KiB/s, about 1 TB a month per stream; five other keyless endpoints probed from this machine (PublicNode, dRPC, Ankr, GetBlock, Blast): none serves logsSubscribe here; Helius answers 401 without a key; provider pricing: Helius WSS 2 credits per 0.1 MB, free plan 1M credits; QuickNode, Triton, Chainstack all above zero for this volume; ops/hunt.py as patched in this session and tests/test_hunt_gaps.py; python -m pytest 48 passed including the 08-28 gate; prereg/IF-01-PREREGISTRATION.md section 2 (a keyless logsSubscribe on the public RPC) and V4 (a RED gap of 10 min is logged, never backfilled); NOT looked: whether the meter is in bytes, messages or something else; the meter's value at the moment of a cut rather than at the next handshake; whether a cut's rate falls when the IP draws less.
- **FACT** · Every cut is a server-side Close with a non-RFC code; the client's 1002 is its answer, not the cause. A lenient client would not keep the stream · _USABLE_
- **FACT** · The 413 is a per-IP free-tier meter overdrawn: endpoint-remaining -19570, retry-after 30, pubsub-remaining 7 of 10 with three subscriptions open from this IP · _USABLE_
- **FACT** · Two streams: 286 cuts a day, 84 % absorbed by the twin, 343 blind seconds a day, 5.0 % of records touched · _USABLE_
- **FACT** · The patched hunter journals every both-down window to journal/gaps, logs the meter on every handshake and refusal, honours retry-after, takes IRV_FLOW_STREAMS (default 2) and no longer miscounts a live twin when the other is refused; 48 tests green · _USABLE_
- **FACT** · The operator has no funds for a paid feed · _USABLE_
- **FACT** · THE CONSTRAINT: COLLECT — heartbeat 0 s, last event 1 s ago, drops this hour 144, streams up 2, lag 2.3 s · _USABLE_
- **INFERENCE** · One stream halves the IP's draw but loses the twin that absorbs 84 % of cuts: it wins only if the cut rate per connection falls by more than half, and nothing on disk says whether cuts follow the meter · _USABLE_
- **INFERENCE** · The meter read at each reconnect after a cut tells whether cuts come with the budget overdrawn; the patched hunter records exactly that, so one day on two streams answers I01 without betting the record on it · _USABLE_
- **ASSUMPTION** · A restart costs the mints watched at that moment, about 480, the same order as two hours of blind windows · _WEAK_
- **HYPOTHESIS** · The cuts are the meter: drawing half as much would cut the cut rate by more than half · _CONTESTED_
- **UNKNOWN** · The meter's unit and refill; whether a keyed free failover would be served at all on the free plan's websocket limits · _UNVERIFIED_

## OPTIONS

| option | status | do | circle | door |
|---|---|---|---|---|
| A-restart-two-streams-measure | open | Stop the hunter and let the scheduled guard start the patched one on two streams; journal the restart gap; for 24 h read the meter logged at every post-cut handshake. If most post-cut meters are negative, a one-stream trial is the next decision; if not, the budget is not the driver and two streams stay | inside | reversible |
| B-restart-one-stream | open | Restart the patched hunter now with IRV_FLOW_STREAMS=1 and compare blind seconds a day against 343 | inside | reversible |
| C-wait-natural-restart | open | Leave pid 20212 running; the patch goes live whenever the guard or a logon next starts the hunter | inside | reversible |
| D-free-keyed-failover | VETOED | Add a third stream on the Helius free plan that connects only while both public streams are down, about 100 MB a day against 1M credits a month | edge | reversible |
| E-paid-feed | VETOED | Move the hunter to a paid feed | inside | reversible |

## SURVIVAL
- **A-restart-two-streams-measure** fails if the guard does not restart it promptly and the gap grows past the watched mints; or the patched code faults live in a way the tests did not reach; or a day of meters is ambiguous and buys nothing
- **B-restart-one-stream** fails if the cut rate per connection holds and every cut the twin used to absorb becomes a blind window: about 143 cuts a day at 2 s or more, worse than today
- **C-wait-natural-restart** fails if outages keep going unjournalled and unmeasured for an unknown span, 5 % of records touched with no record of which
- **D-free-keyed-failover** fails if the free plan's websocket limits refuse it, or the failover's own reconnect is too slow to cover a 2 s window; and it needs a key the prereg's 'keyless' feed excludes, so an amendment and a re-pin · VETOED: rule 2: the prereg names a keyless feed; the change waits on an amendment and the operator's signup, neither of which exists
- **E-paid-feed** fails if there are no funds · VETOED: F05: no funds; and rule 2, the prereg names the public RPC

## INCENTIVES
- Claude first: Claude wrote the patched hunter and the diagnostic, and a restart puts its own code live the moment it was written; it also ran the extra connection that drew on the same IP budget during the hunter's busiest hour. The check is that the one-stream trial, the change Claude's first read pointed at, is ranked behind the measurement because the twin absorbs 84 % of cuts, and that the restart is done by the scheduled guard, not by this session, after a session-started hunter died without cause on 2026-10-03. The operator: wants the hunter whole at zero cost; a restart costs the mints watched at that moment. Nobody else: no counterparty, zero capital.

## SYSTEM EFFECT
- **A-restart-two-streams-measure**: a feed change is measured on the instrument before it is bet on the record; every outage from now on is in journal/gaps
- **B-restart-one-stream**: the hunter's redundancy is traded away on a contested hypothesis
- **C-wait-natural-restart**: a fix sits unshipped until chance ships it
- **D-free-keyed-failover**: a second provider enters the record; every record must say which feed saw its prints
- **E-paid-feed**: the record's cost floor rises above zero

## THE DOOR
- Reversible, decided now: the restart on two streams with the patched code: IRV_FLOW_STREAMS and the code both revert by a restart
- Irreversible, gated: the mints watched at the restart are lost and never backfilled. It waits on: the suite green with the 08-28 gate, the diagnostic connection closed so the IP is back to two subscriptions, and the operator's instruction to make it work on the free tier

## RECOMMENDATION
**A-restart-two-streams-measure.** RULED: restart the patched hunter now on two streams through the guard, journal the restart gap, and read the meter at every post-cut handshake for 24 h before touching the stream count. One stream (B) is the obvious move and the likely wrong one: the twin absorbs 84 % of cuts and H01 is contested. Waiting (C) leaves the outages unrecorded. The keyed failover (D) and a paid feed (E) are vetoed on the prereg and on funds. · _USABLE_

## Gates on the irreversible half

| gate | rule | measured | holds | reading | from |
|---|---|---|---|---|---|
| suite-green | tests_passed >= 48 | 48 | **YES** | BELIEF | python -m pytest, 2026-10-05, after the last change to ops/hunt.py |
| known-answer-0828 | gate_0828_green >= 1 | 1 | **YES** | BELIEF | tests/test_known_answer_0828.py in that run |
| diagnostic-closed | extra_connections_open <= 0 | 0 | **YES** | BELIEF | diag1002.py exited 0 at 15:28Z |
| operator-asked | operator_asked_free_tier_fix >= 1 | 1 | **YES** | BELIEF | the operator, 2026-10-05: 'make this work on the free tier' |

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
| A01 | L2 | ASSUMPTION | **WEAK** | 0.35 | 0.00 |
| H01 | L2 | HYPOTHESIS | **CONTESTED** | 0.23 | 0.23 |
| U01 | L0 | UNKNOWN | **UNVERIFIED** | 0.00 | 0.00 |
| M01 | L1 | FACT | **USABLE** | 0.95 | 0.00 |
| opt-A-restart-two-streams-measure | L3 | INFERENCE | **USABLE** | 0.60 | 0.00 |
| opt-B-restart-one-stream | L3 | HYPOTHESIS | **WEAK** | 0.35 | 0.00 |
| opt-C-wait-natural-restart | L3 | FACT | **USABLE** | 0.60 | 0.00 |
| opt-D-free-keyed-failover | L3 | HYPOTHESIS | **KILLED** | 0.00 | 0.60 |
| opt-E-paid-feed | L3 | FACT | **KILLED** | 0.00 | 0.60 |
| R01 | L4 | INFERENCE | **USABLE** | 0.60 | 0.00 |
