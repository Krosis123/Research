"""Actual Qiskit tests: skipped if local Qiskit is not installed."""
import pytest
pytest.importorskip('qiskit')
pytest.importorskip('qiskit_aer')
from ross_bench.runner import run_adaptive


def test_adaptive_real_aer_classical_coverage_stop():
    # Quantum suppression search is actual Aer; M and stop are classical.
    result=run_adaptive(4,'cycle2',0,42,'aer','exact',128,4,128,
                        0.0,20,False,1,3,2,'classical_audit',2,0.95,'report')
    assert result['status']=='complete_classically_certified'
    assert result['unique_attractors_found']==3
    assert result['attractor_recall']==1.0


def test_adaptive_real_qpe_stop_cycle2():
    # Includes counting AFTER all three cycles are discovered. QPE termination
    # remains heuristic, even if this test passes.
    result=run_adaptive(4,'cycle2',0,42,'aer','qpe_aer',128,5,128,
                        0.0,18,False,1,5,2,'qpe',2,0.95,'report')
    assert result['status']=='complete_qpe_heuristic'
    assert result['unique_attractors_found']==3
    assert result['counting_calls']>=4
