# irv-flow

The flow-filtered pump.fun reclaim, hunted live 24/7 on paper. Read `prereg/IF-01-PREREGISTRATION.md` first.

    python ops/hunt.py          # the hunter (runs forever; the guard task keeps it alive)
    python ops/readout.py       # today's readout -> out/readout.txt
    python ops/loop.py          # seal, score forward captures, gate, readout
    python -m pytest            # includes the 08-28 replication gate (reads ~/mimicry, read-only)

ZERO CAPITAL. NO KEY. NO WALLET. NO ORDER. NO POSITION.
