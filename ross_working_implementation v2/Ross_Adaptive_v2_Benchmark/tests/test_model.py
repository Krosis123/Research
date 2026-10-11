import math
import numpy as np
from ross_bench.model import make_network,exact_truth,verify_candidate
from ross_bench.reference import reduced_state_probabilities,suppression_parameters,qpe_theoretical_distribution,hadamard_inplace


def test_rossini_ground_truth():
    t=exact_truth(make_network(4,'rossini4'))
    assert t.max_transient==3
    assert {format(k[0],'04b'):v for k,v in t.basin_sizes.items()}=={
        '0000':11,'0011':2,'1011':1,'1101':1,'1111':1}


def test_rossini_suppression():
    net=make_network(4,'rossini4');t=exact_truth(net)
    one={(0,)}
    out,par,m,expected,leak=reduced_state_probabilities(net,t,one)
    assert m==11 and par.J==1 and leak<1e-20
    assert math.isclose(out[3],0.4,abs_tol=1e-12)
    assert math.isclose(out[11],0.2,abs_tol=1e-12)
    assert math.isclose(out[13],0.2,abs_tol=1e-12)
    assert math.isclose(out[15],0.2,abs_tol=1e-12)
    four={(0,),(3,),(11,),(15,)}
    out,par,m,expected,leak=reduced_state_probabilities(net,t,four)
    assert m==15
    assert out[13]>1-1e-12 and leak<1e-20


def test_family_idempotency_and_cycles():
    for n in (4,10,15):
        for family in ('projection','skewed','cycle2','long_chain'):
            net=make_network(n,family);t=exact_truth(net)
            assert sum(t.basin_sizes.values())==1<<n
            assert all(t.cycle_of[x] in t.basin_sizes for x in range(net.size))
            assert t.max_transient==(n-1 if family=='long_chain' else 1)
            if family=='cycle2':
                assert sorted(len(c) for c in t.attractors)==[1,1,2]
                assert len(t.attractors)==3


def test_hadamard_unitary():
    for n in (1,2,5):
        a=np.zeros(1<<n,dtype=complex);a[0]=1
        hadamard_inplace(a)
        assert np.allclose(a,1/math.sqrt(1<<n))
        hadamard_inplace(a)
        assert np.allclose(a[0],1)
        assert np.allclose(a[1:],0)


def test_qpe_distribution():
    for M in (0,1,4,11,15,16):
        p=qpe_theoretical_distribution(M,16,6)
        assert np.all(p>=0) and np.isclose(p.sum(),1)
        if M==0: assert p[0]>1-1e-12


def test_single_state_verification_not_whole_graph():
    net=make_network(4,'rossini4')
    good,cycle=verify_candidate(net,int('1101',2))
    assert good and cycle==(13,)
    good,cycle=verify_candidate(net,int('1100',2))
    assert not good and cycle==(0,)
    cyc=make_network(10,'cycle2')
    truth=exact_truth(cyc)
    pair=next(c for c in truth.attractors if len(c)==2)
    for state in pair:
        yes,got=verify_candidate(cyc,state)
        assert yes and got==pair
