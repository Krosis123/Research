import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from atlantis.gui import Application
from atlantis.io import load_network
app=QApplication([]);window=Application()
window.set_network(load_network('examples/quantum/rossini4.json'));window.show();app.processEvents()
root=Path('validation/integration-ui');root.mkdir(exist_ok=True)
window.grab().save(str(root/'main.png'))
window.quantum_analysis();dialog=window.dialogs[-1]
dialog.complete(json.loads(Path('validation/demo-current/aer.json').read_text()))
dialog.compare();app.processEvents();dialog.grab().save(str(root/'comparison.png'))
dialog.plot();app.processEvents();window.windows[-1].grab().save(str(root/'measurements.png'))
window.close()
