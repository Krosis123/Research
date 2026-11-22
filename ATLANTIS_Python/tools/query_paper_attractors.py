"""Query deterministic attractors under the bundled case-study conditions."""
import json
import numpy as np
from check_paper_transitions import ROOT, cases
from atlantis.states import all_states
from atlantis.io import load_fixed_nodes, load_mutations
from atlantis.analysis import deterministic_analysis


def main():
    rows = []
    for case, name, net, states in cases():
        p = ROOT / f'examples/Case Study {case}/Input Files'
        if states is None:
            states = all_states(net.n)
        else:
            fixed = load_fixed_nodes(next(p.rglob('Input Node States.csv')))
            net.clamped.update({net.names[net.index(k)]: v for k, v in fixed.items()})
        controls = {3: ['Control', 'APC+RAS+PTEN+P53'],
                    4: ['HCT-116 Control', 'HCT-116 EGFR inhibition']}.get(case, [None])
        for condition in controls:
            model = net.mutate(load_mutations(p/'Mutation Files'/f'{condition}.txt')) if condition else net
            result = deterministic_analysis(model, states, 200)
            rows.append(dict(case=case, model=name, condition=condition, starts=len(states),
                             clamped=model.clamped, unresolved=result.unresolved,
                             attractors=[dict(period=len(a.states), fraction=a.basin,
                                              representative=''.join(map(str, a.states[0]))) for a in result.attractors]))
    (ROOT/'validation/paper-attractors.json').write_text(json.dumps(rows, indent=2)+'\n')


if __name__ == '__main__':
    main()

