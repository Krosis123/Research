# ATLANTIS 0.2.2 scientific verification

## Why 17 tables are absent

Cho et al. describe a 197-node model. Their Additional File 3 inventory lists
184 tables and explicitly excludes the 13 external inputs. The supplied ATLANTIS
201-node model and the Cho simulation archive both carry four additional phenotype names beyond the 197 nodes described in the Cho article. The ATLANTIS MATLAB
loader derives filenames from node names and warns if they are absent, then
leaves their source lists empty. Its synchronous update initializes a target from
its previous value and overwrites it only when sources exist. Thus retention
reproduces this code path, but it does not establish biological update equations.

| Exact identifier | Role | Provenance and resolution |
|---|---|---|
| EGF | Growth-factor stimulus | Cho external input, supplied condition value |
| ECM | Matrix stimulus | Cho external input, supplied condition value |
| alpha_q_lig | G-alpha-q ligand | Cho external input, supplied condition value |
| alpha_i_lig | G-alpha-i ligand | Cho external input, supplied condition value |
| alpha_s_lig | G-alpha-s ligand | Cho external input, supplied condition value |
| alpha_12_13_lig | G-alpha-12/13 ligand | Cho external input, supplied condition value |
| Stress | Stress stimulus | Cho external input, supplied condition value |
| IL1_TNF | Inflammatory stimulus | Cho external input, supplied condition value |
| ExtPump | External calcium pump | Cho external input, supplied condition value |
| Fas | Death-receptor stimulus | Cho external input, supplied condition value |
| WNT | Wnt pathway stimulus | Cho external input, supplied condition value |
| Tgf-b | TGF-beta stimulus | Cho external input, supplied condition value |
| DNA_damage | DNA damage stimulus | Cho external input, supplied condition value |
| Apoptosis | Phenotype label | Cho and ATLANTIS coordinate, no supplied equation |
| Cell_Adhesion | Phenotype label | Cho and ATLANTIS coordinate, no supplied equation |
| Cell_Migration | Phenotype label | Cho and ATLANTIS coordinate, no supplied equation |
| Proliferation | Phenotype label | Cho and ATLANTIS coordinate, no supplied equation |

The four extra columns have no outgoing dependency in any supplied update
table and are absent from the supplied fate classifier inputs. The reproduction
script checks both properties before setting these columns to a canonical
placeholder for cycle identity. Their placeholder values carry no phenotype
meaning. Fate calls come from the supplied case-specific classifiers. Cho's source archive identifies eight output
nodes: Rho, CyclinD, CyclinE, CyclinA, CyclinB, Casp-3, MMP and E-cad. The four
unruled names are distinct from that output list. Their intended historical
role is undocumented, although the supplied classifier computes corresponding
phenotypes from regulated nodes. After retrieving Additional Files 3 and 4
via Europe PMC, all 184 truth tables matched after normalizing whitespace and
case. The 201-column original Cho initial-state matrix matched Simulation 1
on all 2,010,000 bits after aligning columns by node name. The supplemental
starter script assumes 13 nonupdated inputs, whereas its truth-table inventory
leaves 17 names without tables. Its generic trajectory function retains
coordinates outside the supplied table count. That behavior and the missing
equations do not justify assigning dynamic biological meaning to the four
coordinates. See `validation/cho-source-comparison.json`.

The two cases reuse byte-identical network details and initial-state files.
This is consistent with the ATLANTIS methods and case ReadMe files describing
a shared model and separate experimental configurations. The input CSV differs
in WNT (Case 3 on) and Tgf-b (Case 4 on). Case 4 control pins Ras and PI3K on,
then applies individual node or link interventions. Case 3 applies cumulative
APC, Ras, PTEN and p53 changes. MATLAB's mutation source sets node tables to
constants and retains source-zero rows for a deleted link.

The GUI imports incomplete models as unspecified. They must be given rules,
declared external inputs, or fixed to 0 or 1 before simulation. External inputs
retain each trajectory's starting value, and fixed nodes use the specified value
throughout. The older explicit compatibility import records which identity
rules were assumed. Legacy JSON with absent provenance can be inspected by the
user and reclassified as needed.

## Sampled comparison

Run from the source root with the installed environment:

    python tools/reproduce_colorectal.py

The 22 conditions use a seeded sample of 1,024 rows drawn without replacement
from the three supplied state lists pooled together. Conditions share the
same sampled rows. External inputs and mutation pins are set before the first
update. Cycles are detected by state recurrence within 200 updates. The
batched detector checks its first eight trajectories per condition against
the application solver. The output records point/cycle counts by period,
distinct cycles, unresolved mass and marginal Wilson intervals. Classifier
labels overlap, so their marginal proportions need not sum to one. Intervals
describe sampling variation approximately and do not capture model differences.

| Case 3 condition | Normal proliferation measured | Published |
|---|---:|---:|
| Control | 79.3% | 79% |
| APC | 79.3% | 79% |
| APC + Ras | 25.2% | 39% |
| APC + Ras + PTEN | 25.9% | 41% |
| APC + Ras + PTEN + p53 | 25.9% | 1.3% |

Control-to-final metastasis increased from 20.3% to 93.4%, and abnormal
proliferation increased from 13.1% to 54.8%. The direction agrees with ATLANTIS.
The proliferation magnitude differences exceed the marginal sampling intervals.
The original study averaged three separate state-list analyses, while this run
pools a smaller sample, pins mutations at time zero, and uses a bounded horizon.
Those are protocol differences. Their individual effects have not been isolated.
The reported tumor-progression category still needs a matched definition.

Case 4 apoptosis was 28.8% in the control and 77.2% (AKT), 99.6% (EGFR),
100% (ERK), 80.0% (MDM2–p53), 99.9% (MEK), 84.5% (PI3K), and 92.4% (RAF).
These seven increases match the reported direction. The paper reports effects
relative to untreated control and compares GI50 from experiments. The present
run estimates model fates and does not reproduce experimental drug response.
Cases 1 and 2 retain their existing archived MATLAB regressions. The complete
published biological comparison across all four cases remains partial.

Sources: [ATLANTIS and its supplementary materials](https://www.nature.com/articles/s41598-018-22031-3)
and [Cho et al. and Additional Files 1–5](https://doi.org/10.1186/s12918-016-0341-9).
Local audit files include parse_LogicTables.m, synchronousAttractorSearch_RulesBased.m,
addMutations_RulesBased.m, both case ReadMe files and their CSV conditions/classifiers.

## Acceptance matrix

| Requirement | Status | Evidence or outstanding issue |
|---|---|---|
| Missing node handling | Independently verified | Strict imports, JSON roundtrip, classical execution and quantum compilation checks |
| Shared baseline and experimental inputs | Verified against supplied material | File identity, distinct condition CSVs and mutations |
| Full colorectal and HCT-116 reproduction | Partially verified | Full 10,000-row runs across the supplied protocols, exact archived replay, partial published aggregation and experimental comparison |
| Yeast and MCF-7 reference outputs | Partially verified | Archived yeast fixtures and all eight MCF-7 deterministic treatments verified. Complete probabilistic treatment comparison pending |
| Boolean compiler, ordering and inverse | Independently verified | Hand-evaluated truth table, permuted registers and measured Aer forward/inverse circuits |
| Rossini counting and suppression | Partially verified | Supplement S1–S4, official code, phase-matrix and cyclic Aer tests, matched and unequal QPE measurements |
| Quantum control flow | Independently verified in tested path | Genuine Aer QPE test forbids exhaustive classical enumeration. Adaptive stopping is experimental |
| Three-analysis workflow | Verified with automated Qt | Real application widgets, import, three analyses, plots, export, reopen and durable quantum record |
| Clean wheel and source install | Verified | Fresh environment, native Qt launch, installed three-analysis workflow and dependency check |
| Classical restart | Verified | Forced-exit regression reruns persisted inputs from the beginning. Computational checkpointing remains unsupported |
| Resource rejection | Verified | Twenty 25-qubit statevector attempts exceeded the configured guarded memory budget |
| Timing and scaling | Partially verified | Matched small-network runs, three seeds, process RSS snapshots rather than isolated peak memory |
| IBM Runtime | Verified locally | Fake backend transpilation and client-side sampler, mocked credentials/discovery/cancellation and status/result interfaces |
| Physical hardware | Blocked | Live credentials and explicit paid-job authorization required |

## Archived MATLAB replay and earlier case studies

The supplied MATLAB archive for the final colorectal mutation contains 10,000
rows. EGF, ECM and WNT are already fixed as specified, while the mutation-node
initial values vary. With those values preserved at time zero and the mutation
tables active from the first update, the Python replay resolves 9,977 rows in
200 updates. All six combined fate proportions match the saved MATLAB CSV to
rounding precision. Total variation is 0.00000372 on resolved-conditional
proportions. This verifies the archived fate distribution for this condition.
The 23 unresolved rows remain visible in the raw counts. The earlier exploratory
sweep uses all sampled rows as the denominator. It reports marginal labels,
which can differ substantially from the exact combined categories used by
the archived MATLAB CSV. See `validation/colorectal-archived-comparison.json`
and `tools/compare_archived_colorectal.py`.

The 11-node yeast enumeration gives seven attractors and a stationary G1 basin
of 86.1328%. Existing fixtures verify the states, basin sizes, classifier labels,
and probabilistic transition and steady-state vectors against archived MATLAB
results. The archived probability run stops at 200 iterations before its
convergence criterion. The reference regressions preserve that status.

The 16-node MCF-7 treatment sweep enumerates 65,536 states per condition.
Control is 100% proliferation. Apoptosis is 0% for Etoposide and WIP1 knockdown
alone, 24.60% for Nutlin, 32.55% for Etoposide + Nutlin, 4.50% for Etoposide +
WIP1 knockdown, 56.80% for Nutlin + WIP1 knockdown, and 71.88% for the triple
combination. These match the reported deterministic rates at the paper's
precision. The eight conditions and their point/cycle states are recorded in
`validation/yeast-mcf7-reproduction.json`. The complete MCF-7 probabilistic
treatment comparison and independent experimental validation remain open.
[ATLANTIS paper and published treatment rates](https://pmc.ncbi.nlm.nih.gov/articles/PMC5824948/)

## Matched benchmark and installation evidence

The matched matrix completed all 54 runs and recovered both attractors in each
run. At four nodes, median wall times were 1.40 ms classical, 1.84 ms reference,
21.7 ms ideal Aer, 31.9 ms MPS, 126.5 ms noisy Aer, and 2.02 s adaptive Aer QPE.
These are three-seed measurements for one projection family, with 128 shots
per quantum circuit. Counting and transpilation timing can overlap with
end-to-end execution measurements. Reported RSS is a process snapshot.
The separate 3:1 basin experiment measured 18 actual QPE circuits. Absolute
marked-state count error was 2, 1 and 0 at precision 2, 3 and 4, respectively,
for both marked sets and all three seeds. Exact counts were evaluated separately
from discovery. See `validation/matched-scaling.json`,
`validation/matched-scaling.png`, and `validation/unequal-qpe.json`.

All 20 historical rejections were 25-qubit statevectors. Amplitude storage is
512 MiB, and the configured 3x allowance yields 1,536 MiB against a 1,024 MiB
budget. These attempts were rejected before execution. The guard is a
conservative estimate rather than a measurement of peak RSS.
See `validation/memory-rejection-audit.json`.

A fresh Python 3.12 environment installed the wheel with quantum dependencies
and passed pip check. The native Qt main window launched and closed. The
automated Qt three-analysis workflow passed from the installed wheel and from
a separate installation built from an extracted source ZIP. The tests invoke
the real Qt widgets with automated file selection and run offscreen.
The final automated suite reports 158 passes, zero skips, and 16 third-party
Qt/Matplotlib warnings. The installed GUI workflow and the forced-exit recovery
test cover different behavior. Recovery reruns saved inputs from the beginning.

## Full supplied 201-node state lists

All five colorectal conditions were evaluated separately on each supplied
10,000-row replicate with the archived initialization convention. The table
uses exact combined-category membership in Normal Proliferation and divides
by resolved trajectories. Between-list variation is shown directly because
these are three fixed input lists with different provenance.

| Condition | Simulation 1 | Simulation 2 | Simulation 3 | Three-list mean | Paper |
|---|---:|---:|---:|---:|---:|
| Control | 73.07% | 79.00% | 78.65% | 76.91% | 79% |
| APC | 73.03% | 78.98% | 78.61% | 76.87% | 79% |
| APC + Ras | 32.42% | 39.20% | 39.10% | 36.90% | 39% |
| APC + Ras + PTEN | 32.34% | 40.78% | 40.73% | 37.95% | 41% |
| APC + Ras + PTEN + p53 | 6.63% | 1.35% | 1.17% | 3.05% | 1.3% |

Simulation 2 is within 0.23 percentage points of each published value, and
Simulation 3 is close. The three-list average differs from the published
values, particularly for the final condition. The paper describes averaging
across three lists but does not specify a separate aggregation for the reported
mutation sequence. The individual data support a computational reproduction
for the selected list and an exact archived replay for Simulation 1. The
published aggregation remains unresolved. See
`validation/colorectal-three-replicates.json`.

The HCT-116 follow-up used all 10,000 rows of Simulation 1 and all 17 supplied
files, including the untreated control. Marginal apoptosis was 41.79% in
control and 84.52% (AKT), 99.80% (EGFR), 100% (ERK), 86.59% (MDM2–p53),
99.30% (MEK), 88.85% (PI3K), and 92.00% (RAF), with unresolved states
included in the denominator. This verifies the direction reported for the
seven highlighted inhibitors. MDM4 and XIAP each left 219 trajectories
unresolved at the 200-step cap. These bounded model results do not reproduce
the experimental GI50 comparison. See `validation/hct116-full.json`.

The full deterministic runs can be repeated with:

```powershell
python tools/reproduce_case3_replicates.py
python tools/reproduce_case3_replicates.py --case 4 --replicates 1
python tools/compare_archived_colorectal.py
python tools/reproduce_yeast_mcf7.py
```

[ATLANTIS supplement and Methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC5824948/)
