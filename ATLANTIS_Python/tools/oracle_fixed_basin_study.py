"""Local coherent search for a known fixed-point basin in an eight-variable motif."""
import json
import math
import time
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector

def transition(x):
    regulators = x & 127
    return regulators | (int(regulators == 127) << 7)

def run_study():
    started = time.perf_counter()
    marked = [x for x in range(256) if transition(x) == 255]
    assert transition(255) == 255 and marked == [127, 255]
    oracle = QuantumCircuit(9)
    oracle.mcx(list(range(7)), 8)
    oracle.z(8)
    oracle.mcx(list(range(7)), 8)
    proposal = QuantumCircuit(9)
    proposal.h(range(8))
    phase_test = Statevector.from_instruction(proposal.compose(oracle)).data
    expected = np.zeros(512)
    expected[:256] = 1/16
    expected[marked] *= -1
    np.testing.assert_allclose(phase_test,expected,atol=1e-10)
    diffuser = QuantumCircuit(9)
    diffuser.h(range(8))
    diffuser.x(range(8))
    diffuser.h(7)
    diffuser.mcx(list(range(7)),7)
    diffuser.h(7)
    diffuser.x(range(8))
    diffuser.h(range(8))
    theta = math.asin(math.sqrt(len(marked)/256))
    rows = []
    for k in range(10):
        prob = Statevector.from_instruction(proposal).probabilities()
        mass = float(prob[marked].sum())
        assert abs(mass-math.sin((2*k+1)*theta)**2)<1e-8
        assert prob[256:].sum()<1e-12
        compiled = transpile(proposal,basis_gates=["rz","sx","x","cx"],optimization_level=1,seed_transpiler=42)
        rows.append(dict(iterations=k,success=mass,cx=compiled.count_ops().get("cx",0),depth=compiled.depth()))
        proposal.compose(oracle,inplace=True)
        proposal.compose(diffuser,inplace=True)
    result=dict(description="Seven identity regulators; output is their conjunction. Uniform independent bits. Known all-on target.", width=9, marked=marked,uniform_iid_trials_95=math.ceil(math.log(.05)/math.log1p(-len(marked)/256)),structure_aware_witness=127,structure_aware_transition_evaluations=1,rows=rows,local_simulation_and_compile_seconds=time.perf_counter()-started)
    return result


def main():
    result = run_study()
    path = Path(__file__).resolve().parents[1] / "research/results/oracle-fixed-basin-feasibility-v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    print(result)


if __name__ == "__main__":
    main()
