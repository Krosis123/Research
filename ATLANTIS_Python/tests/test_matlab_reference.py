from pathlib import Path
import numpy as np
import pytest
from scipy.io import loadmat
from atlantis.analysis import deterministic_analysis,probabilistic_analysis
from atlantis.fates import load_fate_logic
from atlantis.model import Network,TruthRule
from atlantis.projection import natural_neighbor,naive_grid
from atlantis.geometry import treemap
from conftest import ROOT,EXAMPLES


def reference(name):
    p=ROOT/'validation'/name
    if not p.exists():pytest.skip('MATLAB fixture absent: '+name)
    return loadmat(p,simplify_cells=True)


def canonical(states):return tuple(sorted(tuple(row) for row in np.atleast_2d(states)))


def test_matlab_yeast_attractors(yeast,yeast_states):
    expected=reference('matlab_yeast_deterministic.mat')
    result=deterministic_analysis(yeast,yeast_states,200)
    actual={canonical(a.states):a.basin for a in result.attractors}
    target={canonical(row[0]):float(row[2]) for row in expected['attractorTable']}
    assert actual==target
    np.testing.assert_array_equal(yeast_states,expected['states'])
    np.testing.assert_array_equal(yeast.weights,expected['weights'])


def test_matlab_yeast_fates(yeast,yeast_states):
    expected=reference('matlab_yeast_fates.mat')
    logic=load_fate_logic(EXAMPLES/'Case Study 1/Input Files/Cell Fate Determination Logic.csv',yeast)
    result=deterministic_analysis(yeast,yeast_states,200,logic)
    target={canonical(row[0]):str(row[3]) if isinstance(row[3],str) else '' for row in expected['attractorTable']}
    assert {canonical(a.states):a.fate for a in result.attractors}==target


def test_matlab_probabilities(yeast,yeast_states):
    expected=reference('matlab_yeast_probabilistic.mat')
    result=probabilistic_analysis(yeast,yeast_states,5,.001,200,1e-7,True)
    np.testing.assert_array_equal(result.states,expected['states'])
    np.testing.assert_allclose(result.transition,expected['transition'],atol=5e-15,rtol=5e-13)
    np.testing.assert_allclose(result.probabilities,expected['probabilities'],atol=1e-12,rtol=1e-10)
    assert result.iterations==200 and not result.converged


def test_matlab_rules_cycles():
    expected=reference('matlab_rules_deterministic.mat')
    n=Network(['a','b'],rules=[TruthRule([0],[1,0]),TruthRule([1],[0,1])])
    result=deterministic_analysis(n,[[0,0],[0,1],[1,0],[1,1]],200)
    assert {canonical(a.states):a.basin for a in result.attractors}=={canonical(row[0]):float(row[2]) for row in expected['attractorTable']}


def test_matlab_natural_neighbor():
    d=reference('matlab_natural.mat');actual=natural_neighbor(d['p'],d['v'],d['q'])
    np.testing.assert_array_equal(np.isnan(actual),np.isnan(d['z']))
    np.testing.assert_allclose(actual,d['z'],atol=5e-12,equal_nan=True)


def test_matlab_treemap_geometry():
    d=reference('matlab_treemap.mat');actual=treemap([.62,.23,.1,.05])
    # findobj returns the patch handles in reverse creation order.
    np.testing.assert_allclose(actual,d['rectangles'][::-1],atol=1e-14)


def test_matlab_saved_naive_grid(yeast_states):
    d=reference('matlab_naive.mat');x,y,z,perm=naive_grid(yeast_states,d['z'],d['permutation'].astype(int)-1)
    np.testing.assert_array_equal(x,d['x']);np.testing.assert_array_equal(y,d['y'])
    padded=np.r_[d['z'],np.zeros(x.size-len(d['z']))]
    np.testing.assert_array_equal(z,padded[perm].reshape(x.shape,order='F'))


def test_matlab_sammon_newton_step():
    from atlantis.projection import sammon_mapping
    d=reference('matlab_sammon_step.mat');xy,stress=sammon_mapping(d['x'],max_iter=1)
    np.testing.assert_allclose(xy,d['xy'],atol=1e-13)
    assert abs(stress-d['stress'])<1e-15


@pytest.mark.parametrize('name',['jet','hot','spring','summer','autumn','winter','cool','gray','hsv','prism','parula'])
@pytest.mark.parametrize('n',[1,4,100])
def test_matlab_color_maps(name,n):
    from atlantis.plots import matlab_colors
    d=reference('matlab_colors.mat')
    np.testing.assert_allclose(matlab_colors(name,n),np.atleast_2d(d['maps'][f'{name}_{n}']),atol=1e-13)
