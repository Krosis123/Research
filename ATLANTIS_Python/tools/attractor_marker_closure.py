"""Sound fixed-context subcube propagation. Each local image is computed exhaustively."""
import itertools
import json
from audit_imc1010 import ids,codes,env,markers,root

def closure():
    fixed = {}
    output = []
    while True:
        added = {}
        for gene,code in zip(ids,codes):
            if gene in fixed:
                continue
            unknown = sorted(set(code.co_names)-env.keys()-fixed.keys())
            ctx = env | fixed
            values = set()
            for bits in itertools.product((0,1),repeat=len(unknown)):
                ctx.update(zip(unknown,bits))
                values.add(int(bool(eval(code,{"__builtins__":{}},ctx))))
                if len(values)==2:
                    break
            if len(values)==1:
                added[gene]=values.pop()
        if not added:
            return fixed,output
        fixed.update(added)
        output.append(added)

if __name__=='__main__':
    fixed,layers=closure()
    result=dict(loci=len(ids),layers=layers, unresolved=sorted(set(ids)-fixed.keys()),
                marker_constants={g:fixed.get(g) for g in markers})
    (root/'research_sources/imc1010-closure.json').write_text(json.dumps(result,indent=2))
    print(len(fixed),[len(a) for a in layers],result['marker_constants'])
