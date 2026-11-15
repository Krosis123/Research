import json
from pathlib import Path
from scipy.io import loadmat
import numpy as np
from atlantis.io import load_weighted,load_rules,export_results
from atlantis.states import all_states
from atlantis.analysis import deterministic_analysis,probabilistic_analysis
from atlantis.fates import load_fate_logic
from atlantis.plots import *
root=Path('.');out=Path('validation/python');out.mkdir(exist_ok=True)
p=Path('examples/Case Study 1/Input Files'); n=load_weighted(p/'NetworkFile.csv');s=all_states(n.n);logic=load_fate_logic(p/'Cell Fate Determination Logic.csv',n)
d=deterministic_analysis(n,s,200,logic);r=probabilistic_analysis(n,s,5,.001,200,1e-7,True,logic)
ref=loadmat('validation/matlab_naive.mat',simplify_cells=True)
f=landscape_figure(s,'basin',d,permutation=ref['permutation'].astype(int)-1,annotate=False,title='Basin Size Landscape - Yeast'); f.savefig(out/'basin_reference.png',dpi=120)
f=cell_fate_figure({'A':.62,'B':.23,'C':.1,'D':.05},title='Cell Fate Landscape - Yeast');f.savefig(out/'treemap_reference.png',dpi=120)
for kind in ['basin','probability','energy']:
 f=landscape_figure(r.states,kind,d,r,seed=83,factor=1);f.savefig(out/(kind+'.png'),dpi=120)
f=landscape_figure(r.states,'energy',d,r,mapping='sammon',factor=1,title='Potential Energy Landscape');f.savefig(out/'sammon_energy.png',dpi=120)
for engine in ['spring','dot','circo']:
 f=network_figure(n,engine);f.savefig(out/('network_'+engine+'.png'),dpi=120)
export_results(out/'yeast_results',n,d,r)
expected=loadmat('validation/matlab_yeast_probabilistic.mat',simplify_cells=True)
report={'weighted_yeast_states':len(s),'yeast_attractors':len(d.attractors),'dominant_basin':d.attractors[0].basin,'pruned_states':len(r.states),'max_transition_absolute_error':float(np.max(np.abs(r.transition-expected['transition']))),'max_probability_absolute_error':float(np.max(np.abs(r.probabilities-expected['probabilities']))),'master_equation_iterations':r.iterations,'master_equation_converged':r.converged,'python_sammon_energy_rendered':True}
Path('validation/comparison_metrics.json').write_text(json.dumps(report,indent=2))
print(report)
