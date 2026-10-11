"""Repeatable, auditable Rossini benchmarks; no Qiskit dependency for reduced engine."""
from __future__ import annotations
import argparse,csv,json,os,platform,sys,time,traceback
from pathlib import Path
import numpy as np
from .model import make_network,exact_truth,verify_candidate
from .reference import reduced_state_probabilities,measure_ideal,qpe_estimate

FAMILIES=('projection','skewed','cycle2','long_chain')
BASE_FIELDS=['timestamp_utc','network','n','family','seed','repeat','engine','counting_mode',
             'shots','counting_precision','counting_shots','readout_flip_probability',
             'status','error','attractors','attractor_states','max_cycle_length',
             'max_transient','T','logical_qubits','counting_qubits','statevector_gib',
             'truth_runtime_s','search_runtime_s','counting_runtime_s','simulation_runtime_s',
             'total_runtime_s','peak_rss_mib','suppression_runs','oracle_calls_ideal',
             'unique_attractors_found','attractor_recall','false_positive_rate',
             'wrong_run_measurement_rate','max_suppressed_leakage','average_M_abs_error',
             'compiled_depth_max','compiled_size_max','compiled_2q_count_max']


def rss_mib():
    """Whole-process peak RSS, cross-platform when OS statistics are available."""
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 if sys.platform!='darwin' else (1024*1024))
    except ImportError:  # Windows
        try:
            import psutil
            info=psutil.Process().memory_info()
            return getattr(info,'peak_wset',info.rss)/(1024*1024)
        except ImportError:
            return None


def now_utc():
    from datetime import datetime,timezone
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def run_one(n,family,repeat,seed,engine,mode,shots,counting_precision,counting_shots,flip,
            max_sim_qubits,force_large,include_first=True):
    start=time.perf_counter(); rng=np.random.default_rng(seed)
    meta=dict(timestamp_utc=now_utc(),network=f'{family}_{n}',n=n,family=family,
              seed=seed,repeat=repeat,engine=engine,counting_mode=mode,shots=shots,
              counting_precision=counting_precision,counting_shots=counting_shots,
              readout_flip_probability=flip,status='ok',error='')
    t=time.perf_counter()
    net=make_network(n,family)
    truth=exact_truth(net)
    truth_runtime=time.perf_counter()-t
    T=max(1,truth.max_transient)
    qubits=n*(T+1)
    meta.update(attractors=len(truth.attractors),
                attractor_states=sum(len(c) for c in truth.attractors),
                max_cycle_length=truth.max_cycle,max_transient=truth.max_transient,T=T,
                logical_qubits=qubits,counting_qubits=qubits+counting_precision,
                statevector_gib=16*2.0**qubits/(1024**3),truth_runtime_s=truth_runtime)
    if engine in ('aer','aer_mps') and (qubits+(counting_precision if mode=='qpe_aer' else 0))>max_sim_qubits and not force_large:
        meta.update(status='skipped_resource',error=f'{qubits+(counting_precision if mode=="qpe_aer" else 0)} circuit qubits exceed --max-sim-qubits={max_sim_qubits}. Use --force-large with MPS explicitly.')
        return finish(meta,start)
    from .circuits import search_circuit,counting_circuit,qiskit_counts,qpe_counts_to_M
    excluded=set();times=[];count_time=0;search_time=0;sim_time=0
    false_hits=0; wrong_run_hits=0;total_hits=0; ideal_calls=0
    max_leak=0;errors=[];max_depth=max_size=max_2q=0
    # We measure a complete run (shots), then harvest only ONE new verified
    # attractor, like Rossini's baseline algorithm. Every member of a cycle is
    # excluded once that cycle has been identified.
    for run_index in range(len(truth.attractors)):
        exact_M=sum(truth.basin_sizes[a] for a in excluded)
        m_used=exact_M
        if excluded and mode!='exact':
            t=time.perf_counter()
            if mode=='qpe_ideal':
                m_used,_=qpe_estimate(exact_M,net.size,counting_precision,counting_shots,rng)
            elif mode=='qpe_aer':
                qc=counting_circuit(net,T,[net.as_bits(s) for c in excluded for s in c],counting_precision)
                results,resource_info=qiskit_counts(qc,counting_shots,
                    method='matrix_product_state' if engine=='aer_mps' else 'statevector',seed=seed+run_index)
                m_used,_=qpe_counts_to_M(results,net.size,counting_precision)
                max_depth=max(max_depth,resource_info['compiled_depth']);max_size=max(max_size,resource_info['compiled_size'])
                max_2q=max(max_2q,resource_info['compiled_2q_count'])
                ideal_calls+=(1<<counting_precision)-1
            count_time+=time.perf_counter()-t
            errors.append(abs(m_used-exact_M))
        if excluded and not(0<m_used<net.size):
            meta.update(status='failed_counting',error=f'QPE returned M={m_used} for exact M={exact_M}')
            break
        t=time.perf_counter()
        if engine=='reduced':
            probs,params,m_exact,expected,leak=reduced_state_probabilities(net,truth,excluded,
                                                                M_parameter=m_used if excluded else None)
            search_time+=time.perf_counter()-t
            max_leak=max(max_leak,leak)
            t=time.perf_counter()
            counts=measure_ideal(probs,shots,n,rng,flip)
            sim_time+=time.perf_counter()-t
        else:
            qc,params=search_circuit(net,T,[net.as_bits(s) for c in excluded for s in c],m_used)
            search_time+=time.perf_counter()-t
            t=time.perf_counter()
            counts_bits,resource_info=qiskit_counts(qc,shots,
                   method='matrix_product_state' if engine=='aer_mps' else 'statevector',seed=seed+run_index)
            sim_time+=time.perf_counter()-t
            counts={int(bits.replace(' ',''),2):int(num) for bits,num in counts_bits.items()}
            max_depth=max(max_depth,resource_info['compiled_depth'])
            max_size=max(max_size,resource_info['compiled_size'])
            max_2q=max(max_2q,resource_info['compiled_2q_count'])
        if params: ideal_calls+=params.J*2+1  # forward/backward T queries, plus final T
        else: ideal_calls+=1
        total_hits+=sum(counts.values())
        # Only *states on an attractor* are eligible. A noise-induced transient
        # output must not be incorrectly accepted as a newly found attractor.
        cycle_states={s for cyc in truth.attractors for s in cyc}
        false_hits+=sum(ct for s,ct in counts.items() if s not in cycle_states)
        wrong_run_hits+=sum(ct for s,ct in counts.items() if
                            s not in cycle_states or truth.cycle_of[s] in excluded)
        candidates=[]
        for s,ct in counts.items():
            valid,cycle=verify_candidate(net,s)
            if valid and cycle not in excluded:
                candidates.append((s,ct,cycle))
        if not candidates:
            meta.update(status='failed_discovery',error=f'No unseen attractor in run {run_index+1}')
            break
        # A single outcome extracted uniformly from VALID shot occurrences.
        # Ground truth is NOT consulted when accepting the candidate or extracting
        # its cycle: only its own experimentally measured state is traced.
        weights=np.array([c for _,c,_ in candidates],dtype=float)
        weights/=weights.sum()
        picked=candidates[int(rng.choice(len(candidates),p=weights))]
        excluded.add(picked[2])
    meta.update(
        search_runtime_s=search_time,counting_runtime_s=count_time,
        simulation_runtime_s=sim_time,suppression_runs=len(excluded),
        oracle_calls_ideal=ideal_calls,unique_attractors_found=len(excluded),
        attractor_recall=len(excluded)/len(truth.attractors),
        false_positive_rate=false_hits/total_hits if total_hits else None,
        wrong_run_measurement_rate=wrong_run_hits/total_hits if total_hits else None,
        max_suppressed_leakage=max_leak,
        average_M_abs_error=float(np.mean(errors)) if errors else 0.0,
        compiled_depth_max=max_depth or None,compiled_size_max=max_size or None,
        compiled_2q_count_max=max_2q or None)
    return finish(meta,start)


def finish(meta,start):
    meta['total_runtime_s']=time.perf_counter()-start
    meta['peak_rss_mib']=rss_mib()
    return meta


def write_rows(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    extras=sorted({x for row in rows for x in row if x not in BASE_FIELDS})
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=BASE_FIELDS+extras)
        writer.writeheader();writer.writerows(rows)


def run_cli(argv=None):
    parser=argparse.ArgumentParser(description='Rossini quantum search scaling benchmark')
    parser.add_argument('--nodes',type=int,nargs='+',default=[4,10,15])
    parser.add_argument('--families',nargs='+',default=list(FAMILIES))
    parser.add_argument('--engine',choices=['reduced','aer','aer_mps'],default='reduced')
    parser.add_argument('--counting-mode',choices=['exact','qpe_ideal','qpe_aer'],default='exact')
    parser.add_argument('--repetitions',type=int,default=3)
    parser.add_argument('--shots',type=int,default=1024)
    parser.add_argument('--counting-shots',type=int,default=256)
    parser.add_argument('--counting-precision',type=int,default=8)
    parser.add_argument('--readout-flip',type=float,default=0.0)
    parser.add_argument('--max-sim-qubits',type=int,default=24)
    parser.add_argument('--force-large',action='store_true')
    parser.add_argument('--seed',type=int,default=2026)
    parser.add_argument('--output',default='results/rossini_benchmark.csv')
    args=parser.parse_args(argv)
    if args.engine!='reduced' and args.readout_flip:
        parser.error('--readout-flip only applies to reduced engine; use calibrated Aer noise separately')
    if args.counting_mode=='qpe_aer' and args.engine=='reduced':
        parser.error('Real Aer QPE requires --engine aer or aer_mps')
    if not 0<=args.readout_flip<=1: parser.error('readout probability must lie in [0,1]')
    rows=[]
    for n in args.nodes:
        for family in args.families:
            if family=='rossini4' and n!=4: continue
            for rep in range(args.repetitions):
                seed=args.seed+n*10000+rep*7919+sum(map(ord,family))
                try:
                    row=run_one(n,family,rep,seed,args.engine,args.counting_mode,
                                args.shots,args.counting_precision,args.counting_shots,args.readout_flip,
                                args.max_sim_qubits,args.force_large)
                except Exception as e:
                    row=dict(timestamp_utc=now_utc(),n=n,family=family,repeat=rep,seed=seed,
                             engine=args.engine,counting_mode=args.counting_mode,
                             status='error',error=f'{type(e).__name__}: {e}')
                rows.append(row)
                print(f"{family:12} n={n:2} rep={rep} status={row['status']:18} "
                      f"recall={row.get('attractor_recall','?')} "
                      f"qubits={row.get('logical_qubits','?')} "
                      f"elapsed={row.get('total_runtime_s',0):.3f}s",flush=True)
                write_rows(args.output,rows)
    manifest={
      'command':sys.argv,'python':sys.version,'platform':platform.platform(),
      'memory_note':'peak_rss_mib is cumulative high-water RSS of the entire process; use per-job subprocess isolation for per-case peak.',
      'engine_note':'reduced is an exact ideal basin-phase mathematical surrogate, not a full n(T+1) quantum circuit simulation.',
      'counting_note':'exact uses classical ground truth M; qpe_ideal uses the ideal QPE distribution as an estimator, no QPE circuit executed.',
      'noise_note':'readout_flip is an independent final measurement bit-flip proxy, NOT a hardware-calibrated circuit noise model.',
      'source_notes':'Original four-gene Qiskit source untouched in original/ directory.',
      'rows':len(rows),
    }
    out=Path(args.output)
    out.with_suffix('.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return rows

if __name__=='__main__': run_cli()
