# Integration audit — 8 November 2026

Baseline archives remain untouched in C:/Bio_research. The Python port was found
in ATLANTIS_Python.zip; this project extends that port, rather than reconstructing
it. Historical validation/ outputs shipped with the archive are not fresh results.

## Source inspection

* Python model: weighted source-to-target matrix, zero sum retains previous bit;
  truth-table inputs are MSB first. Supports arbitrary display names and >150 nodes.
* Existing desktop: Qt GUIDE reconstruction, import/edit/mutations, deterministic
  and probabilistic workers, landscapes, CSV/JSON/MAT exports. No quantum integration.
* MATLAB probabilistic transition formula is .5+.5*tanh(noise*input), with
  degradation c / 1-c at zero input. The Python port preserves it. Pruned matrices
  are substochastic; the flux update retains missing mass on the diagonal rather
  than renormalizing rows. Historical convergence permits 98% component agreement.
* Python rules deterministic output sorts cycle states, losing traversal order.
  Rules basin fractions condition on resolved trajectories, unlike weighted mode.
* Ross adaptive module does not use known attractor count to control discovery.
  Legacy runner uses exhaustive truth for benchmarking and exact-M settings.
* Ross Network.create limits n to 30, and compiler expands up to six-input truth
  tables. These are implementation limits, not biological or quantum limits.
* Reduced reference explicitly enumerates F^T and simulates n amplitudes; full
  circuits retain (T+1)n qubits plus precision for counting. They are different costs.
* T is caller supplied. Repeated finite QPE coverage is heuristic. Classical audit
  is exhaustive certification, never quantum certification.
* Candidate verification in supplied Ross code is unbounded. Resource checks are
  in benchmark runner rather than the reusable algorithm. Neither is suitable for
  arbitrary uploaded models without a bounded integration layer.
* Circuit resource field named physical_qubits actually records logical circuit
  width; gate-name based two-qubit counts omit other two-qubit instructions.
* Desktop jobs are threads with cooperative cancellation; results are only durable
  on export. No IBM account/runtime support is present.
* 201-node supplied datasets have missing tables. Existing explicit identity-rule
  opt-in is retained; full biological equivalence remains unestablished.

## Baseline execution

System Python baseline Ross pytest failed at collection: mixed Qiskit >=1 and
qiskit-terra installation. A separate .venv-atlantis is being established; the
system environment is not modified. Fresh XML reports will record rerun outcomes.

## Scientific sources

Original MATLAB source and port source/documentation; Ross supplied adaptive,
reference, model and circuit modules; official author repository
https://github.com/sysbio-bioinf/QuantumAttractorSearch (cloned under research_sources).
The official optimalphi2 agrees with supplied J and phi formulas. Its five-gene
Giacomantonio2010 rules are used as an independently sourced fixture.
Paper: https://doi.org/10.1016/j.patter.2025.101295 .
ATLANTIS paper: https://doi.org/10.1038/s41598-018-22031-3 .
IBM current API: https://quantum.cloud.ibm.com/docs/en/guides/get-started-with-sampler .

## Delivery policy

Keep legacy behavior accessible. Add explicit corrected semantics where needed.
Do not submit paid hardware work. Live QPU verification remains pending credentials
and explicit authorization. Record incomplete acceptance criteria in handoff.
