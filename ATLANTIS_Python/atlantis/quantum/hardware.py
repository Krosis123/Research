"""Bounded IBM discovery with durable provider IDs and no automatic retry."""
import json
from time import monotonic,sleep
from ..experiments import JobStore
from ..analysis import CancelledError
from .engine import run


class ProviderWaitExpired(TimeoutError):
    """The local deadline elapsed while an IBM workload was still active."""


def run_hardware(network,settings,account,backend_name,*,confirmed=False,
                 max_submissions=24,max_execution_seconds=60,progress=None,cancel=None,store=None):
    if not confirmed:raise PermissionError('Paid submission confirmation required')
    if settings.engine!='ibm' or settings.counting_mode!='qpe_aer':
        raise ValueError('Hardware discovery requires IBM execution and actual QPE counting')
    if settings.noise_probability:raise ValueError('Artificial noise model is not applicable to hardware')
    if not 1<=max_submissions<=100:raise ValueError('Provider submission budget outside [1,100]')
    if not 1<=max_execution_seconds<=300:raise ValueError('Provider execution budget outside [1,300] seconds')
    store=store or JobStore()
    identity=store.create(network,settings)
    with store.connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS provider_jobs (experiment TEXT, ordinal INTEGER, provider_id TEXT, status TEXT, resources TEXT, PRIMARY KEY(experiment,ordinal))')
    submitted=[];start=monotonic()
    def set_provider_status(ordinal,status):
        with store.connect() as c:
            c.execute('UPDATE provider_jobs SET status=? WHERE experiment=? AND ordinal=?',
                      (status,identity,ordinal))

    def executor(circuit,shots,**options):
        if len(submitted)>=max_submissions:raise RuntimeError('Hardware submission quota exhausted; result inconclusive')
        prepared=account.prepare(circuit,backend_name,shots,settings.max_compiled_depth,settings.max_compiled_gates)
        ordinal=len(submitted)
        with store.connect() as c:
            c.execute('INSERT INTO provider_jobs VALUES (?,?,?,?,?)',
                (identity,ordinal,None,'submitting_outcome_unknown',json.dumps(prepared[2])))
        # No retry even if submission acknowledgement is lost.
        job_id=account.submit(prepared,confirmed=True,max_seconds=max_execution_seconds)
        submitted.append(job_id)
        with store.connect() as c:
            c.execute('UPDATE provider_jobs SET provider_id=?,status=? WHERE experiment=? AND ordinal=?',
                      (job_id,'submitted',identity,ordinal))
        while True:
            status=account.status(job_id).upper().split('.')[-1]
            if status in ('DONE','COMPLETED'):break
            if status in ('ERROR','CANCELLED','CANCELED','FAILED'):
                set_provider_status(ordinal,status.lower())
                if status in ('CANCELLED','CANCELED'):
                    raise CancelledError('IBM provider cancelled the job')
                raise RuntimeError('IBM job '+status)
            if cancel and cancel():
                try:
                    account.cancel(job_id)
                except Exception:
                    set_provider_status(ordinal,'cancel_outcome_unknown')
                else:
                    set_provider_status(ordinal,'cancel_requested')
                raise CancelledError(f'Local run cancelled. Check IBM job {job_id} for provider status.')
            if monotonic()-start>settings.timeout_seconds:
                set_provider_status(ordinal,status.lower())
                raise ProviderWaitExpired(
                    f'ATLANTIS stopped waiting for IBM job {job_id} (last status: {status}). '
                    'Use IBM account → Retrieve provider status to track it. '
                    'If it completes, use Retrieve completed measurements.')
            if progress:progress(0,f'IBM {job_id}: {status}')
            sleep(.5)
        set_provider_status(ordinal,'completed')
        counts=account.result(job_id)
        compiled=prepared[1]
        return counts,{'compiled_depth':compiled.depth(),'compiled_size':compiled.size(),
            'compiled_2q_count':sum(len(item.qubits)==2 for item in compiled.data),
            'transpiled_qubits':compiled.num_qubits,'provider_job_id':job_id,'backend':backend_name}
    try:
        result=run(network,settings,progress,cancel,circuit_executor=executor)
        result.update(job_id=identity,provider_job_ids=submitted,backend=backend_name)
        store.finish(identity,'finished',result);return result
    except CancelledError as e:
        store.finish(identity,'cancelled',error=str(e));raise
    except ProviderWaitExpired as e:
        store.finish(identity,'provider_wait_expired',error=str(e));raise
    except Exception as e:
        store.finish(identity,'failed',error=str(e));raise
