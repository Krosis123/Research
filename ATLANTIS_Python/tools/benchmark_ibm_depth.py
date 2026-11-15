"""Compile comparison on the same IBM snapshot using the shipped 0.2.4 baseline."""
import argparse
import json
import sys
from pathlib import Path
from types import ModuleType
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime.fake_provider import FakeBrisbane
from atlantis.io import load_network
from atlantis.quantum.adapter import QuantumNetwork
from atlantis.quantum.ross import circuits
import numpy as np
from atlantis.model import decimal_to_binary, binary_to_decimal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=ROOT.parent / 'dist/ATLANTIS_Quantum_0.2.4_source.zip')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    baseline = ModuleType('atlantis.quantum.ross.baseline')
    baseline.__package__ = circuits.__package__
    with ZipFile(args.baseline) as archive:
        exec(compile(archive.read('ATLANTIS_Quantum/atlantis/quantum/ross/circuits.py'),
                     'release-0.2.4/circuits.py', 'exec'), baseline.__dict__)
    backend = FakeBrisbane()
    results = []
    for filename, horizon in [('giacomantonio5.json', 4), ('fpga-case4-subset15.csv', 3)]:
        model = load_network(ROOT / 'examples/quantum' / filename)
        net = QuantumNetwork(model)
        states = decimal_to_binary(np.arange(net.size), net.n)
        for _ in range(horizon):
            states = model.step(states)
        counts = np.bincount(binary_to_decimal(states).astype(int), minlength=net.size)
        marked = int(counts.argmax())
        m = int(counts[marked])
        for stage in ['forward', 'suppression', 'counting', 'counting_p3']:
            for label, builder in [('release', baseline), ('optimized', circuits)]:
                if stage == 'counting_p3' and label == 'release':
                    continue
                if stage.startswith('counting'):
                    circuit = builder.counting_circuit(net, horizon, [net.as_bits(marked)], 3 if stage == 'counting_p3' else 1)
                else:
                    exclusions = [] if stage == 'forward' else [net.as_bits(marked)]
                    circuit, _ = builder.search_circuit(net, horizon, exclusions, m)
                pm = generate_preset_pass_manager(optimization_level=1, backend=backend, seed_transpiler=42)
                compiled = pm.run(circuit)
                row = dict(network=filename, horizon=horizon, stage=stage, compiler=label,
                           marked_state=net.as_bits(marked), marked_inputs=m, logical_qubits=circuit.num_qubits,
                           depth=compiled.depth(), two_qubit_gates=sum(len(op.qubits)==2 for op in compiled.data))
                results.append(row)
                print(row, flush=True)
                args.output.write_text(json.dumps(results, indent=2)+'\n')


if __name__ == '__main__':
    main()
