"""Measured benchmark matrix; run from project root: python tools/benchmark_integrated.py."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse,csv,json,time,statistics,platform
from dataclasses import replace
import numpy as np
import psutil
from atlantis.io import load_network,network_to_dict
from atlantis.expressions import from_expressions
from atlantis.states import all_states,random_states
from atlantis.analysis import deterministic_analysis
from atlantis.quantum.adapter import QuantumNetwork
from atlantis.quantum.engine import Settings,run,preflight
from atlantis.quantum.ross.model import exact_truth,make_network


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repetitions',type=int,default=20)
    parser.add_argument('--output',default='validation/benchmark-current');args=parser.parse_args()
    root=Path(args.output);root.mkdir(parents=True,exist_ok=True)
    nets=[(load_network('examples/quantum/rossini4.json'),3),(load_network('examples/quantum/giacomantonio5.json'),4)]
    for n in (4,10,15):
        for family in ('projection','skewed','cycle2','long_chain'):
            old=make_network(n,family)
            nets.append((from_expressions(dict(zip(old.genes,[r.expression for r in old.rules])),old.name),n-1 if family=='long_chain' else 1))
    rows=[];estimates=[]
    def record(row):
        rows.append(row)
        with (root/'raw.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(row)+'\n')
    if (root/'raw.jsonl').exists():raise ValueError('Use a new output directory to avoid mixing runs')
    for net,T in nets:
        q=QuantumNetwork(net);start=time.perf_counter();truth=exact_truth(q);truth_seconds=time.perf_counter()-start
        estimates.append({'network':net.name,'n':net.n,'T':T,'classical_truth_s':truth_seconds,
                          'basins':{str(c):v for c,v in truth.basin_sizes.items()},
                          'preflight':preflight(net,Settings(T=T,engine='aer'))})
        # Cheap reference/sampling protocols repeated 20 times; larger costly Aer resource-only.
        protocols=[('classical_sample',None),('reference_exact',Settings(T=T,shots=128,max_rounds=12))]
        if net.n<=5:
            protocols += [('classical_exhaustive',None),('aer_exact',Settings(T=T,engine='aer',shots=128,max_qubits=26))]
        if net.name=='rossini4':
            protocols += [('aer_qpe',Settings(T=T,engine='aer',counting_mode='qpe_aer',stop_policy='qpe',counting_precision=3,shots=128)),
                          ('aer_noisy',Settings(T=T,engine='aer',noise_probability=.002,shots=128))]
        for protocol,settings in protocols:
            reps=min(args.repetitions,3) if protocol in ('aer_qpe','aer_noisy') or (net.n==15 and protocol=='reference_exact') else args.repetitions
            for seed in range(reps):
                start=time.perf_counter()
                row={'network':net.name,'n':net.n,'T':T,'protocol':protocol,'seed':seed,'repetitions':reps,
                     'truth_runtime_s_separate':truth_seconds,'truth_attractors':len(truth.attractors)}
                try:
                    if settings is None:
                        states=all_states(net.n) if protocol=='classical_exhaustive' else random_states(net.n,min(128,1<<net.n),seed)
                        result=deterministic_analysis(net,states,1000)
                        found={tuple(sorted(int(''.join(map(str,s)),2) for s in a.states)) for a in result.attractors}
                        row.update(status='exact' if protocol=='classical_exhaustive' and not result.unresolved else 'sampled',
                                   unresolved=result.unresolved,sample_count=len(states))
                    else:
                        result=run(net,replace(settings,seed=seed))
                        found={tuple(sorted(int(s,2) for s in c)) for c in result['cycles']}
                        row.update(status=result['status'],qubits=result['resources']['circuit_qubits'],
                                   search_runtime_s=result['search_runtime_s'],counting_runtime_s=result['counting_runtime_s'],
                                   simulation_runtime_s=result['simulation_runtime_s'],depth=result['compiled_depth_max'],
                                   two_qubit_gates=result['compiled_2q_count_max'],
                                   rejected_measurements=result['rejected_measurements'],total_measurements=result['total_measurements'])
                        if seed==0:(root/f'{net.name}-{protocol}.json').write_text(json.dumps(result,indent=2),encoding='utf8')
                    expected={tuple(sorted(c)) for c in truth.attractors}
                    row.update(recall=len(found&expected)/len(expected),precision=len(found&expected)/max(1,len(found)))
                except Exception as e:row.update(status='failed',error=type(e).__name__+': '+str(e))
                row['wall_s']=time.perf_counter()-start
                row['process_peak_rss_mib']=getattr(psutil.Process().memory_info(),'peak_wset',psutil.Process().memory_info().rss)/1024**2
                record(row)
            print(net.name,protocol,reps,flush=True)
    (root/'resources.json').write_text(json.dumps(estimates,indent=2))
    fields=sorted(set().union(*(r.keys() for r in rows)))
    with (root/'raw.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    summaries=[]
    for key in sorted({(r['network'],r['protocol']) for r in rows}):
        group=[r for r in rows if (r['network'],r['protocol'])==key]
        times=[r['wall_s'] for r in group]
        summaries.append({'network':key[0],'protocol':key[1],'repetitions':len(group),
            'median_s':statistics.median(times),'q25_s':float(np.quantile(times,.25)),'q75_s':float(np.quantile(times,.75)),
            'mean_recall':statistics.mean(r.get('recall',0) for r in group),
            'failures':sum(r['status']=='failed' for r in group),
            'inconclusive':sum(r['status'].startswith('inconclusive') for r in group)})
    (root/'summary.json').write_text(json.dumps(summaries,indent=2))
    from matplotlib.figure import Figure
    fig=Figure(figsize=(12,6));ax=fig.subplots()
    small=[s for s in summaries if s['network']=='rossini4']
    ax.bar([s['protocol'] for s in small],[s['median_s'] for s in small]);ax.set_yscale('log')
    ax.set_ylabel('Median measured wall seconds (log scale)');ax.set_title('Rossini4 — distinct execution protocols; no speedup claim')
    ax.tick_params(axis='x',rotation=25);fig.tight_layout();fig.savefig(root/'runtime.png',dpi=150)
    (root/'environment.json').write_text(json.dumps({'python':sys.version,'platform':platform.platform(),
        'memory_metric':'process lifetime peak, not per-run isolated peak','reduced_repetitions':'3 for noisy/QPE and 15-node reference due cost'},indent=2))


if __name__=='__main__':main()
