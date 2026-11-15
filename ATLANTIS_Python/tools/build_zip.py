"""Build the complete source distribution without development environments or Git history."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'dist';out.mkdir(exist_ok=True)
files={}
def add(path,arc):
 if path.is_file() and '__pycache__' not in path.parts and '.git' not in path.parts:
  files['ATLANTIS_Python/'+arc.replace('\\','/')]=path
for name in ['README.md','LICENSE','THIRD_PARTY_NOTICES.md','requirements.txt','pyproject.toml','run_atlantis.py','install_windows.bat','launch_atlantis.bat']:
 add(ROOT/name,name)
for name in ['atlantis','docs','tests','tools','examples','supplementary','.graphviz']:
 for p in (ROOT/name).rglob('*'):
  if p.is_file():add(p,p.relative_to(ROOT).as_posix())
original=ROOT/'original/ATLANTIS'
if not original.exists():original=ROOT/'reference'
for p in original.rglob('*'):
 if p.is_file() and '.git' not in p.parts:add(p,'reference/'+p.relative_to(original).as_posix())
for p in (ROOT/'validation').iterdir():
 if p.is_file() and (p.suffix=='.mat' or p.name in ['pytest.xml','comparison_metrics.json','fixtures_manifest.json','release_pytest.xml'] or (p.name.startswith('matlab_') and p.suffix=='.log' and p.stat().st_size>0)):
  add(p,'validation/'+p.name)
for name in ['gui','python']:
 for p in (ROOT/'validation'/name).rglob('*'):
  if p.is_file():add(p,'validation/'+p.relative_to(ROOT/'validation').as_posix())
manifest=[{'path':arc.removeprefix('ATLANTIS_Python/'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for arc,p in sorted(files.items())]
manifest_path=out/'MANIFEST.json';manifest_path.write_text(json.dumps(manifest,indent=2));add(manifest_path,'MANIFEST.json')
path=out/'ATLANTIS_Python.zip'
with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for arc,p in sorted(files.items()):z.write(p,arc)
with zipfile.ZipFile(path) as z:
 bad=z.testzip()
 if bad:raise RuntimeError('Corrupt ZIP member: '+bad)
 assert 'ATLANTIS_Python/launch_atlantis.bat' in z.namelist()
 assert not any('/.git/' in n or '/.deps/' in n or '__pycache__' in n for n in z.namelist())
sha=hashlib.sha256(path.read_bytes()).hexdigest();(out/'ATLANTIS_Python.zip.sha256').write_text(sha+'  ATLANTIS_Python.zip\n')
print(json.dumps({'zip':str(path),'bytes':path.stat().st_size,'files':len(files),'sha256':sha},indent=2))
