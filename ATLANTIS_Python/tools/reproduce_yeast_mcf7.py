"""Run the supplied yeast baseline and all eight MCF-7 treatment combinations."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atlantis.analysis import deterministic_analysis
from atlantis.fates import load_fate_logic
from atlantis.io import load_mutations, load_weighted
from atlantis.states import all_states


def measure(net, fate_path, label):
    result = deterministic_analysis(net,all_states(net.n),200,load_fate_logic(fate_path,net))
    return dict(condition=label,n=len(result.initial_states),unresolved=result.unresolved,
                fates=result.fate_propensities,attractors=[
                    dict(period=len(a.states),states=a.states.tolist(),basin=a.basin,fate=a.fate)
                    for a in result.attractors])


def main():
    yeast = Path('examples/Case Study 1/Input Files')
    fate_filename = 'Cell Fate Determination Logic.csv'
    rows = [measure(load_weighted(yeast/'NetworkFile.csv'),yeast/fate_filename,'Yeast')]
    mcf7 = Path('examples/Case Study 2/Input Files')
    for etoposide, path in (
        (False,'Network files/DNA Damge OFF/Control_MCF7 (0).csv'),
        (True,'Network files/DNA Damge ON/Etoposide.csv')):
        net = load_weighted(mcf7/path)
        for treatment in ('Control','Nutlin','Wip1 KD','Nutlin + Wip KD'):
            model = net.mutate(load_mutations(mcf7/'Mutation Files'/f'{treatment}.txt'))
            label = ('Etoposide + ' if etoposide else '') + treatment
            rows.append(measure(model,mcf7/fate_filename,label))
            print(label,rows[-1]['fates'],flush=True)
    Path('validation/yeast-mcf7-reproduction.json').write_text(json.dumps(rows,indent=2))


if __name__ == '__main__':
    main()
