from pathlib import Path
import numpy as np
from scipy.io import loadmat
from atlantis.io import load_weighted
from atlantis.states import all_states
from atlantis.analysis import deterministic_analysis,probabilistic_analysis
n=load_weighted('original/ATLANTIS/Sample Data/Case Study 1/Input Files/NetworkFile.csv');s=all_states(n.n)
r=loadmat('validation/matlab_yeast_deterministic.mat',simplify_cells=True)
print('matlab attr table',r['attractorTable']); print('states shape',r['states'].shape)
p=loadmat('validation/matlab_yeast_probabilistic.mat',simplify_cells=True)
a=probabilistic_analysis(n,s,5,.001,200,1e-7,True)
print('PA shape',a.transition.shape,'matrix diff',np.max(np.abs(a.transition-p['transition'])),'prob diff',np.max(np.abs(a.probabilities-p['probabilities'])),'iters',a.iterations,p.get('iteration'))
print('Sammon',loadmat('validation/matlab_sammon.mat',simplify_cells=True))
