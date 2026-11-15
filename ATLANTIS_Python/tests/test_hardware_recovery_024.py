"""Exercise durable provider status handling without connecting to IBM."""
from contextlib import closing
from types import SimpleNamespace

import pytest

from atlantis.analysis import CancelledError
from atlantis.experiments import JobStore
from atlantis.expressions import from_expressions
from atlantis.quantum.engine import Settings, preflight
from atlantis.quantum import hardware
from atlantis.quantum.hardware import ProviderWaitExpired, run_hardware


@pytest.mark.parametrize('mode,expected_job,expected_provider,exception',[
    ('ERROR','failed','error',RuntimeError),
    ('CANCELLED','cancelled','cancelled',CancelledError),
    ('RUNNING','cancelled','cancel_requested',CancelledError),
    ('unknown','failed','submitting_outcome_unknown',RuntimeError),
])
def test_durable_provider_terminal_and_uncertain_states(tmp_path,mode,expected_job,expected_provider,exception):
    events=[]
    def submit(*args,**kwargs):
        events.append('submit')
        if mode=='unknown':
            raise RuntimeError('Provider acknowledgement lost')
        return 'offline-provider-id'
    account=SimpleNamespace(prepare=lambda *args:(None,args[0],{}),submit=submit,
                            status=lambda _:mode,cancel=lambda _:events.append('cancel'))
    store=JobStore(tmp_path/'provider.sqlite')
    settings=Settings(T=1,engine='ibm',counting_mode='qpe_aer',stop_policy='qpe')
    network=from_expressions({'input_node':'input_node'})
    with pytest.raises(exception):
        run_hardware(network,settings,account,'offline',confirmed=True,store=store,
                     cancel=lambda:mode=='RUNNING' and bool(events))
    assert events==(['submit','cancel'] if mode=='RUNNING' else ['submit'])
    assert store.list()[0]['status']==expected_job
    with closing(store.connect()) as connection:
        status,job_id=connection.execute('SELECT status,provider_id FROM provider_jobs').fetchone()
    assert status==expected_provider
    assert job_id==(None if mode=='unknown' else 'offline-provider-id')


def test_local_wait_expiry_preserves_pending_provider_job(tmp_path, monkeypatch):
    times = iter([0, 2])
    monkeypatch.setattr(hardware, 'monotonic', lambda: next(times))
    account = SimpleNamespace(
        prepare=lambda *args: (None, args[0], {}),
        submit=lambda *args, **kwargs: 'pending-job',
        status=lambda _: 'QUEUED',
        cancel=lambda _: pytest.fail('Local wait expiry must leave the IBM job queued'),
    )
    store = JobStore(tmp_path/'provider.sqlite')
    settings = Settings(T=1, engine='ibm', counting_mode='qpe_aer',
                        stop_policy='qpe', timeout_seconds=1)
    network = from_expressions({'input_node': 'input_node'})
    with pytest.raises(ProviderWaitExpired, match='pending-job'):
        run_hardware(network, settings, account, 'offline', confirmed=True, store=store)
    assert store.list()[0]['status'] == 'provider_wait_expired'
    with closing(store.connect()) as connection:
        assert connection.execute('SELECT status,provider_id FROM provider_jobs').fetchone() == (
            'queued', 'pending-job',
        )


def test_invalid_evolution_horizon_is_rejected_before_execution():
    network=from_expressions({'input_node':'input_node'})
    assessment=preflight(network,Settings(T=0,engine='aer'))
    assert not assessment['eligible']
    assert any(reason.startswith('T ') for reason in assessment['reasons'])

def test_invalid_counting_masks_rejected():
    from atlantis.quantum.adapter import QuantumNetwork
    from atlantis.quantum.ross.circuits import counting_circuit,search_circuit
    network=QuantumNetwork(from_expressions({'input_node':'input_node'}))
    with pytest.raises(ValueError,match='unique'):
        counting_circuit(network,1,['0','0'],2)
    with pytest.raises(ValueError,match='precision'):
        counting_circuit(network,1,['0'],0)
    with pytest.raises(ValueError,match='register width'):
        search_circuit(network,1,['00'],1)
