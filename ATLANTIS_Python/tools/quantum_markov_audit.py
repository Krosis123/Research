"""One-step Markov proposals for discovery and independent uniform audit shots."""
import json
import math
import random
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator
from scipy.stats import beta
from audit_imc1010 import ids, markers, root, trace_state

P = .25
WIDTH = 10  # each pair is entirely within a block


def mask_circuit(n, paired):
    qc = QuantumCircuit(n)
    if paired:
        for j in range(0,n-1,2):
            qc.rxx(2*math.asin(math.sqrt(P)),j,j+1)
        if n%2:
            qc.ry(2*math.asin(math.sqrt(P)),n-1)
    else:
        qc.h(range(n))
    return qc


def sample(count, paired, seed):
    anchor = bytes(random.Random(17).randbytes(len(ids)))  # convert to bits below
    anchor = bytes(x & 1 for x in anchor)
    states = [bytearray() for _ in range(count)]
    sim = AerSimulator(method="statevector")
    for start in range(0,len(ids),WIDTH):
        n = min(WIDTH,len(ids)-start)
        qc = mask_circuit(n,paired)
        qc.measure_all()
        draws = sim.run(qc,shots=count,memory=True,seed_simulator=seed+start).result().get_memory()
        for state,word in zip(states,draws):
            state.extend(((int(word,2)>>j)&1)^anchor[start+j] for j in range(n))
    return list(map(bytes,states))


def main():
    # Transition x -> x XOR mask. Exact translation symmetry makes all rows shifts.
    np.testing.assert_allclose(Statevector.from_instruction(mask_circuit(2,True)).probabilities(),
                               [1-P,0,0,P],atol=1e-14)
    np.testing.assert_allclose(Statevector.from_instruction(mask_circuit(2,False)).probabilities(),
                               [.25]*4,atol=1e-14)
    proposals=sample(8,True,1000)
    known={trace_state(x) for x in proposals}-{None}
    evidence={}
    qc_holdout=sample(64,False,2000)
    rng=random.Random(811)
    for label,states in [('aer_uniform',qc_holdout),
                         ('classical_uniform',[bytes(rng.randrange(2) for _ in ids) for _ in range(64)])]:
        misses=sum(trace_state(x) not in known for x in states)
        upper=float(beta.ppf(.95,misses+1,64-misses)) if misses<64 else 1.
        evidence[label]=dict(misses=misses,upper95=upper,stop=upper<=.05)
    evidence.update(loci=len(ids),markers=markers,known=sorted(known),proposal_count=len(proposals),
                    shots_per_audit=64,block_width=WIDTH,paired_flip_probability=P)
    dest=root/'research_sources/imc1010-quantum-markov.json'
    dest.write_text(json.dumps(evidence,indent=2))
    print(evidence)

if __name__=='__main__':
    main()
