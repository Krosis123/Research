import ast
import json
import random
from pathlib import Path
from getpass import getpass
from qiskit_ibm_runtime import QiskitRuntimeService
from network300 import run

source=Path("research_sources/erbb004.bnet")
lines=source.read_text().strip().splitlines()
matches=[p.name for p in (Path.home()/"Downloads").glob("*.bnet") if p.read_text(encoding="utf-8-sig").strip().splitlines()==lines]
rows={}
for line in lines[1:]:
    if not line.strip(): continue
    n,e=line.split(",",1)
    tree=ast.parse(e.strip().replace("!","~"),mode="eval")
    assert all(isinstance(x,(ast.Expression,ast.BinOp,ast.BitAnd,ast.BitOr,ast.UnaryOp,ast.Invert,ast.Name,ast.Load,ast.Constant)) for x in ast.walk(tree))
    regs=sorted({x.id for x in ast.walk(tree) if isinstance(x,ast.Name)})
    rows[n.strip()]=regs,compile(tree,"<rule>","eval")
genes=sorted(set(rows).union(*(r for r,c in rows.values())))
rng=random.Random(4004)
state={n:rng.randrange(2) for n in genes}
rules={}
reference={}
for n in genes:
    if n not in rows:
        rules[n]=[[n],[0,1]]
        reference[n]=state[n]
        continue
    regs,code=rows[n]
    reference[n]=eval(code,{"__builtins__":{}},state)&1
    keep=regs[:2]
    table=[eval(code,{"__builtins__":{}},state|{v:(mask>>i)&1 for i,v in enumerate(keep)})&1 for mask in range(1<<len(keep))]
    assert table[sum(state[v]<<i for i,v in enumerate(keep))]==reference[n]
    rules[n]=[keep,table]
print(matches,len(genes),len(rows),sum(len(set(t))>1 for ns,t in rules.values()),flush=True)
Path("research_sources/erbb004-reference.json").write_text(json.dumps(reference))
service=QiskitRuntimeService(channel="ibm_quantum_platform",token=getpass("Key: "),instance=getpass("Instance: "))
run(service.least_busy(operational=True,simulator=False,min_num_qubits=20),dict(state=state,rules=rules))
