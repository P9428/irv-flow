"""THE RULING — one decision through RI (ri_core, ~/Reality-Infrastructure), as ~/hustle/ppg/decide.py rules PPG's.

  python ops/decide.py 2026-10-03-if02-freeze

Input   docs/decisions/<date>-<slug>.json, written AFTER going to look (a step with no read is not that step)
Output  docs/decisions/<date>-<slug>.md, the Decision Output · ri-log-<date>-<slug>.bin, the signed evidence log ·
        journal/decisions/<date>-<slug>.jsonl, the rulings and the log root, pinned. A decision is ruled once.

Enforced, not recited:
  every claim, option and the recommendation is FACT, INFERENCE, ASSUMPTION, HYPOTHESIS or UNKNOWN; the label caps
  its mass and names what it may rest on; UNKNOWN gets none
  `looked` names what was read and what was not; `who_profits` answers for Claude first
  every option states how it fails; not survivable is a veto; outside the circle and irreversible is a veto
  every option states the rule the operation lives under if it becomes the pattern
  the door is split: the reversible half is decided now, the irreversible half waits on gates, each a logged predicate
  the recommendation may not point at a vetoed option, and it is a ruling (0.60), never a fact

Fusion is the cautious rule: two 0.6 sources do not make 0.84, and disagreement lands on the empty set.
A ruling is not a verdict (rule 3) and moves no frozen parameter (rule 2). ZERO CAPITAL: no option carries a dollar.
"""
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal as D

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.environ.get("RI_PATH", r"C:\Users\newce\Reality-Infrastructure\reference-implementation"))
import common as C            # noqa: E402
import journal as J           # noqa: E402
from ri_core.identity import Identity, LocalAuthority      # noqa: E402
from ri_core.log import EvidenceLog                        # noqa: E402
from ri_core.project import project, submit                # noqa: E402
from ri_core.provenance import ProvenanceGraph             # noqa: E402
from ri_core.reconcile import BeliefWeights                # noqa: E402
from ri_core.rules import RuleStore                        # noqa: E402
from ri_core.serialization import encode                   # noqa: E402

DDIR = os.path.join(C.ROOT, "docs", "decisions")
ANCHOR, SEED = "irv-flow-decide", b"irv-flow-decide-ri-v1"
FRAME, OMEGA = ("alive", "dead"), "alive,dead"
M, P, T, E = "measured", "inferred-from-proxy", "true-as-of-date-decaying", "estimated"
SRC = {"disk": ("0.95", [M]), "arith": ("0.95", [M]), "operator": ("0.70", [M]), "web": ("0.45", [T]),      # declared masses: policy, not measurement
       "join": ("0.60", [P]), "ruling": ("0.60", [P]), "assumed": ("0.35", [E]), "hypothesis": ("0.35", [E])}
LABELS = {"FACT": ("disk", "arith", "operator", "web"), "INFERENCE": ("join", "ruling"), "ASSUMPTION": ("assumed",),
          "HYPOTHESIS": ("hypothesis",), "UNKNOWN": ()}
OWN = {"FACT": "ruling", "INFERENCE": "ruling", "ASSUMPTION": "assumed", "HYPOTHESIS": "hypothesis"}       # what an open option rests on


class Ev:
    def __init__(self, as_of):
        self.auth = LocalAuthority(anchor_id=ANCHOR, seed=SEED)
        self.log, self.graph, self.rules = EvidenceLog(), ProvenanceGraph(), RuleStore()
        self.issued, self.bind, self.as_of = set(), {}, as_of

    def gate(self, name, spec):
        self.log.append(self.rules.register(f"irv-{name}", 1, spec, 0))
        self.bind[f"gate:{name}"] = (f"irv-{name}", 1)

    def obs(self, oid, source, prop, mass, ltime, unc, detail, fields=None):
        if source not in self.issued:
            self.auth.issue_identity(source)
            self.issued.add(source)
        u = {"kind": "observation", "id": oid, "source_id": source, "proposition": prop, "ltime": ltime,
             "payload": {"frame": list(FRAME), "mass": mass, "uncertaintyType": sorted(unc), "detail": detail}, **(fields or {})}
        u["sig"] = self.auth.sign(Identity(identity_id=source, anchor_id=ANCHOR, name=source), encode(dict(u)))
        submit(u, self.log, self.graph, self.auth)

    def state(self):
        return project(self.log, self.graph, self.auth, self.rules, self.bind, self.as_of)["propositions"]


def masses(belief):
    bw = BeliefWeights.from_weights(frozenset(belief["frame"]),
                                    {frozenset(k.split(",")) if k else frozenset(): D(str(v)) for k, v in belief["weights"].items()})
    return {",".join(sorted(s)): v for s, v in bw.to_mass_dict().items()}


def ruling(m):
    e, a, d = m.get("", D(0)), m.get("alive", D(0)), m.get("dead", D(0))
    return ("CONTESTED" if e > 0 else "KILLED" if d >= D("0.6") else "USABLE" if a >= D("0.6") else
            "WEAK" if a >= D("0.35") else "LEANS-DEAD" if d >= D("0.35") else "UNVERIFIED")


def check(dec):
    bad = []
    for c in dec["claims"] + [dec["recommendation"]]:
        if c.get("label") not in LABELS:
            bad.append(f"{c.get('id')}: label")
        elif any(s[0] not in LABELS[c["label"]] for s in c.get("src", [])):
            bad.append(f"{c['id']}: a {c['label']} cannot rest on {[s[0] for s in c['src']]}")
        elif c["label"] != "UNKNOWN" and not c.get("src"):
            bad.append(f"{c['id']}: {c['label']} with no source")
    if not (dec.get("who_profits") or "").strip():
        bad.append("who_profits is empty (answer for Claude first)")
    if not dec.get("looked"):
        bad.append("looked is empty: name what was read before reasoning")
    for o in dec["options"]:
        i = o.get("id")
        if o.get("label") not in LABELS:
            bad.append(f"option {i}: label")
        if not (o.get("fails_if") or "").strip():
            bad.append(f"option {i}: fails_if")
        if o.get("survivable") not in (True, False) or o.get("reversible") not in (True, False):
            bad.append(f"option {i}: survivable and reversible")
        if o.get("competence") not in ("inside", "edge", "outside"):
            bad.append(f"option {i}: competence")
        if not (o.get("system_effect") or "").strip():
            bad.append(f"option {i}: system_effect")
    if dec["recommendation"].get("option") not in {o.get("id") for o in dec["options"]}:
        bad.append("recommendation.option names no option")
    if not dec.get("split", {}).get("reversible_now") or not dec.get("split", {}).get("irreversible_gated"):
        bad.append("the door is not split: reversible_now and irreversible_gated")
    if bad:
        raise ValueError("the decision file breaks the laws:\n  " + "\n  ".join(bad))


def veto(o):
    return ("the downside is not survivable" if not o["survivable"] else
            "outside the circle and irreversible" if o["competence"] == "outside" and not o["reversible"] else o.get("veto", ""))


def constraint():
    """The line the last constraint scan named, read from its own output."""
    try:
        with open(os.path.join(C.OUT, "constraint.txt"), encoding="utf-8") as fh:
            return next((line.strip() for line in fh if line.startswith("THE CONSTRAINT:")), "no constraint scan on disk")
    except FileNotFoundError:
        return "no constraint scan on disk"


def run(key):
    if os.path.exists(os.path.join(J.JOURNAL, "decisions", f"{key}.jsonl")):
        raise ValueError(f"{key} is already ruled and pinned; a changed question is a new decision file")
    with open(os.path.join(DDIR, f"{key}.json"), encoding="utf-8") as fh:
        dec = json.load(fh)
    check(dec)
    opts = [dict(o, veto=veto(o)) for o in dec["options"]]
    rec = dec["recommendation"]
    chosen = next(o for o in opts if o["id"] == rec["option"])
    if chosen["veto"]:
        raise ValueError(f"the recommendation points at a vetoed option ({chosen['id']}: {chosen['veto']})")

    claims = [(c["id"], c.get("layer", "L2"), c["label"], c["text"], [tuple(s) for s in c.get("src", [])]) for c in dec["claims"]]
    claims.append(("M01", "L1", "FACT", constraint(), [("disk", "alive", "out/constraint.txt", "")]))
    claims += [(f"opt-{o['id']}", "L3", o["label"], f"[{'VETOED' if o['veto'] else 'OPEN'}] {o['do']}",
                [("ruling", "dead", o["veto"], "veto")] if o["veto"] else
                [(OWN[o["label"]], "alive", o.get("basis", ""), "")] if o["label"] != "UNKNOWN" else []) for o in opts]
    claims.append((rec["id"], "L4", rec["label"], rec["text"], [tuple(s) for s in rec["src"]]))

    day = datetime.fromisoformat(dec["as_of"]).replace(tzinfo=timezone.utc)
    lt = int(day.timestamp())
    ev = Ev(lt + 86399)
    for cid, _layer, label, text, srcs in claims:
        for n, (pol, stance, name, note) in enumerate(srcs):
            mass, unc = SRC[pol]
            ev.obs(f"{key}-{cid}:{n}", name or "unnamed", f"{key}-{cid}", {stance: D(mass), OMEGA: D(1) - D(mass)}, lt, unc,
                   {"claim": text, "note": note, "policy": pol, "label": label})
    for g in dec.get("gates", []):
        ev.gate(g["name"], [g["op"], ["field", g["field"]], ["const", g["bar"]]])
        ev.obs(f"gate:{g['name']}:{key}", "measure", f"gate:{g['name']}", {"alive": D("0.9"), OMEGA: D("0.1")}, lt, [M],
               {"claim": f"{g['field']} = {g['measured']}"}, {g["field"]: g["measured"]})
    state = ev.state()
    ruled = []
    for cid, layer, label, text, _srcs in claims:
        b = state.get(f"{key}-{cid}", {}).get("belief")
        mm = masses(b) if b is not None else {}
        ruled.append({"claim": cid, "layer": layer, "label": label, "text": text, "ruling": ruling(mm) if mm else "UNVERIFIED",
                      "alive": f"{mm.get('alive', D(0)):.2f}", "dead": f"{mm.get('dead', D(0)):.2f}"})
    gates = [{"gate": g["name"], "rule": f"{g['field']} {'>=' if g['op'] == 'ge' else '<='} {g['bar']}", "measured": g["measured"],
              "holds": (g["measured"] >= g["bar"]) if g["op"] == "ge" else (g["measured"] <= g["bar"]),
              "reading": "BELIEF" if state[f"gate:{g['name']}"]["belief"] is not None else "NO BELIEF", "from": g.get("from", "")}
             for g in dec.get("gates", [])]
    root, size = ev.log.root().hex(), len(ev.log)
    with open(os.path.join(DDIR, f"ri-log-{key}.bin"), "wb") as fh:
        fh.write(encode({"kind": "log_export", "anchor": ANCHOR, "entries": [ev.log.entry(i) for i in range(size)]}))

    L = [f"# Decision · {dec['decision']}", "", f"{dec['as_of']} · asked by {dec['asked_by']} · log root `{root}` · size {size}", "",
         "## REALITY", "Looked at before reasoning: " + "; ".join(dec["looked"]) + "."]
    L += [f"- **{r['label']}** · {r['text']} · _{r['ruling']}_" for lab in LABELS for r in ruled if r["layer"] in ("L0", "L1", "L2") and r["label"] == lab]
    L += ["", "## OPTIONS", "", "| option | status | do | circle | door |", "|---|---|---|---|---|"]
    L += [f"| {o['id']} | {'VETOED' if o['veto'] else 'open'} | {o['do']} | {o['competence']} | {'reversible' if o['reversible'] else 'IRREVERSIBLE'} |" for o in opts]
    L += ["", "## SURVIVAL"] + [f"- **{o['id']}** fails if {o['fails_if']}" + (f" · VETOED: {o['veto']}" if o["veto"] else "") for o in opts]
    L += ["", "## INCENTIVES", f"- {dec['who_profits']}"]
    L += ["", "## SYSTEM EFFECT"] + [f"- **{o['id']}**: {o['system_effect']}" for o in opts]
    L += ["", "## THE DOOR", f"- Reversible, decided now: {dec['split']['reversible_now']}", f"- Irreversible, gated: {dec['split']['irreversible_gated']}"]
    L += ["", "## RECOMMENDATION", f"**{rec['option']}.** {rec['text']} · _{ruled[-1]['ruling']}_"]
    L += ["", "## Gates on the irreversible half", "", "| gate | rule | measured | holds | reading | from |", "|---|---|---|---|---|---|"]
    L += [f"| {g['gate']} | {g['rule']} | {g['measured']} | **{'YES' if g['holds'] else 'NO'}** | {g['reading']} | {g['from']} |" for g in gates]
    L += ["", "## Ledger", "", "| claim | layer | label | ruling | m(alive) | m(dead) |", "|---|---|---|---|---|---|"]
    L += [f"| {r['claim']} | {r['layer']} | {r['label']} | **{r['ruling']}** | {r['alive']} | {r['dead']} |" for r in ruled]
    with open(os.path.join(DDIR, f"{key}.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")
    J.write_file("decisions", key, [{"at": C.stamp(), "decision": dec["decision"], "root": root, "size": size, "recommended": rec["option"],
                                     "ruling": ruled[-1]["ruling"], "door_open": all(g["holds"] for g in gates),
                                     "vetoed": {o["id"]: o["veto"] for o in opts if o["veto"]}, "rows": ruled, "gates": gates}])
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(L))
    print(f"\nlog root {root} · size {size} · pinned as journal/decisions/{key}.jsonl")


if __name__ == "__main__":
    try:
        run(*sys.argv[1:])
    except (ValueError, TypeError, FileNotFoundError) as e:
        sys.exit(f"REFUSED: {e}\n{__doc__.split('Input')[0].strip()}")
