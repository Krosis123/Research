"""Measure transpiler levels on fixed paper-faithful circuits."""
import json
from pathlib import Path
from statistics import median
import sys
from threading import Event,Thread
from time import perf_counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import psutil

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from atlantis.expressions import from_expressions
from atlantis.quantum.adapter import QuantumNetwork
from atlantis.quantum.ross.circuits import search_circuit,counting_circuit,qiskit_counts


def measure(circuit,level,seed):
    proc=psutil.Process()
    start_rss=proc.memory_info().rss
    samples=[start_rss]
    stop=Event()
    def poll():
        while not stop.wait(.005):
            samples.append(proc.memory_info().rss)
    worker=Thread(target=poll,daemon=True)
    worker.start()
    start=perf_counter()
    try:
        counts,metrics=qiskit_counts(circuit,512,method='matrix_product_state',
                                    optimization_level=level,seed=seed)
        return counts,dict(**metrics,wall_s=perf_counter()-start,
                           rss_start_bytes=start_rss,observed_peak_rss_bytes=max(samples+[proc.memory_info().rss]))
    finally:
        stop.set()
        worker.join()


def main():
    root=Path('validation')
    rows=[]
    for n,fanin,T,marked_count in ((3,1,1,1),(4,2,1,1),(4,2,1,2),
                                   (4,2,3,2),(5,4,1,2),(5,4,2,3)):
        genes=[f'x{i}' for i in range(n)]
        model=QuantumNetwork(from_expressions({name:name if i<fanin else ' ^ '.join(genes[:fanin])
                                               for i,name in enumerate(genes)}))
        attractors=[f'{i:0{fanin}b}'+str(i.bit_count()%2)*(n-fanin) for i in range(2**fanin)]
        excluded=attractors[:marked_count]
        expected_marked=marked_count*2**(n-fanin)
        tasks=['search','qpe'] if n<=4 and T==1 else ['search']
        for task in tasks:
            start=perf_counter()
            if task=='search':
                circuit,_=search_circuit(model,T,excluded,expected_marked)
            else:
                circuit=counting_circuit(model,T,excluded,3)
            build=perf_counter()-start
            for level in (0,2):
                for seed in range(2):
                    counts,metrics=measure(circuit,level,seed)
                    if task=='search':
                        assert set(counts)<=set(attractors)-set(excluded)
                    rows.append(dict(nodes=n,fanin=fanin,T=T,suppressed=marked_count,
                        task=task,precision=3 if task=='qpe' else None,
                        ancillas=circuit.num_ancillas,expected_marked=expected_marked,
                        optimization_level=level,seed=seed,shots=512,counts=counts,
                        circuit_construction_s=build,**metrics))
    (root/'optimization-023.json').write_text(json.dumps(rows,indent=2))
    search=[r for r in rows if r['task']=='search']
    cases=sorted({(r['nodes'],r['fanin'],r['T'],r['suppressed']) for r in search})
    labels=[f'n{n}/f{f}/T{t}/m{m}' for n,f,t,m in cases]
    for level in (0,2):
        y=[median(r['compiled_2q_count'] for r in search if
                 (r['nodes'],r['fanin'],r['T'],r['suppressed'])==case and
                 r['optimization_level']==level) for case in cases]
        plt.plot(labels,y,marker='o',label=f'optimization level {level}')
    plt.ylabel('Transpiled two-qubit gates')
    plt.xticks(rotation=30)
    plt.legend()
    plt.tight_layout()
    plt.savefig(root/'optimization-023.png',dpi=180)
    print(len(rows),'executed circuit measurements')


if __name__=='__main__':
    main()
