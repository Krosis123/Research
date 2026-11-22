"""Evaluate a synchronous Boolean transition in independent reversible rule blocks."""
import hashlib
import json
import random
from pathlib import Path

from qiskit import QuantumCircuit, transpile


def condition_rules(rules, state, max_inputs=2):
    reduced = {}
    for gene,(names,table) in rules.items():
        names = list(names)
        while len(names)>max_inputs:
            choices = []
            for i,n in enumerate(names):
                half = [v for k,v in enumerate(table) if (k>>i)&1 == state[n]]
                choices.append((min(sum(half),len(half)-sum(half)),i,half))
            # Retain a nonconstant hardware function whenever possible.
            _,i,table = max(choices,key=lambda choice:choice[0])
            names.pop(i)
        reduced[gene] = names,table
    return reduced


def compile_block(rules, state):
    inputs = sorted({name for names, table in rules.values() for name in names})
    qc = QuantumCircuit(len(inputs) + len(rules), len(rules))
    for i, name in enumerate(inputs):
        if state[name]:
            qc.x(i)
    for j, (names, table) in enumerate(rules.values()):
        # Collapse constant subtrees into disjoint control patterns.
        def cubes(values, remaining, controls):
            if all(v == values[0] for v in values):
                return [(values[0], controls)]
            candidates = []
            for i, name in enumerate(remaining):
                halves = [[v for k,v in enumerate(values) if ((k >> i) & 1) == b] for b in (0,1)]
                score = sum(len(set(h)) == 1 for h in halves)
                candidates.append((score,i,halves))
            _,i,halves = max(candidates,key=lambda x:x[0])
            rest = remaining[:i] + remaining[i+1:]
            return [leaf for bit,half in enumerate(halves)
                    for leaf in cubes(half,rest,controls+[(inputs.index(remaining[i]),bit)])]
        leaves = cubes(table,names,[])
        out = len(inputs)+j
        cost = lambda bit: sum(2**len(c) for v,c in leaves if v == bit)
        value = cost(True) <= cost(False)
        if not value:
            qc.x(out)
        for v,controls in leaves:
            if v != value:
                continue
            neg = [i for i,b in controls if not b]
            for i in neg:
                qc.x(i)
            if controls:
                qc.mcx([i for i,b in controls],out)
            else:
                qc.x(out)
            for i in neg:
                qc.x(i)
        qc.measure(out, j)
    return qc


def main(backend=None):
    from audit_imc1010 import ids, codes, env, source, root
    from qiskit_aer import AerSimulator
    mapping = dict(zip(ids, codes))
    deps = {n: sorted(set(c.co_names).intersection(ids)) for n,c in mapping.items()}
    selected = []
    while len(selected) < 500:
        ready = [n for n in ids if n not in selected and set(deps[n]).issubset(selected)]
        selected.append(max(ready,key=lambda n: (bool(deps[n]), bool(mapping[n].co_names))))
    rng = random.Random(425)
    state = {n:rng.randrange(2) for n in selected}
    rules = {}
    for n in selected:
        names = deps[n]
        table = [bool(eval(mapping[n],{'__builtins__':{}},env | {v:(mask>>i)&1 for i,v in enumerate(names)})) for mask in range(1<<len(names))]
        if len(set(table)) == 1:
            names, table = [], table[:1]
        rules[n] = names, table
    (root/'research_sources/imc500-boolean-model.json').write_text(json.dumps(dict(state=state,rules=rules),indent=2))
    expected = {n:int(bool(eval(mapping[n],{'__builtins__':{}},env | state))) for n in selected}
    blocks = [selected[i:i+12] for i in range(0,len(selected),12)]
    conditioned = condition_rules(rules,state)
    circuits = [compile_block({n:conditioned[n] for n in block},state) for block in blocks]
    target = backend or AerSimulator()
    compiled = transpile(circuits,target,optimization_level=1,seed_transpiler=425,num_processes=1)
    path = root/'research_sources'/('imc500-hardware.json' if backend else 'imc500-simulation.json')
    report = dict(max_retained_inputs=2,nonconstant_after_conditioning=sum(len(set(t))>1 for ns,t in conditioned.values()),backend=target.name,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),state=state,expected=expected,external=env,blocks=blocks,depths=[q.depth() for q in compiled],nonconstant=sum(bool(ns) for ns,t in rules.values()))
    if backend:
        from qiskit_ibm_runtime import SamplerV2
        job = SamplerV2(mode=backend).run(compiled,shots=256)
        report['job_id']=job.job_id()
        path.write_text(json.dumps(report))
        print('Submitted',job.job_id(),flush=True)
        counts=[r.data.c.get_counts() for r in job.result()]
    else:
        counts=target.run(compiled,shots=256).result().get_counts()
    report['counts']=counts
    report['mismatches']=[n for block,hist in zip(blocks,counts) for j,n in enumerate(block) if sum(k for s,k in hist.items() if int(s[-1-j])==expected[n])<=128]
    path.write_text(json.dumps(report,indent=2))
    print(target.name,len(selected),len(report['mismatches']),report['nonconstant'],max(report['depths']))
if __name__=='__main__':
    main(globals().get('live_backend'))
