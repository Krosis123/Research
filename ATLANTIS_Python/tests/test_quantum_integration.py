import json
from dataclasses import replace
import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from atlantis.expressions import from_expressions
from atlantis.model import Network,TruthRule
from atlantis.states import all_states,random_states
from atlantis.io import network_from_dict,network_to_dict
from atlantis.analysis import deterministic_analysis
from atlantis.quantum.adapter import QuantumNetwork
from atlantis.quantum.engine import Settings,preflight,run
from atlantis.quantum.ross.model import exact_truth
from atlantis.quantum.ross.circuits import time_evolution,search_circuit,counting_circuit,qiskit_counts,qpe_counts_to_M
from atlantis.quantum.ross.reference import qpe_theoretical_distribution


def rossini():
    return from_expressions({'A':'A AND D','B':'A AND B','C':'C AND D','D':'B OR C'},'rossini4')


def test_rossini_basins_and_roundtrip():
    n=rossini();q=QuantumNetwork(network_from_dict(network_to_dict(n)));t=exact_truth(q)
    assert {q.as_bits(c[0]):v for c,v in t.basin_sizes.items()}=={'0000':11,'0011':2,'1011':1,'1101':1,'1111':1}
    assert t.max_transient==3


@pytest.mark.parametrize('expr',["__import__('os').system('whoami')",'a[0]','a.__class__','a + 1','[a]','2','1.0'])
def test_unsafe_expression(expr):
    with pytest.raises(ValueError):from_expressions({'a':expr})


def test_names_symbolic_high_fanin_mutation():
    rules={f'g{i}':f'g{i}' for i in range(15)};rules['g0']=' & '.join(rules)
    n=from_expressions(rules);q=QuantumNetwork(n)
    assert len(q.rules[0].anf_terms)==1
    assert n.mutate([('g1>g0',2)]).step(np.ones(15))[0,0]==0
    n=from_expressions({'p53-alpha':'NOT `p53-alpha` XOR `cell fate`','cell fate':'1'})
    assert n.step([[0,0]]).tolist()==[[1,1]]


@pytest.mark.parametrize('seed',range(8))
def test_random_weighted_reversible_evolution(seed):
    rng=np.random.default_rng(seed)
    n=Network(['x','y','z'],rng.integers(-2,3,(3,3)),rng.integers(-1,2,3))
    q=QuantumNetwork(n);evolution=time_evolution(q,1)
    for x in range(8):
        c=QuantumCircuit(6)
        for i in range(3):
            if x&(1<<i):c.x(i)
        c.compose(evolution,inplace=True)
        state=Statevector.from_instruction(c)
        assert np.argmax(abs(state.data))==x+(q.step(x)<<3)


def test_suppression_full_distribution():
    q=QuantumNetwork(rossini());excluded=['0000','0011','1011','1111']
    circuit,_=search_circuit(q,3,excluded,15)
    probs=Statevector.from_instruction(circuit.remove_final_measurements(inplace=False)).probabilities(qargs=list(range(12,16)))
    assert probs[13]==pytest.approx(1,abs=1e-12)
    assert np.sum(np.delete(probs,13))<1e-20


def test_actual_qpe_distribution():
    q=QuantumNetwork(from_expressions({'a':'a','b':'b'}))
    c=counting_circuit(q,1,['00'],3)
    actual=Statevector.from_instruction(c.remove_final_measurements(inplace=False)).probabilities(qargs=[0,1,2])
    np.testing.assert_allclose(actual,qpe_theoretical_distribution(1,4,3),atol=1e-12)
    counts,_=qiskit_counts(c,2048,seed=9)
    estimate,_=qpe_counts_to_M(counts,4,3)
    assert abs(estimate-1)<=1


def test_large_network_guard_and_classical():
    n=from_expressions({f'g{i}':'0' for i in range(150)})
    check=preflight(n,Settings(engine='aer'))
    assert not check['eligible'] and check['circuit_qubits']==600
    r=deterministic_analysis(n,random_states(150,10,42),3)
    assert len(r.attractors)==1 and not r.unresolved


@pytest.mark.parametrize('engine',['reduced','aer'])
def test_integrated_discovery(engine):
    result=run(rossini(),Settings(engine=engine,shots=64,max_rounds=6))
    assert result['status']=='complete_classically_certified'
    assert len(result['cycles'])==5
    assert any(h['kind']=='measurements' for h in result['history'])
    assert result['basin_sizes'] is None


def test_inadequate_T_inconclusive():
    r=run(rossini(),Settings(T=1,max_rounds=1,shots=1,stop_policy='bounded'))
    assert r['status'].startswith('inconclusive')


def test_ibm_mock_secret_safety_and_confirmation():
    from atlantis.quantum.ibm import IBMAccount
    calls=[]
    def service_factory(**kwargs):calls.append(kwargs);return object()
    a=IBMAccount();a.connect('dummy-test-secret','dummy-instance',service_factory)
    assert calls[0]['channel']=='ibm_quantum_platform'
    with pytest.raises(PermissionError):a.submit((None,None,{}))
    def bad(**kwargs):raise RuntimeError(kwargs['token'])
    with pytest.raises(RuntimeError) as error:a.connect('dummy-secret-never-echo','x',bad)
    assert 'dummy-secret' not in str(error.value)
    a.disconnect()
    with pytest.raises(ValueError):a.service()


def test_job_process_persistence(tmp_path):
    from atlantis.experiments import execute,JobStore
    store=JobStore(tmp_path/'jobs.sqlite')
    result=execute(rossini(),Settings(shots=32),store=store)
    row=store.list()[0]
    assert row['status']=='finished' and json.loads(row['result'])['job_id']==result['job_id']


def test_quantum_dialog(qtapp):
    from atlantis.gui import Application
    w=Application();w.set_network(rossini());w.quantum_analysis();qtapp.processEvents()
    d=w.dialogs[-1];assert d.check()['eligible']
    assert d.grab().save('validation/quantum-dialog.png')
    w.close()


def test_five_gene_both_suppression_orders():
    from atlantis.io import load_network
    from atlantis.quantum.ross.adaptive import terminal_states,reduced_probabilities
    q=QuantumNetwork(load_network('examples/quantum/giacomantonio5.json'));truth=exact_truth(q)
    assert sorted(truth.basin_sizes.values())==[4,28] and truth.max_transient==4
    terminal=terminal_states(q,4)
    for cycle,M in truth.basin_sizes.items():
        p,_,leak=reduced_probabilities(q,terminal,{cycle},M)
        assert leak<1e-25 and p[cycle[0]]<1e-25
        c,_=search_circuit(q,4,[q.as_bits(x) for x in cycle],M)
        counts,_=qiskit_counts(c,64,method='matrix_product_state',seed=8)
        assert q.as_bits(cycle[0]) not in counts


def test_true_counting_does_not_enumerate(monkeypatch):
    from atlantis.quantum.ross import adaptive
    def forbidden(*a,**kw):raise AssertionError('Classical full state enumeration leaked into QPE search')
    monkeypatch.setattr(adaptive,'terminal_states',forbidden)
    r=run(from_expressions({'a':'a'}),Settings(T=1,engine='aer',counting_mode='qpe_aer',
        counting_precision=2,stop_policy='qpe',shots=32,max_rounds=3))
    assert r['status']=='complete_qpe_heuristic' and len(r['cycles'])==2


def test_cancellation_and_restart(tmp_path):
    from atlantis.experiments import JobStore,execute
    from atlantis.analysis import CancelledError
    store=JobStore(tmp_path/'jobs.sqlite')
    with pytest.raises(CancelledError):execute(rossini(),Settings(),cancel=lambda:True,store=store)
    assert store.list()[0]['status']=='cancelled'
    identity=store.create(rossini(),Settings())
    store.recover()
    assert next(r for r in store.list() if r['id']==identity)['status']=='interrupted'


def test_mock_ibm_runtime_submission_and_retrieval():
    from types import SimpleNamespace
    from atlantis.quantum.ibm import IBMAccount
    calls=[]
    class Job:
        def job_id(self):return 'mock-job'
        def status(self):return 'DONE'
        def cancel(self):return True
        def result(self):return [SimpleNamespace(join_data=lambda:SimpleNamespace(get_counts=lambda:{'0':32}))]
    class Sampler:
        def __init__(self,**kwargs):calls.append(kwargs)
        def run(self,pubs,shots):calls.append((pubs,shots));return Job()
    service=SimpleNamespace(job=lambda _:Job())
    a=IBMAccount();a.connect('mock-key','mock-crn',lambda **_:service)
    identity=a.submit(('mock-backend',QuantumCircuit(1),{'shots':32}),confirmed=True,sampler_factory=Sampler)
    assert identity=='mock-job' and a.status(identity)=='DONE' and a.result(identity)=={'0':32}
    assert a.cancel(identity) and calls[0]['options']['max_execution_time']==60


def test_gui_quantum_end_to_end(qtapp,monkeypatch,tmp_path):
    import time
    from PySide6 import QtWidgets as W
    from atlantis.gui import Application
    from atlantis.experiments import JobStore
    import atlantis.quantum_ui as ui
    from atlantis.experiments import execute
    store=JobStore(tmp_path/'gui-jobs.sqlite')
    monkeypatch.setattr(ui,'execute',lambda net,s,progress,cancel:execute(net,s,progress,cancel,store))
    failures=[];monkeypatch.setattr(W.QMessageBox,'warning',lambda *a:failures.append(a[-1]))
    w=Application();w.set_network(rossini());w.quantum_analysis();d=w.dialogs[-1]
    d.engine.setCurrentText('aer');d.launch()
    deadline=time.monotonic()+40
    while w.job.isRunning() and time.monotonic()<deadline:qtapp.processEvents();time.sleep(.01)
    qtapp.processEvents()
    assert not w.job.isRunning() and not failures and len(d.result['cycles'])==5
    d.compare();assert 'classical_unresolved' in d.output.toPlainText()
    path=tmp_path/'export.json'
    monkeypatch.setattr(W.QFileDialog,'getSaveFileName',lambda *a,**k:(str(path),''))
    d.export();assert json.loads(path.read_text())['taxonomy']=='actual quantum circuit simulation'
    d.plot();assert w.windows
    w.close()


def test_clamps_and_weighted_probability_rejection():
    from atlantis.analysis import transition_probabilities
    n=from_expressions({'a':'NOT b','b':'a'});n.clamped={'b':1}
    q=QuantumNetwork(n)
    for x in range(4):
        expected=n.step([[x>>1,x&1]])[0]
        assert q.step(x)==int(''.join(map(str,expected)),2)
    w=Network(['a'],[[0]],clamped={'a':1})
    with pytest.raises(ValueError):transition_probabilities(w,all_states(1))


def test_cycle_order_and_unresolved_basin_mass():
    # 00 -> 10 -> 01 -> 00, and 11 is fixed: lexicographic sorting destroys order.
    n=Network(['a','b'],rules=[TruthRule([0,1],[1,0,0,1]),TruthRule([0,1],[0,0,1,1])])
    d=deterministic_analysis(n,all_states(2),10)
    cycle=next(a.states for a in d.attractors if len(a.states)==3)
    np.testing.assert_array_equal(n.step(cycle),np.roll(cycle,-1,axis=0))
    partial=deterministic_analysis(n,all_states(2),1)
    assert partial.unresolved==3 and partial.attractors[0].basin==.25


def test_path_traversal_export_rejected(tmp_path):
    from atlantis.io import save_rules
    n=Network(['../escape'],rules=[TruthRule([],[1])])
    with pytest.raises(ValueError):save_rules(n,tmp_path)
    assert not (tmp_path.parent/'escape.txt').exists()

def test_permuted_boolean_evolution_and_inverse_against_aer():
    expressions = {'Z': '(X & Y) | (~X & Z)', 'X': '~X', 'Y': 'Y ^ Z'}
    for names in (['Z', 'X', 'Y'], ['Y', 'Z', 'X']):
        network = QuantumNetwork(from_expressions({name: expressions[name] for name in names}))
        evolution = time_evolution(network, 1)
        for bits in range(8):
            z, x, y = (dict(zip(names, map(int, f'{bits:03b}')))[k] for k in 'ZXY')
            values = {'Z': y if x else z, 'X': 1-x, 'Y': y ^ z}
            expected = int(''.join(str(values[k]) for k in names), 2)
            circuit = QuantumCircuit(6, 6)
            for qubit in range(3):
                if bits & (1 << qubit):
                    circuit.x(qubit)
            circuit.compose(evolution, inplace=True)
            recovered = circuit.compose(evolution.inverse())
            circuit.measure(range(6), range(6))
            recovered.measure(range(6), range(6))
            assert qiskit_counts(circuit, 16, seed=13)[0] == {f'{(expected << 3) | bits:06b}': 16}
            assert qiskit_counts(recovered, 16, seed=13)[0] == {f'{bits:06b}': 16}

def test_ibm_fake_backend_transpile_and_local_runtime():
    from types import SimpleNamespace
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2
    from atlantis.quantum.ibm import IBMAccount

    backend = FakeManilaV2()
    def connect(**kwargs):
        assert kwargs == dict(channel='ibm_quantum_platform', token='fixture-key', instance='fixture-crn')
        return SimpleNamespace(backend=lambda name: backend,
                               backends=lambda **filters: [backend])

    account = IBMAccount()
    with pytest.raises(ValueError, match='API key'):
        account.connect('', '', connect)
    account.connect('fixture-key', 'fixture-crn', connect)
    assert account.backends() == [{'name': backend.name, 'qubits': backend.num_qubits}]
    circuit = QuantumCircuit(1, 1)
    circuit.measure(0, 0)
    prepared = account.prepare(circuit, backend.name, shots=32)
    jobs = {}

    def local_sampler(**kwargs):
        from qiskit_ibm_runtime.executor_sampler import Sampler
        sampler = Sampler(**kwargs)
        def run(pubs, *, shots):
            job = sampler.run(pubs, shots=shots)
            jobs[job.job_id()] = job
            return job
        return SimpleNamespace(run=run)

    account.service().job = jobs.__getitem__
    job_id = account.submit(prepared, confirmed=True, sampler_factory=local_sampler)
    assert sum(account.result(job_id).values()) == 32
    assert 'DONE' in account.status(job_id)

def test_rossini_supplementary_basis_phase_operator():
    from qiskit.quantum_info import Operator
    from atlantis.quantum.ross.circuits import phase_basis_state

    for value in range(16):
        circuit = QuantumCircuit(4)
        phase_basis_state(circuit, [3, 2, 1, 0], f'{value:04b}', .37)
        expected = np.ones(16, dtype=complex)
        expected[value] = np.exp(.37j)
        np.testing.assert_allclose(Operator(circuit).data, np.diag(expected), atol=1e-12)


def test_rossini_supplementary_cycle_suppression_aer():
    rules = {'x0':'x0 & x2', 'x1':'~x0 & x1', 'x2':'~x1', 'x3':'~x2 & ~x3'}
    model = QuantumNetwork(from_expressions(rules))

    def independent_step(bits):
        a,b,c,d = map(int,bits)
        return f'{a&c}{(1-a)&b}{1-b}{(1-c)&(1-d)}'

    terminal = []
    for state in range(16):
        bits = f'{state:04b}'
        for _ in range(4):
            bits = independent_step(bits)
        terminal.append(bits)
    assert set(terminal) == {'0010', '0100', '0101', '1010'}
    marked = ['0010', '0100', '0101']
    count = sum(s in marked for s in terminal)
    circuit, _ = search_circuit(model, 4, marked, count)
    counts, _ = qiskit_counts(circuit, 128, method='matrix_product_state', seed=13)
    assert counts == {'1010':128}
