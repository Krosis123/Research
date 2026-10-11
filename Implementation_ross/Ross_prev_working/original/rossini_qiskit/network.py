"""Classical definition of the 4-gene Boolean network used in Rossini et al."""

from collections import defaultdict

GENES = ("A", "B", "C", "D")
N_GENES = 4


def update_state(state: str) -> str:
    """
    One synchronous Boolean-network update.

    State strings are written in biological order: A B C D.
    Example: "1011" means A=1, B=0, C=1, D=1.
    """
    if len(state) != 4 or any(bit not in "01" for bit in state):
        raise ValueError("state must be a 4-bit string such as '1011'")

    A, B, C, D = (int(bit) for bit in state)

    next_A = A & D
    next_B = A & B
    next_C = C & D
    next_D = B | C

    return f"{next_A}{next_B}{next_C}{next_D}"


def all_states() -> list[str]:
    return [f"{i:04b}" for i in range(2**N_GENES)]


def attractor_cycle(start: str) -> tuple[str, ...]:
    """Follow the classical dynamics until a state repeats."""
    seen_at = {}
    path = []
    state = start

    while state not in seen_at:
        seen_at[state] = len(path)
        path.append(state)
        state = update_state(state)

    cycle_start = seen_at[state]
    return tuple(path[cycle_start:])


def basins() -> dict[tuple[str, ...], list[str]]:
    """
    Map each attractor cycle to all initial states that eventually reach it.
    """
    result = defaultdict(list)

    for state in all_states():
        cycle = attractor_cycle(state)
        result[cycle].append(state)

    return dict(result)


def static_basin_sizes() -> dict[str, int]:
    """
    This toy network has only one-state (static) attractors.
    Return {attractor: basin_size}.
    """
    result = {}

    for cycle, basin in basins().items():
        if len(cycle) != 1:
            raise ValueError(
                "This helper assumes static attractors, but a cycle was found: "
                + repr(cycle)
            )
        result[cycle[0]] = len(basin)

    return result


if __name__ == "__main__":
    print("Transition table:")
    for state in all_states():
        print(f"{state} -> {update_state(state)}")

    print("\nAttractors and basins:")
    for cycle, basin in sorted(basins().items()):
        print(f"{cycle}: size={len(basin)}, states={basin}")
