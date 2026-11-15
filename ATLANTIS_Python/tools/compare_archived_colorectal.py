"""Compare the archived MATLAB final CRC condition with the same input rows."""
from collections import Counter
import json
from pathlib import Path
from time import perf_counter

from reproduce_colorectal import sample_cycles
from atlantis.analysis import Attractor
from atlantis.fates import load_fate_logic
from atlantis.io import load_fixed_nodes, load_mutations, load_rules, load_states, read_rows


def main():
    root = Path('examples/Case Study 3/Input Files')
    details = root/'Network Details'
    archive, = Path('reference/Toolbox/Results').glob('*Node List/**/Network State List DA.mat')
    network = load_rules(details/'Node List.txt', details/'Boolean logic for nodes',
                         missing_policy='unspecified')
    inputs = load_fixed_nodes(next(root.glob('**/Input Node States.csv')))
    network.clamped = {network.names[network.index(k)]: v for k,v in inputs.items()}
    outputs = set(network.metadata['unspecified_rules']) - network.clamped.keys()
    logic = load_fate_logic(next(root.glob('**/*Fate Determination Logic.csv')), network)
    indices = {network.index(k) for k in outputs}
    assert not indices.intersection(logic.nodes)
    assert not any(indices.intersection(rule.sources) for rule in network.rules if rule)
    network.clamped.update(dict.fromkeys(outputs, 0))
    model = network.mutate(load_mutations(root/'Mutation Files/APC+RAS+PTEN+P53.txt'))
    states = load_states(archive, network.n)
    for name, value in model.clamped.items():
        states[:,model.index(name)] = value
    counts = Counter()
    start = perf_counter()
    for i in range(0,len(states),1024):
        batch = states[i:i+1024]
        cycles = sample_cycles(model,batch,200)
        counts['unresolved'] += len(batch)-len(cycles)
        for cycle in cycles.values():
            counts[logic.associate(Attractor(cycle,0).stratified) or 'unclassified'] += 1
    saved_path, = archive.parent.glob('*Cell Fate Propensites.csv')
    saved = {' + '.join(sorted(row[0].split(' + '))):float(row[1])
             for row in read_rows(saved_path)[1:]}
    resolved = len(states)-counts['unresolved']
    measured = {k:v/resolved for k,v in counts.items() if k != 'unresolved'}
    report = dict(archive=str(archive), n=len(states), horizon=200,
                  initialization='archived states with original mutation-node starting values',
                  counts=counts, resolved_conditional_proportions=measured,
                  saved_matlab_proportions=saved, total_variation=0.5*sum(
                      abs(measured.get(k,0)-saved.get(k,0)) for k in measured.keys()|saved.keys()),
                  wall_s=perf_counter()-start)
    Path('validation/colorectal-archived-comparison.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
