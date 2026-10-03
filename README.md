# irv-flow

The flow-filtered pump.fun reclaim, hunted live 24/7 on paper. Read `prereg/IF-01-PREREGISTRATION.md` first.

    python ops/hunt.py          # the hunter (runs forever; the guard task keeps it alive)
    python ops/readout.py       # today's readout -> out/readout.txt
    python ops/freeze.py IF-02  # pin a ruled prereg (first run freezes; later runs re-pin after an AMENDMENT)
    python ops/decide.py KEY    # rule docs/decisions/KEY.json through RI (ri_core); the ruling is pinned in journal/decisions
    python ops/loop.py          # seal, score forward captures, gate, readout
    python ops/predict.py       # the foresight journal's pen (docs/loop/foresight.md); no args = the open questions, blind
    python -m pytest            # includes the 08-28 replication gate (reads ~/mimicry, read-only)

ZERO CAPITAL. NO KEY. NO WALLET. NO ORDER. NO POSITION.
