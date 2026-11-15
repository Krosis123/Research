from pathlib import Path
import json,sys
sys.path.insert(0,str(Path('.deps').resolve()))
import h5py,numpy as np
from scipy.io import loadmat
FIELDS=['Tag','Position','Units','String','Style','Value','Min','Max','Enable','Visible','BackgroundColor','ForegroundColor','FontName','FontSize','FontWeight','HorizontalAlignment','Title','Name','Color','TooltipString']
def scalar(f,obj):
 if isinstance(obj,h5py.Group): return None
 if obj.attrs.get('MATLAB_empty',0): return []
 a=obj[()]
 if h5py.check_dtype(ref=obj.dtype) is not None:
  return [scalar(f,f[r]) if r else None for r in a.T.flat]
 if obj.attrs.get('MATLAB_class',b'')==b'char':
  a=np.atleast_2d(a.T)
  texts=[''.join(chr(int(c)) for c in row).rstrip() for row in a]
  return texts[0] if len(texts)==1 else texts
 a=np.asarray(a).T.squeeze()
 return a.tolist()
def node(f,g):
 t=scalar(f,g['type']); p=g['properties']; ch=g.get('children')
 props={k:scalar(f,p[k]) for k in FIELDS if k in p} if isinstance(p,h5py.Group) else {}
 children=[]
 if isinstance(ch,h5py.Group):
  if h5py.check_dtype(ref=ch['type'].dtype) is not None:
   for i in range(ch['type'].size):
    refs={k:f[v[()].T.flat[i]] for k,v in ch.items() if isinstance(v,h5py.Dataset) and h5py.check_dtype(ref=v.dtype) is not None and v[()].T.flat[i]}
    children.append(node(f,refs))
  else: children=[node(f,ch)]
 return {'type':t,'properties':props,'children':children}
for p in Path('original/ATLANTIS/Toolbox').rglob('*.fig'):
 try:
  with h5py.File(p) as f: d=node(f,f['hgS_070000'])
 except OSError:
  raw=loadmat(p,simplify_cells=True)['hgS_070000']
  def conv(r):
   c=r.get('children',[])
   if isinstance(c,dict): c=[c]
   return {'type':r['type'],'properties':{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in r['properties'].items() if k in FIELDS},'children':[conv(x) for x in c]}
  d=conv(raw)
 Path('atlantis/assets/guide',p.stem+'.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
 print(p.stem,d['properties'].get('Position'),d['properties'].get('Units'))
 def show(n,depth=0):
  pr=n['properties']; print(' '*depth,n['type'],pr.get('Tag'),pr.get('Style'),str(pr.get('String',pr.get('Title','')))[:160],pr.get('Position'),pr.get('Units'))
  for c in n['children']: show(c,depth+1)
 if p.stem in ['ATLANTIS','DeterministicAnalysisMenu','VisualizeResultsMenu','ProbabilisticAnalysisMenu']: show(d)
