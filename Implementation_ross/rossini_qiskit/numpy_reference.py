"""
Small NumPy reference calculation.

This does NOT simulate the full Qiskit circuit. It collapses
T^dagger * phase(attractor) * T into the equivalent statement:
"phase every initial state in the selected basins".

Its purpose is to verify the deletion mathematics independently.
"""

from math import asin, ceil, cos, pi, sin, sqrt
import numpy as np

from network import basins


def hadamard_n(n: int) -> np.ndarray:
    H1 = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
    H = np.array([[1]], dtype=complex)

    for _ in range(n):
        H = np.kron(H, H1)

    return H


def parameters(M: int, N: int) -> tuple[int, float]:
    beta = asin(sqrt(M / N))
    J = max(1, ceil(beta / (pi - 2 * beta)))
    phi = -2 * asin(sin(pi / (4 * J + 2)) / cos(beta))
    return J, phi


def suppress(marked_initial_states: list[str]) -> np.ndarray:
    n = 4
    N = 2**n
    M = len(marked_initial_states)

    H = hadamard_n(n)

    zero = np.zeros(N, dtype=complex)
    zero[0] = 1

    psi = H @ zero
    J, phi = parameters(M, N)

    marked_indices = [int(state, 2) for state in marked_initial_states]

    for _ in range(J):
        # Equivalent to T -> phase marked attractors -> T^dagger.
        basin_phase = np.ones(N, dtype=complex)
        basin_phase[marked_indices] = np.exp(-1j * phi)
        psi = basin_phase * psi

        psi = H @ psi

        zero_phase = np.ones(N, dtype=complex)
        zero_phase[0] = np.exp(1j * phi)
        psi = zero_phase * psi

        psi = H @ psi

    return psi


def main() -> None:
    basin_map = basins()
    basin_by_attractor = {
        cycle[0]: states
        for cycle, states in basin_map.items()
    }

    sequence = ["0000", "1011", "0011", "1111"]
    marked = []

    for attractor in sequence:
        marked += basin_by_attractor[attractor]

        psi = suppress(marked)

        print("\nDeleted initial states:", len(marked))
        for i, amp in enumerate(psi):
            probability = abs(amp) ** 2
            if probability > 1e-10:
                print(f"|{i:04b}>  P={probability:.12f}")


if __name__ == "__main__":
    main()
