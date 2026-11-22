from pathlib import Path
import sys
from atlantis.gui import Application, W, QtGui
from atlantis.io import load_network
from atlantis.fates import load_fate_logic
from atlantis.states import all_states

inputs = Path(__file__).resolve().parent.parent / "ATLANTIS/Sample Data/Case Study 1/Input Files"
app = W.QApplication(sys.argv)
app.setStyle("Fusion")
app.setFont(QtGui.QFont("Arial", 9))
window = Application()
network = load_network(inputs / "NetworkFile.csv")
window.set_network(network)
window.states = all_states(network.n)
window.fate_logic = load_fate_logic(inputs / "Cell Fate Determination Logic.csv", network)
window.last_directory = str(inputs)
window.setWindowTitle("ATLANTIS (Python) | Yeast cell cycle | 11 nodes")
window.show()
sys.exit(app.exec())
