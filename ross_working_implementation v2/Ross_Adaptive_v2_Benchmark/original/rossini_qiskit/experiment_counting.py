"""Test Rossini Step 1.1: quantum counting of already-known basin states."""

from network import static_basin_sizes
from counting import estimate_basin_size_quantum


def main() -> None:
    basin_sizes = static_basin_sizes()

    test_sets = [
        ["0000"],
        ["0000", "1011"],
        ["0000", "1011", "0011"],
        ["0000", "1011", "0011", "1111"],
    ]

    for marked in test_sets:
        exact_M = sum(basin_sizes[a] for a in marked)

        estimated_M, raw_phase_counts, M_histogram = estimate_basin_size_quantum(
            marked_attractors=marked,
            counting_qubits=5,
            shots=2048,
        )

        print("\nMarked attractors:", marked)
        print("Exact M:          ", exact_M)
        print("Estimated M:      ", estimated_M)
        print("M histogram:      ", M_histogram)
        print("QPE raw counts:   ", raw_phase_counts)


if __name__ == "__main__":
    main()
