"""Reproduce the requested local demonstration without GUI clicks."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from atlantis.io import load_network,export_results
from atlantis.states import all_states,random_states
from atlantis.analysis import deterministic_analysis
from atlantis.quantum.engine import Settings,preflight
from atlantis.experiments import execute,JobStore


def main():
    out=Path('validation/demo-current');out.mkdir(exist_ok=True)
    net=load_network('examples/quantum/rossini4.json')
    result=deterministic_analysis(net,all_states(4),100)
    export_results(out/'classical',net,result)
    store=JobStore(out/'jobs.sqlite3')
    for engine in ('reduced','aer'):
        r=execute(net,Settings(engine=engine),store=store)
        (out/f'{engine}.json').write_text(json.dumps(r,indent=2))
    large=load_network('examples/quantum/large150.json')
    assessment=preflight(large,Settings(engine='aer'))
    assert not assessment['eligible']
    d=deterministic_analysis(large,random_states(150,128,42),10)
    assessment['classical_sampled']=d.coverage
    assessment['classical_attractors']=len(d.attractors)
    (out/'large150.json').write_text(json.dumps(assessment,indent=2))
    print('Demo complete:',out.resolve())

if __name__=='__main__':main()
