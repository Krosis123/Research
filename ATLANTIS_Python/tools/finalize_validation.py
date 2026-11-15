from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET,sys,platform
from importlib.metadata import version
p=Path('validation')
fixtures=[{'file':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size} for f in sorted(p.glob('matlab_*.mat'))]
(p/'fixtures_manifest.json').write_text(json.dumps({'python':sys.version,'platform':platform.platform(),'dependencies':{n:version(n) for n in ['numpy','scipy','matplotlib','networkx','PySide6-Essentials','h5py','pytest']},'matlab_fixtures':fixtures},indent=2))
r=ET.parse(p/'release_pytest.xml').getroot()
suites=list(r.iter('testsuite'))
assert sum(int(x.get('tests',0)) for x in suites)==117
assert all(int(x.get('failures',0))==0 and int(x.get('errors',0))==0 and int(x.get('skipped',0))==0 for x in suites)
print('Release report: 117 tests, zero failures/errors/skips')
