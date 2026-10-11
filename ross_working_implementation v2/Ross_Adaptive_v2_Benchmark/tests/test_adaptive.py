"""Pure-Python tests for the truth-independent adaptive control flow."""
import numpy as np
import pytest
from ross_bench.model import make_network
from ross_bench.adaptive import (discover, determine_candidates,
                                  terminal_states, covered_count)


def _run(family='rossini4', T=3, *, seed=42, mode='exact', policy='classical_audit',
         precision=5, max_rounds=10):
    net=make_network(4,family)
    return discover(net,T=T,engine='reduced',counting_mode=mode,
                    shots=512,counting_precision=precision,counting_shots=256,
                    rng=np.random.default_rng(seed),seed=seed,
                    max_rounds=max_rounds,search_retries=2,
                    stop_policy=policy,stop_confirmations=2)


def test_adaptive_exact_stops_without_known_attractor_count():
    # 5 cycles discovered, maximum search round budget is EXACTLY 5.
    result=_run(max_rounds=5)
    assert result.status=='complete_classically_certified'
    assert len(result.cycles)==5
    assert result.search_attempts==5
    assert result.classical_audit_states_scanned>=16
    assert result.counting_calls==4


def test_adaptive_qpe_heuristic_stops_and_labels_its_uncertainty():
    result=_run(mode='qpe_ideal',policy='qpe',precision=5)
    assert result.status=='complete_qpe_heuristic'
    assert len(result.cycles)==5
    assert result.counting_calls>=6
    assert 'NOT certified' in result.completion_reason


def test_insufficient_T_never_certifies_completion():
    result=_run(T=1,max_rounds=10)
    assert not result.status.startswith('complete_')
    assert result.status.startswith('inconclusive_')


def test_reduced_cycle_still_recovers_both_cycle_members():
    result=_run(family='cycle2',T=1,max_rounds=3)
    assert result.status=='complete_classically_certified'
    assert sorted(map(len,result.cycles))==[1,1,2]


def test_candidate_rejection_uses_only_local_trajectory():
    net=make_network(4,'rossini4')
    accepted,invalid,rejected=determine_candidates(net,{12:5,13:4,0:3},set())
    assert invalid==5
    assert rejected==5
    assert {cyc for cyc,_ in accepted}=={(13,),(0,)}


def test_adaptive_mode_does_not_request_exact_truth(monkeypatch):
    # The runner may compute truth later for reports; truth_mode none forbids it.
    from ross_bench import runner
    def forbidden(*args,**kwargs):
        raise AssertionError('Ground truth was consulted by adaptive discovery')
    monkeypatch.setattr(runner,'exact_truth',forbidden)
    row=runner.run_adaptive(4,'rossini4',0,123,'reduced','exact',
                            256,5,128,0.0,24,False,3,5,2,'classical_audit',
                            2,0.95,'none')
    assert row['status']=='complete_classically_certified'
    assert row['unique_attractors_found']==5
    assert 'attractor_recall' not in row
    assert row['completeness_certificate']=='exact_classical'


def test_classical_audit_is_exact_when_T_enough():
    net=make_network(4,'rossini4')
    terminal=terminal_states(net,3)
    assert covered_count(terminal,{(0,)})==11
    assert covered_count(terminal,{(0,),(3,),(11,),(13,),(15,)})==16


def test_no_implicit_T_from_truth():
    from ross_bench.runner import run_adaptive
    with pytest.raises(ValueError,match='evolution-steps'):
        run_adaptive(4,'rossini4',0,12,'reduced','exact',
                     256,5,128,0.0,24,False,None,10,2,'classical_audit',2,0.95,'none')
