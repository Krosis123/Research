"""Independent post-run scoring for genuine Aer QPE discovery."""
import json
import argparse
from pathlib import Path
import sys
from threading import Event, Thread
from time import perf_counter
from unittest.mock import patch

import numpy as np
import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atlantis.expressions import from_expressions
from atlantis.quantum.engine import Settings, run
from atlantis.quantum.ross.circuits import qiskit_counts


def network_fixture(width, seed, fanin):
    rng = np.random.default_rng(seed)
    names = [f'locus_{i}_r{seed}' for i in range(width)]
    inputs = [sorted(rng.choice(width, fanin, replace=False).tolist()) for _ in names]
    tables = rng.integers(0, 2, (width, 2**fanin)).tolist()
    rules = {}
    for name, sources, table in zip(names, inputs, tables):
        terms = ['('+' & '.join(('' if bit=='1' else '~')+names[j]
                               for j,bit in zip(sources,f'{i:0{fanin}b}'))+')'
                 for i,value in enumerate(table) if value]
        rules[name] = ' | '.join(terms) or '0'
    return from_expressions(rules), inputs, tables


def evaluate(width, inputs, tables, horizon, result):
    states = [f'{i:0{width}b}' for i in range(2**width)]
    successor = {state: ''.join(str(table[int(''.join(state[j] for j in indices),2)])
                               for indices,table in zip(inputs,tables)) for state in states}
    basins = {}
    terminal = {}
    max_transient = 0
    for initial in states:
        state = initial
        path = []
        while state not in path:
            path.append(state)
            state = successor[state]
        entry = path.index(state)
        max_transient = max(max_transient, entry)
        key = tuple(sorted(path[entry:]))
        basins[key] = basins.get(key,0)+1
        state = initial
        for _ in range(horizon):
            state = successor[state]
        terminal[initial] = state
    discovered = [tuple(sorted(e['cycle'])) for e in result['history'] if e['kind']=='new_cycle']
    seen = set()
    duplicate_shots = 0
    count_errors = []
    for e in result['history']:
        if e['kind']=='new_cycle':
            seen.update(e['cycle'])
        elif e['kind']=='measurements':
            duplicate_shots += sum(v for k,v in e['counts'].items() if k in seen)
        elif e['kind']=='qpe_measurements':
            actual = sum(x in e['marked_terminal_states'] for x in terminal.values())
            estimate = max(e['M_histogram'],key=e['M_histogram'].get)
            count_errors.append(dict(call=e['call'],actual_at_horizon=actual,estimate=estimate,
                                     signed_error=estimate-actual))
    missing = sorted(set(basins)-set(discovered))
    return dict(ground_truth=[dict(cycle=k,basin=v) for k,v in sorted(basins.items())],
                max_transient=max_transient,missed_attractors=missing,
                false_discoveries=sorted(set(discovered)-set(basins)),
                duplicate_discoveries=len(discovered)-len(set(discovered)),
                duplicate_shots=duplicate_shots, count_errors=count_errors,
                exact_match=not missing and set(discovered)==set(basins),
                heuristic_false_completion=bool(missing) and result['status']=='complete_qpe_heuristic')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--adversarial',action='store_true')
    parser.add_argument('--low-shots',action='store_true',help='Use four shots in the adversarial case')
    parser.add_argument('--longer',action='store_true',help='Repeat three fixtures at fixed longer horizons')
    parser.add_argument('--additional',action='store_true',help='Use three additional randomly generated structures')
    parser.add_argument('--precision',type=int,choices=(1,2,3,4),help='Override adversarial QPE precision')
    args=parser.parse_args()
    if args.low_shots and not args.adversarial:
        parser.error('--low-shots requires --adversarial')
    if args.longer and args.adversarial:
        parser.error('--longer and --adversarial are separate experiments')
    if args.precision is not None and not args.adversarial:
        parser.error('--precision requires --adversarial')
    rows=[]
    def forbidden(*args,**kwargs):
        raise AssertionError('Exhaustive truth requested during genuine discovery')
    cases=((2,11,2,1),(3,17,2,2),(3,39,3,1),(3,55,3,2),(4,61,3,1),(4,82,4,2))
    trials=((32,23,0),(128,23,0),(128,47,0),(128,47,2))
    path=Path('validation/discovery-random-guarded-024.json')
    if args.additional:
        cases=((2,124,2,3),(3,117,2,4),(3,203,3,4))
        path=Path('validation/discovery-additional-024.json')
    if args.longer:
        cases=((2,11,2,3),(3,17,2,4),(3,39,3,3))
        path=Path('validation/discovery-longer-guarded-024.json')
    if args.adversarial:
        cases=((4,0,4,1),)
        trials=tuple((shots,seed,level) for shots in (16,128) for seed in (1,2,3,4) for level in (0,2))
        path=Path('validation/discovery-adversarial-guarded-024.json')
        if args.low_shots:
            trials=tuple((4,seed,0) for seed in range(1,9))
            path=Path('validation/discovery-low-shots-guarded-024.json')
        if args.precision is not None:
            path=Path(f'validation/discovery-stress-p{args.precision}-024.json')
            trials=((16,1,0),(16,2,0),(128,1,0),(128,2,0))
    for width,fixture_seed,fanin,T in cases:
        if args.adversarial:
            names=[f'tiny_{i}' for i in range(width)]
            net=from_expressions({name:' & '.join(names) for name in names})
            inputs=[list(range(width)) for _ in names]
            tables=[[0]*(2**width-1)+[1] for _ in names]
        else:
            net,inputs,tables=network_fixture(width,fixture_seed,fanin)
        for shots,seed,level in trials:
            def executor(qc, nshots, **opts):
                return qiskit_counts(qc,nshots,optimization_level=level,**opts)
            settings=Settings(engine='aer_mps',counting_mode='qpe_aer',stop_policy='qpe',
                              counting_precision=(args.precision or 1) if args.adversarial else 3,
                              T=T,shots=shots,counting_shots=shots,
                              seed=seed,max_rounds=8,timeout_seconds=120)
            start=perf_counter()
            process=psutil.Process()
            peak=[process.memory_info().rss]
            stop=Event()
            def poll():
                while not stop.wait(.005):
                    peak[0]=max(peak[0],process.memory_info().rss)
            monitor=Thread(target=poll,daemon=True)
            monitor.start()
            try:
                with patch('atlantis.quantum.ross.adaptive.terminal_states',forbidden), \
                     patch('atlantis.quantum.ross.model.exact_truth',forbidden):
                    result=run(net,settings,circuit_executor=executor)
            finally:
                stop.set()
                monitor.join()
            elapsed=perf_counter()-start
            rows.append(dict(width=width,fixture_seed=fixture_seed,fanin=fanin,T=T,shots=shots,
                             seed=seed,optimization_level=level,wall_s=elapsed,
                             process_rss_bytes=process.memory_info().rss,
                             observed_peak_rss_bytes=max(peak[0],process.memory_info().rss),
                             score=evaluate(width,inputs,tables,T,result),result=result))
            path.write_text(json.dumps(rows,indent=2))
            print(width,fixture_seed,shots,seed,level,result['status'],rows[-1]['score']['exact_match'],flush=True)


if __name__=='__main__':
    main()
