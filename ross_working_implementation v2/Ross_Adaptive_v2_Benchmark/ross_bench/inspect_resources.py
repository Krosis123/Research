"""Construct actual Qiskit circuits and record gate resources WITHOUT executing shots."""
from __future__ import annotations
import argparse,csv
from pathlib import Path
from .model import make_network,exact_truth
from .circuits import search_circuit


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--nodes',type=int,nargs='+',default=[4,10,15])
    p.add_argument('--families',nargs='+',default=['rossini4','projection','skewed','cycle2','long_chain'])
    p.add_argument('--output',default='results/circuit_resource_estimates.csv')
    p.add_argument('--transpile',action='store_true',help='Transpile (may take long and exhaust memory).')
    args=p.parse_args()
    rows=[]
    for n in args.nodes:
        for family in args.families:
            if family=='rossini4' and n!=4: continue
            net=make_network(n,family);t=exact_truth(net);T=max(1,t.max_transient)
            for suppressed in (False,True):
                # The suppressed circuit excludes one full attractor cycle.
                first=t.attractors[0] if suppressed else ()
                M=t.basin_sizes[first] if suppressed else 0
                if M==net.size:continue
                try:
                    circuit,params=search_circuit(net,T,[net.as_bits(s) for s in first],M)
                    row=dict(n=n,family=family,T=T,qubits=circuit.num_qubits,
                             excluded_first_cycle=suppressed,M=M,J=params.J if params else 0,
                             raw_depth=circuit.depth(),raw_size=circuit.size(),
                             counting_qubits_extra='p (choose QPE precision)',
                             statevector_gib=16*2.0**circuit.num_qubits/(1024**3),status='built')
                    if args.transpile:
                        from qiskit import transpile
                        compiled=transpile(circuit,basis_gates=['cx','rz','sx','x','h'],optimization_level=0)
                        row.update(compiled_depth=compiled.depth(),compiled_size=compiled.size(),
                                   compiled_2q=compiled.count_ops().get('cx',0))
                except Exception as e:
                    row=dict(n=n,family=family,T=T,excluded_first_cycle=suppressed,
                             status='error',error=repr(e))
                rows.append(row)
                print(f'{family} n={n} suppressed={suppressed}: {row["status"]}',flush=True)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    columns=sorted({k for r in rows for k in r})
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)
    print(path)

if __name__=='__main__':main()
