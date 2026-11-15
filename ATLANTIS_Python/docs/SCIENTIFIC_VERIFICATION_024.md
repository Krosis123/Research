# ATLANTIS–Quantum 0.2.4 verification

## Independent discovery experiments

The audit runs actual Aer MPS circuits for state preparation, evolution,
QPE counting, suppression and repeated measurement. The six seeded networks
have two to four nodes and truth tables with fan-in two to four. Their Boolean
expressions are generated from the same input tables that the independent
oracle evaluates directly. The oracle enumerates transitions only after the
run. Test guards cause exhaustive terminal enumeration or exact-truth calls
inside genuine discovery to fail. Neither basin sizes nor the expected
attractor count are passed to the run. T, seeds and shot counts are specified
by the experiment. The candidate validator can follow one measured state
classically. The longer-horizon comparison was designed after the initial
experiment and is reported as a follow-up.

| Experiment | Runs | Oracle exact matches | Heuristic completion | Inconclusive | False completion signals |
|---|---:|---:|---:|---:|---:|
| Six randomized fixtures, 32 and 128 shots | 24 | 24 | 4 | 20 | 0 |
| Three fixtures repeated at longer horizons | 12 | 12 | 12 | 0 | 0 |
| 15:1 stress case, 16 and 128 shots, one QPE bit | 16 | 0 | 0 | 16 | 0 |
| 15:1 stress case, four shots, one QPE bit | 8 | 0 | 4 | 4 | 4 |

No run reported an invalid attractor or accepted the same attractor twice.
The first randomized group measured already discovered cycle states 352
times. The longer-horizon follow-up measured them 194 times. Imperfect
suppression and repeated observations are counted separately from accepted
duplicates. Every stress trial missed one attractor. In the 16/128-shot
stress group, some four-bit measurements reached the rare basin first and the
coarse QPE then estimated zero marked states. The usual case discovered the
large basin and QPE estimated all 16 states marked even though only 15 were.

The initial random trials include cycles of periods 2 and 3, point attractors,
multiple basins and transient lengths up to 7. Five short-horizon configurations
could leave trajectories outside known cycles at their final register.
Recovering the correct attractor set by post-hoc enumeration is compatible
with an inconclusive engine status because the engine does not know the
true set. The 12 follow-up runs cover longer horizons for three of those
configurations and are not independent additional networks.

QPE error is measured against the count of initial states whose terminal
register at T is in the actual marked set, which can differ from the full
basin size when T is short. Mean absolute errors were 0.95 over 40 count calls
in the initial random group, 0.25 over 32 calls at longer horizons, and one
state in both stress groups. Raw phase and count histograms are retained.
For the 4/8 false heuristic completions, the descriptive Wilson interval is
21.5–78.5%. This small, deliberately chosen stress fixture does not estimate
a population-wide error rate. An oracle exact match is a retrospective score.
No trial in this matrix used the exact classical coverage certificate.

[Summary](../validation/discovery-summary-024.json) · [Random trials](../validation/discovery-024.json) · [Longer horizon](../validation/discovery-longer-024.json) · [Stress trials](../validation/discovery-adversarial-024.json) · [Four-shot trials](../validation/discovery-low-shots-024.json)

## Rossini mathematical audit

| Stage | Implementation and check | Interpretation |
|---|---|---|
| State preparation | Hadamards on the initial register, fresh time registers start at zero | Uniform Boolean starts in the original construction |
| Reversible evolution | Boolean algebraic-normal-form monomials XOR into fresh targets | Embeds each synchronous step without erasing its source |
| Inverse | Circuit inverse reverses each step and uncomputes intermediate registers | Verified on independent, permuted basis tests from the baseline |
| Register ordering | Last gene is the low bit, output measured from the terminal register | Renaming and reordering tested independently in v0.2.3 |
| Phase operator | X conjugation and multi-controlled phase select exactly one state | Phase matrix verified at every four-bit basis index. Malformed masks and duplicate marks now rejected |
| Suppression | Terminal mark, uncompute, uniform-state phase and forward evolution | Rossini construction. Exact deletion assumes the correct marked count and applicable T |
| Counting | Controlled powers of Grover, inverse QFT, phase-bin decoding with sin-squared mapping | QPE circuit, without exhaustive terminal enumeration in this mode |
| Iterations | J from the ceiling formula in supplement S3, phase from its suppression formula | Equivalent sign convention documented in the baseline audit |
| Cyclic attractors | Individual trajectory reconstruction, followed by marking every state of the cycle | Supplement S4 test passes. Partial-cycle marking would represent a different oracle |
| Stopping | Bounded runs, repeated finite QPE or optional exhaustive classical coverage | ATLANTIS extensions. Finite-shot signals can be wrong, even after confirmation |

With true marked fraction M/N, the Grover eigenphase angle satisfies
sin²(theta)=M/N. A finite QPE grid cannot resolve arbitrarily close counts.
The implementation pools conjugate phase bins after rounding their decoded
counts. Its modal count does not represent an interval or a confidence bound.
When a rounded count is zero or N, the intermediate suppression formula
cannot be applied. A plausible full-coverage signal is a heuristic with the
failure mode measured above. Additional shots do not remove phase-grid bias.
The GUI now separates individual classical verification from completeness,
and explicitly labels resource/configuration rejection before circuit execution.

[Baseline derivations](QUANTUM_CORRECTNESS.md) · [Rossini et al. and supplement](https://pmc.ncbi.nlm.nih.gov/articles/PMC12485557/) · [Official implementation](https://github.com/sysbio-bioinf/QuantumAttractorSearch)

## Biological reproduction

All 23 unresolved archived trajectories have now been classified at their
later cycles, with state-set equality checked between the batched and
single-trajectory detectors. They enter cycles with periods 120, 140, 210
or 240 and first repeat at updates 201–338. The combined fate counts are
10 abnormal proliferation plus metastasis, 7 abnormal proliferation,
4 quiescence and 2 metastasis. The archived 200-update proportions remain
unchanged, using 9,977 resolved rows and retaining 23 unresolved rows in
the denominator audit. The later cycles are a separate diagnostic.

For each of the five mutation conditions the audit tabulates the individual
replicates, the described arithmetic mean, and sensitivity to pooled
resolved counts and pooled all starts. The last is a sensitivity check,
because the MATLAB code uses resolved rows. For the final mutation, the
mean is 3.0502%, pooled resolved is 3.0500%, and pooled all starts is 3.0433%,
against 1.3% published. Pooling therefore cannot explain the discrepancy.
Simulation 2 gives 1.3524%, but the archive still does not establish that it
was selected for publication. The available MATLAB code defines per-run
counts and the paper describes averaging. No additional source-supported
publication weighting was located.

| Biological result | Status |
|---|---|
| Final archived MATLAB fate distribution | Reproduced to CSV precision at the original cutoff |
| Late-cycle lengths and combined classifications | Independently checked for all 23 |
| Published mutation sequence aggregation | Partial. Each replicate and candidate denominators compared, exact publishing procedure unavailable |
| MCF-7 archived Control and Nutlin probabilities | Reproduced on archived pruned states, maximum error 4.56e-6 |
| MCF-7 full stochastic protocol | Partial. Original pruning inputs and exact Figure S10 vector unavailable. Three Etoposide-background conditions reach the cap |
| HCT-116 simulated intervention effects | Reproduced direction of the highlighted apoptosis effects. Experimental GI50 calibration remains unavailable |

[Aggregation CSV](../validation/colorectal-aggregation-024.csv) · [Late-cycle classifications](../validation/colorectal-unresolved-024.json) · [Previous biological evidence and source provenance](SCIENTIFIC_VERIFICATION_023.md)

## Resource optimization

In v0.2.3, median QPE transpilation increased from 28.7 to 160.1 ms at
level 2, while median simulation fell from 592.1 to 514.1 ms. Search
showed the same direction at smaller scale. The phase circuit may be
cheaper to execute after optimization, but additional transpiler work
can outweigh that saving.

In the 0.2.4 six-pair, 128-shot randomized comparison, level 2 reduced
summed two-qubit gates from 163,900 to 152,056 and simulation from 37.61
to 32.52 seconds. Total transpilation rose from 2.24 to 11.52 seconds and
median discovery wall time rose from 6.05 to 6.68 seconds. Oracle match
was 6/6 at each level. The three-pair longer-horizon subset also retained
all matches and showed slower median wall time at level 2. Paired evidence
does not justify switching the default. New longer-horizon and stress
records include one-qubit gates, ancillas and sampled process RSS. Older
initial random records contain process RSS snapshots. The 5 ms sampling
can miss brief memory peaks and is not an isolated allocator trace.

The full reversible width is n(T+1), with p extra qubits for counting.
Controlled Grover repetitions grow as 2^p-1. Depth and MPS cost also
depend on Boolean rule fan-in, entanglement, and the number of phase
marks. The default preflight cap is 22 qubits and the configured gate,
depth, and memory limits still apply. A reference simulation and a
physical execution have different resource constraints.

[Stage plot](../validation/optimization-stage-024.png) · [Paired timing summary](../validation/discovery-summary-024.json)

## Acceptance and reproduction

| Requirement | Evidence status |
|---|---|
| Existing 167-test baseline | Preserved in full regression |
| Genuine integrated QPE discovery | 60 pre-guard trials and 56 guarded trials, with explicit incomplete and false heuristic outcomes |
| Mathematical construction | Audited and tested on the documented Boolean scope |
| Universal completeness | Unsupported under finite QPE. Classical audit remains a separate certificate |
| Biological reproduction | Partial beyond archived cases and the new late-cycle diagnostics |
| Hardware lifecycle | Fake provider and installed GUI verified. Terminal, cancellation and uncertain submission states are persisted separately |
| Physical hardware | Unverified. Experiments are prepared offline |
| Installed application | Native launch plus automated Qt workflow, labels, export/reopen, guard rejection and credential controls |

The full suite recorded 175 passes, zero skips, and 24 Qt/Matplotlib
deprecation warnings. The installed workflow exercises real Qt widgets
with automated file selection and runs offscreen. Restart recovery
reruns saved inputs. An interrupted hardware submission with unknown
acknowledgement requires inspection and does not auto-resubmit.

From the extracted source root on Python 3.12:

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install ".[quantum,test]"
& .\.venv\Scripts\atlantis.exe
& .\.venv\Scripts\python.exe -m pytest -q --junitxml=validation/final-tests.xml
& .\.venv\Scripts\python.exe tools/validate_discovery_024.py
& .\.venv\Scripts\python.exe tools/validate_discovery_024.py --longer
& .\.venv\Scripts\python.exe tools/validate_discovery_024.py --adversarial
& .\.venv\Scripts\python.exe tools/validate_discovery_024.py --adversarial --low-shots
& .\.venv\Scripts\python.exe tools/summarize_discovery_024.py
& .\.venv\Scripts\python.exe tools/follow_colorectal_unresolved.py
& .\.venv\Scripts\python.exe tools/compare_colorectal_aggregation.py
& .\.venv\Scripts\python.exe tools/prepare_ibm_024.py
```

A system Graphviz installation is needed for the Graphviz viewer tests.
The source ZIP excludes the binary. [Test XML](../validation/final-tests.xml)

### Compiled-circuit reuse pilot

The benchmark-only cache reused one identical compiled circuit per run in
four paired full discoveries. It used a fixed transpiler seed and identical
shot seeds in each pair. Every non-timing history event, including raw shot
counts, was identical. Three warm comparisons reduced wall time by about
6–8%. The first comparison improved by 27%, but the uncached-first ordering
confounds that result with initialization. All four pairs were ordered
uncached first, so this is a pilot rather than a production speed claim.
The default executor is unchanged. A production cache would need bounds
on retained circuits and keys that include backend target, compilation
options and noise assumptions. [Cache pilot](../validation/discovery-cache-pilot-024.json)

## Release stopping rule and statistical model

The first 60 runs above are the **pre-guard discovery baseline**. In the
release rule, a rounded M=N is only a trigger to inspect the raw phase
evidence. For Q=2^p phase bins, full marking ideally yields phase 1/2
(the center bin). If M<N, the conjugate eigenphases have angular
separation from that bin with squared sine 1-M/N. The squared QPE
Dirichlet kernel at the center is at most
1/(Q²(1-M/N)) ≤ N/Q², capped at one. This upper bound holds over every
incomplete integer M without enumerating or assuming a basin size.

For observed central-bin hits k out of s shots, the release tests the
binomial upper tail using that worst-case probability. It also retains
the minimum central-bin fraction and requires every confirmation to pass.
The per-call level is 0.01 divided by the maximum number of tests
(max_rounds+1 times stop_confirmations), a conservative union bound even
when the marked set depends on previous measurements. This is conditional
on the ideal QPE model and independent shots within a call. A bound of one
cannot support a completion signal regardless of the shot count. The
test is disabled for physical hardware and noisy Aer because their
phase distributions are not covered by this bound. A full-count estimate
without evidence is recorded as inconclusive. The raw evidence, assumed
model, alpha and tail bound are exported.

Only exhaustive classical terminal coverage certifies completeness.
Every cycle has at least one starting state already on it, so even when
T is short, marking all terminal states cannot omit a disjoint cycle.
Conversely, insufficient T can leave transient terminal states outside
the marked cycles and prevent a coverage certificate even after every
cycle is recovered. A QPE pass remains a heuristic under an explicit
ideal model, not an exact certificate. Intermediate count errors still
alter suppression angles and can make search incomplete. Increasing T,
phase resolution and shots addresses different failure modes and incurs
different resource costs.

The four-shot 15:1 replay is now inconclusive in all eight trials, including
the four previously false signals. Those runs retain only one of two
attractors. No result was promoted to complete merely by increasing T
or the shot count. The same seeds and counts are retained for comparison.
[Guarded four-shot records](../validation/discovery-low-shots-guarded-024.json)

### Precision, shots, and horizon follow-up

The guarded 15:1 sweep holds T=1, which is sufficient for this map. At
precision 1, all 24 trials across 4, 16 and 128 shots are inconclusive.
At precision 2, all four 16/128-shot trials still alias 15 to 16 and remain
inconclusive. At precision 3, all four discover both attractors. The first
marked count was decoded as 14 instead of 15 and the search still observed
49 already-known-state shots in total. The second basin was nevertheless
found and the subsequent full-count evidence passed. This separates phase
resolution and imperfect suppression from transient-length effects.

The three additional fixed-horizon randomized structures produced 12/12
oracle matches with guarded heuristic completion. They include fixed points
and a three-cycle, with transient lengths 2–4. Each has one basin, so this
extension primarily checks longer evolution and full-count inference.
Multi-basin suppression is exercised in the original paired horizon runs
and the 15:1 precision sweep. The latter explicitly tests the failure
regime as well as a configuration that can separate the near-full count.

[Guarded stress](../validation/discovery-adversarial-guarded-024.json) ·
[Precision 2](../validation/discovery-stress-p2-024.json) ·
[Precision 3](../validation/discovery-stress-p3-024.json) ·
[Additional structures](../validation/discovery-additional-024.json) ·
[Guarded longer-horizon repeats](../validation/discovery-longer-guarded-024.json)

### Counterbalanced cache check

Eight paired full discoveries ran with a fixed, randomized and balanced
order of four cached-first and four uncached-first pairs. Inputs, shots,
transpiler seeds, simulator seeds and resource guards were identical within
each pair. All non-timing events and raw shot records agreed exactly, with
one cache hit per cached run. Seven pairs were faster with caching, and
the median paired wall-time reduction was 9.6%. The first cached-first pair
was 68.2% slower, consistent with sensitivity to startup and run order.
The default executor still does not cache. This test supports correctness
only on the tested local ideal backend and options.
[Counterbalanced cache records](../validation/discovery-cache-counterbalanced-024.json)

The active release guard plus its regression tests supersede the preliminary
pre-guard stopping behavior. The source package retains both measurements.
The 175-test run emitted 24 third-party Qt/Matplotlib deprecation warnings.
