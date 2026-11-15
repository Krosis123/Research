from pathlib import Path
import re,csv,json
from collections import Counter
root=Path('original/ATLANTIS')
if not root.exists():root=Path('reference')
rows=[]
exact={
'NetworkDataStructure':'atlantis.model.Network', 'parse_NetworkFile':'atlantis.io.load_weighted', 'parse_LogicTables':'atlantis.io.load_rules',
'addMutations_WeightsBased':'atlantis.model.Network.mutate','addMutations_RulesBased':'atlantis.model.Network.mutate',
'generate_StatesCombinations':'atlantis.states.all_states','generate_StateCombinations_randomSampling':'atlantis.states.random_states','fix_NodeStates':'atlantis.states.fix_initial_nodes',
'deterministicEngine_WeightsBased':'atlantis.analysis.deterministic_analysis', 'deterministicEngine_RulesBased':'atlantis.analysis.deterministic_analysis',
'synchronousAttractorSearch_WeightsBased':'atlantis.analysis.preliminary_search','synchronousAttractorSearch_RulesBased':'atlantis.model.Network.step (unused source helper)',
'perform_DeterministicAnalysis':'atlantis.analysis.deterministic_analysis','classify_Attractors':'atlantis.analysis.deterministic_analysis + atlantis.fates.FateLogic',
'summarize_AttractorActivity':'atlantis.analysis.Attractor.average / stratified','attractorFrequency':'atlantis.analysis.deterministic_analysis (counts)',
'parse_CellFateLogic':'atlantis.fates.load_fate_logic','parse_CellFateLogic 2':'atlantis.fates.load_fate_logic','associate_CellFates':'atlantis.fates.FateLogic.associate',
'find_StateTransitionProbabilities':'atlantis.analysis.transition_probabilities','find_SteadyStateProbabilities':'atlantis.analysis.steady_state_probabilities','StateSpacePruning':'atlantis.analysis.state_space_pruning',
'perform_ProbabilisticAnalysis':'atlantis.analysis.probabilistic_analysis','map_Trajectory':'atlantis.analysis.map_trajectory','parse_TrajectoryBounds':'atlantis.io.load_states + atlantis.analysis.map_trajectory',
'save_DeterministicAnalysisResults':'atlantis.io.export_results','save_ProbabilisticAnalysisResults':'atlantis.io.export_results',
'sammonMapping':'atlantis.projection.sammon_mapping','naiveMapping':'atlantis.projection.naive_grid','groupCyclicAttractors':'atlantis.geometry.group_cyclic','findPositions':'atlantis.geometry.find_positions','findValidPositions':'atlantis.geometry.group_cyclic',
'binary2Decimal':'atlantis.model.binary_to_decimal','decimal2binary':'atlantis.model.decimal_to_binary','generateDotFile':'atlantis.plots.network_dot',
'sketchGraphUsingGraphViz':'atlantis.graphviz_window.graphviz_svg / GraphvizWindow + plots.graphviz_figure preview','sketchGraphUsingBiograph':'atlantis.plots.network_figure',
'plot_CellFateLandscape':'atlantis.plots.cell_fate_figure + atlantis.geometry.treemap','generate_CellFateLandscape':'atlantis.gui.Application.plot_from_dialog',
'generate_AttractorLandscape':'atlantis.gui.Application.plot_from_dialog','plot_AttractorLandscape':'atlantis.plots.landscape_figure',
'plot_PotentialEnergyLandscape':'atlantis.plots.landscape_values / landscape_figure','plot_BasinSizeLandscape':'atlantis.plots.landscape_values / landscape_figure','plot_ProbabilityLandscape':'atlantis.plots.landscape_values / landscape_figure',
'save_StateSpace':'atlantis.io.save_states + FigureWindow.export_data','annotate_AttractorLandscape':'atlantis.plots.landscape_figure',
'cell2csv':'atlantis.io.write_rows','csv2cell':'atlantis.io.read_rows','csvimport':'atlantis.io.read_rows','saveMatFile':'atlantis.io.save_states / export_results',
'ATLANTIS':'atlantis.gui.Application','GenerateNetwork':'Application.generate_network / network_input','NetworkInputMenu1':'Application.network_input','NetworkInputMenu2':'Application.network_input',
'ModifyNetwork':'Application.modify_network','GenerateStates':'Application.generate_states','DeterministicAnalysisMenu':'Application.analysis_menu / run_analysis','ProbabilisticAnalysisMenu':'Application.analysis_menu / run_analysis',
'NetworkSketchingOptions':'Application.sketch_network','GraphVizMenu':'Application.graphviz_menu','VisualizeResultsMenu':'Application.visualize / plot_from_dialog','StateSpaceSizeSelectionMenu':'Application.select_sammon_states',
'CancelSimulationButton':'QProgressDialog + atlantis.gui.Job.cancel', 'ExportFigureMenu':'atlantis.figure_window.FigureWindow.export','exportFigure':'FigureWindow.save_from_dialog / matplotlib.Figure.savefig','figExportCallBack':'FigureWindow.export',
'assembleToolTipData':'FigureWindow.pick','customToolTips_NaiveMapping':'FigureWindow.pick','customToolTips_SammonMapping':'FigureWindow.pick',
'generate_AttractorStateToolTipData':'FigureWindow.pick','generate_SteadyStatesToolTipData':'FigureWindow.pick',
'addPlotModificationOptionsMenu':'FigureWindow.__init__','addToggleAnnotationMenu':'FigureWindow.toggle_annotations','toggleAnnotations':'FigureWindow.toggle_annotations',
'togglePlotVisibility':'FigureWindow.toggle_surface / toggle_contour','togglePlotAlpha':'FigureWindow.alpha','togglePlotColor':'FigureWindow.recolor','toggleBoxColors':'FigureWindow.recolor','InvertPlot':'FigureWindow.invert',
'isMemorySufficient':'atlantis.states.all_states + analysis.transition_probabilities limits','updateGraphics':'Application.update_enabled / decorate_main','enableATLANTIS':'Application.update_enabled',
'enableDisableFig':'Qt widget enable/modal state','bringToFocus':'Qt show / activateWindow','progressbar':'QProgressDialog + Job.progress',
'pauseButton':'Qt event loop (standalone unused MATLAB helper not replicated)',
'addContextMenuToFigure':'FigureWindow Figure menu','addLegendsForAttractorPlots':'landscape_figure legend','addLegendsForBiograph':'network_figure colored edges (standalone helper not used by source sketcher)',
'joinStr_CellArr':'Python str.join','sortCellArr':'Python stable sorted / NumPy argsort','uniqueCellArray':'Python sets / NumPy unique','generate_OutputFolderName':'Application.export_results (explicit destination selection)',
'restoreUImenus':'Qt window menu lifecycle','toggleEdgeLabels':'network_figure(labels=...)','toggleSurfacePlotFaceColor':'Matplotlib surface renderer; MATLAB texture/interp/flat switching not replicated',
'TruthTable2BooleanExpression':'atlantis.boolnet.truth_tables_to_boolnet',
}
for base in [root,Path('supplementary')]:
 for p in base.rglob('*.m'):
  if '.git' in p.parts:continue
  source=p.read_text(errors='replace');name=p.stem; path=p.relative_to(base).as_posix()
  target=exact.get(name)
  note='See COMPARISON.md and CHECKLIST.md for validation scope.'
  if 'Export Figure/Supplementary Functions/' in path:
   target='Matplotlib Figure.savefig / Qt figure canvas';note='Third-party export_fig helper replaced by backend; not a public API-compatible port. Clipboard, append-PDF, CMYK, Ghostscript internals are not replicated.'
  if target is None: target='Qt/NumPy/Matplotlib infrastructure replacement';note='Support helper role consolidated; no standalone MATLAB-compatible function is provided.'
  if name=='sketchGraphUsingBiograph':note='Scientific graph data preserved; proprietary BioGraph layout/editor not reproduced.'
  if name=='sammonMapping':note='Newton update verified; roundoff clamp and degeneracy errors documented. Original full reference runs produced NaNs.'
  rows.append({'MATLAB file':('ATLANTIS/' if base==root else 'Supplementary/')+path,'MATLAB declarations':' | '.join(re.findall(r'^\s*(?:function|classdef)\s+(.+)',source,re.M)),'Python implementation':target,'Notes':note})
with Path('docs/FUNCTION_MAPPING.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
files=[]
for base in [root,Path('supplementary')]:
 for p in base.rglob('*'):
  if p.is_file() and '.git' not in p.parts:
   files.append({'path':('ATLANTIS/' if base==root else 'Supplementary/')+p.relative_to(base).as_posix(),'bytes':p.stat().st_size,'extension':p.suffix.lower()})
Path('docs/inventory.json').write_text(json.dumps(files,indent=2))
counts=Counter(x['extension'] for x in files)
Path('docs/INVENTORY.md').write_text('# Complete source inventory\n\nThe full machine-readable inventory is `inventory.json`. Git history is excluded. The nested RAR is inventoried both as an outer asset and as extracted supplementary contents.\n\n| Extension | Files |\n| --- | ---: |\n'+'\n'.join(f'| {k or "(none)"} | {v} |' for k,v in sorted(counts.items()))+'\n\nMATLAB-to-Python mappings cover '+str(len(rows))+' MATLAB files.\n')
print('Mapped',len(rows),'MATLAB files;',len(files),'total files inventoried')
