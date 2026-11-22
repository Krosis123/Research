"""Controlled finite-population trial. No physical device calls."""
import json,random,ast
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.stats import beta
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
base=Path(__file__).resolve().parents[2]/"research_sources"
ref=json.loads((base/"ra243-witnesses.json").read_text())
names=ref["order"]; env=ref["external"]
panel=["v_CCL2_Fibroblast___Extracellular_Space","v_NFKBIA_rna"]
indices=[names.index(x) for x in panel]
rules=dict(line.split(", ",1) for line in (base/"ra243-model.bnet").read_text().splitlines()[1:] if line)
codes=[]
for n in names:
    tree=ast.parse(rules[n].replace("!"," not ").replace("&"," and ").replace("|"," or ").strip(),mode="eval")
    assert all(isinstance(x,(ast.Expression,ast.Name,ast.Load,ast.BoolOp,ast.UnaryOp,ast.And,ast.Or,ast.Not,ast.Constant)) for x in ast.walk(tree))
    codes.append(compile(tree,"<model>","eval"))
def label(x):
    path=[]; seen={}
    for t in range(257):
        if x in seen:
            cycle=path[seen[x]:]
            return "/".join("".join(map(str,sorted({z[i] for z in cycle}))) for i in indices)
        seen[x]=t;path.append(x)
        ctx=env|dict(zip(names,x))
        x=bytes(bool(eval(c,{"__builtins__":{}},ctx)) for c in codes)
    raise RuntimeError("unresolved reference")
rng=random.Random(260711)
groups=[[] for _ in range(4)]
for g in range(4):
    for j in range(64):
        x=bytearray(rng.randrange(2) for n in names)
        for k,i in enumerate(indices):x[i]=(g>>k)&1
        groups[g].append(label(bytes(x)))
truth=Counter(x for group in groups for x in group)
# One-step RXX plus independent RY on the first wire (all strata reachable).
qc=QuantumCircuit(2);qc.rxx(np.pi/3,0,1);qc.ry(np.pi/3,0);qc.measure_all()
reps=500;draws=8
mem=AerSimulator().run(qc,shots=reps*draws,memory=True,seed_simulator=73).result().get_memory()
arms={}
for arm in ("uniform","classical_same_kernel","aer"):
    rng=random.Random(174)
    results=Counter()
    for rep in range(reps):
        found=set()
        for j in range(draws):
            if arm=="aer":g=int(mem[draws*rep+j],2)
            elif arm=="uniform":g=rng.randrange(4)
            else:g=(3 if rng.random()<.25 else 0) ^ int(rng.random()<.25)
            found.add(rng.choice(groups[g]))
        mass=sum(v for k,v in truth.items() if k not in found)/256
        # Equal-target-weight strata, independent conditional sampling, one fixed look.
        misses=[sum(rng.choice(group) not in found for _ in range(96)) for group in groups]
        upper=sum(1 if n==96 else beta.ppf(1-.05/4,n+1,96-n) for n in misses)/4
        results["stop"]+=int(upper<=.05)
        results["false_stop"]+=int(upper<=.05 and mass>.05)
        results["found_all"]+=int(mass==0)
    arms[arm]=dict(results)
result=dict(panel=panel,pool_seed=260711,context="same as ra243-witnesses.json",strata_labels=groups,
            outcomes=truth,repetitions=reps,discovery_draws=8,audit_draws=384,arms=arms)
(base/"ra243-stopping-trial.json").write_text(json.dumps(result,indent=2))
print(truth,arms)
