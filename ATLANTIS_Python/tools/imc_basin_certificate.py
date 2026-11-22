"""Certify a fixed point and its entire basin when constant propagation determines every node."""
import hashlib
import json
from pathlib import Path
import time

def certify(rules):
    known={}
    waves=[]
    while True:
        fixed={}
        for node,(parents,table) in rules.items():
            if node in known:
                continue
            compatible=[v for k,v in enumerate(table) if all(
                parent not in known or known[parent]==(k>>i)&1 for i,parent in enumerate(parents))]
            if not compatible:
                raise ValueError(f"Empty truth table for {node}")
            if len(set(compatible))==1:
                fixed[node]=int(compatible[0])
        if not fixed:
            break
        waves.append(fixed)
        known.update(fixed)
    if len(known)==len(rules):
        for node,(parents,table) in rules.items():
            if known[node]!=table[sum(known[p]<<i for i,p in enumerate(parents))]:
                raise AssertionError("Fixed point replay failed")
    return dict(determined=len(known),nodes=len(rules),settling_upper=len(waves) if len(known)==len(rules) else None,
                waves=waves,complete=len(known)==len(rules))

if __name__=="__main__":
    base=Path(__file__).resolve().parents[2]
    source=base/"ATLANTIS_Python/research/models/imc500.json"
    model=json.loads(source.read_text())
    result={}
    for n in [300,500]:
        genes=list(model["rules"])[:n]
        rules={g:model["rules"][g] for g in genes}
        assert all(set(parents)<=rules.keys() for parents,_ in rules.values())
        start=time.perf_counter()
        report=certify(rules)
        report["seconds"]=time.perf_counter()-start
        result[n]=report
        print(n,report["determined"],report["settling_upper"])
    result["source_sha256"]=hashlib.sha256(source.read_bytes()).hexdigest()
    (base/"ATLANTIS_Python/research/results/imc-basin-certificate.json").write_text(json.dumps(result))
