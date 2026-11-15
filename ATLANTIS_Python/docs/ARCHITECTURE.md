# Architecture and source examination

The outer ZIP was extracted before implementation. Its 113 MATLAB files, 14 GUIDE figures, 13 MAT files, 41 CSV files, 14 JPEG interface assets, 10 screenshots, one 45-page manual, and supporting files were inventoried. The nested supplementary RAR was also extracted; its inventory includes two additional MATLAB conversion scripts, four DOT diagrams, 24 MAT datasets, comparison scripts, and archived outputs. Git internals are source-control history rather than executable application content. No standalone ATLANTIS research-paper PDF was supplied; the manual and source were the available references. The manual's bibliography and the case-study readmes were inspected.

The original application has a singleton GUIDE main window. Its root `UserData` holds a mutable `NetworkDataStructure`, or a cell array of variants. Six image buttons open network generation, mutation, sketching, deterministic analysis, probabilistic analysis, and result visualization. Input routines populate network properties; callbacks collect analysis settings. Results are stored back on the network object and written through CSV/MAT helper routines. Landscape generators read those same properties, optionally change the plotting state space, project it, then create surfaces and annotations. Third-party export_fig utilities and MATLAB BioGraph provide platform-specific rendering services.

Python separates the same responsibilities:

| Original responsibility | Python module |
| --- | --- |
| NetworkDataStructure and update rules | `atlantis.model` |
| Original file formats and result exports | `atlantis.io` |
| Full/random state generation; initial-node fixing | `atlantis.states` |
| Synchronous candidate search, cycle confirmation, basins | `atlantis.analysis` |
| Tanh transition law and master-equation iteration | `atlantis.analysis` |
| Fate-rule Cartesian products and wildcard classification | `atlantis.fates` |
| Sammon/Newton projection and natural-neighbor interpolation | `atlantis.projection` |
| Treemap partitioning and cyclic-state grid grouping | `atlantis.geometry` |
| Scientific surfaces, graphs, color maps, treemaps | `atlantis.plots` |
| GUIDE control construction | `atlantis.guide` and `assets/guide/*.json` |
| Original six-button workflow and worker coordination | `atlantis.gui` |
| Figure interaction and export | `atlantis.figure_window` |
| Supplementary DNF/BoolNet conversion | `atlantis.boolnet` |

Network variants are deep copies. Explicit result records replace mutation of global MATLAB graphics state. Qt worker threads keep the application responsive and support cancellation. NumPy/SciPy use float64 for calculations; binary states are uint8. Files retain MSB-first ordering. Interaction matrices retain the MATLAB orientation: source in rows, target in columns. No MATLAB calls exist in the `atlantis/` package.

All GUIDE layouts were decoded from their MAT/HDF representation into JSON control specifications. The Python GUI uses saved positions, parent groups, text, radio defaults, colors, and fonts, with Qt-specific font fitting. The generated scientific figures remain data-driven and interactive; original screenshots are reference material only.

Graphviz is the original external layout engine, not a replacement algorithm. Graphviz-generated positions and cubic Bezier control points are used in the Python drawing. NetworkX replaces the proprietary BioGraph viewer. The Graphviz desktop path uses a native Qt SVG viewer for complete generated vector output; its Matplotlib preview API also uses Graphviz coordinates. Matplotlib and Qt replace MATLAB graphics/export helpers. PNG/JPEG/TIFF and vector PDF/SVG/EPS exports are available, but MATLAB FIG files are reference definitions rather than editable Python figure files.

See `FUNCTION_MAPPING.csv` for all original `.m` files, including supporting libraries and the two supplementary converters. A mapping to a library replacement means its role is covered; it does not promise identical private APIs or every latent third-party option.
