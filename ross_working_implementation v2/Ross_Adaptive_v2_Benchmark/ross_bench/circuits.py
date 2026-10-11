"""Actual Qiskit/Aer construction of Rossini evolution, suppression and QPE.

Qiskit is deliberately imported only inside functions so truth/reference benchmarks
work on machines where qiskit-aer is unavailable.
"""
from __future__ import annotations
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
    zeros=[q for q,b in zip(qubits,bits) if b=='0']
    for q in zeros: qc.x(q)
    if len(qubits)==1: qc.p(angle,qubits[0])
    else: qc.mcp(angle,qubits[:-1],qubits[-1])
    for q in reversed(zeros): qc.x(q)


def append_update(qc, net: Network, step: int):
    """Exact reversible embedding (x,0)->(x,F(x)) using each rule's ANF."""
    for i,rule in enumerate(net.rules):
        target=gene_qubit(net,step+1,i)
        for term in rule.anf_terms:
            controls=[gene_qubit(net,step,rule.inputs[j])
                      for j in range(len(rule.inputs)) if term & (1<<j)]
            if not controls: qc.x(target)
            elif len(controls)==1: qc.cx(controls[0],target)
            elif len(controls)==2: qc.ccx(controls[0],controls[1],target)
            else: qc.mcx(controls,target)


def time_evolution(net: Network,T: int):
    QC,_,_=_require_qiskit()
    if T<1: raise ValueError('T must be >=1')
    qc=QC((T+1)*net.n,name=f'T{T}')
    for t in range(T): append_update(qc,net,t)
    return qc


def search_circuit(net: Network, T: int, excluded_states: list[str], M: int):
    """Full (T+1)n-qubit search run; M must come from documented counting mode."""
    QC,_,_=_require_qiskit()
    forward=time_evolution(net,T)
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
    try:
        from qiskit.circuit.library import QFTGate
    except ImportError:
        from qiskit.circuit.library import QFT
        QFTGate=None
    evolve=time_evolution(net,T)
    U=evolve.to_gate(label='T')
    system_qubits=evolve.num_qubits
    oracle=QC(system_qubits,name='BasinOracle')
    oracle.append(U,list(range(system_qubits)))
    last=[gene_qubit(net,T,i) for i in range(net.n)]
    for bits in excluded_states: phase_basis_state(oracle,last,bits,pi)
    oracle.append(U.inverse(),list(range(system_qubits)))
    grover=QC(system_qubits,name='G')
    grover.compose(oracle,inplace=True)
    first=[gene_qubit(net,0,i) for i in range(net.n)]
    for q in first: grover.h(q)
    phase_basis_state(grover,first,'0'*net.n,pi)
    for q in first: grover.h(q)
    grover.global_phase+=pi
    g=grover.to_gate(label='Grover').control(1)
    total=precision+system_qubits
    qc=QC(total,precision)
    controls=list(range(precision));system=list(range(precision,total))
    for c in controls: qc.h(c)
    for q in first: qc.h(precision+q)
    for j,control in enumerate(controls):
        for _ in range(1<<j): qc.append(g,[control]+system)
    if QFTGate is not None: qc.append(QFTGate(precision).inverse(),controls)
    else: qc.compose(QFT(precision,inverse=True,do_swaps=True),qubits=controls,inplace=True)
    qc.measure(controls,controls)
    return qc


def qiskit_counts(qc, shots:int, method='statevector',optimization_level=0,seed=0):
    QC,transpile,AerSimulator=_require_qiskit()
    backend=AerSimulator(method=method)
    compiled=transpile(qc,backend,optimization_level=optimization_level,seed_transpiler=seed)
    result=backend.run(compiled,shots=shots,seed_simulator=seed).result()
    return result.get_counts(),{
        'compiled_depth':compiled.depth(),
        'compiled_size':compiled.size(),
        'compiled_2q_count':sum(count for gate,count in compiled.count_ops().items() if gate in ('cx','cz','ecr','swap','rxx','rzz')),
        'raw_depth':qc.depth(),
        'raw_size':qc.size(),
        'physical_qubits':qc.num_qubits,
    }


def qpe_counts_to_M(counts:dict[str,int],N:int,precision:int):
    from math import sin
    histogram={}
    for bits,cnt in counts.items():
        y=int(bits.replace(' ',''),2)
        m=round(N*sin(pi*y/(1<<precision))**2)
        histogram[m]=histogram.get(m,0)+cnt
    return max(histogram,key=histogram.get),histogram
