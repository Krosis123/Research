"""Original ATLANTIS CSV/TXT, truth tables, MAT arrays, and portable JSON sessions."""
from pathlib import Path
import csv,json,re
import numpy as np
from scipy.io import loadmat,savemat
from .model import Network,TruthRule,boolean_states,decimal_to_binary


def read_rows(path):
    text=Path(path).read_text(encoding='utf-8-sig',errors='replace')
    lines=[l for l in text.splitlines() if l.strip()]
    if not lines: return []
    delimiter='\t' if '\t' in lines[0] else ',' if ',' in lines[0] else None
    rows=list(csv.reader(lines,delimiter=delimiter)) if delimiter else [re.split(r'\s+',l.strip()) for l in lines]
    return [[x.strip() for x in row] for row in rows]


def write_rows(path,rows):
    with Path(path).open('w',newline='',encoding='utf-8-sig') as f: csv.writer(f).writerows(rows)


def load_weighted(path):
    rows=read_rows(path)
    if not rows: raise ValueError('Network file is empty')
    if rows[-1] == ['Weight Based'] and any(not any(row) for row in rows):
        # FPGA export: node list, source/weight/target edges, drawing metadata.
        separators = [i for i, row in enumerate(rows) if not any(row)]
        if len(separators) < 2:
            raise ValueError('Missing FPGA edge-list separator')
        nodes = rows[:separators[0]]
        if any(len(row) != 2 or not row[0] or row[1] != '1' for row in nodes):
            raise ValueError('Expected FPGA binary node records with value 1')
        names = [row[0] for row in nodes]
        index = {name: i for i, name in enumerate(names)}
        if len(index) != len(names):
            raise ValueError('Duplicate FPGA node')
        weights = np.zeros((len(names), len(names)))
        for row in rows[separators[0]+1:separators[1]]:
            if len(row) != 3 or row[0] not in index or row[2] not in index:
                raise ValueError(f'Invalid FPGA edge: {row!r}')
            weights[index[row[0]], index[row[2]]] += float(row[1])
        return Network(names, weights, name=Path(path).stem)
    names=rows[0][1:]; n=len(names)
    if len(rows)<n+2: raise ValueError('Weighted network needs N labeled rows and basal values')
    weights=np.array([[float(x) for x in row[1:n+1]] for row in rows[1:n+1]])
    remainder=rows[n+1:]
    basal=[]
    for row in remainder:
        for cell in row:
            if cell:
                try: basal.append(float(cell))
                except ValueError: pass
    return Network(names,weights,np.array(basal),name=Path(path).stem)


def save_weighted(network,path):
    if network.weights is None: raise ValueError('Network uses truth tables')
    write_rows(path,[['']+network.names]+[[name]+row.tolist() for name,row in zip(network.names,network.weights)]+[['basal']+network.basal.tolist()])


def load_rules(node_list,folder,allow_missing=False,*,missing_policy=None):
    rows=read_rows(node_list)
    names=[cell for row in rows for cell in row if cell]
    network=Network(names,rules=[None]*len(names),name=Path(node_list).stem)
    files={p.name.casefold():p for p in Path(folder).glob('*.txt')}
    rules=[]; missing=[]
    for name in names:
        p=files.get((name+'.txt').casefold())
        if p is None:
            if allow_missing or missing_policy == 'unspecified':
                rules.append(None); missing.append(name); continue
            raise ValueError(f'Missing truth table for {name}')
        table=read_rows(p)
        sources=[network.index(x) for x in table[0][:-1]]
        if table[0][-1].casefold()!=name.casefold(): raise ValueError(f'Truth table target does not match {name}')
        values=boolean_states([[float(x) for x in row] for row in table[1:]],len(sources)+1)
        if len(values)!=2**len(sources): raise ValueError(f'Incomplete truth table for {name}')
        if sources and not np.array_equal(values[:,:-1],decimal_to_binary(range(len(values)),len(sources))):
            raise ValueError(f'Truth table {name} must use ascending, MSB-first binary row order (original ATLANTIS convention)')
        rules.append(TruthRule(sources,values[:,-1]))
    network.rules=rules
    if missing:
        key = 'unspecified_rules' if missing_policy == 'unspecified' else 'assumed_identity_rules'
        network.metadata[key] = missing
    return network


def save_rules(network,folder):
    if any(name in ('.','..') or any(c in name for c in '/\\:') for name in network.names):
        raise ValueError('Node names are unsafe as filenames; export network JSON instead')
    p=Path(folder); p.mkdir(parents=True,exist_ok=True)
    write_rows(p/'Node List.txt',[[n] for n in network.names])
    tables=p/'Boolean logic for nodes'; tables.mkdir(exist_ok=True)
    for name,r in zip(network.names,network.rules):
        if r is None: continue
        inputs=decimal_to_binary(range(len(r.outputs)),len(r.sources)) if r.sources else np.empty((1,0),dtype=int)
        write_rows(tables/(name+'.txt'),[[network.names[i] for i in r.sources]+[name]]+np.column_stack((inputs,r.outputs)).tolist())


def load_mutations(path):
    rows=read_rows(path)
    return [(r[0],int(r[1])) for r in rows if len(r)>1 and r[0]]


def load_fixed_nodes(path):
    rows=read_rows(path)
    if len(rows)!=2 or len(rows[0])!=len(rows[1]): raise ValueError('Fixed nodes file requires node names in row 1 and states in row 2')
    return dict(zip(rows[0],[int(x) for x in rows[1]]))


def load_mat(path):
    try: return {k:v for k,v in loadmat(path,simplify_cells=True).items() if not k.startswith('__')}
    except NotImplementedError:
        import h5py
        with h5py.File(path) as h:
            def decode(obj):
                if isinstance(obj,h5py.Group): return {k:decode(v) for k,v in obj.items()}
                a=obj[()]
                if h5py.check_dtype(ref=obj.dtype) is not None:
                    return np.array([decode(h[r]) if r else None for r in a.flat],dtype=object).reshape(a.shape).T
                cls=obj.attrs.get('MATLAB_class',b'')
                if cls==b'char': return ''.join(chr(int(c)) for c in a.T.flat)
                return np.asarray(a).T
            return {k:decode(v) for k,v in h.items() if not k.startswith('#')}


def load_states(path,n):
    if Path(path).suffix.lower() in ('.mat','.npz'):
        d=load_mat(path) if Path(path).suffix.lower()=='.mat' else dict(np.load(path,allow_pickle=False))
        for key in ('NetworkStateList','networkStateList','initialStates','states','data'):
            if key in d:
                a=np.asarray(d[key])
                if n == 1 and a.ndim <= 1:
                    a = a.reshape(-1, 1)
                if a.dtype!=object and a.ndim<=2:
                    try: return boolean_states(a,n)
                    except ValueError: pass
        candidates=[]
        for v in d.values():
            try: candidates.append(boolean_states(v,n))
            except (ValueError,TypeError): pass
        if len(candidates)!=1: raise ValueError('MAT file must contain one unambiguous Boolean state matrix')
        return candidates[0]
    rows=read_rows(path)
    try: return boolean_states([[float(c) for c in r] for r in rows],n)
    except (ValueError,TypeError) as e: raise ValueError(f'Invalid state file: {e}') from e


def save_states(path,states):
    p=Path(path)
    if p.suffix.lower()=='.mat': savemat(p,{'networkStateList':np.asarray(states,dtype=float)},do_compression=True)
    else: write_rows(p,np.asarray(states).tolist())


def network_to_dict(network):
    from .expressions import ExpressionRule
    return {'names':network.names,'name':network.name,'weights':network.weights.tolist() if network.weights is not None else None,
        'basal':network.basal.tolist() if network.basal is not None else None,
        'rules':[({'expression':r.expression} if isinstance(r,ExpressionRule) else {'sources':r.sources,'outputs':r.outputs.tolist()}) if r else None for r in network.rules] if network.rules is not None else None,
        'positions':network.positions,'clamped':network.clamped,'metadata':network.metadata}


def save_network(network,path):
    Path(path).write_text(json.dumps(network_to_dict(network),indent=2),encoding='utf-8')


def load_mapping(path):
    """Read original {x,y} MAT mapping files or exported Python plot coordinates."""
    d=dict(np.load(path,allow_pickle=False)) if Path(path).suffix.lower()=='.npz' else load_mat(path)
    if 'data' in d:
        data=np.asarray(d['data'],dtype=object)
        if data.shape!=(2,2): raise ValueError('Original mapping data must contain the x/y header and coordinate row')
        x=np.asarray(data[1,0],dtype=float).squeeze(); y=np.asarray(data[1,1],dtype=float).squeeze()
        if x.ndim==1 and y.ndim==1: return {'coordinates':np.column_stack((x,y))}
        raise ValueError('This original Naive Mapping file saves the grid but omits the state permutation. The original random placement cannot be recovered. Import a Python plot-data NPZ containing the permutation instead.')
    if 'coordinates' not in d: raise ValueError('No saved mapping coordinates found')
    return d


def load_network(path):
    if Path(path).suffix.lower()!='.json': return load_weighted(path)
    if Path(path).stat().st_size>16*1024**2: raise ValueError('Network JSON exceeds 16 MiB limit')
    d=json.loads(Path(path).read_text(encoding='utf-8'))
    return network_from_dict(d)


def network_from_dict(d):
    from .expressions import ExpressionRule,from_expressions
    d=dict(d)
    if isinstance(d.get('rules'),dict):
        net=from_expressions(d['rules'],d.get('name','Boolean network'))
        return Network(net.names,rules=net.rules,name=net.name,clamped=d.get('clamped',{}),metadata=d.get('metadata',{}))
    if d.get('rules') is not None:
        d['rules']=[(ExpressionRule(r['expression'],d['names']) if 'expression' in r else TruthRule(**r)) if r else None for r in d['rules']]
    return Network(**d)


def export_results(folder,network,deterministic=None,probabilistic=None):
    p=Path(folder); p.mkdir(parents=True,exist_ok=True)
    save_network(network,p/'network.json')
    if deterministic:
        d=deterministic
        save_states(p/'Network State List DA.mat',d.initial_states)
        save_states(p/'Network State List DA.csv',d.initial_states)
        header=['Attractor #','Attractor Type','Associated Cell Fate','Basin Size']+network.names
        full=[]; avg=[]; strat=[]
        for i,a in enumerate(d.attractors,1):
            for row in a.states: full.append([i,a.kind,a.fate,a.basin]+row.tolist())
            avg.append([i,a.kind,a.fate,a.basin]+a.average.tolist())
            strat.append([i,a.kind,a.fate,a.basin]+a.stratified.tolist())
        write_rows(p/'Attractor Table.csv',[header]+full)
        write_rows(p/'Attractor Table (Average Activity in Fractions).csv',[header]+avg)
        write_rows(p/'Attractor Table (Stratified Average Activity).csv',[header]+strat)
        write_rows(p/'Cell Fate Propensites.csv',[['Cell Fate','Propensity']]+list(d.fate_propensities.items()))
        Path(p/'deterministic.json').write_text(json.dumps({'unresolved':d.unresolved,'search_duration':d.search_duration,'coverage':d.coverage,'attractors':[{'states':a.states.tolist(),'basin':a.basin,'fate':a.fate} for a in d.attractors]},indent=2))
    if probabilistic:
        r=probabilistic
        save_states(p/('Prunned Network State List PA.mat' if r.pruned else 'Network State List PA.mat'),r.states)
        write_rows(p/'Steady State Probabilities.csv',[['Probability','Cell Fate']+network.names]+[[float(prob),r.fates[i] if r.fates else '']+s.tolist() for i,(prob,s) in enumerate(zip(r.probabilities,r.states))])
        savemat(p/'Probabilistic Results.mat',{'states':r.states.astype(float),'StateTransitionProbabilities':r.transition,'SteadyStateProbabilities':r.probabilities[:,None]},do_compression=True)
        Path(p/'probabilistic.json').write_text(json.dumps({
            'iterations':r.iterations,'converged':r.converged,'noise':r.noise,
            'degradation':r.degradation,'error':r.error,'pruned':r.pruned,
            'convergence_criterion':'historical 98% componentwise change',
            'flux_residual_inf':r.flux_residual_inf},indent=2))
        if r.trajectory is not None:
            write_rows(p/'Trajectory.csv',[['State Index','Probability']+network.names]+[[int(i)+1,float(r.probabilities[i])]+r.states[i].tolist() for i in r.trajectory])
