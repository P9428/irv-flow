# WHAT RUNS UNATTENDED ON THIS MACHINE

⛔ THIS FILE IS A RECORD, NOT A MECHANISM. The tasks live in Windows Task Scheduler (ops/register_tasks.ps1
creates them). Each one writes a state file an instrument reads — the registration is never trusted, only the effect.

| task | cadence | runs | writes | guard |
|---|---|---|---|---|
| `irv-flow - HUNT GUARD` | at logon + every 5 min | `ops/hunt_guard.ps1` → starts `ops/hunt.py` if no live heartbeat | `monitor/hunt-heartbeat.json`, `journal/live/<day>.jsonl`, `monitor/flow-alerts.log` | `ops/freshness.py` (RED at 10 min), stage 1 of the constraint scan |
| `irv-flow - LOOP` | daily 05:20 | `ops/loop.py` — the ten-instrument battery | `monitor/loop-status.json`, `out/*`, `docs/digest.html`, `journal/MANIFEST` pins, push to origin | `tests/test_loop_fleet.py` |

The hunter is the collector. There is no capture stream dependency; mimicry captures, if they resume, are a second witness only.
