import importlib.util
from pathlib import Path

def load_tool(name):
    path=Path(__file__).resolve().parents[1]/"tools"/(name+".py")
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_constant_certificate_preserves_unresolved_feedback():
    tool=load_tool("imc_basin_certificate")
    rules={"x":[["x"],[1,0]],"y":[[],[1]],"z":[["y","x"],[0,1,0,1]]}
    result=tool.certify(rules)
    assert result["waves"]==[{"y":1},{"z":1}]
    assert result["settling_upper"] is None

def test_trajectory_labels_cover_full_period_and_transient(tmp_path):
    import numpy as np
    tool=load_tool("transfer_basin_trial")
    model=tmp_path/"rotate.bnet"
    model.write_text("a,b\nb,!a\nc,0")
    net=tool.load_bnet(model)
    starts=np.array([[0,0,0],[0,0,1]],dtype=np.uint8)
    a,b=tool.labels(net,starts,4)
    assert a is not None and b is None
    assert tool.labels(net,starts,5)==[a,a]
