from pathlib import Path
from getpass import getpass
import json
from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

def classical(x, kind):
    a,b,c,d = [(x>>i)&1 for i in range(4)]
    feedback = {"ring":1-d,"linear":a^d,"nonlinear":d^(a&b)}[kind]
    return ((x<<1)&15)|feedback

def circuit(x,kind):
    q=QuantumCircuit(8,4)
    for i in range(4):
        if x>>i&1:
            q.x(i)
    q.barrier()
    for i in range(3):
        q.cx(i,5+i)
    q.cx(3,4)
    if kind=="ring":
        q.x(4)
    elif kind=="linear":
        q.cx(0,4)
    else:
        q.ccx(0,1,4)
    q.measure(range(4,8),range(4))
    return q

def periods(mapping):
    cycles=set()
    for x in range(16):
        path=[]
        while x not in path:
            path.append(x)
            x=mapping[x]
        cycle=path[path.index(x):]
        cycles.add(tuple(cycle[cycle.index(min(cycle)):]+cycle[:cycle.index(min(cycle))]))
    return sorted(map(len,cycles))

def main():
    service=QiskitRuntimeService(channel="ibm_quantum_platform",token=getpass("Key: "),instance=getpass("Instance: "))
    backend=service.least_busy(operational=True,simulator=False,min_num_qubits=8)
    for kind in ("ring","linear","nonlinear"):
        circuits=transpile([circuit(x,kind) for x in range(16)],backend,optimization_level=1,num_processes=1,seed_transpiler=42)
        job=SamplerV2(mode=backend).run(circuits,shots=256)
        counts=[r.data.c.get_counts() for r in job.result()]
        modal=[int(max(h,key=h.get),2) for h in counts]
        expected=[classical(x,kind) for x in range(16)]
        report=dict(job=job.job_id(),backend=backend.name,counts=counts,observed=modal,expected=expected,periods=periods(modal),expected_periods=periods(expected),correct=sum(a==b for a,b in zip(modal,expected)))
        Path(f"research_sources/feedback-{kind}-{job.job_id()}.json").write_text(json.dumps(report,indent=2))
        print(kind,report["correct"],report["periods"],job.job_id(),flush=True)

if __name__=="__main__":
    main()
