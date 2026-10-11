"""Machine-readable network contracts reusable by fixed-point and ATLANTIS adapters."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from .model import make_network,exact_truth


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--nodes',type=int,nargs='+',default=[4,10,15])
    p.add_argument('--output-dir',default='network_definitions')
    args=p.parse_args()
    dest=Path(args.output_dir);dest.mkdir(exist_ok=True,parents=True)
    for n in args.nodes:
        families=['rossini4','projection','skewed','cycle2','long_chain'] if n==4 else ['projection','skewed','cycle2','long_chain']
        for family in families:
            net=make_network(n,family);truth=exact_truth(net)
            payload={
                'format':'synchronous_boolean_network_v1',
                'model_type':'deterministic_synchronous',
                'name':net.name,'n':net.n,'node_order':list(net.genes),
                'rules':{name:rule.expression for name,rule in zip(net.genes,net.rules)},
                'transient_bound_exact':truth.max_transient,
                'attractor_truth':[{'cycle':[net.as_bits(s) for s in cycle],
                                    'basin_size':truth.basin_sizes[cycle]}
                                   for cycle in truth.attractors],
                'provenance':'synthetic except rossini4 from uploaded reproduction',
                'note':'Ground-truth data must be excluded from the quantum solver input.'}
            (dest/f'{net.name}.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print('Wrote files to',dest)

if __name__=='__main__':main()
