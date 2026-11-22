"""SAT enumeration of primitive synchronous cycles and implicit bounded basins."""
import ast
import time
import numpy as np
from .expressions import ExpressionRule

def symbolic_cycles(net, limit=64, seconds=20, cancel=None):
    import z3
    net.require_resolved_rules()
    if net.rules is None:
        raise ValueError("Symbolic search requires a Boolean rule network")
    def expression(node, state):
        if isinstance(node,ast.Name):
            return state[int(node.id[6:])]
        if isinstance(node,ast.Constant):
            return z3.BoolVal(bool(node.value))
        if isinstance(node,ast.UnaryOp):
            return z3.Not(expression(node.operand,state))
        a,b=expression(node.left,state),expression(node.right,state)
        if isinstance(node.op,ast.BitAnd): return z3.And(a,b)
        if isinstance(node.op,ast.BitOr): return z3.Or(a,b)
        return z3.Xor(a,b)
    results=[]
    for p in range(1,7):
        solver=z3.Solver()
        states=[[z3.Bool(f"s{t}_{i}") for i in range(net.n)] for t in range(p)]
        for t,s in enumerate(states):
            nxt=states[(t+1)%p]
            for i,(n,r) in enumerate(zip(net.names,net.rules)):
                if n in net.clamped: value=bool(net.clamped[n])
                elif r is None: value=s[i]
                elif isinstance(r,ExpressionRule): value=expression(r.tree,s)
                else:
                    terms=[z3.And(*[s[j] if (k>>(len(r.sources)-1-bit))&1 else z3.Not(s[j]) for bit,j in enumerate(r.sources)]) for k,y in enumerate(r.outputs) if y]
                    value=z3.Or(*terms)
                solver.add(nxt[i]==value)
            if t:
                solver.add(z3.Or(*[a!=b for a,b in zip(states[0],s)]))
        cycles=[]
        deadline=time.monotonic()+seconds
        status="limit"
        while len(cycles)<limit and time.monotonic()<deadline:
            if cancel is not None and cancel(): raise InterruptedError("Cancelled")
            solver.set(timeout=max(1,int(1000*(deadline-time.monotonic()))))
            check=solver.check()
            if check!=z3.sat:
                status="complete" if check==z3.unsat else "timeout_or_unknown"
                break
            m=solver.model()
            trajectory=np.array([[z3.is_true(m.eval(v,model_completion=True)) for v in s] for s in states],dtype=np.uint8)
            assert np.array_equal(net.step(trajectory),np.roll(trajectory,-1,axis=0))
            cycles.append([np.packbits(row).tobytes().hex() for row in trajectory])
            for row in trajectory:
                solver.add(z3.Or(*[v!=bool(bit) for v,bit in zip(states[0],row)]))
        results.append(dict(period=p,status=status,cycles=cycles))
    return results
def classify_bounded_starts(net, starts, periods, transient=6):
    """Return (period-index, cycle-index, entry time) or None for each start."""
    lookup = {}
    for group in periods:
        for i,cycle in enumerate(group["cycles"]):
            for state in cycle:
                lookup[bytes.fromhex(state)] = (group["period"],i)
    current = np.asarray(starts,dtype=np.uint8).copy()
    for name,value in net.clamped.items():
        current[:,net.index(name)] = value
    results = [None]*len(current)
    for t in range(transient+1):
        for j,row in enumerate(np.packbits(current,axis=1)):
            cycle = lookup.get(row.tobytes())
            if results[j] is None and cycle is not None:
                results[j] = (*cycle,t)
        if t<transient:
            current=net.step(current)
    return results
