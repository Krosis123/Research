"""Audit bounded symbolic witnesses with fresh starts; account for censored trajectories."""
import json
import time
from pathlib import Path
import numpy as np
from collections import Counter
from scipy.stats import beta
from transfer_basin_trial import labels, load_bnet
from atlantis.symbolic_cycles import symbolic_cycles

root=Path(__file__).resolve().parents[1]/"research"
net=load_bnet(root/"models/004.bnet")
net.clamped=dict.fromkeys(net.metadata["external_inputs"],0)
start=time.perf_counter()
groups=symbolic_cycles(net,limit=16,seconds=6)
search_seconds=time.perf_counter()-start
witnesses={}
for g in groups:
    for cycle in g["cycles"]:
        j=cycle.index(min(cycle))
        witnesses["".join(cycle[j:]+cycle[:j])]=g["period"]
rng=np.random.default_rng(314159)
counts=Counter()
for batch in range(16):
    starts=rng.integers(2,size=(64,net.n),dtype=np.uint8)
    for name in net.clamped:
        starts[:,net.index(name)]=0
    counts.update(labels(net,starts,160))
report=[]
for key,p in witnesses.items():
    hits=counts[key]+counts[None]
    upper=1 if hits==1024 else beta.ppf(1-.05/len(witnesses),hits+1,1024-hits)
    report.append(dict(cycle=key,period=p,hits=counts[key],upper=float(upper)))
result=dict(conditions=net.clamped,seed=314159,budget=1024,horizon=160,unresolved=counts[None],
            search_seconds=search_seconds,total_seconds=time.perf_counter()-start,
            groups=groups,witnesses=report)
(root/"results/erbb-symbolic-audit.json").write_text(json.dumps(result))
print(len(report),sum(r["upper"]<=.01 for r in report),counts[None],search_seconds,result["total_seconds"])
