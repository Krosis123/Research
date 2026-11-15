# Migration checklist

Statuses describe observed verification, not promises of full parity. The automated report is `validation/pytest.xml`; comparison details and remaining limits are in `COMPARISON.md`.

| Feature | Implemented | Verification |
| --- | --- | --- |
| Outer source archive and nested RAR inventory | Yes | 1334 files; 115 MATLAB-file mappings |
| Main six-button desktop window with original artwork | Yes | Qt render and import workflow tests |
| All 14 GUIDE definitions | Yes | All instantiated and rendered on Windows offscreen |
| Weighted network import/export | Yes | All supplied weighted model inputs and roundtrip tests |
| Node-list/truth-table import/export | Yes | Roundtrips and both 201-node examples; missing files require explicit opt-in |
| Network creation/editing | Yes | Functional Qt table editor; not every edit path manually exercised |
| Multiple mutation files and variant generation | Yes | Node/edge rule and weight unit tests; multi-file GUI not exhaustively exercised |
| Exhaustive, sampled, and custom states | Yes | Encoding, uniqueness, repeatability, fair-bit behavior, supplied MAT datasets |
| Fixed initial-node states | Yes | Tests confirm initialization-only behavior and duplicate preservation |
| Weighted synchronous attractors and basins | Yes | Exact MATLAB yeast comparison; archived p53 Control/Nutlin checks |
| Rule-based attractors and cycles | Yes | MATLAB two-node cycle comparison; full 201-node parity remains unverified |
| Search timeout reporting | Yes | Independent timeout test |
| Cell-fate logic, wildcards, multi-value rules | Yes | MATLAB yeast fate comparison; independent wildcard expansion tests |
| Average and stratified attractor activities | Yes | Cycle/threshold tests and MATLAB fate outcomes |
| Probabilistic node/state transition probabilities | Yes | Hand-calculated tests and MATLAB 242-state matrix comparison |
| Source master-equation iteration and stopping rule | Yes | MATLAB comparison and independent substochastic matrix equilibrium test |
| One-step state-space pruning | Yes | MATLAB state list and separate unit test |
| Probability-ranked trajectory interval | Yes | Independent rank-interval test; all case-study bounds not compared |
| Naive projection with MATLAB column-major reshape | Yes | Saved MATLAB permutation comparison |
| Cyclic-state grouping | Yes | Source translation; rare/large cycles not MATLAB-validated |
| Sammon PCA/Newton/halving and stress | Yes | Finite MATLAB one-step comparison; Python 242-state rendering; full convergence parity unverified |
| Sammon input-distance/random initialization options | Yes | API implemented; not all option combinations MATLAB-compared |
| Natural-neighbor interpolation | Yes | MATLAB and linear-precision tests |
| Basin, probability, and potential-energy surfaces | Yes | All regenerated and rendered; source energy singularities are explicit errors |
| Cell-fate treemap geometry | Yes | MATLAB rectangle comparison; rendered annotations and legends |
| MATLAB color maps | Yes | 33 MATLAB checks across 11 maps and three sizes |
| Graphviz regulatory diagrams | Yes | Graphviz 2.38 layouts, generated plots, native SVG viewer test |
| Advanced custom DOT rendering | Yes, via native SVG viewer | Graphviz generates all geometry; advanced case-by-case Qt SVG fidelity is not certified |
| BioGraph-specific layout/editor | Partial | NetworkX replacement preserves scientific graph; proprietary visual/editor parity absent |
| Plot annotations and state inspection | Yes | Figure-control tests; metadata click handler implemented |
| Rotation, zoom, pan, inversion, colors, alpha, visibility | Yes | Qt/Matplotlib controls and property tests |
| Figure exports | Yes | PNG/JPEG/TIFF/PDF/SVG/EPS automated outputs and native SVG-viewer export tests; not every DPI/path manually checked |
| MATLAB FIG export / every export_fig private option | No direct equivalent | Replaced by Python data and standard image/vector export; limitations documented |
| State/result CSV and MAT exports, JSON networks | Yes | Roundtrips and result reopening test |
| Original saved Sammon coordinates | Yes | Compatible MAT reader; placement reuse requires matching state count/order |
| Original naive mapping missing permutation | Cannot reconstruct missing data | Explicit diagnostic; Python NPZ saves future permutations |
| Cancellation and progress | Yes | Core cancellation and GUI worker tests; cancellation during every subroutine not exhaustively tested |
| Automatic timestamped MATLAB output folders | Changed | Explicit result export with destination selection; documented |
| Supplementary truth-table to BoolNet conversion | Yes | Independent conversion test |
| No MATLAB dependency in ordinary execution | Yes | Application uses Python/Qt/Graphviz; MATLAB only in developer reference tools |
| Clean Windows installation test | Pending | Tested on the current Windows/Python 3.12 host; pinned installer and launcher supplied |
| Exhaustive biological/visual equivalence across all case studies | Pending | Not represented as complete |
