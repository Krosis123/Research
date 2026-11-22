"""Validate a regulatory-edge proposal as an ideal quantum preparation and an O(n) classical sampler."""
from pathlib import Path
import json
import math
import platform
import sys
import time
import numpy as np
from qiskit import QuantumCircuit,transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator
from research_mcf7_signed_pair import ROOT,load_weighted,load_mutations,proposals,all_states,labels_for,binary_to_decimal

def prepare(weights):
    n=len(weights)
    qc=QuantumCircuit(n)
    free=set(range(n))
    pairs=[]
    for _,i,j in sorted((-abs(weights[i,j]),i,j) for i,j in zip(*np.nonzero(weights)) if i!=j):
        if i not in free or j not in free:
            continue
        free.difference_update((i,j))
        negative=weights[i,j]<0
        pairs.append((i,j,negative))
        qc.h(n-1-i)
        qc.ry(2*math.asin(math.sqrt(.2)),n-1-j)
        qc.cx(n-1-i,n-1-j)
        if negative:
            qc.x(n-1-j)
    for i in free:
        qc.h(n-1-i)
    return qc,pairs


def run():
    states=all_states(16)
    base=ROOT/"examples/Case Study 2/Input Files"
    rows=[]
    for env,file in [("off","DNA Damge OFF/Control_MCF7 (0).csv"),("on","DNA Damge ON/Etoposide.csv")]:
        for treatment in ["Control","Nutlin","Wip1 KD","Nutlin + Wip KD"]:
            net=load_weighted(base/"Network files"/file).mutate(load_mutations(base/"Mutation Files"/(treatment+".txt")))
            labels=labels_for(binary_to_decimal(net.step(states)))
            rare=np.bincount(labels,minlength=65536)[labels]<=655
            pmf=dict(proposals(states,net.weights))["signed_matching"]
            start=time.perf_counter()
            qc,pairs=prepare(net.weights)
            exact=.8*Statevector.from_instruction(qc).probabilities()+.2/65536
            error=float(abs(exact-pmf).max())
            if error>1e-12: raise ValueError("Classical and quantum proposal disagree")
            exact_seconds=time.perf_counter()-start
            rng=np.random.default_rng(25381)
            count=8192
            uniform_count=int(rng.binomial(count,.2))
            begin=time.perf_counter()
            uniform=QuantumCircuit(16);uniform.h(range(16))
            qc.measure_all();uniform.measure_all()
            backend=AerSimulator(method="matrix_product_state",max_parallel_threads=1)
            circuits=transpile([qc,uniform],backend,optimization_level=1,num_processes=1)
            histograms=[]
            for circuit,shots in zip(circuits,(count-uniform_count,uniform_count)):
                job=backend.run(circuit,shots=shots,seed_simulator=shots)
                histograms.append(job.result().get_counts())
            hits=sum(v for h in histograms for word,v in h.items() if rare[int(word,2)])
            aer_seconds=time.perf_counter()-begin
            begin=time.perf_counter()
            starts=rng.integers(2,size=(count,16),dtype=np.uint8)
            for i,j,negative in pairs:
                starts[uniform_count:,j]=starts[uniform_count:,i]^negative^(rng.random(count-uniform_count)<.2)
            native_hits=int(rare[binary_to_decimal(starts)].sum())
            rows.append(dict(env=env,treatment=treatment,shots=count,uniform_component_shots=uniform_count,
                            aer_hits=hits,classical_hits=native_hits,pmf_max_abs_error=error,
                            classical_seconds=time.perf_counter()-begin,aer_seconds=aer_seconds,
                            exact_verification_seconds=exact_seconds,seed=25381,depth=circuits[0].depth(),
                            gate_counts=dict(circuits[0].count_ops()),expected_hits=float(pmf[rare].sum()*count)))
    return rows

if __name__=="__main__":
    rows=run()
    (ROOT/"research/results/signed-proposal-local-circuits.json").write_text(json.dumps(rows,indent=2))
    print("Conditions",len(rows),"max PMF difference",max(r["pmf_max_abs_error"] for r in rows))
