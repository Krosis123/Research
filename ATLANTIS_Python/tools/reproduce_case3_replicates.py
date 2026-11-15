"""Run supplied 10,000-row replicates with archived initialization semantics."""
import argparse
from collections import Counter
import json
from pathlib import Path
from time import perf_counter

from reproduce_colorectal import sample_cycles
from atlantis.analysis import Attractor
from atlantis.fates import load_fate_logic
from atlantis.io import load_fixed_nodes, load_mutations, load_rules, load_states


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=int, choices=(3, 4), default=3)
    parser.add_argument('--replicates', type=int, choices=(1, 2, 3), default=3)
    args = parser.parse_args()
    root = Path(f'examples/Case Study {args.case}/Input Files')
    output = Path('validation/colorectal-three-replicates.json' if args.case == 3
                  else 'validation/hct116-full.json')
    details = root/'Network Details'
    network = load_rules(details/'Node List.txt', details/'Boolean logic for nodes',
                         missing_policy='unspecified')
    external = load_fixed_nodes(next(root.glob('**/Input Node States.csv')))
    network.clamped = {network.names[network.index(k)]: v for k,v in external.items()}
    outputs = set(network.metadata['unspecified_rules']) - network.clamped.keys()
    logic = load_fate_logic(next(root.glob('**/*Fate Determination Logic.csv')), network)
    indices = {network.index(k) for k in outputs}
    assert not indices.intersection(logic.nodes)
    assert not any(indices.intersection(rule.sources) for rule in network.rules if rule)
    network.clamped.update(dict.fromkeys(outputs, 0))
    records = []
    for path in sorted((root/'Network State Lists').glob('Simulation *.mat'))[:args.replicates]:
        states = load_states(path, network.n)
        for name, value in network.clamped.items():
            states[:,network.index(name)] = value
        for mutation in sorted((root/'Mutation Files').glob('*.txt')):
            start = perf_counter()
            model = network.mutate(load_mutations(mutation))
            combined = Counter()
            periods = Counter()
            for i in range(0,len(states),1024):
                batch = states[i:i+1024]
                cycles = sample_cycles(model,batch,200)
                combined['unresolved'] += len(batch)-len(cycles)
                for cycle in cycles.values():
                    periods[len(cycle)] += 1
                    combined[logic.associate(Attractor(cycle,0).stratified) or 'unclassified'] += 1
            resolved = len(states)-combined['unresolved']
            records.append(dict(replicate=path.name, condition=mutation.stem,
                                rows=len(states), horizon=200, cycle_period_counts=periods,
                                combined_fate_counts=combined, normal_only=combined['Normal Proliferation']/resolved,
                                normal_marginal=sum(v for k,v in combined.items()
                                    if 'Normal Proliferation' in k.split(' + '))/resolved,
                                wall_s=perf_counter()-start))
            output.write_text(json.dumps(records,indent=2))
            print(path.name, mutation.stem, resolved, round(records[-1]['normal_only'],4),flush=True)


if __name__ == '__main__':
    main()
