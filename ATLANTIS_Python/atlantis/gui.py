"""Desktop orchestration for the original ATLANTIS GUIDE workflow."""
from pathlib import Path
from threading import Event
import traceback
import numpy as np
from PySide6 import QtCore,QtGui,QtWidgets as W
from .guide import GuideWindow,ASSETS,show_warning
from .figure_window import FigureWindow
from . import io
from .model import Network,TruthRule
from .states import all_states,random_states,fix_initial_nodes
from .fates import load_fate_logic
from .analysis import deterministic_analysis,probabilistic_analysis,map_trajectory,CancelledError
from .plots import network_figure,graphviz_figure,cell_fate_figure,landscape_figure,network_dot
from .quantum.hardware import ProviderWaitExpired


class Job(QtCore.QThread):
    progress=QtCore.Signal(float,str); success=QtCore.Signal(object); failure=QtCore.Signal(str,str)
    def __init__(self,work,parent=None): super().__init__(parent); self.work=work; self.cancel=Event()
    def run(self):
        try: self.success.emit(self.work(self.progress.emit,self.cancel.is_set))
        except ProviderWaitExpired as error:
            self.failure.emit(str(error), 'IBM wait ended')
        except CancelledError as error:
            self.failure.emit(str(error) or 'Analysis cancelled. Previous results are retained.', 'Cancelled')
        except Exception:
            self.failure.emit(traceback.format_exc(), 'Error')


class Application(GuideWindow):
    def __init__(self):
        super().__init__('ATLANTIS'); self.setWindowTitle('ATLANTIS - Attractor Landscape Analysis Toolbox (Python)')
        self.networks=[]; self.original_network=None; self.states=None; self.fate_logic=None; self.results={}; self.windows=[]; self.dialogs=[]; self.job=None; self.prune=False; self.plot_cache={}; self.modified_states=None
        self.last_directory=str(Path(__file__).resolve().parent.parent/'examples'); self.saved_mapping=None
        self.decorate_main()
        for tag,method in [('GenerateNetwork',self.generate_network),('ModifyNetwork',self.modify_network),('SketchNetwork',self.sketch_network),('DeterministicAnalysis',lambda:self.analysis_menu(False)),('ProbabilisticAnalysis',lambda:self.analysis_menu(True)),('VisualizeResults',self.visualize)]: self.bind(tag,method)
        self.controls['LogoButton'].setText(''); self.controls['LogoButton'].setFlat(True)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu); self.customContextMenuRequested.connect(self.context)
        self.update_enabled()
        self.quantum_button=W.QPushButton('Quantum / Experiments',self)
        self.controls['versionHistory'].hide()
        self.quantum_button.setGeometry(self.width()-190,38,180,24)
        self.quantum_button.clicked.connect(lambda:self.safe(self.quantum_analysis))

    def quantum_analysis(self):
        if not self.networks:
            raise ValueError('No network is loaded. Use Generate Network to import or create a network, then reopen Quantum / Experiments.')
        from .quantum_ui import QuantumDialog
        d=QuantumDialog(self); self.dialogs.append(d); d.show()

    def decorate_main(self):
        images={'GenerateNetwork':'Create Network','ModifyNetwork':'Edit Network','SketchNetwork':'Sketch Network','DeterministicAnalysis':'Deterministic Analysis','ProbabilisticAnalysis':'Probabilistic Analysis','VisualizeResults':'View Results','LogoButton':'Logo'}
        for tag,name in images.items():
            p=ASSETS/'images'/'Active'/(name+'.jpg')
            if p.exists():
                icon=QtGui.QIcon(str(p)); inactive=ASSETS/'images'/'Inactive'/(name+'.jpg')
                if inactive.exists(): icon.addFile(str(inactive),QtCore.QSize(),QtGui.QIcon.Disabled)
                b=self.controls[tag]; b.setText(''); b.setIcon(icon); b.setIconSize(b.size()); b.setStyleSheet('QPushButton {border:0px;background:white;}')
        self.set_text('versionHistory','Python 0.2.4')

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'controls'):
            for tag in ['GenerateNetwork','ModifyNetwork','SketchNetwork','DeterministicAnalysis','ProbabilisticAnalysis','VisualizeResults','LogoButton']:
                if tag in self.controls: self.controls[tag].setIconSize(self.controls[tag].size())

    def update_enabled(self):
        loaded=bool(self.networks)
        for tag in ['ModifyNetwork','SketchNetwork','DeterministicAnalysis']: self.controls[tag].setEnabled(loaded)
        self.controls['ProbabilisticAnalysis'].setEnabled(loaded and self.networks[0].weights is not None)
        self.controls['VisualizeResults'].setEnabled(bool(self.results))

    def context(self,position):
        menu=W.QMenu(self)
        for title,callback in [('Open Python Network...',self.open_network),('Bounded attractor and basin search...',self.bounded_search),('Save Network...',self.save_network),('Configure External and Fixed Nodes...',self.configure_inputs),('Edit / Create Network...',self.edit_network),('Export Analysis Results...',self.export_results),('Open Saved Results...',self.open_results),('Recover Classical Job...',self.recover_classical_job),('Load Saved Mapping...',self.load_mapping),('Save Regulatory DOT...',self.save_dot),('User Manual',self.help)]:
            a=menu.addAction(title); a.triggered.connect(lambda _,f=callback:self.safe(f))
        menu.exec(self.mapToGlobal(position))

    def dialog(self,name):
        d=GuideWindow(name,self); d.setAttribute(QtCore.Qt.WA_DeleteOnClose); self.dialogs.append(d)
        d.bind('Help',self.help); d.finished.connect(lambda *_:self.update_enabled()); d.show(); return d

    def file(self,title,filters='ATLANTIS inputs (*.csv *.txt *.mat *.json);;All files (*)',multiple=False):
        if multiple: paths,_=W.QFileDialog.getOpenFileNames(self,title,self.last_directory,filters); return paths
        path,_=W.QFileDialog.getOpenFileName(self,title,self.last_directory,filters)
        if path: self.last_directory=str(Path(path).parent)
        return path

    def help(self):
        root=Path(__file__).resolve().parent.parent
        manual=root/'reference'/'User Manual'/'A Complete Guide to Using ATLANTIS (v3.0).pdf'
        if not manual.exists(): manual=root/'original'/'ATLANTIS'/'User Manual'/'A Complete Guide to Using ATLANTIS (v3.0).pdf'
        if manual.exists(): QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(manual)))
        else: W.QMessageBox.information(self,'ATLANTIS','See README.md and docs/COMPARISON.md in the project folder.')

    def set_network(self,network):
        self.original_network=network.copy(); self.networks=[network]; self.states=None; self.fate_logic=None; self.results={}; self.plot_cache={}; self.modified_states=None; self.update_enabled()

    def generate_network(self):
        d=self.dialog('GenerateNetwork')
        d.bind('Ok',lambda:self.network_input(d))

    def network_input(self,d):
        rules=d.checked('NetworkType2'); d.accept()
        w=self.dialog('NetworkInputMenu2' if rules else 'NetworkInputMenu1'); w.paths={}
        if rules:
            def node_list():
                p=self.file('Select Node List','Node lists (*.txt *.csv)')
                if p: w.paths['nodes']=p; w.set_text('BrowseFile',Path(p).name)
            def tables():
                p=W.QFileDialog.getExistingDirectory(w,'Select Folder Containing Node Truth Tables',self.last_directory)
                if p: w.paths['tables']=p; w.set_text('BrowseFolder',p)
            w.bind('BrowseNodeList',node_list); w.bind('BrowseNodeLogicTables',tables)
        else:
            def weighted():
                p=self.file('Select Network File','Network (*.txt *.csv *.json)')
                if p: w.paths['weighted']=p; w.set_text('BrowseFile',Path(p).name)
            w.bind('BrowseNetworkFile',weighted)
        def load():
            if rules:
                if not {'nodes','tables'}<=w.paths.keys(): raise ValueError('Select a node list and truth-table folder')
                try: network=io.load_rules(w.paths['nodes'],w.paths['tables'])
                except ValueError as e:
                    if not str(e).startswith('Missing truth table'): raise
                    candidate=io.load_rules(w.paths['nodes'],w.paths['tables'],missing_policy='unspecified')
                    missing=[name for name,r in zip(candidate.names,candidate.rules) if r is None]
                    answer=W.QMessageBox.question(
                        w, 'Missing Truth Tables',
                        'Import with unspecified rules for: '+', '.join(missing)
                        +'. Resolve them through the network editor or Configure External and Fixed Nodes before analysis.')
                    if answer!=W.QMessageBox.Yes: return
                    network=candidate
            else:
                if 'weighted' not in w.paths: raise ValueError('Select a network file')
                network=io.load_network(w.paths['weighted'])
            self.set_network(network); w.accept()
        w.bind('Ok',load)

    def bounded_search(self):
        from .bounded_basins import bounded_basins
        import json
        if not self.networks:
            raise ValueError("Open a network first")
        net = self.networks[0].copy()
        budget,ok = W.QInputDialog.getInt(self,"Bounded search",f"{net.name}: maximum starts (period and transient up to 6)",65536,1,10000000)
        if not ok:
            return
        path,_ = W.QFileDialog.getSaveFileName(self,"Save bounded basin results","bounded-basins.json","JSON (*.json)")
        if not path:
            return
        def complete(result):
            Path(path).write_text(json.dumps(result),encoding="utf-8")
            scope = "Exhaustive" if result["exhaustive"] else "Uniform sample"
            W.QMessageBox.information(self,"Bounded basins",f"{scope}: {len(result['basins'])} sampled/enumerated cycles across {result['starts']} starts. Symbolic results by period are in the report. Outside bounds: {result['unresolved']}. Results saved to {path}")
        def work(progress,cancel):
            report = bounded_basins(net,budget,progress=progress,cancel=cancel)
            if not report["exhaustive"] and net.rules is not None:
                from .symbolic_cycles import symbolic_cycles
                progress(0.95,"Searching for additional cycles by Boolean constraints")
                report["symbolic_periods"] = symbolic_cycles(net,cancel=cancel)
                report["symbolic_basin_definition"] = "For each listed cycle C, its bounded basin is exactly the starting states x with F^6(x) in C. Sample histogram counts are separate."
            return report
        self.start_job(work,complete)

    def open_network(self):
        p=self.file('Open Network','Boolean or Python network (*.bnet *.json);;Weighted network (*.csv *.txt)')
        if p: self.set_network(io.load_network(p))
    def save_network(self):
        if not self.networks: raise ValueError('Load or create a network first')
        p,_=W.QFileDialog.getSaveFileName(self,'Save Network','network.json','Python network (*.json);;Weighted network (*.csv)')
        if p:
            if Path(p).suffix.lower()=='.csv': io.save_weighted(self.networks[0],p)
            else: io.save_network(self.networks[0],p)
    def save_dot(self):
        if not self.networks: raise ValueError('Load a network first')
        p,_=W.QFileDialog.getSaveFileName(self,'Save Regulatory DOT','network.dot','Graphviz (*.dot)')
        if p: Path(p).write_text(network_dot(self.networks[0]),encoding='utf-8')

    def load_mapping(self):
        p=self.file('Load Saved Landscape Coordinates','Mapping data (*.mat *.npz)')
        if p: self.saved_mapping=io.load_mapping(p); self.plot_cache={}

    def configure_inputs(self):
        import json
        from dataclasses import replace

        if not self.networks:
            raise ValueError('Load a network first')
        network = self.networks[0]
        initial = {'external_inputs': network.metadata.get('external_inputs', []),
                   'fixed': network.clamped}
        text, accepted = W.QInputDialog.getMultiLineText(
            self, 'Configure Nodes',
            'External inputs retain their starting values. Fixed nodes use the specified 0 or 1.',
            json.dumps(initial, indent=2))
        if accepted:
            config = json.loads(text)
            self.set_network(replace(network, clamped=config['fixed'],
                                     metadata={**network.metadata, 'external_inputs': config['external_inputs']}))

    def edit_network(self):
        from .expressions import ExpressionRule
        if self.networks and any(isinstance(r,ExpressionRule) for r in (self.networks[0].rules or [])):
            import json
            net=self.networks[0]
            text,ok=W.QInputDialog.getMultiLineText(self,'Edit expressions','Node-to-rule JSON',json.dumps({n:r.expression for n,r in zip(net.names,net.rules)},indent=2))
            if ok:
                from .expressions import from_expressions
                self.set_network(from_expressions(json.loads(text),net.name))
            return
        if not self.networks:
            text,ok=W.QInputDialog.getText(self,'Create Network','Node names, separated by commas:')
            if not ok:return
            names=[n.strip() for n in text.split(',')]
            net=Network(names,np.zeros((len(names),len(names))))
        else: net=self.networks[0].copy()
        d=W.QDialog(self); d.setWindowTitle('ATLANTIS - Edit Network'); layout=W.QVBoxLayout(d)
        table=W.QTableWidget(d); layout.addWidget(table)
        if net.weights is not None:
            table.setRowCount(net.n+1); table.setColumnCount(net.n); table.setHorizontalHeaderLabels(net.names); table.setVerticalHeaderLabels(net.names+['basal'])
            for i,row in enumerate(np.vstack((net.weights,net.basal))):
                for j,val in enumerate(row): table.setItem(i,j,W.QTableWidgetItem(f'{val:g}'))
            def apply():
                a=np.array([[float(table.item(i,j).text()) for j in range(net.n)] for i in range(net.n+1)])
                self.set_network(Network(net.names,a[:-1],a[-1],name=net.name)); d.accept()
        else:
            table.setRowCount(net.n); table.setColumnCount(3); table.setHorizontalHeaderLabels(['Target','Sources (comma separated)','Outputs in binary row order'])
            for i,(name,r) in enumerate(zip(net.names,net.rules)):
                vals=[name,', '.join(net.names[s] for s in r.sources) if r else '', ' '.join(map(str,r.outputs)) if r else '']
                for j,val in enumerate(vals): table.setItem(i,j,W.QTableWidgetItem(val))
            def apply():
                rules=[]
                for i in range(net.n):
                    sources=[net.index(s) for s in table.item(i,1).text().split(',') if s.strip()]
                    outputs=[int(s) for s in table.item(i,2).text().split()]
                    rules.append(TruthRule(sources,np.array(outputs)) if outputs else None)
                self.set_network(Network(net.names,rules=rules,name=net.name,positions=net.positions,clamped=net.clamped,metadata=net.metadata)); d.accept()
        buttons=W.QDialogButtonBox(W.QDialogButtonBox.Save|W.QDialogButtonBox.Cancel); layout.addWidget(buttons)
        buttons.accepted.connect(lambda:self.safe(apply)); buttons.rejected.connect(d.reject); d.resize(850,500); d.exec()

    def modify_network(self):
        if not self.networks: raise ValueError('Load a network first')
        d=self.dialog('ModifyNetwork'); d.paths=[]
        def browse():
            paths=self.file('Select Mutation Files','Mutations (*.txt *.csv)',True)
            if paths: d.paths=paths; d.set_text('BrowseFile',', '.join(Path(p).name for p in paths))
        def apply():
            if not d.paths: raise ValueError('Select mutation files')
            networks=[]
            for p in d.paths:
                n=self.original_network.mutate(io.load_mutations(p)); n.name=Path(p).stem; networks.append(n)
            self.networks=networks; self.results={}; self.plot_cache={}; self.update_enabled(); d.accept()
        d.bind('BrowseMutations',browse); d.bind('Ok',apply)

    def generate_states(self,parent):
        d=self.dialog('GenerateStates')
        d.controls['PruneStateSpace'].setVisible(parent.guide_name=='ProbabilisticAnalysisMenu')
        def done():
            n=self.networks[0].n
            if d.checked('RandomSample'): states=random_states(n,int(d.text('EditSampleSize')))
            else: states=all_states(n)
            self.states=states; self.prune=d.checked('PruneStateSpace')
            parent.console(f'{len(states):,} initial states ready.'); d.accept()
        d.bind('Ok',done)

    def analysis_menu(self,probabilistic):
        if not self.networks: raise ValueError('Load a network first')
        if probabilistic and self.networks[0].weights is None: raise ValueError('Original ATLANTIS does not support probabilistic analysis for rules-based networks')
        d=self.dialog('ProbabilisticAnalysisMenu' if probabilistic else 'DeterministicAnalysisMenu'); d.bounds=None
        d.bind('GenerateStates',lambda:self.generate_states(d))
        def custom():
            p=self.file('Load Initial Network States','States (*.csv *.txt *.mat *.npz)')
            if p: self.states=io.load_states(p,self.networks[0].n); self.prune=False; d.console(f'{len(self.states):,} custom initial states loaded.')
        def fixed():
            p=self.file('Select Fixed Initial Node States','Fixed states (*.csv *.txt)')
            if p:
                if self.states is None: raise ValueError('Generate or load initial states first')
                self.states=fix_initial_nodes(self.networks[0],self.states,io.load_fixed_nodes(p)); d.set_text('BrowseFile1',Path(p).name)
        def fate():
            p=self.file('Select Cell Fate Determination Logic','Fate logic (*.csv *.txt)')
            if p: self.fate_logic=load_fate_logic(p,self.networks[0]); d.set_text('BrowseFile2',Path(p).name)
        def bounds():
            p=self.file('Select Trajectory Bounds','Trajectory bounds (*.csv *.txt *.mat)')
            if p: d.bounds=io.load_states(p,self.networks[0].n); d.set_text('BrowseFile3',Path(p).name)
        d.bind('CustomStates',custom); d.bind('BrowseFixNodeStates',fixed); d.bind('BrowseCellFateLogic',fate)
        if probabilistic: d.bind('BrowseTrajectoryBounds',bounds)
        d.bind('Ok',lambda:self.run_analysis(d,probabilistic))

    def run_analysis(self,d,probabilistic):
        if self.states is None: raise ValueError('Generate or load network states first')
        states=self.states.copy(); logic=self.fate_logic; networks=[n.copy() for n in self.networks]
        if probabilistic:
            settings={'noise':float(d.text('EditNoise')),'degradation':float(d.text('EditDegradationConstant')),'max_steps':int(d.text('EditSimulationTime')),'error':float(d.text('EditErrorMargin')),'prune':self.prune}
            if d.checked('MapTrajectory') and d.bounds is None: raise ValueError('Load trajectory bounds first')
            bounds=d.bounds if d.checked('MapTrajectory') else None
        else: settings={'search_duration':int(d.text('EditSearchDuration'))}; bounds=None
        from .classical_jobs import ClassicalJobs, make_request
        kind = 'probabilistic' if probabilistic else 'deterministic'
        request = make_request(networks, states, logic, kind, settings, bounds)
        jobs = ClassicalJobs()

        def work(progress, cancel):
            return jobs.run(request, progress, cancel)

        def complete(output):
            for name,kind,result in output: self.results.setdefault(name,{})[kind]=result
            self.plot_cache={}; self.update_enabled()
            summaries=[]
            for name,kind,result in output:
                if kind=='deterministic': summaries.append(f'{name}: {len(result.attractors)} attractors; {result.unresolved} unresolved initial states.')
                else:
                    status = 'historical 98% criterion met' if result.converged else 'time-step limit reached'
                    summaries.append(f'{name}: {result.iterations} iterations, {status}. '
                                     f'Maximum one-step probability change: {result.flux_residual_inf:.3g}.')
            d.console('\n'.join(summaries)); self.result_table(output)
        self.start_job(work,complete,d)

    def recover_classical_job(self):
        import json
        from .classical_jobs import ClassicalJobs

        jobs = ClassicalJobs()
        requests = {f"{status} | {identity} | {json.loads(payload)['kind']}": (identity, payload)
                    for identity, payload, status in jobs.recoverable()}
        if not requests:
            W.QMessageBox.information(self, 'ATLANTIS', 'No classical jobs to rerun.')
            return
        label, accepted = W.QInputDialog.getItem(
            self, 'Recover Classical Job', 'Rerun saved inputs from the beginning',
            list(requests), editable=False)
        if not accepted:
            return
        identity, payload = requests[label]
        request = json.loads(payload)

        def complete(output):
            networks = [io.network_from_dict(net) for net in request['networks']]
            self.set_network(networks[0])
            self.networks = networks
            self.states = np.asarray(request['states'], dtype=np.uint8)
            for name, kind, result in output:
                self.results.setdefault(name, {})[kind] = result
            self.update_enabled()
            self.result_table(output)

        self.start_job(lambda progress, cancel: jobs.run(request, progress, cancel, source=identity), complete)

    def start_job(self,work,complete,parent=None,*,on_error=None):
        if self.job and self.job.isRunning(): raise ValueError('An analysis is already running')
        progress=W.QProgressDialog('Starting...','Cancel',0,1000,parent or self); progress.setWindowTitle('ATLANTIS'); progress.setWindowModality(QtCore.Qt.WindowModal); progress.setAutoClose(False); progress.setAutoReset(False)
        self.job=Job(work,self); progress.canceled.connect(self.job.cancel.set)
        self.job.progress.connect(lambda f,m:(progress.setValue(round(f*1000)),progress.setLabelText(m)))
        self.job.success.connect(lambda result:(progress.close(),self.safe(lambda:complete(result))))
        def show_failure(message, heading):
            progress.close()
            if on_error:
                on_error(message, heading)
            else:
                show_warning(parent or self,'ATLANTIS',message)
        self.job.failure.connect(show_failure)
        self.job.finished.connect(self.update_enabled); self.job.start(); progress.show(); self.progress_dialog=progress

    def result_table(self,output):
        for name,kind,result in output:
            d=W.QDialog(self); d.setWindowTitle('ATLANTIS - '+name+' - '+kind.title()+' Results'); layout=W.QVBoxLayout(d); table=W.QTableWidget(); layout.addWidget(table)
            if kind=='deterministic':
                coverage=result.coverage
                summary=(f"{coverage['taxonomy'].capitalize()} · "
                         f"{coverage['unique_initial_states']} unique starts · {result.unresolved} unresolved")
                rows=[[i+1,a.kind,a.basin,a.fate]+a.average.tolist() for i,a in enumerate(result.attractors)]
                headers=['Attractor','Type','Basin Size Ratio','Cell Fate']+self.networks[0].names
            else:
                scope='pruned state space' if result.pruned else 'supplied state space'
                summary=(f'Probabilistic flux estimate on {scope} · {len(result.states)} states · '
                         f'Maximum one-step change {result.flux_residual_inf:.3g}')
                order=np.argsort(result.probabilities)[::-1]
                rows=[[int(i)+1,float(result.probabilities[i]),result.fates[i] if result.fates else '']+result.states[i].tolist() for i in order]
                headers=['State Index','Probability','Cell Fate']+self.networks[0].names
            layout.insertWidget(0,W.QLabel(summary))
            table.setColumnCount(len(headers)); table.setHorizontalHeaderLabels(headers); table.setRowCount(len(rows))
            for i,row in enumerate(rows):
                for j,value in enumerate(row): table.setItem(i,j,W.QTableWidgetItem(f'{value:.12g}' if isinstance(value,float) else str(value)))
            table.setEditTriggers(W.QAbstractItemView.NoEditTriggers); table.resizeColumnsToContents()
            export=W.QPushButton('Export Results...'); export.clicked.connect(lambda:self.safe(self.export_results)); layout.addWidget(export); d.resize(950,450); d.show(); self.windows.append(d)

    def show_figure(self,fig,title):
        w=FigureWindow(fig,title,self); w.show(); self.windows.append(w); return w

    def sketch_network(self):
        d=self.dialog('NetworkSketchingOptions')
        def done():
            graphviz=d.checked('GraphViz'); d.accept()
            if graphviz: self.graphviz_menu()
            else:
                for net in self.networks:
                    fig=network_figure(net); net.positions=fig.atlantis_data['positions']
                    self.show_figure(fig,'ATLANTIS - '+net.name)
        d.bind('Ok',done)

    def graphviz_menu(self):
        d=self.dialog('GraphVizMenu'); d.dot_path=None
        def custom():
            if d.checked('CustomDotFile'):
                p=self.file('Select Graphviz DOT','DOT (*.dot *.gv)')
                if p: d.dot_path=p
        d.bind('CustomDotFile',custom)
        def draw():
            engine={'Circos':'circo','Dot':'dot','Default':'dot'}[d.text('SelectedPlotType')]
            for net in self.networks:
                dot=Path(d.dot_path).read_text(encoding='utf-8') if d.checked('CustomDotFile') and d.dot_path else network_dot(net)
                if d.checked('CustomDotFile') and not d.dot_path: raise ValueError('Select a DOT file')
                color={'White':'white','Black':'black','Grey':'gray'}[d.text('SelectedBGColor')]
                from .graphviz_window import graphviz_svg,GraphvizWindow
                first=dot.find('{')
                if first>=0:dot=dot[:first+1]+'\n graph [bgcolor="'+color+'"];\n'+dot[first+1:]
                svg=graphviz_svg(dot,engine)
                window=GraphvizWindow(svg,'ATLANTIS - '+d.text('PlotTitle'),self);window.show();self.windows.append(window)
        d.bind('Draw',draw)

    def visualize(self):
        if not self.results: raise ValueError('Perform an analysis first')
        d=self.dialog('VisualizeResultsMenu'); d.set_text('Reset','Reset')
        has_det=any('deterministic' in r for r in self.results.values()); has_prob=any('probabilistic' in r for r in self.results.values())
        has_fates=any(bool(r.get('deterministic') and r['deterministic'].fate_propensities) for r in self.results.values())
        for tag,available in [('CheckBasinValues',has_det),('CheckTreeMap',has_fates),('CheckPELandscape',has_prob),('CheckProbabilityLandscape',has_prob)]:
            d.controls[tag].setEnabled(available); d.controls[tag].setChecked(available and tag in ('CheckBasinValues','CheckTreeMap'))
        d.bind('SammonProjection',lambda:self.select_sammon_states(d))
        d.bind('Reset',lambda:self.plot_cache.clear()); d.bind('Plot',lambda:self.plot_from_dialog(d))

    def select_sammon_states(self,parent):
        if not parent.checked('SammonProjection'): return
        n=self.networks[0].n
        if n<7:
            parent.controls['NaiveProjection'].setChecked(True)
            raise ValueError('The original GUI requires at least 2^7 states for Sammon mapping. Use Naive Random for small networks.')
        count=len(self.states) if self.states is not None else 0
        if count in (128,256,512,1024,2048,4096): return
        d=self.dialog('StateSpaceSizeSelectionMenu')
        def done():
            size=128 if d.checked('OptimalSize') else 2**int(d.text('StateSpaceSelection').split('^')[1])
            self.modified_states=random_states(n,size)
            self.plot_cache={}; d.accept()
        d.bind('Ok',done)

    def plot_from_dialog(self,d):
        selected=[kind for tag,kind in [('CheckBasinValues','basin'),('CheckPELandscape','energy'),('CheckProbabilityLandscape','probability')] if d.checked(tag)]
        tree=d.checked('CheckTreeMap'); method='sammon' if d.checked('SammonProjection') else 'naive'
        if not selected and not tree: raise ValueError('Select a plot type')
        requests=[]
        for net in self.networks:
            results=self.results.get(net.name,{}); det=results.get('deterministic'); prob=results.get('probabilistic')
            states=self.modified_states.copy() if method=='sammon' and self.modified_states is not None else prob.states.copy() if prob else det.initial_states.copy() if det else None
            if states is None: continue
            if method=='naive' and det and len(states)<2**net.n:
                states=np.unique(np.vstack([states]+[a.states for a in det.attractors]),axis=0)
            if method=='sammon' and len(states)>4096:
                raise MemoryError('Sammon uses dense pairwise distances. Use the state-space selection dialog or explicitly load a smaller state space.')
            requests.append((net,states,det,prob))
        options={'mapping':method,'factor':int(d.text('SelectedNoiseReductionFactor')),'cmap':d.text('SelectedColorSchemeAttractorLandscape'),'annotate':d.checked('AnnotateAttractors'),'group':d.checked('GroupCyclicAttractors'),'title':d.text('EditAttractorLandscapeTitle'),'tooltips':d.checked('ShowToolTip')}
        tree_options=(d.text('SelectedColorSchemeTreeMap'),d.checked('AnnotateBoxes'),d.text('EditTreemapTitle'))
        def work(progress,cancel):
            output=[]
            for net,states,det,prob in requests:
                cache=self.plot_cache.get((net.name,method),{})
                coordinates=cache.get('coordinates') if method=='sammon' else None; permutation=cache.get('permutation')
                if self.saved_mapping:
                    saved_states=self.saved_mapping.get('states')
                    if saved_states is not None and not np.array_equal(states,saved_states): raise ValueError('Saved mapping states differ from this plot state space')
                    if method=='sammon': coordinates=self.saved_mapping.get('coordinates')
                    else: permutation=self.saved_mapping.get('permutation')
                for kind in selected:
                    fig=landscape_figure(states,kind,det,prob,coordinates=coordinates,permutation=permutation,progress=progress,cancel=cancel,**options)
                    data=fig.atlantis_data; coordinates=data['coordinates']; permutation=data['permutation']; output.append((net.name,kind,fig))
                if tree and det: output.append((net.name,'fate',cell_fate_figure(det.fate_propensities,*tree_options)))
            return output
        def complete(output):
            for name,kind,fig in output:
                if kind!='fate': self.plot_cache[(name,method)]=fig.atlantis_data
                self.show_figure(fig,'ATLANTIS - '+name+' - '+kind.title()+' Landscape')
            wants_export=d.checked('ExportTreeMap') or d.checked('ExportAttractorLandscape')
            if wants_export:
                folder=W.QFileDialog.getExistingDirectory(d,'Export Figures')
                if folder:
                    for name,kind,fig in output:
                        is_tree=kind=='fate'
                        if d.checked('ExportTreeMap' if is_tree else 'ExportAttractorLandscape'):
                            fmt=d.text('EditFormatTreeMap' if is_tree else 'EditFormatAttractorLandscape').lower(); dpi=float(d.text('EditResolutionTreemap' if is_tree else 'EditResolutionAttractorLandscape'))
                            safe=''.join(c if c.isalnum() or c in ' -_' else '_' for c in name)
                            fig.savefig(Path(folder)/(safe+' - '+kind+'.'+fmt),dpi=dpi)
        self.start_job(work,complete,d)

    def export_results(self):
        if not self.results: raise ValueError('No analysis results available')
        folder=W.QFileDialog.getExistingDirectory(self,'Export Analysis Results')
        if folder:
            for net in self.networks:
                r=self.results.get(net.name,{})
                name=''.join(c if c.isalnum() or c in ' -_' else '_' for c in net.name)
                io.export_results(Path(folder)/name,net,r.get('deterministic'),r.get('probabilistic'))
            W.QMessageBox.information(self,'ATLANTIS','Results exported to '+folder)

    def open_results(self):
        import json
        from .analysis import Attractor,DeterministicResult,ProbabilisticResult
        folder=W.QFileDialog.getExistingDirectory(self,'Select Exported Result Folder (containing network.json)')
        if not folder:return
        p=Path(folder); net=io.load_network(p/'network.json'); self.set_network(net); results={}
        if (p/'deterministic.json').exists():
            meta=json.loads((p/'deterministic.json').read_text()); states=io.load_states(p/'Network State List DA.mat',net.n)
            attrs=[Attractor(np.array(a['states'],dtype=np.uint8),a['basin'],a['fate']) for a in meta['attractors']]
            fates={}
            for a in attrs:fates[a.fate]=fates.get(a.fate,0)+a.basin
            results['deterministic']=DeterministicResult(states,attrs,np.full(len(states),-1),meta['unresolved'],meta['search_duration'],fates)
            self.states=states
        if (p/'Probabilistic Results.mat').exists():
            data=io.load_mat(p/'Probabilistic Results.mat'); m=json.loads((p/'probabilistic.json').read_text())
            states = np.asarray(data['states'], dtype=np.uint8).reshape(-1, net.n)
            results['probabilistic']=ProbabilisticResult(states,np.atleast_2d(data['StateTransitionProbabilities']),np.atleast_1d(data['SteadyStateProbabilities']),m['iterations'],m['converged'],m['noise'],m['degradation'],m['error'],m['pruned'])
        self.results={net.name:results}; self.update_enabled()

    def closeEvent(self,event):
        if self.job and self.job.isRunning():
            self.job.cancel.set(); event.ignore(); return
        for window in self.windows:
            try: window.close()
            except RuntimeError:pass
        event.accept()


def main():
    import sys
    app=W.QApplication.instance() or W.QApplication(sys.argv)
    app.setStyle('Fusion'); app.setFont(QtGui.QFont('Arial',9))
    w=Application(); w.show(); return app.exec()
