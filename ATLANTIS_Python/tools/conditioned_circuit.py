"""Compile synchronous BNet updates symbolically under specified initial conditions.

Signals are signed integer references. +/-1 are constants. AND gates are
interned, OR uses De Morgan, and negation requires only flipping the sign.
Only gates reachable from terminal outputs are emitted.
"""
import ast
from qiskit import QuantumCircuit


def compile_dynamics(trees, initial, free, steps, *, semantic=False, relative_phase=False):
    gates = {}
    nodes = {}
    signals = {name: 1 if bit else -1 for name, bit in initial.items()}
    for i, name in enumerate(free, 2):
        signals[name] = i

    # A signature is the value of a signal on every permitted input branch.
    # Complemented signatures share one wire. The bound caps classical work.
    signatures = {}
    representatives = {}
    if semantic:
        if len(free) > 12:
            raise ValueError("Signature compilation supports at most 12 free bits")
        branches = 1 << len(free)
        mask = (1 << branches) - 1
        signatures[1] = mask
        for j in range(len(free)):
            signatures[j+2] = sum(((b >> j) & 1) << b for b in range(branches))
        for ref, signature in signatures.items():
            representatives[signature] = ref
            representatives[mask ^ signature] = -ref

    def signature(ref):
        return signatures[abs(ref)] ^ (mask if ref < 0 else 0)

    def conjunction(a, b):
        if -1 in (a,b) or a == -b:
            return -1
        if a == 1 or a == b:
            return b
        if b == 1:
            return a
        pair = tuple(sorted((a,b)))
        if pair not in gates:
            if semantic:
                table = signature(a) & signature(b)
                if table in representatives:
                    return representatives[table]
            index = len(free) + 2 + len(gates)
            gates[pair] = index
            nodes[index] = pair
            if semantic:
                signatures[index] = table
                representatives[table] = index
                representatives[mask ^ table] = -index
        return gates[pair]

    def signal(tree):
        if isinstance(tree, ast.Name):
            return signals[tree.id]
        if isinstance(tree, ast.Constant):
            return 1 if tree.value else -1
        if isinstance(tree, ast.UnaryOp):
            return -signal(tree.operand)
        a, b = signal(tree.left), signal(tree.right)
        if isinstance(tree.op, ast.BitAnd):
            return conjunction(a,b)
        return -conjunction(-a,-b)

    for _ in range(steps):
        signals.update({name: signal(tree) for name,tree in trees.items()})
    active = {abs(s) for s in signals.values()}
    for index in reversed(nodes):
        if index in active:
            active.update(abs(s) for s in nodes[index])
    live = sorted(active.intersection(nodes))
    qc = QuantumCircuit(len(free) + len(live))
    wires = {i+2:i for i in range(len(free))}
    qc.h(range(len(free)))
    for i,index in enumerate(live,len(free)):
        a,b = nodes[index]
        neg = [wires[-s] for s in (a,b) if s < 0]
        for wire in neg:
            qc.x(wire)
        (qc.rccx if relative_phase else qc.ccx)(wires[abs(a)],wires[abs(b)],i)
        for wire in neg:
            qc.x(wire)
        wires[index] = i
    def decode(name, value):
        s = signals[name]
        bit = 1 if abs(s)==1 else (value >> wires[abs(s)]) & 1
        return bit ^ (s < 0)
    return qc, decode
