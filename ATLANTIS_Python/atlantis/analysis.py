"""Ports of deterministicEngine_*, transition probabilities, and master equation."""
from dataclasses import dataclass, field
from collections import Counter
import numpy as np
from .model import boolean_states


class CancelledError(RuntimeError): pass


def checkpoint(progress, cancel, fraction, message):
    if cancel and cancel(): raise CancelledError('Analysis cancelled')
    if progress: progress(float(fraction),message)


@dataclass
class Attractor:
    states: np.ndarray
    basin: float
    fate: str = ''
    @property
    def kind(self): return 'Point' if len(self.states)==1 else 'Cyclic'
    @property
    def average(self): return self.states.mean(axis=0)
    @property
    def stratified(self):
        a=self.average
        return np.where(a < .2,0,np.where(a > .8,1,2)).astype(np.uint8)


@dataclass
class DeterministicResult:
    initial_states: np.ndarray
    attractors: list[Attractor]
    assignments: np.ndarray
    unresolved: int
    search_duration: int
    fate_propensities: dict = field(default_factory=dict)

    @property
    def coverage(self):
        unique=len(np.unique(self.initial_states,axis=0))
        return {'taxonomy':'exact classical result' if unique==2**self.initial_states.shape[1] and not self.unresolved else 'sampled or bounded classical result',
                'initial_state_count':len(self.initial_states),'unique_initial_states':unique,
                'unresolved':self.unresolved,'distribution':'empirical input rows; duplicates count as repeated observations'}


@dataclass
class ProbabilisticResult:
    states: np.ndarray
    transition: np.ndarray
    probabilities: np.ndarray
    iterations: int
    converged: bool
    noise: float
    degradation: float
    error: float
    pruned: bool
    fates: list[str] = field(default_factory=list)
    trajectory: np.ndarray | None = None

    @property
    def flux_residual_inf(self):
        """Maximum one-step change under the historical probability update."""
        p = self.probabilities
        residual = self.transition.T @ p - p * self.transition.sum(axis=1)
        return float(np.max(np.abs(residual)))


def preliminary_search(network, states, progress=None, cancel=None):
    s=states.copy(); previous=0; similar=0
    for k in range(network.n):
        checkpoint(progress,cancel,.2*(k+1)/network.n,'Preliminary synchronous search')
        s=network.step(s)
        count=np.unique(s,axis=0).size  # MATLAB numel(unique(...,'rows'))
        similar=similar+1 if previous==count else 0
        previous=count
        if similar>=5: break
    return s


def find_cycle(network, state, duration):
    current=state.copy(); visited={}; trajectory=[]
    for name, value in network.clamped.items():
        current[network.names.index(name)] = value
    for step in range(duration):
        visited[current.tobytes()]=step; trajectory.append(current.copy())
        nxt=network.step(current)[0]
        index=visited.get(nxt.tobytes())
        if index is not None: return np.array(trajectory[index:],dtype=np.uint8)
        current=nxt
    return None


def deterministic_analysis(network, states, search_duration=1000, fate_logic=None, progress=None, cancel=None, historical=False):
    initial=boolean_states(states,network.n)
    if not len(initial) or int(search_duration)!=search_duration or search_duration<1:
        raise ValueError('Nonempty initial states and positive integer search duration required')
    for name, value in network.clamped.items():
        initial[:, network.names.index(name)] = value
    start=preliminary_search(network,initial,progress,cancel) if network.weights is not None else initial
    candidates,inverse,counts=np.unique(start,axis=0,return_inverse=True,return_counts=True)
    keys={}; cycles=[]; sizes=[]; candidate_labels=np.full(len(candidates),-1,dtype=int)
    # Source confirms each distinct candidate. No approximate search or cycle truncation.
    for i,state in enumerate(candidates):
        checkpoint(progress,cancel,.2+.8*i/len(candidates),'Confirming attractors')
        cycle=find_cycle(network,state,int(search_duration))
        if cycle is None: continue
        key=tuple(sorted(row.tobytes() for row in cycle))
        if key not in keys:
            keys[key]=len(cycles)
            # Rules engine sorts rows before its unique-cell table construction.
            if historical and network.rules is not None:
                cycle=np.array(sorted(cycle.tolist()),dtype=np.uint8)
            else:
                first=min(range(len(cycle)),key=lambda j:tuple(cycle[j]))
                cycle=np.concatenate((cycle[first:],cycle[:first]))
            cycles.append(cycle); sizes.append(0)
        label=keys[key]; candidate_labels[i]=label; sizes[label]+=int(counts[i])
    labels=candidate_labels[inverse]
    unresolved=int(np.sum(labels<0))
    # Rules source drops unresolved trajectories before attractorFrequency.
    denominator=len(initial) if not historical or network.weights is not None else len(initial)-unresolved
    attrs=[Attractor(c,s/denominator) for c,s in zip(cycles,sizes)] if denominator else []
    order=sorted(range(len(attrs)),key=lambda j:(attrs[j].basin,tuple(attrs[j].states.flatten())),reverse=True)
    remap={old:new for new,old in enumerate(order)}
    labels=np.array([remap.get(int(v),-1) for v in labels])
    attrs=[attrs[j] for j in order]
    fates={}
    if fate_logic:
        for attr in attrs:
            attr.fate=fate_logic.associate(attr.stratified)
            fates[attr.fate]=fates.get(attr.fate,0)+attr.basin
        fates=dict(sorted(fates.items(),key=lambda kv:kv[1],reverse=True))
    checkpoint(progress,cancel,1,'Deterministic analysis complete')
    return DeterministicResult(initial.copy(),attrs,labels,unresolved,int(search_duration),fates)


def state_space_pruning(network, states):
    return np.unique(network.step(states),axis=0)


def transition_probabilities(network, states, noise=5., degradation=.001, progress=None, cancel=None, max_bytes=1024**3):
    if network.weights is None: raise ValueError('Original ATLANTIS supports probabilistic analysis only for weighted networks')
    if network.clamped: raise ValueError('Historical probabilistic model does not define hard clamps; use explicit historical basal perturbations')
    if not np.isfinite(noise) or noise<0 or not 0<=degradation<=1:
        raise ValueError('Noise must be finite and nonnegative; degradation must be in [0,1]')
    s=boolean_states(states,network.n)
    if not len(s): raise ValueError('State space is empty')
    if len(s)**2*8>max_bytes: raise MemoryError('Exact transition matrix exceeds configured memory limit. Choose fewer states or pruning explicitly.')
    total=s@network.weights+network.basal
    p=.5+.5*np.tanh(noise*total)
    zero=total==0
    p[zero]=np.where(s==0,degradation,1-degradation)[zero]
    t=np.empty((len(s),len(s)),dtype=float)
    for i,on in enumerate(p):
        checkpoint(progress,cancel,i/len(s),'State transition probabilities')
        t[i]=np.prod(np.where(s==1,on,1-on),axis=1)
    return t


def steady_state_probabilities(transition, max_steps=1000, error=1e-8, progress=None, cancel=None):
    t=np.asarray(transition,dtype=float)
    if t.ndim!=2 or t.shape[0]!=t.shape[1] or not len(t) or not np.isfinite(t).all() or (t<0).any():
        raise ValueError('Transition matrix must be finite, nonnegative, nonempty, and square')
    if max_steps<1 or error<0 or not np.isfinite(error): raise ValueError('Invalid master-equation settings')
    p=np.full(len(t),1/len(t))
    row_sums=t.sum(axis=1)
    if np.any(row_sums>1+1e-12): raise ValueError('Transition rows must sum to at most one')
    for iteration in range(1,max_steps+1):
        checkpoint(progress,cancel,iteration/max_steps,'Master equation')
        # Same flux equation, including lost transitions in a subset/pruned state space.
        updated=p-p*row_sums+t.T@p
        converged=np.mean(np.abs(p-updated)<=error)>=.98 and iteration>10 and np.all(p>=0)
        if converged: return updated,iteration,True
        p=updated
    return updated,max_steps,False


def probabilistic_analysis(network, states, noise=5., degradation=.001, max_steps=1000, error=1e-8, prune=False, fate_logic=None, progress=None, cancel=None):
    s=boolean_states(states,network.n)
    if prune: s=state_space_pruning(network,s)
    t=transition_probabilities(network,s,noise,degradation,
        (lambda f,m: progress(.5*f,m)) if progress else None,cancel)
    p,it,conv=steady_state_probabilities(t,max_steps,error,
        (lambda f,m: progress(.5+.5*f,m)) if progress else None,cancel)
    fates=[fate_logic.associate(row) for row in s] if fate_logic else []
    return ProbabilisticResult(s,t,p,it,conv,noise,degradation,error,prune,fates)


def map_trajectory(result, bounds):
    """Original map_Trajectory: contiguous probability-ranked states between bounds."""
    b=boolean_states(bounds,result.states.shape[1])
    if len(b)!=2: raise ValueError('Trajectory bounds must have exactly two rows')
    order=np.argsort(result.probabilities,kind='stable')[::-1]
    ranked=result.states[order]
    positions=[]
    for row in b:
        match=np.flatnonzero(np.all(ranked==row,axis=1))
        if not len(match): raise ValueError('Trajectory bound is not in the analyzed state space')
        positions.append(int(match[0]))
    lo,hi=sorted(positions)
    result.trajectory=order[lo:hi+1]
    return result.trajectory
