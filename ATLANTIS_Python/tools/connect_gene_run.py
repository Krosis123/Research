from getpass import getpass
from qiskit_ibm_runtime import QiskitRuntimeService
import runpy
def main():
    key=getpass('IBM key: ')
    crn=getpass('Instance: ')
    try:
        s=QiskitRuntimeService(channel='ibm_quantum_platform',token=key,instance=crn)
        b=s.least_busy(operational=True,simulator=False,min_num_qubits=40)
        print("Connected",b.name,flush=True)
    except Exception as e:
        print("Connection failed",type(e).__name__)
        return
    runpy.run_path('ATLANTIS_Python/tools/gene_block_update.py',init_globals={'live_backend':b},run_name='__main__')
if __name__=='__main__': main()
