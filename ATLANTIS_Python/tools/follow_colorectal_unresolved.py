"""Follow unresolved archived CRC states without changing the original denominator."""
import json
from pathlib import Path

from reproduce_colorectal import sample_cycles
from atlantis.analysis import Attractor, find_cycle
from atlantis.fates import load_fate_logic
from atlantis.io import load_fixed_nodes, load_mutations, load_rules, load_states


def main():
    root = Path('examples/Case Study 3/Input Files')
    details = root / 'Network Details'
    network = load_rules(details/'Node List.txt', details/'Boolean logic for nodes',
                         missing_policy='unspecified')
    fixed = load_fixed_nodes(next(root.glob('**/Input Node States.csv')))
    network.clamped = {network.names[network.index(k)]: v for k,v in fixed.items()}
    unused = set(network.metadata['unspecified_rules']) - network.clamped.keys()
    assert not any(set(rule.sources) & {network.index(k) for k in unused}
                   for rule in network.rules if rule)
    logic = load_fate_logic(next(root.glob('**/*Fate Determination Logic.csv')), network)
    assert not set(logic.nodes) & {network.index(k) for k in unused}
    network.clamped.update(dict.fromkeys(unused, 0))
    network = network.mutate(load_mutations(root/'Mutation Files/APC+RAS+PTEN+P53.txt'))
    archive, = Path('reference/Toolbox/Results').glob('*Node List/**/Network State List DA.mat')
    states = load_states(archive, network.n)
    for name, value in network.clamped.items():
        states[:,network.index(name)] = value
    unresolved = []
    for i in range(0,len(states),1024):
        batch = states[i:i+1024]
        found = sample_cycles(network,batch,200)
        unresolved.extend(i+j for j in range(len(batch)) if j not in found)
    assert len(unresolved) == 23
    extended = sample_cycles(network,states[unresolved],5000)
    rows = []
    for j,i in enumerate(unresolved):
        assert find_cycle(network,states[i],200) is None
        row = {'archive_row_one_based': i+1}
        if j in extended:
            cycle = extended[j]
            state = states[i]
            entry = 0
            while not (cycle == state).all(axis=1).any():
                state = network.step(state)[0]
                entry += 1
            independent = find_cycle(network,states[i],5000)
            assert {x.tobytes() for x in independent} == {x.tobytes() for x in cycle}
            row.update(transient=entry,period=len(cycle),first_repeat=entry+len(cycle),
                       fate=logic.associate(Attractor(cycle,0).stratified))
        else:
            row['unresolved_at'] = 5000
        rows.append(row)
    Path('validation/colorectal-unresolved-024.json').write_text(json.dumps(rows,indent=2))
    print(rows)


if __name__ == '__main__':
    main()
