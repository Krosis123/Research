"""Reversible Qiskit circuit for the Rossini 4-gene Boolean network."""

from qiskit import QuantumCircuit
from network import N_GENES


def gene_qubits(step: int) -> dict[str, int]:
    """
    Qiskit prints a register as q_high ... q_low.

    Inside each four-qubit time slice we therefore store:
        q_low  = D
        next   = C
        next   = B
        q_high = A

    This makes measured bitstrings print naturally as A B C D.
    """
    base = step * N_GENES
    return {
        "D": base + 0,
        "C": base + 1,
        "B": base + 2,
        "A": base + 3,
    }


def abcd_qubits(step: int) -> list[int]:
    """Physical qubits corresponding to the string order A, B, C, D."""
    q = gene_qubits(step)
    return [q["A"], q["B"], q["C"], q["D"]]


def append_one_transition(qc: QuantumCircuit, input_step: int) -> None:
    """
    Append |x>|0000> -> |x>|F(x)>.

    Because the old state is kept, this is reversible even though the
    classical Boolean map F itself is many-to-one.
    """
    old = gene_qubits(input_step)
    new = gene_qubits(input_step + 1)

    # A' = A AND D
    qc.ccx(old["A"], old["D"], new["A"])

    # B' = A AND B
    qc.ccx(old["A"], old["B"], new["B"])

    # C' = C AND D
    qc.ccx(old["C"], old["D"], new["C"])

    # D' = B OR C
    #
    # Boolean identity:
    # B OR C = B XOR C XOR (B AND C)
    #
    # Since new["D"] starts in |0>, these three gates compute OR into it.
    qc.cx(old["B"], new["D"])
    qc.cx(old["C"], new["D"])
    qc.ccx(old["B"], old["C"], new["D"])


def forward_transition_circuit(num_transitions: int = 3) -> QuantumCircuit:
    """
    Build Rossini's T_t operator using (T+1)*n qubits.

    For this 4-gene toy network, T=3 is enough for every initial state
    to have reached its attractor.
    """
    if num_transitions < 1:
        raise ValueError("num_transitions must be >= 1")

    total_qubits = (num_transitions + 1) * N_GENES
    qc = QuantumCircuit(total_qubits, name=f"T_{num_transitions}")

    for step in range(num_transitions):
        append_one_transition(qc, step)

    return qc
