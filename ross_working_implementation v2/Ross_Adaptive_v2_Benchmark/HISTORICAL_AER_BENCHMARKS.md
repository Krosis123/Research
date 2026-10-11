# Historical Qiskit Aer benchmarks (user-reported CSVs, Oct. 10, 2026)

**Preservation note.** The results below were transcribed/aggregated from the
CSV data the researcher pasted into the conversation. They are **not outputs
of the modified adaptive program** and should not be mistaken for independent
re-executions here. The original per-run records remain in that conversation;
this file preserves primary aggregates as local backup if CSVs are deleted.

Software: Python 3.12.10; Qiskit 2.5.2; Aer 0.17.2; ideal simulator,
`readout_flip_probability=0` for all following actual Aer datasets.
All benchmarks up to the new adaptive version used **the classical true
number of attractors to stop** and **the exact classical maximum transient to
set T**. Except explicitly named `qpe_aer`, `--counting-mode exact` used
**classically enumerated** basin sizes. All success rates were after
classical candidate verification/post-selection. No ATLANTIS MATLAB runtime
comparison or physical quantum advantage is established.

## Main family scaling (actual Aer, 10 repetitions each, 1024 shots per run)

| family | n | K | T | evolution qubits | mean total s | mean search construction s | mean search Aer simulation s | mean peak RAM MiB | recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| skewed | 4 | 2 | 1 | 8 | 0.5006 | 0.3770 | 0.1111 | 81.71 | 100% |
| skewed | 6 | 2 | 1 | 12 | 0.5081 | 0.3819 | 0.1140 | 81.70 | 100% |
| skewed | 8 | 2 | 1 | 16 | 0.5193 | 0.3813 | 0.1243 | 83.22 | 100% |
| skewed | 10 | 2 | 1 | 20 | 0.5465 | 0.3726 | 0.1584 | 99.27 | 100% |
| cycle2 | 4 | 3 | 1 | 8 | 0.5806 | 0.3760 | 0.1920 | 81.83 | 100% |
| cycle2 | 6 | 3 | 1 | 12 | 0.5622 | 0.3660 | 0.1840 | 81.91 | 100% |
| cycle2 | 8 | 3 | 1 | 16 | 0.6027 | 0.3910 | 0.1980 | 83.35 | 100% |
| cycle2 | 10 | 3 | 1 | 20 | 0.7324 | 0.4310 | 0.2860 | 99.40 | 100% |

All 80 listed family-scaling runs reported status ok, zero false positives
and 100% recall. Cycle2 includes one two-state cyclic attractor, so its
three attractors occupy four distinct cycle states.

### Other exact-count Aer baselines

- `projection_4`: three runs (1024 shots), eight attractors, all recovered;
  total runtimes 0.95525 / 0.99447 / 0.82841 s, peak RAM about 82.5 MiB,
  8 evolution qubits.
- `rossini4_4`: ten runs (1024 shots), five fixed attractors with basin sizes
  11/2/1/1/1, `T=3`, 16 evolution qubits, all recovered; average total
  runtime ~0.686 s and mean peak RAM ~83.78 MiB.
- `skewed_10`: one separate exploratory run at 256 shots (different from the
  ten-run controlled study); total 0.498965 s, peak 99.2695 MiB, 2/2 attractors.

## First real quantum-counting (QPE) experiments

`cycle2_4`, precision 5, 256 counting shots, 512 search shots, **three** runs:
all 3/3 attractors recovered; counting error 0 on all; average total runtime
1.446 s, counting runtime 0.846 s, peak RSS 112.57 MiB, mean compiled depth
~10,404, mean reported two-qubit gates ~1,325, oracle-call metric 69.

### Four-gene cycle2 QPE precision sweep (10 repetitions per precision)

All runs used 512 search shots and 256 counting shots. All 40 runs recovered
3/3 attractors. Average wrong-measurement rates are NONZERO at p=3 and p=4
in spite of 100% overall recall.

| precision p | mean total s | mean counting s | mean peak RSS MiB | mean abs count error | wrong-run measurement rate | mean maximum circuit depth | mean reported 2q gates | ideal oracle calls |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 0.8026 | 0.2752 | 91.21 | 1.30 | 11.59% | 2,289 | 289 | 23 |
| 4 | 0.9648 | 0.4439 | 98.44 | 0.65 | 0.96% | 4,911 | 620 | 37 |
| 5 | 1.4305 | 0.9115 | 112.07 | 0 | 0% | 10,163 | 1,279 | 69 |
| 6 | 2.8473 | 2.3445 | 139.97 | 0 | 0% | 20,678 | 2,599 | 133 |

### Original Rossini4 QPE, matched p=4 vs p=5

Same three seeds (42853 / 50772 / 58691), 512 search shots, 128 counting
shots. Five fixed attractors, maximum transient T=3, 16 evolution qubits.

| precision | runs | mean total s | mean counting s | mean RSS MiB | mean abs M error | wrong-run rate | mean maximum depth | mean 2q gates | mean oracle calls |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 3 | 6.66210 | 5.98362 | 144.642 | 0.41667 | 2.13542% | 14,421 | 1,472 | 78.33 |
| 5 | 3 | 24.74939 | 24.00977 | 209.070 | 0.25 | 0.58594% | 29,819 | 3,040 | 141.0 |

All six matched trials recovered 5/5 attractors. Separate initial p=4
one-repetition exploratory run: total time 6.4054 s, counting time 5.7608 s,
RAM 145.5977 MiB, counting error 0.5, wrong-run rate 3.046875%.

**Important**: the legacy Aer `max_suppressed_leakage=0` was an uncomputed
placeholder, **not** a measured zero-leakage guarantee. `simulation_runtime_s`
there excluded the quantum-counting stage, which is recorded separately.

## Record count audit

Total separate user-provided Aer rows represented by these datasets:
3 (projection exploratory) + 10 (Rossini4 exact) + 1 (skewed10 exploratory)
+ 40 (skewed scaling) + 40 (cycle2 scaling) + 3 (initial cycle2 QPE)
+ 40 (QPE precision sweep) + 1 (initial Rossini4 p4 QPE)
+ 3 (Rossini4 p5 QPE) + 3 (matched Rossini4 p4 QPE) = **144**.
Earlier chat messages inadvertently cited **140**. The corrected total is
144 **separate execution records**; some use the same seed/settings but are
independent runs, and not all are independent controlled treatments.
