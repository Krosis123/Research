"""Paired discovery pilot for in-run reuse of identical compiled circuits."""
import json
from pathlib import Path
from random import Random
from time import perf_counter

from qiskit import transpile
from qiskit_aer import AerSimulator
from validate_discovery_024 import network_fixture,evaluate
from atlantis.quantum.engine import Settings,run


def main():
    rows=[]
    cached_first=[False]*4+[True]*4
    Random(24024).shuffle(cached_first)
    orders=iter(cached_first)
    for width,fixture_seed,fanin,horizon in ((2,11,2,3),(3,17,2,4)):
        network,inputs,tables=network_fixture(width,fixture_seed,fanin)
        for seed in (23,47,71,89):
            signatures=[]
            first=next(orders)
            for position,enabled in enumerate((first,not first),1):
                backend=AerSimulator(method='matrix_product_state',max_parallel_threads=2)
                compiled_circuits=[]
                hits=0
                def executor(qc,shots,**options):
                    nonlocal hits
                    start=perf_counter()
                    compiled=next((mapped for original,mapped in compiled_circuits if qc==original),None)
                    if compiled is None:
                        compiled=transpile(qc,basis_gates=['u','cx'],optimization_level=2,seed_transpiler=17)
                        if enabled:
                            compiled_circuits.append((qc,compiled))
                    else:
                        hits+=1
                    compile_time=perf_counter()-start
                    if compiled.depth()>options['max_depth'] or compiled.size()>options['max_gates']:
                        raise ValueError('Compiled circuit exceeds resource guard')
                    start=perf_counter()
                    counts=backend.run(compiled,shots=shots,seed_simulator=options['seed']).result().get_counts()
                    return counts,dict(compiled_depth=compiled.depth(),compiled_size=compiled.size(),
                       compiled_2q_count=sum(len(x.qubits)==2 for x in compiled.data),
                       transpilation_s=compile_time,execution_s=perf_counter()-start)
                start=perf_counter()
                result=run(network,Settings(T=horizon,engine='aer_mps',counting_mode='qpe_aer',
                           stop_policy='qpe',shots=128,counting_shots=128,seed=seed),circuit_executor=executor)
                wall=perf_counter()-start
                events=[e['resources'] for e in result['history'] if e['kind']=='circuit_execution']
                signatures.append([e for e in result['history'] if e['kind']!='circuit_execution'])
                rows.append(dict(width=width,fixture_seed=fixture_seed,T=horizon,seed=seed,cached=enabled,
                    cached_first=first,position=position,
                    cache_hits=hits,wall_s=wall,transpile_s=sum(x['transpilation_s'] for x in events),
                    simulation_s=sum(x['execution_s'] for x in events),status=result['status'],
                    score=evaluate(width,inputs,tables,horizon,result)))
            assert signatures[0]==signatures[1]
    Path('validation/discovery-cache-counterbalanced-024.json').write_text(json.dumps(rows,indent=2))
    print([(r['fixture_seed'],r['cached'],r['cache_hits'],round(r['wall_s'],3)) for r in rows])


if __name__=='__main__':
    main()
