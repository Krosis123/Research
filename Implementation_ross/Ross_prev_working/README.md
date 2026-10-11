# Rossini Attractor Search — 4/10/15 Gene Reproduction and Benchmarks

**Research status:** reproducible *mathematical validation* and Qiskit-ready circuits; full Aer and QPE circuit execution must be run on a Qiskit-enabled machine. This archive excludes the Windows `.venv` from your 117 MB original ZIP and preserves the actual original files under `original/`.

## What changed

- Original archive contained a **4-gene**, not a 3-gene, network (`A' = A&D; B'=A&B; C'=C&D; D'=B|C`). Its five attractors have basin sizes `11,2,1,1,1`; maximum transient length `T=3`.
- A new generic deterministic synchronous Boolean network class accepts `&`, `|`, `^`, `~`, parentheses, variables, and constants. Each update rule is compiled into **algebraic normal form (ANF)**, then reversibly implemented with `X`, `CX`, `CCX`, `MCX` gates. One extra n-qubit register is used per transition, matching the uploaded Rossini reproduction.
- A full-cycle-aware suppression oracle phases **all states of each already-discovered cycle**, not just one representative. This supports cyclic as well as static attractors.
- Added 10- and 15-gene cases with controlled attractor counts and transient depths; ground-truth network definitions exported as JSON for an eventual fixed-point comparison and ATLANTIS adapter.
- Added repeatable CSV benchmark runners, source-preserving tests, reference plots, finite-shot measurements, readout-flip proxy, and ideal QPE-counting estimator.
- Added optional genuine Qiskit Aer and QPE paths, **not executed in the provided environment** because neither `qiskit` nor `qiskit-aer` can be installed there.

## Directory guide

```text
README.md                      this guide
RESULTS.md                     preliminary findings and limits
original/                      original source extracted from Ross.zip (NOT .venv)
ross_bench/model.py            Boolean rules and exact classical ground truth
ross_bench/reference.py        reduced Rossini mathematical reference, ideal QPE model
ross_bench/circuits.py         Qiskit evolution, suppression, controlled-QPE circuit
ross_bench/runner.py           single-process benchmark with CSV output
ross_bench/campaign.py         isolated benchmark, per-process peak RAM
ross_bench/inspect_resources.py  construct circuits without running Aer
ross_bench/export_networks.py    JSON contracts for ATLANTIS/fixed-point use
ross_bench/reports.py          summary tables and plots
network_definitions/           Rossini4 and synthetic 4/10/15-node examples
tests/                         independent reference tests + optional Qiskit tests
results/                       measured reference experiment CSVs/plots
```

## Windows PowerShell setup

Unzip the package, then open PowerShell **inside the extracted folder containing `ross_bench`**:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-qiskit.txt
python -m pytest -q
```

For the **reduced mathematical reference only**, `pip install -r requirements-reference.txt`. If Windows PowerShell blocks activation, `Set-ExecutionPolicy -Scope Process Bypass`, then retry activation. The original ZIP's Windows venv is not needed in this new package.

## Step A — verify source mathematics, 10/15 gene baselines

```powershell
python -m ross_bench.campaign --nodes 4 10 15 --repetitions 20 --shots 2048 --engine reduced --counting-mode exact --output results/reference_exact.csv
```

`--counting-mode exact` feeds **classically enumerated** M into the deletion angles. This is an oracle-assisted *algorithm validation*, **not a fair full quantum runtime**. The `reduced` engine algebraically replaces `T^dagger P T` with phase-marking initial basin states and simulates only the initial n-qubit amplitudes. Its runtime and RAM **cannot** be represented as the runtime and RAM of a real `(T+1)n`-qubit circuit.

### Additional protocol — idealized QPE uncertainty

```powershell
python -m ross_bench.campaign --nodes 4 10 15 --repetitions 20 --shots 2048 --engine reduced --counting-mode qpe_ideal --counting-precision 8 --counting-shots 256 --output results/reference_qpe.csv
```

Here the M estimator is *sampled from the mathematically exact finite-precision quantum phase estimation distribution*, not executed as a controlled-Grover circuit. This tests how finite counting precision perturbs suppression accuracy but does NOT measure counting resource costs.

### Additional protocol — measurement noise proxy

```powershell
python -m ross_bench.campaign --nodes 4 10 15 --repetitions 20 --shots 2048 --engine reduced --readout-flip 0.01 --output results/reference_readout.csv
```

`--readout-flip 0.01` independently flips each **measured bit** with 1% probability; it is NOT a gate noise model nor the IBM Brisbane profile. A useful control is 0.00, 0.002, 0.01, and 0.03.

## Step B — build *real* Qiskit circuits and inspect resource budgets

```powershell
python -m ross_bench.inspect_resources --nodes 4 10 15 --output results/circuit_resources.csv
```

The command constructs the time evolution, exact phase marking and search circuit and records their widths, raw composite depth and size; it does not execute shots. `--transpile` adds transpiled depth/size/2-qubit gate count, possibly costly for large cases.

## Step C — execute Aer shot experiments

**Start with the uploaded 4-gene benchmark:**

```powershell
python -m ross_bench.campaign --nodes 4 --families rossini4 --engine aer --counting-mode exact --repetitions 10 --shots 1024 --output results/aer_rossini4.csv
```

**Extend to the realistic low-transient 10-gene cases:**

```powershell
python -m ross_bench.campaign --nodes 10 --families projection skewed cycle2 --engine aer --counting-mode exact --repetitions 10 --shots 1024 --max-sim-qubits 24 --timeout 300 --output results/aer_10.csv
```

**15-gene low-transient circuits need 30 evolution-register qubits.** A double-precision full statevector requires at least ~16 GiB *for amplitudes alone*. For Qiskit Aer matrix product state on your own machine, the circuit may or may not be efficient depending on entanglement:

```powershell
python -m ross_bench.campaign --nodes 15 --families projection skewed cycle2 --engine aer_mps --counting-mode exact --repetitions 3 --shots 256 --force-large --timeout 300 --output results/aer_mps_15.csv
```

Use `--force-large` carefully. The `long_chain` families at 10 and 15 nodes need 100 and 225 qubits and **should initially be resource-assessment only**, not presumed feasible simulation tests. A successful MPS simulation is not a device implementation and can have network-dependent performance.

## Step D — real quantum counting as an independent experiment

The pipeline supports:

```powershell
python -m ross_bench.campaign --nodes 4 --families rossini4 --engine aer --counting-mode qpe_aer --counting-precision 3 --counting-shots 128 --repetitions 2 --shots 256 --max-sim-qubits 24 --timeout 600 --output results/aer_with_qpe.csv
```

**WARNING:** Real QPE applies `2^p-1` controlled Grover operators *per counting invocation*, and the counting register increases width by `p`; large runs can be prohibitively slow. This command attempts actual counting and records status/errors/timeouts. The same 4-gene circuit with p=3 has poor counting precision; raising precision is expensive and may need stronger resources. Neither such counting nor its accuracy has been verified on Qiskit here. For credible claims about exactness, characterize failure probability and distinguish finite-p counting from an exact oracle.

## Step E — summarize and plot

```powershell
python -m ross_bench.reports --files results/reference_exact.csv results/reference_qpe.csv results/reference_readout.csv --output-dir results/plots
```

The bundled plots are separate figures: `qubit_scaling.png`, `reduced_reference_runtime.png`, and `readout_error.png`. They are clearly labeled as mathematical reference or resource calculations, **not hardware timings**.

## Synthetic network definitions and controlled variables

| Family | Attractors K | Max transient T | Main stress case |
|---|---:|---:|---|
| `projection` | 8 | 1 | More attractors, equally sized basins |
| `skewed` | 2 | 1 | Imbalanced basins, 3:1 |
| `cycle2` | 3 (including one 2-cycle) | 1 | Correct marking of all cycle states |
| `long_chain` | 2 | n-1 | Transient/width explosion |
| `rossini4` | 5 | 3 | Exactly reproduce 4-gene uploaded baseline |

`projection`, `skewed`, `cycle2` and `long_chain` are **synthetic test networks** and are NOT biologically validated GRNs. Their identical names and rule definitions must be used in future fixed-point and ATLANTIS comparisons. The JSON `attractor_truth` must only be consumed by independent verification, not by an end-to-end quantum solver.

### Primary metrics

- **Time:** per-run construction `search_runtime_s`, simulator time `simulation_runtime_s`, counting time `counting_runtime_s`, total pipeline time `total_runtime_s`; `campaign.py` additionally reports full child process startup (`isolation_wallclock_s`).
- **RAM:** isolated process high-water `peak_rss_mib`; `statevector_gib` is a lower-bound amplitude storage estimate, not measured usage.
- **Quantum resources:** `(T+1)n` register width; optional physical compiled depth/size/two-qubit gates from Aer/transpile. Counting needs p extra qubits and expensive controlled repetitions.
- **Accuracy:** recovered cycles, `attractor_recall`, `false_positive_rate` (non-attractor shots), `wrong_run_measurement_rate` (includes previously excluded attractors), `max_suppressed_leakage`, and `average_M_abs_error`.
- **Experimental design:** repeat over seeds and increasing n; hold the family fixed to isolate n, then hold n fixed and vary family to isolate transient length, number of attractors, presence of cycles, and basin imbalance. Increase repetitions to >=20–30 for a research report.

## Scientifically important limitations

1. The original main experiment uses exact classically computed M and the counting code is independent; this code keeps those cases explicitly separated. Do not report classically supplied M as quantum counting.
2. Neither Qiskit Aer nor an external quantum processor was available in the environment that generated this archive. Optional Qiskit tests are **skipped**, not passed, here. Validate them on your machine before asserting Qiskit correctness.
3. The reduced-reference results confirm the deletion mathematics for *synthetic* networks, not the gate-level implementation, circuit noise robustness, or a quantum speedup.
4. End-to-end classical comparison requires an actual, similarly configured **ATLANTIS MATLAB run** on each identical network. The independent ground-truth enumeration in this archive is not the ATLANTIS software and should not be described as ATLANTIS runtime.
5. Rossini basin suppression is formulated for deterministic synchronous Boolean networks; ATLANTIS probabilistic/stochastic mode is outside the present experimental scope.
6. The pipeline uses a classical verifier to decide if a sampled outcome is an attractor state and to identify all members of its cycle. The verifier traces each measured state using only the Boolean update rules; exhaustive ground truth is used separately for scoring and for exact-M/ideal-reference protocols. This avoids leaking the full attractor list into discovery decisions.
7. **Crucial fairness limitation:** full quantum speed claims require the cost of `M` estimation, suppression and extraction, including compilation, gate depth, shots and noise. A 15-node *small-T* example is not a general large-network result.

## Next fixed-point comparison

The JSON rules are the agreed input contract for both approaches: `node_order`, `rules`, `model_type`, `n`. The output contract is attractor cycles (canonical bitstrings), basin info when produced, certainty/error, time, RAM and quantum resource metrics. The fixed-point method will need an independently verified cycle oracle, not only `F(x)=x`.
