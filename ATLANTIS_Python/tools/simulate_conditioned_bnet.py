"""Compile a restricted initial-state ensemble into a reversible terminal-state circuit.
Run from any directory with the project's Qiskit environment. Input syntax is BNet.
"""
import argparse
import ast
import hashlib
import json
import random
import re
from pathlib import Path
from time import perf_counter

import qiskit
import qiskit_aer
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

DATA = Path(__file__).resolve().parents[1] / "validation" / "large_dynamics"


def run(path, steps, k, seed):
    lines = path.read_text().splitlines()
    rules = {}
    for line in lines:
        if not line.strip() or line.startswith(("#", "targets,")):
            continue
        name, expr = map(str.strip, line.split(",", 1))
        if name in rules or not name.isidentifier():
            raise ValueError(name)
        if not re.fullmatch(r"[\w\s!&|()01]+", expr):
            raise ValueError(expr)
        rules[name] = expr
    trees = {name: ast.parse(expr.replace("!", "~"), mode="eval").body
             for name, expr in rules.items()}
    allowed = (ast.Name, ast.Load, ast.BinOp, ast.BitAnd, ast.BitOr,
               ast.UnaryOp, ast.Invert, ast.Constant)
    for tree in trees.values():
        if any(not isinstance(n, allowed) for n in ast.walk(tree)):
            raise ValueError("Unsupported BNet expression")
    refs = {n.id for tree in trees.values() for n in ast.walk(tree) if isinstance(n, ast.Name)}
    inputs = sorted((refs - rules.keys()) | {n for n,e in rules.items() if n == e})
    names = sorted(refs | rules.keys())
    if not 1 <= k <= min(8, len(inputs)) or steps < 1:
        raise ValueError("Choose 1–8 available inputs and a positive horizon")
    free = random.Random(seed).sample(inputs, k)
    rng = random.Random(seed)
    initial = {n: rng.randrange(2) for n in names}
    branches = 1 << k
    from conditioned_circuit import compile_dynamics
    start = perf_counter()
    qc, decode = compile_dynamics(trees, initial, free, steps)
    qc.measure_all()
    simulator = AerSimulator(method="matrix_product_state")
    circuit = transpile(qc, basis_gates=["cx","u"], optimization_level=1, seed_transpiler=seed)
    compile_s = perf_counter() - start
    counts = simulator.run(circuit, shots=32*branches, seed_simulator=seed).result().get_counts()
    # Independent scalar interpreter using Python Boolean operators on single states.
    scalar = {n: compile(e.replace("!", " not ").replace("&"," and ").replace("|"," or ").strip(),
                         "<bnet>", "eval") for n,e in rules.items()}
    seen = set()
    for key in counts:
        value = int(key, 2)
        branch = value % branches
        seen.add(branch)
        state = initial.copy()
        state.update({n: (branch >> j) & 1 for j,n in enumerate(free)})
        for _ in range(steps):
            state.update({n: int(eval(code, {"__builtins__": {}}, state)) for n,code in scalar.items()})
        if any(decode(n,value) != state[n] for n in names):
            raise AssertionError(key)
    if len(seen) != branches:
        raise AssertionError("Incomplete branch coverage")
    return dict(model_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), variables=len(names),
                rules=len(rules), inputs=inputs, free=free, steps=steps, seed=seed, qubits=qc.num_qubits,
                depth=circuit.depth(), cx=circuit.count_ops().get("cx",0),
                compile_seconds=compile_s, total_seconds=perf_counter()-start, counts=counts,
                decoded_nodes_checked_per_branch=len(names), verified_branches=len(seen),
                qiskit=qiskit.__version__, aer=qiskit_aer.__version__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DATA/"model.bnet")
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument("--free-inputs", type=int, default=4)
    parser.add_argument("--seed", type=int, default=37)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(run(args.model,args.steps,args.free_inputs,args.seed), indent=2)
    if args.output:
        args.output.write_text(result)
    else:
        print(result)
