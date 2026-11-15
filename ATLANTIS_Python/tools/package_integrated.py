"""Package source, examples and validation; exclude executables and environments."""
from pathlib import Path
import zipfile,hashlib,json
root=Path(__file__).resolve().parents[1]
out=root.parent/'dist';out.mkdir(exist_ok=True)
target=out/'ATLANTIS_Quantum_0.2.4_source.zip'
excluded={'.graphviz','.venv','.deps','__pycache__','.pytest_cache','build','atlantis_python.egg-info'}
extensions={'.exe','.dll','.pyc','.pyd','.mexw64','.mexw32','.rar','.zip','.msi','.so'}
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for path in sorted(root.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(root)
        if any(p in excluded for p in relative.parts) or path.suffix.lower() in extensions:continue
        z.write(path,'ATLANTIS_Quantum/'+relative.as_posix())
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    assert 'ATLANTIS_Quantum/HANDOFF.md' in z.namelist()
checks={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.suffix in ('.zip','.whl')}
(out/'SHA256SUMS.json').write_text(json.dumps(checks,indent=2))
print(target,round(target.stat().st_size/1024**2,2),'MiB',len(checks),'artifacts hashed')
