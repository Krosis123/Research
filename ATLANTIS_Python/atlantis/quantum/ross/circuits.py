"""Actual Qiskit/Aer construction of Rossini evolution, suppression and QPE.

Qiskit is deliberately imported only inside functions so truth/reference benchmarks
work on machines where qiskit-aer is unavailable.
"""
from __future__ import annotations
from functools import lru_cache
from math import pi
from .model import Network
from .reference import suppression_parameters


def _require_qiskit():
    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit_aer import AerSimulator
    except ImportError as e:
        raise RuntimeError('Install requirements-qiskit.txt on your machine for the real Qiskit benchmark') from e
    return QuantumCircuit,transpile,AerSimulator


def gene_qubit(net: Network, step: int, gene_index: int):
    return step*net.n+(net.n-1-gene_index)


def phase_basis_state(qc, qubits: list[int], bits: str, angle: float):
    """Apply e^(i angle) to exactly one gene-order computational basis vector."""
    if not qubits or len(bits)!=len(qubits) or set(bits)-{'0','1'}:
        raise ValueError('Phase target must be a binary string matching the register width')
    zeros=[q for q,b in zip(qubits,bits) if b=='0']
    for q in zeros: qc.x(q)
    if len(qubits)==1: qc.p(angle,qubits[0])
    elif angle == pi and len(qubits) >= 7 and qc.num_qubits >= 2*len(qubits)-3:
        # H-MCX-H is the exact multi-controlled sign flip. Borrow evolution
        # wires in arbitrary states and restore them before the next operation.
        from qiskit.synthesis import synth_mcx_n_dirty_i15
        dirty = [q for q in range(qc.num_qubits) if q not in qubits][:len(qubits)-3]
        qc.h(qubits[-1])
        qc.compose(synth_mcx_n_dirty_i15(len(qubits)-1), qubits + dirty, inplace=True)
        qc.h(qubits[-1])
    else: qc.mcp(angle,qubits[:-1],qubits[-1])
    for q in reversed(zeros): qc.x(q)


@lru_cache(maxsize=2048)
def _single_cube(terms):
    """Recognize a conjunction of signed literals or its complement from ANF."""
    if len(terms) < 2:
        return None
    masks = set(terms)
    for complement in (False, True):
        candidate = masks ^ {0} if complement else masks
        if not candidate:
            continue
        high = max(candidate)
        low = high
        for mask in candidate:
            low &= mask
        free = high ^ low
        if (all(mask & ~high == 0 for mask in candidate)
                and len(candidate) == 1 << free.bit_count()):
            return high, free, complement
    return None


def _toggle(qc, controls, target, relative):
    if not controls:
        qc.x(target)
    elif len(controls) == 1:
        qc.cx(controls[0], target)
    elif len(controls) == 2:
        (qc.rccx if relative else qc.ccx)(*controls, target)
    elif relative and len(controls) == 3:
        qc.rcccx(*controls, target)
    else:
        qc.mcx(controls, target)


def append_update(qc, net: Network, step: int, *, relative=False):
    """Embed the Boolean update. Relative phases are opt-in for paired or measured use."""
    for i, rule in enumerate(net.rules):
        target = gene_qubit(net, step + 1, i)
        wires = [gene_qubit(net, step, source) for source in rule.inputs]
        cube = _single_cube(tuple(rule.anf_terms))
        terms = rule.anf_terms
        inverted = []
        if cube is not None:
            support, negatives, complement = cube
            inverted = [q for j, q in enumerate(wires) if negatives & (1 << j)]
            terms = (support,)
            if complement:
                qc.x(target)
        for q in inverted:
            qc.x(q)
        for term in terms:
            controls = [q for j, q in enumerate(wires) if term & (1 << j)]
            _toggle(qc, controls, target, relative)
        for q in inverted:
            qc.x(q)


def time_evolution(net: Network,T: int, *, relative=False):
    QC,_,_=_require_qiskit()
    if type(T) is not int or T<1: raise ValueError('T must be a positive integer')
    qc=QC((T+1)*net.n,name=f'T{T}')
    for t in range(T): append_update(qc,net,t,relative=relative)
    return qc


def search_circuit(net: Network, T: int, excluded_states: list[str], M: int):
    """Full (T+1)n-qubit search run; M must come from documented counting mode."""
    QC,_,_=_require_qiskit()
    if len(set(excluded_states))!=len(excluded_states):
        raise ValueError('Excluded terminal states must be unique')
    forward=time_evolution(net,T,relative=True)
    U=forward.to_gate(label='T')
    total=forward.num_qubits
    qc=QC(total,net.n)
    first=[gene_qubit(net,0,i) for i in range(net.n)]
    last=[gene_qubit(net,T,i) for i in range(net.n)]
    for q in first: qc.h(q)
    params=None
    if excluded_states:
        params=suppression_parameters(M,net.size)
        for _ in range(params.J):
            qc.append(U,list(range(total)))
            for bits in excluded_states: phase_basis_state(qc,last,bits,-params.phi)
            qc.append(U.inverse(),list(range(total)))
            for q in first: qc.h(q)
            phase_basis_state(qc,first,'0'*net.n,params.phi)
            for q in first: qc.h(q)
    qc.append(U,list(range(total)))
    for i in range(net.n):
        qc.measure(gene_qubit(net,T,i),net.n-1-i)
    return qc,params


def counting_circuit(net: Network,T: int,excluded_states: list[str],precision: int):
    """Actual QPE/Grover quantum basin count (very costly for large n,T,p)."""
    QC,_,_=_require_qiskit()
    if type(precision) is not int or not 1<=precision<=10:
        raise ValueError('QPE precision must be an integer from 1 to 10')
    if len(set(excluded_states))!=len(excluded_states):
        raise ValueError('Excluded terminal states must be unique')
    try:
        from qiskit.circuit.library import QFTGate
    except ImportError:
        from qiskit.circuit.library import QFT
        QFTGate=None
    evolve = time_evolution(net, T, relative=True)
    U = evolve.to_gate(label='T')
    system = list(range(precision, precision + evolve.num_qubits))
    qc = QC(precision + evolve.num_qubits, precision)
    first = [precision + gene_qubit(net, 0, i) for i in range(net.n)]
    last = [precision + gene_qubit(net, T, i) for i in range(net.n)]
    controls = list(range(precision))
    qc.h(controls + first)
    for j, control in enumerate(controls):
        # When control=0, each unconditional conjugation cancels exactly.
        for _ in range(1 << j):
            qc.append(U, system)
            for bits in excluded_states:
                if len(bits) != net.n:
                    raise ValueError('Phase target must match register width')
                phase_basis_state(qc, [control] + last, '1' + bits, pi)
            qc.append(U.inverse(), system)
            qc.h(first)
            phase_basis_state(qc, [control] + first, '1' + '0' * net.n, pi)
            qc.h(first)
            qc.z(control)  # controlled global minus sign of the diffuser
    if QFTGate is not None: qc.append(QFTGate(precision).inverse(),controls)
    else: qc.compose(QFT(precision,inverse=True,do_swaps=True),qubits=controls,inplace=True)
    qc.measure(controls,controls)
    return qc


def qiskit_counts(qc, shots:int, method='statevector',optimization_level=0,seed=0,
                  max_depth=200000,max_gates=500000,max_memory_mb=1024,noise_probability=0.0):
    QC,transpile,AerSimulator=_require_qiskit()
    noise=None
    if noise_probability:
        from qiskit_aer.noise import NoiseModel, depolarizing_error
        noise=NoiseModel()
        noise.add_all_qubit_quantum_error(depolarizing_error(noise_probability,1),['u'])
        noise.add_all_qubit_quantum_error(depolarizing_error(noise_probability,2),['cx'])
    backend=AerSimulator(method=method,max_memory_mb=max_memory_mb,noise_model=noise,max_parallel_threads=2)
    from time import perf_counter
    start=perf_counter()
    compiled=transpile(qc,basis_gates=['u','cx'],optimization_level=optimization_level,seed_transpiler=seed)
    transpilation_s=perf_counter()-start
    if compiled.depth()>max_depth or compiled.size()>max_gates:
        raise ValueError('Transpiled depth/gate budget exceeded')
    start=perf_counter()
    result=backend.run(compiled,shots=shots,seed_simulator=seed).result()
    if not result.success: raise RuntimeError('Aer execution failed')
    return result.get_counts(),{
        'compiled_depth':compiled.depth(),
        'compiled_size':compiled.size(),
        'compiled_1q_count':sum(len(item.qubits)==1 and item.operation.name not in ('measure','barrier')
                                 for item in compiled.data),
        'compiled_2q_count':sum(len(item.qubits)==2 for item in compiled.data),
        'raw_depth':qc.depth(),
        'raw_size':qc.size(),
        'logical_qubits':qc.num_qubits,
        'transpiled_qubits':compiled.num_qubits,
        'logical_ancillas':qc.num_ancillas,
        'transpiled_ancillas':compiled.num_ancillas,
        'transpilation_s':transpilation_s,
        'execution_s':perf_counter()-start,
    }


def qpe_counts_to_M(counts:dict[str,int],N:int,precision:int):
    from math import sin
    histogram={}
    for bits,cnt in counts.items():
        y=int(bits.replace(' ',''),2)
        m=round(N*sin(pi*y/(1<<precision))**2)
        histogram[m]=histogram.get(m,0)+cnt
    return max(histogram,key=histogram.get),histogram
