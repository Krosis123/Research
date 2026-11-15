"""Offline one-circuit IBM experiment estimate from a fake-backend snapshot."""
import json
from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qiskit_ibm_runtime.fake_provider import FakeBrisbane
from atlantis.io import load_network
from atlantis.quantum.adapter import QuantumNetwork
from atlantis.quantum.ibm import IBMAccount
from atlantis.quantum.ross.circuits import search_circuit


def main():
    backend=FakeBrisbane()
    account=IBMAccount()
    account.connect('local-placeholder','local-placeholder',
                    lambda **_:SimpleNamespace(backend=lambda name:backend))
    model=QuantumNetwork(load_network('examples/quantum/rossini4.json'))
    circuit,_=search_circuit(model,3,[],0)
    _,compiled,summary=account.prepare(circuit,backend.name,shots=128)
    duration=compiled.estimate_duration(backend.target)
    delay=backend.default_rep_delay
    summary.update(status='offline estimate only',experiment='unsuppressed Rossini4 terminal sampling',
                   compiled_two_qubit_gates=sum(len(item.qubits)==2 for item in compiled.data),
                   active_qubits=len({q for item in compiled.data for q in item.qubits}),
                   circuit_duration_s=duration,repetition_delay_s=delay,
                   shot_duration_subtotal_s=128*(duration+delay),proposed_usage_cap_s=60,
                   expected_terminal_probabilities={'0000':11/16,'0011':2/16,
                     '1011':1/16,'1101':1/16,'1111':1/16})
    Path('validation/ibm-offline-estimate-023.json').write_text(json.dumps(summary,indent=2))
    print(summary)


if __name__=='__main__':
    main()
