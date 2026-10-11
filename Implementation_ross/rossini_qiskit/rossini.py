"""Modern-Qiskit reimplementation of Rossini et al.'s exact basin suppression."""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, ceil, cos, pi, sin, sqrt

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from network import N_GENES
from phase_tools import phase_basis_state, phase_many_basis_states
from quantum_network import abcd_qubits, gene_qubits, forward_transition_circuit


@dataclass(frozen=True)
class SuppressionParameters:
    M: int
    N: int
    beta: float
    J: int
    phi: float


def optimal_suppression_parameters(M: int, N: int) -> SuppressionParameters:
    """
    Liu-Ouyang/Rossini exact-deletion parameters.

    beta = asin(sqrt(M/N))

    J = ceil(beta / (pi - 2 beta))

    phi = -2 asin(
        sin(pi / (4J + 2)) / cos(beta)
    )

    The sign convention matches the authors' released implementation.
    """
    if not (0 < M < N):
        raise ValueError("Need 0 < M < N.")

    beta = asin(sqrt(M / N))
    denominator = pi - 2 * beta

    if denominator <= 0:
        raise ValueError("Invalid deletion geometry: pi - 2*beta <= 0.")

    J = max(1, ceil(beta / denominator))

    ratio = sin(pi / (4 * J + 2)) / cos(beta)

    # Floating-point protection around +/-1.
    ratio = max(-1.0, min(1.0, ratio))

    phi = -2 * asin(ratio)

    return SuppressionParameters(M=M, N=N, beta=beta, J=J, phi=phi)


def build_suppression_circuit(
    marked_attractors: list[str],
    total_marked_basin_size: int,
    num_transitions: int = 3,
) -> tuple[QuantumCircuit, SuppressionParameters]:
    """
    Build only the state-preparation / basin-suppression section.

    Implements, per Rossini iteration:

        H
        T
        attractor phase
        T^dagger
        H
        |0...0> phase
        H

    The T ... T^dagger sandwich turns phase-marking of final attractors
    into phase-marking of every initial state in their basins.
    """
    if not marked_attractors:
        raise ValueError("Use the no-suppression path when no attractor is marked.")

    N = 2**N_GENES
    params = optimal_suppression_parameters(total_marked_basin_size, N)

    forward = forward_transition_circuit(num_transitions)
    forward_gate = forward.to_gate(label="T")
    backward_gate = forward_gate.inverse()

    total_qubits = forward.num_qubits
    qc = QuantumCircuit(total_qubits, name="Rossini_suppression")

    initial = abcd_qubits(0)
    final = abcd_qubits(num_transitions)

    # Uniform superposition over all initial Boolean-network states.
    for qubit in initial:
        qc.h(qubit)

    for _ in range(params.J):
        # Step 1.2: propagate to attractors.
        qc.append(forward_gate, range(total_qubits))
        # The authors' code computes phi as negative, then applies -phi
        # to the attractors being suppressed.
        phase_many_basis_states(
            qc,
            final,
            marked_attractors,
            angle=-params.phi,
        )

        # Backpropagate the phase from attractors to their basins.
        qc.append(backward_gate, range(total_qubits))

        # Step 1.3
        for qubit in initial:
            qc.h(qubit)

        # Step 1.4
        phase_basis_state(qc, initial, "0000", angle=params.phi)

        # Step 1.5
        for qubit in initial:
            qc.h(qubit)

    return qc, params


def build_attractor_search_circuit(
    marked_attractors: list[str] | None = None,
    total_marked_basin_size: int = 0,
    num_transitions: int = 3,
) -> tuple[QuantumCircuit, SuppressionParameters | None]:
    """
    Complete one Rossini algorithm run.

    If marked_attractors is empty:
        prepare uniform state -> T -> measure

    Otherwise:
        exact basin suppression -> T -> measure
    """
    if marked_attractors is None:
        marked_attractors = []

    forward = forward_transition_circuit(num_transitions)
    total_qubits = forward.num_qubits
    qc = QuantumCircuit(total_qubits, N_GENES)

    params = None

    if marked_attractors:
        suppression, params = build_suppression_circuit(
            marked_attractors=marked_attractors,
            total_marked_basin_size=total_marked_basin_size,
            num_transitions=num_transitions,
        )
        qc.compose(suppression, inplace=True)
    else:
        for qubit in abcd_qubits(0):
            qc.h(qubit)

    # Part 2 of the paper: evolve the surviving states to their attractors.
    qc.append(forward.to_gate(label="T_final"), range(total_qubits))

    # Map D,C,B,A -> c0,c1,c2,c3.
    # Qiskit prints classical keys as c3 c2 c1 c0 = A B C D.
    final = gene_qubits(num_transitions)
    qc.measure(
        [final["D"], final["C"], final["B"], final["A"]],
        [0, 1, 2, 3],
    )

    return qc, params


def simulate_counts(qc: QuantumCircuit, shots: int = 10_000) -> dict[str, int]:
    backend = AerSimulator()
    compiled = transpile(qc, backend, optimization_level=1)
    result = backend.run(compiled, shots=shots).result()
    return result.get_counts()


def probabilities_from_counts(counts: dict[str, int]) -> dict[str, float]:
    total = sum(counts.values())
    return {
        state: count / total
        for state, count in sorted(counts.items())
    }
