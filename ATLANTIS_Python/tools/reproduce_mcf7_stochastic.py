"""Replay pruned MCF-7 stochastic analyses and compare saved MATLAB vectors."""
import json
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from atlantis.analysis import probabilistic_analysis, deterministic_analysis
from atlantis.io import load_weighted,load_mutations,read_rows
from atlantis.fates import load_fate_logic
from atlantis.states import all_states


def main():
    base=Path('examples/Case Study 2/Input Files')
    rows=[]
    for etoposide,path in ((False,'DNA Damge OFF/Control_MCF7 (0).csv'),
                           (True,'DNA Damge ON/Etoposide.csv')):
        network=load_weighted(base/'Network files'/path)
        for treatment in ('Control','Nutlin','Wip1 KD','Nutlin + Wip KD'):
            model=network.mutate(load_mutations(base/'Mutation Files'/f'{treatment}.txt'))
            logic=load_fate_logic(base/'Cell Fate Determination Logic.csv',model)
            result=probabilistic_analysis(model,all_states(model.n),noise=5,degradation=.001,
                                          max_steps=1000,error=1e-7,prune=True,fate_logic=logic)
            actual={tuple(s):float(v) for s,v in zip(result.states,result.probabilities)}
            p=result.probabilities
            drift=result.transition.T @ p - p * result.transition.sum(axis=1)
            label=('Etoposide + ' if etoposide else '')+treatment
            row=dict(condition=label,states=len(actual),iterations=result.iterations,
                     converged=bool(result.converged),mass=sum(actual.values()),
                     flux_residual_inf=float(np.linalg.norm(drift,ord=np.inf)),
                     flux_residual_l1=float(np.linalg.norm(drift,ord=1)),
                     mass_by_fate={f:sum(float(p) for p,x in zip(result.probabilities,result.fates) if x==f)
                                   for f in sorted(set(result.fates))})
            if not etoposide and treatment in ('Control','Nutlin'):
                archived,=Path('reference/Toolbox/Results').rglob(f'{treatment} - Steady State Probabilities.csv')
                expected={tuple(map(int,r[3:3+model.n])):float(r[2]) for r in read_rows(archived)[1:]}
                if set(actual)==set(expected):
                    error={str(k):abs(actual[k]-expected[k]) for k in actual}
                    row.update(archive=str(archived),max_abs_error=max(error.values()),
                               l1_error=sum(error.values()))
                else:
                    row.update(archive=str(archived),state_set_difference=len(actual.keys()^expected.keys()))
                replay=probabilistic_analysis(model,np.asarray(list(expected),dtype=np.uint8),
                    noise=5,degradation=.001,max_steps=1000,error=1e-7,prune=False)
                delta=replay.probabilities-np.asarray(list(expected.values()))
                row['archived_state_replay']={'states':len(expected),'iterations':replay.iterations,
                    'converged':bool(replay.converged),'max_abs_error':float(np.max(abs(delta))),
                    'l1_error':float(np.sum(abs(delta))), 'archived_mass':sum(expected.values())}
            if etoposide and treatment=='Nutlin + Wip KD':
                deterministic=deterministic_analysis(model,all_states(model.n),200,logic)
                row['point_attractors']=[dict(state=a.states[0].tolist(),fate=a.fate,
                    probability=actual.get(tuple(a.states[0]))) for a in deterministic.attractors if len(a.states)==1]
            rows.append(row)
            print(row,flush=True)
    Path('validation/mcf7-stochastic-023.json').write_text(json.dumps(dict(
        noise=5,degradation=.001,max_steps=1000,tolerance=1e-7,results=rows),indent=2))


if __name__=='__main__':
    main()
