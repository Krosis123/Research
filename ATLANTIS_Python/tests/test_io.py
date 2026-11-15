from pathlib import Path
import numpy as np
import pytest
from atlantis import io
from atlantis.fates import load_fate_logic
from atlantis.model import Network,TruthRule
from atlantis.analysis import deterministic_analysis,probabilistic_analysis
from atlantis.states import all_states
from conftest import EXAMPLES,ROOT


@pytest.mark.parametrize('suffix',['.csv','.mat'])
def test_state_roundtrip(tmp_path,suffix):
    states=all_states(3);p=tmp_path/('states'+suffix);io.save_states(p,states)
    np.testing.assert_array_equal(io.load_states(p,3),states)


def test_weighted_roundtrip(yeast,tmp_path):
    p=tmp_path/'network.csv';io.save_weighted(yeast,p);n=io.load_weighted(p)
    np.testing.assert_array_equal(n.weights,yeast.weights);np.testing.assert_array_equal(n.basal,yeast.basal);assert n.names==yeast.names


def test_json_roundtrip(yeast,tmp_path):
    p=tmp_path/'network.json';io.save_network(yeast,p);n=io.load_network(p)
    np.testing.assert_array_equal(n.step(all_states(n.n)),yeast.step(all_states(n.n)))


def test_rules_roundtrip(tmp_path):
    n=Network(['a','b'],rules=[TruthRule([0],[1,0]),TruthRule([1],[0,1])]);io.save_rules(n,tmp_path)
    r=io.load_rules(tmp_path/'Node List.txt',tmp_path/'Boolean logic for nodes')
    np.testing.assert_array_equal(n.step(all_states(2)),r.step(all_states(2)))


def test_original_fate_expansion_wildcards(tmp_path):
    p=tmp_path/'fates.csv';p.write_text(',a,b\ncycling,2,\nactive,1,0 1\n')
    n=Network(['a','b'],np.zeros((2,2)));logic=load_fate_logic(p,n)
    assert logic.associate([2,0])=='cycling';assert logic.associate([1,1])=='active';assert logic.associate([0,0])==''


def test_all_weighted_case_study_networks():
    count=0
    for p in EXAMPLES.rglob('*.csv'):
        if p.name=='NetworkFile.csv' or p.name in ('Control_MCF7 (0).csv','Etoposide.csv'):
            n=io.load_weighted(p);assert n.n in (11,16);count+=1
    assert count>=3


@pytest.mark.parametrize('case',['Case Study 3','Case Study 4'])
def test_large_rule_networks(case):
    root=EXAMPLES/case/'Input Files/Network Details'
    n=io.load_rules(root/'Node List.txt',root/'Boolean logic for nodes',allow_missing=True)
    assert n.n==201
    states=io.load_states(EXAMPLES/case/'Input Files/Network State Lists/Simulation 1.mat',n.n)
    assert states.shape==(10000,201)
    updated=n.step(states[:32]);assert updated.shape==(32,201)
    assert set(np.unique(updated))<={0,1}


def test_export_results(yeast,tmp_path):
    d=deterministic_analysis(yeast,all_states(11),200)
    r=probabilistic_analysis(yeast,all_states(11),max_steps=11,prune=True)
    io.export_results(tmp_path,yeast,d,r)
    assert (tmp_path/'Attractor Table.csv').exists()
    assert io.read_rows(tmp_path/'Attractor Table.csv')[0][:4]==['Attractor #','Attractor Type','Associated Cell Fate','Basin Size']
    np.testing.assert_array_equal(io.load_states(tmp_path/'Network State List DA.mat',11),all_states(11))


def test_bad_state_file(tmp_path):
    p=tmp_path/'bad.csv';p.write_text('0,2\n')
    with pytest.raises(ValueError):io.load_states(p,2)


def test_original_mapping_files_load():
    base=ROOT/'original/ATLANTIS/Toolbox/Results'
    if not base.exists():base=ROOT/'reference/Toolbox/Results'
    files=list(base.rglob('*Mapping Results.mat'))
    if not files:pytest.skip('Original result bundle not present')
    for p in files: assert io.load_mat(p)['data'].shape==(2,2)


@pytest.mark.parametrize('mutation',['Control','Nutlin'])
def test_archived_p53_attractors(mutation):
    from atlantis.states import all_states
    p=EXAMPLES/'Case Study 2/Input Files'
    n=io.load_weighted(p/'Network files/DNA Damge OFF/Control_MCF7 (0).csv')
    n=n.mutate(io.load_mutations(p/('Mutation Files/'+mutation+'.txt')))
    logic=load_fate_logic(p/'Cell Fate Determination Logic.csv',n)
    d=deterministic_analysis(n,all_states(n.n),200,logic)
    source=ROOT/'original/ATLANTIS/Toolbox/Results'
    if not source.exists():source=ROOT/'reference/Toolbox/Results'
    files=list(source.rglob(mutation+' - Attractor Table.csv'))
    if not files:pytest.skip('Archived MATLAB result not available')
    expected=io.read_rows(files[0])[1:]
    expected=[r for r in expected if r and r[0]]
    assert len(expected)==len(d.attractors)
    for row,a in zip(expected,d.attractors):
        np.testing.assert_array_equal(a.states[0],[int(x) for x in row[4:] if x])
        assert a.fate==row[2] and abs(a.basin-float(row[3]))<5e-6


def test_supplementary_boolnet_conversion(tmp_path):
    from atlantis.boolnet import truth_tables_to_boolnet
    p=tmp_path/'tables';p.mkdir();(p/'b.txt').write_text('a\tb\n0\t1\n1\t0\n')
    out=tmp_path/'network.txt';truth_tables_to_boolnet(p,out)
    assert out.read_text()=='targets,factors\nb, (!a)\n'

def test_missing_rules_require_explicit_resolution(tmp_path):
    import json
    from dataclasses import replace
    from atlantis.io import load_rules, network_from_dict, network_to_dict
    from atlantis.quantum.adapter import QuantumNetwork

    nodes = tmp_path / 'nodes.txt'
    nodes.write_text('Input\nFixed\n')
    network = load_rules(nodes, tmp_path, missing_policy='unspecified')
    with pytest.raises(ValueError, match='Unspecified update rules'):
        network.step([[0, 1]])
    with pytest.raises(ValueError, match='Unspecified update rules'):
        QuantumNetwork(network)
    resolved = replace(network, clamped={'Fixed': 0},
                       metadata={**network.metadata, 'external_inputs': ['Input']})
    restored = network_from_dict(json.loads(json.dumps(network_to_dict(resolved))))
    assert restored.step([[0, 1], [1, 1]]).tolist() == [[0, 0], [1, 0]]
    assert QuantumNetwork(restored).step(3) == 2
    mutated = network_from_dict(network_to_dict(restored.mutate([('Input', 1)])))
    assert mutated.step([[0, 1]]).tolist() == [[1, 0]]
