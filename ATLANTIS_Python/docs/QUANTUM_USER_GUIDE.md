# Integrated ATLANTIS setup and use

## Windows

From the delivered project folder, with Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-integrated.lock.txt
.\.venv\Scripts\python.exe run_atlantis.py
.\.venv\Scripts\python.exe -m pytest -q
```

During this integration, the verified interpreter is
`C:\Bio_research\.venv-atlantis\Scripts\python.exe`.
The source ZIP does not include a virtual environment or Graphviz binaries.
Install Graphviz separately for its SVG layouts, or use the existing NetworkX
network viewer. The local workspace also has the original bundled Graphviz for
compatibility tests. Tests requiring that external executable fail if it is absent.

## Demonstration

1. Start the desktop. Right-click, **Open Python Network**, and select
   `examples/quantum/rossini4.json`.
2. Run the existing deterministic analysis with all 16 initial states. Expected
   fixed points: 0000,0011,1011,1101,1111; basin sizes 11,2,1,1,1.
3. Click **Quantum / Experiments**. Use T=3, reduced, exact, classical_audit.
   Preflight, then Run. This is an ideal mathematical reference using classical M.
4. Change execution to aer and repeat. This executes full circuits. Use Compare
   classical, Plot measurements and Export JSON. Compare uses the saved network
   snapshot, even if the editor was subsequently changed.
5. For actual quantum counting select aer, qpe_aer and qpe stopping. Low precision
   can return inconclusive results or heuristic completion; neither certifies all
   attractors. Higher precision costs exponentially more controlled Grover calls.
6. Open `large150.json`. Quantum preflight rejects it (T=3 requires 600 evolution
   qubits). Existing classical sampled analysis remains available.
7. Open Job history to restore results. After a crash explicitly mark interrupted
   jobs; no job is automatically resubmitted. Cancel terminates local quantum worker
   processes, including native simulator execution.

The five-gene example is `giacomantonio5.json`; use T=4. Its 25 evolution qubits
exceed the default 22-qubit budget. Explicitly choose aer_mps and raise the qubit
budget to 25 for the tested small circuit. This is simulation, not hardware.

## Model format and editing

All original weighted/truth-table CSV/TXT/MAT and Python JSON formats remain.
An additional JSON expression format is:

```json
{"name":"toggle","rules":{"p53-alpha":"NOT `p53-alpha`","output":"`p53-alpha` XOR output"}}
```

Supported operators: AND/OR/NOT/XOR, &, |, ~, !, ^, parentheses, 0 and 1.
Backticks quote arbitrary node identifiers. Rules are parsed with a whitelist;
Python function calls, indexing, attributes, arithmetic and executable code are
rejected. Graph topology alone is insufficient: provide weights or update rules.
Expression rules can be edited through the existing network editor. Original
node/link perturbation semantics remain; weighted +/-1000 basal mutation is a
historical perturbation, not a universal hard clamp for arbitrary large weights.

## IBM account and recovery

In Quantum / Experiments choose IBM account, enter your API key and instance CRN,
then discover/select a real QPU. Keys are cleared from the input and retained only
inside the in-memory service; never exported or written to disk. Disconnect clears
the account reference. Select ibm execution and qpe_aer (actual QPE circuit counting).
The first circuit is transpiled for review; a separate confirmation authorizes at
most 24 search/count submissions, each capped at 60 seconds of QPU execution.
Charges follow your provider plan. No hardware job was submitted during development.

Job IDs are in the `provider_jobs` table of `%USERPROFILE%\.atlantis\jobs.sqlite3`.
After restart reconnect to the same account, paste an ID in the IBM dialog, and
retrieve its status/results or cancel. An uncertain submission must be checked in
the provider dashboard before any retry. The application never retries paid jobs.
Provider recovery currently restores individual measurements, not an interrupted
adaptive search automatically.

## Python API

`atlantis.io.load_network(path)` loads the canonical model.
`atlantis.quantum.engine.preflight(network, Settings(...))` returns feasibility.
`atlantis.experiments.execute(network, settings, progress, cancel)` runs a durable,
isolated local job. `atlantis.quantum.engine.run` is the synchronous library API;
its deadline is cooperative between circuit calls, so use execute for hard timeout.
`atlantis.quantum.hardware.run_hardware` requires an authenticated account and
explicit confirmation. There is no HTTP API or externally exposed server.

## Reproduction and troubleshooting

`python tools/benchmark_integrated.py --output validation/new-benchmark` creates
raw measurements, summaries and charts. Output directories must be new.
Use an isolated environment: mixed qiskit-terra and Qiskit >=1 installations fail.
Resource rejection means adjust a documented budget only when suitable resources
exist; it never silently switches to classical execution. See correctness report
for exact/sampled/reference/circuit/heuristic/certified distinctions.
