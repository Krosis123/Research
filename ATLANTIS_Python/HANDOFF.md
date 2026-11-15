# ATLANTIS–Quantum handoff — 8 November 2026

**A working integrated desktop application is delivered, but the entire requested
research programme is not complete.** The remaining acceptance gaps are listed
below rather than being treated as verified functionality.

## Start

In this workspace:

```powershell
cd C:\Bio_research\ATLANTIS_Python
C:\Bio_research\.venv-atlantis\Scripts\python.exe run_atlantis.py
```

For a new installation, run install_windows.bat, then launch_atlantis.bat, or follow
docs/QUANTUM_USER_GUIDE.md. Use Python 3.12 and the integration lock file. Graphviz
is an external dependency for SVG layouts; the source package excludes binaries.

## Delivered

The supplied Qt application now exposes Rossini reference, full Aer, noisy Aer and
IBM-account workflows on its existing network model. Expression parsing, symbolic
ANF, weighted conversion, point/cycle verification, QPE, bounded/heuristic/classical
certification statuses, preflight limits, durable quantum jobs, cancellation,
comparison, plots and JSON export are implemented. Original classical functionality
and archived sources are preserved. IBM submission is guarded by an explicit paid
execution confirmation and tested with mocks; no QPU was accessed.

The primary matrix contains 738 records, plus 20 isolated five-gene MPS records.
There were 738 completed runs and 20 deliberate memory-budget rejections. Rossini4
median times: classical exhaustive 0.000748 s (20 repeats), reference 0.001319 s
(20), exact-M Aer 0.749 s (20), actual-QPE Aer 45.839 s (3), noisy Aer 41.265 s (3).
All executed runs in this matrix recovered all independent reference attractors;
this is limited to the tested cases and does not certify finite-QPE stopping.
No quantum speedup is demonstrated.

## Evidence and reproduction

See [0.2.2 scientific verification](docs/SCIENTIFIC_VERIFICATION_022.md) for the 17-node audit, sampled biological results, matched benchmark and acceptance matrix.

The 0.2.4 full suite recorded **175 passed, zero skipped**. The 24 warnings
come from third-party Qt/Matplotlib deprecated high-DPI attributes. Original
`MANIFEST.json` and older validation images are archive provenance, not current
verification; use the explicitly named integration manifest and current reports.

* `docs/INTEGRATION_AUDIT.md`: source/dependency/scientific baseline audit.
* `docs/VERIFICATION_CURRENT.md`: preserved features, fixes and compatibility limits.
* `docs/QUANTUM_CORRECTNESS.md`: formulas, bit order, test scope and uncertainty.
* `docs/BENCHMARK_CURRENT.md`: measured statistics and limitations.
* `docs/QUANTUM_USER_GUIDE.md`: Windows setup, input format, API and IBM guide.
* `validation/final-tests.xml`: authoritative full test results.
* `validation/integration-expanded.xml`: 34 focused integration tests.
* `validation/baseline-python.xml`, `baseline-ross.xml`: original baseline outcomes.
* `validation/benchmark-current/`: raw CSV/JSONL, histories, summaries, chart.
* `validation/benchmark-five-mps/`: all 20 actual circuit histories and durable jobs.
* `validation/demo-current/`: classical/reference/Aer exports and 150-node rejection.
* `validation/integration-ui/`: rendered main, comparison and measurement windows.
* `validation/integration-file-manifest.json`: exact created/modified source paths
  and SHA-256 hashes compared to the supplied Python archive.

```powershell
python -m pytest -q
python tools/demo_integrated.py
python tools/benchmark_integrated.py --output validation/new-matrix
python tools/benchmark_five_mps.py
```

## Acceptance criteria

| # | Status | Evidence / remaining condition |
|---|---|---|
| 1 | Partial | Isolated environment and installed wheel smoke verified; fresh OS/VM not tested |
| 2 | Verified | Deterministic core, archived fixtures, GUI and large sampled model |
| 3 | Verified within scope | Weighted historical probabilities; rules stochastic rejected |
| 4 | Verified | Quantum action in same Qt application |
| 5 | Verified within limits | Arbitrary supported rules/weights; symbolic/table budgets explicit |
| 6 | Verified core; partial literature audit | Independent distributions and official models; supplement retrieval incomplete |
| 7 | Verified | Actual Aer, QPE and 25-qubit MPS executions |
| 8 | Verified tested cases | Bounded/heuristic/certified distinctions; no finite-shot proof claim |
| 9 | Verified | Canonical ordered cycles, complete-cycle marking, cyclic regression |
| 10 | Verified supported inputs | Safe AST and format validation; archive uploads not offered |
| 11 | Verified | 150-node rejection before construction; classical still usable |
| 12 | Partial biological scope | 150-node sampling verified; full 201-node biological results not reproduced |
| 13 | Implemented/mock-tested | Current Runtime service and client-side Sampler; full live interoperability pending |
| 14 | Explicitly unverified | No physical QPU submission or hardware result |
| 15 | Measured, incomplete publishable protocol | Raw results present; broader sweeps/per-run memory and complete instrumentation pending |
| 16 | Verified design/mock scope | Ephemeral credentials, no save_account, sanitized connection errors; not a multi-user server audit |
| 17 | Verified | Tests, instructions, sample models, reproducible scripts |
| 18 | Delivered | Source, wheel, reports, artifacts and file manifest |

Right-click the main window and choose **Recover Classical Job** to rerun saved
inputs after interruption. This restarts the solver from the beginning.

Hardware recovery retrieves individual provider jobs but cannot
automatically resume adaptive discovery; no server API/multi-tenant service;
exact published colorectal aggregation, HCT-116 experimental comparison, and shared-ancilla optimization
are unfinished. A previous-state Bayesian or probabilistic landscape is never
invented from quantum measurement frequencies.

The next research work should prioritize missing biological model definitions,
independent supplement review, larger QPE precision/shot sweeps, backend-calibrated
noise, and explicitly authorized hardware validation. Those gaps prevent calling
this the fully completed research programme requested in the specification.

See docs/SCIENTIFIC_VERIFICATION_023.md and docs/IBM_READINESS_023.md for the 0.2.3 evidence, remaining limits and acceptance matrix.

See [0.2.4 scientific verification](docs/SCIENTIFIC_VERIFICATION_024.md) and [hardware plans](docs/IBM_READINESS_024.md) for the current evidence and limits.
