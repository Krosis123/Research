"""Independent Boolean oracle and measured reversible-circuit checks."""
from itertools import product

import numpy as np
import pytest
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from atlantis.expressions import from_expressions
from atlantis.quantum.adapter import QuantumNetwork
from atlantis.quantum.ross.circuits import time_evolution
from atlantis.quantum.ross.model import exact_truth


def fixture(width, seed, dense):
    rng = np.random.default_rng(seed)
    names = [f'gene_{i}_alt' for i in range(width)]
    specs = []
    rules = {}
    for i, name in enumerate(names):
        # Include self feedback and vary fan-in independently of label ordering.
        peers = list(range(width)) if dense else [i, (i+1)%width]
        a,b,c = map(int,rng.choice(peers,3,replace=True))
        operation = int(rng.integers(3))
        A,B,C = [names[j] for j in (a,b,c)]
        rules[name] = [f'({A} ^ {B}) | (~{C} & {name})',
                       f'(~{A} & ({B} | {name})) ^ {C}',
                       f'({A} | {B}) & (~{C} | {name})'][operation]
        specs.append((a,b,c,operation))
    def step(bits):
        result=[]
        for i,(a,b,c,op) in enumerate(specs):
            x,y,z=bits[a],bits[b],bits[c]
            if op==0:
                value=(x != y) or (not z and bits[i])
            elif op==1:
                value=(not x and (y or bits[i])) != bool(z)
            else:
                value=(x or y) and (not z or bits[i])
            result.append(int(value))
        return tuple(result)
    return names,rules,step


def basins(states, step):
    outcomes={}
    for initial in states:
        path=[]
        state=initial
        while state not in path:
            path.append(state)
            state=step(state)
        outcomes[initial]=frozenset(path[path.index(state):])
    return outcomes


@pytest.mark.parametrize('width,seed,dense',[(2,27,False),(3,76,False),(4,91,True),(5,23,True)])
def test_unseen_network_aer_all_inputs(width,seed,dense):
    names,rules,step=fixture(width,seed,dense)
    inputs=list(product((0,1),repeat=width))
    expected_basins=basins(inputs,step)
    aer=AerSimulator(method='matrix_product_state',max_parallel_threads=2)
    for order in (list(range(width)),list(reversed(range(width)))):
        renamed={names[i]:f'node_{i}_renamed' for i in range(width)}
        relabeled={renamed[names[i]]:replace_names(rules[names[i]],renamed) for i in order}
        network=from_expressions(relabeled)
        adapter=QuantumNetwork(network)
        evolution=time_evolution(adapter,2)
        circuits=[]
        expected=[]
        index=lambda bits: int(''.join(str(bits[i]) for i in order),2)
        for state in inputs:
            value=index(state)
            circuit=QuantumCircuit(3*width,3*width)
            for bit in range(width):
                if value & (1<<bit):
                    circuit.x(bit)
            circuit.compose(evolution,inplace=True)
            forward=value | (index(step(state))<<width) | (index(step(step(state)))<<(2*width))
            inverse=circuit.compose(evolution.inverse())
            for item,answer in ((circuit,forward),(inverse,value)):
                item.measure(range(3*width),range(3*width))
                circuits.append(item)
                expected.append(f'{answer:0{3*width}b}')
        compiled=transpile(circuits,aer,optimization_level=1,seed_transpiler=42,num_processes=1)
        results=aer.run(compiled,shots=4,seed_simulator=42).result()
        assert [results.get_counts(i) for i in range(len(compiled))]==[{x:4} for x in expected]
        truth=exact_truth(adapter)
        actual={frozenset(c):size for c,size in truth.basin_sizes.items()}
        reference={}
        for cycle in expected_basins.values():
            key=frozenset(index(state) for state in cycle)
            reference[key]=reference.get(key,0)+1
        assert actual==reference


def replace_names(expression, names):
    import re
    return re.sub(r'\b\w+\b',lambda token:names[token.group()],expression)

def test_clamped_coordinate_applied_at_initial_state():
    from atlantis.analysis import deterministic_analysis
    from atlantis.expressions import from_expressions
    network = from_expressions({'Input':'Input','Output':'Input'})
    network.clamped = {'Input':1}
    result = deterministic_analysis(network, [[0,1],[1,1]], search_duration=1)
    assert result.unresolved == 0
    assert result.initial_states.tolist() == [[1,1],[1,1]]
    assert result.attractors[0].basin == 1

def test_finite_precision_can_alias_almost_full_coverage():
    from atlantis.quantum.ross.reference import qpe_theoretical_distribution
    # Distinct counts can map to the same most likely QPE outcome.
    full = qpe_theoretical_distribution(256,256,2)
    almost = qpe_theoretical_distribution(255,256,2)
    tiny = qpe_theoretical_distribution(1,256,2)
    assert np.argmax(full) == np.argmax(almost) == 2
    assert almost[2] > .95
    assert np.argmax(tiny) == 0


def test_high_attractor_count_small_search_budget_is_inconclusive():
    from atlantis.quantum.engine import Settings,run
    network = from_expressions({name:name for name in ('u','v','w','z')})
    report=run(network,Settings(engine='aer',T=1,max_rounds=1,stop_policy='bounded',shots=16))
    assert report['status'].startswith('inconclusive')
    assert len(report['cycles']) < 16

def test_unseen_mixed_cycle_genuine_aer_discovery(monkeypatch):
    from atlantis.quantum.engine import Settings,run
    from atlantis.quantum.ross import adaptive

    def forbid_enumeration(*args, **kwargs):
        raise AssertionError('Classical full-state enumeration entered the genuine counting path')

    monkeypatch.setattr(adaptive,'terminal_states',forbid_enumeration)
    network=from_expressions({'switch':'switch','osc':'~osc & switch','lag':'osc & switch'})
    report=run(network,Settings(engine='aer',T=1,counting_mode='qpe_aer',stop_policy='qpe',
                               counting_precision=3,shots=64,counting_shots=128,seed=42))
    assert report['status']=='complete_qpe_heuristic'
    assert {frozenset(c) for c in report['cycles']}=={
        frozenset(['000']),frozenset(['101','110'])}

def test_ideal_qpe_null_bound_and_coarse_grid():
    from atlantis.quantum.ross.adaptive import qpe_full_coverage_evidence
    from atlantis.quantum.ross.reference import qpe_theoretical_distribution
    for size in (2,4,8,16,32):
        for precision in range(1,6):
            bins=1<<precision
            evidence=qpe_full_coverage_evidence({f'{bins//2:0{precision}b}':32},
                                               size,precision,.001,.95)
            for count in range(size):
                observed=qpe_theoretical_distribution(count,size,precision)[bins//2]
                assert observed<=evidence['null_bound']+1e-12
    assert not qpe_full_coverage_evidence({'1':128},16,1,.001,.95)['passes']
    assert qpe_full_coverage_evidence({'100':32},16,3,.001,.95)['passes']


def test_rare_basin_alias_does_not_signal_completion(monkeypatch):
    from atlantis.quantum.engine import Settings,run
    from atlantis.quantum.ross import adaptive
    def forbidden(*args,**kwargs):
        raise AssertionError('Exhaustive terminal enumeration entered genuine QPE')
    monkeypatch.setattr(adaptive,'terminal_states',forbidden)
    names=['u','v','w','z']
    network=from_expressions({name:'u & v & w & z' for name in names})
    result=run(network,Settings(T=1,engine='aer_mps',counting_mode='qpe_aer',
                              stop_policy='qpe',counting_precision=1,
                              shots=4,counting_shots=4,seed=1))
    assert result['status']=='inconclusive_coverage_evidence'
    assert result['cycles']==[['0000']]
    evidence=[e for e in result['history'] if e['kind']=='qpe_coverage_evidence']
    assert evidence[0]['central_hits']==4 and evidence[0]['null_bound']==1
