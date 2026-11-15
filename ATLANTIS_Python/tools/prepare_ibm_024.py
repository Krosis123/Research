"""Execute simulator arms of the IBM Rossini4 preparation plan."""
import json
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from atlantis.io import load_network
from atlantis.quantum.adapter import QuantumNetwork
from atlantis.quantum.ross.circuits import qiskit_counts,search_circuit


def main():
    model=QuantumNetwork(load_network('examples/quantum/rossini4.json'))
    circuit,_=search_circuit(model,3,[],0)
    expected={'0000':11/16,'0011':2/16,'1011':1/16,'1101':1/16,'1111':1/16}
    rows=[]
    seeds=np.random.default_rng(20261108).integers(1,2**31-1,size=9).tolist()
    for shots,block_seeds in ((128,seeds[:1]),(512,seeds[1:])):
        for noise in (0,.002):
            for seed in block_seeds:
                counts,metrics=qiskit_counts(circuit,shots,method='matrix_product_state',
                                            seed=seed,noise_probability=noise)
                distance=.5*sum(abs(counts.get(k,0)/shots-expected.get(k,0)) for k in counts.keys()|expected.keys())
                rows.append(dict(shots=shots,seed=seed,depolarizing=noise,counts=counts,
                                 total_variation_from_ideal=distance,**metrics))
                Path('validation/ibm-simulation-arms-024.json').write_text(json.dumps(rows,indent=2))
    print(len(rows),'local simulation arms')


if __name__=='__main__':
    main()
