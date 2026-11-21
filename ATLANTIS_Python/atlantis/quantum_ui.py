"""Quantum configuration and comparison within the existing ATLANTIS desktop."""
import json
from pathlib import Path
from PySide6 import QtWidgets as W
from .quantum.engine import Settings,preflight
from .experiments import execute,JobStore


class QuantumDialog(W.QDialog):
    def __init__(self,app):
        super().__init__(app); self.app=app; self.result=None
        from .quantum.ibm import IBMAccount
        self.account=IBMAccount();self.backend_name=''
        self.finished.connect(lambda _:self.account.disconnect())
        self.setWindowTitle('ATLANTIS | Quantum analysis & experiments'); self.resize(900,700)
        self.setStyleSheet('QDialog { background-color: white; } QLabel { color: #202020; background-color: white; }')
        layout=W.QVBoxLayout(self)
        label=W.QLabel('Use the loaded ATLANTIS network. Reference = classical amplitude model; Aer = actual circuits.\nT is user supplied. Finite QPE completion is heuristic. Exact M uses classical enumeration.')
        label.setWordWrap(True); layout.addWidget(label)
        form=W.QFormLayout(); layout.addLayout(form)
        self.network=W.QComboBox(); self.network.addItems([n.name for n in app.networks]); form.addRow('Network variant',self.network)
        self.engine=W.QComboBox(); self.engine.addItems(['reduced','aer','aer_mps','ibm']); form.addRow('Execution mode',self.engine)
        self.counting=W.QComboBox(); self.counting.addItems(['exact','qpe_ideal','qpe_aer']); form.addRow('Counting',self.counting)
        self.stop=W.QComboBox(); self.stop.addItems(['classical_audit','qpe','bounded']); form.addRow('Stopping policy',self.stop)
        self.fields={}
        field_labels = ['Evolution steps (T)', 'Search shots', 'Counting precision (bits)', 'Counting shots',
                        'Random seed', 'Maximum rounds', 'Maximum qubits', 'Memory limit (MiB)', 'Timeout (seconds)']
        for label_text, (name,value,lo,hi) in zip(field_labels, [('T',3,1,10000),('shots',256,1,100000),('counting_precision',3,1,10),
            ('counting_shots',128,1,100000),('seed',42,0,2147483647),('max_rounds',12,1,1000),
            ('max_qubits',22,1,1000),('max_memory_mib',1024,1,1048576),('timeout_seconds',120,1,3600)]):
            box=W.QSpinBox();box.setRange(lo,hi);box.setValue(value);self.fields[name]=box;form.addRow(label_text,box)
        self.noise=W.QDoubleSpinBox();self.noise.setRange(0,.2);self.noise.setDecimals(4);self.noise.setSingleStep(.001)
        form.addRow('Depolarizing gate noise probability',self.noise)
        row=W.QHBoxLayout();layout.addLayout(row)
        for title,callback in [('Preflight',self.check),('Run',self.launch),('Compare classical',self.compare),
                               ('Export JSON',self.export),('Plot measurements',self.plot),('Job history',self.history),('IBM account',self.ibm)]:
            b=W.QPushButton(title);row.addWidget(b);b.clicked.connect(lambda _,f=callback:self.safe(f))
        self.scientific_status=W.QLabel('Status: Ready.')
        self.scientific_status.setWordWrap(True)
        layout.addWidget(self.scientific_status)
        layout.addWidget(W.QLabel('Analysis output and error details'))
        self.output=W.QPlainTextEdit();self.output.setReadOnly(True);layout.addWidget(self.output)

    def safe(self, callback):
        try:
            callback()
        except Exception as error:
            self.show_error(str(error), callback.__name__.capitalize() + ' failed', 'ATL-Q-' + callback.__name__.upper())

    def show_error(self, message, heading='Analysis failed', code='ATL-Q-RUN'):
        self.scientific_status.setText(f"[{code}] {heading.rstrip('.')}. See the details below.")
        self.output.appendPlainText(f"\n[{code}] {heading.rstrip('.')}\n{message}")

    def settings(self):
        return Settings(engine=self.engine.currentText(),counting_mode=self.counting.currentText(),
            stop_policy=self.stop.currentText(),noise_probability=self.noise.value(),**{k:v.value() for k,v in self.fields.items()})

    def selected(self):
        if self.network.currentIndex() < 0:
            raise ValueError('Load a network in Generate Network first.')
        return self.app.networks[self.network.currentIndex()].copy()

    def check(self):
        assessment=preflight(self.selected(),self.settings())
        self.scientific_status.setText(
            'Preflight passed. Execution has not started.' if assessment['eligible']
            else '[ATL-Q-PREFLIGHT] Preflight rejected these settings. No circuit was executed. ' + ' '.join(assessment['reasons']))
        self.output.setPlainText(json.dumps(assessment,indent=2));return assessment

    def launch(self):
        if not self.check()['eligible']:return
        net=self.selected();settings=self.settings()
        if settings.engine=='ibm':
            from .quantum.hardware import run_hardware
            from .quantum.adapter import QuantumNetwork
            from .quantum.ross.circuits import search_circuit
            if not self.backend_name:raise ValueError('Connect your IBM account and select a QPU first')
            if settings.counting_mode!='qpe_aer':raise ValueError('Select qpe_aer for actual QPE circuits on IBM')
            circuit,_=search_circuit(QuantumNetwork(net),settings.T,[],0)
            prepared=self.account.prepare(circuit,self.backend_name,settings.shots)
            summary=json.dumps(prepared[2],indent=2)
            answer=W.QMessageBox.question(self,'Confirm potentially paid QPU analysis',
                summary+'\nSubmit up to 24 search/count circuits, each capped at 60 seconds QPU execution?\nLater counting/suppression circuits may cost more. Provider pricing applies. No automatic retries.',
                W.QMessageBox.Yes|W.QMessageBox.No,W.QMessageBox.No)
            if answer!=W.QMessageBox.Yes:return
            self.app.start_job(lambda progress,cancel:run_hardware(net,settings,self.account,self.backend_name,
                confirmed=True,progress=progress,cancel=cancel),self.complete,self,on_error=self.show_error)
            return
        self.app.start_job(lambda progress,cancel:execute(net,settings,progress,cancel),
                           self.complete,self,on_error=self.show_error)

    def complete(self,result):
        self.result=result
        status=result.get('status','')
        completeness={
            'complete_classically_certified':'Classical coverage audit certified completeness at the configured horizon.',
            'complete_qpe_heuristic':'Ideal-model QPE evidence supports completeness. No completeness certificate.',
            'inconclusive_coverage_evidence':'Inconclusive discovery. The full-count estimate lacks sufficient coverage evidence.',
        }.get(status,'Inconclusive discovery. Additional attractors may exist.')
        self.scientific_status.setText(
            f"{result.get('taxonomy','Quantum analysis')}. "
            f"{len(result.get('cycles',[]))} reported attractors passed individual classical verification. "
            + completeness)
        self.output.setPlainText(json.dumps(result,indent=2))

    def compare(self):
        if not self.result:raise ValueError('Run or reopen a quantum result first')
        from .io import network_from_dict
        from .states import all_states
        from .analysis import deterministic_analysis
        net=network_from_dict(self.result['network'])
        if net.n>16: raise ValueError('Exact comparison limited to 65536 states')
        result=deterministic_analysis(net,all_states(net.n),10000)
        rows=[{'cycle':[''.join(map(str,row)) for row in a.states],'basin':a.basin} for a in result.attractors]
        self.output.setPlainText(json.dumps({'network_hash':self.result['network_hash'],
            'classical':rows,'classical_unresolved':result.unresolved,'quantum':self.result['cycles'],
            'quantum_status':self.result['status'],'quantum_basin_sizes':None},indent=2))

    def export(self):
        if not self.result: raise ValueError('No quantum result to export')
        path,_=W.QFileDialog.getSaveFileName(self,'Export experiment','quantum-result.json','JSON (*.json)')
        if path:Path(path).write_text(json.dumps(self.result,indent=2),encoding='utf8')

    def plot(self):
        if not self.result:raise ValueError('No result')
        from matplotlib.figure import Figure
        records=[h for h in self.result['history'] if h['kind']=='measurements']
        if not records:raise ValueError('No measurements')
        fig=Figure(figsize=(10,5));ax=fig.subplots()
        # Initial distribution only; suppressed rounds are different distributions.
        counts=records[0]['counts'];total=sum(counts.values())
        ax.bar(list(counts),[v/total for v in counts.values()]);ax.tick_params(axis='x',rotation=60)
        ax.set_xlabel('Measured state');ax.set_ylabel('Observed frequency');ax.set_title(self.result['taxonomy']+' — first search round')
        fig.tight_layout();self.app.show_figure(fig,'Quantum measurements')

    def history(self):
        store=JobStore();rows=store.list()
        d=W.QDialog(self);d.setWindowTitle('Persistent quantum jobs');box=W.QVBoxLayout(d)
        listing=W.QListWidget();box.addWidget(W.QLabel('Saved jobs (creation time | status | ID)'));box.addWidget(listing)
        for row in rows:listing.addItem(row['created']+' | '+row['status']+' | '+row['id'])
        def open_selected():
            i=listing.currentRow()
            if i>=0 and rows[i]['result']:self.complete(json.loads(rows[i]['result']));d.accept()
        b=W.QPushButton('Open selected result');b.clicked.connect(lambda:self.safe(open_selected));box.addWidget(b)
        b=W.QPushButton('Mark interrupted jobs after restart')
        def recover():
            if self.app.job and self.app.job.isRunning():raise ValueError('An active job is still running')
            store.recover();d.accept()
        b.clicked.connect(lambda:self.safe(recover));box.addWidget(b);d.resize(800,400);d.exec()

    def ibm(self):
        from .quantum.ibm import IBMAccount
        d=W.QDialog(self);d.setWindowTitle('IBM Quantum — ephemeral account');layout=W.QFormLayout(d)
        account=self.account;token=W.QLineEdit();token.setEchoMode(W.QLineEdit.Password)
        instance=W.QLineEdit();backends=W.QComboBox();status=W.QPlainTextEdit();status.setReadOnly(True)
        def show_account_status(callback):
            try:
                callback()
            except Exception as error:
                status.appendPlainText(f'\n[ATL-Q-IBM] The IBM account or job request failed.\n{error}')
        layout.addRow('API key (memory only)',token);layout.addRow('Instance CRN',instance);layout.addRow('QPU',backends)
        def connect():
            secret=token.text();token.clear()
            account.connect(secret,instance.text());secret=None
            backends.clear();backends.addItems([b['name'] for b in account.backends()])
            self.backend_name=backends.currentText()
            status.setPlainText('Connected. Credentials are not saved. Live hardware validation is pending.')
        b=W.QPushButton('Connect / discover QPUs');b.clicked.connect(lambda:show_account_status(connect));layout.addRow(b)
        b=W.QPushButton('Disconnect');b.clicked.connect(lambda:(account.disconnect(),token.clear(),backends.clear(),status.setPlainText('Disconnected')));layout.addRow(b)
        backends.currentTextChanged.connect(lambda name:setattr(self,'backend_name',name))
        layout.addRow('Account and job status',status)
        job_id=W.QLineEdit();job_id.setPlaceholderText('Paste an existing IBM job ID')
        layout.addRow('Existing provider job ID',job_id)
        def provider_status():status.setPlainText(account.status(job_id.text()))
        b=W.QPushButton('Retrieve provider status');b.clicked.connect(lambda:show_account_status(provider_status));layout.addRow(b)
        def provider_result():status.setPlainText(json.dumps(account.result(job_id.text()),indent=2))
        b=W.QPushButton('Retrieve completed measurements');b.clicked.connect(lambda:show_account_status(provider_result));layout.addRow(b)
        b=W.QPushButton('Cancel provider job');b.clicked.connect(lambda:show_account_status(lambda:account.cancel(job_id.text())));layout.addRow(b)
        layout.addRow(W.QLabel('Close this dialog to configure IBM execution and actual QPE counting.\nCredentials remain only in memory until Disconnect or the analysis dialog closes.'))
        d.resize(650,500);d.exec()
