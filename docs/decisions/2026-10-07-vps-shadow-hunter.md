# Decision · The owed ruling: deploy ops/systemd/irv-flow-hunt.service on the VPS as a second witness. The laptop lost 13.2 h of IF-02 sample on 2026-10-06/07 to a flat battery and a guard that waited for a logon; look 2 is about 3 days out. Move the hunter to the VPS now, run it there as a shadow that counts toward nothing, or leave it on the laptop alone?

2026-10-07 · asked by the operator, 2026-10-07: 'Sometimes the laptop shuts off. You sure we shouldn't run it on the VPS?', then 'Go with this: Install the hunter on the VPS as a shadow run that counts toward nothing. It writes only on the VPS.' · log root `125c54153bc849ccdd026d79abd7477b0a1dcb9b8308e1e58bb65292ca5db67a` · size 17

## REALITY
Looked at before reasoning: Windows System log 2026-10-06: Kernel-Power 524 'Critical Battery Trigger Met' 22:15:35Z, User32 1074 power off 22:15:39Z, boot 23:44Z; Security 4624 first logon 11:23Z; monitor/hunt-guard.log first start 11:23Z; journal/gaps/2026-10-07.jsonl 13.2 h blind; Get-ScheduledTask: irv-flow - HUNT GUARD Interactive, DisallowStartIfOnBatteries and StopIfGoingOnBatteries true; LOOP and MORNING S4U; the VPS, read-only over ssh: up 52 days, / 30 GB free of 52 (41 %), 1 CPU, 1962 MB RAM with about 220 MB available, Python 3.12.3, no websockets module, no /opt/irv-flow, irv-flow-hunt inactive, the public RPC answers getSlot HTTP 200 in 68 ms; enp1s0 received 1759 GB and sent 548 GB in 52 days; pid 20056 working set 67 MB on the laptop; laptop websockets 11.0.3; ops/hunt.py imports common, excursion, journal, rule; it reads no prereg file; it writes journal/, monitor/ and its heartbeat under its own root; prereg/IF-01 and IF-02: the feed is the keyless public logsSubscribe; no clause names the machine; ops/readout.py and src/foresight.py rows(): IF-02 counts journal/live and journal/forward on the laptop; nothing reads a VPS path; docs/decisions/2026-10-05-hunter-free-tier.md: the public RPC meters per IP; the laptop's meter reads endpoint-remaining about -27000 at every handshake; NOT looked: the VPS plan's bandwidth allowance and whether inbound traffic is billed; the VPS's own cut rate under its own meter.
- **FACT** · The laptop shut down on a critical battery at 22:15Z and the hunter stayed down until the 11:23Z logon: 13.2 h with no IF-02 sample · _USABLE_
- **FACT** · The VPS has run 52 days without a reboot, has 30 GB free and about 220 MB of RAM available, and reaches the public RPC in 68 ms from its own IP · _USABLE_
- **FACT** · IF-02 counts only the laptop's journal/live and journal/forward; a VPS journal enters no look, readout or ledger unless code is changed to read it · _USABLE_
- **FACT** · The operator ruled: a shadow on the VPS that counts toward nothing and writes only on the VPS · _USABLE_
- **FACT** · THE CONSTRAINT: MACHINE — last suite 2026-10-07T13:58:19+00:00 rc 1 (FAILED tests/test_attribution.py::test_every_trade_in_the_jo) · _USABLE_
- **INFERENCE** · Three days of overlap show whether the VPS hunter records the same mints, entries and outcomes as the laptop, and how its cut rate compares under its own meter, before anything is bet on it · _USABLE_
- **INFERENCE** · A cut-over now restarts the instrument inside the window look 2 reads, on a host never run, with no sync into the laptop's LOOP · _USABLE_
- **UNKNOWN** · The VPS plan's bandwidth allowance and whether about 2 TB a month of inbound websocket traffic is billed · _UNVERIFIED_

## OPTIONS

| option | status | do | circle | door |
|---|---|---|---|---|
| A-shadow-now | open | Install ops/hunt.py and its four src modules in /opt/irv-flow on the VPS with websockets 11.0.3 in a venv, run it under systemd as irv-flow-shadow (Restart=always, MemoryMax 400M, Nice 10); it writes only under /opt/irv-flow and nothing on the laptop reads it. Compare it with the laptop daily; the switch of primary is its own ruling at A-0001 | inside | reversible |
| B-cut-over-now | VETOED | Make the VPS the primary hunter today and stop the laptop's | edge | reversible |
| C-laptop-only | open | Leave the hunter on the laptop alone and rely on AC power and the guard | inside | reversible |

## SURVIVAL
- **A-shadow-now** fails if its traffic overruns the plan's bandwidth and bills the operator; or it starves the VPS's other jobs of RAM; or a later session reads its journal into a look without a ruling
- **B-cut-over-now** fails if an untested host and a restart land inside look 2's window, and the laptop LOOP has no copy of what the VPS records · VETOED: timing: look 2 is about 3 days out and the operator ruled a shadow (F04)
- **C-laptop-only** fails if the laptop shuts off again: it already did once with the hunter on it

## INCENTIVES
- Claude first: Claude proposed the VPS shadow and the staged move, and installing it is work Claude does and can point to. The check is that the shadow is ruled to count toward nothing until a later ruling at A-0001, so it cannot flatter or rescue IF-02's sample, and that the immediate cut-over Claude could have pushed is laid out and vetoed on timing. The operator: wants a hunter that survives the laptop; bears the VPS bandwidth bill. Nobody else: zero capital, no key, no counterparty.

## SYSTEM EFFECT
- **A-shadow-now**: the instrument is measured on its next host before it is trusted there
- **B-cut-over-now**: an instrument is swapped mid-window on faith
- **C-laptop-only**: the record stays hostage to one laptop

## THE DOOR
- Reversible, decided now: the shadow: install, venv, unit, start; all removed with systemctl disable and rm -rf /opt/irv-flow
- Irreversible, gated: none here; making the VPS primary, or counting any VPS row, is its own ruling at A-0001

## RECOMMENDATION
**A-shadow-now.** RULED: run the hunter on the VPS as a shadow that counts toward nothing and writes only there; compare daily; the move to primary is ruled at A-0001. B is vetoed on timing and on the operator's word; C leaves the record on the machine that just lost 13.2 h. · _USABLE_

## Gates on the irreversible half

| gate | rule | measured | holds | reading | from |
|---|---|---|---|---|---|
| operator-ruled | operator_go >= 1 | 1 | **YES** | BELIEF | the operator, 2026-10-07: 'Go with this' |
| vps-disk-free-gb | disk_free_gb >= 5 | 30 | **YES** | BELIEF | df -h / on the VPS, 2026-10-07 |
| vps-ram-free-mb | ram_available_mb >= 150 | 221 | **YES** | BELIEF | free -m on the VPS, 2026-10-07; the hunter used 67 MB on the laptop |

## Ledger

| claim | layer | label | ruling | m(alive) | m(dead) |
|---|---|---|---|---|---|
| F01 | L0 | FACT | **USABLE** | 0.95 | 0.00 |
| F02 | L0 | FACT | **USABLE** | 0.95 | 0.00 |
| F03 | L0 | FACT | **USABLE** | 0.95 | 0.00 |
| F04 | L0 | FACT | **USABLE** | 0.70 | 0.00 |
| I01 | L2 | INFERENCE | **USABLE** | 0.60 | 0.00 |
| I02 | L2 | INFERENCE | **USABLE** | 0.60 | 0.00 |
| U01 | L0 | UNKNOWN | **UNVERIFIED** | 0.00 | 0.00 |
| M01 | L1 | FACT | **USABLE** | 0.95 | 0.00 |
| opt-A-shadow-now | L3 | INFERENCE | **USABLE** | 0.60 | 0.00 |
| opt-B-cut-over-now | L3 | INFERENCE | **KILLED** | 0.00 | 0.60 |
| opt-C-laptop-only | L3 | INFERENCE | **USABLE** | 0.60 | 0.00 |
| R01 | L4 | INFERENCE | **USABLE** | 0.60 | 0.00 |
