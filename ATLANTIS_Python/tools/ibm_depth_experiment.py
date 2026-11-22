"""Depth comparison and optional IBM submission for terminal Z-basis sampling."""
import argparse
import ast
import hashlib
import json
from collections import Counter
import random
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime.fake_provider import FakeFez
from conditioned_circuit import compile_dynamics

DATA = Path(__file__).resolve().parents[1] / "validation" / "large_dynamics"


def verify_routed(native, expected):
    """Remove idle hardware wires; independently recover measured probabilities."""
    touched = sorted({native.find_bit(q).index for inst in native.data
                      if inst.operation.name != "barrier" for q in inst.qubits})
    if len(touched) > 24:
        raise ValueError("Routed verification exceeds statevector budget")
    compact = QuantumCircuit(len(touched))
    readout = {}
    for inst in native.data:
        if inst.operation.name == "barrier":
            continue
        wires = [touched.index(native.find_bit(q).index) for q in inst.qubits]
        if inst.operation.name == "measure":
            readout[native.find_bit(inst.clbits[0]).index] = wires[0]
        else:
            compact.append(inst.operation,wires)
    probs = Statevector.from_instruction(compact).probabilities()
    dist = {}
    for index in map(int,np.flatnonzero(probs > 1e-14)):
        word = sum(((index >> q) & 1) << c for c,q in readout.items())
        dist[word] = dist.get(word,0.) + float(probs[index])
    ideal = {v:1/len(expected) for v in expected.values()}
    tv = .5 * sum(abs(dist.get(x,0.) - ideal.get(x,0.)) for x in dist.keys() | ideal.keys())
    if tv > 1e-10:
        raise AssertionError(f"Routed readout distribution mismatch: {tv}")
    return tv


def experiment(backend, seed, free_count, steps):
    raw = (DATA / "model.bnet").read_bytes()
    rules = dict(line.split(", ", 1) for line in raw.decode().splitlines()[1:] if line)
    trees = {n: ast.parse(e.replace("!", "~"), mode="eval").body for n,e in rules.items()}
    inputs = sorted({v.id for t in trees.values() for v in ast.walk(t)
                     if isinstance(v, ast.Name)} - rules.keys())
    names = sorted(set(inputs) | rules.keys())
    free = random.Random(seed).sample(inputs, free_count)
    rng = random.Random(seed)
    initial = {n:rng.randrange(2) for n in names}
    scalar = {n:compile(e.replace("!", " not ").replace("&"," and ").replace("|"," or ").strip(),
                        "<model>", "eval") for n,e in rules.items()}
    truth = []
    for branch in range(1 << free_count):
        state = initial.copy()
        state.update({n:(branch >> j) & 1 for j,n in enumerate(free)})
        for _ in range(steps):
            state.update({n:int(eval(c, {"__builtins__":{}}, state)) for n,c in scalar.items()})
        truth.append(state)

    rows = []
    best = None
    for semantic,relative in [(False,False),(False,True),(True,False),(True,True)]:
        qc, decode = compile_dynamics(trees, initial, free, steps, semantic=semantic, relative_phase=relative)
        if qc.num_qubits > 22:
            raise ValueError("Exact statevector verification exceeds 22-wire budget")
        probs = Statevector.from_instruction(qc).probabilities()
        support = np.flatnonzero(probs > 1e-12)
        expected = {}
        for word in map(int,support):
            b = word % len(truth)
            if b in expected or any(decode(n,word) != truth[b][n] for n in names):
                raise AssertionError("Decoded state mismatch")
            expected[b] = word
        if len(expected)!=len(truth) or not np.allclose(probs[support],1/len(truth),atol=1e-12,rtol=0):
            raise AssertionError("Distribution mismatch")
        qc.measure_all()
        for route in (4,19,37):
            native = transpile(qc, backend=backend, optimization_level=3, seed_transpiler=route)
            depth = native.depth(lambda inst: inst.operation.num_qubits==2)
            cost = (depth,native.depth())
            rows.append(dict(semantic=semantic,relative_phase=relative,route=route,
                             logical_width=qc.num_qubits,two_qubit_depth=depth,depth=native.depth(),
                             two_qubit_gates=sum(i.operation.num_qubits==2 for i in native.data)))
            if best is None or cost < best[0]:
                best = (cost,native,expected.copy(),rows[-1])
    routed_tv = verify_routed(best[1],best[2])
    return best,dict(routed_ideal_tv=routed_tv,backend=backend.name,sha256=hashlib.sha256(raw).hexdigest(),seed=seed,
                     steps=steps,free=free,states_verified=len(truth),nodes_checked=len(names),rows=rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hardware",action="store_true")
    parser.add_argument("--seed",type=int,default=4)
    parser.add_argument("--inputs",type=int,default=6,choices=range(1,9))
    parser.add_argument("--steps",type=int,default=10)
    args = parser.parse_args()
    service = QiskitRuntimeService() if args.hardware else None
    backend = service.least_busy(operational=True,simulator=False,min_num_qubits=16) if service else FakeFez()
    best,report = experiment(backend,args.seed,args.inputs,args.steps)
    _,native,expected,winner = best
    report.update(hardware=args.hardware,winner=winner,expected_words=expected)
    dest = DATA / f"depth-{backend.name}-{args.seed}-{args.inputs}-{args.steps}.json"
    if args.hardware and dest.exists():
        raise SystemExit("Existing live run record; check existing job before resubmission")
    dest.write_text(json.dumps(report,indent=2))
    if args.hardware:
        from qiskit_ibm_runtime.executor_sampler import Sampler
        job=Sampler(mode=backend,options={"max_execution_time":60}).run([native],shots=2048)
        report["job_id"]=job.job_id()
        dest.write_text(json.dumps(report,indent=2))
        counts=job.result()[0].join_data().get_counts()
        shots = sum(counts.values())
        branches = len(expected)
        inputs_seen = Counter()
        correct = 0
        for bits, number in counts.items():
            word = int(bits, 2)
            branch = word % branches
            inputs_seen[branch] += number
            if expected[branch] == word:
                correct += number
        # Exact ideal distribution on the complete measured logical word.
        measured = {int(bits,2):n/shots for bits,n in counts.items()}
        ideal = {w:1/branches for w in expected.values()}
        tv = .5*sum(abs(measured.get(w,0.)-ideal.get(w,0.)) for w in ideal.keys()|measured.keys())
        report.update(counts=counts, valid_word_shots=correct, shots=shots,
                      branch_count=len(inputs_seen), hardware_tv_from_ideal=tv)
        dest.write_text(json.dumps(report,indent=2))
    print(dest,winner)
