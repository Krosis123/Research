"""Run the bounded 201-node checks from the ATLANTIS project directory."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from atlantis import io
from atlantis.analysis import deterministic_analysis


def main():
    reports = []
    for case in ('Case Study 3', 'Case Study 4'):
        root = Path('examples') / case / 'Input Files'
        details = root / 'Network Details'
        network = io.load_rules(details / 'Node List.txt',
                                details / 'Boolean logic for nodes', allow_missing=True)
        missing = [name for name, rule in zip(network.names, network.rules) if rule is None]
        for path in sorted((root / 'Network State Lists').glob('Simulation *.mat')):
            states = io.load_states(path, network.n)
            updated = network.step(states)
            assert updated.shape == states.shape and ((updated == 0) | (updated == 1)).all()
            result = deterministic_analysis(network, states[:128], search_duration=100)
            reports.append(dict(case=case, input=path.name, transition_rows=len(states),
                                attractor_sample=128, horizon=100, identity_fallback_nodes=missing,
                                attractors=len(result.attractors), unresolved=result.unresolved))
            print(case, path.name, len(missing), len(result.attractors), result.unresolved, flush=True)
    Path('validation/large-biological-smoke.json').write_text(json.dumps(reports, indent=2))


if __name__ == '__main__':
    main()
