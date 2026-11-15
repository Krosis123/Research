import numpy as np
import pytest
from atlantis.model import Network,TruthRule,binary_to_decimal,decimal_to_binary
from atlantis.states import all_states,random_states,fix_initial_nodes
from atlantis.analysis import *


def test_state_encoding():
    states=all_states(5)
    np.testing.assert_array_equal(binary_to_decimal(states),np.arange(32))
    np.testing.assert_array_equal(decimal_to_binary(range(32),5),states)
    assert binary_to_decimal(np.array([[1,0,1]]))[0]==5


def test_zero_input_retains_state():
    n=Network(['a','b'],np.zeros((2,2)))
    np.testing.assert_array_equal(n.step(all_states(2)),all_states(2))


def test_source_target_orientation():
    n=Network(['a','b'],[[0,-2],[3,0]],[0,0])
    np.testing.assert_array_equal(n.step([[1,0],[0,1]]),[[1,0],[1,1]])


def test_rules_synchronous():
    n=Network(['a','b'],rules=[TruthRule([1],[0,1]),TruthRule([0],[0,1])])
    np.testing.assert_array_equal(n.step([[1,0],[0,1]]),[[0,1],[1,0]])


def test_rules_constants_and_missing():
    n=Network(['a','b'],rules=[TruthRule([],[1]),None])
    np.testing.assert_array_equal(n.step([[0,0],[0,1]]),[[1,0],[1,1]])


def test_cyclic_attractor_and_basins():
    n=Network(['a','b'],rules=[TruthRule([0],[1,0]),TruthRule([1],[0,1])])
    d=deterministic_analysis(n,all_states(2),20)
    assert len(d.attractors)==2
    assert all(a.kind=='Cyclic' and a.basin==.5 for a in d.attractors)
    assert d.unresolved==0
    np.testing.assert_array_equal(d.attractors[0].stratified,[2,1])


def test_timeout_is_reported():
    n=Network(['a','b'],rules=[TruthRule([0],[1,0]),TruthRule([1],[0,1])])
    d=deterministic_analysis(n,all_states(2),1)
    assert d.unresolved==4 and not d.attractors


def test_weighted_mutation_basal_semantics():
    n=Network(['a','b'],[[0,1],[0,0]])
    m=n.mutate([('a',1),('a>b',2)])
    assert m.basal[0]==1000 and m.weights[0,1]==0
    assert n.basal[0]==0 and n.weights[0,1]==1


def test_rule_link_deletion_fixes_source_off():
    n=Network(['a','b'],rules=[None,TruthRule([0,1],[0,1,1,0])])
    m=n.mutate([('a>b',2)])
    assert m.rules[1].sources==[1]
    np.testing.assert_array_equal(m.rules[1].outputs,[0,1])
    m=n.mutate([('b',1)])
    assert np.all(m.rules[1].outputs==1)


def test_sampling_unique_and_repeatable():
    a=random_states(201,100,83); b=random_states(201,100,83)
    assert a.shape==(100,201) and len(np.unique(a,axis=0))==100
    np.testing.assert_array_equal(a,b)


def test_initial_fixed_nodes_are_not_clamped():
    n=Network(['a'],[[0]],[1])
    states=fix_initial_nodes(n,all_states(1),{'a':0})
    np.testing.assert_array_equal(states,[[0],[0]])
    np.testing.assert_array_equal(n.step(states),[[1],[1]])


def test_transition_hand_calculated():
    n=Network(['a'],[[0]],[0]); s=all_states(1)
    t=transition_probabilities(n,s,5,.1)
    np.testing.assert_allclose(t,[[.9,.1],[.1,.9]])
    n=Network(['a'],[[0]],[1]); t=transition_probabilities(n,s,1,.1)
    on=.5+.5*np.tanh(1)
    np.testing.assert_allclose(t,[[1-on,on],[1-on,on]])


def test_subset_flux_is_not_renormalized():
    p,it,converged=steady_state_probabilities([[.2,.3],[.4,.1]],10000,1e-12)
    np.testing.assert_allclose(p,[4/7,3/7],atol=1e-10)
    assert converged and it>10


def test_pruning_one_synchronous_step():
    n=Network(['a'],[[0]],[1])
    np.testing.assert_array_equal(state_space_pruning(n,all_states(1)),[[1]])


def test_trajectory_is_probability_rank_interval():
    r=ProbabilisticResult(all_states(2),np.eye(4),np.array([.1,.4,.3,.2]),11,True,5,.001,1e-7,False)
    np.testing.assert_array_equal(map_trajectory(r,[[0,1],[1,1]]),[1,2,3])


@pytest.mark.parametrize('work',[lambda:Network(['a','A'],np.zeros((2,2))),lambda:Network(['a'],[[np.nan]]),lambda:TruthRule([0],[1]),lambda:all_states(50),lambda:random_states(2,5),lambda:decimal_to_binary([4],2)])
def test_invalid_inputs(work):
    with pytest.raises((ValueError,MemoryError)):work()


def test_cancelled():
    n=Network(['a'],[[0]])
    with pytest.raises(CancelledError):deterministic_analysis(n,all_states(1),cancel=lambda:True)


def test_rules_pa_rejected():
    n=Network(['a'],rules=[TruthRule([],[1])])
    with pytest.raises(ValueError):probabilistic_analysis(n,all_states(1))


def test_sampling_fair_bit_distribution():
    sample=random_states(201,5000,883)
    assert abs(float(sample.mean())-.5)<.003
    assert np.all(np.abs(sample.mean(axis=0)-.5)<.04)
