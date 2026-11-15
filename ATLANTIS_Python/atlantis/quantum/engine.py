"""Preflight and auditable, bounded quantum discovery entry point."""
from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from time import perf_counter
import numpy as np
from ..io import network_to_dict
from ..analysis import CancelledError
from .adapter import QuantumNetwork
from .ross.adaptive import discover


@dataclass(frozen=True)
class Settings:
    T: int = 3
    engine: str = 'reduced'
    counting_mode: str = 'exact'
    shots: int = 256
    counting_precision: int = 3
    counting_shots: int = 128
    seed: int = 42
    max_rounds: int = 12
    stop_policy: str = 'classical_audit'
    max_qubits: int = 22
    max_reference_states: int = 65536
    max_memory_mib: int = 1024
    max_compiled_depth: int = 200000
    max_compiled_gates: int = 500000
    max_verification_steps: int = 10000
    timeout_seconds: int = 120
    noise_probability: float = 0.0


def preflight(network, settings):
    s=settings
    errors=[]
    for key,lo,hi in [('T',1,10000),('shots',1,100000),('counting_shots',1,100000),
                      ('counting_precision',1,10),('max_rounds',1,1000),('timeout_seconds',1,3600),
                      ('max_verification_steps',1,1000000),('max_qubits',1,1000),
                      ('max_memory_mib',1,1048576),('max_reference_states',1,1048576)]:
        value=getattr(s,key)
        if type(value) is not int or not lo<=value<=hi: errors.append(f'{key} must be integer in [{lo},{hi}]')
    if errors: return {'eligible':False,'reasons':errors}
    if s.engine not in ('reduced','aer','aer_mps','ibm'): errors.append('Unsupported engine')
    if s.counting_mode not in ('exact','qpe_ideal','qpe_aer'): errors.append('Unsupported counting mode')
    if s.stop_policy not in ('qpe','classical_audit','bounded'): errors.append('Unsupported stop policy')
    if s.counting_mode=='qpe_aer' and s.engine=='reduced': errors.append('Actual counting requires Aer')
    if s.counting_mode=='qpe_ideal' and s.engine!='reduced': errors.append('Ideal QPE is reference-only')
    if not 0<=s.noise_probability<=.2: errors.append('Noise probability outside [0,.2]')
    if s.noise_probability and s.engine=='reduced': errors.append('Gate noise requires actual Aer circuits')
    q=network.n*(s.T+1)+(s.counting_precision if s.counting_mode=='qpe_aer' else 0)
    memory=16*(1<<q) # integer avoids overflow for large models
    if s.engine!='reduced' and q>s.max_qubits: errors.append(f'{q} circuit qubits exceed budget {s.max_qubits}')
    if s.engine=='aer' and memory*3>s.max_memory_mib*1024**2:
        errors.append(f'Statevector plus 3x working allowance exceeds {s.max_memory_mib} MiB')
    enumerates=s.engine=='reduced' or s.counting_mode in ('exact','qpe_ideal') or s.stop_policy=='classical_audit'
    if enumerates and (1<<network.n)>s.max_reference_states:
        errors.append(f'Classical reference/count/audit needs 2^{network.n} states; budget {s.max_reference_states}')
    # Reject before symbolic/table synthesis.
    terms=None
    if not errors:
        try:
            adapted=QuantumNetwork(network)
            terms=sum(len(r.anf_terms) for r in adapted.rules)
            if terms*s.T*((1<<s.counting_precision) if s.counting_mode=='qpe_aer' else 1)>s.max_compiled_gates:
                errors.append('Evolution/counting synthesis lower bound exceeds gate budget')
        except ValueError as e: errors.append(str(e))
    return {'eligible':not errors,'reasons':errors,'logical_evolution_qubits':network.n*(s.T+1),
            'logical_counting_qubits':s.counting_precision if s.counting_mode=='qpe_aer' else 0,
            'circuit_qubits':q,'statevector_bytes_lower_bound':memory,'anf_terms':terms,
            'transpiled_depth':None,'transpiled_width':None,
            'note':'MPS memory is entanglement-dependent. Transpiled limits checked before execution; worker deadline enforced.'}


def run(network, settings=Settings(), progress=None, cancel=None, circuit_executor=None):
    started=perf_counter()
    assessment=preflight(network,settings)
    if not assessment['eligible']: raise ValueError('; '.join(assessment['reasons']))
    s=settings
    if s.engine=='ibm' and circuit_executor is None: raise ValueError('Hardware requires an authenticated, confirmed executor')
    net=QuantumNetwork(network)
    preprocessing_runtime_s = perf_counter() - started
    def checkpoint():
        if cancel and cancel(): raise CancelledError('Cancelled')
        if perf_counter()-started>s.timeout_seconds: raise TimeoutError('Quantum deadline exceeded')
    result=discover(net,T=s.T,engine=s.engine,counting_mode=s.counting_mode,
        shots=s.shots,counting_precision=s.counting_precision,counting_shots=s.counting_shots,
        rng=np.random.default_rng(s.seed),seed=s.seed,max_rounds=s.max_rounds,
        stop_policy=s.stop_policy,checkpoint=checkpoint,progress=progress,
        max_verification_steps=s.max_verification_steps,
        circuit_executor=circuit_executor,
        execution_options={'max_depth':s.max_compiled_depth,'max_gates':s.max_compiled_gates,
                           'max_memory_mb':s.max_memory_mib,'noise_probability':s.noise_probability})
    d=asdict(result)
    d['cycles']=[[net.as_bits(x) for x in cycle] for cycle in sorted(result.cycles)]
    d.update(schema_version=1,network=network_to_dict(network),
             network_hash=sha256(json.dumps(network_to_dict(network),sort_keys=True).encode()).hexdigest(),
             parameters=asdict(s),resources=assessment,T_selection='user supplied',
             taxonomy=('physical QPU result' if s.engine=='ibm' else 'ideal mathematical quantum reference' if s.engine=='reduced' else
                       'noisy quantum circuit simulation' if s.noise_probability else 'actual quantum circuit simulation'),
             basin_sizes=None,basin_size_origin='unavailable; counting history estimates combined excluded coverage',
             classical_information=('enumerated F^T for exact M' if s.counting_mode=='exact' else
                                    'enumerated F^T for ideal QPE' if s.counting_mode=='qpe_ideal' else 'candidate trajectories only; optional audit separately labeled'),
             preprocessing_runtime_s=preprocessing_runtime_s,
             total_runtime_s=perf_counter()-started)
    return d
