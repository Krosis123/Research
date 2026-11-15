from pathlib import Path
from scipy.io import loadmat
import numpy as np
for p in Path('original/ATLANTIS/Toolbox').rglob('*.fig'):
 d=loadmat(p,simplify_cells=True)
 print(p.name,[(k,type(v).__name__) for k,v in d.items() if not k.startswith('_')])
 if p.name=='ATLANTIS.fig':
  r=d[[k for k in d if not k.startswith('_')][0]]
  print(str(r)[:7000])
for p in Path('original/ATLANTIS').rglob('*.mat'):
 try:
  d=loadmat(p,simplify_cells=True)
  print(p.name,[(k, getattr(v,'shape',type(v).__name__)) for k,v in d.items() if not k.startswith('_')])
 except Exception as e: print(p,e)
