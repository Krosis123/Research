"""Fixed-anchor paired-flip proposal on all MCF7 conditions, with exact uniform truth."""
import json,random,sys,time
from getpass import getpass
from pathlib import Path
import numpy as np
from qiskit import transpile
from qiskit_ibm_runtime import QiskitRuntimeService,SamplerV2
from quantum_markov_audit import mask_circuit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from atlantis.io import load_weighted,load_mutations
from atlantis.model import binary_to_decimal
from atlantis.states import all_states

def main():
    root=Path(__file__).resolve().parents[2]
    base=root/'ATLANTIS_Python/examples/Case Study 2/Input Files'
    service=QiskitRuntimeService(channel="ibm_quantum_platform",token=getpass("Key: "),instance=getpass("Instance: "))
    backend=service.least_busy(operational=True,simulator=False,min_num_qubits=16)
    shots=8192
    start=time.perf_counter()
    qc=mask_circuit(16,True)
    qc.measure_all()
    job=SamplerV2(mode=backend).run([transpile(qc,backend,seed_transpiler=42)],shots=shots)
    words=job.result()[0].data.meas.get_bitstrings()
    hardware_seconds=time.perf_counter()-start
    anchor=np.array([x&1 for x in random.Random(17).randbytes(16)])
    bits=np.arange(16)
    hardware=binary_to_decimal(((np.array([int(w,2) for w in words])[:,None]>>bits)&1)^anchor)
    rng=np.random.default_rng(42)
    start=time.perf_counter()
    classical=binary_to_decimal(np.repeat(rng.random((shots,8))<.25,2,axis=1)^anchor)
    classical_seconds=time.perf_counter()-start
    patterns=((np.arange(256)[:,None]>>np.arange(8))&1)
    support=binary_to_decimal(np.repeat(patterns,2,axis=1)^anchor)
    weights=.25**patterns.sum(axis=1)*.75**(8-patterns.sum(axis=1))
    uniform=rng.integers(65536,size=shots)
    report=dict(job=job.job_id(),backend=backend.name,hardware_seconds=hardware_seconds,classical_seconds=classical_seconds,shots=shots,anchor=anchor.tolist(),outside_support=int((~np.isin(hardware,support)).sum()),conditions=[])
    for env,file in [('off','DNA Damge OFF/Control_MCF7 (0).csv'),('on','DNA Damge ON/Etoposide.csv')]:
        base_net=load_weighted(base/'Network files'/file)
        for treatment in ['Control','Nutlin','Wip1 KD','Nutlin + Wip KD']:
            net=base_net.mutate(load_mutations(base/'Mutation Files'/f'{treatment}.txt'))
            nxt=binary_to_decimal(net.step(all_states(16)))
            assert np.array_equal(binary_to_decimal(all_states(16)),np.arange(65536))
            labels=np.full(65536,-1)
            for x in range(65536):
                path={}
                while labels[x]<0 and x not in path:
                    path[x]=len(path)
                    x=nxt[x]
                label=labels[x] if labels[x]>=0 else min(list(path)[path[x]:])
                if path: labels[list(path)]=label
            sizes=np.bincount(labels)
            rare=sizes[labels]<=655.36
            row=dict(environment=env,treatment=treatment,rare_basins=int(sum((sizes>0)&(sizes<=655))),uniform_probability=float(rare.mean()),paired_probability=float(weights@rare[support]))
            for name,draw in [('ibm',hardware),('matched',classical),('uniform',uniform)]:
                hits=rare[draw].reshape(-1,64)
                row[name]=dict(hits=int(hits.sum()),successful_batches=int(hits.any(axis=1).sum()))
            report['conditions'].append(row)
    dest=root/'research_sources/mcf7-paired-ibm.json'
    dest.write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
if __name__=='__main__':main()
