"""Check every input phase, restored scratch qubit and analytical amplification curve."""
import runpy
from pathlib import Path

import pytest


def test_known_basin_oracle_and_amplification():
    pytest.importorskip("qiskit")
    module = runpy.run_path(str(Path(__file__).resolve().parents[1] / "tools/oracle_fixed_basin_study.py"))
    # run_study checks all amplitudes immediately after the oracle and at every iteration.
    result = module["run_study"]()
    assert result["marked"] == [127, 255]
    assert result["rows"][8]["success"] == pytest.approx(0.9956198656945)
    assert result["uniform_iid_trials_95"] == 382
