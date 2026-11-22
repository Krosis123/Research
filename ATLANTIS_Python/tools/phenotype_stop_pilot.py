"""Pilot stopping audit for the same conditioned macrophage ensemble as seed 4."""
import json
import random
from pathlib import Path
from scipy.stats import beta

data = Path(__file__).resolve().parents[1] / "validation" / "large_dynamics"
spec = json.loads((data/"nonlinear.json").read_text())
rules = dict(line.split(", ", 1) for line in (data/"model.bnet").read_text().splitlines()[1:] if line)
code = {name: compile(expr.replace("!", " not ").replace("&"," and ").replace("|"," or ").strip(),
                      "<model>", "eval") for name,expr in rules.items()}
names = sorted(set(rules) | set(spec["inputs"]))
rng = random.Random(spec["seed"])
initial = {n:rng.randrange(2) for n in names}
marker = "v_Apoptosis"
size = 1 << len(spec["free"])

def outcome(branch, limit=512):
    state = initial.copy()
    state.update({n:(branch >> j)&1 for j,n in enumerate(spec["free"])})
    path, seen = [], {}
    for _ in range(limit+1):
        key = bytes(state[n] for n in names)
        if key in seen:
            cycle = path[seen[key]:]
            ix = cycle.index(min(cycle))
            phenotype = tuple(sorted({row[names.index(marker)] for row in cycle}))
            return tuple(cycle[ix:]+cycle[:ix]), phenotype
        seen[key] = len(path)
        path.append(key)
        state.update({n:int(eval(c,{"__builtins__":{}},state)) for n,c in code.items()})
    return None,None

def audit():
    # First eight uniform draws propose witnesses. Only fresh iid draws certify.
    proposal = random.Random(810)
    samples = [outcome(proposal.randrange(size)) for _ in range(8)]
    known = {p for _,p in samples if p is not None}
    cycles = {c for c,_ in samples if c is not None}
    holdout = random.Random(811)
    misses = sum(outcome(holdout.randrange(size))[1] not in known for _ in range(64))
    upper = 1. if misses==64 else float(beta.ppf(.95,misses+1,64-misses))
    # Exhaustive scoring only after the single stopping decision.
    stop = upper <= .05
    reference = [outcome(b) for b in range(size)]
    assert all(c is not None for c,_ in reference)
    return dict(free_inputs=spec["free"],marker=marker,branches=size,discovery_draws=8,
                holdout_draws=64, misses=misses, upper95=upper, stop=stop,
                discovered_cycles=len(cycles),exact_cycles=len({c for c,_ in reference}),
                observed_marker_classes=sorted(known),exact_unseen_marker_mass=sum(p not in known for _,p in reference)/size)
if __name__=="__main__":
    result=audit()
    (data/"phenotype-audit.json").write_text(json.dumps(result,indent=2))
    print(result)
