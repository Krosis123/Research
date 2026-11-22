"""Benchmark complete three-input Boolean rules using shared gate templates."""
import json
import random
from pathlib import Path
from getpass import getpass
from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

def run(backend,model):
    state,rules=model["state"],model["rules"]
    expected={}
    circuits=[]
    genes=list(rules)
    for start in range(0,len(genes),6):
        block=genes[start:start+6]
        names=sorted({v for n in block for v in rules[n][0]})
        q=QuantumCircuit(len(names)+len(block),len(block))
        for i,v in enumerate(names):
            if state[v]:
                q.x(i)
        q.barrier()
        for j,n in enumerate(block):
            regs,table=rules[n]
            expected[n]=table[sum(state[v]<<i for i,v in enumerate(regs))]
            # Choose a fixed input polarity to reduce expensive multi-control gates.
            candidates=[]
            for polarity in range(len(table)) if len(regs)<=5 else [0]:
                terms=[table[k^polarity] for k in range(len(table))]
                for i in range(len(regs)):
                    for mask in range(len(terms)):
                        if mask & (1<<i):
                            terms[mask]^=terms[mask^(1<<i)]
                cost=sum(4**mask.bit_count() for mask,active in enumerate(terms) if active)
                candidates.append((cost+2*polarity.bit_count(),polarity,terms))
            _,polarity,terms=min(candidates)
            target=len(names)+j
            inverted=[names.index(v) for i,v in enumerate(regs) if polarity & (1<<i)]
            for i in inverted:
                q.x(i)
            for mask,active in enumerate(terms):
                if active:
                    ctrl=[names.index(v) for i,v in enumerate(regs) if mask & (1<<i)]
                    if ctrl:
                        q.mcx(ctrl,target)
                    else:
                        q.x(target)
            for i in inverted:
                q.x(i)
            q.measure(target,j)
        circuits.append(q)
    compiled=transpile(circuits,backend,optimization_level=2,seed_transpiler=41,num_processes=1)
    job=SamplerV2(mode=backend).run(compiled,shots=256)
    print(job.job_id(),flush=True)
    counts=[r.data.c.get_counts() for r in job.result()]
    votes={n:sum(k for s,k in counts[i//6].items() if int(s[-1-i%6])==expected[n]) for i,n in enumerate(genes)}
    report=dict(model=model,backend=backend.name,job=job.job_id(),counts=counts,expected=expected,votes=votes,depths=[q.depth() for q in compiled])
    Path(f"research_sources/network300-{job.job_id()}.json").write_text(json.dumps(report))
    print(backend.name,sum(k>128 for k in votes.values()),max(report["depths"]))

    return report

if __name__=="__main__":
    import sys
    rng=random.Random(7321)
    genes=[f"v{i}" for i in range(300)]
    model=dict(state={n:rng.randrange(2) for n in genes},rules={n:[rng.sample(genes,3),[rng.randrange(2) for _ in range(8)]] for n in genes})
    if len(sys.argv)>1:
        model=json.loads(Path(sys.argv[1]).read_text())
    service=QiskitRuntimeService(channel="ibm_quantum_platform",token=getpass("Key: "),instance=getpass("Instance: "))
    backend=service.least_busy(operational=True,simulator=False,min_num_qubits=40)
    run(backend,model)
    if len(sys.argv)==1:
        full=json.loads(Path("research_sources/imc500-boolean-model.json").read_text())
        genes=list(full["rules"])[:300]
        assert all(set(full["rules"][n][0])<=set(genes) for n in genes)
        run(backend,{key:{n:full[key][n] for n in genes} for key in ("state","rules")})

