# ATLANTIS for Python

## Quantum integration (0.2.4)

The existing desktop now includes **Quantum / Experiments** for ideal reference,
Qiskit Aer, noisy Aer and Bring Your Own IBM account execution. Read
[the integrated setup and user guide](docs/QUANTUM_USER_GUIDE.md) first; use
`requirements-integrated.lock.txt` for the verified integration environment.
See [quantum correctness](docs/QUANTUM_CORRECTNESS.md) and the handoff report for
verified results and incomplete acceptance criteria. No live QPU experiment has
been performed. Historical port results below predate this integration.

A Windows desktop migration of the supplied ATLANTIS MATLAB toolbox. Python 3.12; no MATLAB or MATLAB Runtime is used by the application.

This is a runnable migration with tested analysis engines and recreated GUIDE interfaces. It is **not a claim of complete visual or behavioral equivalence**. Read `docs/COMPARISON.md` for known source defects, renderer differences, and validation limits.

## Install and launch on Windows

1. Extract the entire ZIP into a writable folder, such as Documents\ATLANTIS_Python. Keep its subfolders together.
2. Install Python 3.12, including the Python launcher (`py`).
3. Double-click `install_windows.bat`. It creates `.venv` and installs the pinned dependencies. Internet access is needed for this step.
4. Double-click `launch_atlantis.bat`.

Alternatively, from PowerShell in the extracted folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_atlantis.py
```

The legacy Graphviz binary may need its Visual C++ runtime (MSVCR90.dll) on a fresh PC. A separately installed Graphviz on PATH is used when the local `.graphviz` folder is absent.

The ZIP includes a local Graphviz 2.38 administrative extraction from the supplied installer. It is used without installing Graphviz globally. NetworkX is also available for drawing networks. A separately installed Graphviz on PATH can be used when the local folder is absent. The old Graphviz distribution is retained for layout fidelity; its license is in `.graphviz/share/license.rtf`.

`PySide6-Essentials` supplies the Qt desktop widgets and SVG functionality used here. The much larger WebEngine and Addons packages are unnecessary.

## Original workflow

- **Generate Network**: choose weighted inputs or node names plus a truth-table folder. All four supplied case studies are under `examples/`.
- **Modify Network**: select one or more original mutation TXT/CSV files. Each file produces a variant of the original loaded network. Node mutations use the original +/-1000 basal values for weighted networks. Link mutations use `Source>Target,2`.
- **Sketch Network**: use the BioGraph replacement (NetworkX) or Graphviz. Graphviz supports original generated DOT and custom DOT files. The BioGraph replacement preserves connections, signs, and labels; its layout differs from MATLAB's proprietary viewer.
- **Deterministic Analysis**: generate exhaustive or sampled states, or load CSV/TXT/MAT states. Optional fixed-node files change initial states only. Load cell-fate logic if desired, then run.
- **Probabilistic Analysis**: available for weighted networks, matching the original restriction. Set noise, degradation, error margin, and maximum timesteps. Pruning is available in Generate States. Optional trajectory mapping uses the original probability-ranked interval method.
- **Visualize Results**: BSL = basin size, PL = probability, PEL = potential energy, CFL = cell-fate treemap. Choose Naive Random or Sammon mapping, colors, annotations, grouping, and export settings. The Sammon size-selection dialog is available for incompatible state counts.
- **Right-click the main window** for network JSON import/export, a network editor, result export/reopening, saved projection import, DOT export, and the supplied manual.
- Every figure has rotation/zoom/pan controls and a **Figure** menu for exports, annotations, contours, transparency, colors, and Z-axis inversion. When tooltips are enabled, click landscape state locations to inspect their state and plotted value. Export plot data to NPZ to retain coordinates and random placement.

Analysis results remain in memory until exported. Use the results table's **Export Results** button or the main window's right-click menu to save CSV, JSON, and MAT results. A saved result folder can be reopened. Saved results include convergence status; exhausting the iteration limit is not reported as convergence.

### Start with the yeast example

Load `examples/Case Study 1/Input Files/NetworkFile.csv`. In deterministic analysis generate the full 2048 states, set search duration 200, and load `Cell Fate Determination Logic.csv` from the same folder. This yields seven point attractors; the dominant basin is 0.861328125. For a cell-fate treemap select CFL after analysis.

For the probabilistic example generate states with pruning enabled, use noise 5, degradation 0.001, error margin 1e-7, and 200 or more steps. There are 242 pruned states. At 200 steps the original and Python solvers have not met the stopping criterion.

For PEL choose an **odd** noise-reduction factor, such as **1**. The saved GUIDE default is 8, but the source's normalization divides by zero for even factors; Python reports this instead of drawing invalid data. Some complete Boolean cubes also produce overlapping PCA points in the source Sammon initialization. Use pruned/custom states or Naive Random in that case. No automatic approximation is substituted.

The 201-node case studies omit 17 truth-table files, including input and phenotype nodes. Loading is strict by default. The GUI offers an explicit option to continue with those nodes retaining their current state. This interpretation is documented and has not been established as MATLAB-equivalent for the complete large-model analyses.

## Additional CLI

```powershell
.\.venv\Scripts\python.exe -m atlantis.cli "examples/Case Study 1/Input Files/NetworkFile.csv" --fates "examples/Case Study 1/Input Files/Cell Fate Determination Logic.csv" --probabilistic --prune --steps 200 --output results\yeast
```

Use `--help` for truth-table folders, custom states, mutations, sampling, seeds, and analysis settings. The CLI calls the same analysis code as the GUI.

## Validation and project layout

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

- `atlantis/`: network model, readers/writers, deterministic/probabilistic engines, fate logic, projections, figures, Qt GUI.
- `atlantis/assets/`: controls extracted from all 14 GUIDE files, original interface images, and MATLAB color maps.
- `examples/`: all supplied example inputs and the original supplementary RAR.
- `supplementary/`: the extracted nested RAR, including archived results and DOT diagrams.
- `reference/`: original MATLAB software and manual in the distribution ZIP. The development workspace uses `original/ATLANTIS/` instead.
- `tests/`: algorithm, compatibility, MATLAB-reference, renderer, and GUI tests.
- `validation/`: actual MATLAB fixtures, comparison metrics, test results, and rendered images.
- `docs/`: architecture, full inventory, function mapping, checklist, and comparison report.
- `tools/`: audit, reference-generation, rendering, and packaging scripts. MATLAB scripts are development-only; ordinary application execution never calls MATLAB.

The exact transition matrix scales quadratically in the number of analyzed states. Enumeration and matrix memory checks reject excessive requests and ask you to choose sampling or pruning explicitly. The software never silently replaces exact computations with an approximation.

## Attribution

Original ATLANTIS: Biomedical Informatics Research Laboratory, LUMS, Pakistan. Supplied source headers identify the toolbox as version 2.0.0, the manual as v3.0, and saved interfaces as version 1.0.0. These inconsistencies are retained in the reference archive. The Python migration is version 0.1.0. Original assets and notices are retained. ATLANTIS is GPL v3; see `LICENSE` and `THIRD_PARTY_NOTICES.md`.
