"""Generate auditable source manifest and measured benchmark report."""
from pathlib import Path
import hashlib,json,zipfile,statistics
root=Path(__file__).resolve().parents[1]
original=zipfile.ZipFile(root.parent/'ATLANTIS_Python.zip')
manifest=[]
for path in sorted(root.rglob('*')):
    if not path.is_file() or any(p.startswith('.') or p in ('__pycache__','build','atlantis_python.egg-info') for p in path.relative_to(root).parts):continue
    relative=path.relative_to(root).as_posix()
    if not (relative.startswith(('atlantis/','tests/','tools/','docs/')) or len(path.relative_to(root).parts)==1):continue
    key='ATLANTIS_Python/'+relative
    data=path.read_bytes()
    status='modified' if key in original.namelist() else 'created'
    if key in original.namelist() and data==original.read(key):continue
    manifest.append({'path':relative,'status':status,'sha256':hashlib.sha256(data).hexdigest()})
(root/'validation/integration-file-manifest.json').write_text(json.dumps(manifest,indent=2))
summary=json.loads((root/'validation/benchmark-current/summary.json').read_text())
mps=[json.loads(p.read_text()) for p in (root/'validation/benchmark-five-mps').glob('seed-*.json')]
lines=['# Measured benchmark report — 8 November 2026','',
'738 matrix records plus 20 isolated five-gene MPS runs: **758 attempts**, of which',
'**738 completed** and **20 were rejected before execution by the memory guard**.',
'The rejected configurations are 25-qubit five-gene statevector runs, requiring',
'512 MiB amplitudes plus the configured 3x working allowance, exceeding 1024 MiB.',
'These are resource rejections, not successful circuit measurements.','',
'## Rossini four-gene results','',
'| Protocol | Repeats | Median seconds | IQR seconds | Mean attractor recall |',
'|---|---:|---:|---:|---:|']
for s in summary:
    if s['network']=='rossini4':lines.append(f"| {s['protocol']} | {s['repetitions']} | {s['median_s']:.6g} | {s['q25_s']:.6g}–{s['q75_s']:.6g} | {s['mean_recall']:.3f} |")
lines += ['', 'QPE uses 3 precision bits, 128 counting shots, and 128 search shots. All three',
'QPE runs reported heuristic completion and were independently scored at full recall.',
'This does not validate the heuristic for unseen networks or prove completeness.',
'Noisy runs use depolarizing error 0.002 on one- and two-qubit gates, not a real',
'device calibration. Exact-M Aer uses classical enumeration for M and classical',
'coverage certification; its timing is not a quantum-only solution.','',
'## Five-gene MPS','',
f'{len(mps)} isolated runs, T=4, 25 logical qubits, 128 shots. Every run found both',
'attractors and obtained independent classical coverage certification. Median',
f"solver time {statistics.median(x['total_runtime_s'] for x in mps):.6g} s; median isolated wall time",
f"{statistics.median(x['isolated_wall_s'] for x in mps):.6g} s including process startup.",'',
'## Larger models and methodology','',
'Projection, skewed, cycle2 and long_chain families were exercised at 4, 10 and 15',
'nodes. The small families have 20 repetitions. Fifteen-node reference runs use',
'3 repeats due their enumeration cost; QPE/noise also use 3 due circuit cost.',
'10/15-node full circuits are resource estimates only in this matrix. In particular',
'the 15-node long chain requires 225 logical evolution qubits.','',
'The classical_sample protocol draws min(128,2^n) unique states; for 4/5 nodes this',
'happens to cover the full state space and is not evidence of sparse-sampling ability.',
'Independent exhaustive truth timings are separate. Raw measurements, timing,',
'rejected outcomes, seeds, circuit depth, two-qubit counts and completion flags are',
'in benchmark-current/raw.csv and raw.jsonl. Seed-zero full quantum histories and',
'all five-gene MPS histories are retained. Per-process peak memory in the main',
'matrix is a lifetime high-water mark, not isolated incremental memory per run.',
'Compilation/transpilation records are in circuit execution history where retained.',
'Queue time and physical execution time are unavailable: no QPU was used.','',
'IQR is empirical variability, not a confidence interval. With all 20 repeated',
'runs successful, a binomial Wilson 95% interval for run-success probability is',
'approximately [0.839,1]; with only 3 it is [0.438,1]. These intervals describe this',
'fixed protocol under independent trials, not completeness guarantees or biological',
'generalization. Small-n classical enumeration is much faster here; no quantum',
'speedup is established.','',
'## Reproduce','',
'```powershell','python tools/benchmark_integrated.py --output validation/new-matrix',
'python tools/benchmark_five_mps.py','python tools/demo_integrated.py','```','',
'The MPS/demo scripts overwrite their named result JSONs on rerun and append new',
'durable job records. Preserve original outputs when comparing experiments.','',
'![Measured Rossini4 runtimes](../validation/benchmark-current/runtime.png)']
(root/'docs/BENCHMARK_CURRENT.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
print('Manifest entries',len(manifest),'MPS runs',len(mps))
