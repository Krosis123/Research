"""Check one-step dynamics of the supplied ATLANTIS biological case studies."""
from pathlib import Path
import json
import os
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from atlantis.io import load_weighted, load_rules, load_states
from atlantis.quantum.adapter import QuantumNetwork


def cases():
    for case in range(1, 5):
        p = ROOT / f'examples/Case Study {case}/Input Files'
        if case < 3:
            paths = [p/'NetworkFile.csv'] if case == 1 else sorted((p/'Network files').rglob('*.csv'))
            for path in paths:
                yield case, path.stem, load_weighted(path), None
        else:
            d = p/'Network Details'
            net = load_rules(d/'Node List.txt', d/'Boolean logic for nodes', allow_missing=True)
            yield case, f'case{case}', net, load_states(p/'Network State Lists/Simulation 1.mat', net.n)[:64]


def main(hardware):
    from qiskit import QuantumCircuit
    from atlantis.quantum.ross.circuits import append_rule
    from atlantis.quantum.ibm import IBMAccount
    rows = []
    circuits = []
    rng = np.random.default_rng(20261116)
    for case, name, net, states in cases():
        q = QuantumNetwork(net)
        if states is None:
            states = np.unpackbits(np.arange(q.size, dtype='>u2').view('u1').reshape(-1, 2), axis=1)[:, -net.n:]
        else:
            states = np.vstack([states, rng.integers(2, size=(64, net.n), dtype=np.uint8)])
        expected = net.step(states)
        encode = lambda row: int.from_bytes(np.packbits(row).tobytes(), 'big') >> (-len(row) % 8)
        for x, y in zip(states, expected):
            if q.step(encode(x)) != encode(y):
                raise AssertionError(f'{name}: transition mismatch at {encode(x)}')
        i = next(i for i,r in enumerate(q.rules) if 2 <= len(r.inputs) <= 4 and any(t.bit_count()>1 for t in r.anf_terms) and expected[:,i].min()!=expected[:,i].max())
        rule = q.rules[i]
        k = len(rule.inputs)
        qc = QuantumCircuit(2*(k+1), 2)
        for bit in (0, 1):
            state = states[np.flatnonzero(expected[:,i]==bit)[0]]
            offset = bit*(k+1)
            wires = list(range(offset, offset+k))
            for wire, src in zip(wires, rule.inputs):
                if state[src]: qc.x(wire)
            append_rule(qc, rule, wires, offset+k)
            qc.measure(offset+k, bit)
        circuits.append(qc)
        rows.append(dict(case=case, model=name, nodes=net.n, verified_transitions=len(states),
                         assumed_identity=net.metadata.get('assumed_identity_rules', []), probe=net.names[i],
                         expected_register='10'))
    out = ROOT/'validation'/('paper-hardware.json' if hardware else 'paper-transitions.json')
    def save():
        out.write_text(json.dumps(rows, indent=2)+'\n')
    save()
    if hardware:
        account = IBMAccount()
        account.connect(os.environ['ATLANTIS_IBM_KEY'], os.environ['ATLANTIS_IBM_CRN'])
        backend = account.service().least_busy(operational=True, simulator=False).name
        for row, qc in zip(rows, circuits):
            prepared = account.prepare(qc, backend, shots=256)
            row.update(backend=backend, job=account.submit(prepared, confirmed=True), shots=256)
            save()
        for row in rows:
            row['counts'] = account.result(row['job'])
            save()
    print(out)


if __name__ == '__main__':
    main('--hardware' in sys.argv)
