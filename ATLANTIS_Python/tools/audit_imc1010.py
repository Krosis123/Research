"""Classical fixed-context audit of MEWpy's iMC1010 table; numeric external signals
are clamped to zero except pH=7. This diagnostic omits flux feedback."""
import ast
import csv
import hashlib
import json
import random
import re
from pathlib import Path
from scipy.stats import beta

root = Path(__file__).resolve().parents[2]
source = root/"research_sources/iMC1010.csv"
rows = list(csv.DictReader(source.open(encoding="utf-8-sig")))
ids = [r["Alias_3"] for r in rows]
assert len(set(ids)) == len(ids) and all(re.fullmatch(r"b\d{4}", k) for k in ids)
external = set()
codes = []
for row in rows:
    expr = re.sub(r"[A-Za-z_]\w*(?:-[A-Za-z_]\w*)*", lambda m:m[0].replace("-","_"),row["Rule"])
    for a,b in [("NOT","not"),("OR","or"),("AND","and"),("TRUE","True"),("FALSE","False")]:
        expr = re.sub(r"\b"+a+r"\b",b,expr)
    expr = re.sub(r"\b(\d+[A-Za-z_]\w*)", r"signal_\1", expr)
    tree = ast.parse(expr,mode="eval")
    for node in ast.walk(tree):
        assert isinstance(node,(ast.Expression,ast.BoolOp,ast.And,ast.Or,ast.UnaryOp,ast.Not,ast.Compare,ast.Lt,ast.Gt,ast.Name,ast.Load,ast.Constant)),type(node)
        if isinstance(node,ast.Name) and node.id not in ids:
            assert not re.fullmatch(r"b\d{4}",node.id)
            external.add(node.id)
    codes.append(compile(tree,"<model>","eval"))
env = dict.fromkeys(external,0)
if "pH" in env: env["pH"]=7
markers = ["b0002","b0019"]  # thrA and nhaA, illustrative expression markers
indices = [ids.index(m) for m in markers]
def trace(rng):
    state = bytes(rng.randrange(2) for _ in ids)
    return trace_state(state)

def trace_state(state):
    if len(state) != len(ids) or any(bit > 1 for bit in state):
        raise ValueError('Expected one binary value per locus')
    seen, path = {}, []
    for _ in range(65):
        if state in seen:
            cycle = path[seen[state]:]
            return tuple(tuple(sorted({s[j] for s in cycle})) for j in indices)
        seen[state]=len(path)
        path.append(state)
        context = env | dict(zip(ids,state))
        state = bytes(bool(eval(c,{"__builtins__":{}},context)) for c in codes)
    return None
if __name__ == '__main__':
    discovery=random.Random(810)
    known={trace(discovery) for _ in range(8)}-{None}
    audit=random.Random(811)
    misses=sum(trace(audit) not in known for _ in range(64))
    upper=float(beta.ppf(.95,misses+1,64-misses)) if misses<64 else 1.
    result=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),distinct_loci=len(ids),
                nonconstant_rules=sum(r["Rule"]!="TRUE" for r in rows),context=env,
                markers=markers,known=sorted(known),misses=misses,upper95=upper,stop=upper<=.05)
    (root/"research_sources/imc1010-stopping-result.json").write_text(json.dumps(result,indent=2))
    print({k:v for k,v in result.items() if k!="context"})
    
