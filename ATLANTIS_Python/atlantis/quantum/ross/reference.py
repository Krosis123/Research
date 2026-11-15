"""Reduced-state, ideal mathematical reference of Rossini suppression.

This is NOT a simulation of the n*(T+1)-qubit circuit, nor quantum hardware.
It eliminates the T^dagger P T sandwich algebraically using exact basin ground
truth. It validates the suppression mathematics and finite-shot extraction.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import asin, ceil, pi, sin, cos, sqrt
import numpy as np
from .model import Network, Truth


@dataclass(frozen=True)
class Suppression:
    M: int
    N: int
    beta: float
    J: int
    phi: float


def suppression_parameters(M: int, N: int) -> Suppression:
    if not 0<M<N: raise ValueError(f'Suppression requires 0<M<N, got {M},{N}')
    beta=asin(sqrt(M/N))
    J=max(1,ceil(beta/(pi-2*beta)))
    arg=sin(pi/(4*J+2))/cos(beta)
    if abs(arg)>1+1e-10: raise ValueError(f'Nonphysical phase argument {arg}')
    phi=-2*asin(min(1.0,max(-1.0,arg)))
    return Suppression(M,N,beta,J,phi)


def hadamard_inplace(a: np.ndarray):
    """n-qubit Hadamard as efficient Walsh-Hadamard (no 2^n x 2^n matrix)."""
    N=a.size
    width=1
    while width<N:
        mat=a.reshape(-1,2,width)
        left=mat[:,0,:].copy()
        right=mat[:,1,:].copy()
        mat[:,0,:]=(left+right)/sqrt(2)
        mat[:,1,:]=(left-right)/sqrt(2)
        width*=2


def reduced_state_probabilities(net: Network, truth: Truth,
                                excluded_cycles: set[tuple[int,...]],
                                M_parameter: int | None = None):
    N=net.size
    marked=np.fromiter((truth.cycle_of[i] in excluded_cycles for i in range(N)),
                       dtype=bool,count=N)
    exact_M=int(marked.sum())
    amps=np.full(N, 1/sqrt(N), dtype=np.complex128)
    if exact_M==N:
        raise ValueError('Cannot suppress all initial states')
    params=None
    if exact_M:
        params=suppression_parameters(exact_M if M_parameter is None else M_parameter,N)
        marked_phase=np.exp(-1j*params.phi)
        zero_phase=np.exp(1j*params.phi)
        for _ in range(params.J):
            amps[marked]*=marked_phase
            hadamard_inplace(amps)
            amps[0]*=zero_phase
            hadamard_inplace(amps)
    probs=np.abs(amps)**2
    # The final T maps every initial state to a periodic orbit state.
    final=np.arange(N)
    for _ in range(max(1,truth.max_transient)):
        final=np.take(truth.successors,final)
    outcomes=np.bincount(final,weights=probs,minlength=N)
    outcomes=outcomes/outcomes.sum()
    expected={}
    for cyc,sz in truth.basin_sizes.items():
        if cyc not in excluded_cycles:
            expected[cyc]=sz/(N-exact_M)
    return outcomes, params, exact_M, expected, float(probs[marked].sum())


def qpe_theoretical_distribution(M: int, N: int, precision: int):
    """Ideal QPE outcome distribution for a Grover 2D iterate (no circuit)."""
    if M<0 or M>N: raise ValueError('Invalid M')
    Q=1<<precision
    theta=asin(sqrt(M/N))
    w=theta/pi
    y=np.arange(Q)
    probs=np.zeros(Q)
    for eig in (w,(1-w)%1):
        delta=eig-y/Q
        numerator=np.sin(np.pi*Q*delta)
        denominator=Q*np.sin(np.pi*delta)
        r=np.ones(Q)
        np.divide(numerator,denominator,out=r,where=abs(denominator)>1e-12)
        probs+=0.5*r*r
    return probs/probs.sum()


def qpe_estimate(M: int,N: int,precision: int,shots: int,rng,*,return_phase_counts=False):
    """Modes over rounded M, combining conjugate QPE peaks."""
    dist=qpe_theoretical_distribution(M,N,precision)
    counts=rng.multinomial(shots,dist)
    histogram={}
    for y,ct in enumerate(counts):
        if ct:
            est=int(round(N*sin(pi*y/(1<<precision))**2))
            histogram[est]=histogram.get(est,0)+int(ct)
    estimate=min(histogram,key=lambda v:(-histogram[v],v))
    if return_phase_counts:
        return estimate,histogram,{f'{y:0{precision}b}':int(ct) for y,ct in enumerate(counts) if ct}
    return estimate,histogram


def measure_ideal(outcome_probabilities: np.ndarray, shots: int,
                  n: int, rng, readout_flip_probability: float=0.0):
    """Finite shots, optional *independent readout-bitflip proxy*, not QPU noise."""
    indices=np.flatnonzero(outcome_probabilities>1e-14)
    weights=outcome_probabilities[indices]
    samples=rng.choice(indices,size=shots,p=weights/weights.sum())
    if readout_flip_probability:
        for bit in range(n):
            flips=rng.random(shots)<readout_flip_probability
            samples[flips]^=1<<bit
    unique,count=np.unique(samples,return_counts=True)
    return {int(v):int(c) for v,c in zip(unique,count)}
