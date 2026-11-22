# Autonomous research log

## Entry 1. Feasibility and existing evidence

The original ATLANTIS deterministic engine computes synchronous attractors. Its probabilistic engine uses a separate weighted master equation. The experiment here uses deterministic dynamics and specifies a distribution over initial states. The existing QPE implementation stores time slices and may require an exhaustive classical audit. The fixed-anchor IBM paired-flip trial reached 256 possible ideal starts out of 65,536. Exact-mass and matched-sampler checks are necessary before proposing a hardware advantage.

The existing workspace had uncommitted modifications before this study. Research experiments use an isolated branch and separate outputs. All runs in this study are local. Run Python from the repository virtual environment with ATLANTIS_Python on PYTHONPATH. Run regression tests from ATLANTIS_Python.

## Entry 2. Held-out structural sampling

Hypothesis: feedback-linked sets of variables may benefit from correlated activity levels at initialization. The SCC proposal mixes equal parts uniform sampling and a guided draw. Within each nontrivial strongly connected component the guided draw samples a Beta(1/2,1/2) activation probability and conditionally independent bits. The mixture lower-bounds the probability of any permissible initial state by half its reference mass. Inputs were set to zero as an explicit test context. This context is not a measured physiological condition.

Run tools/transfer_basin_trial.py with a bnet input and a new JSON output path. The frozen design uses eight paired 32-start discovery replicates per method, a separate 1,024-start uniform audit, and a 32-transition ceiling. Every reported orbit is replayed under the source rules. Distinct orbit identifiers include every model variable. Each audit upper bound adds every unresolved trajectory to the candidate count and applies a simultaneous one-sided 95% Clopper-Pearson bound over the independently discovered candidates. This can rule in small basin mass conservatively; failing a threshold is inconclusive. Unseen attractors have no estimates.

On ErbB, the search discovered 137 distinct cycles across all replicates. Uniform versus SCC sampling found 16.375 versus 17.625 distinct cycles on average per 32 starts. The audit had 500 unresolved starts; no candidate was certified rare. Extending the audit horizon is a more relevant improvement than increasing shot count here.

On BioDiVinE 247, the first Boolean-cube run treated threshold bits as independent. This is a software stress test only. The original model is multi-valued. A follow-up run samples uniformly from ordered levels consistent with zero-valued external bits. Its guided half instead gives each extreme level three times the weight of an interior level. All permitted levels retain nonzero probability. This follow-up discovered one cycle; three of 1,024 audit starts were unresolved. The four cycles and rare-candidate result from the unconstrained Boolean cube must not be interpreted as a biological discovery. This model has 300 Boolean columns including external inputs. It does not establish a 300-distinct-gene rare attractor.

Models 252 and 263 exceeded the existing expression parser guard. They produced no benchmark outcomes. All BioDiVinE sources were retrieved from commit 314b2fed94689c38d3aaaf8101ed622b3501c7f7 of sybila/biodivine-boolean-models, using the named models' model.bnet files. The held-out panels are independent of sampler tuning on MCF-7; model 004 had already been used in earlier ATLANTIS work.

## Entry 3. Exact structural baseline

The earlier iMC hardware trajectory leaves an important control question: can any alternative basin exist in the same fixed-context model? Iteratively evaluate each truth table on all assignments compatible with the genes already proven constant. Add a wave of forced values only after finishing the current pass. Induction on synchronous steps proves that each variable in wave k has its forced value for every time t >= k, regardless of the initial state. Replay the final state against every original rule.

tools/imc_basin_certificate.py certifies the entire 300-locus model after three waves and the 500-locus model after four. Each has exactly one fixed point, a full-mass basin and zero rare basins in this context. This is a classical exact result conditioned on the deposited Boolean model and fixed external environment. It is not an assertion about changing external signals or flux feedback.

## Reproduction and limitations

The regression suite passed from its documented package working directory. An initial invocation at the repository root failed three directory-sensitive tests. Both logs are retained locally. Timings from simultaneous trials and low replicate counts should not be used to infer a wall-clock advantage. Next hypotheses include exact structural restrictions for networks with nontrivial feedback and comparisons against symbolic search under the same fixed inputs.

## Entry 4. Longer audit horizon and frozen test

The first ErbB audit implicated the 32-step horizon. With the same discovery starts, audit starts, and settings, increasing the horizon to 160 eliminated all 500 audit non-resolutions. The new discovery set contains 200 cycles, 99 of which individually meet the simultaneous upper mass bound of 1%. This is not an exhaustive list of rare cycles.

Freeze these 99 targets and use 128 fresh 32-start trials per method. Endpoints are hits on any frozen target and distinct frozen targets detected. Minimize reuse of target labels by setting the policy parameters before the confirmation. Each method used 4,096 evaluations; per-start hit counts were 112 uniform, 230 SCC, 105 scrambled SCC, and 234 globally biased. Exact binomial per-draw intervals and all ordered replicate summaries appear in results/erbb-frozen-controls.json. Estimated independent draws for 95% probability of one hit: 109, 52, 116, 51. These are plug-in estimates, not confidence guarantees. Full-budget local times were 13.3–14.1 seconds per method. Global bias is an equally strong control; this experiment cannot attribute the gain to feedback structure or quantum effects. The audit certifies the labels under the chosen reference distribution; it does not prove that the frozen target set is complete. Fixed batch sizes do not measure an early-stopping wall-clock speedup.

BioDiVinE 001 was tested as an additional separate macrophage signaling model. At the fixed zero input context and 160-step horizon the discovery set contained just one cycle and all 1,024 audit starts resolved. A model with this observed behavior gives little power to discriminate rare-basin proposals. Initial context is part of the benchmark and should be varied in a future separately specified panel.
