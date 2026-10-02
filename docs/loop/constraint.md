# BINDING CONSTRAINT SCAN
Find the single current bottleneck in the on-chain edge program. Report and STOP.
Target: 15 minutes. If it runs past 25, you are writing rather than diagnosing.

## ADVERSARIAL PREMISE — read before step 0, not after
Your reasoning is motivated. You will nominate the constraint your existing skills solve,
that is most pleasant, that you already started and are invested in being right about, or
that is a new frame rather than the unfinished thing in front of you. Those candidates need
a HIGHER evidence bar than their rivals. If the real constraint needs a skill nobody has,
an unpleasant conversation, or waiting — say it. Comfort is a signal of error, not of fit.

Claude's documented failure in this program, six logged instances: substituting a
distribution over one quantity for a distribution over a correlated one, then reasoning
from the substitute. Entry rank for entry time, twice. Supply consumption for entry timing,
once — that one produced a verdict that had to be VACATED. Read CALIBRATION.md before you
scan.

## BASELINE — pass these or the scan stops
- [ ] Last contract's MANIFEST and goldens verify against their committed report. Any delta
      is explained before the scan proceeds.
- [ ] `contracts/CURRENT.md` state reported. If a contract is in flight, IT is the
      constraint and the scan ends there.
- [ ] `git status` and unpushed commit count. A local-only ordering-proof commit is not a
      proof.

## STEP 0 — IS THE OUTPUT UNIT STILL RIGHT?
State the single unit of real, external, measurable output this program exists to produce.
Then ask: has the operator's stated goal moved since this unit was set? If it has, every
downstream stage may be measuring the wrong clock.

This step exists because it already happened. The horizon moved from hold-to-graduation to
seconds-to-hours in-curve, and M-WI-12, M-WI-13, and M-WI-14 had already measured the
abandoned horizon. A scan that assumes the output unit is stable cannot catch that, and it
was the largest error the program made.

If the unit has moved, STOP HERE. Re-deriving the value chain is the constraint and nothing
else is.

## STEP 1 — MAP
The value chain as an ordered sequence, input → output. One line per stage. The whole
chain, not the interesting part.

## STEP 2 — SCAN THE SOURCE OF TRUTH
Per stage, cite on-disk evidence: a committed artifact, a verified MANIFEST, a hash, a git
state. A label, plan, README, or intention is NOT evidence. A summary of an artifact is NOT
the artifact. Unavailable → mark UNKNOWN, never inferred. The count of UNKNOWNs is itself a
finding.

## STEP 3 — ONE PLAIN SENTENCE PER STAGE
What it does and what it produces. No jargon, no abstraction. A stage you cannot say
plainly is a stage you do not understand, and that is a constraint candidate. Name any that
fail.

This step has fired repeatedly: it is what separated detection latency from actionable
latency, liquidity from price, and entry rank from entry time. Each confusion produced a
wrong verdict before it was named.

## STEP 4 — MEASURE OR BUILD
Is the candidate constraint an unmeasured fact that is cheaply knowable, or a known fact
requiring a build? Unmeasured and knowable → MEASURING IS THE CONSTRAINT and no build
starts.

This is the highest-value line in the scan. Nine contracts named build constraints over
facts that were cheap to measure.

## STEP 5 — NAME ONE
Symptom versus cause: the visibly failing stage is often downstream of the binding one. One
constraint, not a list. If two compete, name what was given up by choosing.

## STEP 6 — CLASSIFY
- **SELF** — movable today.
- **DEPENDENT** — waiting on another party. Then the constraint is EXPOSURE to that
  dependency, and the move is reducing the exposure or building a parallel path — never
  waiting attentively.
- **STRUCTURAL** — unmovable at current resources. Say so, and name what the program should
  do instead of pretending.

## STEP 7 — THE FALSIFIABLE MOVE
One action, completable today, with an observable proof signal. No stateable proof means the
move is not specified.

## OUTPUT — six lines, prose not form
```
OUTPUT UNIT (and whether it moved):
THE CONSTRAINT + the on-disk evidence it is binding:
MEASURE OR BUILD:
CLASS and its implication:
THE MOVE, completable today:
PROOF IT MOVED, observable tonight:
```

Plus, only if either applies:
```
STAGES THAT FAILED THE PLAIN-SENTENCE TEST:
WHAT I WANT THE CONSTRAINT TO BE, AND WHY I RULED IT OUT:
```

## HARD RULES
Effort on a non-constraint produces ZERO — not less, zero. It yields inventory, polish, or
optionality, none of which reach the output. A wrong diagnosis is a fully spent day with
nothing at the end of it. Precision of diagnosis outranks volume of action.

Re-run whenever state changes. Constraints move; yesterday's answer is stale by default.

You are the FINDER, not the referee (CF-002). The operator writes his own determination
BEFORE reading yours. Where you diverge, the GROUNDED reading wins — the one tracing to a
committed artifact, not the more confident one. Log the divergence in
`docs/loop/divergence.md`.

Report and STOP. No contract, no preregistration, no starting the move.
