"""Import synchronous BooleanNet (.bnet) equations and search bounded trajectories."""
from pathlib import Path
import re
import numpy as np
from .expressions import ExpressionRule
from .model import Network

IDENTIFIER = r"[A-Za-z_]\w*"


def load_bnet(path):
    equations = {}
    symbols = set()
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.partition("#")[0].strip()
        if not line or line.replace(" ", "").lower() == "targets,factors":
            continue
        target, comma, rule = line.partition(",")
        target = target.strip()
        if not comma or not re.fullmatch(IDENTIFIER, target) or target in equations:
            raise ValueError(f"Invalid or duplicate .bnet target on line {line_no}")
        equations[target] = rule.strip()
        symbols.update(re.findall(IDENTIFIER, rule))
    external = sorted(symbols - equations.keys())
    names = list(equations) + external
    rules = [ExpressionRule(equations[n], names) for n in equations] + [None]*len(external)
    return Network(names, rules=rules, name=Path(path).stem, metadata={"external_inputs": external})


def bounded_basins(net, budget=65536, period=6, transient=6, seed=42,
                   progress=lambda fraction, message: None, cancel=None):
    """Enumerate small state spaces, otherwise sample uniformly with replacement."""
    if min(budget, period) < 1 or transient < 0:
        raise ValueError("Invalid search limits")
    free = [i for i,n in enumerate(net.names) if n not in net.clamped]
    space = 1 << len(free)
    exact = space <= budget
    total = min(space, budget)
    rng = np.random.default_rng(seed)
    basins = {}
    missed = 0
    for offset in range(0,total,512):
        if cancel is not None and cancel():
            raise InterruptedError("Search cancelled")
        count = min(512,total-offset)
        start = np.zeros((count,net.n),dtype=np.uint8)
        if exact:
            indexes = np.arange(offset,offset+count,dtype=np.int64)
            for bit,i in enumerate(free):
                start[:,i] = (indexes >> bit) & 1
        else:
            start[:,free] = rng.integers(2,size=(count,len(free)),dtype=np.uint8)
        for n,value in net.clamped.items():
            start[:,net.index(n)] = value
        path = [start]
        for _ in range(transient+period):
            path.append(net.step(path[-1]))
        packed = [np.packbits(s,axis=1) for s in path]
        active = np.ones(count,dtype=bool)
        for t in range(transient+1):
            for p in range(1,period+1):
                found = np.flatnonzero(active & np.all(packed[t]==packed[t+p],axis=1))
                for j in found:
                    cycle = [s[j].tobytes() for s in packed[t:t+p]]
                    pos = cycle.index(min(cycle))
                    key = tuple(cycle[pos:]+cycle[:pos])
                    hist = basins.setdefault(key,[0]*(transient+1))
                    hist[t] += 1
                active[found] = False
        missed += int(active.sum())
        progress((offset+count)/total,f"Checked {offset+count} of {total} starts")
    return dict(names=net.names,clamps=net.clamped,seed=seed,period_limit=period,
                transient_limit=transient,exhaustive=exact,starts=total,unresolved=missed,
                state_encoding="hex, node order MSB first, zero-padded on right",
                basins=[dict(cycle=[s.hex() for s in k],period=len(k),by_transient=v,
                             starts=sum(v)) for k,v in basins.items()])
