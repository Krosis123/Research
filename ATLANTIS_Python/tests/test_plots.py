import numpy as np
import pytest
from atlantis.plots import *
from atlantis.projection import sammon_mapping,natural_neighbor
from atlantis.analysis import deterministic_analysis,probabilistic_analysis
from atlantis.states import all_states
from conftest import ROOT


def test_sammon_finite_with_appropriate_data():
    x=np.random.default_rng(12).normal(size=(12,5));xy,stress=sammon_mapping(x,max_iter=100)
    assert xy.shape==(12,2) and np.isfinite(xy).all() and stress>=0


def test_natural_linear_precision():
    p=np.array([[0,0],[1,0],[0,1],[1,1],[.4,.5]])
    q=np.array([[.2,.2],[.6,.5],[2,2]])
    z=natural_neighbor(p,2*p[:,0]-3*p[:,1]+1,q)
    np.testing.assert_allclose(z[:2],2*q[:2,0]-3*q[:2,1]+1,atol=1e-12)
    assert np.isnan(z[2])


def test_scientific_figures_render(yeast,yeast_states,tmp_path):
    from atlantis.fates import load_fate_logic
    from conftest import EXAMPLES
    logic=load_fate_logic(EXAMPLES/'Case Study 1/Input Files/Cell Fate Determination Logic.csv',yeast)
    d=deterministic_analysis(yeast,yeast_states,200,logic)
    r=probabilistic_analysis(yeast,yeast_states,max_steps=30,prune=True)
    figures=[network_figure(yeast),cell_fate_figure(d.fate_propensities)]
    for kind in ['basin','probability','energy']:
        f=landscape_figure(r.states,kind,d,r,seed=1,factor=1)
        assert f.axes[0].get_xlabel()=='States' and f.axes[0].get_zlim()==(0,1.08)
        figures.append(f)
    for i,f in enumerate(figures):
        path=tmp_path/f'{i}.png';f.savefig(path,dpi=100);assert path.stat().st_size>5000


def test_sammon_surface_figure():
    # Distinct real-valued saved coordinates avoid the source PCA degeneracy.
    states=all_states(4);xy=np.random.default_rng(4).normal(size=(16,2))
    from atlantis.analysis import Attractor,DeterministicResult
    d=DeterministicResult(states,[Attractor(states[:1],1.)],np.zeros(16,dtype=int),0,200)
    f=landscape_figure(states,'basin',d,mapping='sammon',coordinates=xy)
    assert np.isfinite(f.atlantis_data['grid']).any()


def test_invalid_energy_transform_is_reported(yeast,yeast_states):
    r=probabilistic_analysis(yeast,yeast_states,max_steps=11,prune=True)
    with pytest.raises(ValueError):landscape_values(r.states,'energy',probabilistic=r,factor=2)


def test_dot_uses_original_edge_order_and_colors(yeast):
    dot=network_dot(yeast)
    assert 'color=red' in dot and 'color=green' in dot
    assert dot.count(' -> ')==np.count_nonzero(yeast.weights)
    assert dot.index('"Cln3" -> "Cln3"')<dot.index('"Cln3" -> "MBF"')


def test_graphviz_if_installed(yeast):
    try:find_graphviz()
    except FileNotFoundError:pytest.skip('Graphviz external executable not installed')
    f=network_figure(yeast,'dot');assert len(f.atlantis_data['nodes'])==11


@pytest.mark.parametrize('extension',['png','jpg','tiff','svg','pdf','eps'])
def test_scientific_export_formats(yeast,yeast_states,tmp_path,extension):
    d=deterministic_analysis(yeast,yeast_states,200)
    f=landscape_figure(yeast_states,'basin',d,seed=83,annotate=False)
    p=tmp_path/('basin.'+extension);f.savefig(p,dpi=100)
    assert p.stat().st_size>1000
