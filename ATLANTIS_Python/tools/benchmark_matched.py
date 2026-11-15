"""Small matched benchmark and audit of historical memory rejections."""
import json
from pathlib import Path
import sys
from time import perf_counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atlantis.analysis import deterministic_analysis
from atlantis.expressions import from_expressions
from atlantis.quantum.engine import Settings, preflight, run
from atlantis.quantum.ross.adaptive import terminal_states
from atlantis.quantum.adapter import QuantumNetwork
from atlantis.io import load_network
from atlantis.states import all_states


def main():
    root = Path('validation')
    five = load_network('examples/quantum/giacomantonio5.json')
    rejected = [row for row in map(json.loads, (root/'benchmark-current/raw.jsonl').read_text().splitlines())
                if row['status'] == 'failed']
    assessment = preflight(five, Settings(engine='aer', T=4, max_qubits=26))
    assert len(rejected) == 20 and all('Statevector' in row['error'] for row in rejected)
    assert not assessment['eligible']
    (root/'memory-rejection-audit.json').write_text(json.dumps(dict(
        attempts=len(rejected), amplitude_bytes=16*2**25, guarded_bytes=3*16*2**25,
        budget_bytes=2**30, assessment=assessment), indent=2))

    rows = []
    for width in (2, 3, 4):
        network = from_expressions({'x0':'x0', **{f'x{i}':'x0' for i in range(1,width)}})
        for seed in range(3):
            for protocol in ('classical','reference','aer','qpe','noisy','mps'):
                start = perf_counter()
                row = dict(nodes=width, protocol=protocol, seed=seed, shots=128, T=1)
                if protocol == 'classical':
                    result = deterministic_analysis(network, all_states(width), 10)
                    cycles = {tuple(''.join(map(str,s)) for s in a.states) for a in result.attractors}
                    row['status'] = 'exact'
                else:
                    result = run(network, Settings(T=1, seed=seed, shots=128, counting_shots=128,
                        engine={'reference':'reduced','mps':'aer_mps'}.get(protocol,'aer'),
                        counting_mode='qpe_aer' if protocol=='qpe' else 'exact',
                        stop_policy='qpe' if protocol=='qpe' else 'classical_audit',
                        counting_precision=3, noise_probability=.002 if protocol=='noisy' else 0))
                    cycles = {tuple(c) for c in result['cycles']}
                    row.update({k:result[k] for k in ('status','preprocessing_runtime_s','search_runtime_s',
                        'counting_runtime_s','verification_runtime_s','classical_audit_runtime_s',
                        'compiled_depth_max','compiled_2q_count_max')})
                    circuits = [event['resources'] for event in result['history'] if event['kind']=='circuit_execution']
                    row.update(qubits=result['resources']['circuit_qubits'],
                               transpilation_s=sum(c['transpilation_s'] for c in circuits),
                               aer_execution_s=sum(c['execution_s'] for c in circuits))
                row['wall_s'] = perf_counter()-start
                row['process_rss_bytes'] = psutil.Process().memory_info().rss
                row['success'] = cycles == {('0'*width,), ('1'*width,)}
                if protocol=='qpe':
                    adapted = QuantumNetwork(network)
                    terminal = terminal_states(adapted,1)
                    discovered = set()
                    errors = []
                    for event in result['history']:
                        if event['kind']=='new_cycle':
                            discovered.update(int(s,2) for s in event['cycle'])
                        if 'M_est' in event:
                            errors.append(abs(event['M_est']-sum(s in discovered for s in terminal)))
                    row['count_absolute_errors'] = errors
                rows.append(row)
    (root/'matched-scaling.json').write_text(json.dumps(rows,indent=2))
    for protocol in sorted({row['protocol'] for row in rows}):
        plt.plot((2,3,4),[np.median([r['wall_s'] for r in rows if r['nodes']==n and r['protocol']==protocol])
                           for n in (2,3,4)], marker='o', label=protocol)
    plt.yscale('log')
    plt.xlabel('Boolean network nodes')
    plt.ylabel('Median wall time (seconds)')
    plt.legend()
    plt.tight_layout()
    plt.savefig(root/'matched-scaling.png', dpi=180)


if __name__ == '__main__':
    main()
