"""Circuit fidelity test, automatically skipped without Qiskit."""
import pytest
pytest.importorskip('qiskit')
pytest.importorskip('qiskit_aer')
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from ross_bench.model import make_network
from ross_bench.circuits import time_evolution,gene_qubit,search_circuit,qiskit_counts


def test_reversible_boolean_update():
    net=make_network(4,'rossini4')
    t=time_evolution(net,1)
    for x in range(16):
        qc=QuantumCircuit(t.num_qubits)
        for i,bit in enumerate(net.as_bits(x)):
            if bit=='1':qc.x(gene_qubit(net,0,i))
        qc.compose(t,inplace=True)
        v=Statevector.from_instruction(qc)
        assert max(range(len(v)),key=lambda i:abs(v.data[i]))==x+(net.step(x)<<4)


def test_suppression_end_to_end_aer():
    net=make_network(4,'rossini4')
    circuit,params=search_circuit(net,3,['0000','0011','1011','1111'],15)
    counts,_=qiskit_counts(circuit,shots=256,seed=3)
    assert counts=={'1101':256}
