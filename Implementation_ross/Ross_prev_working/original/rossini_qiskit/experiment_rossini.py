"""Reproduce the 4-gene noiseless Rossini attractor-suppression experiment."""

from network import basins, static_basin_sizes
from rossini import (
    build_attractor_search_circuit,
    probabilities_from_counts,
    simulate_counts,
)


PAPER_SUPPRESSION_ORDER = [
    "0000",
    "1011",
    "0011",
    "1111",
]
# After those four basins are removed, |1101> is the only attractor left.


def print_distribution(title: str, counts: dict[str, int]) -> None:
    probs = probabilities_from_counts(counts)

    print("\n" + title)
    print("-" * len(title))

    for state, probability in sorted(
        probs.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        print(f"|{state}>  {100 * probability:7.3f}%")


def main() -> None:
    basin_map = basins()
    basin_sizes = static_basin_sizes()

    print("Classical sanity check: attractors and basin sizes")
    for attractor, size in sorted(basin_sizes.items()):
        states = basin_map[(attractor,)]
        print(f"|{attractor}> : basin size {size:2d} : {states}")

    # Run 1: nothing suppressed.
    qc, _ = build_attractor_search_circuit()
    counts = simulate_counts(qc)
    print_distribution("Run 1: no basins suppressed", counts)

    marked = []

    for run_number, attractor in enumerate(PAPER_SUPPRESSION_ORDER, start=2):
        marked.append(attractor)

        M = sum(basin_sizes[a] for a in marked)

        qc, params = build_attractor_search_circuit(
            marked_attractors=marked,
            total_marked_basin_size=M,
        )

        counts = simulate_counts(qc)

        print(
            f"\nSuppressed attractors: {marked}\n"
            f"M={M}, N={params.N}, beta={params.beta:.6f}, "
            f"J={params.J}, phi={params.phi:.6f} rad"
        )

        print_distribution(f"Run {run_number}", counts)


if __name__ == "__main__":
    main()
