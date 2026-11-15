"""Ephemeral BYO IBM account and explicit-confirmation circuit submission.

Never calls save_account. Caller persists provider IDs, never service/credentials.
"""
class IBMAccount:
    def __init__(self): self._service=None

    def connect(self,token,instance,service_factory=None):
        if not token or not instance: raise ValueError('API key and instance CRN required')
        if service_factory is None:
            from qiskit_ibm_runtime import QiskitRuntimeService
            service_factory=QiskitRuntimeService
        try: service=service_factory(channel='ibm_quantum_platform',token=token,instance=instance)
        except Exception: raise RuntimeError('IBM connection failed. Check account, instance and network access.') from None
        self._service=service

    def disconnect(self): self._service=None

    def service(self):
        if self._service is None: raise ValueError('Connect an IBM account first')
        return self._service

    def backends(self):
        try:return [{'name':b.name,'qubits':b.num_qubits} for b in self.service().backends(simulator=False,operational=True)]
        except Exception:raise RuntimeError('IBM backend discovery failed; check account access') from None

    def prepare(self,circuit,backend_name,shots=256,max_depth=10000,max_gates=100000):
        from qiskit.transpiler import generate_preset_pass_manager
        try:
            backend=self.service().backend(backend_name)
            simulator=backend.configuration().simulator
        except Exception:raise RuntimeError('IBM backend access failed') from None
        if simulator: raise ValueError('Physical QPU required')
        if not 1<=shots<=4096: raise ValueError('Shots outside local budget [1,4096]')
        if circuit.num_qubits>backend.num_qubits: raise ValueError('Insufficient backend qubits')
        compiled=generate_preset_pass_manager(optimization_level=1,backend=backend,seed_transpiler=42).run(circuit)
        if compiled.depth()>max_depth or compiled.size()>max_gates: raise ValueError('Hardware circuit exceeds depth/gate budget')
        return backend,compiled,{'backend':backend_name,'logical_qubits':circuit.num_qubits,
            'transpiled_width':compiled.num_qubits,'depth':compiled.depth(),'gates':compiled.size(),'shots':shots,
            'cost':'Provider plan determines charges; no price estimate available'}

    def submit(self,prepared,*,confirmed=False,max_seconds=60,sampler_factory=None):
        if not confirmed: raise PermissionError('Explicit confirmation required before potentially paid submission')
        if not 1<=max_seconds<=300: raise ValueError('Execution budget must be 1..300 seconds')
        backend,circuit,summary=prepared
        if sampler_factory is None:
            from qiskit_ibm_runtime.executor_sampler import Sampler
            sampler_factory=Sampler
        try:
            sampler=sampler_factory(mode=backend,options={'max_execution_time':max_seconds})
            job=sampler.run([circuit],shots=summary['shots'])
            return job.job_id()
        except Exception:
            raise RuntimeError('IBM submission outcome uncertain. Inspect provider jobs before retrying; no automatic retry.') from None

    def status(self,job_id):
        try: return str(self.service().job(job_id).status())
        except Exception: raise RuntimeError('Could not retrieve IBM job status') from None

    def cancel(self,job_id):
        try: return self.service().job(job_id).cancel()
        except Exception: raise RuntimeError('Could not cancel IBM job') from None

    def result(self,job_id):
        try:
            pub=self.service().job(job_id).result()[0]
            return pub.join_data().get_counts()
        except Exception: raise RuntimeError('Could not retrieve IBM measurements') from None
