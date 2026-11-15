# Verification of this integration

The supplied Python port was found in ATLANTIS_Python.zip and extracted. It was
not replaced with a new application. Both original source archives remain intact.
The initial system-Python Ross test attempt failed due mixed Qiskit generations;
the isolated environment resolved that without modifying system Python.

## Baselines and regressions

* Ross baseline: 18 passed, including actual Aer/QPE tests.
* Python baseline: 111 passed, 5 failed, 1 skipped. All five failures and the skip
  were missing Graphviz after source-only extraction. Restoring the archive's
  bundled runtime resolved them; no scientific test failed in that baseline.
* Final integration regression: **158 passed, zero skipped**.
  The expanded quantum suite contains 34 tests. Final full-suite XML is retained.
* 16 third-party Qt/Matplotlib deprecation warnings remain; no assertion failures.
* pip check: no broken requirements. Python compileall: passed.
* Wheel built and installed into an independent target directory. From that
  directory, Qt assets loaded and a one-node cyclic reference run succeeded.
  This is an installed-package smoke check, not a fresh OS/VM installation test.

## Preserved and changed behavior

Weighted deterministic zero input retains the current bit. Historical probability
formula, degradation behavior, pruning, flux update and 98% convergence criterion
remain. Rules-based stochastic analysis remains rejected. Classical cell-fate,
mutation, landscape, MAT/CSV/JSON and source GUI workflows remain available.

Default deterministic cycle output now preserves traversal order, rotated to its
lexicographically smallest state. Previously it sorted cycle members. Default basin
fractions now retain unresolved initial-state mass in the denominator; the old rules
engine conditioned on resolved states. `historical=True` restores those legacy
reporting behaviors. New tests exercise a non-lexicographic three-cycle and partial
resolution. Existing reference fixtures still pass.

New hard clamps are explicit and distinct from legacy +/-1000 basal perturbations.
Hard clamps are supported in deterministic and quantum dynamics; historical
probabilistic mode rejects them because no equivalent original stochastic definition
is established. Existing basal perturbations remain available there.

Added validated expression parsing, bounded symbolic ANF, a unified quantum adapter,
resource preflight, bounded candidate verification, subprocess cancellation, durable
quantum results, saved input snapshots/hashes, raw measurements, exact-M disclosures,
IBM ephemeral accounts/submission guards, and side-by-side exact comparison.
Unsafe truth-table export filenames now fail with a JSON-export alternative.

## Biological validation boundaries

Fresh tests compare yeast deterministic/fates/probabilistic results to bundled
MATLAB fixtures and MCF-7 Control/Nutlin results to archived attractor tables.
These reference files predate this integration; MATLAB itself was not rerun.
Case Studies 3 and 4 load 201-node models and supplied 10,000-state inputs, and
test transition shape/Boolean validity. They do **not** reproduce complete published
tumorigenesis/HCT-116 intervention results. Seventeen missing truth tables require
the port's explicit identity-rule opt-in, which is not scientifically certified.

The follow-up check processes all 10,000 input rows in each of the six supplied
simulation files and searches the first 128 rows per file for attractors with a
100-step horizon. The two studies ship byte-identical network details and matching
simulation files, so these runs cover three distinct input files and one rule set.
The 17 identity fallbacks include four phenotype nodes. See
`validation/large-biological-smoke.json` for counts and fallback names and
`tools/check_large_cases.py` for reproduction.

## Remaining incomplete work

Full large biological phenotype/perturbation reproduction; complete supplementary
methods review; live IBM execution and real account recovery; calibrated device
noise; full precision/shot/imbalance sweep; isolated per-run memory across the entire
benchmark matrix; raw per-seed circuit histories for every matrix entry; broader
platform and accessibility verification; automated continuation of interrupted hardware discovery;
server/multi-tenant authentication; shared-ancilla circuit synthesis optimization.
These are not claimed complete by the package or its test count.

See [the 0.2.2 follow-up](SCIENTIFIC_VERIFICATION_022.md) for the corrected missing-node policy and sampled biological comparison.
