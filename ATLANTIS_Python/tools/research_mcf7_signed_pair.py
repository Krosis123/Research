"""Exact one-draw and finite-budget benchmark; PMFs enumerated for evaluation only."""
from pathlib import Path
import hashlib
import json
import math
import random
import sys
import numpy as np
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from atlantis.io import load_weighted, load_mutations
from atlantis.model import binary_to_decimal
from atlantis.states import all_states


def labels_for(nxt):
    labels = np.full(len(nxt), -1)
    for x in range(len(nxt)):
        path = {}
        while labels[x] < 0 and x not in path:
            path[x] = len(path)
            x = nxt[x]
        root = labels[x] if labels[x] >= 0 else min(list(path)[path[x]:])
        for v in path:
            labels[v] = root
    return labels


def proposals(states, weights):
    uniform = np.full(len(states), 1/len(states))
    yield "uniform", uniform
    anchor = np.array([x & 1 for x in random.Random(17).randbytes(16)])
    mask = states ^ anchor
    flips = mask[:, ::2].sum(axis=1).astype(int)
    paired = np.all(mask[:, ::2] == mask[:, 1::2], axis=1)*(.25**flips)*(.75**(8-flips))
    yield "legacy_matched", paired
    yield "legacy_uniform_mixture", .8*paired + .2*uniform
    # Disjoint edges enable exact O(n) ancestral sampling: draw root uniformly,
    # then satisfy each signed edge with probability .8. Ties follow node order.
    edges = sorted(((-abs(weights[i,j]),i,j,int(weights[i,j]<0))
                    for i,j in zip(*np.nonzero(weights)) if i!=j))
    used=set()
    matching=[]
    for _,i,j,neg in edges:
        if i not in used and j not in used:
            matching.append((i,j,neg))
            used.update([i,j])
    perm=np.random.default_rng(1701).permutation(states.shape[1])
    for name,order in [("signed_matching",np.arange(states.shape[1])),("scrambled_matching",perm)]:
        density=uniform.copy()
        for i,j,neg in matching:
            satisfied=(states[:,order[i]] ^ states[:,order[j]])==neg
            density*=np.where(satisfied,1.6,.4)
        yield name,.2*uniform+.8*density


def main():
    states=all_states(16)
    assert np.array_equal(binary_to_decimal(states),np.arange(len(states)))
    base=ROOT/'examples/Case Study 2/Input Files'
    results=[]
    for env,file in [('off','DNA Damge OFF/Control_MCF7 (0).csv'),('on','DNA Damge ON/Etoposide.csv')]:
        graph=base/'Network files'/file
        for treatment in ['Control','Nutlin','Wip1 KD','Nutlin + Wip KD']:
            mutation=base/'Mutation Files'/f'{treatment}.txt'
            net=load_weighted(graph).mutate(load_mutations(mutation))
            nxt=binary_to_decimal(net.step(states))
            labels=labels_for(nxt)
            assert np.array_equal(labels,labels[nxt])
            sizes=np.bincount(labels,minlength=len(states))
            rare=(sizes>0)&(sizes<=len(states)*.01)
            row=dict(environment=env,treatment=treatment,hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in (graph,mutation)],basins={int(i):int(sizes[i]) for i in np.flatnonzero(sizes)},methods={})
            for method,pmf in proposals(states,net.weights):
                assert np.isclose(pmf.sum(),1)
                masses=np.bincount(labels,weights=pmf,minlength=len(states))
                hit=masses[rare].sum()
                draws=np.random.default_rng(90210).choice(len(states),(512,64),p=pmf)
                successes=int(rare[labels[draws]].any(axis=1).sum())
                ci=binomtest(successes,512).proportion_ci()
                row['methods'][method]=dict(p=float(hit),n95=math.ceil(math.log(.05)/math.log1p(-hit)) if hit else None,
                    support=int((pmf>0).sum()),expected_unique_rare64=float((1-(1-masses[rare])**64).sum()),
                    expected_unique_total64=float((1-(1-masses)**64).sum()),wins=successes,trials=512,success95=[ci.low,ci.high])
            results.append(row)
    dest=ROOT/'research/results/mcf7_exact_signed_pair_benchmark.json'
    dest.write_text(json.dumps(results,indent=2))
    for r in results:
        print(r['environment'],r['treatment'],{k:v['n95'] for k,v in r['methods'].items()})
if __name__=='__main__':
    main()
