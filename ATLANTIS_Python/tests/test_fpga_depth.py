from pathlib import Path

import numpy as np
from qiskit.quantum_info import Statevector

from atlantis.io import load_network
from atlantis.model import decimal_to_binary
from atlantis.quantum.adapter import QuantumNetwork
from atlantis.quantum.ross.circuits import counting_circuit, time_evolution
from atlantis.quantum.ross.model import Network
from atlantis.quantum.ross.reference import qpe_theoretical_distribution


def test_relative_phase_qpe_with_nonlinear_evolution():
    net = Network.create('nonlinear', {'a': '~b & c', 'b': 'a | b', 'c': 'a ^ c'})
    marked = ['000', '011']
    count = sum(net.as_bits(net.step(net.step(x))) in marked for x in range(net.size))
    circuit = counting_circuit(net, 2, marked, 2).remove_final_measurements(inplace=False)
    probabilities = Statevector.from_instruction(circuit).probabilities(qargs=[0, 1])
    np.testing.assert_allclose(probabilities, qpe_theoretical_distribution(count, 8, 2), atol=1e-12)


def test_fpga_subset_compiled_basis_transitions():
    path = Path(__file__).resolve().parents[1] / 'examples/quantum/fpga-case4-subset15.csv'
    model = load_network(path)
    assert model.n == 15 and np.count_nonzero(model.weights) == 21
    assert model.weights[model.names.index('gata6'), model.names.index('nanog')] == -1
    net = QuantumNetwork(model)
    circuit = time_evolution(net, 3, relative=True)
    states = decimal_to_binary(np.arange(net.size), net.n)
    wires = np.zeros((circuit.num_qubits, net.size), np.uint8)
    wires[:net.n] = states[:, ::-1].T
    # All emitted update gates are basis permutations up to a phase.
    for op in circuit.data:
        assert op.operation.name in ('x', 'cx', 'ccx', 'rccx', 'rcccx', 'mcx')
        indices = [circuit.find_bit(w).index for w in op.qubits]
        wires[indices[-1]] ^= np.bitwise_and.reduce(wires[indices[:-1]], axis=0, initial=1)
    for step in range(1, 4):
        states = model.step(states)
        np.testing.assert_array_equal(states, wires[step*net.n:(step+1)*net.n][::-1].T)


def test_large_phase_oracle_restores_borrowed_wires():
    from math import pi
    from qiskit import QuantumCircuit
    from atlantis.quantum.ross.circuits import phase_basis_state
    qc = QuantumCircuit(11)
    phase_basis_state(qc, list(range(7)), '1010100', pi)
    rng = np.random.default_rng(52)
    amplitudes = rng.normal(size=2048) + 1j*rng.normal(size=2048)
    amplitudes /= np.linalg.norm(amplitudes)
    expected = amplitudes.copy()
    expected[int('1010100'[::-1], 2)::128] *= -1
    np.testing.assert_allclose(Statevector(amplitudes).evolve(qc).data, expected, atol=1e-12)
