"""Confirm ErbB discoveries on fresh runs against the previously audited candidate set."""
from pathlib import Path
import json
import math
import time
import numpy as np
import networkx as nx
from scipy.stats import beta
from transfer_basin_trial import sample, labels, load_bnet

root=Path(__file__).resolve().parents[1]/"research"
frozen=json.loads((root/"results/transfer004-long.json").read_text())
rare={c["packed_cycle"] for c in frozen["cycles"] if c["simultaneous_upper95"]<=.01}
net=load_bnet(root/"models/004.bnet")
net.clamped=frozen["clamps"]
components=[sorted(c) for c in nx.strongly_connected_components(nx.from_numpy_array(net.adjacency,create_using=nx.DiGraph)) if len(c)>1]
report={}
rng_permutation=np.random.default_rng(184)
free=[i for i,name in enumerate(net.names) if name not in net.clamped]
permutation=dict(zip(free,rng_permutation.permutation(free)))
shuffled=[[permutation.get(i,i) for i in c] for c in components]
for method in ("uniform","scc_mixture","permuted_scc","global_bias"):
    blocks={"uniform":components,"scc_mixture":components,"permuted_scc":shuffled,"global_bias":[free]}[method]
    proposal="uniform" if method=="uniform" else "scc_mixture"
    begin=time.perf_counter()
    rows=[]
    for batch in range(16):
        seeds=range(12000+8*batch,12008+8*batch)
        starts=np.concatenate([sample(net,np.random.default_rng(seed),32,proposal,blocks) for seed in seeds])
        words=labels(net,starts,160)
        for j,seed in enumerate(seeds):
            seq=words[j*32:j*32+32]
            hits=[i+1 for i,k in enumerate(seq) if k in rare]
            rows.append(dict(seed=seed,first=min(hits,default=None),hits=len(hits),distinct=len(set(seq)&rare),
                             coverage=len(set(seq)-{None}),unresolved=seq.count(None)))
    successes=sum(r["hits"]>0 for r in rows)
    hit_count=sum(r["hits"] for r in rows)
    n=len(rows)*32
    rate=hit_count/n
    report[method]=dict(seconds=time.perf_counter()-begin,rows=rows,successes=successes,
        per_draw=rate,n95_estimated=math.ceil(math.log(.05)/math.log1p(-rate)),
        rate_ci=[float(beta.ppf(.025,hit_count,n-hit_count+1)),float(beta.ppf(.975,hit_count+1,n-hit_count))],
        mean_distinct=float(np.mean([r["distinct"] for r in rows])))
    print(method,{k:v for k,v in report[method].items() if k!="rows"},flush=True)
(root/"results/erbb-frozen-controls.json").write_text(json.dumps(report,indent=2))
