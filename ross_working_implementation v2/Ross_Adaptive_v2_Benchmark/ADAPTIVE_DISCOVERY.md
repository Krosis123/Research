# Rossini adaptive discovery — v2 experimental protocol

## What changed

The original pipeline is retained, unmodified in behavior, as `--discovery-mode legacy`
(the default for backward compatibility). This reproduces the results already collected,
but it **uses exhaustive truth to choose** the number of discovery rounds, the transient
bound `T`, and (with `--counting-mode exact`) the removed basin size `M`. **Do not
represent the legacy benchmark as autonomous.**

New: `--discovery-mode adaptive` runs a search until its own termination policy
fires or a configured limit is reached. It never uses `exact_truth()` to select
`T`, the number of rounds, the excluded cycles, the QPE phase or suppression
parameters. The network rules and `T` are supplied explicitly, a candidate
attractor is verified by tracing its **one measured state**, and any full-graph
truth is computed **after** the solver exits, for scoring only.

### Input and termination

- **T is user-specified** with `--evolution-steps T`; no general efficient method
  for choosing a tight sufficient `T` has been established. `T >= 2^n-1` is a
  sufficient finite-state upper bound, but would make a Rossini circuit generally
  infeasible. `T=3` is suitable for the previously tested Rossini four-gene
  case; `T=1` for the synthetic `skewed` and `cycle2` cases. The benchmark must
  NOT look up a true `T` internally when adaptive mode is selected.
- **QPE termination** (`--stop-policy qpe`): after a candidate is found, the
  full excluded-basin fraction is estimated with the selected counting mode.
  To stop, **all** of at least two separate counting calls must estimate
  `M == 2^n` with at least 95% of their mapped measurement mass there
  (`--stop-confirmations 2 --min-full-fraction .95`). A finite-precision QPE
  response cannot **certify** that no unknown basin remains. The resulting
  `complete_qpe_heuristic` flag means *probabilistic/heuristic* completion, not
  proof. Do not describe this as an exact completeness test.
- **Exact classical audit** (`--stop-policy classical_audit`): independently
  evaluate `F^T(x)` for **all** `2^n` initial states, and check that every
  resulting state belongs to a discovered attractor. If true, completeness
  is mathematically certified; otherwise searching continues or returns
  `inconclusive`. This costs at least `O(2^n*T)` *classical* work and cannot
  demonstrate any quantum speedup.
- **Bounded search** (`--max-rounds`, `--search-retries`): avoids an infinite
  loop and labels exhausted runs `inconclusive_*`. It NEVER labels a mere
  iteration limit as success. If `T` is too short, a run may be inconclusive
  even after discovering every genuine attractor.
- **Candidate validation** traces **only one measured outcome**, rejects
  transient states, and canonicalizes the entire fixed-point or cyclic orbit.
  One new attractor is kept per search round. The entire list of true
  attractors is not consulted in these decisions.

## Two runnable PowerShell examples

Activate your existing `C:\Bio_research\Implementation\rossini_qiskit\.venv`
first, then `cd` into the extracted benchmark root containing `ross_bench`.

### 1. Small, fast and exactly certified *hybrid* test

This uses actual Aer **search circuits**, but supplies basin counts and checks
coverage by explicit classical computation. This is the most reliable first
smoke test of the rewritten stopping logic:

```powershell
python -m ross_bench.campaign `
    --nodes 4 --families rossini4 `
    --discovery-mode adaptive --evolution-steps 3 `
    --engine aer --counting-mode exact `
    --stop-policy classical_audit --truth-mode report `
    --max-rounds 8 --repetitions 1 --shots 512 `
    --max-sim-qubits 22 --timeout 300 `
    --output results/adaptive_aer_rossini4_verified.csv
```

Expected logical outcome: 5 cycles, `complete_classically_certified`, true
recall 100%. The actual Aer execution must still be tested on Windows.

### 2. Actual Aer QPE and self-stopping (NO full-graph oracle in control flow)

```powershell
python -m ross_bench.campaign `
    --nodes 4 --families rossini4 `
    --discovery-mode adaptive --evolution-steps 3 `
    --engine aer --counting-mode qpe_aer `
    --counting-precision 5 --counting-shots 128 `
    --stop-policy qpe --stop-confirmations 2 `
    --min-full-fraction 0.95 --truth-mode report `
    --max-rounds 8 --search-retries 2 `
    --repetitions 1 --shots 512 `
    --max-sim-qubits 22 --timeout 600 `
    --output results/adaptive_aer_rossini4_qpe.csv
```

Unlike the prior benchmark, this executes counting **after the last discovered
attractor** to decide whether to terminate. It may be markedly slower than the
original four-gene QPE timings and can return `inconclusive_*` for finite-shot
errors; these are legitimate outcomes. A `complete_qpe_heuristic` status does
not equal an exact proof, regardless of reported perfect recall.

### 3. Test the control logic without Qiskit

```powershell
python -m pytest tests/test_adaptive.py -v
python -m ross_bench.campaign --nodes 4 --families cycle2 `
    --discovery-mode adaptive --evolution-steps 1 `
    --engine reduced --counting-mode qpe_ideal `
    --counting-precision 5 --counting-shots 256 `
    --stop-policy qpe --repetitions 3 --shots 512 `
    --output results/adaptive_reduced_cycle2.csv
```

`reduced` uses a mathematically exact **n-qubit phase surrogate** and is
NOT a simulation of the full `n*(T+1)` search+counting circuit. In adaptive
mode it enumerates `F^T` internally as part of computing the reference
probability distribution, and `qpe_ideal` enumerates marked states to simulate
finite-precision QPE: **neither is a quantum performance measurement.**

## CSV fields and interpretation

New fields: `discovery_mode`, `evolution_steps_source`, `stop_policy`,
`status`, `completion_reason`, `completeness_certificate`, `discovered_cycles`,
`history_json`, `search_attempts`, `counting_calls`, `solver_runtime_s`,
`validation_wallclock_s`, `classical_audit_runtime_s`,
`classical_audit_states_scanned`, `validation_status` and
`actual_all_discovered` (optional *post hoc* check).

The `solver_runtime_s` includes the selected stopping strategy and, if chosen,
any exponential classical completeness audit. `validation_wallclock_s` is
reported separately; for writing about solver runtime, prefer
`solver_runtime_s` to `total_runtime_s`, which also includes evaluation work.

For `--truth-mode none`, the solver NEVER asks for an exhaustive truth graph
and `attractor_recall` / `average_M_abs_error` may be blank. For `report`,
`exact_truth` is called **only after** discovery finishes, and its output never
changes a decision. For `n>18`, exhaustive truth is skipped when unavailable;
the solver result is retained.

`max_suppressed_leakage` is only calculated for the reduced model; for Aer it
is blank because it has **not been evaluated**. Real QPE estimates and the
`wrong_run_measurement_rate` must not be confused with suppression guarantees.

## What still needs further research

1. The bound `T` remains an external choice. User-specified `T=3` does not
   establish general unknown-network attractor completeness.
2. Finite-precision QPE and a finite number of shots do not logically prove
   `M=2^n`; `complete_qpe_heuristic` could be mistaken in rare/imbalanced
   basins. Characterize failure rates; ideally add a principled one-sided
   statistical test or a separately costed independent verification routine.
3. A classical trajectory verifier and candidate post-selection remain; its
   cost and effect on observed recall must be reported.
4. **The full adaptive Aer path is not executed in this source-generation
   environment** because Qiskit/Aer is unavailable here. The new optional
   integration tests will execute in your Windows environment.
5. This is deterministic synchronous Boolean dynamics only. No stochastic
   ATLANTIS mode or speedup against MATLAB ATLANTIS has been demonstrated.

## Reproducibility

The original `original/` code is preserved. The legacy campaign interface
is unchanged unless `--discovery-mode adaptive` is explicitly requested.
Prefer isolated `ross_bench.campaign` for peak-memory measurements, keep raw
CSVs with their companion JSON manifests, and make precision/shot counts,
`T`, and termination policy explicit in any comparison to the fixed-point
oracle.
