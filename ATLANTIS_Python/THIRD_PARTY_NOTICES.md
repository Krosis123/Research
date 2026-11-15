# Third-party notices

- Original ATLANTIS toolbox and images: Biomedical Informatics Research Laboratory, LUMS, Pakistan. Original GPL v3 license, copyright headers, manual, and support-library notices are retained in `reference/` in the ZIP. The migration is distributed under GPL-3.0-or-later; see `LICENSE`.
- Sammon projection: the supplied MATLAB routine credits Dr Gavin C. Cawley, November 2007. The Python implementation follows that routine's PCA/Newton/step-halving algorithm with documented numeric guards.
- Graphviz 2.38: extracted from the MSI supplied with ATLANTIS. The complete supplied administrative image is retained under `.graphviz/`, including its Common Public License and supporting notices in `.graphviz/share/license.rtf` and other distribution files. Graphviz is an external layout/rendering dependency. No MATLAB component is used to run it.
- Python dependencies installed through pip retain their own licenses: NumPy, SciPy, Matplotlib, NetworkX, PySide6/Qt, h5py, Pillow (a Matplotlib dependency), and pytest. Their package license files accompany the installed packages. PySide6-Essentials supplies the GUI modules without requiring WebEngine.
- The original export_fig support sources and their own license are preserved for reference; Python delegates figure export to Matplotlib and Qt rather than incorporating those MATLAB implementations.
- System fonts are loaded from the user's Windows installation when available. No proprietary font files are included in this project.

The original source, examples, nested supplementary archive, and test fixtures are included for traceability. The external R comparison scripts are reference material and are not runtime dependencies of the Python application.
# Quantum integration additions

The `atlantis/quantum/ross` package is adapted from the user-supplied
Ross_Adaptive_v2_Benchmark reproduction. Original modules remain in the supplied
archive. Its scientific algorithm and five-gene fixture derive from Rossini et al.
(2025), DOI 10.1016/j.patter.2025.101295, and
https://github.com/sysbio-bioinf/QuantumAttractorSearch (GPL-3.0).
This integrated application is distributed under the existing GPL-3.0-or-later
license. Qiskit, Qiskit Aer and IBM Runtime are Apache-2.0 components. PySide6
Essentials is LGPL/GPL/commercial licensed; distributed dependencies retain their
own licenses. Dependencies are installed separately rather than bundled binaries.
See installed distribution metadata for complete third-party license texts.

