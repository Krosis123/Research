"""Prospective transfer pilot: discover under fixed inputs, audit with independent uniform starts."""
import argparse
import hashlib
import json
import re
import time
from collections import Counter
from pathlib import Path

import networkx as nx
import numpy as np
from scipy.stats import beta

from atlantis.bounded_basins import load_bnet


def threshold_groups(net):
    groups={}
    for i,name in enumerate(net.names):
        match=re.fullmatch(r"(.+)_b(\d+)",name)
        if not match:
            raise ValueError(f"Missing threshold suffix: {name}")
        groups.setdefault(match[1],[]).append((int(match[2]),i))
    result=[]
    for name,items in groups.items():
        items.sort()
        levels=[level for level,i in items]
        if levels!=list(range(1,max(levels)+1)):
            raise ValueError(f"Incomplete thresholds for {name}")
        columns=[i for level,i in items]
        allowed=[v for v in range(len(items)+1) if all(
            net.names[i] not in net.clamped or net.clamped[net.names[i]]==int(v>=k)
            for k,i in items)]
        if not allowed:
            raise ValueError(f"Inconsistent clamps for {name}")
        result.append((columns,np.array(allowed)))
    return result


def sample(net, rng, size, method, components, groups=None):
    starts = rng.integers(2, size=(size,net.n),dtype=np.uint8)
    if method == "scc_mixture":
        # Half uniform draws preserve at least half the reference mass everywhere.
        guided = np.flatnonzero(rng.random(size)<0.5)
        for component in components:
            bias = rng.beta(0.5,0.5,size=(len(guided),1))
            starts[np.ix_(guided,component)] = rng.random((len(guided),len(component))) < bias
    if groups is not None:
        for columns,allowed in groups:
            levels=rng.choice(allowed,size)
            if method=="scc_mixture" and len(allowed)>1:
                # Within the guided half, bias levels toward the two extremes.
                weights=np.ones(len(allowed))
                weights[[0,-1]]=3
                levels[guided]=rng.choice(allowed,len(guided),p=weights/weights.sum())
            starts[:,columns]=levels[:,None]>=np.arange(1,len(columns)+1)
    for name,value in net.clamped.items():
        starts[:,net.index(name)] = value
    return starts


def labels(net, starts, horizon):
    pending=np.arange(len(starts))
    path=[starts.copy()]
    result=[None]*len(starts)
    for _ in range(horizon):
        if not len(pending):
            break
        current=net.step(path[-1])
        found=np.zeros(len(current),dtype=bool)
        for t,previous in enumerate(path):
            match=np.flatnonzero(np.all(current==previous,axis=1))
            for i in match:
                cycle=np.stack([layer[i] for layer in path[t:]])
                # Independently replay every edge of every reported cycle.
                if not np.array_equal(net.step(cycle),np.roll(cycle,-1,axis=0)):
                    raise ValueError("Invalid cycle")
                words=[row.tobytes() for row in np.packbits(cycle,axis=1)]
                k=words.index(min(words))
                result[pending[i]]=b"".join(words[k:]+words[:k]).hex()
            found[match]=True
        pending=pending[~found]
        path=[layer[~found] for layer in path]+[current[~found]]
    return result


def trial(path, repeats, budget, audit_n, level_support=False, horizon=32):
    net=load_bnet(path)
    # Fixed context, chosen without inspecting the dynamics.
    net.clamped=dict.fromkeys(net.metadata["external_inputs"],0)
    graph=nx.from_numpy_array(net.adjacency,create_using=nx.DiGraph)
    components=[sorted(c) for c in nx.strongly_connected_components(graph) if len(c)>1]
    groups=threshold_groups(net) if level_support else None
    rows=[]
    def evaluate(seed,size,method):
        rng=np.random.default_rng(seed)
        sequence=[]
        for offset in range(0,size,64):
            states=sample(net,rng,min(64,size-offset),method,components,groups)
            sequence.extend(labels(net,states,horizon))
        return sequence
    for i in range(repeats):
        for method in ("uniform","scc_mixture"):
            begin=time.perf_counter()
            seq=evaluate(5000+i,budget,method)
            rows.append(dict(method=method,seed=5000+i,seconds=time.perf_counter()-begin,sequence=seq))
    candidates={key for r in rows for key in r["sequence"] if key is not None}
    audit=evaluate(9000,audit_n,"uniform")
    counts=Counter(audit)
    upper={}
    for key in candidates:
        hits=counts[key]+counts[None]
        upper[key]=1.0 if hits==audit_n else float(beta.ppf(1-.05/len(candidates),hits+1,audit_n-hits))
    keys=sorted(candidates)
    index={k:i for i,k in enumerate(keys)}
    for row in rows:
        row["sequence"]=[index.get(k) for k in row["sequence"]]
    return dict(support="uniform permitted levels; guided extremes mixture" if groups else "Boolean cube",source=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),names=net.names,
                clamps=net.clamped,scc_sizes=list(map(len,components)),audit_n=audit_n,audit_seed=9000,
                audit_unresolved=counts[None],cycles=[dict(packed_cycle=k,uniform_hits=counts[k],
                simultaneous_upper95=upper[k]) for k in keys],trials=rows,horizon=horizon)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("model",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--horizon",type=int,default=32)
    parser.add_argument("--levels",action="store_true")
    args=parser.parse_args()
    result=trial(args.model,8,32,1024,args.levels,args.horizon)
    args.output.write_text(json.dumps(result,indent=1))
    print(args.model,len(result["cycles"]),result["audit_unresolved"])
