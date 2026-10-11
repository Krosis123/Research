"""Isolated benchmark campaign: each case launches a fresh Python process.

This provides independent process high-water memory measurements and protects
against a single stuck run via subprocess timeouts. Use on Windows PowerShell
or Linux. The 10/15-node experiments use identical network rules across engines.
"""
from __future__ import annotations
import argparse,csv,platform,subprocess,sys,tempfile,time
from pathlib import Path
from .runner import FAMILIES,write_rows,now_utc


def main(argv=None):
    p=argparse.ArgumentParser(description='Isolated Rossini benchmarking campaign')
    p.add_argument('--nodes',nargs='+',type=int,default=[4,10,15])
    p.add_argument('--families',nargs='+',default=['rossini4',*FAMILIES])
    p.add_argument('--engine',choices=['reduced','aer','aer_mps'],default='reduced')
    p.add_argument('--discovery-mode',choices=['legacy','adaptive'],default='legacy')
    p.add_argument('--evolution-steps',type=int,default=None)
    p.add_argument('--max-rounds',type=int,default=24)
    p.add_argument('--search-retries',type=int,default=2)
    p.add_argument('--stop-policy',choices=['qpe','classical_audit'],default='qpe')
    p.add_argument('--stop-confirmations',type=int,default=2)
    p.add_argument('--min-full-fraction',type=float,default=0.95)
    p.add_argument('--truth-mode',choices=['report','none'],default='report')
    p.add_argument('--counting-mode',choices=['exact','qpe_ideal','qpe_aer'],default='exact')
    p.add_argument('--repetitions',type=int,default=5)
    p.add_argument('--shots',type=int,default=1024)
    p.add_argument('--readout-flip',type=float,default=0)
    p.add_argument('--counting-precision',type=int,default=8)
    p.add_argument('--counting-shots',type=int,default=256)
    p.add_argument('--max-sim-qubits',type=int,default=24)
    p.add_argument('--force-large',action='store_true')
    p.add_argument('--timeout',type=int,default=180)
    p.add_argument('--seed',type=int,default=2026)
    p.add_argument('--output',default='results/isolated.csv')
    args=p.parse_args(argv)
    if args.discovery_mode=='adaptive' and (args.evolution_steps is None or args.evolution_steps<1):
        p.error('Adaptive discovery needs --evolution-steps >= 1 (chosen by user, not from exact truth)')
    rows=[]
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    for n in args.nodes:
        for family in args.families:
            if family=='rossini4' and n!=4: continue
            for rep in range(args.repetitions):
                with tempfile.TemporaryDirectory(prefix='rossini_') as td:
                    temp=Path(td)/'child.csv'
                    cmd=[sys.executable,'-m','ross_bench.runner', '--nodes',str(n),
                         '--families',family,'--engine',args.engine,
                         '--counting-mode',args.counting_mode,
                         '--repetitions','1','--shots',str(args.shots),
                         '--counting-precision',str(args.counting_precision),
                         '--counting-shots',str(args.counting_shots),
                         '--readout-flip',str(args.readout_flip),
                         '--max-sim-qubits',str(args.max_sim_qubits),
                         '--seed',str(args.seed+7919*rep),'--output',str(temp),
                         '--discovery-mode',args.discovery_mode,
                         '--max-rounds',str(args.max_rounds),
                         '--search-retries',str(args.search_retries),
                         '--stop-policy',args.stop_policy,
                         '--stop-confirmations',str(args.stop_confirmations),
                         '--min-full-fraction',str(args.min_full_fraction),
                         '--truth-mode',args.truth_mode]
                    if args.evolution_steps is not None:
                        cmd+=['--evolution-steps',str(args.evolution_steps)]
                    if args.force_large:cmd.append('--force-large')
                    begin=time.perf_counter()
                    try:
                        result=subprocess.run(cmd,capture_output=True,text=True,
                                              timeout=args.timeout,check=False)
                        if result.returncode and not temp.exists():
                            row=dict(timestamp_utc=now_utc(),n=n,family=family,repeat=rep,
                                    status='child_error',error=(result.stderr or result.stdout)[-500:])
                        else:
                            with temp.open(newline='',encoding='utf-8') as f:
                                row=next(csv.DictReader(f))
                    except subprocess.TimeoutExpired:
                        row=dict(timestamp_utc=now_utc(),n=n,family=family,repeat=rep,
                                 status='timeout',error=f'exceeded {args.timeout}s')
                    row['isolation_wallclock_s']=time.perf_counter()-begin
                    row['independent_process_peak_memory']=True
                    row['repeat']=rep
                    rows.append(row)
                    write_rows(out,rows)
                    print(f'{family:12} n={n:2} rep={rep} status={row["status"]} '
                          f'peak_rss_mib={row.get("peak_rss_mib","NA")}',flush=True)
    print('Output:',out)

if __name__=='__main__':main()
