"""Iterate IBM majority outputs until a full state repeats or the budget expires."""
import json
from pathlib import Path
from getpass import getpass
from qiskit_ibm_runtime import QiskitRuntimeService
from network300 import run
from gene_block_update import condition_rules

def trajectory(backend, model, max_steps=12):
    state=model["state"]
    rules=model["rules"]
    genes=list(rules)
    history=[tuple(state[n] for n in genes)]
    records=[]
    for step in range(max_steps):
        reference={n:t[sum(state[g]<<i for i,g in enumerate(ns))] for n,(ns,t) in rules.items()}
        result=run(backend,dict(state=state,rules=condition_rules(rules,state)))
        counts=result["counts"]
        ones=[sum(v for s,v in counts[i//6].items() if s[-1-i%6]=="1") for i in range(len(genes))]
        if 128 in ones:
            raise RuntimeError("Ambiguous majority; see raw counts "+result["job"])
        next_state=tuple(int(k>128) for k in ones)
        errors=sum(next_state[i]!=reference[n] for i,n in enumerate(genes))
        records.append(dict(job=result["job"],errors=errors))
        report=dict(genes=genes,history=history+[next_state],records=records)
        if next_state in history:
            first=history.index(next_state)
            report.update(transient=first,period=len(history)-first)
        Path("research_sources/imc300-hardware-trajectory.json").write_text(json.dumps(report))
        if "period" in report:
            print("Repeat",first,report["period"],records,flush=True)
            break
        history.append(next_state)
        state=dict(zip(genes,next_state))

if __name__=="__main__":
    model=json.loads(Path("research_sources/network300-dc1jgimq4uuc73a410ng.json").read_text())["model"]
    service=QiskitRuntimeService(channel="ibm_quantum_platform",token=getpass("Key: "),instance=getpass("Instance: "))
    trajectory(service.least_busy(operational=True,simulator=False,min_num_qubits=20),model)
