from pathlib import Path
import re,json
root=Path('original/ATLANTIS/Toolbox')
items=[]
for p in root.rglob('*.m'):
 text=p.read_text(errors='replace')
 items.append({'source':p.relative_to(root).as_posix(),'functions':re.findall(r'^\s*(?:function|classdef)\s+(.+)',text,re.M),'lines':len(text.splitlines())})
Path('docs/source_symbols.json').write_text(json.dumps(items,indent=2))
for i in items:
 if any(s in i['source'] for s in ['Menu','Input','GenerateNetwork','GraphViz']):
  print(i['source'],':', ' | '.join(i['functions']))
