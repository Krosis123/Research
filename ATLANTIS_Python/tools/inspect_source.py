from pathlib import Path
from collections import Counter
import re,json
root=Path('original/ATLANTIS')
files=[p for p in root.rglob('*') if p.is_file() and '.git' not in p.parts]
Path('docs/inventory.json').write_text(json.dumps([{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size} for p in files],indent=2))
print(Counter(p.suffix.lower() for p in files))
for folder in ['Analyses','Generate Network','Modify Network','Visualize Results','Classes']:
 ps=[p for p in root.rglob('*.m') if folder in p.parts]
 out=[]
 for p in ps:
  lines=[l for l in p.read_text(errors='replace').splitlines() if l.strip() and not l.lstrip().startswith('%')]
  out.append('\nFILE '+str(p.relative_to(root))+'\n'+'\n'.join(lines))
 Path('docs/source_'+folder.replace(' ','_')+'.txt').write_text('\n'.join(out),encoding='utf-8')
print([str(p) for p in root.rglob('*.m') if 'classdef' in p.read_text(errors='replace')])
