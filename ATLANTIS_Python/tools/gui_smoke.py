import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys
from pathlib import Path
sys.path.insert(0,str(Path('.deps').resolve()))
from PySide6 import QtWidgets
from atlantis.gui import Application
from atlantis.guide import GuideWindow
from atlantis.io import load_weighted
from atlantis.states import all_states
from atlantis.analysis import deterministic_analysis
app=QtWidgets.QApplication([]); app.setStyle('Fusion'); w=Application(); w.show(); app.processEvents()
Path('validation/gui').mkdir(exist_ok=True)
w.grab().save('validation/gui/main.png')
for p in Path('atlantis/assets/guide').glob('*.json'):
 if p.stem=='ATLANTIS':continue
 d=GuideWindow(p.stem); d.show(); app.processEvents(); d.grab().save('validation/gui/'+p.stem+'.png'); d.close()
print('Rendered all 14 GUIDE windows')
w.close()
from atlantis.graphviz_window import graphviz_svg,GraphvizWindow
from atlantis.plots import network_dot
n=load_weighted('examples/Case Study 1/Input Files/NetworkFile.csv')
g=GraphvizWindow(graphviz_svg(network_dot(n)));g.show();app.processEvents();g.fit();app.processEvents();g.grab().save('validation/gui/GraphvizView.png');g.close()
