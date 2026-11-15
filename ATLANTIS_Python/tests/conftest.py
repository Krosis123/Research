from pathlib import Path
import os,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
local=Path(__file__).resolve().parents[1]/'.deps'
if local.exists(): sys.path.insert(0,str(local))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('MPLBACKEND','Agg')
import pytest
from atlantis.io import load_weighted
from atlantis.states import all_states

ROOT=Path(__file__).resolve().parents[1]
EXAMPLES=ROOT/'examples'
if not EXAMPLES.exists(): EXAMPLES=ROOT/'original/ATLANTIS/Sample Data'

@pytest.fixture(scope='session')
def yeast(): return load_weighted(EXAMPLES/'Case Study 1/Input Files/NetworkFile.csv')
@pytest.fixture(scope='session')
def yeast_states(yeast): return all_states(yeast.n)
@pytest.fixture(scope='session')
def qtapp():
    from PySide6.QtWidgets import QApplication
    from atlantis.guide import load_system_fonts
    app=QApplication.instance() or QApplication([]);load_system_fonts();yield app
