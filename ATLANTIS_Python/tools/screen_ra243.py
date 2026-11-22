"""Fixed-context full-cycle witness screen. Markers are exploratory."""
import ast,json,random
from pathlib import Path
root=Path(__file__).resolve().parents[2]/"research_sources"
rules=dict(line.split(", ",1) for line in (root/"ra243-model.bnet").read_text().splitlines()[1:] if line)
expr={n:ast.parse(e.replace("!"," not ").replace("&"," and ").replace("|"," or ").strip(),mode="eval") for n,e in rules.items()}
assert all(isinstance(x,(ast.Expression,ast.Name,ast.Load,ast.BoolOp,ast.UnaryOp,ast.And,ast.Or,ast.Not,ast.Constant)) for e in expr.values() for x in ast.walk(e))
refs={x.id for e in expr.values() for x in ast.walk(e) if isinstance(x,ast.Name)}
names=list(rules)
codes=[compile(expr[n],"<rule>","eval") for n in names]
rng=random.Random(43)
env={n:rng.randrange(2) for n in sorted(refs-set(names))}
witnesses=[]
for sample in range(32):
    state=bytes(rng.randrange(2) for n in names)
    initial=state.hex()
    seen={}
    for t in range(257):
        if state in seen:
            cycle=list(seen)[seen[state]:]
            witnesses.append(dict(initial=initial,cycle=[v.hex() for v in cycle]))
            break
        seen[state]=t
        ctx=env|dict(zip(names,state))
        state=bytes(bool(eval(c,{"__builtins__":{}},ctx)) for c in codes)
mapped=json.loads((root/"ra243-label-audit.json").read_text())
varied={}
for i,n in enumerate(names):
    if n[2:] not in mapped:continue
    signatures=[''.join(map(str,sorted({bytes.fromhex(s)[i] for s in w['cycle']}))) for w in witnesses]
    if len(set(signatures))>1:varied[n]={s:signatures.count(s) for s in sorted(set(signatures))}
result=dict(external=env,order=names,witnesses=witnesses,attempts=32,marker_counts=varied)
(root/'ra243-witnesses.json').write_text(json.dumps(result))
print(len(names),len(env),len(witnesses),len(varied),list(varied.items())[:4])
