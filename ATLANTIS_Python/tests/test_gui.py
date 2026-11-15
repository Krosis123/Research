import os,time
os.environ['QT_QPA_PLATFORM']='offscreen'
import numpy as np
import pytest
from pathlib import Path
from PySide6 import QtGui, QtWidgets as W
from atlantis.gui import Application
from atlantis.guide import GuideWindow
from atlantis.figure_window import FigureWindow
from atlantis.analysis import deterministic_analysis,probabilistic_analysis
from atlantis.plots import landscape_figure
from conftest import ROOT,EXAMPLES


@pytest.mark.parametrize('name',[p.stem for p in (ROOT/'atlantis/assets/guide').glob('*.json')])
def test_all_guide_windows_render(qtapp,name,tmp_path):
    d=GuideWindow(name);d.show();qtapp.processEvents()
    assert d.width()>100 and d.height()>50
    assert d.grab().save(str(tmp_path/(name+'.png')))
    assert d.controls
    d.close()


def test_gui_network_import_workflow(qtapp,monkeypatch):
    w=Application();w.generate_network();d=w.dialogs[-1]
    d.controls['Ok'].click();d=w.dialogs[-1]
    monkeypatch.setattr(w,'file',lambda *a,**k:str(EXAMPLES/'Case Study 1/Input Files/NetworkFile.csv'))
    d.controls['BrowseNetworkFile'].click();d.controls['Ok'].click()
    assert w.networks[0].n==11 and w.controls['DeterministicAnalysis'].isEnabled()
    w.close()


def test_quantum_warning_explains_missing_network(qtapp, monkeypatch):
    shown = []

    def inspect_warning(dialog):
        dialog.ensurePolished()
        label = dialog.findChild(W.QLabel, 'qt_msgbox_label')
        label.ensurePolished()
        assert label.palette().color(QtGui.QPalette.ColorRole.WindowText).name() == '#202020'
        shown.append(label.text())
        return W.QMessageBox.StandardButton.Ok

    monkeypatch.setattr(W.QMessageBox, 'exec', inspect_warning)
    window = Application()
    window.quantum_button.click()
    assert len(shown) == 1
    assert 'No network is loaded.' in shown[0]
    assert 'Use Generate Network' in shown[0]
    window.close()


def test_gui_analysis_worker_and_result_table(qtapp,yeast,yeast_states,monkeypatch):
    w=Application();w.set_network(yeast);w.states=yeast_states;w.analysis_menu(False);d=w.dialogs[-1]
    failures=[];monkeypatch.setattr('atlantis.gui.show_warning',lambda *a:failures.append(a[-1]))
    w.run_analysis(d,False)
    deadline=time.monotonic()+20
    while w.job.isRunning() and time.monotonic()<deadline:qtapp.processEvents();time.sleep(.01)
    qtapp.processEvents()
    assert not w.job.isRunning() and not failures
    assert len(w.results[yeast.name]['deterministic'].attractors)==7
    assert w.controls['VisualizeResults'].isEnabled()
    w.close()


def test_gui_plot_worker(qtapp,yeast,yeast_states,monkeypatch):
    w=Application();w.set_network(yeast);w.states=yeast_states
    w.results={yeast.name:{'deterministic':deterministic_analysis(yeast,yeast_states,200)}}
    w.visualize();d=w.dialogs[-1];failures=[]
    monkeypatch.setattr('atlantis.guide.show_warning',lambda *a:failures.append(a[-1]))
    w.plot_from_dialog(d)
    deadline=time.monotonic()+30
    while w.job.isRunning() and time.monotonic()<deadline:qtapp.processEvents();time.sleep(.01)
    qtapp.processEvents()
    assert not w.job.isRunning() and not failures
    assert any(isinstance(x,FigureWindow) for x in w.windows)
    w.close()


def test_figure_controls(qtapp,yeast,yeast_states):
    d=deterministic_analysis(yeast,yeast_states,200);f=landscape_figure(yeast_states,'basin',d,seed=83)
    w=FigureWindow(f);w.show();qtapp.processEvents()
    w.toggle_annotations();assert all(not a.get_visible() for a in f.atlantis_data['annotations'])
    w.toggle_surface();assert not f.atlantis_data['surface'].get_visible()
    w.toggle_contour();w.invert();assert f.axes[0].zaxis_inverted()
    w.alpha(.3);assert f.atlantis_data['surface'].get_alpha()==.3
    w.recolor('winter');w.close()


def test_result_reopening(qtapp,yeast,yeast_states,tmp_path,monkeypatch):
    from atlantis.io import export_results
    d=deterministic_analysis(yeast,yeast_states,200)
    export_results(tmp_path,yeast,d)
    w=Application();monkeypatch.setattr(W.QFileDialog,'getExistingDirectory',lambda *a,**k:str(tmp_path))
    w.open_results();assert len(w.results[yeast.name]['deterministic'].attractors)==7;w.close()


def test_native_graphviz_svg_viewer(qtapp,yeast,tmp_path):
    from atlantis.graphviz_window import graphviz_svg,GraphvizWindow
    from atlantis.plots import network_dot
    svg=graphviz_svg(network_dot(yeast))
    assert b'<svg' in svg and b'Cln3' in svg
    w=GraphvizWindow(svg);w.show();qtapp.processEvents();w.fit()
    assert w.renderer.isValid() and w.grab().save(str(tmp_path/'graphviz.png'))
    w.close()


@pytest.mark.parametrize('extension',['png','jpg','tiff','pdf'])
def test_svg_figure_exports(qtapp,yeast,tmp_path,monkeypatch,extension):
    from atlantis.graphviz_window import graphviz_svg,GraphvizWindow
    from atlantis.plots import network_dot
    w=GraphvizWindow(graphviz_svg(network_dot(yeast)));path=tmp_path/('network.'+extension)
    monkeypatch.setattr(W.QFileDialog,'getSaveFileName',lambda *a,**k:(str(path),''))
    monkeypatch.setattr(W.QInputDialog,'getInt',lambda *a,**k:(100,True))
    w.export();assert path.exists() and path.stat().st_size>1000;w.close()

def test_gui_three_analyses_export_and_reopen(qtapp, monkeypatch, tmp_path):
    from atlantis.io import save_network
    from atlantis.model import Network
    from atlantis.experiments import JobStore, execute
    import atlantis.quantum_ui as quantum_ui

    network = Network(['Signal'], weights=[[1]], name='Workflow')
    path = tmp_path / 'network.json'
    save_network(network, path)
    store = JobStore(tmp_path / 'quantum.sqlite')
    monkeypatch.setattr(quantum_ui, 'execute',
                        lambda net, settings, progress, cancel: execute(net, settings, progress, cancel, store))
    failures = []
    monkeypatch.setattr('atlantis.gui.show_warning', lambda *args: failures.append(args[-1]))
    monkeypatch.setattr(W.QMessageBox, 'information', lambda *args: None)

    def wait(window):
        deadline = time.monotonic() + 40
        while window.job.isRunning() and time.monotonic() < deadline:
            qtapp.processEvents()
            time.sleep(.01)
        qtapp.processEvents()
        assert not window.job.isRunning() and not failures

    window = Application()
    window.show()
    monkeypatch.setattr(window, 'file', lambda *args: str(path))
    window.open_network()
    window.states = np.array([[0], [1]], dtype=np.uint8)
    for probabilistic in (False, True):
        window.analysis_menu(probabilistic)
        window.run_analysis(window.dialogs[-1], probabilistic)
        wait(window)
    labels = [label.text() for dialog in window.windows for label in dialog.findChildren(W.QLabel)]
    assert any('Exact classical result' in label for label in labels)
    assert any('Probabilistic flux estimate' in label for label in labels)
    window.quantum_analysis()
    quantum = window.dialogs[-1]
    quantum.engine.setCurrentText('aer')
    quantum.launch()
    wait(window)
    assert len(quantum.result['cycles']) == 2
    assert 'Classical coverage audit certified completeness' in quantum.scientific_status.text()
    original = quantum.result
    quantum.complete({**original, 'status':'complete_qpe_heuristic'})
    assert 'No completeness certificate' in quantum.scientific_status.text()
    quantum.complete({**original, 'status':'inconclusive_counting'})
    assert 'Additional attractors may exist' in quantum.scientific_status.text()
    quantum.fields['max_qubits'].setValue(1)
    assert not quantum.check()['eligible']
    assert 'No circuit was executed' in quantum.scientific_status.text()
    quantum.complete(original)
    quantum.plot()
    assert window.windows
    monkeypatch.setattr(W.QFileDialog, 'getExistingDirectory', lambda *args: str(tmp_path))
    window.export_results()
    window.close()

    reopened = Application()
    reopened.show()
    monkeypatch.setattr(W.QFileDialog, 'getExistingDirectory',
                        lambda *args: str(tmp_path / network.name))
    reopened.open_results()
    assert set(reopened.results[network.name]) == {'deterministic', 'probabilistic'}
    assert len(reopened.results[network.name]['deterministic'].attractors) == 2
    assert JobStore(store.path).list()[0]['status'] == 'finished'
    reopened.close()

def test_ibm_dialog_mock_controls(qtapp, monkeypatch):
    from types import SimpleNamespace
    from atlantis.expressions import from_expressions

    window=Application()
    window.set_network(from_expressions({'signal':'signal'}))
    window.quantum_analysis()
    analysis=window.dialogs[-1]
    events=[]
    def result(job):
        if job == 'missing-job':
            raise RuntimeError('Could not retrieve IBM measurements')
        return {'1010': 128}
    analysis.account=SimpleNamespace(
        connect=lambda token,instance: events.append(('connect',token,instance)),
        backends=lambda:[{'name':'offline-test-backend','qubits':16}],
        status=lambda job:'DONE',
        result=result,
        cancel=lambda job:events.append(('cancel',job)),
        disconnect=lambda:events.append(('disconnect',)))
    def exercise(dialog):
        edits=dialog.findChildren(W.QLineEdit)
        buttons={b.text():b for b in dialog.findChildren(W.QPushButton)}
        token=next(field for field in edits if field.echoMode()==W.QLineEdit.Password)
        normal=[field for field in edits if field is not token]
        token.setText('synthetic-token')
        normal[0].setText('test-instance')
        buttons['Connect / discover QPUs'].click()
        assert token.text()=='' and analysis.backend_name=='offline-test-backend'
        normal[1].setText('offline-job')
        status=dialog.findChild(W.QPlainTextEdit)
        buttons['Retrieve provider status'].click()
        assert status.toPlainText()=='DONE'
        buttons['Retrieve completed measurements'].click()
        assert '1010' in status.toPlainText()
        normal[1].setText('missing-job')
        buttons['Retrieve completed measurements'].click()
        assert 'Could not retrieve IBM measurements' in status.toPlainText()
        normal[1].setText('offline-job')
        buttons['Cancel provider job'].click()
        buttons['Disconnect'].click()
        assert analysis.backend_name==''
        return 0
    monkeypatch.setattr(W.QDialog,'exec',exercise)
    analysis.ibm()
    assert events==[('connect','synthetic-token','test-instance'),('cancel','offline-job'),('disconnect',)]
    window.close()


@pytest.mark.parametrize('wait_expired', [False, True])
def test_quantum_worker_failure_is_written_to_output(qtapp, wait_expired):
    from atlantis.expressions import from_expressions
    from atlantis.quantum.hardware import ProviderWaitExpired

    window = Application()
    window.set_network(from_expressions({'signal': 'signal'}))
    window.quantum_analysis()
    analysis = window.dialogs[-1]

    def fail(progress, cancel):
        if wait_expired:
            raise ProviderWaitExpired('ATLANTIS stopped waiting for IBM job test-id.')
        raise RuntimeError('Example worker failure')

    window.start_job(fail, analysis.complete, analysis, on_error=analysis.show_error)
    assert window.job.wait(5000)
    qtapp.processEvents()
    output = analysis.output.toPlainText()
    if wait_expired:
        assert 'IBM wait ended\nATLANTIS stopped waiting for IBM job test-id.' in output
        assert 'Traceback' not in output
    else:
        assert 'Example worker failure' in output
    window.close()
