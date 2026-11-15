"""Adaptive Rossini attractor discovery, without ground-truth control-flow leakage.

This is an experimental HYBRID algorithm. The transition map and measured
candidate trajectories may be evaluated classically. No complete transition
graph / known K / precomputed transient bound controls the search.

Two distinct termination claims are supported:
 - 'qpe': repeated QPE estimates of full excluded-basin coverage are a
   HEURISTIC only, subject to false-positive termination from finite precision.
 - 'classical_audit': explicitly check every initial state reaches a discovered
   cycle within T; this is an EXACT classical completeness certificate with
   O(2**n * T) work. It does not show quantum advantage.

The number of evolution steps T is supplied by the CALLER. A small T may
result in an inconclusive run, even if all attractors are present.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from time import perf_counter
import numpy as np

from .model import Network, verify_candidate
from .reference import (hadamard_inplace, suppression_parameters,
                        qpe_estimate, measure_ideal)


@dataclass
class DiscoveryResult:
    cycles: set[tuple[int, ...]] = field(default_factory=set)
    status: str = 'inconclusive'
    completion_reason: str = ''
    search_attempts: int = 0
    counting_calls: int = 0
    rejected_measurements: int = 0
    total_measurements: int = 0
    invalid_measurements: int = 0
    compiled_depth_max: int = 0
    compiled_size_max: int = 0
    compiled_2q_count_max: int = 0
    oracle_calls_ideal: int = 0
    search_runtime_s: float = 0.0
    counting_runtime_s: float = 0.0
    simulation_runtime_s: float = 0.0
    verification_runtime_s: float = 0.0
    max_suppressed_leakage: float | None = None
    classical_audit_runtime_s: float = 0.0
    classical_audit_states_scanned: int = 0
    history: list[dict] = field(default_factory=list)


def terminal_states(net: Network, T: int) -> list[int]:
    """Classical O(N*T) surrogate for reduced-state validation/auditing only."""
    return [evolve_one(net, x, T) for x in range(net.size)]


def evolve_one(net: Network, x: int, T: int) -> int:
    for _ in range(T):
        x = net.step(x)
    return x


def covered_count(terminal: list[int], excluded: set[tuple[int,...]]) -> int:
    states = {s for cycle in excluded for s in cycle}
    return sum(x in states for x in terminal)


def reduced_probabilities(net: Network, terminal: list[int],
                          excluded: set[tuple[int,...]], M: int):
    """Independent n-qubit ideal surrogate; not an Aer circuit execution."""
    N=net.size
    marked_states={v for c in excluded for v in c}
    marked=np.fromiter((s in marked_states for s in terminal),dtype=bool,count=N)
    amps=np.full(N,1/sqrt(N),dtype=np.complex128)
    params=None
    if excluded:
        params=suppression_parameters(M,N)
        for _ in range(params.J):
            amps[marked]*=np.exp(-1j*params.phi)
            hadamard_inplace(amps)
            amps[0]*=np.exp(1j*params.phi)
            hadamard_inplace(amps)
    probabilities=np.bincount(terminal,weights=np.abs(amps)**2,minlength=N)
    probabilities/=probabilities.sum()
    leakage=float(np.abs(amps[marked])@np.abs(amps[marked])) if excluded else 0.0
    return probabilities,params,leakage


def determine_candidates(net: Network, counts: dict[int,int],
                         excluded: set[tuple[int,...]], max_steps=10000):
    """Use only each measured state and the network rules, never exact_truth."""
    accepted=[]
    invalid=0
    rejected=0
    for state,num in counts.items():
        is_cycle,cycle=verify_candidate(net,state,max_steps=max_steps)
        if not is_cycle:
            invalid+=num
            rejected+=num
        elif cycle in excluded:
            rejected+=num
        else:
            accepted.append((cycle,num))
    return accepted,invalid,rejected


def choose_candidate(accepted, rng):
    weights=np.array([ct for _,ct in accepted],dtype=float)
    weights/=weights.sum()
    return accepted[int(rng.choice(len(accepted),p=weights))][0]


def qpe_full_coverage_evidence(counts, size, precision, alpha, min_fraction):
    """Conservative ideal-shot test against every count M < size."""
    from scipy.stats import binom

    bins = 1 << precision
    central = f'{bins//2:0{precision}b}'
    hits = sum(value for key,value in counts.items() if key.replace(' ','') == central)
    shots = sum(counts.values())
    # At phase 1/2, the squared Dirichlet kernel is at most
    # 1 / (bins**2 * (1-M/size)) for either conjugate eigenphase.
    null_bound = min(1., size/(bins*bins))
    tail = float(binom.sf(hits-1,shots,null_bound)) if shots else 1.
    return dict(central_hits=hits,shots=shots,null_bound=null_bound,tail_bound=tail,alpha=alpha,
                passes=bool(shots and hits/shots>=min_fraction and tail<=alpha))


def discover(net: Network, *, T: int, engine: str, counting_mode: str,
             shots: int, counting_precision: int, counting_shots: int,
             rng: np.random.Generator, seed: int,
             max_rounds: int=24, search_retries: int=2,
             stop_policy: str='qpe', stop_confirmations: int=2,
             min_full_fraction: float=0.95, readout_flip: float=0.0,
             checkpoint=lambda:None, progress=None, max_verification_steps=10000,
             execution_options=None, circuit_executor=None) -> DiscoveryResult:
    if T<1: raise ValueError('Adaptive mode needs a user-specified --evolution-steps >= 1')
    if shots<1 or counting_shots<1: raise ValueError('Shots must be positive')
    if max_rounds<1 or search_retries<1 or stop_confirmations<1:
        raise ValueError('Round, retry and confirmation budgets must be >= 1')
    if not 0.5<=min_full_fraction<=1.0:
        raise ValueError('min_full_fraction must be between 0.5 and 1.0')
    if stop_policy not in ('qpe','classical_audit','bounded'):
        raise ValueError('Unknown stopping policy')
    if counting_mode=='qpe_aer' and engine=='reduced':
        raise ValueError('qpe_aer needs actual Aer engine')
    if engine!='reduced' and counting_mode=='qpe_ideal':
        raise ValueError('qpe_ideal is a reduced-engine reference only')

    out=DiscoveryResult()
    def execute_circuit(qc,shots,**options):
        from .circuits import qiskit_counts
        checkpoint()
        counts,info=(circuit_executor or qiskit_counts)(qc,shots,**options)
        out.history.append({'kind':'circuit_execution','resources':info})
        checkpoint()
        return counts,info
    cached_terminal=None
    def terminal():
        nonlocal cached_terminal
        if cached_terminal is None:
            cached_terminal=terminal_states(net,T)
        return cached_terminal

    def add_resources(info):
        out.compiled_depth_max=max(out.compiled_depth_max,info['compiled_depth'])
        out.compiled_size_max=max(out.compiled_size_max,info['compiled_size'])
        out.compiled_2q_count_max=max(out.compiled_2q_count_max,info['compiled_2q_count'])

    def count_once(index):
        """Return estimated marked count, and fraction of shots implying full coverage."""
        t=perf_counter()
        phase_counts=None
        if counting_mode=='exact':
            estimate=covered_count(terminal(),out.cycles)
            histogram={estimate:counting_shots}  # LABEL: classical enumeration, not QPE
        elif counting_mode=='qpe_ideal':
            true_count=covered_count(terminal(),out.cycles)
            estimate,histogram,phase_counts=qpe_estimate(
                true_count,net.size,counting_precision,counting_shots,rng,return_phase_counts=True)
        elif counting_mode=='qpe_aer':
            from .circuits import counting_circuit,qiskit_counts,qpe_counts_to_M
            excluded_bits=[net.as_bits(s) for cyc in sorted(out.cycles) for s in cyc]
            qc=counting_circuit(net,T,excluded_bits,counting_precision)
            counts,info=execute_circuit(qc,counting_shots,
                         method='matrix_product_state' if engine=='aer_mps' else 'statevector',
                         seed=seed+100_003*index, **(execution_options or {}))
            estimate,histogram=qpe_counts_to_M(counts,net.size,counting_precision)
            phase_counts=counts
            out.history.append({'kind':'qpe_measurements', 'call':index,
                                'marked_terminal_states':excluded_bits,
                                'phase_counts':dict(counts), 'M_histogram':histogram})
            add_resources(info)
            out.oracle_calls_ideal+=(1<<counting_precision)-1
        else: raise ValueError('Unsupported counting mode '+counting_mode)
        out.counting_calls+=1
        out.counting_runtime_s+=perf_counter()-t
        supported=False
        if phase_counts is not None and stop_policy=='qpe':
            evidence=qpe_full_coverage_evidence(
                phase_counts,net.size,counting_precision,
                .01/((max_rounds+1)*stop_confirmations),min_full_fraction)
            evidence['ideal_shot_model_applicable']=(engine!='ibm' and not
                (execution_options or {}).get('noise_probability',0))
            supported=evidence['passes'] and evidence['ideal_shot_model_applicable']
            out.history.append({'kind':'qpe_coverage_evidence','call':index,**evidence})
        return estimate,histogram.get(net.size,0)/max(1,sum(histogram.values())),supported

    for round_index in range(max_rounds):
        checkpoint()
        if progress: progress(round_index/max_rounds,f'Quantum search round {round_index+1}')
        # A newly verified first cycle has NO suppression yet, so count is
        # only meaningful after at least one round.
        m=0
        if out.cycles:
            if stop_policy=='classical_audit':
                audit_start=perf_counter()
                # Exact certificate: F^T(x) lies in one of the discovered cycles
                # for ALL 2**n initial states. This intentionally costs O(2**n*T).
                covered=covered_count(terminal(),out.cycles)
                out.classical_audit_runtime_s+=perf_counter()-audit_start
                out.classical_audit_states_scanned+=net.size
                if covered==net.size:
                    out.status='complete_classically_certified'
                    out.completion_reason='Exhaustive F^T coverage audit; classical O(2^n*T), not a quantum certificate'
                    return out
            m,full_fraction,supported=count_once(out.counting_calls+1)
            out.history.append({'round':round_index,'kind':'count','M_est':m,
                                'full_fraction':full_fraction,
                                'cycles_found_before':len(out.cycles)})
            if stop_policy=='qpe' and counting_mode=='exact' and m==net.size:
                out.status='complete_classically_certified'
                out.completion_reason='Exhaustive classical terminal counting established full coverage'
                return out
            if stop_policy=='qpe' and m==net.size and supported:
                confirmed=True
                for _ in range(stop_confirmations-1):
                    m2,f2,supported2=count_once(out.counting_calls+1)
                    out.history.append({'round':round_index,'kind':'stop_confirmation',
                                        'M_est':m2,'full_fraction':f2})
                    if m2!=net.size or not supported2:
                        confirmed=False
                        break
                if confirmed:
                    out.status='complete_qpe_heuristic'
                    out.completion_reason='Repeated phase counts passed the ideal-model coverage test; heuristic, not certified'
                    return out
                # conflicting estimates; safer to leave inconclusive than
                # continue with a nonphysical parameter M=N.
                out.status='inconclusive_conflicting_stop_estimates'
                out.completion_reason='QPE estimates disagreed about completeness'
                return out
            if not 0<m<net.size:
                if m==net.size and stop_policy=='qpe':
                    out.status='inconclusive_coverage_evidence'
                    out.completion_reason='Full-count estimate lacks sufficient ideal-model coverage evidence'
                else:
                    out.status='inconclusive_counting'
                    out.completion_reason=f'Counting returned M={m} (N={net.size}); suppression parameters undefined'
                return out

        for retry_index in range(search_retries):
            checkpoint()
            t=perf_counter()
            if engine=='reduced':
                probabilities,params,leakage=reduced_probabilities(net,terminal(),out.cycles,m)
                out.search_runtime_s+=perf_counter()-t
                out.max_suppressed_leakage=max(out.max_suppressed_leakage or 0,leakage)
                t=perf_counter()
                counts=measure_ideal(probabilities,shots,net.n,rng,readout_flip)
                out.simulation_runtime_s+=perf_counter()-t
            else:
                from .circuits import search_circuit,qiskit_counts
                excluded_bits=[net.as_bits(s) for c in sorted(out.cycles) for s in c]
                qc,params=search_circuit(net,T,excluded_bits,m)
                out.search_runtime_s+=perf_counter()-t
                t=perf_counter()
                counts_bits,info=execute_circuit(qc,shots,
                                method='matrix_product_state' if engine=='aer_mps' else 'statevector',
                                seed=seed+17*round_index+retry_index, **(execution_options or {}))
                out.simulation_runtime_s+=perf_counter()-t
                counts={int(bits.replace(' ',''),2):int(ct) for bits,ct in counts_bits.items()}
                add_resources(info)
            out.oracle_calls_ideal+=(params.J*2+1 if params else 1)
            out.search_attempts+=1
            out.total_measurements+=sum(counts.values())
            out.history.append({'round':round_index,'kind':'measurements',
                                'counts':{net.as_bits(k):int(v) for k,v in counts.items()}})
            checkpoint()
            verification_started = perf_counter()
            accepted,invalid,rejected=determine_candidates(net,counts,out.cycles,max_verification_steps)
            out.verification_runtime_s += perf_counter() - verification_started
            out.invalid_measurements+=invalid
            out.rejected_measurements+=rejected
            if accepted:
                picked=choose_candidate(accepted,rng)
                out.cycles.add(picked)
                out.history.append({'round':round_index,'kind':'new_cycle',
                                    'cycle':[net.as_bits(s) for s in picked],
                                    'retry':retry_index,'rejected_measurements':rejected})
                break
        else:
            out.status='inconclusive_no_new_candidate'
            out.completion_reason=f'No verified unseen attractor after {search_retries} search attempts'
            return out

    # A last discovery on the round budget must still get a chance to prove
    # termination; the budget limits SEARCH attempts, not the final check.
    if out.cycles:
        if stop_policy=='classical_audit':
            audit_start=perf_counter()
            covered=covered_count(terminal(),out.cycles)
            out.classical_audit_runtime_s+=perf_counter()-audit_start
            out.classical_audit_states_scanned+=net.size
            if covered==net.size:
                out.status='complete_classically_certified'
                out.completion_reason='Exact full-coverage classical audit at round budget'
                return out
        elif stop_policy=='qpe' and counting_mode=='exact':
            if covered_count(terminal(),out.cycles)==net.size:
                out.status='complete_classically_certified'
                out.completion_reason='Exhaustive classical terminal counting established full coverage at round budget'
                return out
        elif stop_policy=='qpe':
            checks=[]
            for _ in range(stop_confirmations):
                est,fraction,supported=count_once(out.counting_calls+1)
                out.history.append({'round':max_rounds,'kind':'final_stop_confirmation',
                                    'M_est':est,'full_fraction':fraction})
                checks.append(est==net.size and supported)
                if not checks[-1]: break
            if len(checks)==stop_confirmations and all(checks):
                out.status='complete_qpe_heuristic'
                out.completion_reason='Repeated phase counts passed the ideal-model coverage test at round budget; heuristic, not certified'
                return out
    out.status='inconclusive_round_budget'
    out.completion_reason=f'Reached --max-rounds={max_rounds} without convincing full-coverage evidence'
    return out
