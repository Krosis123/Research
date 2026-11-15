# IBM Quantum experiment preparation, 0.2.4

The local application uses Qiskit IBM Runtime 0.51.0 with the client-side
Sampler interface. Authentication, sanitized errors, backend discovery,
ISA compilation and result parsing were exercised with local or mocked
accounts. The 0.2.4 tests drive the durable hardware runner through provider
error, provider cancellation, user cancellation request, and lost submission
acknowledgement. An acknowledgement loss leaves an explicit unknown status
with no auto-resubmission. Live credentials and QPU execution were not used.
[IBM client-side Sampler](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/executor-sampler-sampler)

| Plan | Circuit and shots | Offline resource snapshot | Usage estimate and goal |
|---|---|---|---|
| A | One unsuppressed Rossini4 terminal circuit, T=3, 128 shots | 16 active qubits, 127 layout wires, depth 471, 225 two-qubit gates | About 0.044 s shot-duration subtotal. Verify provider submission, counts and register interpretation |
| B | Same circuit, eight blocks of 512 shots per arm, 4,096 QPU shots | Same calibration-snapshot circuit, recompile for authorized real backend | About 1.405 s shot-duration subtotal. Compare block and pooled distributions across ideal Aer, noisy Aer and QPU |

Both plans sample the full 16-bin terminal distribution. Keep shot blocks
separate, retain invalid terminal strings, and compare total variation from
the exact ideal distribution. Report Wilson intervals per bin and block
variability separately. Under independent shots the worst-case nominal 95%
proportion half-width is about 1.53 percentage points for 4,096 shots, versus
8.66 points for 128. Hardware drift and gate/readout errors can exceed
shot uncertainty. Record backend calibration time, mapped qubits, actual
usage, job IDs and provider errors. A 0.2% synthetic gate-depolarizing model
is an offline comparison arm and carries no claim to a live noise calibration.
Both simulator arms were executed and raw counts retained. These plans
validate forward-evolution sampling. A full QPU suppression and counting
experiment would require a separate budget and approval.

Usage subtotals use the FakeBrisbane schedule and 250 microseconds repetition
delay. They exclude provider overhead, queueing and calibration drift. At
IBM's published USD 96 per minute starting Pay-As-You-Go rate, shot subtotals
correspond to about USD 0.07 and USD 2.25 before minimum purchase and overhead.
A proposed 60-second cap per job corresponds to USD 96 per job at the
starting rate. Use one submitted job with blocks as separate PUBs for Plan B
if the authorized backend supports it. Otherwise verify aggregate caps before
approval. Open Plan can be free within quota. These are estimates and plan
limits, with actual usage dependent on the approved account and backend.
[IBM pricing](https://www.ibm.com/quantum/products) · [Workload usage](https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time) · [Execution-time limits](https://quantum.cloud.ibm.com/docs/en/guides/max-execution-time)

[Offline compilation](../validation/ibm-offline-estimate-023.json) · [Simulator counts](../validation/ibm-simulation-arms-024.json)

## Executed local comparison arms

The eight 512-shot ideal blocks had mean total variation 0.0352 from the
exact terminal distribution. The synthetic-noise blocks averaged 0.0801.
The 128-shot arms were also executed. A pilot with adjacent simulator seeds
produced nearly identical noisy histograms, so the reported experiment uses
widely dispersed, reproducible seeds and retains the pilot separately.
Each reported arm produced eight distinct 512-shot histograms. Distinct
histograms alone do not establish independence. Keep hardware block-level
variability separate from the ideal independent-shot interval.
[Pilot raw data](../validation/ibm-simulation-adjacent-seeds-pilot-024.json)
