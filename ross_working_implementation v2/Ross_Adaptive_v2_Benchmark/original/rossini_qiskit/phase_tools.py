"""Phase-shift helpers for computational-basis states."""

from qiskit import QuantumCircuit


def phase_basis_state(
    qc: QuantumCircuit,
    qubits_in_string_order: list[int],
    bitstring: str,
    angle: float,
) -> None:
    """
    Multiply exactly one basis state by exp(i * angle).

    qubits_in_string_order and bitstring use the SAME left-to-right order.

    Example:
        qubits_in_string_order = [qA, qB, qC, qD]
        bitstring = "1011"

    means phase |A B C D> = |1 0 1 1>.
    """
    if len(qubits_in_string_order) != len(bitstring):
        raise ValueError("Number of qubits and number of bits must match.")

    if any(bit not in "01" for bit in bitstring):
        raise ValueError("bitstring must contain only 0 and 1.")

    zeros = [
        qubit
        for qubit, bit in zip(qubits_in_string_order, bitstring)
        if bit == "0"
    ]

    # Turn the requested bitstring into |11...1>.
    for qubit in zeros:
        qc.x(qubit)

    if len(qubits_in_string_order) == 1:
        qc.p(angle, qubits_in_string_order[0])
    else:
        controls = qubits_in_string_order[:-1]
        target = qubits_in_string_order[-1]
        qc.mcp(angle, controls, target)

    # Undo the temporary X gates.
    for qubit in reversed(zeros):
        qc.x(qubit)


def phase_many_basis_states(
    qc: QuantumCircuit,
    qubits_in_string_order: list[int],
    bitstrings: list[str],
    angle: float,
) -> None:
    """Apply the same phase to several basis states."""
    for bitstring in bitstrings:
        phase_basis_state(qc, qubits_in_string_order, bitstring, angle)
