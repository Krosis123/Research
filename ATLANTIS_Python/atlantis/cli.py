"""Optional command line interface to the same desktop analysis engines."""
import argparse
from pathlib import Path
from .io import load_network,load_rules,load_states,load_mutations,export_results
from .states import all_states,random_states
from .fates import load_fate_logic
from .analysis import deterministic_analysis,probabilistic_analysis


def main():
    p=argparse.ArgumentParser(description='ATLANTIS Boolean network analysis')
    p.add_argument('network',help='Weighted CSV/TXT/JSON, or rules node list with --tables')
    p.add_argument('--tables',help='Truth table folder')
    p.add_argument('--allow-missing',action='store_true',help='Explicitly retain states of nodes whose tables are absent')
    p.add_argument('--states');p.add_argument('--sample',type=int);p.add_argument('--seed',type=int)
    p.add_argument('--mutations');p.add_argument('--fates');p.add_argument('--probabilistic',action='store_true');p.add_argument('--prune',action='store_true')
    p.add_argument('--duration',type=int,default=200);p.add_argument('--steps',type=int,default=1000);p.add_argument('--noise',type=float,default=5);p.add_argument('--degradation',type=float,default=.001);p.add_argument('--error',type=float,default=1e-7)
    p.add_argument('--output',default='results');a=p.parse_args()
    try:
        n=load_rules(a.network,a.tables,a.allow_missing) if a.tables else load_network(a.network)
        if a.mutations:n=n.mutate(load_mutations(a.mutations))
        s=load_states(a.states,n.n) if a.states else random_states(n.n,a.sample,a.seed) if a.sample else all_states(n.n)
        logic=load_fate_logic(a.fates,n) if a.fates else None
        d=deterministic_analysis(n,s,a.duration,logic)
        r=probabilistic_analysis(n,s,a.noise,a.degradation,a.steps,a.error,a.prune,logic) if a.probabilistic else None
        export_results(a.output,n,d,r)
        print(f'{len(d.attractors)} attractors; {d.unresolved} unresolved initial states. Results: {Path(a.output).resolve()}')
        if r:print(f'Master equation: {r.iterations} steps; converged={r.converged}')
    except (ValueError,MemoryError,OSError) as e:p.error(str(e))
    return 0

if __name__=='__main__':raise SystemExit(main())
