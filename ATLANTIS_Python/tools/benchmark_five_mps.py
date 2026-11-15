import sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from atlantis.io import load_network
from atlantis.quantum.engine import Settings
from atlantis.experiments import execute,JobStore

if __name__=='__main__':
    root=Path('validation/benchmark-five-mps');root.mkdir(exist_ok=True)
    net=load_network('examples/quantum/giacomantonio5.json');store=JobStore(root/'jobs.sqlite3')
    for seed in range(20):
        start=time.perf_counter()
        result=execute(net,Settings(T=4,engine='aer_mps',max_qubits=25,seed=seed,shots=128),store=store)
        result['isolated_wall_s']=time.perf_counter()-start
        (root/f'seed-{seed:02d}.json').write_text(json.dumps(result,indent=2))
        print(seed,result['status'],len(result['cycles']),flush=True)
