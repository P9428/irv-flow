---
description: MR-01, irv-flow's morning scan — reproduce the last close, re-check what changed, name the constraint, answer the three questions
---

The contract is `docs/contracts/MR-01-morning-scan.md`. The First Law binds: reality is the final authority; when a
model and an observation disagree, the observation stays and the model is revised.

1. Build the sheet (the task `irv-flow - MORNING` runs this at 06:00 Central; run it again only if today's is missing):

```bash
cd /c/Users/newce/irv-flow && python ops/morning.py build
```

2. Read `out/morning/<today>.md` in full.

3. If it is STOPPED: for each `STOP field: old → new` line, find why the number moved, from the files named on the line.
   Close the row only with a revision of the model, never by changing the observation:
   `python ops/morning.py explain <D-id> "<evidence>" --revised <belief|debt|commit|close|ruling> <ref>`.
   A belief or a debt line is written with `ops/predict.py`, a ruling with `ops/decide.py`, a code fix is a commit;
   today's close already carries a `corrects` line for every delta (`--revised close close/<today>`). If none of these
   is true yet, leave the row open and say so: the day stays STOPPED.

4. Answer against the constraint the sheet named, not in the abstract. The Why must contain its id:
   `python ops/morning.py answer --leverage ".." --inversion ".." --attention ".." --move ".." --why ".."`.
   No verdict, no mean against a bar and no z off a look boundary (rule 3); a LOOK is the readout's to speak.

5. `python ops/morning.py check` and report, briefly: the constraint and its line, the status, each open operator
   action, each open disagreement, and the Highest Leverage Move with its Why.

Write nothing else. Never touch `prereg/`, an existing journal day, the hunter, or `docs/loop/`.
