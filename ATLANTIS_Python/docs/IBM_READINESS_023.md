# IBM Quantum hardware readiness

The application uses Qiskit IBM Runtime 0.51 with the client-side
`executor_sampler.Sampler`. The offline workflow exercises synthetic
credentials, backend discovery, fake-backend ISA compilation, local Sampler
execution, provider-style job IDs and retrieval, mocked status and cancel
operations, sanitized error reporting, and the actual Qt account controls.
The password input clears on connect and credentials stay in process memory.
Submitting requires the application's explicit confirmation. An uncertain
submission is surfaced for inspection without automatic resubmission.

The proposed minimal hardware experiment is one unsuppressed Rossini4
forward circuit at T=3 and 128 shots. It measures the terminal distribution
against ideal probabilities 11/16, 2/16 and 1/16 for the other three outcomes.
On the FakeBrisbane calibration snapshot it compiled to 16 active qubits,
depth 471, 1,264 instructions and 225 two-qubit gates. The output circuit
retains the backend's 127-wire layout. Estimated scheduled duration is 92.94
microseconds, plus the default 250 microseconds repetition delay per shot.
The 128-shot subtotal is about 0.044 seconds before provider overhead.
This probe tests forward evolution only. It does not establish hardware
suppression, counting, or adaptive discovery. [Offline estimate](../validation/ibm-offline-estimate-023.json)

IBM lists free Open Plan allowance subject to quota and Pay-As-You-Go starting
at USD 96 per usage minute. At that rate the 0.044-second subtotal is about
USD 0.07 before minimum purchase and provider overhead. This is a duration-based
subtotal, not a billing prediction. A proposed 60-second usage cap corresponds
to USD 96 at the published starting rate. Live backend layout, plan terms,
remaining quota, preparation overhead and measured billable usage must be
checked before approving execution. No real credentials were used and no
provider job was submitted. [IBM pricing](https://www.ibm.com/quantum/products) ·
[IBM workload usage](https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time) ·
[Client-side Sampler](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/executor-sampler-sampler)
