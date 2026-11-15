"""Measure actual QPE for a hand-enumerated 3:1 basin split."""
import json
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from atlantis.expressions import from_expressions
from atlantis.quantum.adapter import QuantumNetwork
from atlantis.quantum.ross.circuits import counting_circuit, qiskit_counts, qpe_counts_to_M


def main():
    model = QuantumNetwork(from_expressions({'a':'a | b', 'b':'a | b', 'c':'a | b'}))
    rows=[]
    for terminal, expected in (('000',2),('111',6)):
        for precision in (2,3,4):
            start=perf_counter()
            circuit=counting_circuit(model,1,[terminal],precision)
            construction=perf_counter()-start
            for seed in range(3):
                counts, metrics=qiskit_counts(circuit,128,seed=seed)
                estimate, histogram=qpe_counts_to_M(counts,8,precision)
                rows.append(dict(terminal=terminal,precision=precision,seed=seed,shots=128,
                                 expected=expected,estimate=estimate,absolute_error=abs(estimate-expected),
                                 construction_s=construction,counts=counts,estimate_histogram=histogram,
                                 **metrics))
    Path('validation/unequal-qpe.json').write_text(json.dumps(rows,indent=2))
    print(len(rows), 'runs; absolute errors:', [r['absolute_error'] for r in rows])


if __name__=='__main__':
    main()
