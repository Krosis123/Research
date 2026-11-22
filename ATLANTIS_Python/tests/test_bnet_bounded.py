from atlantis.io import load_network
from atlantis.bounded_basins import bounded_basins
from atlantis.symbolic_cycles import symbolic_cycles, classify_bounded_starts
import numpy as np
import pytest

@pytest.mark.parametrize("p",[5,6])
def test_exact_period_and_six_step_entry(tmp_path,p):
    path=tmp_path/"feedback.bnet"
    rows=[f"r{i},r{(i-1)%p}" for i in range(p)]
    rows+=["d0,0"]+[f"d{i},d{i-1}" for i in range(1,6)]
    path.write_text("targets,factors\n"+"\n".join(rows))
    net=load_network(path)
    sampled=bounded_basins(net,cancel=lambda: False)
    groups=symbolic_cycles(net,cancel=lambda: False)
    assert all(g["status"]=="complete" for g in groups)
    assert len(sampled["basins"])==sum(len(g["cycles"]) for g in groups)
    start=np.zeros((1,net.n),dtype=np.uint8)
    start[0,[0,p]]=1
    [(period,_,entry)]=classify_bounded_starts(net,start,groups)
    assert (period,entry)==(p,6)
    assert sampled["exhaustive"] and sampled["unresolved"]==0


@pytest.mark.parametrize("search", [bounded_basins, symbolic_cycles])
def test_desktop_cancel_callback(tmp_path, search):
    path = tmp_path / "identity.bnet"
    path.write_text("x,x")
    with pytest.raises(InterruptedError):
        search(load_network(path), cancel=lambda: True)
