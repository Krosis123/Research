# Comparison and verification report

This report describes the implemented migration and its actual limits. It does not certify complete MATLAB equivalence or a pixel-identical GUI.

## Verified numerical results

Reference computations were executed using the supplied MATLAB source on MATLAB 9.0.0.341360 (R2016a). Ordinary Python execution does not use MATLAB.

| Check | Observed result |
| --- | --- |
| Yeast full enumeration | Identical 2048 x 11 states and interaction matrix |
| Yeast attractors | Same seven point attractors; all basin ratios identical |
| Dominant yeast basin | 0.861328125 in both implementations |
| Yeast cell-fate association | Same associations for all seven attractors |
| Rules-based two-node cyclic network | Same two cycles and 0.5 basin ratios |
| One-step state-space pruning | Identical 242-state yeast subset |
| Tanh transition matrix | Maximum absolute MATLAB/Python difference 3.3306690738754696e-16 |
| Master equation after 200 steps | Maximum absolute difference 4.596323321948148e-14 |
| Convergence in that 200-step run | Neither implementation reached the configured criterion |
| Natural-neighbor interpolation | Same outside-hull NaNs; maximum tested finite difference about 1.1e-14 |
| Treemap geometry | Same four rectangles to floating-point tolerance |
| Naive projection | Same coordinates and state placement when supplied MATLAB's saved permutation |
| Sammon Newton update | One finite reference step agrees within 1e-13; stress agrees within 1e-15 |
| Color maps | MATLAB jet/hot/spring/summer/autumn/winter/cool/gray/hsv/prism/parula match tested lengths 1, 4, 100 |
| p53 Control and Nutlin examples | Same attractor states, classifications, and basin ratios within the archived CSV precision |

The final automated suite recorded **117 passing tests** in `validation/pytest.xml`. It includes numerical reference checks, independent hand-calculated transition tests, invalid inputs, mutation behavior, file roundtrips, large network loading, fair-bit sampling, scientific image generation, all 14 GUIDE window definitions, network import, threaded analysis, threaded plotting, figure controls, and reopening results. MATLAB fixtures and the scripts that generated them are included. `validation/comparison_metrics.json` contains measured errors.

The 201-node examples were tested for file compatibility and state updates using their actual saved states, with missing-rule retention explicitly selected. Full 10000-state attractor searches and phenotype equivalence were **not** validated against MATLAB for these incomplete inputs. Do not treat successful loading as full scientific validation.

## Preserved scientific semantics

- Synchronous updates use source-row/target-column interaction matrices. Zero weighted input retains the prior state.
- States and truth-table rows use ascending, MSB-first binary encoding. No column reversal or transposition is applied to the model.
- Weighted mutations set basal values to +/-1000; they do not impose a mathematically different hard clamp. Rule link deletion fixes the removed source input to zero and selects corresponding truth-table rows.
- Fixed-node files change initial states only, retain duplicate rows, and do not clamp nodes throughout simulation.
- Attractor confirmation is exact within the user-specified search duration. No heuristic or approximate cycle finder replaces it. Unresolved states are counted and reported. The source's different unresolved-state denominators for weighted/rules analyses are retained.
- Node activation probability is `0.5 + 0.5*tanh(noise*input)` for nonzero input and `c`/`1-c` for zero input, according to prior state. Transition probabilities multiply the node probabilities.
- Master-equation updates retain the source flux formulation for subsets, including rows whose sums are less than one. Pruned matrices are not silently renormalized. The 98% stopping rule and minimum 11 iterations are preserved.
- Fate matching expands allowed-state Cartesian products, treats blank cells as wildcards, and stratifies average activities using strict thresholds below 0.2 and above 0.8; the inclusive middle range becomes 2.
- Trajectory mapping retains the original contiguous probability-ranked interval. It is not replaced with a graph path algorithm.
- Potential-energy values retain the original transform: `raw=-log(p)`, subtract its maximum, raise to the selected integer factor, divide by the minimum transformed value. The source's zero-probability plotting replacement is retained. Plotting does not overwrite analysis probabilities.

## Known differences and source defects

1. **Desktop rendering:** Qt recreates the saved GUIDE layout, labels, groups, defaults, and original image buttons. Windows decorations, font metrics, disabled states, borders, and native dialogs differ. Font fitting prevents clipped labels. Automated GUI tests run offscreen on Windows; every native window has not been manually operated at every display scaling setting.
2. **BioGraph:** MATLAB's proprietary BioGraph renderer and editor are replaced with NetworkX. Graph meaning, signs, weights, and labels are retained, and saved Python node positions are reused. BioGraph's exact layout, dragging/editor behavior, fake-node self-loop geometry, and private APIs are not reproduced.
3. **Graphviz:** the supplied Graphviz 2.38 is included locally. Positions and cubic edge control points come from Graphviz. Generated DOT retains the original implicit node-creation order and positive-weight >=1 filter; isolated nodes and positive weights below 1 are therefore omitted by this particular source plotting path, while the BioGraph replacement shows them. The desktop Graphviz workflow displays its complete generated SVG in a native Qt viewer, preserving Graphviz labels, clusters, shapes, and arrowheads with zoom, pan, and image/vector export. The additional Matplotlib graph preview API supports common shapes and cubic paths but does not reproduce every advanced DOT feature. Qt SVG text metrics and advanced styling have not been compared for every DOT input. This legacy binary imports MSVCR90.dll; a fresh Windows machine may need its Visual C++ runtime. A compatible separately installed Graphviz can be used on PATH when the local `.graphviz` folder is absent.
4. **Surfaces:** data, MATLAB-order placement, labels, original view orientation, color maps, and z limits are retained. Matplotlib's lighting, contour generation, anti-aliasing, face shading, legend placement, and 3D label positioning differ. Display tessellation provides interpolated coloring without changing the exported analysis grid. MATLAB's texture/interp/flat context-menu modes are not identical backend operations and are not separately exposed. Figure comparisons are content/geometry checks and visual inspection, not a pixel-level acceptance test for every case study.
5. **Sammon numerics:** the same PCA initialization, gradient, diagonal Hessian, step halving, stress scale, and convergence criterion are implemented. Negative roundoff in squared distances is clamped to zero. Several unmodified MATLAB full-reference runs produced complex values and NaNs; these are retained as failed reference evidence. A finite one-step case was compared successfully, and Python completed a finite 242-state landscape rendering. This does not establish identical full Sammon convergence. Overlapping PCA points and other degeneracies produce an explicit error, with Naive Random or a suitable state subset remaining available. Random initialization and precomputed-distance input are supported through the Python API.
6. **Potential-energy source defect:** even exponents yield a zero normalization denominator in the source formula; uniform distributions can do the same. The saved GUIDE default factor is 8. Python reports the undefined transform and asks for an odd factor/nonuniform distribution; it does not replace it with arbitrary zero energies. Choose factor 1 for ordinary use.
7. **Incomplete truth tables:** both large examples omit 17 node files. Strict loading rejects them. An explicit opt-in retains each missing node's current state. The original parser offered continuation, but its downstream indexing can fail on empty rule arrays. Python makes the interpretation explicit rather than inventing biological rules. This is a documented behavior repair and is not certified equivalent for those omitted nodes.
8. **Sammon size selection:** the original GUI computes a `ModifiedStateSpace` that is not reliably consumed by its plot generator. Python actually uses the user-selected plotting subset. The source's optimal-size behavior selects 128. The analyzed state space and saved results remain unchanged. Exact scientific calculations are not replaced by this visualization-only sampling choice.
9. **Randomness:** NumPy PCG64 replaces MATLAB's random generator. Unseeded random samples and naive placements differ. Their independent fair-bit/unique-sampling behavior is tested statistically; identical seeds do not imply MATLAB-identical samples. A saved permutation/coordinate set reproduces placement. Original Naive Mapping MAT files omit their permutation and cannot restore that missing information; Python NPZ exports include it.
10. **Export and persistence:** original weighted/truth/state/mutation/fate formats are supported; MAT v5 and the supplied v7.3 data are readable. Python JSON replaces serialized MATLAB class objects. Python does not create editable MATLAB FIG files. CSV output fields preserve the original attractor-table meaning and ordering; Python may emit greater numeric precision and uses standard CSV quoting. Results are exported explicitly rather than always writing timestamped folders automatically. The application adds result reopening and a small network editor. Original standalone export_fig utilities are replaced with Matplotlib/Qt; CMYK, clipboard image transfer, PDF append, Ghostscript utilities, and private MATLAB graphics APIs are not independently replicated.
11. **Capacity and diagnostics:** allocation guards reject exhaustive state sets above the configured byte limit and exact transition matrices above 1 GiB by default. Users must choose sampling/pruning explicitly. Invalid values, incomplete/noncanonical truth tables, cancellation, and nonconvergence are reported. More transparent failure reporting replaces broad silent MATLAB catches.

## Graphical evidence

`validation/matlab_basin.png` and `validation/matlab_treemap.png` were produced by the original MATLAB plotting code. Matching Python data/permutation figures are under `validation/python/`. Additional Python probability, energy, Sammon energy, and network diagrams were rendered from computed data. `validation/gui/` contains all recreated GUIDE dialogs and the main window. Images are QA evidence, never runtime substitutes for plots.

## Remaining validation

Not completed: exhaustive MATLAB/Python comparison of all case-study conditions; complete 201-node phenotype equivalence; large/rare cyclic grouping comparisons against MATLAB; pixel-perfect BioGraph/Graphviz reproduction; case-by-case Qt SVG fidelity for every advanced custom DOT feature; full Sammon convergence parity; every third-party export_fig option; clean-machine installation testing; manual accessibility/DPI validation; recovery of serialized MATLAB handle-class sessions. These limitations are part of the delivered migration status, not silently omitted features.
