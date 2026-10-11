# Preliminary benchmark results — generated from the uploaded Ross reproduction

## Verified source facts

- The original Python source is a **four-gene** rather than a three-gene Rossini reproduction.
- It correctly defines the core Boolean update rules `A'=A&D`, `B'=A&B`, `C'=C&D`, `D'=B|C`.
- Exact classical graph enumeration confirms attractor sizes `0000:11, 0011:2, 1011:1, 1101:1, 1111:1`, with T=3.
- The source's `experiment_rossini.py` uses **classically known M**; `experiment_counting.py` separately estimates M with QPE. This distinction must be preserved in any claims about complete algorithm runtime.

## Newly added reproducibility protocols

1. **Ideal exact-M reduced-state validation:** `results/ideal_exact.csv`, 39 successful runs (4-, 10-, and 15-gene controlled tests; 3 repetitions each). For every run, all K attractors were identified. Maximum suppressed-state leakage is at floating-point roundoff level. This verifies ideal mathematics only.
2. **Finite precision QPE mathematical model:** `results/ideal_qpe_estimated.csv`, 39 successful runs. Under an ideal QPE outcome distribution with p=8, even a small M estimation error can create nonzero suppression leakage; `average_M_abs_error` and `wrong_run_measurement_rate` record it. **No QPE gates executed.**
3. **Readout-flip proxy:** `results/readout_flip_1pct.csv`, 39 successful runs. This independently flips each measured gene with probability 1%. Average *wrong/previous-attractor output measurement fraction* is approximately 9–10% in the 10-gene experiments and 13–15% in the 15-gene experiments. This is not a calibrated quantum noise model.
4. **Independent process resource timing:** `results/isolated_exact.csv`, 26 successful mathematical-reference cases; every process reports its own `peak_rss_mib`. The baseline uses about 95–100 MiB of peak RAM in these local tests; this is **not** the memory demand of the full Qiskit circuit.
5. **Static hardware/memory estimate:** `results/resource_scaling_estimates.csv`, accounting for the explicit Qiskit evolution registers, *not* a hardware measurement.

All reference accuracy tests use full 2^n ground truth for independent assessment. The extraction verifier traces one measured state using the update rules; it does not consult the ground-truth attractor list to decide what to accept. In exact-M mode, however, the search **does use** classically computed total M as Rossini's suppression input; it is not an end-to-end quantum implementation.

## Scalability table

| Synthetic family | n | K attractors | T max transient | Evolution qubits | Full statevector amplitude storage |
|---|---:|---:|---:|---:|---:|
| projection | 10 | 8 | 1 | 20 | 16 MiB |
| skewed | 10 | 2 | 1 | 20 | 16 MiB |
| cycle2 | 10 | 3 | 1 | 20 | 16 MiB |
| long_chain | 10 | 2 | 9 | 100 | astronomically large |
| projection | 15 | 8 | 1 | 30 | 16 GiB |
| skewed | 15 | 2 | 1 | 30 | 16 GiB |
| cycle2 | 15 | 3 | 1 | 30 | 16 GiB |
| long_chain | 15 | 2 | 14 | 225 | astronomically large |

More precise resource estimates in the CSV; large figures are deliberately *not* treated as feasible simulator targets. The long-chain reference code still executes quickly because it replaces `T†PT` algebraically: this **must not** be mistaken for the efficiency of the 225-qubit Rossini quantum algorithm.

## Status of actual quantum implementation

- Generalized n-gene Qiskit circuits are provided in `ross_bench/circuits.py`.
- Real Aer shot experiments and quantum counting are supported by `ross_bench/campaign.py` with safe width caps and timeouts.
- **Not executed in this environment:** Qiskit and Qiskit Aer are unavailable, and dependencies could not be downloaded.
- Qiskit-specific tests exist but were **skipped**. No hardware runtime, gate-level empirical error, transpilation depth, or true full-circuit memory claim is justified by these files until executed on the user's machine.

## What remains before selecting an ATLANTIS quantum option

Run Qiskit circuit experiments first on 4 genes, then n=10, then only attempt n=15 with careful matrix-product-state or resource estimation. Carry over exactly these same rule JSON files for fixed-point experiments. Compare whole search costs, including counting, suppression, measurements and verification; then run ATLANTIS's own deterministic MATLAB analysis on the *same* networks for a fair classical baseline. The 201-node ATLANTIS experiment from the paper is not equivalent to exhaustive attractor enumeration.
