"""Immutable Boolean-network specifications and independently checkable truth graphs.

This is a classical *validation* component, not the quantum algorithm.
States are integers; their bitstrings are gene-order g00...g(n-1) (MSB first).
"""
from __future__ import annotations
import ast
from dataclasses import dataclass
from typing import Dict


def _parse_expression(expr: str, names: tuple[str, ...]):
    tree = ast.parse(expr, mode='eval')
    dependencies = set()

    def compute(node, values):
        if isinstance(node, ast.Expression):
            return compute(node.body, values)
        if isinstance(node, ast.Name) and node.id in names:
            dependencies.add(node.id)
            return values[node.id]
        if isinstance(node, ast.Constant) and node.value in (0, 1):
            return int(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Invert):
            return 1 ^ compute(node.operand, values)
        if isinstance(node, ast.BinOp) and type(node.op) in (ast.BitAnd, ast.BitOr, ast.BitXor):
            a = compute(node.left, values)
            b = compute(node.right, values)
            return (a & b) if isinstance(node.op, ast.BitAnd) else ((a | b) if isinstance(node.op, ast.BitOr) else (a ^ b))
        raise ValueError(f'Unsafe or unsupported Boolean rule: {expr!r}, expression node {type(node).__name__}')

    # Validate AST and collect dependencies without executing arbitrary code.
    compute(tree, dict.fromkeys(names, 0))
    deps = tuple(name for name in names if name in dependencies)
    if len(deps) > 6:
        raise ValueError('Max six input genes per rule (reversible synthesis grows exponentially in fan-in)')
    lookup = []
    for mask in range(1 << len(deps)):
        values = {name: (mask >> j) & 1 for j, name in enumerate(deps)}
        lookup.append(compute(tree, values))
    anf = lookup.copy()
    for bit in range(len(deps)):
        for mask in range(1 << len(deps)):
            if mask & (1 << bit):
                anf[mask] ^= anf[mask ^ (1 << bit)]
    return deps, tuple(lookup), tuple(m for m,v in enumerate(anf) if v)


@dataclass(frozen=True)
class Rule:
    expression: str
    inputs: tuple[int, ...]
    values: tuple[int, ...]
    anf_terms: tuple[int, ...]


@dataclass(frozen=True)
class Network:
    name: str
    genes: tuple[str, ...]
    rules: tuple[Rule, ...]

    @classmethod
    def create(cls, name: str, rules: dict[str, str]):
        genes = tuple(rules)
        if not 1 <= len(genes) <= 30:
            raise ValueError('Networks must have 1..30 genes')
        compiled = []
        for expr in rules.values():
            deps, values, anf = _parse_expression(expr, genes)
            compiled.append(Rule(expr, tuple(genes.index(d) for d in deps), values, anf))
        return cls(name, genes, tuple(compiled))

    @property
    def n(self): return len(self.genes)

    @property
    def size(self): return 1 << self.n

    def as_bits(self, x: int): return format(x, f'0{self.n}b')

    def step(self, x: int) -> int:
        output = 0
        for rule in self.rules:
            mask = 0
            for j, idx in enumerate(rule.inputs):
                mask |= ((x >> (self.n - 1 - idx)) & 1) << j
            output = (output << 1) | rule.values[mask]
        return output


def make_network(n: int, family: str) -> Network:
    """Controlled synthetic networks; NOT validated biological regulatory networks."""
    if family == 'rossini4':
        if n != 4: raise ValueError('rossini4 must have n=4')
        return Network.create('rossini4', {
            'A': 'A & D', 'B': 'A & B', 'C': 'C & D', 'D': 'B | C'})
    if n < 3: raise ValueError('Synthetic families require n>=3')
    genes = tuple(f'g{i:02d}' for i in range(n))
    rules: Dict[str,str] = {}
    a,b,c=genes[:3]
    if family == 'projection':
        patterns = [f'{a} & {b}', f'{a} | {c}', f'{b} ^ {c}',
                    f'~{a}', f'{a} & ~{c}', f'{a} ^ {b}', f'{b} | {c}']
        for i,g in enumerate(genes):
            rules[g] = g if i<3 else patterns[(i-3) % len(patterns)]
    elif family == 'skewed':
        p=f'({a} & {b})'
        for i,g in enumerate(genes):
            rules[g] = p if (i<2 or i%2==0) else f'~{p}'
    elif family == 'cycle2':
        patterns = [a,b,f'{a} & {b}',f'{a} | {b}',f'{a} ^ {b}',f'~{a}',f'~{b}']
        for i,g in enumerate(genes):
            rules[g] = (b if i==0 else a) if i<2 else patterns[(i-2)%len(patterns)]
    elif family == 'long_chain':
        for i,g in enumerate(genes):
            rules[g] = genes[i-1] if i else g
    else:
        raise ValueError(f'Unknown family: {family}')
    return Network.create(f'{family}_{n}', rules)


@dataclass
class Truth:
    successors: list[int]
    attractors: tuple[tuple[int, ...], ...]
    cycle_of: list[tuple[int, ...]]
    basin_sizes: dict[tuple[int, ...], int]
    max_transient: int
    max_cycle: int
    transient_lengths: list[int]


def exact_truth(net: Network, max_states: int = 1 << 18) -> Truth:
    """Exhaustive ground truth, O(2^n) states, never a quantum speedup claim."""
    N=net.size
    if N > max_states: raise ValueError(f'exact ground truth refused for {N:,} states')
    successors = [net.step(x) for x in range(N)]
    cycle_of = [None] * N
    transient = [0] * N
    for start in range(N):
        if cycle_of[start] is not None: continue
        path=[]
        index={}
        curr=start
        while curr not in index and cycle_of[curr] is None:
            index[curr]=len(path)
            path.append(curr)
            curr=successors[curr]
        if curr in index:
            cut=index[curr]
            raw = path[cut:]
            k=raw.index(min(raw))
            cyc=tuple(raw[k:]+raw[:k])
            for node in raw:
                cycle_of[node]=cyc
                transient[node]=0
            path=path[:cut]
        for node in reversed(path):
            nxt=successors[node]
            cycle_of[node]=cycle_of[nxt]
            transient[node]=transient[nxt]+1
    counts={}
    for c in cycle_of:
        counts[c]=counts.get(c,0)+1
    return Truth(successors, tuple(sorted(counts)), cycle_of, counts,
                 max(transient), max(len(c) for c in counts), transient)


def verify_candidate(net: Network, candidate: int, max_steps=10000):
    """Trace JUST ONE observed state (hybrid verification, no whole-graph oracle).

    Return (is_on_attractor, canonical_cycle). An output is rejected if it is
    transient, even if its trajectory eventually enters a genuine attractor.
    """
    seen={}
    path=[]
    curr=candidate
    while curr not in seen:
        if len(path)>=max_steps: return False,()
        seen[curr]=len(path)
        path.append(curr)
        curr=net.step(curr)
    raw=path[seen[curr]:]
    k=raw.index(min(raw))
    cycle=tuple(raw[k:]+raw[:k])
    return (candidate in cycle),cycle
