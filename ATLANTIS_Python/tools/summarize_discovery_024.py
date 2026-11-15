"""Summarize completed discovery trials and paired circuit-stage timings."""
from collections import Counter
import json
from pathlib import Path
from statistics import mean, median
from math import sqrt

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def interval(success, total):
    p=success/total
    z=1.95996398454
    scale=1+z*z/total
    center=(p+z*z/(2*total))/scale
    half=z*sqrt(p*(1-p)/total+z*z/(4*total*total))/scale
    return [max(0,center-half),min(1,center+half)]


def main():
    root=Path('validation')
    report={}
    for label,filename in (('random','discovery-024.json'),('longer','discovery-longer-024.json'),
                            ('adversarial','discovery-adversarial-024.json'),
                            ('low_shots','discovery-low-shots-024.json'),
                            ('guarded_low_shots','discovery-low-shots-guarded-024.json'),
                            ('guarded_stress','discovery-adversarial-guarded-024.json'),
                            ('guarded_stress_p2','discovery-stress-p2-024.json'),
                            ('guarded_stress_p3','discovery-stress-p3-024.json'),
                            ('additional','discovery-additional-024.json'),
                            ('guarded_longer','discovery-longer-guarded-024.json')):
        rows=json.loads((root/filename).read_text())
        scores=[r['score'] for r in rows]
        errors=[c['signed_error'] for s in scores for c in s['count_errors']]
        false=sum(s['heuristic_false_completion'] for s in scores)
        report[label]=dict(runs=len(rows),statuses=Counter(r['result']['status'] for r in rows),
                           exact_matches=sum(s['exact_match'] for s in scores),
                           missed_attractors=sum(len(s['missed_attractors']) for s in scores),
                           false_attractors=sum(len(s['false_discoveries']) for s in scores),
                           duplicate_discoveries=sum(s['duplicate_discoveries'] for s in scores),
                           duplicate_shots=sum(s['duplicate_shots'] for s in scores),
                           count_calls=len(errors),count_bias=mean(errors),count_mae=mean(map(abs,errors)),
                           count_rmse=sqrt(mean(e*e for e in errors)),heuristic_false_completions=false,
                           descriptive_false_completion_wilson95=interval(false,len(rows)))
        paired={}
        for level in (0,2):
            choices=[r for r in rows if r['optimization_level']==level and r['shots']==128
                     and (label=='adversarial' or r['seed']==47)]
            if choices:
                circuits=[e['resources'] for r in choices for e in r['result']['history']
                          if e['kind']=='circuit_execution']
                paired[level]=dict(runs=len(choices),median_wall_s=median(r['wall_s'] for r in choices),
                                   total_transpilation_s=sum(e['transpilation_s'] for e in circuits),
                                   total_simulation_s=sum(e['execution_s'] for e in circuits),
                                   total_counting_s=sum(r['result']['counting_runtime_s'] for r in choices),
                                   two_qubit_gates=sum(e['compiled_2q_count'] for e in circuits),
                                   exact_matches=sum(r['score']['exact_match'] for r in choices))
        report[label]['paired_128']=paired
    old=json.loads((root/'optimization-023.json').read_text())
    stages=[]
    for task in ('search','qpe'):
        for level in (0,2):
            rows=[r for r in old if r['task']==task and r['optimization_level']==level]
            stages.append(dict(task=task,level=level,transpile=median(r['transpilation_s'] for r in rows),
                               execute=median(r['execution_s'] for r in rows),
                               wall=median(r['wall_s'] for r in rows)))
    report['v023_stage_breakdown']=stages
    (root/'discovery-summary-024.json').write_text(json.dumps(report,indent=2))
    fig,axes=plt.subplots(1,2,figsize=(9,4))
    for task,ax in zip(('search','qpe'),axes):
        vals=[row for row in stages if row['task']==task]
        xs=range(len(vals))
        ax.bar(xs,[x['transpile'] for x in vals],label='transpilation')
        ax.bar(xs,[x['execute'] for x in vals],bottom=[x['transpile'] for x in vals],label='Aer execution')
        ax.set_xticks(list(xs),[str(x['level']) for x in vals])
        ax.set_xlabel('Transpiler optimization level')
        ax.set_ylabel('Median stage duration (s)')
        ax.set_title(task)
        ax.legend()
    fig.tight_layout()
    fig.savefig(root/'optimization-stage-024.png',dpi=180)


if __name__=='__main__':
    main()
