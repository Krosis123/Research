"""Reproduce bounded sampled runs for the supplied colorectal and HCT-116 configurations."""
from collections import Counter
import json
from pathlib import Path
import sys

import numpy as np
from scipy.stats import binomtest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atlantis.analysis import Attractor, deterministic_analysis
from atlantis.fates import load_fate_logic
from atlantis.io import load_fixed_nodes, load_mutations, load_rules, load_states


def sample_cycles(network, states, horizon):
    active = np.arange(len(states))
    current = states.copy()
    history = []
    seen = [{} for _ in states]
    cycles = {}
    for time in range(horizon + 1):
        packed = np.packbits(current, axis=1)
        keep = []
        for row, index in enumerate(active):
            key = packed[row].tobytes()
            start = seen[index].get(key)
            if start is None:
                seen[index][key] = time
                keep.append(row)
            else:
                cycles[index] = np.array([layer[index] for layer in history[start:]])
        if not keep or time == horizon:
            break
        layer = np.empty_like(states)
        layer[active] = current
        history.append(layer)
        active = active[keep]
        current = network.step(current[keep])
    return cycles


def main():
    report = []
    for case in (3, 4):
        root = Path('examples') / f'Case Study {case}' / 'Input Files'
        details = root / 'Network Details'
        net = load_rules(details / 'Node List.txt', details / 'Boolean logic for nodes',
                         missing_policy='unspecified')
        external = load_fixed_nodes(next(root.glob('**/Input Node States.csv')))
        net.metadata['external_inputs'] = [net.names[net.index(name)] for name in external]
        net.clamped = {net.names[net.index(name)]: value for name, value in external.items()}
        outputs = set(net.metadata['unspecified_rules']) - net.clamped.keys()
        logic = load_fate_logic(next(root.glob('**/*Fate Determination Logic.csv')), net)
        output_indices = {net.index(name) for name in outputs}
        assert len(outputs) == 4
        assert not output_indices.intersection(logic.nodes)
        assert not any(output_indices.intersection(rule.sources) for rule in net.rules if rule)
        # Canonical placeholders project unused reporting coordinates out of cycle identity.
        net.clamped.update(dict.fromkeys(outputs, 0))
        sources = [load_states(p, net.n) for p in sorted((root/'Network State Lists').glob('Simulation *.mat'))]
        states = np.concatenate(sources)
        states = states[np.random.default_rng(20261108).choice(len(states), 1024, replace=False)]
        for path in sorted((root/'Mutation Files').glob('*.txt')):
            model = net.mutate(load_mutations(path))
            initial = states.copy()
            for name, value in model.clamped.items():
                initial[:,model.index(name)] = value
            # Original rule mutations are pinned throughout the run.
            for name, value in load_mutations(path):
                if value in (0, 1):
                    initial[:,model.index(name)] = value
            cycles = sample_cycles(model, initial, 200)
            baseline = deterministic_analysis(model, initial[:8], 200, logic)
            assert baseline.unresolved == sum(i not in cycles for i in range(8))
            for i, label in enumerate(baseline.assignments):
                if label >= 0:
                    assert {row.tobytes() for row in cycles[i]} == {
                        row.tobytes() for row in baseline.attractors[label].states}
            fates = Counter()
            combined_fates = Counter()
            signatures = set()
            lengths = Counter()
            for cycle in cycles.values():
                signatures.add(tuple(sorted(row.tobytes() for row in cycle)))
                lengths[len(cycle)] += 1
                fate = logic.associate(Attractor(cycle, 0).stratified)
                combined_fates[fate or 'unclassified'] += 1
                fates.update(fate.split(' + ') if fate else ['unclassified'])
            fates['unresolved'] = len(initial)-len(cycles)
            intervals = {key: list(binomtest(count,len(initial)).proportion_ci(method='wilson'))
                         for key,count in fates.items()}
            report.append(dict(case=case, condition=path.stem, n=len(initial), horizon=200,
                               external=external, projected_outputs=sorted(outputs),
                               distinct_attractors=len(signatures), cycle_length_counts=dict(lengths),
                               combined_fate_counts=dict(combined_fates),
                               fate_counts=dict(fates), marginal_wilson95=intervals))
            Path('validation/colorectal-sampled.json').write_text(json.dumps(report, indent=2))
            print(case, path.stem, dict(fates), flush=True)


if __name__ == '__main__':
    main()
