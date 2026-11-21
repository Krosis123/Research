# Research figures — integrated ATLANTIS 0.2.4

Created from the current local implementation on 18 November 2026.

- `graphical_abstract`: integrated architecture, classical analysis and adaptive quantum discovery.
- `algorithm_flowchart`: detailed adaptive discovery algorithm, including counting, suppression, candidate verification, retries and termination.
- PDF: vector manuscript insertion. SVG: editable vector artwork with live text. PNG: 300 dpi raster export. Preview PNGs are lower resolution.
- `generate_figures.py`: editable, reproducible Matplotlib source. Run using `C:\Bio_research\.venv-atlantis\Scripts\python.exe`.

## Suggested captions

**Graphical abstract.** Integrated ATLANTIS architecture for regulatory-network analysis and adaptive quantum attractor discovery. A shared Boolean network model supports classical deterministic analysis and, for weighted networks, probabilistic analysis. The quantum branch compiles synchronous update rules into reversible evolution circuits. Adaptive discovery alternates coverage counting, suppression of previously discovered cycles, terminal-state measurement and classical verification. Classical analysis supplies basin and landscape information; quantum discovery supplies verified cycles, measurements and execution records. Execution interfaces include ideal mathematical references, Aer simulation and IBM hardware, with no live QPU validation or demonstrated quantum speedup in the current project.

**Algorithm flowchart.** Source-aligned control flow for adaptive Rossini attractor discovery in ATLANTIS. The user selects evolution horizon T, execution and counting modes, and resource budgets. Verified cycles define the marked terminal set; counting estimates the number of initial states reaching this set after T steps. Phase-adjusted suppression biases subsequent measurements away from known cycles. Bounded classical tracing validates measured candidates, and one accepted cycle is added per successful round. Exhaustive coverage checks provide classical certification; supported repeated QPE estimates yield heuristic completion. Budget exhaustion, invalid counts and unsuccessful candidate searches retain an inconclusive outcome.

## Source grounding and interpretation

Primary sources: `atlantis/quantum/engine.py`, `atlantis/quantum/ross/adaptive.py`, `atlantis/quantum/ross/circuits.py`, `atlantis/quantum/adapter.py`, and the architecture / quantum correctness documentation.

The flowchart follows executable `adaptive.py` where prose documentation is less detailed. In particular, the QPE stopping path tests ideal-shot-model coverage evidence and repeats confirmations. Its reported result is still heuristic; noisy / hardware evidence does not satisfy that ideal-model gate. Exact counting and ideal-QPE reference modes use classical enumeration. The round-limit exact-count certificate applies under QPE policy; a bounded policy does not certify completeness. Combined excluded-state coverage is not an individual-basin-size estimate. The architecture network sketch is illustrative, not a case-study result.

The graphical abstract presents the integrated project; the detailed algorithm focuses on its adaptive quantum discovery contribution. Figures were visually checked after rendering. No application code was modified.
