# ATLANTIS–Quantum 0.2.3 scientific verification

## Biological reproduction

### Colorectal tumorigenesis

The archived MATLAB rules engine follows each supplied initial state for
`AttractorSearchDuration` updates and records the first repeated state and
the cycle that precedes it. It removes unresolved rows, groups resolved cycles
by sorted state membership, and passes their labels to `attractorFrequency`.
Each resolved input contributes one count. The basin denominator is the number
of resolved inputs in that run. This is a resolved-conditional estimator.
Fate rows may represent combined labels. Counting the Normal Proliferation
label within a combined category answers a different question from counting
the exact standalone category. The default Python result also reports
unresolved mass against the full input count. Historical comparison uses the
archived resolved denominator explicitly.

The 10,000-row final mutation archive has 9,977 resolved trajectories at
200 updates. The six category probabilities agree with the archived MATLAB
CSV to its saved precision, with total variation 0.00000372. The same bound
was checked against the original Python single-trajectory detector for all
23 unresolved inputs. Extending only those trajectories found a repeat for
all 23 between updates 201 and 338. Their transient lengths were 11–128 and
their periods were 120, 140, 210 or 240. The original 200-update comparison is
unchanged. Finite deterministic networks must eventually repeat, and these
cases were insufficiently bounded. [Per-row diagnostic](../validation/colorectal-unresolved-023.json)

Each condition was replayed over each supplied 10,000-row list. The numbers
below use standalone Normal Proliferation and the resolved denominator.

| Mutation sequence | Simulation 1 | Simulation 2 | Simulation 3 | Mean | Published |
|---|---:|---:|---:|---:|---:|
| Control | 73.07% | 79.00% | 78.65% | 76.91% | 79% |
| APC | 73.03% | 78.98% | 78.61% | 76.87% | 79% |
| APC + Ras | 32.42% | 39.20% | 39.10% | 36.90% | 39% |
| APC + Ras + PTEN | 32.34% | 40.78% | 40.73% | 37.95% | 41% |
| APC + Ras + PTEN + p53 | 6.63% | 1.35% | 1.17% | 3.05% | 1.3% |

The paper describes three-list averaging, but its reported series agrees
closely with the ATLANTIS-generated lists individually. The Cho-origin list
has a different empirical input distribution and yields different results
under the same update and classification code. The source, supplement and
one available MATLAB archive establish per-run computation but do not establish
which list or weighting produced the published mutation series. No aggregate
was adjusted to fit it. [Paper and supplements](https://pmc.ncbi.nlm.nih.gov/articles/PMC5824948/) · [All replicate counts](../validation/colorectal-three-replicates.json)

### Node semantics

The 13 input nodes are exogenous. The supplied condition CSVs fix their values
for each case. An explicitly external node can instead retain its supplied
starting value per trajectory. Deterministic searches now apply configured
clamps before the initial state enters cycle detection, and synchronous
updates continue to honor them. Mutation update tables still act from the
first update, preserving archived starting values. Quantum analysis embeds
the clamped synchronous map in a full Boolean register and represents each
fixed assignment with equal redundant input multiplicity.

The four phenotype coordinates have no rules, no outgoing dependencies and
no role as classifier inputs. The supplied classifiers derive fate labels
from regulated trajectories. The reproduction scripts check those dependency
conditions before canonicalizing the unused coordinates. The historical
coordinate labels carry no independent biological dynamics. Unspecified nodes
in an imported network require explicit resolution. [Node inventory and source comparison](SCIENTIFIC_VERIFICATION_022.md)

### MCF-7 stochastic comparison

The MATLAB interface specifies noise 5, degradation 0.001, tolerance 10e-8
and 1,000 iterations. These values were used for an eight-condition,
one-step-pruned sweep. Reconstructing from all 65,536 initial states yielded
1,758 and 1,438 pruned states for Control and Nutlin. Their archived state
sets have 694 and 653 rows, respectively. The archival pruning inputs are
not recorded. Replaying the archived sets directly reproduced the exported
probabilities with maximum absolute error 3.80e-6 for Control and 4.56e-6
for Nutlin. The archived CSV mass deviates from unity by a few parts per
million, consistent with export rounding. This is conditional numerical
reproduction on the saved state set.

The triple treatment reproduces the two apoptosis and three senescence
point-attractor labels identified in Figure S10. Their five computed
probabilities are in the raw record. Exact reference probabilities for that
figure and its original pruned state set were unavailable for vector replay.
Three of the four Etoposide-background conditions hit the 1,000-step cap.
Several other conditions met the historical rule at 11 iterations, despite
nontrivial componentwise drift. For example, Nutlin has maximum one-step
change 0.00129 and the triple treatment 0.000655. The GUI and JSON export now
report the maximum one-step probability change alongside the historical 98%
stopping flag. It remains possible for a few high-mass states to exceed the
tolerance when that flag is true. [Raw stochastic records](../validation/mcf7-stochastic-023.json)

### HCT-116 and experimental comparison

On the full 10,000-row list, control marginal apoptosis was 41.79%.
The seven highlighted interventions give 84.52% AKT, 99.80% EGFR,
100.00% ERK, 86.59% MDM2–p53, 99.30% MEK, 88.85% PI3K and 92.00% RAF.
That is approximately 2.02–2.39 times the untreated model propensity. The
complete counts cover all 16 interventions, five possibly overlapping fates,
and unresolved rows. The fraction denominator here includes all 10,000
starts. Figure 6f reports measured drug concentrations at 50% growth inhibition.
These concentrations and simulated fate fractions have different units and
endpoints. No quantitative calibration or exact GI50 table was available in
the supplied data, so the reported comparison remains directional.
[HCT-116 counts](../validation/hct116-full.json) · [Figure 6 and methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC5824948/)

## Rossini verification and network generality

The reference derivations and cited official code in
[Quantum correctness](QUANTUM_CORRECTNESS.md) remain the mathematical
baseline. The compiler embeds the map as reversible XOR into a fresh
register per update. Register mapping follows the ordered node list with
the last gene in the low bit. Hadamard initialization is uniform; backward
evolution uncomputes intermediate states after the conditional terminal-state
phase. Exact basin suppression requires the correct marked count and enough
updates for basin states to enter their cycles. A cyclic basin requires
marking every state of the cycle. These conditions are independent of
the biological labels.

New independent Boolean oracles enumerate all 60 basis inputs across four
seeded networks of two to five nodes, including nested expressions and
sparse and dense feedback. The tests verify complete forward registers,
inverse recovery and basin partitions for two renamed orderings. Aer
executed 240 basis circuits with four shots per circuit. A separate
three-node example uses genuine Aer QPE to discover a point and a cycle,
with exhaustive classical terminal enumeration disabled in the discovery
path. The application still validates individual candidates classically.
Noise and physical hardware are separate execution modes.

For 2-bit ideal QPE, counts of 255 and 256 out of 256 share the same modal
outcome. The near-full count puts more than 95% of the mass in that bin,
so increasing shots alone can reinforce a false full-coverage inference.
A one-state marked basin can similarly share the zero-count mode. These
are analytical adversarial checks. A high-attractor-count Aer run exhausted
a one-round budget and reported an inconclusive status. Earlier actual QPE
experiments for a 3:1 split and existing insufficient-T tests remain in
scope. Adaptive QPE stopping is explicitly heuristic. Classical audit can
certify a finite coverage claim at the configured horizon at an exponential
cost. Dense Boolean synthesis can also expand exponentially and is guarded.

## Optimization and benchmarking

The paired study executes 36 MPS-backed circuit measurements on six
configurations, varying 3–5 nodes, fan-in, 1–3 updates, and 1–3 suppressed
basins. It compares transpiler levels 0 and 2 on identical circuits and seeds.
All 24 search circuits had zero sampled suppressed-state leakage at 512 shots.
Across equal paired search runs, level 2 reduced summed two-qubit gates from
1,302 to 1,254, while median wall time changed from 47.4 to 49.1 ms. Across
12 QPE runs, it reduced summed two-qubit gates from 17,106 to 15,786, while
median wall time rose from 0.715 to 0.796 s. It was therefore kept as a
measured alternative to the unchanged baseline. RSS is observed at 5 ms
intervals and is process-wide. Brief peaks may be missed.

The data include raw and compiled depth and gates, logical and transpiled
width, ancillas, construction, transpilation, Aer execution, and measured
wall time. The earlier matched runs compare reference, classical, Aer, noisy
Aer, QPE and MPS. On these sizes, direct classical analysis remains more
practical in elapsed time. No physical speed comparison was made.
[Raw data](../validation/optimization-023.json) · [Gate scaling plot](../validation/optimization-023.png)

## Acceptance matrix

| Requirement | Status | Evidence and limits |
|---|---|---|
| Missing-node semantics | Verified | Original tables, explicit input/clamp policy, classifier dependency audit and time-zero clamp regression |
| Archived colorectal replay and 23 unresolved inputs | Verified | Six fate proportions and per-row recurrence diagnostics |
| Published colorectal aggregation | Partial | All five conditions and three lists reproduced, exact publication aggregation unavailable |
| MCF-7 stochastic | Partial | Eight executed conditions, archived vectors agree on saved states, three capped runs and incomplete Figure S10 numerical reference |
| HCT-116 | Partial | Full 16-intervention model sweep, experimental concentration calibration unavailable |
| General compiler and inverse | Verified on tested scope | Independent exhaustive oracle, renamed/permuted Aer circuits, genuine QPE mixed attractors |
| Adaptive suppression | Partial guarantee | Exact under stated assumptions, finite QPE alias and bounded stopping documented |
| Optimization | Measured | Modest gate reductions with slower median wall time in this matrix |
| IBM workflow | Verified locally | Fake backend, mocked account/job lifecycle and Qt controls |
| Physical QPU | Unverified | Requires explicit authorization and account access |
| Application and distribution | Verified locally | Automated test XML, native launch and installed Qt workflow, recovery reruns saved inputs |

## Reproduction commands

From the extracted source root, using Python 3.12:

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install ".[quantum,test]"
& .\.venv\Scripts\atlantis.exe
& .\.venv\Scripts\python.exe -m pytest -q --junitxml=validation/final-tests.xml
& .\.venv\Scripts\python.exe tools/follow_colorectal_unresolved.py
& .\.venv\Scripts\python.exe tools/reproduce_mcf7_stochastic.py
& .\.venv\Scripts\python.exe tools/benchmark_optimization_023.py
& .\.venv\Scripts\python.exe tools/estimate_ibm_023.py
```

Graphviz is required for the Graphviz viewer regression tests. The source ZIP
omits the binary and uses a system installation if present. The validated
workspace had Graphviz available. The full suite passed 167 tests with no skips
and 16 Qt/Matplotlib deprecation warnings. [Test XML](../validation/final-tests.xml)
