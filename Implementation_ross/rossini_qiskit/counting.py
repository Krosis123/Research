"""
Quantum counting for Step 1.1 of Rossini et al.

This is intentionally separate from the baseline reproduction because
controlled Grover iterations are much more expensive to simulate.

Quantum counting estimates M, the number of initial Boolean-network states
whose trajectories end in the already-known attractor set.
"""

from __future__ import annotations

from collections import Counter
from math import pi
import numpy as np

from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import QFTGate
from qiskit_aer import AerSimulator

from network import N_GENES
from phase_tools import phase_many_basis_states, phase_basis_state
from quantum_network import (
    abcd_qubits,
    forward_transition_circuit,
)


def build_basin_phase_oracle(
    marked_attractors: list[str],
    num_transitions: int = 3,
) -> QuantumCircuit:
    """
    Phase flip every INITIAL state that flows to a marked attractor.

    T
    -> phase pi on marked final attractors
    -> T^dagger

    Work registers return to |0>.
    """
    forward = forward_transition_circuit(num_transitions)
    gate_T = forward.to_gate(label="T")
    total_qubits = forward.num_qubits

    qc = QuantumCircuit(total_qubits, name="O_basin")
    qc.append(gate_T, range(total_qubits))

    phase_many_basis_states(
        qc,
        abcd_qubits(num_transitions),
        marked_attractors,
        angle=pi,
    )

    qc.append(gate_T.inverse(), range(total_qubits))
    return qc


def build_exact_diffuser_on_initial_register(
    num_transitions: int = 3,
) -> QuantumCircuit:
    """
    D = 2|s><s| - I on the t=0 register.

    A common H-X-MCZ-X-H circuit equals I - 2|s><s|,
    so we add global phase pi to obtain the exact sign needed for
    phase estimation / quantum counting.
    """
    total_qubits = (num_transitions + 1) * N_GENES
    qc = QuantumCircuit(total_qubits, name="D")

    initial = abcd_qubits(0)

    for q in initial:
        qc.h(q)

    # Phase |0000> by pi -> I - 2|0000><0000|
    phase_basis_state(qc, initial, "0000", angle=pi)

    for q in initial:
        qc.h(q)

    # Convert I - 2|s><s| into 2|s><s| - I.
    qc.global_phase += pi

    return qc


def build_grover_for_basin_counting(
    marked_attractors: list[str],
    num_transitions: int = 3,
) -> QuantumCircuit:
    oracle = build_basin_phase_oracle(marked_attractors, num_transitions)
    diffuser = build_exact_diffuser_on_initial_register(num_transitions)

    qc = QuantumCircuit(oracle.num_qubits, name="G")
    qc.compose(oracle, inplace=True)
    qc.compose(diffuser, inplace=True)
    return qc


def build_quantum_counting_circuit(
    marked_attractors: list[str],
    counting_qubits: int = 5,
    num_transitions: int = 3,
) -> QuantumCircuit:
    """
    Standard quantum counting = phase estimation on the Grover iterate.

    The first `counting_qubits` are the phase-estimation register.
    The remaining qubits are the Boolean-network/Grover system.
    """
    if counting_qubits < 2:
        raise ValueError("Use at least 2 counting qubits.")

    grover = build_grover_for_basin_counting(
        marked_attractors,
        num_transitions,
    )
    system_qubits = grover.num_qubits

    total_qubits = counting_qubits + system_qubits
    qc = QuantumCircuit(total_qubits, counting_qubits)

    count = list(range(counting_qubits))
    system = list(range(counting_qubits, total_qubits))

    # Phase-estimation register.
    for q in count:
        qc.h(q)

    # Uniform superposition only on the t=0 Boolean-network register.
    first_register_offset = counting_qubits
    for local_q in abcd_qubits(0):
        qc.h(first_register_offset + local_q)

    controlled_G = grover.to_gate(label="G").control(1)

    # QPE controlled powers: G^(1), G^(2), G^(4), ...
    # We use repeated applications instead of Gate.power so the logic is explicit.
    for j, control in enumerate(count):
        for _ in range(2**j):
            qc.append(controlled_G, [control] + system)

    qc.append(QFTGate(counting_qubits).inverse(), count)

    qc.measure(count, range(counting_qubits))
    return qc


def phase_to_M(phase_fraction: float, N: int = 16) -> int:
    """
    Grover eigenphases are exp(+/- 2 i theta), where
        sin^2(theta) = M/N.

    QPE returns theta/pi or 1-theta/pi.
    Both give the same sin^2(pi * phase_fraction).
    """
    estimate = N * np.sin(np.pi * phase_fraction) ** 2
    return int(round(float(estimate)))


def estimate_basin_size_quantum(
    marked_attractors: list[str],
    counting_qubits: int = 5,
    num_transitions: int = 3,
    shots: int = 2048,
) -> tuple[int, dict[str, int], dict[int, int]]:
    qc = build_quantum_counting_circuit(
        marked_attractors=marked_attractors,
        counting_qubits=counting_qubits,
        num_transitions=num_transitions,
    )

    backend = AerSimulator()
    compiled = transpile(qc, backend, optimization_level=1)
    counts = backend.run(compiled, shots=shots).result().get_counts()

    histogram_M = Counter()
    denominator = 2**counting_qubits

    for measured_bits, count in counts.items():
        y = int(measured_bits, 2)
        phase_fraction = y / denominator
        M_est = phase_to_M(phase_fraction, N=2**N_GENES)
        histogram_M[M_est] += count

    best_M = histogram_M.most_common(1)[0][0]
    return best_M, counts, dict(sorted(histogram_M.items()))
