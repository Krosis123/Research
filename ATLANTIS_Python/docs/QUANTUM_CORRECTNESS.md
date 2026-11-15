# Quantum correctness and interpretation

This extends the supplied Python port. Source archives and historical Ross
experiments are preserved outside this distribution. The vendored `atlantis/quantum/ross`
code derives from the supplied Ross_Adaptive_v2_Benchmark; modifications add bounded
verification, raw measurements, execution hooks, cancellation and honest resources.

## Mathematical contract

Supported dynamics are deterministic synchronous Boolean maps F. Weighted ATLANTIS
updates use xW+b: positive -> 1, negative -> 0, exactly zero -> previous node value.
The adapter includes that previous bit in synthesis. All engines use gene order
left-to-right (MSB first); gene i in time register t maps to qubit tn+n-1-i.

Reversible evolution maps (x,0,...,0) to (x,F(x),...,F^T(x)). It retains n(T+1)
logical qubits; QPE adds p. No reduced n-qubit representation is claimed to have
the same circuit resources. ANF monomials compile to X/CX/CCX/MCX. Boolean expression
ANFs are synthesized symbolically with budgets; weighted and imported truth-table
rules use bounded local truth tables (12 inputs at quantum compilation).

For excluded initial states M out of N=2^n, beta=asin(sqrt(M/N)),
J=max(1,ceil(beta/(pi-2 beta))), phi=-2 asin(sin(pi/(4J+2))/cos(beta)).
The paper writes J=ceil(pi/(2pi-4beta)-1/2), which simplifies to the same expression.
The official `optimalphi2` uses the negative phi convention retained here. The
paper uses the positive convention; simultaneous conjugation of phase operations
changes amplitudes by conjugation, preserving probabilities for real initial state
and reversible Boolean permutations. Each iteration applies phase -phi to known
terminal states, reverses evolution, then H P_zero(phi) H to the initial register.
Exact cancellation requires accurate M and sufficiently long evolution for basin
marking. All cycle members must be marked. Tests compare full distributions.

Counting uses Grover eigenphases +/-theta, sin(theta)^2=M/N. Measuring y on p
QPE bits gives round(N sin(pi*y/2^p)^2). Conjugate peaks are pooled. Finite precision
and finite shots can over/underestimate M and leave suppressed probability. Repeated
full estimates are heuristic, never a completeness proof. No confidence level for
this heuristic is asserted. Exhaustive independent F^T coverage is a classical
certificate with exponential work. Bounded termination remains inconclusive.

T is always caller supplied and recorded. Candidate verification traces only
measured trajectories and rejects transient outcomes. Its step budget can reject
long valid cycles; this is an inconclusive outcome, not proof of their absence.
The exact-M and ideal-QPE reference modes enumerate F^T and explicitly disclose
that classical information. The genuine QPE control path has an automated test
which makes classical enumeration raise an exception.

## Verified scope

Fresh tests include Rossini4 basins 11,2,1,1,1, T=3; official Giacomantonio5 basins
28,4, T=4; both five-gene suppression orders; random weighted reversible updates;
full ideal suppression distribution; actual Aer QPE; full Qt execution/export;
150-node classical use with quantum rejection; malicious rules; durable cancellation.
Original MATLAB fixtures are reused as reference data, not newly executed MATLAB.

IBM uses QiskitRuntimeService with ibm_quantum_platform and the client-side executor_sampler.Sampler.
The installed 0.51.0 signature was inspected. Credentials remain ephemeral and
save_account is never called. Each circuit is backend-transpiled and checked.
User confirmation precedes a bounded series of potentially paid submissions.
Provider IDs and uncertain submission outcomes are durable; no automatic retry.
Mock account/submission/retrieval tests pass; physical QPU execution is **unverified**.

## Remaining limitations

No demonstrated quantum speedup; no live QPU result; no fault-tolerant cost model.
No asynchronous or continuous/stochastic-to-quantum conversion. Symbolic ANF can
still expand exponentially; budgets reject this, and shared-ancilla synthesis is
not implemented. MPS efficiency is not guaranteed. Backend-specific dynamic quota
discovery and comprehensive multi-tenant hosting are not implemented; this is a
single-user local desktop. The Rossini supplemental PDF was recovered through Europe PMC.
Sections S1–S4 provide the four-agent truth tables, conditional phase matrix,
suppression parameters, and a worked cyclic example. The test suite verifies
the phase matrix at every 4-qubit basis index and reproduces the final worked
cyclic suppression measurement on Aer MPS. The X-conjugated multi-controlled
phase realizes the same diagonal as the supplement's elementary-gate circuit.
The optional adaptive termination policies remain application extensions.

Sources: [Rossini paper](https://doi.org/10.1016/j.patter.2025.101295),
[official implementation](https://github.com/sysbio-bioinf/QuantumAttractorSearch)
at commit 638141c004bee7c8f9f640a766a78d4f558bc909,
[IBM Sampler documentation](https://quantum.cloud.ibm.com/docs/en/guides/get-started-with-sampler).
