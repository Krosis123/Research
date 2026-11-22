"""Run one synchronous transition from a JSON truth-table network.

Input fields: state (gene -> 0/1), rules (gene -> [ordered regulators, table]).
Table index bit i is the value of regulator i. Cyclic networks are supported.
Pass a physical backend to run_update from Python, or use the CLI simulator.
"""
import argparse
import json
from pathlib import Path
from qiskit import transpile
from qiskit_aer import AerSimulator
from gene_block_update import compile_block, condition_rules


def run_update(model, backend=None, shots=256):
    state, rules = model["state"], model["rules"]
    if not rules or rules.keys()!=state.keys() or any(x not in (0,1) for x in state.values()):
        raise ValueError("Supply one binary initial value per gene")
    for gene,(names,table) in rules.items():
        if len(set(names))!=len(names) or set(names)-state.keys() or len(table)!=1<<len(names) or any(x not in (0,1) for x in table):
            raise ValueError(f"Invalid rule for {gene}")
    rules = condition_rules(rules,state)
    target = backend or AerSimulator(method="matrix_product_state",max_parallel_threads=2)
    width = target.num_qubits
    blocks, block, inputs = [], [], set()
    for gene,(names,table) in rules.items():
        if len(names)+1>width:
            raise ValueError(f"Rule for {gene} exceeds backend width")
        if len(inputs.union(names))+len(block)+1>width or len(block)>=12:
            blocks.append(block)
            block,inputs=[],set()
        block.append(gene)
        inputs.update(names)
    blocks.append(block)
    circuits=transpile([compile_block({n:rules[n] for n in b},state) for b in blocks],target,optimization_level=1,num_processes=1,seed_transpiler=425)
    if backend:
        from qiskit_ibm_runtime import SamplerV2
        job=SamplerV2(mode=backend).run(circuits,shots=shots)
        print("Submitted",job.job_id(),flush=True)
        counts=[result.data.c.get_counts() for result in job.result()]
    else:
        job=target.run(circuits,shots=shots)
        result=job.result()
        counts=[result.get_counts(i) for i in range(len(blocks))]
    ones={n:sum(k for s,k in h.items() if s[-1-i]=="1") for b,h in zip(blocks,counts) for i,n in enumerate(b)}
    return dict(backend=target.name,job_id=job.job_id(),shots=shots,ones=ones,
                next_state={n:None if 2*k==shots else int(2*k>shots) for n,k in ones.items()})

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model",type=Path)
    args=parser.parse_args()
    print(json.dumps(run_update(json.loads(args.model.read_text()))))

