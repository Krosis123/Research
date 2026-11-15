"""Run the three-step Case 4 forward-sampling experiment."""
import argparse
from getpass import getpass
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from atlantis.io import load_network
from atlantis.quantum.adapter import QuantumNetwork
from atlantis.quantum.ibm import IBMAccount
from atlantis.quantum.ross.circuits import search_circuit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ibm', action='store_true', help='connect to a physical IBM backend')
    args = parser.parse_args()
    model = load_network(ROOT / 'examples/quantum/fpga-case4-subset15.csv')
    circuit, _ = search_circuit(QuantumNetwork(model), 3, [], 0)
    if not args.ibm:
        from qiskit_ibm_runtime.fake_provider import FakeBrisbane
        from qiskit.transpiler import generate_preset_pass_manager
        compiled = generate_preset_pass_manager(optimization_level=1, backend=FakeBrisbane(),
                                                seed_transpiler=42).run(circuit)
        print(f'Offline FakeBrisbane preview: {circuit.num_qubits} logical qubits, depth {compiled.depth()}, '
              f'{sum(len(op.qubits)==2 for op in compiled.data)} two-qubit gates.')
        return
    account = IBMAccount()
    account.connect(getpass('IBM Quantum Platform API key: '), input('IBM instance CRN: ').strip())
    choices = [b['name'] for b in account.backends() if b['qubits'] >= circuit.num_qubits]
    if not choices:
        raise SystemExit('No operational backend with enough qubits is available on this instance.')
    print('Available backends:', ', '.join(choices))
    name = input('Backend name: ').strip()
    if name not in choices:
        raise SystemExit('Choose one of the listed backend names.')
    prepared = account.prepare(circuit, name, shots=1024)
    print(json.dumps(prepared[2], indent=2))
    if input('Submit one potentially paid 1024-shot job? Type RUN: ').strip() != 'RUN':
        return
    job_id = account.submit(prepared, confirmed=True, max_seconds=60)
    print(f'IBM job ID: {job_id}', flush=True)
    counts = account.result(job_id)
    output = Path.cwd() / f'case4-forward-{job_id}.json'
    output.write_text(json.dumps(dict(job_id=job_id, settings=prepared[2], genes=model.names,
                                     time_steps=3, counts=counts), indent=2))
    print(f'Measurements saved to {output}')


if __name__ == '__main__':
    main()
